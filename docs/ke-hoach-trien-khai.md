# Kế hoạch triển khai: Lakehouse + Data Vault 2.0 trên Spark (Freddie Mac)

Oct 3, 2026 · @Vĩnh

**Quyết định:** chốt có điều kiện đề tài *"Xây dựng Data Lakehouse kết hợp Data Vault 2.0 trên Apache Spark cho phân tích rủi ro tín dụng khoản vay thế chấp"* với dữ liệu Freddie Mac vintage 2019, triển khai trong 8 tuần; mốc MVP end-to-end trên bộ mẫu vào cuối tuần 5.

**Giả định của kế hoạch:** một người, 10–15 giờ/tuần (ban đầu giả định nhóm 3–4 người; điều chỉnh ở `Review.md` R-25), môn Big Data hoặc Kỹ thuật dữ liệu, máy chính RAM 16 GB. Mục 12 nêu cách điều chỉnh nếu giả định sai. Kế hoạch đã qua 8 phản biện ở mục 11; 4 phản biện làm thay đổi thiết kế (P1, P2, P3, P5). Mỗi giai đoạn kết thúc bằng một cổng kiểm thử; chỉ đi tiếp khi cổng đạt (mục 6). Vòng review ngày 27/10/2026 sửa thêm các điểm lệch với PRD, xem `Review.md`.

## 1. Bài toán và mục tiêu

Một tổ chức tài chính cần nền tảng dữ liệu theo dõi rủi ro tín dụng của danh mục khoản vay thế chấp, truy vết được trạng thái từng khoản vay tại bất kỳ tháng nào.

**Vì sao cần cả ba công nghệ:**

| Yêu cầu | Công nghệ đáp ứng |
| --- | --- |
| Lưu toàn bộ lịch sử, truy vết nguồn gốc, chịu được dữ liệu nguồn bị sửa và đổi schema | Data Vault 2.0 |
| Tách rõ dữ liệu thô, dữ liệu tích hợp và dữ liệu phân tích | Medallion (Bronze, Silver, Gold) |
| Xử lý hàng chục triệu dòng lịch sử hằng tháng, nạp tăng dần | Apache Spark + Delta Lake |

**Mục tiêu đo được:**

- Pipeline nạp tăng dần theo kỳ, chạy từ một lệnh, trên bộ mẫu và bộ đầy đủ vintage 2019
- Raw Vault 3 Hub, 2 Link, 5 Satellite; Business Vault 2 Satellite tính toán và 1 PIT table
- Gold gồm star schema (1 fact, 5 dim) và 3 mart phân tích rủi ro
- Ít nhất 4 thực nghiệm Spark có số liệu và giải thích
- Báo cáo chất lượng dữ liệu: số dòng lỗi, mồ côi, trùng ở từng bước

**Câu hỏi nghiệp vụ:**

1. Tỷ lệ quá hạn 30/60/90+ ngày thay đổi thế nào theo tháng, đặc biệt giai đoạn COVID 2020–2021?
2. Điểm tín dụng, LTV, DTI ban đầu ảnh hưởng thế nào đến khả năng quá hạn?
3. Bang nào, bên bán nào có danh mục rủi ro cao hơn?
4. Bao nhiêu khoản vay được hỗ trợ hoãn trả nợ và sau đó hồi phục hay vỡ nợ?
5. Tỷ lệ trả trước hạn (do tái cấp vốn) theo thời gian?

## 2. Dữ liệu và phạm vi

Dùng Freddie Mac Single-Family Loan-Level Dataset, vintage 2019: bộ mẫu để phát triển, bộ đầy đủ để chạy thật và làm thực nghiệm.

| File | Dung lượng | Hạt dữ liệu | Vai trò |
| --- | --- | --- | --- |
| `sample_orig_2019` | \~6,2 MB (đã tải) | 1 dòng / khoản vay | Hub, Link, Satellite khởi tạo |
| `sample_perf_2019` | \~216 MB (đã tải) | 1 dòng / khoản vay / tháng | Satellite lịch sử |
| `orig_2019Qn`, `perf_2019Qn` (4 quý) | 8,2 GB txt: orig 1.781.144 khoản vay (246 MB), perf 69.630.113 dòng (7,98 GB) | Như trên, theo quý khởi tạo | Chạy thật, thực nghiệm Spark |
| File Layout / User Guide | — | — | Tên và kiểu cột (file không có tiêu đề, phân tách bằng `\|`) |

**Đặc điểm cần lưu ý:** dữ liệu thật, không đảm bảo đầy đủ hay không lỗi; một số tên cột đổi từ Release 47 (tháng 7/2026); miễn phí cho học thuật nhưng không được phân phối lại, nên không đưa dữ liệu lên GitHub.

**Phạm vi MVP (bắt buộc hoàn thành):**

- Bronze: nạp file thô, khai báo schema, chuẩn hóa tên cột theo Release 47
- Raw Vault: 3 Hub, 2 Link, 5 Satellite, nạp tăng dần theo kỳ báo cáo
- Business Vault: 2 Satellite tính toán, 1 PIT table theo tháng
- Gold: star schema (1 fact, 5 dim) và 3 mart phân tích rủi ro
- Notebook trả lời 5 câu hỏi nghiệp vụ (dashboard Metabase đã cắt, R-25)
- 4 thực nghiệm Spark bắt buộc (1, 2, 4, 6) chạy ở tuần 6, sau mốc MVP

**Mở rộng (chỉ làm nếu MVP xong trước tuần 6):**

