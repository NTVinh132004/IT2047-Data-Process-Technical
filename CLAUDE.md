# mortgage-datavault

Đồ án cao học: Lakehouse + Data Vault 2.0 trên Spark cho dữ liệu khoản vay Freddie Mac vintage 2019.
Tài liệu chính nằm trong repo, đọc trước khi làm: `docs/PRD.md`, `docs/ke-hoach-trien-khai.md`, `docs/review.md`.

## Quyết định đã chốt (đừng đổi khi chưa qua PRD mục 8)

- Stack: PySpark (Bronze, cổng chất lượng, xuất PostgreSQL), dbt-spark + automate-dv (staging, Raw Vault, Business Vault, Gold), Airflow (LocalExecutor) điều phối, Delta Lake trên ổ đĩa cục bộ, Hive Metastore + Thrift Server. Không có MinIO, Metabase (R-25).
- Kỳ nạp = một quý báo cáo, nhưng `load_date` theo **tháng**: ngày 1 của tháng sau tháng báo cáo. Lý do: khóa Satellite (`hash_key`, `load_date`) sẽ trùng nếu cả quý dùng chung một `load_date` (review R-01). Không dùng lẫn `load_date` với `reporting_period`.
- Hash: sha2-256, trim, upper, null thành `^^`, nối bằng `||`. Không đổi sau khi đã nạp dữ liệu.
- Idempotent: Bronze và quarantine ghi đè lát của kỳ (`replaceWhere`); Satellite bỏ qua dòng (`hash_key`, `load_date`) đã có; chạy lại kỳ cũ cũng sinh 0 dòng.
- FR-14 (đợt sửa dữ liệu + bảng đối chứng ghi đè, AC-09) là bằng chứng chính cho việc chọn Data Vault, là Must.

## Quy tắc làm việc

- Mỗi giai đoạn kết thúc bằng cổng kiểm thử C0–C7 (Kế hoạch mục 6). Code của giai đoạn sau chỉ bắt đầu khi cổng trước đạt. Không nới tiêu chí để qua cổng mà không ghi vào lịch sử thay đổi của PRD.
- Đổi FR, AC hoặc kiến trúc: ghi vào `docs/review.md`, sửa PRD, Kế hoạch và test cổng trong cùng một pull request, tăng phiên bản PRD.
- Lệnh `make` chưa cài đặt phải thoát với mã lỗi, không giả vờ chạy được.
- Không commit dữ liệu (`data/` đã được ignore). Tài liệu viết bằng tiếng Việt.
- `ingestion/periods.py::load_date_for` để chủ repo tự cài đặt; đừng viết thay khi chưa được yêu cầu.

## Trạng thái (29/10/2026)

Cổng C0 đạt ngày 29/10/2026 (PRD 1.5, `tests/gates/results/c0-20261029-095352.json`). Đang ở giai đoạn 1: docker compose, Bronze, `load_control`, khung DAG Airflow; nghiệm thu ở C1.
- Phạm vi chốt theo R-25, không cắt thêm (quyết định 29/10/2026)

## Môi trường

- Bộ đầy đủ 2019 (Release 47, 8,2 GB): `/mnt/f/Thac si/Data processing technical/Final_project/Dataset/historical_data/unzip/historical_data_2019/`
- WSL 12 GB RAM (`.wslconfig`); Docker Engine cài trong Ubuntu, không dùng Docker Desktop
- `uv` ở `~/.local/bin`; Python 3.11 qua `uv run`; `make gate`/`make test` dùng `uv run pytest`
- Spike: `cd experiments/spike_c0 && docker compose up -d`, rồi `make gate N=0` (khoảng 2 phút)
- automate-dv trên dbt-spark cần lớp tương thích: shim sinh bằng `gen_shim.py`, `spark__hub`/`spark__sat` viết tay vì Spark không có `QUALIFY`. Dùng Spark 3.5.5, không dùng 3.5.7 (R-26)
