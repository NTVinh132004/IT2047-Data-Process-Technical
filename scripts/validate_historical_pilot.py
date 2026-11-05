"""Đối soát pilot historical; báo cáo này không phải cổng C5."""
import hashlib
import csv
import io
import json
import re
import subprocess
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
PROJECT = 'mortgage-datavault-historical'


def spark_sql(query):
    result = subprocess.run(['docker', 'compose', '-p', PROJECT, 'exec', '-T', 'spark-thrift',
        '/opt/spark/bin/beeline', '-u', 'jdbc:hive2://localhost:10000', '-n', 'lakehouse',
        '--silent=true', '--outputformat=csv2', '-e', query], capture_output=True, text=True, check=True)
    lines = [re.sub(r'^\d+: jdbc:hive2://\S+> ?', '', line) for line in result.stdout.splitlines()]
    rows = list(csv.DictReader(io.StringIO('\n'.join(line for line in lines if line))))
    if not rows:
        raise RuntimeError('Không có kết quả SQL: ' + result.stderr[-1000:])
    return rows


def main():
    report_dir = ROOT / 'data/reports/historical'
    manifest = json.loads((report_dir / 'source-manifest.json').read_text())
    assert manifest['passed']
    expected_perf = sum(n for f in manifest['files'] for m, n in f['months'].items() if '201901' <= m <= '201903')
    env = dict(line.split('=', 1) for line in (ROOT / '.env').read_text().splitlines() if '=' in line and not line.startswith('#'))
    with psycopg.connect(host='127.0.0.1', port=5433, dbname='analytics', user=env['POSTGRES_USER'], password=env['POSTGRES_PASSWORD']) as conn, conn.cursor() as cur:
        cur.execute("SELECT layer FROM control.layer_run WHERE period='2019Q1' AND dataset='historical' AND status='SUCCESS'")
        layers = {r[0] for r in cur.fetchall()}
        assert layers == {'ingest', 'quality', 'raw_vault', 'business_vault', 'gold', 'export'}, layers
        checks = {}
        for mart in ['mart_delinquency', 'mart_prepayment', 'mart_covid_forbearance']:
            cur.execute(f'SELECT COUNT(*) FROM serving.{mart}')
            count = cur.fetchone()[0]
            assert count == int(spark_sql(f'SELECT COUNT(*) AS n FROM gold.{mart}')[0]['n'])
            checks[mart] = count
    row = spark_sql("SELECT COUNT(*) AS n FROM bronze.perf WHERE period='2019Q1'")[0]
    assert int(row['n']) == expected_perf, (row, expected_perf)
    ac05 = spark_sql("WITH b AS (SELECT reporting_period, COUNT(*) n, SUM(CAST(current_upb AS DECIMAL(20,4))) upb FROM bronze.perf GROUP BY reporting_period), f AS (SELECT DATE_FORMAT(reporting_date,'yyyyMM') reporting_period, COUNT(*) n, SUM(current_upb) upb FROM gold.fact_loan_month GROUP BY reporting_date) SELECT COUNT(*) months, SUM(CASE WHEN NOT (b.upb <=> f.upb) OR NOT (b.n <=> f.n) THEN 1 ELSE 0 END) wrong FROM b FULL OUTER JOIN f ON b.reporting_period=f.reporting_period")[0]
    assert int(ac05['months']) > 0 and int(ac05['wrong']) == 0, ac05
    report = dict(scope='historical pilot 2019Q1, không phải C5', passed=True,
                  bronze_perf_rows=expected_perf, ac05=ac05, export_rows=checks,
                  manifest_sha256=hashlib.sha256((report_dir / 'source-manifest.json').read_bytes()).hexdigest())
    (report_dir / 'pilot.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
