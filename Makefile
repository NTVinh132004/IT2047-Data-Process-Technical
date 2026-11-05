# Lệnh chưa cài đặt sẽ thoát với mã lỗi, để không ai nhầm là đã chạy được.
.PHONY: help up down landing run run-all correction status smoke gate test notebook notebook-ui verify-clean

help:
	@echo "make up | down | landing | run PERIOD=2020Q1 | run-all | correction | status | smoke | gate N=0 | test | notebook | notebook-ui | verify-clean | experiments | experiment-charts | preflight-historical | up-historical | run-historical PERIOD=2019Q1 | run-all-historical | status-historical | notebook-historical"

up:
	@test -f .env || { echo "Thiếu .env: cp .env.example .env rồi đổi mật khẩu"; exit 1; }
	mkdir -p "$(or $(LAKE_DATA_DIR),data/lake)"
	@if [ "$(NO_BUILD)" != "1" ]; then docker compose build --provenance=false; fi
	docker compose up -d --wait --no-build
	@# Package dbt (automate_dv) cài vào dbt/dbt_packages, không nằm trong git
	test -d dbt/dbt_packages/automate_dv || docker compose exec -T airflow-scheduler bash -c "cd /opt/project/dbt && /opt/dbt-venv/bin/dbt deps"
	docker compose exec -T postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$$POSTGRES_USER" -d analytics' < docker/postgres/migrations/004_gold.sql
	@# Pool: một job Spark (ingest, quality) và một lệnh dbt chạy cùng lúc (R-33)
	docker compose exec -T airflow-scheduler airflow pools set spark_local 1 "Job Spark local trong container scheduler" >/dev/null
	docker compose exec -T airflow-scheduler airflow pools set dbt 1 "Lệnh dbt qua Thrift Server" >/dev/null

down:
	docker compose down

# Dựng lại landing kể cả khi nguồn không đổi (bình thường DAG tự dựng khi nguồn hoặc conf/schema đổi)
landing:
	docker compose exec -T airflow-scheduler python -m ingestion.landing --force

run:
	@test -n "$(PERIOD)" || { echo "Thiếu PERIOD, ví dụ: make run PERIOD=2020Q1"; exit 1; }
	scripts/run_period.sh $(PERIOD)

run-all:
	scripts/run_all.sh

# Đợt sửa dữ liệu giả lập FR-14 (conf/pipeline.yml mục corrections), nạp sau kỳ cuối
correction:
	scripts/run_period.sh CORR1

# Trạng thái từng tầng của các kỳ đã yêu cầu
status:
	docker compose exec -T airflow-scheduler python -m ingestion.control status

# Kiểm nhanh landing → Bronze → cổng chất lượng trên fixture giả lập (khoảng 30 giây), không đụng dữ liệu thật
smoke:
	docker compose exec -T airflow-scheduler python -m ingestion.smoke

gate:
	@test -n "$(N)" || { echo "Thiếu N, ví dụ: make gate N=0"; exit 1; }
	uv run pytest tests/gates/c$(N) -v

test:
	uv run pytest tests

notebook:
	uv run python -m scripts.run_notebook

notebook-ui:
	mkdir -p data/jupyter/runtime data/jupyter/config data/jupyter/share
	JUPYTER_RUNTIME_DIR="$(CURDIR)/data/jupyter/runtime" JUPYTER_CONFIG_DIR="$(CURDIR)/data/jupyter/config" JUPYTER_DATA_DIR="$(CURDIR)/data/jupyter/share" uv run jupyter lab --no-browser --ip=127.0.0.1 --port=8888 --ServerApp.port_retries=0 --ServerApp.root_dir="$(CURDIR)" --ServerApp.default_url=/lab/tree/data/reports/rui_ro_tin_dung.executed.ipynb

verify-clean:
	uv run python -m scripts.verify_clean

# Môi trường đầy đủ riêng biệt; không thay cấu hình sample.
.PHONY: up-historical run-historical run-all-historical status-historical stop-historical preflight-historical
up-historical:
	bash scripts/historical.sh up NO_BUILD=1
run-historical:
	bash scripts/historical.sh run PERIOD=$(PERIOD)
run-all-historical:
	bash scripts/historical.sh run-all
status-historical:
	bash scripts/historical.sh status
stop-historical:
	bash scripts/historical.sh down
preflight-historical:
	uv run python -m scripts.preflight_historical

.PHONY: notebook-historical
notebook-historical:
	uv run python -m scripts.run_notebook --dataset historical

.PHONY: audit-historical-bronze
audit-historical-bronze:
	uv run python -m scripts.audit_historical_bronze

.PHONY: report-sample
report-sample:
	uv run python -m scripts.collect_sample_report
	uv run python -m scripts.build_sample_slides

# Thực nghiệm C5 trên bộ mẫu (R-38): stack riêng mortgage-datavault-exp, lake data/lake-exp; khoảng 4–5 giờ.
# Dừng stack sample trước (RAM WSL 12 GB). Kết quả thô: experiments/results/*.csv
.PHONY: experiments experiment-charts
experiments:
	@test -z "$$(docker compose ps -q)" || { echo "Stack sample đang chạy: make down trước"; exit 1; }
	uv run python -m experiments.subset
	uv run python -m experiments.run all
	scripts/experiment.sh down
experiment-charts:
	uv run python -m experiments.charts
