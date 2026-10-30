#!/usr/bin/env bash
# Yêu cầu xử lý lại một kỳ qua mọi tầng (force, kể cả tầng đã xong) rồi chờ đến khi xong (FR-01, R-33).
# Dùng: scripts/run_period.sh 2020Q1 ['{"inject_test_failure": true, "max_attempts": 1}']
set -euo pipefail
period="${1:?Thiếu kỳ, ví dụ: scripts/run_period.sh 2020Q1}"
[[ "$period" =~ ^([0-9]{4}Q[1-4]|CORR[0-9]+)$ ]] || { echo "Kỳ không hợp lệ: $period"; exit 1; }
options="${2:-}"
[ -n "$options" ] || options='{}'
cd "$(dirname "$0")/.."
docker compose exec -T airflow-scheduler python -m ingestion.control request --period "$period" --force --options "$options"
# Huých tầng đầu để khỏi chờ lịch 5 phút; các tầng sau được tầng trên huých khi xong việc
docker compose exec -T airflow-scheduler airflow dags trigger layer_ingest >/dev/null
echo "Đã yêu cầu $period"
scripts/wait_periods.sh "$period"
