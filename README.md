# mortgage-datavault

Lakehouse + Data Vault 2.0 trên Apache Spark cho phân tích rủi ro tín dụng khoản vay thế chấp
(Freddie Mac Single-Family Loan-Level Dataset, vintage 2019).

Tài liệu: [PRD](docs/PRD.md) · [Kế hoạch triển khai](docs/ke-hoach-trien-khai.md) · [Review](docs/review.md) · [Từ điển dữ liệu](docs/tu-dien-du-lieu.md)

## Trạng thái

Cổng C0 đạt (29/10/2026). Đang làm giai đoạn 1: hạ tầng, Bronze và `load_control` (cổng C1).

## Yêu cầu máy

- Linux hoặc WSL2, RAM cấp cho Docker ít nhất 12 GB (WSL: `memory=12GB` trong `%UserProfile%\.wslconfig`)
- Docker Engine và Docker Compose v2, `make`
- [uv](https://docs.astral.sh/uv/) để chạy test (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Ổ đĩa trống khoảng 35 GB nếu chạy bộ đầy đủ

## Dữ liệu

Dữ liệu không nằm trong repo (điều khoản của Freddie Mac không cho phân phối lại). Tải trên trang Clarity của
Freddie Mac (cần đăng ký, miễn phí), giải nén theo layout Release 47 rồi đặt vào:

```
data/raw/sample_2019/sample_orig_2019.txt         # bộ mẫu, 50.000 khoản vay
data/raw/sample_2019/sample_perf_2019.txt
data/raw/historical_2019/orig_2019Q1.txt ... Q4    # bộ đầy đủ, 8,2 GB
data/raw/historical_2019/perf_2019Q1.txt ... Q4
```

Chọn bộ dữ liệu bằng `dataset.source` trong `conf/pipeline.yml` (`sample` hoặc `historical`).

## Chạy

```bash
cp .env.example .env        # đổi mật khẩu và AIRFLOW_JWT_SECRET
make up                     # build image, khởi động và chờ mọi service healthy
make run PERIOD=2019Q2      # nạp một kỳ (chạy cả khi kỳ đã SUCCESS)
make run-all                # nạp tuần tự mọi kỳ chưa SUCCESS
make down
```

| Giao diện | Địa chỉ |
| --- | --- |
| Airflow | http://localhost:8080 (tài khoản trong `.env`) |
| Spark UI của Thrift Server | http://localhost:4040 |
| Spark Thrift (JDBC, dbt) | `jdbc:hive2://localhost:10000` |
| PostgreSQL (`analytics`, `control.load_control`) | `localhost:5432` |

## Kiểm thử

```bash
make test        # unit test và mọi cổng đã qua
make gate N=1    # một cổng; lần đầu nạp cả 29 kỳ của bộ mẫu
```

Kết quả mỗi lần chạy cổng được lưu ở `tests/gates/results/`.

## Cấu trúc

```
conf/           schema nguồn theo File Layout Release 47, cấu hình pipeline (FR-03)
dags/           DAG Airflow theo kỳ nạp
docker/         Dockerfile và cấu hình Spark, Hive Metastore, Airflow, PostgreSQL
ingestion/      PySpark: Bronze, load_control, đọc cấu hình
dbt/            staging, Raw Vault, Business Vault, Gold (từ giai đoạn 2)
experiments/    khám phá dữ liệu, spike C0, thực nghiệm Spark
tests/          unit test và test cổng C0–C7
```
