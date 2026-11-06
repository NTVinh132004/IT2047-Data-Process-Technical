# mortgage-datavault

Đồ án cao học: Lakehouse + Data Vault 2.0 trên Spark cho dữ liệu khoản vay Freddie Mac vintage 2019.
Tài liệu chính nằm trong repo, đọc trước khi làm: `docs/PRD.md`, `docs/ke-hoach-trien-khai.md`, `docs/review.md`.

## Quyết định đã chốt (đừng đổi khi chưa qua PRD mục 8)

- Stack: PySpark (Bronze, cổng chất lượng, xuất PostgreSQL), dbt-spark + automate-dv (staging, Raw Vault, Business Vault, Gold), Airflow (LocalExecutor) điều phối, Delta Lake trên ổ đĩa cục bộ, Hive Metastore + Thrift Server. Không có MinIO, Metabase (R-25).
- Kỳ nạp = một quý báo cáo, nhưng `load_date` theo **tháng**: ngày 1 của tháng sau tháng báo cáo. Lý do: khóa Satellite (`hash_key`, `load_date`) sẽ trùng nếu cả quý dùng chung một `load_date` (review R-01). Không dùng lẫn `load_date` với `reporting_period`.
- Hash: sha2-256, trim, upper, null thành `^^`, nối bằng `||`. Không đổi sau khi đã nạp dữ liệu.
- Idempotent: Bronze và quarantine ghi đè lát của kỳ (`replaceWhere`); Satellite bỏ qua dòng (`hash_key`, `load_date`) đã có; chạy lại kỳ cũ cũng sinh 0 dòng.
- FR-14 (đợt sửa dữ liệu + bảng đối chứng ghi đè, AC-09) là bằng chứng chính cho việc chọn Data Vault, là Must.

## Nguyên tắc phát triển (bắt buộc)

@docs/principles.md

## Quy tắc làm việc

- Mỗi giai đoạn kết thúc bằng cổng kiểm thử C0–C7 (Kế hoạch mục 6). Code của giai đoạn sau chỉ bắt đầu khi cổng trước đạt. Không nới tiêu chí để qua cổng mà không ghi vào lịch sử thay đổi của PRD.
- Đổi FR, AC hoặc kiến trúc: ghi vào `docs/review.md`, sửa PRD, Kế hoạch và test cổng trong cùng một pull request, tăng phiên bản PRD.
- Lệnh `make` chưa cài đặt phải thoát với mã lỗi, không giả vờ chạy được.
- Không commit dữ liệu (`data/` đã được ignore). Tài liệu viết bằng tiếng Việt, trừ `docs/principles.md` (tiếng Anh theo yêu cầu chủ repo).

## Trạng thái (06/11/2026)

Cổng C0–C6 đạt. R-38 (PRD 1.9): phạm vi cuối là bộ mẫu. R-39: heap Thrift 2,5 GiB và restart policy. C5 đạt 7/7; C6 (`make verify-clean`) 89/89 trên clone của code freeze `b5e21bc`. Sau code freeze chỉ sửa lỗi và tài liệu.

**Còn lại: C7 (bàn giao, Kế hoạch mục 13).** Đã làm (06/11/2026): viết lại lịch sử nhánh `giai-doan-3` xóa mã khoản vay thật (R-40, bảng đối chiếu hash cũ → mới; bundle sao lưu ở `data/backup/`, xóa khi không cần), xóa `scripts/build_sample_docs.py`. Chủ repo còn làm: chuyển ổ ảo Ubuntu (`ext4.vhdx`, đang ở ổ C) sang ổ F và bật sparse; video demo, thông tin học viên, mẫu bìa.
- Lệnh dài (`make experiments`, `make verify-clean`): tắt chế độ ngủ Windows (`powercfg /change standby-timeout-ac 0`) và chạy tách phiên (`setsid nohup ... &`); tác vụ nền của Claude Code bị dừng khi RAM sát mức. Số liệu thực nghiệm: `data/reports/experiments/exp_numbers.py`
- Tầng phải dựng lại vì đổi model: `python -m ingestion.control invalidate --layers raw_vault,business_vault --reason ...` rồi `make run-all`; không chạy lại tầng dưới
- Phạm vi chốt theo R-25 và R-38, không cắt thêm; bộ đầy đủ là hướng phát triển (hạ tầng historical giữ trong repo, không nghiệm thu)

## Môi trường

- Bộ đầy đủ 2019 (Release 47, 8,2 GB): `/mnt/f/Thac si/Data processing technical/Final_project/Dataset/historical_data/unzip/historical_data_2019/`
- WSL 12 GB RAM (`.wslconfig`); Docker Engine cài trong Ubuntu, không dùng Docker Desktop
- `uv` ở `~/.local/bin`; Python 3.11 qua `uv run`; `make gate`/`make test` dùng `uv run pytest`
- Stack chính: `make up`; nạp: `make run PERIOD=...`, `make run-all`; Airflow UI http://localhost:8080
- `make gate N=0` tự bật và tắt stack spike (khoảng 3 phút); `make gate N=1` khoảng 2 phút khi đã nạp đủ 29 kỳ
- Pipeline: TXT → landing → Bronze → cổng chất lượng (`quality.*_clean`/`_quarantine`) → dbt staging (bảng) → Raw Vault (R-27 đến R-30)
- `make smoke`: landing → Bronze → cổng chất lượng trên fixture giả lập (khoảng 30 giây). `make gate N=2` khoảng 15 phút khi đã nạp đủ 29 kỳ
- dbt chạy trong container scheduler: `/opt/dbt-venv/bin/dbt` (thư mục `/opt/project/dbt`). Model base_* sinh từ conf: `uv run python -m scripts.gen_dbt_staging`
- Model incremental tham chiếu nguồn nhiều lần thì nguồn phải là bảng, không phải view (Spark chép cây biểu thức của view, R-30)
- automate-dv trên dbt-spark cần lớp tương thích: shim sinh bằng `scripts/gen_automate_dv_shim.py`, `spark__hub`/`spark__link`/`spark__sat` viết tay vì Spark không có `QUALIFY`. Dùng Spark 3.5.5, không dùng 3.5.7 (R-26)
- Thực nghiệm C5: `make experiments` (stack `mortgage-datavault-exp` qua `scripts/experiment.sh`, lake `data/lake-exp`, cổng 8082/5434/10002; khoảng 3–4 giờ; dừng stack sample trước). Kết quả thô `experiments/results/*.csv` gắn digest code (`manifest.json`); vẽ bằng `make experiment-charts`; kiểm bằng `make gate N=5`. Đổi code trong `experiments/`, `ingestion/`, `dbt/`, `conf/`, `docker/` là phải đo lại
