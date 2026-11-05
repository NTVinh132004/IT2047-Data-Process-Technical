# Chạy bộ đầy đủ trong môi trường riêng

> **Hướng phát triển, không thuộc nghiệm thu (R-38, 05/11/2026).** Dữ liệu, output, container và volume historical đã xóa ngày 31/10/2026 theo yêu cầu chủ dự án (R-37); từ PRD 1.9 phạm vi cuối là bộ mẫu. Hạ tầng dưới đây giữ lại để chạy bộ đầy đủ về sau; các đường dẫn artifact historical nhắc tới không còn tồn tại.

Bộ mẫu giữ nguyên `conf/pipeline.yml`, `data/lake/` và volume
`mortgage-datavault_pgdata`. Bộ đầy đủ dùng `conf/environments/historical.yml`,
`data/lake-historical/` và volume `mortgage-datavault-historical_pgdata`.
Không xóa volume khi chuyển môi trường. Không chạy đồng thời hai stack Spark
trên WSL 12 GB; dừng stack sample trước khi bật historical.

| Thành phần | Sample | Historical |
| --- | --- | --- |
| Nguồn TXT chỉ đọc | `data/raw/sample_2019/` | `data/raw/historical_2019/` |
| Lake | `data/lake/warehouse/` | `data/lake-historical/warehouse/` |
| Airflow UI | http://localhost:8080 | http://localhost:8081 |
| PostgreSQL host port | 5432 | 5433 |
| Thrift host port | 10000 | 10001 |
| Spark UI | 4040 | 4041 |

Tên schema và bảng trong hai môi trường giữ nguyên; landing, Bronze, quality,
staging, Raw Vault, Business Vault và Gold historical đều nằm dưới lake mới.
PostgreSQL mới chứa riêng metastore, Airflow, control và serving. Các lệnh con
kế thừa project Compose qua `scripts/historical.sh`. Image dùng lại từ sample;
không cần build lại chỉ vì đổi nguồn và đường dẫn. Nếu chưa có image, chạy
`bash scripts/historical.sh up` để build.

```bash
make preflight-historical
# Dừng dịch vụ tính toán sample, giữ nguyên dữ liệu và PostgreSQL sample.
docker compose stop airflow-scheduler airflow-dag-processor airflow-apiserver spark-thrift hive-metastore
make up-historical
make run-historical PERIOD=2019Q1
make status-historical
```

Preflight quét đủ tám file, kiểm số trường và phạm vi tháng, lưu SHA-256,
số dòng và phân bố tháng vào `data/reports/historical/source-manifest.json`.
Đây là kiểm tra kỹ thuật nguồn, không thay thế cổng chất lượng hoặc C5.
Pilot đầu tiên dựng landing từ toàn bộ TXT nhưng các tầng sau chỉ nạp quý yêu cầu.
Batch ban đầu bằng một kỳ để đo tài nguyên; chưa tăng batch khi chưa đo.

Sau khi sáu tầng pilot SUCCESS, chạy `uv run python -m scripts.validate_historical_pilot`
để đối soát số dòng perf với TXT, số tháng/dư nợ AC-05 và số dòng export với Gold.
Chỉ sau khi pilot đạt đối soát và tài nguyên mới chạy `make run-all-historical`.
Lệnh chạy toàn bộ từ chối nếu thiếu báo cáo pilot hoặc manifest nguồn đã thay đổi.
Lệnh này bỏ qua tầng/kỳ đã SUCCESS. Không dùng `make run-all` mặc định vì lệnh
đó vẫn trỏ sample. `make run-historical` là chạy lại cưỡng bức một kỳ.
CORR1 và các thực nghiệm C5 thực hiện sau dải kỳ chính; pilot không phải nghiệm thu C5.

`make notebook-historical` đọc PostgreSQL cổng 5433, kiểm tra dataset publication,
lưu kết quả dưới `data/reports/historical/`. Notebook sample vẫn dùng cổng 5432.
Các quý chưa có COVID hiển thị chưa có quan sát, không sinh kết quả giả.
Không coi các số liệu C4 sample là số liệu bộ đầy đủ.

Quay lại sample: `make stop-historical`, sau đó `make up`. Không dùng `down -v`.

