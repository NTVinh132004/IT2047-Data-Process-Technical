# PRD và kế hoạch: Lakehouse + Data Vault 2.0 trên Spark (Freddie Mac)

Oct 8, 2026 · @Vĩnh · Phiên bản 1.5 (29/10/2026), xem lịch sử ở mục 8

Sản phẩm là một pipeline chạy bằng một lệnh, biến dữ liệu khoản vay Freddie Mac vintage 2019 thành kho Data Vault giữ đủ lịch sử và các bảng Gold trả lời 5 câu hỏi rủi ro tín dụng. MVP trên bộ mẫu đạt cuối tuần 5, nộp cuối tuần 8. Bộ tài liệu gồm ba file: PRD (file này), Kế hoạch triển khai và `Review.md`. Vòng review ngày 27/10/2026 sửa lỗi thiết kế khóa Satellite, các chỗ PRD và kế hoạch lệch nhau, và các tiêu chí nghiệm thu chưa kiểm được; chi tiết trong `Review.md`.

## 1. Vấn đề và bối cảnh

Một tổ chức tài chính (giả định) nắm danh mục khoản vay thế chấp cần trả lời hai loại câu hỏi: rủi ro của danh mục đang thay đổi thế nào, và một khoản vay bất kỳ ở trạng thái gì tại một tháng bất kỳ, theo dữ liệu của đợt nạp nào.

Dữ liệu đến theo đợt, có lỗi, có thể bị sửa ở lần phát hành sau và từng đổi tên cột (Release 47, tháng 7/2026). Một bảng phẳng hoặc star schema nạp ghi đè sẽ mất lịch sử nạp và không truy vết được nguồn gốc. Vì vậy sản phẩm dùng Data Vault 2.0 làm lớp lưu lịch sử, Medallion để tách lớp, Spark và Delta Lake để xử lý hàng chục triệu dòng lịch sử hằng tháng.

Về công cụ: PySpark nạp Bronze, chạy cổng chất lượng và xuất dữ liệu; dbt (dbt-spark, package automate-dv) mô hình hóa Raw Vault, Business Vault và Gold trên chính Spark; Airflow điều phối toàn bộ luồng theo kỳ nạp.

Kiến trúc chi tiết, mô hình Data Vault và phần tự phản biện nằm trong Kế hoạch triển khai: Lakehouse + Data Vault 2.0 trên Spark (Freddie Mac); PRD này đặc tả sản phẩm phải làm được gì và nghiệm thu thế nào.

## 2. Người dùng và nhu cầu

Năm nhóm người dùng quyết định yêu cầu; nhóm kiểm toán là lý do chính để chọn Data Vault thay vì star schema trực tiếp.

| Người dùng | Cần làm được | Dùng lớp nào |
| --- | --- | --- |
| Chuyên viên phân tích rủi ro | Xem tỷ lệ quá hạn theo tháng, bang, nhóm điểm tín dụng, bên bán | Gold, notebook |
| Kiểm toán, tuân thủ | Truy trạng thái một khoản vay tại tháng X; biết dòng đó đến từ file nào, đợt nạp nào | Raw Vault, PIT |
| Kỹ sư dữ liệu vận hành | Nạp kỳ mới, chạy lại kỳ lỗi mà không trùng dữ liệu, xem dòng bị chặn và lý do | `load_control`, quarantine |
| Nhà khoa học dữ liệu (hướng phát triển) | Lấy đặc trưng khoản vay tại một thời điểm, không rò rỉ dữ liệu tương lai | PIT, Business Vault |
| Giảng viên chấm | Chạy lại toàn bộ bằng một lệnh, thấy số liệu thực nghiệm có giải thích | Repo, báo cáo |

## 3. Mục tiêu, chỉ số và phi mục tiêu

Năm mục tiêu, mỗi mục tiêu có một chỉ số kiểm được bằng máy hoặc bằng cách chạy lại từ một bản clone sạch.

