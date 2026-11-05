#!/usr/bin/env bash
# Stack thực nghiệm C5 (R-38): project Compose, lake và volume PostgreSQL riêng. Lake sample dùng cho số liệu
# báo cáo (data/lake, volume mortgage-datavault_pgdata) không bị đọc hay ghi. Không chạy đồng thời với stack sample.
# Dùng: EXP_SUBSET=p25|p50|p100 scripts/experiment.sh up | down | run-all | compose <lệnh docker compose>
set -euo pipefail
cd "$(dirname "$0")/.."
subset="${EXP_SUBSET:-p100}"
export COMPOSE_PROJECT_NAME=mortgage-datavault-exp
export LAKE_DATA_DIR="$PWD/data/lake-exp"
# p100 dùng thẳng nguồn sample; p25, p50 là tập con theo khoản vay (experiments/subset.py)
if [ "$subset" = "p100" ]; then
    export RAW_DATA_DIR="$PWD/data/raw"
else
    export RAW_DATA_DIR="$PWD/data/raw-exp/$subset"
fi
export POSTGRES_PORT=5434 AIRFLOW_PORT=8082 THRIFT_PORT=10002 SPARK_UI_PORT=4042
case "${1:-}" in
    up) exec make up NO_BUILD=1 ;;
    # -v chỉ xóa volume của project exp (COMPOSE_PROJECT_NAME ở trên), không đụng volume sample
    down) exec docker compose down -v --remove-orphans ;;
    run-all) exec make run-all ;;
    compose) shift; exec docker compose "$@" ;;
    *) echo "Lệnh hợp lệ: up, down, run-all, compose ..." >&2; exit 2 ;;
esac
