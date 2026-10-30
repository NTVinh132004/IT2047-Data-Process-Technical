#!/usr/bin/env bash
# Kích hoạt DAG lakehouse_pipeline cho một kỳ và chờ đến khi xong (FR-01).
# Luôn chạy, kể cả kỳ đã SUCCESS (để chạy lại, R-03). Thoát mã 1 nếu DAG run thất bại.
# Dùng: scripts/run_period.sh 2020Q1 ['{"inject_test_failure": true}']   (tham số 2: conf thêm cho DAG)
set -euo pipefail
period="${1:?Thiếu kỳ, ví dụ: scripts/run_period.sh 2020Q1}"
[[ "$period" =~ ^[0-9]{4}Q[1-4]$ ]] || { echo "Kỳ không hợp lệ: $period"; exit 1; }
cd "$(dirname "$0")/.."
af() { docker compose exec -T airflow-scheduler airflow "$@"; }

run_id="manual__${period}__$(date -u +%Y%m%dT%H%M%S)"
extra="${2:-}"
[ -n "$extra" ] || extra='{}'
conf=$(python3 -c 'import json, sys; d = json.loads(sys.argv[2]); d["period"] = sys.argv[1]; print(json.dumps(d))' "$period" "$extra")
af dags trigger lakehouse_pipeline --conf "$conf" --run-id "$run_id" >/dev/null
echo "Đã kích hoạt $run_id"
while true; do
  state=$(af dags list-runs lakehouse_pipeline --output json 2>/dev/null \
    | python3 -c "import json,sys; print(next((r['state'] for r in json.load(sys.stdin) if r['run_id']=='$run_id'), 'unknown'))")
  case "$state" in
    success) echo "$period: SUCCESS"; exit 0 ;;
    failed)  echo "$period: FAILED (xem log trên Airflow UI http://localhost:8080)"; exit 1 ;;
  esac
  sleep 5
done