| # | Mục tiêu | Chỉ số đạt |
| --- | --- | --- |
| G1 | Pipeline tăng dần chạy bằng một lệnh | `make run-all` kích hoạt DAG Airflow nạp hết các kỳ của bộ mẫu không can thiệp tay; chạy lại một kỳ không đổi số dòng ở bảng dữ liệu nào (`load_control` là nhật ký chạy nên được thêm dòng) |
| G2 | Lịch sử và truy vết đầy đủ | 100% dòng Raw Vault có `load_date`, `record_source`; cả 4 phép đối soát ở mục 6 đạt (AC-01, AC-03, AC-05, AC-06) |
| G3 | Trả lời 5 câu hỏi nghiệp vụ | Mỗi câu có ít nhất 1 bảng Gold và 1 biểu đồ |
| G4 | Chứng minh thiết kế bằng số liệu | 4 thực nghiệm bắt buộc chạy trên bộ đầy đủ (hoặc phương án thay thế ở mục 12 Kế hoạch nếu máy không đủ), mỗi cấu hình 3 lần |
| G5 | Chất lượng dữ liệu minh bạch | Báo cáo số dòng lỗi, mồ côi, trùng theo từng kỳ, lấy từ `load_control` |

**Năm câu hỏi nghiệp vụ (G3):**

1. Tỷ lệ quá hạn 30/60/90+ ngày thay đổi thế nào theo tháng, đặc biệt giai đoạn COVID 2020–2021?
2. Điểm tín dụng, LTV, DTI ban đầu ảnh hưởng thế nào đến khả năng quá hạn?
3. Bang nào, bên bán nào có danh mục rủi ro cao hơn?
4. Bao nhiêu khoản vay được hoãn trả nợ, và sau đó hồi phục hay vỡ nợ?
5. Tỷ lệ trả trước hạn (do tái cấp vốn) thay đổi theo thời gian ra sao?

**Phi mục tiêu:** mô hình AI hoàn chỉnh, streaming, triển khai cloud, tích hợp FDIC, giao diện người dùng riêng. Các mục này ghi vào hướng phát triển.

## 4. Yêu cầu chức năng

22 yêu cầu: 19 bắt buộc (Must) và 3 nên có (Should); cả 3 Should đã cắt ở bản 1.5 vì đồ án làm một người (`Review.md` R-25). Các Must tạo thành MVP, trừ FR-19 (thực nghiệm) được nghiệm thu ở cổng C5. Một **kỳ nạp** là một quý báo cáo, cắt từ file perf theo tháng báo cáo; trong kỳ, mỗi tháng báo cáo có một `load_date` riêng (xem mục 6).