Cơ chế project và volume theo tài liệu Docker:
[project name](https://docs.docker.com/compose/how-tos/project-name/),
[volumes](https://docs.docker.com/reference/compose-file/volumes/).

## Pilot đã đo ngày 30/10/2026

Preflight 8 TXT đạt: 1.781.144 dòng orig, 69.630.113 dòng perf,
87 tháng 201901–202603. Manifest SHA-256 từng file lưu trong thư mục báo cáo historical.

Quý 2019Q1 chạy qua Airflow đủ sáu tầng SUCCESS: ingest 350,1 giây,
quality 52,8, Raw Vault 105,5, Business Vault 51,1, Gold 36,4, export 23,7.
Bronze có 157.583 dòng orig và 229.215 dòng perf; quality không quarantine/trùng.
Đối soát perf bằng tổng dòng TXT trong quý; AC-05 đủ 3 tháng, 0 tháng lệch.
PostgreSQL bằng số dòng Delta: delinquency 59.805, prepayment 3, cohort COVID 0.
Notebook historical thực thi thành công, 7 biểu đồ; chưa có tháng COVID nên
hiển thị chưa có quan sát. Đây là kết quả pilot, không phải kết quả toàn bộ/C5.

Lần đo RAM khi ingest quan sát khoảng 4,65 GiB/5 GiB ở scheduler;
đây là mẫu đo tức thời, không phải peak được đo liên tục.
Bằng chứng không commit: `data/reports/historical/source-manifest.json`,
`pilot.json`, `resources-latest.json`, `rui_ro_tin_dung.executed.ipynb`.

## Cấu hình sau OOM tại Raw Vault 2019Q2

`scripts/historical.sh` tự ghép `docker-compose.yml` với
`docker-compose.historical.yml`. Historical dùng dbt một luồng, Spark local[2],
heap 2 GiB/container 4 GiB, 64 shuffle partition và giảm lịch sử Spark UI.
Sample giữ thông số cũ. Không cần build image để áp dụng cấu hình runtime này.

Nếu một kỳ thử hết retry, sau khi xử lý nguyên nhân phải tạo request mới
**không force** cho đúng kỳ rồi trigger DAG tầng bị lỗi. Không chạy
`make run-historical PERIOD=...` trong trường hợp này vì target đó force cả sáu tầng.
Ví dụ phục hồi Raw Vault 2019Q2:

```bash
docker compose -p mortgage-datavault-historical exec -T airflow-scheduler python -m ingestion.control request --period 2019Q2 --options '{"max_attempts": 1}'
docker compose -p mortgage-datavault-historical exec -T airflow-scheduler airflow dags trigger layer_raw_vault
```

Không tăng retry để che lỗi OOM; xác nhận container không bị OOM và kỳ bị lỗi
thật sự SUCCESS trước khi công bố đã khắc phục.

Kiểm chứng phục hồi ngày 30/10/2026: Raw Vault 2019Q2 SUCCESS sau 283,4 giây,
dbt PASS=100/ERROR=0; 2019Q3 đã bắt đầu. Cgroup container mới chưa ghi OOM tại
checkpoint này. RAM tổng kể cả file cache đã chạm giới hạn và có reclaim,
vì vậy vẫn phải theo dõi các quý tiếp theo; chưa công bố full/C5 đạt.
Bằng chứng: `data/reports/historical/oom-recovery.json`.

## Đối soát Bronze và quality bộ đầy đủ

Khi ingest/quality đã hoàn tất, chạy `make audit-historical-bronze`.
Lệnh chỉ đọc TXT và Delta log historical, không khởi động Spark hay nạp lại tầng.
Đếm perf theo quý trực tiếp từ TXT; orig theo tháng perf đầu tiên của từng khoản vay,
tính độc lập từ nguồn. SHA-256 từng file phải khớp manifest preflight.
So từng kỳ với thống kê dòng của các file đang hoạt động trong snapshot Delta;
kiểm `Bronze = clean + quarantine + dedup`. Thiếu thống kê hoặc lệch số dòng
phải báo lỗi. Báo cáo có phiên bản snapshot Delta tại
`data/reports/historical/bronze-quality-audit.json`; không lưu khóa khoản vay.

Đây là kiểm AC-01 và bảo toàn số dòng quality. Chưa thay AC-02/AC-05/AC-06,
thực nghiệm ba lần hoặc toàn bộ cổng C5.

Lượt đối soát 30/10/2026 đã PASS trên bộ đầy đủ: số dòng từng lát orig/perf
khớp TXT, bảo toàn dòng quality, SHA-256 đủ 8 file khớp preflight.
Báo cáo snapshot chi tiết ở đường dẫn trên. Những kết quả này không chứng minh
các tầng Vault/Gold/export đã hoàn tất.