- Thêm vintage 2007 để so sánh khủng hoảng 2008 với COVID
- Demo mô hình dự báo quá hạn 90+ ngày
- Kiểm tra chất lượng tự động bằng Great Expectations

**Ngoài phạm vi:** tích hợp FDIC, streaming, triển khai cloud.

## 3. Kiến trúc tổng thể

Data Vault nằm ở lớp Silver của Medallion: Bronze giữ dữ liệu thô, Silver tích hợp và lưu lịch sử, Gold trình bày cho phân tích.

&#91;embedded content: kiến trúc Medallion + Data Vault 2.0 · 5 lớp\]

Gold có thể xóa và dựng lại bất cứ lúc nào từ Silver; ngược lại, Raw Vault chỉ được thêm mới, không bao giờ sửa hay xóa.

**Mặt phẳng điều khiển** quyết định nạp kỳ nào và ghi lại kết quả: `DAG Airflow` đọc `load_control` để lấy kỳ tiếp theo, schema và luật kiểm tra nằm trong cấu hình, dòng lỗi bị chặn ở cổng chất lượng và đưa vào quarantine. Chạy lại cùng một kỳ cho kết quả không đổi: Bronze và quarantine ghi đè lát của kỳ, Raw Vault bỏ qua dòng đã có, Business Vault và Gold dựng lại từ Raw Vault. Thứ tự task trong DAG: nạp Bronze (PySpark), cổng chất lượng (PySpark), dbt build từng tầng kèm dbt test, xuất mart sang PostgreSQL.

**Cố ý không dùng:** không tách Business Vault thành một lớp lưu trữ riêng; Raw Vault và Business Vault cùng nằm trong Silver. Staging không lưu lịch sử: view ép kiểu, cộng bảng stage ghi đè mỗi lần chạy (R-30). Kiến trúc này được chốt tạm thời và sẽ điều chỉnh nếu gặp vấn đề khi triển khai.

## 4. Mô hình Data Vault

Mô hình xoay quanh `hub_loan`; các cột perf được tách thành nhiều Satellite theo tốc độ thay đổi để `hash_diff` có ý nghĩa.

&#91;embedded content: mô hình Data Vault · 3 Hub, 2 Link, 5 Satellite (esat đã cắt), 1 PIT\]

| Thành phần | Khóa / nguồn | Ghi chú |
| --- | --- | --- |
| `hub_loan` | Mã khoản vay (Loan Sequence Number / Loan Identifier) | Khóa giữ nguyên giữa các lần phát hành |
| `hub_seller`, `hub_servicer` | Tên bên bán (orig), tên bên quản lý (perf, từ Release 47) | Tên dưới ngưỡng 1% UPB bị gộp thành `OTHER` (R-22) |
| `link_loan_seller`, `link_loan_servicer` | Cặp khóa từ orig (seller) và từ perf (servicer) | Chỉ thêm mới |
| `sat_loan_origination`, `sat_loan_property` | orig: điều kiện khoản vay, tài sản thế chấp | Gần như không đổi; đổi khi có đợt sửa dữ liệu (FR-14) |
| `sat_loan_balance` | perf: dư nợ, lãi suất, tuổi khoản vay | Đổi hằng tháng |
| `sat_loan_delinquency` | perf: tình trạng quá hạn, hoãn trả nợ, sửa đổi khoản vay | Chỉ đổi khi có sự kiện; nơi `hash_diff` thể hiện giá trị |
| `sat_loan_termination` | perf: mã và ngày kết thúc, khoản thu hồi | Thường chỉ một phiên bản |
| `esat_loan_servicer` | Theo dõi đổi bên quản lý | Đã xác minh: 37,5% khoản vay bộ mẫu đổi servicer (R-21); đã cắt (R-25), ghi vào hướng phát triển |
| Cột kỹ thuật mọi bảng | `hash_key`, `load_date`, `record_source`; Satellite thêm `hash_diff` | Pipeline tự sinh |
| Hai trục thời gian | `load_date` (khi nạp) và `reporting_period` (kỳ nghiệp vụ) | Không dùng lẫn hai cột này |

**Khóa Satellite và `load_date`:** Satellite có khóa (`hash_key`, `load_date`). DAG chạy theo quý, nhưng mỗi tháng báo cáo trong quý mang một `load_date` riêng (ngày 1 của tháng sau). Nếu cả quý dùng chung một `load_date`, ba dòng perf của một khoản vay sẽ trùng khóa và Satellite chỉ giữ được một tháng (chi tiết ở PRD mục 6).

Bảng mã (tình trạng quá hạn, lý do kết thúc, bang) là bảng tham chiếu, không làm thành Hub.

## 5. Công nghệ và môi trường

Toàn bộ chạy bằng Docker Compose trên máy cá nhân, không dùng cloud trả phí; PySpark nạp Bronze và chạy cổng chất lượng, dbt (dbt-spark, automate-dv) mô hình hóa Raw Vault, Business Vault và Gold, Airflow điều phối toàn luồng.