| ID | Yêu cầu | Ưu tiên | Nghiệm thu |
| --- | --- | --- | --- |
| FR-01 | `make run PERIOD=2020Q1` kích hoạt DAG Airflow nạp một kỳ, kể cả kỳ đã SUCCESS (dùng để chạy lại); `make run-all` nạp tuần tự mọi kỳ chưa thành công | Must | Thứ tự đúng; `run-all` bỏ qua kỳ đã SUCCESS |
| FR-02 | Bảng `load_control`: kỳ, trạng thái, số dòng vào, sạch, lỗi, thời gian chạy | Must | Mỗi lần chạy ghi một dòng; kỳ FAILED chạy lại được |
| FR-03 | Schema, ánh xạ tên cột và luật kiểm tra đọc từ `conf/` | Must | Đổi tên một cột chỉ sửa `conf/`, không sửa code |
| FR-04 | Bronze nạp file thô không tiêu đề (phân tách bằng dấu gạch đứng), gắn `load_date`, `record_source`, `source_file`. Mỗi kỳ nhận lát perf của các tháng trong quý và lát orig của các khoản vay có tháng perf đầu tiên trong quý; lát của kỳ được ghi đè (Delta `replaceWhere` theo kỳ), không cộng dồn | Must | Số dòng Bronze bằng số dòng nguồn của lát kỳ; chạy lại kỳ không đổi số dòng |
| FR-05 | Chuẩn hóa tên cột theo Release 47 | Must | Một bảng ánh xạ tên cũ sang mới trong `conf/` |
| FR-06 | Model staging trong dbt (macro stage của automate-dv) tính hash key và `hash_diff`: trim, upper, null thay bằng `^^`, nối bằng `\|\|`, sha2-256, lưu dạng chuỗi hex in hoa 64 ký tự; dấu phân cách và ký hiệu null khai báo một lần trong `dbt_project.yml`, không đổi sau khi đã nạp | Must | Unit test: cùng đầu vào cùng hash; đổi một cột thì `hash_diff` đổi; `('A', null)` và `(null, 'A')` cho hash khác nhau |
| FR-07 | Cổng chất lượng (job PySpark, chạy trước dbt) chặn dòng mồ côi (perf không có orig), trùng khóa (loan × tháng báo cáo), sai kiểu, ngoài miền giá trị; dòng lỗi vào quarantine kèm lý do, lát quarantine của kỳ được ghi đè khi chạy lại | Must | Không dòng lỗi nào vào Raw Vault |
| FR-08 | `hub_loan`, `hub_seller` (từ orig), `hub_servicer` (từ perf, vì Release 47 chuyển tên servicer sang perf): model dbt incremental dùng macro `hub` của automate-dv | Must | Mỗi khóa nghiệp vụ đúng một dòng |
| FR-09 | `link_loan_seller` (từ orig), `link_loan_servicer` (từ perf, mọi cặp khoản vay × servicer đã từng xuất hiện): model dbt dùng macro `link` | Must | Mỗi cặp khóa đúng một dòng |
| FR-10 | 5 Satellite trên `hub_loan`, tách theo tốc độ thay đổi: `sat_loan_origination`, `sat_loan_property` (từ orig), `sat_loan_balance`, `sat_loan_delinquency`, `sat_loan_termination` (từ perf). Khóa là (`hash_key`, `load_date`); macro `sat` chỉ thêm phiên bản khi `hash_diff` khác phiên bản gần nhất trước đó; dòng stage có `load_date` không mới hơn phiên bản mới nhất của khóa bị bỏ qua (`apply_source_filter`, R-26), nên dòng có (`hash_key`, `load_date`) đã tồn tại không bao giờ được chèn lại | Must | Chạy lại một kỳ bất kỳ, kể cả kỳ cũ sau khi đã nạp kỳ mới hơn, sinh 0 dòng mới |
| FR-11 | `esat_loan_servicer` theo dõi servicer hiệu lực tại từng `load_date` (perf có tên servicer theo tháng từ Release 47; 37,5% khoản vay bộ mẫu đổi servicer) | Đã cắt (R-25) | Servicer qua esat tại tháng m khớp `servicer_name` của dòng perf tháng m. Nếu cắt, Gold dùng servicer đầu tiên trong Link và ghi hạn chế |
| FR-12 | `bsat_loan_risk`, `bsat_loan_lifecycle`: model dbt SQL viết theo quy tắc nghiệp vụ | Must | Số tháng quá hạn liên tiếp, cờ từng quá hạn 90+, trạng thái vòng đời khớp tính tay trên 20 khoản vay |
| FR-13 | `pit_loan_monthly`: macro `pit` của automate-dv; bảng mốc thời gian (as-of dates) là các `load_date` theo tháng, nên trạng thái của tháng báo cáo m là dòng PIT tại `load_date` của tháng m | Must | Trạng thái tại một tháng bất kỳ lấy được bằng một join |
| FR-14 | Kịch bản sửa dữ liệu: một đợt sửa nạp sau kỳ cuối, mang vài giá trị khởi tạo đã sửa giả lập, với `load_date` mới và `record_source` riêng. Cùng đợt sửa được nạp vào một bảng đối chứng kiểu star schema ghi đè (`baseline_dim_loan_overwrite`). Đây là bằng chứng chính cho việc chọn Data Vault | Must | AC-09 |
| FR-15 | Star schema dạng model dbt: `fact_loan_month` và 5 dim (`dim_loan`, `dim_seller`, `dim_servicer`, `dim_date`, `dim_geography`) | Must | Hạt fact là khoản vay × tháng báo cáo |
| FR-16 | 3 mart: `mart_delinquency` (tháng × bang × bên bán × nhóm điểm tín dụng, LTV, DTI), `mart_prepayment`, `mart_covid_forbearance` | Must | Trả lời được 5 câu hỏi ở mục 3 (câu 1–3 từ `mart_delinquency`) |
| FR-17 | Task PySpark cuối DAG xuất các mart sang PostgreSQL qua JDBC (database `analytics`, tách khỏi database metadata của Hive Metastore) | Must | Notebook đọc được số mới từ PostgreSQL sau mỗi lần chạy |
| FR-18 | Dashboard Metabase 4–6 biểu đồ | Đã cắt (R-25) | Thay bằng notebook (AC-08) |
| FR-19 | Thực nghiệm 1, 2, 4, 6: quy mô, MERGE tăng dần, PIT, tách Satellite | Must | Kết quả thô CSV, biểu đồ, giải thích |
| FR-20 | Thực nghiệm 3, 5: partition theo kỳ, broadcast join | Đã cắt (R-25) | Hướng phát triển |
| FR-21 | DAG Airflow theo kỳ: nạp Bronze, cổng chất lượng, dbt build Raw Vault, Business Vault, Gold, xuất PostgreSQL; retry 2 lần, chỉ một lượt chạy cùng lúc, ghi trạng thái vào load\_control | Must | Giao diện Airflow hiện đủ task; kỳ lỗi chạy lại từ task lỗi mà không trùng dữ liệu |
| FR-22 | dbt test (unique, not\_null, relationships) trên Hub, Link, Satellite, fact, dim chạy sau mỗi tầng; test lỗi thì DAG dừng trước tầng sau | Must | dbt test đạt 100% trên bộ mẫu; một test cố ý sai làm DAG dừng |

