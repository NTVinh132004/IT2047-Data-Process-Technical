#!/usr/bin/env bash
# Nạp tuần tự mọi kỳ chưa SUCCESS trong load_control, theo thứ tự thời gian (FR-01). Dừng ở kỳ lỗi đầu tiên.
set -euo pipefail
cd "$(dirname "$0")/.."
# Bỏ dòng rỗng: khi đã nạp hết, danh sách rỗng không được thành một "kỳ" rỗng
mapfile -t periods < <(docker compose exec -T airflow-scheduler python -m ingestion.load_control pending | sed '/^$/d')
echo "Còn ${#periods[@]} kỳ chưa SUCCESS"
for period in "${periods[@]}"; do
  scripts/run_period.sh "$period"
done