| Thành phần | Công nghệ | Ghi chú |
| --- | --- | --- |
| Xử lý | PySpark (Spark 3.5.5, Delta 3.3.2) | Hai Spark local mode: Thrift Server cho dbt và job PySpark trong Airflow, chung Hive Metastore (R-27). Không dùng 3.5.7: lỗi `CREATE OR REPLACE` với Delta 3.3.2 (R-26) |
| Lưu trữ | Ổ đĩa cục bộ (volume Docker) | Đường dẫn trong `conf/`; chuyển sang S3 hoặc MinIO qua `s3a://` chỉ đổi cấu hình (R-25) |
| Định dạng bảng | Delta Lake | `MERGE` cho nạp tăng dần, time travel để truy vết |
| Hash key | `sha2(…, 256)` của Spark | Chuẩn hóa: trim, upper, null thay bằng `^^`, nối bằng `\|\|` trước khi hash; chốt một lần, không đổi sau khi đã nạp |
| Môi trường làm việc | Jupyter + PySpark | Khám phá dữ liệu, thực nghiệm |
| Phục vụ | PostgreSQL (database `analytics`) | Nhận mart từ Gold qua JDBC; tách khỏi database metadata của Hive |
| Dashboard | Notebook (Metabase đã cắt, R-25) | Đọc mart trong PostgreSQL |
| Quản lý mã nguồn | GitHub | Không đưa dữ liệu lên repo |
| Mô hình hóa | dbt-core 1.12.5 + dbt-spark 1.11.0, automate-dv 0.11.5 | Staging, Raw Vault, Business Vault, Gold; dbt test, dbt docs. Cần lớp tương thích dbt-spark (R-26) |
| Điều phối | Apache Airflow 3.3.2 (LocalExecutor) | DAG tuyến tính theo kỳ nạp, retry, theo dõi trạng thái; task Spark chạy trong container scheduler (R-27) |
| Catalog | Hive Metastore + Spark Thrift Server | dbt kết nối Spark qua Thrift; metadata lưu trên PostgreSQL |

**Yêu cầu máy chạy chính:** RAM 16 GB; ổ cứng trống ít nhất 3–4 lần dung lượng dữ liệu thô của bộ đầy đủ.

**Cấu trúc thư mục:**

```
mortgage-datavault/
├── docker-compose.yml   # Spark, PostgreSQL, Hive Metastore, Thrift Server, Airflow, Jupyter
├── Makefile             # make run PERIOD=..., make run-all, make gate N=..., make test
├── conf/                # schema theo File Layout, luật kiểm tra, cấu hình phiên bản
├── dags/
│   └── lakehouse_pipeline.py      # DAG Airflow theo kỳ nạp
├── ingestion/           # PySpark: nạp Bronze, cổng chất lượng, xuất PostgreSQL
├── dbt/
│   ├── models/staging/            # hash key, hash_diff (automate-dv stage)
│   ├── models/raw_vault/          # hub_*, link_*, sat_*
│   ├── models/business_vault/     # bsat_*, pit_*
│   ├── models/gold/               # dim_*, fact_*, mart_*
│   └── tests/
├── tests/               # unit test PySpark, test idempotent
│   ├── gates/                     # test của cổng C0–C7; results/ lưu kết quả mỗi lần chạy cổng
│   └── fixtures/                  # giá trị kỳ vọng tính tay (20 khoản vay, đợt sửa dữ liệu)
├── experiments/
└── README.md
```

## 6. Các giai đoạn triển khai

Toàn bộ MVP được phát triển và chạy end-to-end trên bộ mẫu trước cuối tuần 5; chỉ sau mốc đó mới chuyển sang bộ đầy đủ. Mỗi giai đoạn kết thúc bằng một cổng kiểm thử (C0–C7, bảng ở cuối mục); code của giai đoạn sau chỉ bắt đầu khi cổng trước đạt.

**Giai đoạn 0: Hiểu dữ liệu và thiết kế (tuần 1)**

- [x] Đọc User Guide, File Layout; chốt cột nghiệp vụ theo Satellite (`docs/tu-dien-du-lieu.md`)
- [x] Khám phá bộ mẫu: số khoản vay, số tháng, phân bố quá hạn, giá trị thiếu, mã đặc biệt (`experiments/kham_pha_bo_mau.py`)
- [x] Xác minh: perf có tên bên quản lý (Release 47); seller/servicer nhỏ bị gộp thành `OTHER`
- [x] Xem dung lượng bộ đầy đủ 2019 trên trang tải và ổ cứng còn trống (điều kiện chốt P4): 8,2 GB, ổ còn 953 GB
- [x] Spike kỹ thuật: dbt-spark + automate-dv qua Thrift Server, nạp `hub_loan` và `sat_loan_balance` cho 2 tháng; kiểm tra macro `sat` với nhiều `load_date` trong một stage và khi chạy lại kỳ cũ (`experiments/spike_c0/`, R-26)
- [ ] Vẽ mô hình Data Vault, định nghĩa khóa nghiệp vụ và quy tắc hash

Đầu ra: tài liệu thiết kế 2–3 trang, từ điển dữ liệu, kết luận spike (dùng automate-dv hay tự viết macro).

**Giai đoạn 1: Hạ tầng và Bronze (tuần 2)**

- [x] Docker Compose: Spark, PostgreSQL, Hive Metastore, Thrift Server, Airflow (LocalExecutor); đọc/ghi Delta trên volume cục bộ. Jupyter để giai đoạn 4 (notebook)
- [x] Khai báo schema cho orig và perf, chuẩn hóa tên cột theo Release 47
- [x] Tạo bảng load\_control và DAG Airflow điều phối theo kỳ; nạp Bronze theo kỳ (ghi đè lát của kỳ), thêm `load_date` theo tháng, `record_source`, `source_file`
- [x] Landing: chuyển file TXT sang Delta phân vùng theo tháng một lần cho mỗi bộ dữ liệu; Bronze đọc từ landing (R-28)