Nội dung từng thực nghiệm nằm ở mục 8 của tài liệu kiến trúc.

## 5. Yêu cầu phi chức năng

Tính idempotent và khả năng tái lập là hai yêu cầu không được cắt, vì giảng viên sẽ chạy lại và hỏi về chúng.

| Thuộc tính | Yêu cầu | Cách kiểm |
| --- | --- | --- |
| Idempotent | Chạy lại một kỳ không đổi số dòng ở bất kỳ bảng dữ liệu nào (Bronze, quarantine, Raw Vault, Business Vault, Gold); `load_control` chỉ thêm một dòng nhật ký | Test tự động từ tuần 3 |
| Tái lập | `docker compose up` rồi một lệnh là chạy; phiên bản Spark, Delta, Airflow, dbt-core, dbt-spark, automate-dv ghi cố định | Clone repo vào thư mục mới, `docker compose down -v`, chạy lại theo README |
| Truy vết | Raw Vault chỉ thêm mới; mọi dòng có `load_date`, `record_source`; giữ lịch sử Delta để time travel | Kiểm tra not null; thử đọc phiên bản cũ |
| Hiệu năng (mục tiêu tạm) | Bộ mẫu chạy end-to-end trong 45 phút trên máy RAM 16 GB; hiệu chỉnh sau khi đo baseline tuần 2 | Thời gian ghi trong `load_control` |
| Cấu hình | Schema, luật, đường dẫn nằm trong `conf/` | Review code |
| Khả chuyển | Delta lưu trên ổ đĩa cục bộ, đường dẫn đọc từ `conf/pipeline.yml`; chuyển sang S3 hoặc MinIO (`s3a://`) chỉ đổi cấu hình và thêm hadoop-aws | Review cấu hình |
| Giấy phép dữ liệu | Không đưa dữ liệu lên repo (`data/` trong `.gitignore`); slide và video chỉ hiện số tổng hợp | Kiểm tra trước khi nộp |
| Lineage | dbt docs sinh sơ đồ phụ thuộc từ staging đến mart | Mở trang dbt docs, đủ các bảng Raw Vault, Business Vault, Gold |

