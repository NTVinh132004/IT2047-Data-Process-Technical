# mortgage-datavault

Lakehouse + Data Vault 2.0 trên Apache Spark cho phân tích rủi ro tín dụng khoản vay thế chấp
(Freddie Mac Single-Family Loan-Level Dataset, vintage 2019).

Tài liệu: [Báo cáo trên sample](docs/bao-cao-do-an.md) · [PRD](docs/PRD.md) · [Kế hoạch triển khai](docs/ke-hoach-trien-khai.md) · [Review](docs/review.md) · [Từ điển dữ liệu](docs/tu-dien-du-lieu.md)

## Trạng thái

**05/11/2026 (R-38, PRD 1.9):** phạm vi nghiệm thu cuối là bộ mẫu. Cổng C0–C4 đạt (30/10/2026, 69/69 kiểm tra trên clone sạch, R-36). Năm thực nghiệm C5 (TN1 quy mô, TN2 incremental, TN4 PIT, TN6 tách Satellite, TN7 kỹ thuật nạp) chạy trên bộ mẫu và tập con, mỗi cấu hình 3 lần đo, kết quả thô ở `experiments/results/`. Báo cáo: [docs/bao-cao-do-an.md](docs/bao-cao-do-an.md). Bộ đầy đủ là hướng phát triển ([docs/chay-historical.md](docs/chay-historical.md)).

## Yêu cầu máy

- Linux hoặc WSL2, RAM cấp cho Docker ít nhất 12 GB (WSL: `memory=12GB` trong `%UserProfile%\.wslconfig`)
- Docker Engine và Docker Compose v2, `make`
- [uv](https://docs.astral.sh/uv/) để chạy test (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Ổ đĩa trống khoảng 10 GB cho bộ mẫu và lake thực nghiệm (35 GB nếu chạy bộ đầy đủ, ngoài phạm vi nghiệm thu)

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

## Thực nghiệm (C5)

```bash
make down                 # stack sample và stack thực nghiệm không chạy cùng lúc (RAM 12 GB)
make experiments          # khoảng 3 giờ: tập con p25/p50, rồi TN1, TN4, TN7, TN6, TN2
make experiment-charts    # biểu đồ PNG trong experiments/results/
make gate N=5             # kiểm đủ lần đo, phép kiểm đúng, biểu đồ, digest code
```

Thực nghiệm chạy trên stack Compose riêng (`scripts/experiment.sh`: project `mortgage-datavault-exp`,
lake `data/lake-exp`, cổng Airflow 8082), không đụng lake sample dùng cho báo cáo. Mỗi file kết quả gắn
với digest code lúc đo (`experiments/results/manifest.json`); đổi code ở `experiments/`, `ingestion/`,
`dbt/`, `conf/`, `docker/` thì phải đo lại. Thiết kế: `docs/review.md` R-38.

## Cấu trúc

```
conf/           schema nguồn theo File Layout Release 47, cấu hình pipeline (FR-03)
dags/           DAG Airflow theo kỳ nạp
docker/         Dockerfile và cấu hình Spark, Hive Metastore, Airflow, PostgreSQL
ingestion/      PySpark: Bronze, load_control, đọc cấu hình
dbt/            staging, Raw Vault, Business Vault, Gold (từ giai đoạn 2)
experiments/    khám phá dữ liệu, spike C0, thực nghiệm C5 (run.py, spark_bench.py) và kết quả thô
tests/          unit test và test cổng C0–C7
```

## Gold và phân tích (giai đoạn 4)

Sau `make run-all`, tầng `gold` dựng `fact_loan_month`, 5 dimension và 3 mart từ Raw/Business Vault; tầng `export` dùng JDBC đưa mart sang schema `serving` trong database PostgreSQL `analytics`. `make status` theo dõi đủ sáu tầng. Khi chỉ thêm tầng mới, các tầng đã SUCCESS được bỏ qua.

```bash
make notebook
```

Mở notebook qua trình duyệt từ terminal Ubuntu/WSL:

```bash
make notebook-ui
```

JupyterLab phục vụ trên `http://localhost:8888`; mở URL có token được in trong terminal. Lệnh chạy ở foreground, dừng bằng `Ctrl+C`. Mở `data/reports/rui_ro_tin_dung.executed.ipynb` để xem biểu đồ đã sinh; có thể chạy lại các cell để đọc số liệu mới từ PostgreSQL. Airflow UI vẫn ở cổng 8080.

Lệnh thực thi [notebook rủi ro tín dụng](notebooks/rui_ro_tin_dung.ipynb), đọc mart PostgreSQL và tạo biểu đồ cho đủ 5 câu hỏi. Bản chạy có kết quả nằm ở `data/reports/rui_ro_tin_dung.executed.ipynb` (không commit). Thư viện notebook được khóa trong `uv.lock`; không cần bật thêm Jupyter container. Có thể mở bản notebook bằng Jupyter/VS Code sau khi `uv sync`.

```bash
make gate N=4
make verify-clean
```

`make gate N=4` đối soát Gold/Delta/PostgreSQL, oracle TXT, lịch sử chiều khởi tạo, notebook và khả năng phục hồi khi công bố lỗi. AC-07 cần bằng chứng từ `make verify-clean`: lệnh clone repo vào thư mục tạm, chép snapshot thay đổi đang review, gắn nguồn TXT chỉ đọc, dùng lake/volume Docker mới và chạy toàn bộ `pytest tests` từ sạch. Stack hiện tại tạm dừng để tránh trùng cổng/thiếu RAM rồi tự bật lại; dữ liệu lake và volume của workspace được giữ nguyên. Log, JUnit và định danh snapshot ở `data/reports/clean-tests.log`, `clean-tests.xml`, `clean-run.json`; kết quả cổng được chép về `tests/gates/results/`.

Hạn chế phân tích: tên `OTHER` gộp nhiều tổ chức; SMM/CPR không chứng minh lý do tái cấp vốn. Kết cục hoãn trả là phân tích hồi cứu, `UNKNOWN` biểu thị thiếu quan sát cuối cửa sổ 12 tháng. Dư nợ là measure tại thời điểm, không cộng qua các tháng. Chi tiết thiết kế và căn cứ official: `docs/review.md` R-36.

Hướng phát triển, chạy bộ đầy đủ với lake/volume riêng (không thuộc nghiệm thu, R-38): [Chạy historical](docs/chay-historical.md).

Bộ bàn giao: [Báo cáo kỹ thuật](docs/bao-cao-do-an.md) · [Slide và cách mở/tái sinh](docs/huong-dan-slide.md).