Đầu ra: Bronze đủ dòng so với file gốc (AC-01); đo thời gian baseline để hiệu chỉnh mục tiêu 45 phút. **Cổng C1 đạt 30/10/2026:** 29 kỳ bộ mẫu, Bronze nạp tổng 788,6 giây (trung vị 26,9 giây mỗi kỳ, chủ yếu là chi phí cố định của Spark, R-28).

**Giai đoạn 2: Raw Vault (tuần 3)**

- [x] Cổng chất lượng trước dbt (mồ côi, trùng, sai kiểu, ngoài miền); dòng lỗi vào quarantine, ghi số dòng lỗi vào load\_control
- [x] Staging dbt: tính hash key, `hash_diff`
- [x] Model dbt incremental: Hub, Link (chỉ thêm mới), Satellite (chỉ thêm khi `hash_diff` đổi, bỏ qua dòng đã có)
- [x] dbt test sau mỗi tầng; DAG dừng khi test lỗi
- [x] Test idempotent tự động: chạy lại kỳ gần nhất và một kỳ cũ, số dòng không đổi (AC-02)

Đầu ra: Raw Vault nạp tăng dần qua toàn bộ các kỳ của bộ mẫu. **Cổng C2 đạt 30/10/2026:** 29 kỳ, `hub_loan` 50.000 khoản vay, `sat_loan_balance` 1.934.614 dòng (mọi tháng), `sat_loan_delinquency` 109.997 dòng (5,7% số dòng perf nhờ `hash_diff`, P2), 0 dòng bị chặn trên bộ mẫu.

**Giai đoạn 3: Business Vault và PIT (tuần 4)**

- [ ] `bsat_loan_risk`: số tháng quá hạn liên tiếp, cờ từng quá hạn 90+, nhóm rủi ro
- [ ] `bsat_loan_lifecycle`: trạng thái đang hoạt động, trả trước hạn, vỡ nợ, thanh lý
- [ ] `pit_loan_monthly`: con trỏ tới phiên bản Satellite hiệu lực tại mỗi `load_date` theo tháng
- [ ] Đợt sửa dữ liệu giả lập (FR-14) và bảng đối chứng `baseline_dim_loan_overwrite`: bằng chứng chính cho việc chọn Data Vault

Đầu ra: truy vấn được trạng thái khoản vay tại một tháng bất kỳ (AC-04); đợt sửa cho thấy Data Vault giữ được giá trị cũ, còn bảng ghi đè thì mất (AC-09).

**Giai đoạn 4: Gold (tuần 5)**

- [ ] `fact_loan_month` (hạt: khoản vay × tháng báo cáo), `dim_loan`, `dim_seller`, `dim_servicer`, `dim_date`, `dim_geography`
- [ ] Mart: `mart_delinquency` (tháng × bang × bên bán × nhóm điểm tín dụng, LTV, DTI); `mart_prepayment`; `mart_covid_forbearance`
- [ ] Xuất mart sang PostgreSQL; notebook trả lời 5 câu hỏi nghiệp vụ
- [ ] `DAG Airflow` chạy Bronze → Gold bằng một lệnh; chạy lại theo README từ một bản clone sạch

Đầu ra: **mốc MVP**: pipeline end-to-end trên bộ mẫu, đạt AC-01 đến AC-09.

**Giai đoạn 5: Chạy thật và thực nghiệm (tuần 6)**

- [ ] Tải bộ đầy đủ 2019 (toàn năm hoặc 1–2 quý tùy dung lượng đã kiểm ở tuần 1)
- [ ] Chạy pipeline, chạy 4 thực nghiệm bắt buộc ở mục 8

**Giai đoạn 6: Phân tích và code freeze (tuần 7)**

- [ ] Hoàn thiện notebook trả lời 5 câu hỏi nghiệp vụ (dashboard Metabase đã cắt, R-25)
- [ ] (Mở rộng) vintage 2007 hoặc demo mô hình dự báo
- [ ] **Code freeze cuối tuần 7:** nghiệm thu thực nghiệm; sau mốc này chỉ sửa lỗi

**Giai đoạn 7: Hoàn thiện (tuần 8)**

- [ ] Báo cáo, slide, README, video demo dự phòng, tập vấn đáp

**Cổng kiểm thử theo giai đoạn**

Cổng chỉ đạt khi mọi kiểm thử trong cổng đạt. Kiểm thử tự động nằm trong `tests/gates/`, chạy bằng `make gate N=<số cổng>`. Lệnh `make test` chạy lại mọi cổng đã qua để bắt lỗi hồi quy. Mỗi lần chạy cổng lưu commit, ngày và kết quả từng kiểm thử vào `tests/gates/results/`.

