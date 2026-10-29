# Lệnh chưa cài đặt sẽ thoát với mã lỗi, để không ai nhầm là đã chạy được.
.PHONY: help up down run run-all gate test

help:
	@echo "make up | down | run PERIOD=2020Q1 | run-all | gate N=0 | test"

up:
	docker compose up -d

down:
	docker compose down

run:
	@test -n "$(PERIOD)" || { echo "Thiếu PERIOD, ví dụ: make run PERIOD=2020Q1"; exit 1; }
	@echo "Chưa cài đặt (giai đoạn 1): kích hoạt DAG lakehouse_pipeline cho kỳ $(PERIOD)"; exit 1

run-all:
	@echo "Chưa cài đặt (giai đoạn 1): nạp tuần tự các kỳ chưa SUCCESS"; exit 1

gate:
	@test -n "$(N)" || { echo "Thiếu N, ví dụ: make gate N=0"; exit 1; }
	uv run pytest tests/gates/c$(N) -v

test:
	uv run pytest tests