## 6. Dữ liệu và tiêu chí nghiệm thu MVP

MVP được nghiệm thu bằng 9 kiểm tra định lượng trên bộ mẫu 2019, không bằng nhận xét "đúng chuẩn Data Vault". Các kiểm tra này được chạy dần qua các cổng C1–C4 (Kế hoạch mục 6), không dồn đến tuần 5.

**Dữ liệu:** Freddie Mac Single-Family Loan-Level Dataset, vintage 2019. File orig có một dòng mỗi khoản vay (\~6,2 MB bộ mẫu); file perf có một dòng mỗi khoản vay mỗi tháng (\~216 MB bộ mẫu). Hai file nối bằng mã khoản vay. Bộ đầy đủ chia theo **quý khởi tạo** (2019Q1 đến Q4), mỗi quý một cặp orig và perf, layout Release 47: tổng 1.781.144 khoản vay, 69.630.113 dòng perf, 8,2 GB file txt (khoảng 36 lần bộ mẫu).

**Kỳ nạp:** vì file chia theo quý khởi tạo chứ không theo thời gian, pipeline tự cắt perf theo **quý báo cáo** để giả lập dữ liệu đến theo đợt. Một khoản vay vào Hub ở kỳ đầu tiên nó xuất hiện trong perf, kèm Satellite khởi tạo lấy từ orig.

**Hai trục thời gian:** `load_date` là lúc hệ thống nạp, `reporting_period` là tháng nghiệp vụ. Không dùng lẫn hai cột này.

**`load_date` theo tháng, DAG theo quý:** một lần chạy DAG xử lý một quý (đơn vị điều phối), nhưng mỗi tháng báo cáo m trong quý được gán một `load_date` riêng, giả lập ngày dữ liệu tháng m đến (ngày 1 của tháng m+1). Dòng orig nhận `load_date` của tháng perf đầu tiên của khoản vay. Nhờ vậy mỗi khoản vay có tối đa một dòng perf cho mỗi `load_date`, khóa Satellite (`hash_key`, `load_date`) không trùng và `hash_diff` so được giữa hai tháng liên tiếp. Nếu dùng một `load_date` cho cả quý, ba dòng perf của cùng khoản vay sẽ trùng khóa và Satellite mất hai trong ba tháng. Spike C0 xác nhận macro `sat` xử lý đúng nhiều `load_date` trong một lần chạy (R-26), nên mỗi kỳ chỉ chạy dbt Raw Vault một lần.

**Tiêu chí nghiệm thu MVP:**

- [ ] AC-01: Số dòng Bronze bằng số dòng nguồn của lát kỳ ở mọi kỳ
- [ ] AC-02: Chạy lại một kỳ bất kỳ (kỳ gần nhất và một kỳ cũ hơn) sinh 0 dòng mới ở Hub, Link, Satellite
- [ ] AC-03: Sau kỳ cuối, số dòng `hub_loan` bằng số mã khoản vay khác nhau trong orig có ít nhất một dòng perf, trừ số bị quarantine
- [ ] AC-04: Với 100 khoản vay ngẫu nhiên, trạng thái lấy qua PIT tại tháng m khớp dòng perf tháng m ở Bronze
- [ ] AC-05: Tổng dư nợ theo tháng ở Gold khớp tổng tính trực tiếp từ Bronze, sai lệch bằng 0
- [ ] AC-06: Theo từng kỳ, số dòng sạch cộng số dòng quarantine bằng số dòng Bronze
- [ ] AC-07: Toàn bộ bộ mẫu chạy bằng một lệnh; chạy lại được theo README từ một bản clone sạch, sau `docker compose down -v`
- [ ] AC-08: Dashboard hoặc notebook thay thế trả lời đủ 5 câu hỏi nghiệp vụ
- [ ] AC-09: Sau đợt sửa (FR-14), Satellite khởi tạo có phiên bản mới cho đúng các khoản vay bị sửa và phiên bản cũ còn nguyên; PIT trước và sau `load_date` của đợt sửa trả về giá trị cũ và giá trị mới; bảng đối chứng ghi đè chỉ còn giá trị mới