| Cổng | Cuối giai đoạn | Kiểm thử phải đạt | Cách kiểm |
| --- | --- | --- | --- |
| C0 | 0 (tuần 1) | 3 điều kiện chốt ở mục 12 có câu trả lời. Từ điển dữ liệu phủ mọi cột dùng ở FR-10, FR-12, FR-16. Quá hạn, trả trước hạn, vỡ nợ, hoãn trả nợ được định nghĩa theo mã. Spike: `hub_loan` và `sat_loan_balance` nạp 2 tháng qua dbt-spark, số dòng Satellite bằng số dòng perf của 2 tháng (kiểm R-01); chạy lại tháng 1 sau tháng 2 sinh 0 dòng (kiểm R-08). Kết luận spike ghi vào lịch sử thay đổi của PRD | Nhóm review tài liệu; `make gate N=0` cho spike |
| C1 | 1 (tuần 2) | `docker compose up`: mọi service healthy. AC-01 ở mọi kỳ của bộ mẫu. Chạy lại một kỳ: số dòng Bronze không đổi, `load_control` thêm đúng 1 dòng. Đổi tên một cột chỉ trong `conf/` thì pipeline vẫn đọc đúng (FR-03, FR-05). Có số đo thời gian baseline | `make gate N=1` |
| C2 | 2 (tuần 3) | Unit test hash (FR-06). AC-06 ở mọi kỳ; không dòng quarantine nào vào Raw Vault. AC-03. AC-02 với kỳ gần nhất và một kỳ cũ. 100% dòng Raw Vault có `load_date`, `record_source`. dbt test Raw Vault đạt 100%; một test cố ý sai làm DAG dừng (FR-22) | `make gate N=2` |
| C3 | 3 (tuần 4) | FR-12: 20 khoản vay khớp giá trị tính tay trong `tests/fixtures/`. AC-04 trên 100 khoản vay ngẫu nhiên (seed cố định). AC-09. dbt test Business Vault đạt 100% | `make gate N=3` |
| C4 | 4 (tuần 5, MVP) | AC-05, AC-07, AC-08. Số dòng mart trong PostgreSQL bằng số dòng mart trên Delta (FR-17). Mọi test C1–C3 đạt khi chạy lại trên môi trường sạch (`docker compose down -v`). Thời gian end-to-end được ghi lại và so với mục tiêu tạm 45 phút; không đạt thì ghi điều chỉnh vào lịch sử thay đổi của PRD, không chặn cổng | `make test`; chạy lại theo README từ bản clone sạch |
| C5 | 5 (tuần 6) | Trên bộ đầy đủ: AC-01, AC-02, AC-05, AC-06 đạt. 4 thực nghiệm bắt buộc, mỗi cấu hình 3 lần, có CSV thô, biểu đồ, ảnh Spark UI hoặc `explain()` | `make gate N=5` |
| C6 | 6 (tuần 7, code freeze) | `make test` xanh trên commit freeze. Mỗi thực nghiệm có phần giải thích. Dashboard hoặc notebook trả lời đủ 5 câu hỏi. Chạy lại theo README từ bản clone sạch, sau `docker compose down -v` | `make test`; review nhóm |
| C7 | 7 (tuần 8) | Đủ hồ sơ ở mục 13. `git ls-files` không chứa dữ liệu Freddie Mac. Slide và video chỉ có số tổng hợp | Checklist trước khi nộp |

**Khi cổng không đạt:**
1. Sửa trong tối đa 2 ngày, lấy từ thời gian của giai đoạn sau.
2. Quá 2 ngày thì mở yêu cầu thay đổi theo PRD mục 8: cắt mục Should theo thứ tự ở P6 hoặc điều chỉnh tiêu chí có ghi lý do. Chỉ đi tiếp sau khi đã quyết định.
3. Không nới tiêu chí để qua cổng mà không ghi vào lịch sử thay đổi.

Việc chuẩn bị cho giai đoạn sau (đọc tài liệu, viết test của cổng sau) vẫn làm song song; chỉ code của giai đoạn sau phải chờ cổng.

## 7. Timeline 8 tuần

Bốn mốc kiểm soát: chốt đề tài cuối tuần 1 (C0), MVP trên bộ mẫu cuối tuần 5 (C4), code freeze cuối tuần 7 (C6), nộp bài cuối tuần 8 (C7). Các tuần còn lại cũng kết thúc bằng cổng kiểm thử của giai đoạn đó.

&#91;embedded content: timeline 8 tuần · 4 mốc kiểm soát\]

Nếu cuối tuần 5 chưa đạt MVP, nhóm cắt giảm theo thứ tự ở P6 (mục 11) thay vì lùi lịch báo cáo.

## 8. Thực nghiệm Spark

Các thực nghiệm được chọn để trả lời câu hỏi riêng của Data Vault trên Spark, không lặp lại các bài so sánh chung chung; mỗi cấu hình chạy 3 lần, lấy trung bình.

| # | Thực nghiệm | Biến thay đổi | Đo | Giả thuyết |
| --- | --- | --- | --- | --- |
| 1 | Mở rộng quy mô | Bộ mẫu, 1 quý, 2 quý, 4 quý đầy đủ | Thời gian toàn pipeline, thời gian từng tầng | Thời gian tăng gần tuyến tính theo số dòng; tầng nào tăng nhanh hơn tuyến tính là điểm nghẽn (thường là `MERGE` Satellite) |
| 2 | Nạp Satellite: incremental (`MERGE`) vs `dbt run --full-refresh` | Cách nạp, số kỳ đã có | Thời gian mỗi kỳ, dung lượng | Tăng dần gần như không đổi theo kỳ; ghi đè chậm dần khi lịch sử dài |
| 3 | Partition Satellite theo kỳ báo cáo (đã cắt, R-25) | Có/không partition | Thời gian truy vấn 1 tháng, `PartitionFilters` | Partition pruning giảm mạnh dữ liệu đọc |
| 4 | PIT table vs join trực tiếp Satellite | Cách truy vấn trạng thái tại thời điểm | Thời gian, độ phức tạp câu lệnh | PIT nhanh và đơn giản hơn rõ rệt |
| 5 | Broadcast join Hub nhỏ (đã cắt, R-25) | Bật/tắt broadcast với Hub seller, servicer | Thời gian, lượng shuffle | Broadcast tránh shuffle |
| 6 | Tách Satellite theo tốc độ thay đổi | 1 Satellite gộp vs 2 Satellite tách | Số dòng, dung lượng | Tách giúp Satellite ít đổi nhỏ hơn nhiều |

