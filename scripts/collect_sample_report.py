"""Đọc sample hiện hữu, đối soát nguồn/Delta/PostgreSQL và xuất số liệu tổng hợp cho báo cáo."""
import hashlib
import json
import os
import subprocess
from decimal import Decimal
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import psycopg2
from psycopg2.extensions import make_dsn
from psycopg2.extras import RealDictCursor
from deltalake import DeltaTable
from ingestion.config import Config
from ingestion.control import status

ROOT = Path(__file__).resolve().parents[1]


def validate_monthly(counts, upb, rows):
    if {r['reporting_date'].replace('-', '')[:6] for r in rows} != set(counts):
        raise RuntimeError('Thiếu hoặc thừa tháng')
    for row in rows:
        month = row['reporting_date'].replace('-', '')[:6]
        if row['loan_count'] != counts[month] or Decimal(str(row['total_upb'])) != Decimal(str(upb[month])):
            raise RuntimeError('Số dòng hoặc dư nợ từng tháng lệch TXT')


def main():
    cfg = Config()
    if cfg.source != 'sample':
        raise RuntimeError('Chỉ thu thập sample')
    output = ROOT / 'data/reports/sample-report'
    output.mkdir(parents=True, exist_ok=True)
    (output / 'collector-source.py').write_bytes(Path(__file__).read_bytes())
    report = {'commit': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(), 'uncommitted_changes': bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()), 'collector_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'measured_at': datetime.now(timezone.utc).isoformat(), 'dataset': 'sample', 'passed': False}
    env = dict(line.split('=', 1) for line in (ROOT / '.env').read_text().splitlines()
               if '=' in line and not line.startswith('#'))
    os.environ['ANALYTICS_DSN'] = make_dsn(host='127.0.0.1',port=5432,dbname='analytics',
                     user=env['POSTGRES_USER'],password=env['POSTGRES_PASSWORD'])
    stages = status(cfg)
    if len(stages) != 30 or any(v != 'SUCCESS' for r in stages for k,v in r.items() if k != 'period'):
        raise RuntimeError('Sample chưa SUCCESS đủ 29 quý và CORR1')
    report['completed_periods'] = stages
    raw = ROOT / 'data/raw/sample_2019'
    report['source_files'] = []
    for kind, schema in [('orig',cfg.orig),('perf',cfg.perf)]:
        path = raw / schema.file_pattern['sample'].format(vintage=cfg.vintage)
        digest = hashlib.sha256(); rows = 0; loans = set(); months = Counter()
        loan_pos = next(c.pos for c in schema.columns if c.role == 'loan_key') - 1
        monthly_upb = Counter()
        upb_pos = next((c.pos-1 for c in schema.columns if c.name == 'current_upb'), None)
        month_pos = next((c.pos-1 for c in schema.columns if c.role == 'reporting_period'), None)
        with path.open('rb') as stream:
            for line in stream:
                digest.update(line); fields = line.rstrip(b'\r\n').split(b'|')
                if len(fields) != schema.field_count:
                    raise RuntimeError('Sai số trường trong nguồn')
                loans.add(fields[loan_pos]); rows += 1
                if month_pos is not None:
                    month = fields[month_pos].decode()
                    months[month] += 1
                    monthly_upb[month] += Decimal(fields[upb_pos].decode() or '0')
        report['source_files'].append(dict(kind=kind,name=path.name,bytes=path.stat().st_size,
             sha256=digest.hexdigest(),rows=rows,loans=len(loans),months=dict(sorted(months.items())), monthly_upb=dict(sorted(monthly_upb.items()))))
    report['tables'] = {}
    names = {'bronze':['orig','perf'], 'quality':[f'{k}_{s}' for k in ('orig','perf') for s in ('clean','quarantine','dedup')],
             'raw_vault':['hub_loan','sat_loan_origination'], 'baseline':['baseline_dim_loan_overwrite'],
             'business_vault':['pit_loan_monthly','bsat_loan_risk','bsat_loan_lifecycle'],
             'gold':['fact_loan_month','dim_loan','dim_date','mart_delinquency','mart_prepayment','mart_covid_forbearance']}
    for database, tables in names.items():
        for name in tables:
            dt = DeltaTable(str(ROOT / 'data/lake/warehouse' / f'{database}.db' / name))
            actions = pa.table(dt.get_add_actions(flatten=True)).to_pydict()
            rows = actions.get('num_records',[])
            if any(v is None for v in rows): raise RuntimeError('Thiếu thống kê dòng Delta')
            report['tables'][f'{database}.{name}'] = dict(rows=sum(rows),version=dt.version())
    with psycopg2.connect(os.environ['ANALYTICS_DSN']) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        def query(sql):
            cur.execute(sql); return [dict(r) for r in cur.fetchall()]
        publication = query("SELECT dataset,ready FROM control.gold_publication WHERE dataset='sample'")
        if publication != [{'dataset':'sample','ready':True}]: raise RuntimeError('Gold chưa sẵn sàng')
        report['export_rows'] = {}
        for mart in names['gold'][-3:]:
            n = query(f'SELECT COUNT(*) AS n FROM serving.{mart}')[0]['n']
            if n != report['tables'][f'gold.{mart}']['rows']: raise RuntimeError('Export lệch Gold')
            report['export_rows'][mart] = n
        report['monthly'] = query("SELECT reporting_date::text, SUM(loan_count)::bigint loan_count, SUM(eligible_count)::bigint eligible_count, SUM(d30_count)::bigint d30_count, SUM(d60_count)::bigint d60_count, SUM(d90_plus_count)::bigint d90_plus_count, SUM(total_upb) total_upb FROM serving.mart_delinquency GROUP BY reporting_date ORDER BY reporting_date")
        report['bands'] = {}
        for column in ['credit_score_band','ltv_band','dti_band','property_state','seller_name']:
            report['bands'][column] = query(f'SELECT {column} AS label,SUM(eligible_count)::bigint eligible_count,SUM(d90_plus_count)::bigint d90_plus_count FROM serving.mart_delinquency GROUP BY {column} ORDER BY {column}')
        report['covid'] = query('SELECT outcome,SUM(loan_count)::bigint loan_count FROM serving.mart_covid_forbearance GROUP BY outcome ORDER BY outcome')
        report['prepayment'] = query('SELECT reporting_date::text,prepaid_count,prepaid_upb,previous_active_upb,smm,cpr FROM serving.mart_prepayment ORDER BY reporting_date')
    perf = next(f for f in report['source_files'] if f['kind']=='perf')
    if sum(r['loan_count'] for r in report['monthly']) != perf['rows']: raise RuntimeError('Gold không bảo toàn perf')
    if len(report['monthly']) != len(perf['months']): raise RuntimeError('Thiếu tháng Gold')
    validate_monthly(perf['months'], perf['monthly_upb'], report['monthly'])
    for kind in ('orig','perf'):
        n=report['tables'][f'bronze.{kind}']['rows']
        if n != sum(report['tables'][f'quality.{kind}_{suffix}']['rows'] for suffix in ('clean','quarantine','dedup')):
            raise RuntimeError('Quality không bảo toàn số dòng')
    book = json.loads((ROOT / 'data/reports/rui_ro_tin_dung.executed.ipynb').read_text())
    report['notebook_figures'] = sum('image/png' in o.get('data',{}) for c in book['cells'] for o in c.get('outputs',[]))
    if any(o.get('output_type')=='error' for c in book['cells'] for o in c.get('outputs',[])): raise RuntimeError('Notebook có lỗi')
    report['gate_evidence'] = {}
    for gate,filename in [('C1','c1-20261030-140936.json'),('C2','c2-20261030-143422.json'),('C3','c3-20261030-145648.json'),('C4','c4-20261030-150942.json')]:
        report['gate_evidence'][gate] = json.loads((ROOT / 'tests/gates/results' / filename).read_text())
    report['passed'] = True
    (output / 'metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str))
    print(json.dumps({'passed':True,'completed_periods':len(stages),'source':[{k:f[k] for k in ['kind','rows','loans','bytes']} for f in report['source_files']], 'months':len(report['monthly']),'export_rows':report['export_rows'],'notebook_figures':report['notebook_figures']},ensure_ascii=False))


if __name__ == '__main__':
    main()
