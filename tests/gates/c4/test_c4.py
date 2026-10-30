"""C4: đối soát Gold, JDBC, notebook; AC-07 và hồi quy sạch do scripts/verify_clean.py thực thi."""
from decimal import Decimal
import json
import os
import time

import psycopg
import pytest

from ingestion.config import Config
from scripts.run_notebook import run as execute_notebook
from tests.gates.c2.test_c2 import spark_sql
from tests.gates.c4.oracle import compute, month_index
from tests.gates.conftest import ROOT, dotenv, save_gate_result, sh

RESULT = {}
MARTS = ['mart_delinquency', 'mart_prepayment', 'mart_covid_forbearance']


@pytest.fixture(scope='module')
def loaded():
    start = time.monotonic()
    sh('make', 'up', timeout=1800)
    sh('make', 'run-all', timeout=6*3600)
    RESULT['run_all_seconds'] = round(time.monotonic() - start, 1)


@pytest.fixture(scope='module', autouse=True)
def record(request):
    yield
    selected = {item.name for item in request.session.items if item.path == request.node.path}
    expected = {name for name, value in globals().items() if name.startswith('test_') and callable(value)}
    RESULT['selected_checks'] = sorted(selected)
    RESULT['passed'] = selected == expected and request.session.testsfailed == 0
    save_gate_result('C4', RESULT)


def test_ac05_exact_monthly_upb_and_fact_grain(loaded):
    row = spark_sql("WITH b AS (SELECT reporting_period, COUNT(*) AS n, SUM(CAST(current_upb AS DECIMAL(20,4))) AS upb FROM bronze.perf GROUP BY reporting_period),"
                    " f AS (SELECT DATE_FORMAT(reporting_date,'yyyyMM') AS reporting_period, COUNT(*) AS n, SUM(current_upb) AS upb FROM gold.fact_loan_month GROUP BY reporting_date)"
                    " SELECT COUNT(*) AS months, SUM(CASE WHEN NOT (b.upb <=> f.upb) OR NOT (b.n <=> f.n) THEN 1 ELSE 0 END) AS wrong"
                    " FROM b FULL OUTER JOIN f ON b.reporting_period=f.reporting_period")[0]
    RESULT['ac05'] = row
    assert int(row['months']) > 0 and int(row['wrong']) == 0
    out = sh('docker','compose','exec','-T','airflow-scheduler','bash','-c',
             'cd /opt/project/dbt && /opt/dbt-venv/bin/dbt test --select gold --indirect-selection cautious', check=False)
    RESULT['dbt_tests_pass'] = out.returncode == 0
    assert out.returncode == 0, out.stdout[-5000:]


def test_marts_match_independent_txt_oracle(loaded):
    monthly, outcomes = compute(Config())
    fields = ['loan_count','total_upb','eligible_count','eligible_upb','d30_count','d60_count','d90_plus_count','d30_upb','d60_upb','d90_plus_upb']
    rows = spark_sql('SELECT DATE_FORMAT(reporting_date,\'yyyyMM\') AS month, '+', '.join(f'SUM({f}) AS {f}' for f in fields)+' FROM gold.mart_delinquency GROUP BY reporting_date')
    assert {r['month'] for r in rows} == set(monthly)
    wrong = sum(Decimal(r[f] or 0) != monthly[r['month']][f] for r in rows for f in fields)
    assert wrong == 0, f'{wrong} tổng tháng sai so với TXT'
    prepay = spark_sql('SELECT DATE_FORMAT(reporting_date,\'yyyyMM\') AS month, prepaid_count, prepaid_upb, previous_active_upb, smm, cpr FROM gold.mart_prepayment')
    by_index = {month_index(m): v for m,v in monthly.items()}
    for r in prepay:
        expected = monthly[r['month']]
        assert Decimal(r['prepaid_count']) == expected['prepaid_count']
        assert Decimal(r['prepaid_upb']) == expected['prepaid_upb']
        prev = by_index.get(month_index(r['month'])-1)
        if prev is None or prev['active_upb'] == 0:
            assert r['smm'] is None
        else:
            assert Decimal(r['previous_active_upb']) == prev['active_upb']
            smm = expected['prepaid_upb']/prev['active_upb']
            assert abs(Decimal(r['smm'])-smm) < Decimal('0.00000001')
            assert abs(Decimal(r['cpr'])-(1-(1-smm)**12)) < Decimal('0.0000001')
    actual = {r['outcome']:int(r['n']) for r in spark_sql('SELECT outcome, SUM(loan_count) AS n FROM gold.mart_covid_forbearance GROUP BY outcome')}
    assert actual == dict(outcomes), (actual, outcomes)
    RESULT['oracle'] = {'months':len(monthly),'monthly_mismatches':wrong,'covid_outcomes':actual}


def test_postgres_export_matches_delta(loaded):
    env = dotenv()
    with psycopg.connect(host='127.0.0.1',dbname='analytics',user=env['POSTGRES_USER'],password=env['POSTGRES_PASSWORD']) as conn, conn.cursor() as cur:
        counts = {}
        for name in MARTS:
            cur.execute(f'SELECT COUNT(*) FROM serving.{name}')
            actual = cur.fetchone()[0]
            expected = int(spark_sql(f'SELECT COUNT(*) AS n FROM gold.{name}')[0]['n'])
            assert actual == expected and expected > 0
            counts[name] = actual
    RESULT['export_rows'] = counts