**Quy tắc đo:** bấm giờ quanh action (`count()`, `write`) hoặc lấy thời gian model từ `run_results.json` của dbt; xóa cache Spark giữa các lần, bỏ lần chạy khởi động đầu tiên; ghi lại cấu hình máy, phiên bản, `spark.driver.memory`; lưu kết quả thô ra CSV, báo cáo trung vị và min–max của 3 lần; kèm ảnh Spark UI hoặc `explain()` làm bằng chứng.

Thực nghiệm 2, 4 và 6 là điểm khác biệt chính, vì chúng chứng minh bằng số liệu giá trị của các quyết định thiết kế Data Vault.

## 9. Phân công nhóm

Phân công theo lớp dữ liệu, mỗi lớp có một người review chéo để cả nhóm trả lời được vấn đáp về toàn hệ thống.

| Thành viên | Phụ trách chính | Review chéo | Phần báo cáo |
| --- | --- | --- | --- |
| A | Hạ tầng Docker, MinIO, Bronze, schema theo File Layout | Gold | Kiến trúc, môi trường, dữ liệu |
| B | Raw Vault: staging, hash, Hub, Link, Satellite | Bronze | Thiết kế Data Vault |
| C | Business Vault, PIT, Gold, dashboard | Raw Vault | Mô hình phân tích, kết quả nghiệp vụ |
| D | Thực nghiệm Spark, kiểm tra chất lượng, (mở rộng) AI | Toàn pipeline | Thực nghiệm và đánh giá |

Nhóm 3 người: gộp D vào A (thực nghiệm 1, 3, 5) và C (thực nghiệm 2, 4, 6).

**Thực tế (R-25):** đồ án làm một người, đảm nhận cả bốn vai trò; review chéo thay bằng tự review theo checklist của từng cổng.

**Nhịp làm việc:** họp 30 phút, 2 lần/tuần; mỗi tính năng một branch, merge qua pull request có review; tuần 1 cả nhóm cùng đọc tài liệu dữ liệu và thiết kế Data Vault, không chia việc sớm.

## 10. Rủi ro và phương án

Rủi ro lớn nhất là quá tải phạm vi; vì vậy mốc MVP trên bộ mẫu ở tuần 5 là điểm kiểm soát bắt buộc.

| Rủi ro | Khả năng | Ảnh hưởng | Phương án |
| --- | --- | --- | --- |
| Khối lượng Medallion + Data Vault + Spark vượt sức nhóm | Cao | Trễ, làm dở dang | Khóa phạm vi MVP; mọi mở rộng chỉ bắt đầu sau mốc tuần 5 |
| Thiếu kiến thức nghiệp vụ cho vay thế chấp Mỹ | Trung bình | Thiết kế sai, phân tích nông | Tuần 1 cả nhóm đọc User Guide; giới hạn 15–20 cột chính |
| Bộ đầy đủ 2019 quá lớn cho máy | Trung bình | Không chạy được thực nghiệm | Chỉ lấy 1–2 quý; tăng partition, giới hạn bộ nhớ driver |
| Lỗi phiên bản Spark, Delta, hadoop-aws | Cao | Trễ tuần 2 | Chốt phiên bản tuần 1; đã chốt Spark 3.5.5 + Delta 3.3.2 ở C0 (R-26); lưu ổ đĩa thay MinIO (R-25) |
| `MERGE` trên Delta chậm khi Satellite lớn | Trung bình | Thời gian nạp dài | Partition theo kỳ, chỉ so `hash_diff` với phiên bản mới nhất |
| Tên cột đổi giữa bản tải và tài liệu | Thấp | Lỗi đọc file | Ánh xạ tên cột trong `conf/`, ghi nhận thành ví dụ schema evolution |
| Seller/servicer nhỏ bị gộp thành nhóm chung | Đã xảy ra (R-22) | Hub seller/servicer kém ý nghĩa | `OTHER` giữ là một khóa; ghi rõ hạn chế trong báo cáo |
| Ít ca vỡ nợ trong vintage 2019 | Thấp | Phân tích rủi ro nghèo nàn | Tập trung vào quá hạn và hoãn trả nợ COVID; thêm 2007 nếu dư thời gian |
| automate-dv không chạy đúng với dbt-spark, hoặc cấu hình Thrift Server, Metastore, Delta trên MinIO tốn công | Trung bình | Trễ tuần 2–3 | Thử tuần 1 trên một Hub; lỗi thì tự viết macro dbt, vẫn giữ Airflow |
| Airflow và Thrift Server làm thiếu RAM trên máy 16 GB | Trung bình | Spark lỗi bộ nhớ | Airflow LocalExecutor, bỏ Jupyter khi chạy DAG, giảm worker Spark còn 1 |

## 11. Tự phản biện

Mỗi quyết định chính được đặt trước phản biện mạnh nhất có thể; 4 phản biện làm thay đổi kế hoạch (P1, P2, P3, P5), 2 phản biện chưa giải quyết được và trở thành điều kiện chốt (P4, P6).

**P1. "Chỉ có một nguồn dữ liệu, Data Vault là thừa. Star schema trực tiếp là đủ."**

