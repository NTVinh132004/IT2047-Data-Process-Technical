# Lệnh chưa cài đặt sẽ thoát với mã lỗi, để không ai nhầm là đã chạy được.
.PHONY: help up down landing run run-all gate test

help:
	@echo "make up | down | landing | run PERIOD=2020Q1 | run-all | gate N=0 | test"

up:
	@test -f .env || { echo "Thiếu .env: cp .env.example .env rồi đổi mật khẩu"; exit 1; }
	mkdir -p data/lake
	docker compose up -d --build --wait

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

gate:
	@test -n "$(N)" || { echo "Thiếu N, ví dụ: make gate N=0"; exit 1; }
	uv run pytest tests/gates/c$(N) -v

test:
	uv run pytest tests
