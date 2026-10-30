#!/usr/bin/env bash
# Chờ đến khi mọi tầng của các kỳ đã yêu cầu đều SUCCESS (thoát 0) hoặc có tầng đã thử hết số lần (thoát 1).
# Dùng: scripts/wait_periods.sh [kỳ]   (không có kỳ: mọi kỳ đã yêu cầu)
set -euo pipefail
cd "$(dirname "$0")/.."
args=()
[ -n "${1:-}" ] && args=(--period "$1")
last=""
while true; do
  report=$(docker compose exec -T airflow-scheduler python -m ingestion.control status "${args[@]}" \
    | python3 scripts/status_summary.py)
  state=${report%%|*}; text=${report#*|}
  [ "$text" != "$last" ] && echo "$(date +%H:%M:%S) $text" && last=$text
  case "$state" in
    DONE) exit 0 ;;
    GAVE_UP*) echo "Dừng: ${state#GAVE_UP } đã thử hết số lần (xem control.layer_run và Airflow UI)"; exit 1 ;;
  esac
  sleep 10
done
