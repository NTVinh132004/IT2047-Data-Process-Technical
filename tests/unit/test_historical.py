"""Chặn việc profile historical ghi lên lake hoặc cấu hình sample."""
from pathlib import Path
import subprocess
import json
import os
import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_historical_config_separate():
    sample = yaml.safe_load((ROOT / 'conf/pipeline.yml').read_text())
    full = yaml.safe_load((ROOT / 'conf/environments/historical.yml').read_text())
    assert sample['dataset']['source'] == 'sample'
    assert full['dataset']['source'] == 'historical'
    assert full['orchestration']['max_periods_per_batch'] == 1
    assert full['periods'] == sample['periods']
    assert full['load_date'] == sample['load_date']


def test_compose_historical_isolation():
    env = dict(os.environ, COMPOSE_FILE=str(ROOT / 'docker-compose.yml') + ':' + str(ROOT / 'docker-compose.historical.yml'), COMPOSE_PROJECT_NAME='mortgage-datavault-historical',
               LAKE_DATA_DIR=str(ROOT / 'data/lake-historical'),
               PIPELINE_CONFIG_FILE=str(ROOT / 'conf/environments/historical.yml'),
               POSTGRES_PORT='5433', AIRFLOW_PORT='8081', THRIFT_PORT='10001', SPARK_UI_PORT='4041')
    config = json.loads(subprocess.check_output(['docker', 'compose', 'config', '--format', 'json'], cwd=ROOT, env=env))
    for name in ['airflow-scheduler', 'airflow-apiserver', 'airflow-dag-processor', 'hive-metastore', 'spark-thrift']:
        mounts = {v['target']: v for v in config['services'][name]['volumes']}
        assert mounts['/lake']['source'] == str(ROOT / 'data/lake-historical')
        if name.startswith('airflow'):
            assert mounts['/opt/project/conf/pipeline.yml']['read_only']
            assert mounts['/data/raw']['read_only']
    assert config['services']['airflow-scheduler']['environment']['DBT_THREADS'] == '1'
    thrift = config['services']['spark-thrift']
    assert '--master=local[2]' in thrift['command']
    assert '--driver-memory=2g' in thrift['command']
    assert '--conf=spark.sql.shuffle.partitions=64' in thrift['command']
    assert int(thrift['mem_limit']) == 4 * 1024 ** 3
    assert config['volumes']['pgdata']['name'] == 'mortgage-datavault-historical_pgdata'
    assert str(config['services']['postgres']['ports'][0]['published']) == '5433'
    assert str(config['services']['airflow-apiserver']['ports'][0]['published']) == '8081'


def test_notebook_historical_persists_connection(monkeypatch, tmp_path):
    from scripts import run_notebook
    class Client:
        def __init__(self, *args, **kwargs):
            pass
        def execute(self):
            pass
    monkeypatch.setattr(run_notebook, 'NotebookClient', Client)
    book = run_notebook.run(output=tmp_path / 'historical.ipynb', dataset='historical')
    code = '\n'.join(c.source for c in book.cells if c.cell_type == 'code')
    assert 'NOTEBOOK_DATASET = "historical"' in code
    assert 'NOTEBOOK_PG_PORT = "5433"' in code
    assert 'control.gold_publication' in code
    assert 'if c.empty:' in code


def test_preflight_rejects_bad_fields_and_month(monkeypatch, tmp_path):
    import pytest
    from scripts import preflight_historical
    monkeypatch.setattr(preflight_historical, 'ROOT', tmp_path)
    raw = tmp_path / 'data/raw/historical_2019'
    raw.mkdir(parents=True)
    for quarter in range(1, 5):
        (raw / f'orig_2019Q{quarter}.txt').write_text('|'.join(['x'] * 31) + '\n')
        row = ['x', '201902'] + [''] * 33
        (raw / f'perf_2019Q{quarter}.txt').write_text('|'.join(row) + '\n')
    preflight_historical.main()
    manifest = tmp_path / 'data/reports/historical/source-manifest.json'
    assert json.loads(manifest.read_text())['passed']
    (raw / 'perf_2019Q1.txt').write_text('x|202613|bad\n')
    with pytest.raises(SystemExit):
        preflight_historical.main()
    assert not json.loads(manifest.read_text())['passed']


def test_historical_full_run_requires_pilot(tmp_path):
    # Root tạm chưa có pilot: phải dừng trước khi gọi Make/Docker.
    script = tmp_path / 'scripts/historical.sh'
    script.parent.mkdir()
    script.write_text((ROOT / 'scripts/historical.sh').read_text())
    result = subprocess.run(['bash', str(script), 'run-all'], capture_output=True, text=True)
    assert result.returncode != 0
    assert 'Chưa đủ điều kiện' in result.stderr
