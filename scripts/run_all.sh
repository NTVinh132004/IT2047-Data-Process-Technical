#!/usr/bin/env bash
# Yêu cầu mọi kỳ trong dải của conf rồi chờ các job theo tầng xử lý hết (FR-01, R-33). Tầng đã xong của một kỳ không
# bị xử lý lại; các tầng cần thứ tự thời gian (Raw Vault, Business Vault) đi lần lượt từng kỳ.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose exec -T airflow-scheduler python -m ingestion.control request --all
docker compose exec -T airflow-scheduler airflow dags trigger layer_ingest >/dev/null
scripts/wait_periods.sh