Thực nghiệm trên bộ đầy đủ không thuộc MVP; chúng được nghiệm thu ở cổng C5 (tuần 6) và chốt ở cổng code freeze C6 (tuần 7).

## 7. Giả định, phụ thuộc và câu hỏi mở

PRD giữ các giả định của kế hoạch trước; ba câu hỏi đầu phải có câu trả lời trước cổng chốt đề tài cuối tuần 1.

**Giả định:** một người (ban đầu giả định nhóm 3–4 người, đổi ở bản 1.5), 10–15 giờ/tuần, 8 tuần, môn Big Data hoặc Kỹ thuật dữ liệu, máy chính RAM 16 GB.

**Phụ thuộc:** tài khoản Freddie Mac (đã có, đã tải bộ mẫu 2019), File Layout bản Release 47, Docker trên máy chính; Spark Thrift Server và Hive Metastore (metadata lưu trên PostgreSQL sẵn có) để dbt kết nối Spark.

**Câu hỏi mở:**

- [x] Môn học là Big Data hay Kho dữ liệu? Môn Kỹ thuật xử lý dữ liệu, gần với phương án Big Data
- [x] Nhóm mấy người? Một người; phạm vi đang chờ quyết định (`Review.md` R-25)
- [x] Bộ đầy đủ 2019 nặng bao nhiêu, ổ cứng còn trống bao nhiêu (cần gấp 3–4 lần dữ liệu thô)? 8,2 GB txt, cần khoảng 25–33 GB; ổ WSL còn 953 GB
- [x] File perf có tên bên quản lý không (quyết định FR-11)? Có, từ Release 47 (`Review.md` R-21)
- [ ] Giảng viên có chấp nhận dữ liệu tài chính nước ngoài không?
- [x] automate-dv có chạy được với adapter dbt-spark không (tài liệu chính thức nhắm Databricks)? Có, với lớp tương thích: shim `spark__*` và macro `hub`, `sat` viết lại không dùng `QUALIFY` (R-26)
- [x] Macro `sat` của automate-dv có nạp đúng khi một stage chứa nhiều `load_date` cho cùng khóa, và có bỏ qua dòng (`hash_key`, `load_date`) đã tồn tại khi chạy lại kỳ cũ không? Nhiều `load_date`: đúng. Chạy lại kỳ cũ: chỉ đúng khi bật `apply_source_filter` (R-26)
- [ ] Máy RAM 16 GB có chạy cùng lúc Spark, Thrift Server, Metastore và Airflow được không?

Cách điều chỉnh phạm vi khi giả định sai nằm ở mục 12 Kế hoạch triển khai; khi câu trả lời làm đổi yêu cầu, sửa PRD theo mục 8.

## 8. Quản lý thay đổi

PRD là tài liệu sống: được sửa khi spike, cổng kiểm thử hoặc dữ liệu thật cho thấy giả định sai. Mọi thay đổi đều phải ghi lại, để tiêu chí nghiệm thu không bị trôi.