def test_gold_history_uses_pit_origination_version(loaded):
    row = spark_sql("SELECT COUNT(*) AS n FROM gold.fact_loan_month f JOIN business_vault.pit_loan_monthly p ON p.LOAN_HK=f.LOAN_HK AND p.AS_OF_DATE=f.load_date"
                    " WHERE f.loan_version_key <> CONCAT(p.SAT_LOAN_ORIGINATION_PK, ':', CAST(p.SAT_LOAN_ORIGINATION_LDTS AS STRING))")[0]
    assert int(row['n']) == 0


def test_ac08_execute_notebook(loaded):
    book = execute_notebook()
    figures = sum('image/png' in out.get('data',{}) for c in book.cells if c.cell_type == 'code' for out in c.outputs)
    assert figures >= 5
    RESULT['ac08'] = {'executed':True,'figures':figures}


def test_rerun_only_new_layers_preserves_gold_and_export(loaded):
    tables = ['fact_loan_month','dim_loan','dim_seller','dim_servicer','dim_geography','dim_date',*MARTS]
    def snapshot():
        return {r['t']:int(r['n']) for r in spark_sql(' UNION ALL '.join(f"SELECT '{t}' AS t, COUNT(*) AS n FROM gold.{t}" for t in tables))}
    before = snapshot()
    sh('docker','compose','exec','-T','airflow-scheduler','python','-m','ingestion.control','invalidate',
       '--layers','gold,export','--reason','C4 kiểm idempotent Gold/export')
    sh('make','run-all',timeout=7200)
    after = snapshot()
    assert after == before
    RESULT['rerun'] = {'before':before,'after':after}
    test_postgres_export_matches_delta(loaded)


def test_ac07_clean_reproduction(loaded):
    from scripts.verify_clean import source_digest
    if os.environ.get('C4_CLEAN_RUN') == '1':
        context = json.loads((ROOT/'data/clean-context.json').read_text())
        assert context['lake_initially_absent'] and (ROOT/'.git').is_dir()
        assert os.environ['COMPOSE_PROJECT_NAME'] == context['project']
    else:
        path = ROOT/'data/reports/clean-run.json'
        assert path.exists(), 'Chạy make verify-clean để xác minh AC-07 trên bản clone và volume riêng'
        context = json.loads(path.read_text())
        assert context['passed'] is True
    assert source_digest(ROOT, context['source_files']) == context['source_digest']
    RESULT['ac07'] = {'isolated_clone':True, 'source_digest':context['source_digest']}


def test_export_publication_rolls_back_all_marts_on_error(loaded):
    import psycopg2
    from ingestion.export import publish
    # Chỉ tạo bảng dữ liệu tổng hợp giả lập; không làm thay đổi mart đang phục vụ.
    env = dotenv()
    params = dict(host='127.0.0.1',dbname='analytics',user=env['POSTGRES_USER'],password=env['POSTGRES_PASSWORD'])
    dsn = psycopg2.extensions.make_dsn(**params)
    names = ['c4_probe_one','c4_probe_two']
    try:
        with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
            for name in names:
                cur.execute(f'CREATE TABLE serving.{name} (n INTEGER)')
                cur.execute(f'INSERT INTO serving.{name} VALUES (7)')
            cur.execute('CREATE TABLE export_stage.c4_probe_one (n INTEGER)')
            cur.execute('INSERT INTO export_stage.c4_probe_one VALUES (8)')
            cur.execute('CREATE TABLE export_stage.c4_probe_two (n TEXT)')
            cur.execute("INSERT INTO export_stage.c4_probe_two VALUES ('bad')")
        with pytest.raises(psycopg2.Error):
            publish(dsn,names)
        with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
            for name in names:
                cur.execute(f'SELECT n FROM serving.{name}')
                assert cur.fetchall() == [(7,)]
        RESULT['export_rollback'] = True
    finally:
        with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
            for schema in ('serving','export_stage'):
                for name in names:
                    cur.execute(f'DROP TABLE IF EXISTS {schema}.{name}')


def test_failed_gold_cannot_be_exported(loaded, monkeypatch):
    import psycopg2
    from types import SimpleNamespace
    from ingestion import control, layers
    import ingestion.config
    env = dotenv()
    params = dict(host='127.0.0.1',dbname='analytics',user=env['POSTGRES_USER'],password=env['POSTGRES_PASSWORD'])
    monkeypatch.setattr(control,'connect',lambda: psycopg2.connect(**params))
    monkeypatch.setattr(ingestion.config,'Config',lambda: SimpleNamespace(source='C4_SYNTHETIC'))
    def fail(*args, **kwargs):
        raise ValueError('Lỗi Gold giả lập')
    monkeypatch.setattr(layers,'_run',fail)
    try:
        with pytest.raises(ValueError,match='Lỗi Gold giả lập'):
            layers.run('gold',['2019Q1'])
        with pytest.raises(RuntimeError,match='Gold chưa có snapshot'):
            layers.run('export',['2019Q1'])
        RESULT['failed_gold_blocks_export'] = True
    finally:
        with psycopg2.connect(**params) as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM control.gold_publication WHERE dataset='C4_SYNTHETIC'")


def test_gold_dependencies_stay_in_vault_and_gold(loaded):
    manifest = json.loads((ROOT/'dbt/target/manifest.json').read_text())
    checked = []
    for node in manifest['nodes'].values():
        if node['resource_type'] == 'model' and node['schema'] == 'gold':
            for parent in node['depends_on']['nodes']:
                upstream = manifest['nodes'].get(parent)
                assert upstream is not None and upstream['schema'] in ('raw_vault','business_vault','gold'), (node['name'],parent)
            checked.append(node['name'])
    assert len(checked) == 9
    RESULT['gold_dependencies'] = checked