- Phản biện đúng một phần: thế mạnh tích hợp nhiều nguồn của Data Vault sẽ không được thể hiện.
- Nhưng hai thế mạnh còn lại vẫn có thật trong dữ liệu này: lưu lịch sử chính xác theo từng kỳ nạp, và chịu được dữ liệu nguồn bị sửa hoặc đổi schema (Release 47) mà không phải thiết kế lại.
- 5 câu hỏi phân tích tự chúng không cần Data Vault; star schema nạp thẳng cũng trả lời được. Giá trị của Data Vault nằm ở nhóm người dùng kiểm toán.
- **Thay đổi kế hoạch:** giữ Data Vault; báo cáo nói thẳng giới hạn "một nguồn". Giá trị được chứng minh bằng kịch bản sửa dữ liệu (FR-14, nâng lên Must, AC-09): cùng một đợt sửa, bảng star schema nạp ghi đè mất giá trị cũ, còn Data Vault trả lời được trạng thái trước và sau khi sửa. Thực nghiệm 4 chỉ so hai cách truy vấn *bên trong* Data Vault, nên không dùng làm bằng chứng cho lựa chọn mô hình.

**P2. "Dư nợ đổi mỗi tháng, Satellite sẽ thêm dòng mỗi tháng. Như vậy chỉ là bảng snapshot đổi tên, hash\_diff vô nghĩa."**

- Phản biện này **đúng** nếu gộp mọi cột perf vào một Satellite.
- **Thay đổi kế hoạch:** tách theo tốc độ thay đổi: `sat_loan_balance` (đổi hằng tháng) tách khỏi `sat_loan_delinquency` (chỉ đổi khi có sự kiện). `hash_diff` thể hiện giá trị ở Satellite thứ hai. Thực nghiệm 6 được thêm vào để đo đúng điều này.

**P3. "load\_date giả lập theo kỳ báo cáo là không trung thực."**

- Đúng: trong thực tế, dữ liệu một tháng có thể đến trễ hoặc bị sửa ở lần phát hành sau.
- **Thay đổi kế hoạch:** tách rõ hai trục thời gian: `load_date` (khi hệ thống nạp, giả lập theo tháng: ngày 1 của tháng sau tháng báo cáo) và `reporting_period` (thời điểm nghiệp vụ). Giải thích rõ trong báo cáo; đây là kiến thức thầy cô hay hỏi.

**P4. "Bộ mẫu chỉ 216 MB, dùng Spark là phô trương."**

- Đúng với bộ mẫu. Vì vậy bộ mẫu chỉ dùng để phát triển; thực nghiệm chạy trên bộ đầy đủ.
- **Chưa giải quyết được:** dung lượng bộ đầy đủ 2019 chưa biết. Nếu máy chỉ chạy được 1 quý, lập luận Spark yếu đi. Đây là điều kiện chốt (mục 12).

**P5. "Tự viết Data Vault bằng PySpark dễ sai, sao không dùng AutomateDV hay datavault4dbt?"**

- Phản biện **đúng**: tự viết logic hash, so `hash_diff` và nạp chỉ thêm mới dễ sai ở các ca biên (null, chạy lại, nhiều phiên bản trong một đợt), và không có sẵn test.
- Rủi ro của hướng dùng package: automate-dv chủ yếu nhắm tới kho dữ liệu cloud và Databricks; kết hợp với dbt-spark, Thrift Server và Delta trên MinIO có thể tốn công cấu hình.
- **Thay đổi kế hoạch:** chuyển phần mô hình hóa sang dbt + automate-dv để chuẩn hóa và có sẵn dbt test; PySpark chỉ giữ Bronze, cổng chất lượng và xuất dữ liệu. Nhóm vẫn phải giải thích được SQL mà macro sinh ra (`dbt compile`), vì đó là phần thầy cô sẽ hỏi. Rủi ro tương thích được thử bằng spike tuần 1; không chạy được thì tự viết macro hub, link, sat trong dbt.

**P6. "Đề tài nặng, nhóm có thể không kịp."**

- Hợp lý. Kế hoạch đã có mốc MVP trên bộ mẫu ở tuần 5 và danh sách cắt giảm ưu tiên, chỉ cắt phần Should của PRD trước khi đụng tới Must: bỏ mở rộng → bỏ thực nghiệm 3, 5 (FR-20) → bỏ `esat_loan_servicer` (FR-11) → bỏ dashboard, thay bằng notebook (FR-18). Nếu vẫn trễ, áp dụng phương án "nhóm 2 người" ở mục 12.
- **Chưa thể kết luận** khi chưa biết quy mô nhóm và loại môn học.

**P7. "Có bộ nào tốt hơn Freddie Mac không?"**

- Đã khảo sát IBM AML, Santander, FDIC, Fannie Mae, SEC, Home Credit, Berka. Không bộ nào đạt cùng lúc lịch sử có sẵn, quy mô lớn và dữ liệu thật. Fannie Mae tương đương nhưng phải tự tách file rộng.
- **Kết luận:** giữ Freddie Mac.

**P8. "Delta Lake đã có time travel, cần gì Data Vault để truy vết?"**