- **Nguồn thay đổi hợp lệ:** kết quả spike, cổng kiểm thử không đạt, câu hỏi mở ở mục 7 được trả lời, góp ý của giảng viên.
- **Thay đổi nhỏ** (làm rõ câu chữ, không đổi FR, AC hay ưu tiên): sửa trực tiếp, thêm một dòng vào lịch sử thay đổi.
- **Thay đổi lớn** (thêm, bỏ hoặc đổi ưu tiên FR; sửa AC; đổi kiến trúc): ghi vấn đề, các phương án và quyết định vào `Review.md`; cả nhóm đồng ý ở buổi họp; cập nhật PRD, Kế hoạch và test cổng liên quan trong cùng một pull request; tăng phiên bản phụ.
- **Thay đổi tiêu chí của một cổng đã qua** thì phải chạy lại cổng đó.
- **Không nới AC chỉ để một cổng đang trượt được qua.** Nếu buộc phải hạ tiêu chí, ghi rõ lý do và ảnh hưởng tới báo cáo trong lịch sử thay đổi.

**Lịch sử thay đổi**

| Phiên bản | Ngày | Thay đổi | Lý do |
| --- | --- | --- | --- |
| 1.0 | 08/10/2026 | Bản đầu | — |
| 1.1 | 27/10/2026 | `load_date` theo tháng; idempotent cho kỳ cũ, Bronze, quarantine; mart đủ chiều; chốt quy tắc hash; sửa các chỗ lệch với Kế hoạch | `Review.md` R-01 đến R-16 |
| 1.2 | 27/10/2026 | FR-14 lên Must, thêm AC-09 và bảng đối chứng ghi đè; thêm mục quản lý thay đổi; AC gắn với cổng kiểm thử | `Review.md` R-17 đến R-20 |
| 1.3 | 27/10/2026 | `hub_servicer`, `link_loan_servicer` nạp từ perf; FR-11 có dữ liệu, giữ Should, thêm tiêu chí nghiệm thu; trả lời 3 câu hỏi mở ở mục 7 | `Review.md` R-21; từ điển dữ liệu `docs/tu-dien-du-lieu.md` |
| 1.4 | 29/10/2026 | Kết luận spike C0: dùng automate-dv với lớp tương thích dbt-spark; FR-10 đổi câu chữ quy tắc bỏ dòng khi chạy lại; FR-06 ghi dạng lưu hash; bỏ phương án chạy dbt 3 lần mỗi kỳ; chốt Spark 3.5.5 | `Review.md` R-26; `make gate N=0` |
| 1.5 | 29/10/2026 | Làm một người: cắt FR-11, FR-18, FR-20; bỏ MinIO (Delta trên ổ đĩa cục bộ); Airflow LocalExecutor; AC-07 và NFR "Tái lập" đổi từ "thành viên khác chạy lại" sang "chạy lại từ bản clone sạch" (tiêu chí yếu hơn, ghi vào hạn chế của báo cáo) | `Review.md` R-25 |
| 1.5 | 29/10/2026 | Bổ sung (thay đổi nhỏ): dung lượng bộ đầy đủ 2019; cả 3 điều kiện chốt có câu trả lời, cổng C0 đạt | Kế hoạch mục 6, 12; `tests/gates/results/c0-20261029-095352.json` |
| 1.5 | 30/10/2026 | Bổ sung (thay đổi nhỏ): cổng C1 đạt; baseline Bronze bộ mẫu 788,6 giây cho 29 kỳ. Mục tiêu 45 phút end-to-end giữ nguyên, đánh giá lại ở C4 khi có đủ các tầng | `Review.md` R-27, R-28; `tests/gates/results/c1-*.json` |
| 1.5 | 30/10/2026 | Bổ sung (thay đổi nhỏ): cổng C2 đạt (AC-02, AC-03, AC-06, FR-06, FR-07, FR-22). FR-10: staging lưu thành bảng ghi đè mỗi lần chạy thay vì view, không đổi tiêu chí | `Review.md` R-29, R-30; `tests/gates/results/c2-*.json` |
