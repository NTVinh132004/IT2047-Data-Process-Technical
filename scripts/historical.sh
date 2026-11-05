#!/usr/bin/env bash
# Tất cả lệnh Compose con thừa hưởng cùng project, bind mount và cổng.
set -euo pipefail
cd "$(dirname "$0")/.."
case "${1:-}" in
    up|down|status|run|run-all) ;;
    *) echo "Lệnh historical hợp lệ: up, down, status, run, run-all" >&2; exit 2 ;;
esac
export COMPOSE_FILE="$PWD/docker-compose.yml:$PWD/docker-compose.historical.yml"
export COMPOSE_PROJECT_NAME=mortgage-datavault-historical
export LAKE_DATA_DIR="$PWD/data/lake-historical"
export RAW_DATA_DIR="$PWD/data/raw"
export PIPELINE_CONFIG_FILE="$PWD/conf/environments/historical.yml"
export POSTGRES_PORT=5433 AIRFLOW_PORT=8081 THRIFT_PORT=10001 SPARK_UI_PORT=4041
if [ "${1:-}" = "run-all" ]; then
    python3 - <<'CHECK'
import hashlib, json
from pathlib import Path
root = Path.cwd()
folder = root / 'data/reports/historical'
manifest_path = folder / 'source-manifest.json'
try:
    manifest = json.loads(manifest_path.read_text())
    pilot = json.loads((folder / 'pilot.json').read_text())
    assert manifest['passed'] and pilot['passed']
    assert pilot['manifest_sha256'] == hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    source = root / 'data/raw/historical_2019'
    actual = {p.name for kind in ('orig', 'perf') for p in source.glob(f'{kind}_2019Q?.txt')}
    assert actual == {entry['name'] for entry in manifest['files']}
    for entry in manifest['files']:
        path = root / 'data/raw/historical_2019' / entry['name']
        assert path.stat().st_size == entry['bytes']
        assert path.stat().st_mtime_ns <= manifest_path.stat().st_mtime_ns
except (OSError, KeyError, AssertionError, ValueError) as exc:
    raise SystemExit('Chưa đủ điều kiện chạy toàn bộ: cần preflight và đối soát pilot hợp lệ.') from exc
CHECK
fi
exec make "$@"
