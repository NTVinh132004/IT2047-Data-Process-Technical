# Lệnh chưa cài đặt sẽ thoát với mã lỗi, để không ai nhầm là đã chạy được.
.PHONY: help up down landing run run-all correction status smoke gate test

help:
	@echo "make up | down | landing | run PERIOD=2020Q1 | run-all | correction | status | smoke | gate N=0 | test"

up:
	@test -f .env || { echo "Thiếu .env: cp .env.example .env rồi đổi mật khẩu"; exit 1; }
	mkdir -p data/lake
	docker compose up -d --build --wait
	@# Package dbt (automate_dv) cài vào dbt/dbt_packages, không nằm trong git
	test -d dbt/dbt_packages/automate_dv || docker compose exec -T airflow-scheduler bash -c "cd /opt/project/dbt && /opt/dbt-venv/bin/dbt deps"
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
