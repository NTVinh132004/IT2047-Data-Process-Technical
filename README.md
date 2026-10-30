# mortgage-datavault

Lakehouse + Data Vault 2.0 trên Apache Spark cho phân tích rủi ro tín dụng khoản vay thế chấp
(Freddie Mac Single-Family Loan-Level Dataset, vintage 2019).

Tài liệu: [PRD](docs/PRD.md) · [Kế hoạch triển khai](docs/ke-hoach-trien-khai.md) · [Review](docs/review.md) · [Từ điển dữ liệu](docs/tu-dien-du-lieu.md)

## Trạng thái

Cổng C0–C4 đạt (30/10/2026): toàn bộ 69 kiểm tra qua trên bản clone với lake và volume mới, gồm C4 10/10 và 30 unit test. Pipeline bộ mẫu từ `make run-all` qua đủ sáu tầng mất 1.056,6 giây (17 phút 36,6 giây), đạt mục tiêu tạm 45 phút. Đã có Gold, mart PostgreSQL và notebook 8 biểu đồ. Bằng chứng: `tests/gates/results/c4-20261030-150942.json`; snapshot code được định danh bằng `source_digest`. Kế tiếp: giai đoạn 5, chạy bộ đầy đủ và thực nghiệm (C5).

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
make smoke                  # kiểm nhanh luồng trên dữ liệu giả lập (khoảng 30 giây)
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

## Gold và phân tích (giai đoạn 4)

Sau `make run-all`, tầng `gold` dựng `fact_loan_month`, 5 dimension và 3 mart từ Raw/Business Vault; tầng `export` dùng JDBC đưa mart sang schema `serving` trong database PostgreSQL `analytics`. `make status` theo dõi đủ sáu tầng. Khi chỉ thêm tầng mới, các tầng đã SUCCESS được bỏ qua.

```bash
make notebook
```

Lệnh thực thi [notebook rủi ro tín dụng](notebooks/rui_ro_tin_dung.ipynb), đọc mart PostgreSQL và tạo biểu đồ cho đủ 5 câu hỏi. Bản chạy có kết quả nằm ở `data/reports/rui_ro_tin_dung.executed.ipynb` (không commit). Thư viện notebook được khóa trong `uv.lock`; không cần bật thêm Jupyter container. Có thể mở bản notebook bằng Jupyter/VS Code sau khi `uv sync`.

```bash
make gate N=4
make verify-clean
```

`make gate N=4` đối soát Gold/Delta/PostgreSQL, oracle TXT, lịch sử chiều khởi tạo, notebook và khả năng phục hồi khi công bố lỗi. AC-07 cần bằng chứng từ `make verify-clean`: lệnh clone repo vào thư mục tạm, chép snapshot thay đổi đang review, gắn nguồn TXT chỉ đọc, dùng lake/volume Docker mới và chạy toàn bộ `pytest tests` từ sạch. Stack hiện tại tạm dừng để tránh trùng cổng/thiếu RAM rồi tự bật lại; dữ liệu lake và volume của workspace được giữ nguyên. Log, JUnit và định danh snapshot ở `data/reports/clean-tests.log`, `clean-tests.xml`, `clean-run.json`; kết quả cổng được chép về `tests/gates/results/`.

Hạn chế phân tích: tên `OTHER` gộp nhiều tổ chức; SMM/CPR không chứng minh lý do tái cấp vốn. Kết cục hoãn trả là phân tích hồi cứu, `UNKNOWN` biểu thị thiếu quan sát cuối cửa sổ 12 tháng. Dư nợ là measure tại thời điểm, không cộng qua các tháng. Chi tiết thiết kế và căn cứ official: `docs/review.md` R-36.