- Time travel trả lời câu "bảng trông thế nào ở phiên bản n". Như vậy là đủ để khôi phục một lần nạp lỗi và để gỡ lỗi.
- Nhưng phiên bản cũ bị xóa sau `VACUUM` (mặc định giữ 7 ngày), nên time travel không phải nơi lưu lịch sử lâu dài. Nó truy theo phiên bản của cả bảng, không theo khóa nghiệp vụ và hai trục thời gian. Nó cũng không có `record_source` trên từng dòng, và mỗi lần đổi schema hay ghi đè toàn bộ thì lịch sử khó so sánh.
- **Kết luận:** dùng time travel cho vận hành (khôi phục lần nạp lỗi), dùng Data Vault cho lịch sử nghiệp vụ và kiểm toán. Ghi vào báo cáo và tập vấn đáp.

## 12. Quyết định cuối cùng

**Chốt có điều kiện:** triển khai đề tài với Freddie Mac vintage 2019; chốt chính thức khi 3 điều kiện dưới đây được xác nhận trong tuần 1.

**Đề tài:** Xây dựng Data Lakehouse kết hợp Data Vault 2.0 trên Apache Spark cho phân tích rủi ro tín dụng khoản vay thế chấp

**Điều kiện chốt:**

- [x] Dung lượng bộ đầy đủ 2019 vừa máy, ít nhất 2 quý (giải quyết P4): đủ 4 quý về ổ đĩa (8,2 GB, cần 25–33 GB, còn 953 GB). RAM 12 GB với 69,6 triệu dòng perf sẽ được kiểm ở baseline C1 và C5
- [x] Nhóm từ 3 người trở lên, có khoảng 8 tuần (giải quyết P6). **Không đạt:** làm một người; đã cắt giảm phạm vi theo R-25
- [x] Xác nhận loại môn học để phân bổ trọng tâm: Kỹ thuật xử lý dữ liệu, áp dụng hướng "Môn Big Data"

**Phương án theo kết quả kiểm tra:**

| Tình huống | Điều chỉnh |
| --- | --- |
| Môn Big Data | Giữ nguyên; trọng tâm thực nghiệm Spark, Data Vault ở mức MVP |
| Môn Kho dữ liệu | Giữ nguyên dữ liệu; thêm thời gian cho Business Vault, PIT, bridge; chỉ làm 4 thực nghiệm bắt buộc (1, 2, 4, 6) |
| Nhóm 2 người | Giảm Raw Vault còn 2 Hub, 1 Link, 3 Satellite; bỏ dashboard |
| Máy chỉ chạy được 1 quý | Vẫn làm; thực nghiệm mở rộng quy mô dùng nhiều vintage mẫu (2017–2021) thay cho bộ đầy đủ |

**Các thay đổi rút ra từ phản biện:** tách Satellite theo tốc độ thay đổi (P2), tách `load_date` và `reporting_period` (P3), chuyển mô hình hóa sang dbt + automate-dv (P5), thêm thực nghiệm 6, nêu rõ giới hạn một nguồn và chứng minh giá trị Data Vault bằng kịch bản sửa dữ liệu (P1).

## 13. Bàn giao, checklist bảo vệ và nguồn

Bộ hồ sơ nộp gồm mã nguồn chạy được bằng một lệnh (không kèm dữ liệu), báo cáo, slide và video demo.

**Sản phẩm bàn giao:**

- [ ] Repo GitHub: code, `docker-compose.yml`, README hướng dẫn tải dữ liệu và chạy
- [ ] Báo cáo, slide 15–20 trang, video demo 5–7 phút
- [ ] Sơ đồ Data Vault, từ điển dữ liệu, kết quả thực nghiệm

**Dàn ý báo cáo:**

1. Bài toán và mục tiêu
2. Cơ sở lý thuyết: Medallion, Data Vault 2.0 (Hub, Link, Satellite, PIT, Business Vault), Spark và Delta Lake
3. Dữ liệu Freddie Mac và các vấn đề chất lượng
4. Thiết kế và cài đặt pipeline
5. Thực nghiệm và đánh giá
6. Kết quả phân tích rủi ro tín dụng
7. Hạn chế (một nguồn, `load_date` giả lập) và hướng phát triển

**Câu hỏi vấn đáp cần chuẩn bị:**

- [ ] Vì sao chọn Data Vault mà không làm star schema trực tiếp? (demo đợt sửa dữ liệu, AC-09)
- [ ] Vì sao không dùng Delta time travel thay cho Data Vault? (P8)
- [ ] `hash_diff` hoạt động thế nào, vì sao tách Satellite theo tốc độ thay đổi?
- [ ] `load_date` khác `reporting_period` thế nào? Vì sao `load_date` theo tháng dù DAG chạy theo quý?
- [ ] PIT table giải quyết vấn đề gì?
- [ ] Nạp lại cùng một kỳ hai lần thì chuyện gì xảy ra?
- [ ] Xử lý thế nào khi Freddie Mac đổi tên cột?

**Nguồn:**

- [Freddie Mac – Single-Family Loan-Level Dataset](https://freddiemac.com/research/datasets/sf-loanlevel-dataset)
- [General User Guide (July 2026)](https://www.freddiemac.com/fmac-resources/research/pdf/general_user_guide_july_2026.pdf)
- [Disclosure Changes Summary (Release 47)](https://www.freddiemac.com/fmac-resources/research/pdf/disclosure-changes-summary.pdf)
- [FAQ](https://www.freddiemac.com/fmac-resources/research/pdf/faq.pdf)
- [Trang tải SFLLD trên Clarity](https://claritydownload.fmapps.freddiemac.com/CRT/#/sflld)
- [AutomateDV – Worked example (tham khảo mẫu Data Vault)](https://automate-dv.readthedocs.io/en/latest/worked_example/)
