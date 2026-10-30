# Review: PRD và Kế hoạch triển khai

Oct 27, 2026 · @Vĩnh

Vòng review đọc chéo PRD và Kế hoạch triển khai, tìm ra 16 vấn đề: 1 lỗi thiết kế nghiêm trọng, 6 chỗ hai tài liệu mâu thuẫn hoặc tự mâu thuẫn, 9 chỗ thiếu hoặc mơ hồ. Vòng 2 (mục 4) bổ sung 4 vấn đề về lập luận chọn Data Vault và quy trình thực thi. Tất cả đã sửa trong hai file; 2 điểm còn phụ thuộc vào spike kỹ thuật tuần 1 (mục 5). Bản gốc trước khi sửa được giữ ở thư mục backup ngoài repo.

## 1. Lỗi thiết kế nghiêm trọng

**R-01. Khóa Satellite trùng khi kỳ nạp là một quý.**
Kỳ nạp là một quý, nên mỗi khoản vay có 3 dòng perf trong một đợt. Nếu cả đợt dùng chung một `load_date`, ba dòng này trùng khóa (`hash_key`, `load_date`) ở `sat_loan_balance` và `sat_loan_delinquency`. Macro `sat` sẽ giữ một dòng và bỏ hai, nên Satellite mất 2/3 lịch sử. AC-04 (PIT khớp Bronze) sẽ sai ở 2/3 số tháng, và thực nghiệm 6 mất ý nghĩa.

*Sửa:* DAG vẫn chạy theo quý, nhưng mỗi tháng báo cáo m trong quý mang `load_date` riêng (ngày 1 của tháng m+1). PIT dùng các `load_date` theo tháng làm mốc as-of. Phương án dự phòng: nếu macro `sat` không xử lý được nhiều `load_date` trong một stage thì chạy dbt Raw Vault 3 lần mỗi kỳ. (PRD mục 4, 6, FR-10, FR-13; Kế hoạch mục 4)

*Phương án đã cân nhắc và không chọn:* đổi kỳ nạp thành một tháng. Cách này đúng về logic nhưng tăng số lần chạy DAG lên khoảng 80 lần, khó đạt mục tiêu 45 phút. Thêm `reporting_period` vào khóa Satellite (multi-active) thì Satellite luôn có dòng mới mỗi tháng, làm mất giá trị của `hash_diff` mà P2 dựa vào.

## 2. Mâu thuẫn

| # | Vấn đề | Sửa |
| --- | --- | --- |
| R-02 | Idempotent "không đổi số dòng ở bảng nào", nhưng FR-02 yêu cầu `load_control` ghi một dòng mỗi lần chạy | Loại trừ `load_control` (là nhật ký chạy) ở G1 và NFR |
| R-03 | FR-01 bỏ qua kỳ đã SUCCESS, nhưng AC-02 và FR-14 cần chạy lại kỳ | `make run PERIOD=` luôn chạy; chỉ `run-all` bỏ qua kỳ đã SUCCESS; FR-14 thành một đợt sửa có `load_date` mới |
| R-04 | AC-08 (MVP tuần 5) cần dashboard hoặc notebook, nhưng kế hoạch để dashboard ở tuần 7 | Tuần 5 làm notebook; dashboard Metabase (Should) ở tuần 7 |
| R-05 | PRD nhắc "code freeze tuần 7" nhưng kế hoạch không có mốc này | Thêm mốc thứ 4 vào mục 6 và 7 |
| R-06 | Thứ tự cắt giảm ở P6 bỏ 1 Satellite Business Vault, trong khi FR-12 là Must | Chỉ cắt các mục Should trước: FR-20 → FR-11 → FR-18 (FR-14 được nâng lên Must ở R-17) |
| R-07 | P5 lập luận nên viết tay nhưng kết luận dùng automate-dv; số "2 phản biện đổi thiết kế" bỏ sót P5 | Viết lại P5; cập nhật số lượng thành 3 (P2, P3, P5) |

## 3. Thiếu hoặc mơ hồ

| # | Vấn đề | Sửa |
| --- | --- | --- |
| R-08 | Chạy lại một kỳ *cũ* sau khi đã nạp kỳ mới hơn: macro `sat` so với phiên bản mới nhất nên có thể chèn lại giá trị cũ | FR-10: bỏ qua dòng có (`hash_key`, `load_date`) đã tồn tại; AC-02 kiểm cả kỳ cũ |
| R-09 | Bronze và quarantine nạp lại có thể nhân đôi dòng | Ghi đè lát của kỳ bằng `replaceWhere` (FR-04, FR-07) |
| R-10 | Không nói rõ orig vào Bronze theo kỳ nào; AC-01 và AC-03 không kiểm được | Lát orig của kỳ là các khoản vay có tháng perf đầu tiên trong quý; AC-03 tính sau kỳ cuối, chỉ trên khoản vay có perf |
| R-11 | 3 mart không trả lời được câu 2 (LTV, DTI) và câu 3 (bên bán) | `mart_delinquency` có thêm chiều bên bán và nhóm LTV, DTI |
| R-12 | Số Satellite lệch (5 hay 6) và chưa đặt tên; số dim lệch (4–5 hay 5) | Đặt tên 5 Satellite; esat ghi là tùy chọn; chốt 5 dim |
| R-13 | Hash: `sha2` hay `md5`, dấu phân cách và cách xử lý null chưa chốt | sha2-256, `\|\|`, null thành `^^`; thêm test thứ tự null |
| R-14 | "4 phép đối soát" ở G2 không chỉ rõ là những AC nào | Ghi rõ AC-01, 03, 05, 06 |
| R-15 | Giả thuyết thực nghiệm 1 "tuyến tính nhờ phân tán" không đúng trên một máy; quy tắc đo chưa xử lý cache, lần khởi động | Viết lại giả thuyết theo điểm nghẽn từng tầng; xóa cache, bỏ lần đầu, báo cáo trung vị |
| R-16 | Spike automate-dv và việc kiểm dung lượng bộ đầy đủ là điều kiện tuần 1 nhưng không có trong giai đoạn 0; PostgreSQL phục vụ dùng chung với Metastore | Thêm vào giai đoạn 0; tách database `analytics` |

## 4. Vòng 2: lập luận chọn Data Vault và quy trình thực thi

Câu hỏi đặt ra: Data Vault có phải lựa chọn mô hình sai cho use case này không? Kết luận: không. Các chỗ thiếu ở vòng 1 (từ điển dữ liệu, định nghĩa nghiệp vụ, luật chất lượng) mô hình nào cũng cần, và Data Vault đáp ứng đúng nhu cầu truy vết của nhóm kiểm toán. Tuy nhiên, lập luận bảo vệ lựa chọn này đang mỏng hơn mức tài liệu tự nhận.

| # | Vấn đề | Sửa |
| --- | --- | --- |
| R-17 | Kịch bản duy nhất cho thấy Data Vault làm được điều star schema ghi đè không làm được (FR-14) lại là Should, dễ bị cắt đầu tiên | FR-14 lên Must; thêm AC-09 và bảng đối chứng `baseline_dim_loan_overwrite` |
| R-18 | P1 dùng thực nghiệm 4 làm bằng chứng, nhưng thực nghiệm này chỉ so hai cách truy vấn bên trong Data Vault | Sửa P1: bằng chứng là đợt sửa dữ liệu (AC-09) |
| R-19 | Chưa trả lời câu "sao không dùng Delta time travel?" | Thêm phản biện P8 và câu vấn đáp tương ứng |
| R-20 | PRD sẽ thay đổi khi thực thi nhưng chưa có quy trình; các giai đoạn chưa có điều kiện cụ thể để đi tiếp | PRD mục 8 (quản lý thay đổi, lịch sử phiên bản); Kế hoạch mục 6 thêm cổng C0–C7, mỗi cổng gắn với AC/FR và có lệnh `make gate` |

## 5. Còn mở, chờ spike tuần 1

- [x] Macro `sat` của automate-dv trên dbt-spark có xử lý được nhiều `load_date` trong một stage không (quyết định cách giải R-01). Có, xem R-26
- [x] Macro `sat` có bỏ qua dòng đã tồn tại khi chạy lại kỳ cũ không, hay cần bọc thêm bộ lọc (R-08). Không, cần bật bộ lọc `valid_stg`, xem R-26

## 6. Vòng 3: phát hiện từ File Layout Release 47 và bộ mẫu (giai đoạn 0)

Ngày 27/10/2026, khi lập từ điển dữ liệu (`docs/tu-dien-du-lieu.md`), đọc File Layout Release 47 và khám phá bộ mẫu cho thấy một giả định kiến trúc sai và ba điểm cần chốt. PRD lên bản 1.3.

| # | Vấn đề | Quyết định |
| --- | --- | --- |
| R-21 | Release 47 chuyển Servicer Name từ orig sang perf (vị trí 34). Thiết kế cũ lấy `hub_servicer`, `link_loan_servicer` từ orig. Trên bộ mẫu, 18.774 khoản vay (37,5%) đổi servicer, 2.368 khoản vay quay lại servicer cũ | `hub_servicer` và `link_loan_servicer` nạp từ perf. FR-11 (`esat_loan_servicer`) giữ mức Should nhưng nay có dữ liệu để làm. Nếu cắt FR-11, Gold gắn mỗi khoản vay với servicer đầu tiên trong Link và ghi hạn chế, vì Link không biểu diễn được A → B → A. *Phương án không chọn:* nâng FR-11 lên Must (tăng phạm vi khi nhóm chỉ còn một người, xem R-25); bỏ `hub_servicer` và để servicer là thuộc tính Satellite (làm yếu mô hình) |
| R-22 | Seller và servicer dưới ngưỡng 1% UPB của quý bị gộp thành `OTHER` (33,7% khoản vay ở seller) | Giữ `OTHER` là một khóa Hub; mart và báo cáo ghi rõ đây không phải một tổ chức. Rủi ro ở mục 10 Kế hoạch chuyển thành hạn chế đã biết |
| R-23 | Trong forbearance COVID, mã quá hạn vẫn tăng. Định nghĩa vỡ nợ "180 ngày trở lên" cho 1.701 khoản vay, bỏ các tháng forbearance thì còn 926 | Vỡ nợ = quá hạn 180+ ngoài tháng forbearance, hoặc `RA`, hoặc ZBC `02`/`03`/`09` (từ điển dữ liệu mục 4) |
| R-24 | Bộ mẫu có 29 kỳ (2019Q1–2026Q1), 87 `load_date`. Mục tiêu 45 phút tương đương khoảng 1,5 phút mỗi kỳ | Không đổi mục tiêu lúc này; baseline ở C1 quyết định. Nếu không đạt, điều chỉnh theo PRD mục 8 |

## 7. Kết luận spike C0 (29/10/2026)

Spike ở `experiments/spike_c0/`: Spark Thrift Server (Delta, metastore Derby nhúng) và dbt-spark nạp `hub_loan`, `sat_loan_balance` cho tháng 201904 và 201905 của bộ mẫu. Lệnh `make gate N=0` chạy lại 6 kiểm thử.

**R-26. automate-dv chạy được trên dbt-spark, nhưng cần một lớp tương thích.**

| Phát hiện | Quyết định |
| --- | --- |
| automate-dv 0.11.5 chỉ có macro `databricks__*`. Adapter dbt-spark tìm `spark__*` rồi `default__*` (SQL kiểu Snowflake), nên lỗi ngay ở bước compile | Sinh tự động 24 macro `spark__X` gọi `databricks__X` (`gen_shim.py`); chạy lại khi đổi phiên bản automate-dv |
| Bản Databricks của `hub`, `link`, `sat`, `eff_sat` dùng `QUALIFY`. Spark mã nguồn mở 3.5 và 4.1 đều không hỗ trợ cú pháp này | Viết tay `spark__hub`, `spark__sat` (thay `QUALIFY` bằng truy vấn con, giữ nguyên logic); `link` làm ở C2. Nhóm phải giải thích được SQL của các macro này khi vấn đáp (P5) |
| Spark 3.5.7 + Delta 3.3.2 lỗi ở `CREATE OR REPLACE TABLE AS SELECT`, câu lệnh dbt-spark dùng khi tạo bảng | Chốt Spark 3.5.5, Delta 3.3.2, dbt-core 1.12.5, dbt-spark 1.11.0, automate_dv 0.11.5 |
| R-01: macro `sat` so `hash_diff` với dòng liền trước theo `load_date` ngay trong stage, nên nạp nhiều tháng một lần vẫn đúng (28.069 dòng Satellite = 28.069 dòng perf) | Không cần chạy dbt Raw Vault 3 lần mỗi kỳ; bỏ phương án dự phòng ở PRD mục 6 |
| R-08: không có bộ lọc, chạy lại tháng 201904 sau 201905 chèn lại 12.042 dòng trùng khóa, vì dòng cũ bị so với phiên bản mới nhất | Bật `apply_source_filter`: chỉ nhận dòng của khóa mới hoặc có `load_date` sau phiên bản mới nhất. Sửa câu chữ FR-10 cho khớp |
| Hash lưu dạng chuỗi hex in hoa 64 ký tự: `UPPER(SHA2(UPPER(TRIM(x)), 256))` | Ghi vào FR-06; test hash và các phép join so theo kiểu chuỗi |

*Phương án đã cân nhắc và không chọn:* bỏ automate-dv, tự viết toàn bộ macro (mất phần staging, hash, PIT đã chạy được); chuyển sang Databricks (trái với yêu cầu chạy cục bộ, không dùng cloud trả phí).

*Hệ quả của bộ lọc R-08:* dữ liệu đến trễ của một tháng cũ bị bỏ qua thay vì được chèn vào giữa lịch sử. Đây là chủ ý: nếu chèn vào giữa, phép so `hash_diff` sẽ so với sai phiên bản. Đợt sửa dữ liệu FR-14 dùng `load_date` mới nên không bị ảnh hưởng.

## 8. Vòng 4: làm một người (29/10/2026)

**R-25. Điều kiện chốt "nhóm từ 3 người" không đạt.** Đồ án làm một người, môn Kỹ thuật xử lý dữ liệu, 10–15 giờ/tuần. Ước tính cho phạm vi bản 1.4 là 100–110 giờ, vượt sức chứa khi một người làm.

| Thay đổi | Lý do | Ảnh hưởng |
| --- | --- | --- |
| Cắt FR-11 (`esat_loan_servicer`), FR-18 (dashboard Metabase), FR-20 (thực nghiệm 3, 5) | Ba mục Should, theo đúng thứ tự cắt giảm ở P6; tiết kiệm khoảng 12–18 giờ. `eff_sat` còn cần viết tay macro không dùng `QUALIFY` (R-26) | Không biết servicer theo từng tháng; câu hỏi 1–5 vẫn trả lời đủ qua notebook (AC-08); còn 4 thực nghiệm bắt buộc |
| Giữ nguyên Raw Vault: 3 Hub, 2 Link, 5 Satellite | Spike cho thấy mỗi bảng chỉ là một lời gọi macro (khoảng 1 giờ kể cả test); cắt còn 2 Hub, 1 Link, 3 Satellite chỉ tiết kiệm 3–5 giờ | `link_loan_servicer` vẫn ghi nhận mọi cặp khoản vay × servicer, dùng làm ví dụ lịch sử khi vấn đáp |
| Bỏ MinIO: Delta lưu trên volume cục bộ, đường dẫn trong `conf/pipeline.yml` | Bớt một service, bớt hadoop-aws và cấu hình `s3a://`, là rủi ro phiên bản đã nêu ở mục 10 Kế hoạch | NFR "Khả chuyển" đổi: chuyển sang S3 hoặc MinIO chỉ đổi cấu hình và thêm hadoop-aws |
| Airflow chạy LocalExecutor, DAG tuyến tính | Đỡ RAM, đỡ cấu hình | Không ảnh hưởng FR-21 |
| AC-07, NFR "Tái lập", cổng C4, C6: "một thành viên khác chạy lại theo README" thành "chạy lại theo README từ một bản clone sạch, sau `docker compose down -v`" | Không có thành viên khác | Tiêu chí yếu hơn: cùng máy, cùng người. Báo cáo ghi rõ hạn chế này |

*Phương án đã cân nhắc và không chọn:* thu Raw Vault còn 2 Hub, 1 Link, 3 Satellite theo phương án "nhóm 2 người" ở mục 12 Kế hoạch (tiết kiệm ít, mất ví dụ servicer); bỏ Airflow, chạy bằng script (trái quyết định đã chốt về điều phối, và FR-21 là Must).

**Hạn nộp:** C0 trễ khoảng 3 tuần so với kế hoạch (bắt đầu 03/10/2026). Ngày 29/10/2026 chủ repo quyết định không cắt thêm: giữ phạm vi trên, làm đầy đủ.

## 9. Giai đoạn 1: quyết định hạ tầng và Bronze (29/10/2026)

**R-27.** Các quyết định khi dựng `docker-compose.yml` và job Bronze. Không đổi FR hay AC, nhưng đổi kiến trúc ở mục 5 Kế hoạch.

| # | Quyết định | Lý do | Phương án không chọn |
| --- | --- | --- | --- |
| 1 | Không dựng Spark standalone cluster (Kế hoạch ghi 1 master + 2 worker). Hai Spark local mode, mỗi cái một JVM: Thrift Server cho dbt (`local[4]`, 3 GB) và job PySpark trong container Airflow scheduler (3 GB). Hai bên dùng chung Hive Metastore và volume `/lake` | Thrift Server chạy trên cluster sẽ giữ executor suốt thời gian sống và tranh tài nguyên với job Bronze. Trên một máy, cluster không thêm năng lực tính toán, chỉ thêm JVM và RAM | Standalone cluster với dynamic allocation (phức tạp, tốn RAM với 12 GB) |
| 2 | Airflow 3.3.2, LocalExecutor, tách api-server, scheduler, dag-processor; đăng nhập bằng FAB auth manager. Task chạy trong container scheduler nên image có Java 17 và PySpark 3.5.5 | Bản 3.x hiện hành; bản 2.x đã hết hỗ trợ | `airflow standalone` (gộp mọi thứ, chỉ dành cho thử nghiệm) |
| 3 | Hive Metastore 3.1.3 trên PostgreSQL, với script khởi động tự viết | Client Hive tích hợp trong Spark 3.5 là 2.3.9, tương thích metastore 3.1. Entrypoint gốc chạy `-initSchema` mỗi lần khởi động và thoát khi schema đã có | Metastore 4.0 (rủi ro tương thích với client 2.3.9); Derby nhúng (không dùng chung được giữa hai JVM) |
| 4 | `load_control` là bảng `control.load_control` trong database `analytics` (PostgreSQL) | Airflow đọc và ghi nhật ký chạy mà không cần khởi động Spark; báo cáo chất lượng (G5) đọc bằng SQL | Bảng Delta (mỗi lần ghi nhật ký phải khởi động một SparkSession) |
| 5 | Bronze giữ mọi cột dạng chuỗi, thêm `_field_count` và `_raw` (dòng gốc, chỉ khi số trường lệch). File được đọc dạng text rồi tách theo dấu `\|` | Cổng chất lượng (FR-07) cần thấy giá trị sai kiểu và dòng sai số trường. Reader CSV với schema cố định tự lấp null hoặc cắt bớt trường, làm mất bằng chứng | Ép kiểu ở Bronze; reader CSV với `columnNameOfCorruptRecord` (không bắt được dòng thừa trường) |
| 6 | Bảng Bronze là bảng Delta được quản lý trong database `bronze` của metastore, phân vùng theo `period`; ghi đè lát bằng `replaceWhere` | dbt (C2) đọc Bronze qua metastore; phân vùng theo kỳ giúp `replaceWhere` chỉ chạm một thư mục | Bảng theo đường dẫn (dbt khó tham chiếu) |
| 7 | Mọi container chạy uid 1000 | Tránh lỗi quyền giữa Hive, Spark và Airflow trên cùng thư mục `data/lake` | Chạy root (file trên máy thuộc root, khó xóa) |

**Hệ quả cần theo dõi:** mỗi lần chạy Bronze phải quét toàn bộ file perf, để lấy lát tháng và để tìm tháng perf đầu tiên của từng khoản vay (lát orig, R-10). Trên bộ đầy đủ (8 GB) điều này lặp lại ở cả 29 kỳ. Đã xử lý ở R-28.

**R-28. Tầng landing: chuyển file TXT sang Delta một lần cho mỗi bộ dữ liệu.**

| Vấn đề | Quyết định |
| --- | --- |
| Bronze đọc thẳng file TXT ở mỗi kỳ. File là một khối không phân vùng, nên mỗi kỳ quét toàn bộ file hai lần (lấy lát tháng, tìm tháng perf đầu tiên cho lát orig). Trên bộ đầy đủ là 8 GB × 2 × 29 kỳ | Thêm `ingestion/landing.py`: đọc TXT một lần, ghi `landing.<source>_orig`, `landing.<source>_perf` (phân vùng theo tháng báo cáo, mỗi tháng một file) và `landing.<source>_loan_first_month`. Bronze đọc từ landing, mỗi kỳ chỉ đọc 3 thư mục tháng |
| Landing phải luôn khớp với nguồn và schema | Dấu vân tay (tên, kích thước, thời điểm sửa của file TXT và nội dung `conf/schema`) lưu trong file trạng thái nằm trong thư mục database landing. Task `landing` của DAG chỉ dựng lại khi dấu vân tay đổi; nếu không đổi thì không khởi động Spark (0,3 giây) |
| Landing không được làm mất bằng chứng cho cổng chất lượng | Giữ nguyên quy tắc của Bronze: mọi cột dạng chuỗi, `_field_count`, `_raw`, `source_file` trỏ về file TXT gốc. AC-01 vẫn đối chiếu với file TXT gốc |

*Số đo trên bộ mẫu (29/10/2026):* dựng landing một lần mất 27 giây. Task Bronze mỗi kỳ: 25,9 giây (trung vị 13 kỳ) khi đọc TXT, 23,5 giây khi đọc landing. Đo tách từng bước cho thấy trên bộ mẫu thời gian chủ yếu là chi phí cố định của Spark: truy vấn đầu tiên trong JVM mất khoảng 9 giây khởi động nguội, còn khi đã "nóng" thì đọc lát perf 0,5 giây và lát orig 0,8 giây. Ước tính ban đầu "landing giảm còn 8–12 giây mỗi kỳ trên bộ mẫu" là sai. Giá trị của landing nằm ở bộ đầy đủ, nơi phần đọc dữ liệu tăng khoảng 36 lần; thực nghiệm 1 (C5) đo con số này.

*Phương án không chọn:* cache dữ liệu perf trong một job (chỉ gộp hai lượt quét thành một, vẫn quét toàn bộ file mỗi kỳ); một SparkSession sống lâu cho mọi kỳ (giảm chi phí khởi động, nhưng phá cấu trúc một DAG run cho một kỳ và việc chạy lại từng kỳ, FR-21).

*Sửa kèm:* Delta cập nhật schema bảng trong metastore sau mỗi lần ghi; metastore 3.1 mặc định từ chối (`hive.metastore.disallow.incompatible.col.type.changes`) và Delta in stack trace dài (không làm hỏng dữ liệu). Đặt cấu hình này thành `false` để log sạch.

## 10. Giai đoạn 2: cổng chất lượng và Raw Vault (30/10/2026)

**R-29.** Các quyết định khi cài cổng chất lượng (FR-07) và Raw Vault. Không đổi FR hay AC.

| # | Quyết định | Lý do |
| --- | --- | --- |
| 1 | Cổng chất lượng ghi `quality.<x>_clean` (dòng hợp lệ, giữ dạng chuỗi như Bronze) và `quality.<x>_quarantine` (thêm `_reject_reason`, `_reject_column`), phân vùng theo kỳ, ghi đè lát bằng `replaceWhere` | dbt chỉ đọc bảng clean nên dòng lỗi không thể vào Raw Vault; AC-06 kiểm được bằng phép cộng; chạy lại kỳ không nhân đôi (R-09) |
| 2 | Luật đọc từ `conf/schema` (`type`, `domain`, `values`, `missing`, `pattern`, `nullable`), không viết cứng trong code | Từ điển, schema và cổng chất lượng không thể lệch nhau; đổi luật chỉ sửa `conf/` (FR-03) |
| 3 | Mỗi dòng lỗi mang một lý do chính, theo thứ tự: sai số trường, sai khóa, sai kiểu, ngoài miền, trùng khóa, mồ côi | Dòng thiếu trường thì các luật sau vô nghĩa; báo nhiều lý do làm báo cáo chất lượng (G5) đếm trùng |
| 4 | Trùng khóa: chặn mọi bản sao, nhưng chỉ đếm giữa các dòng đã qua luật trên từng dòng | Không biết bản nào đúng; một bản hỏng kiểu không làm bản đúng bị chặn oan |
| 5 | Cột không khai báo `nullable` mà rỗng thì bị chặn với lý do `ngoai_mien` | Thiếu giá trị bắt buộc là một dạng ngoài miền; không thêm lý do mới |
| 6 | Mồ côi so với orig ở Bronze của mọi kỳ đến kỳ hiện tại | Lát orig của một khoản vay nằm ở kỳ có tháng perf đầu tiên, luôn không muộn hơn kỳ của dòng perf. Hệ quả: phải nạp các kỳ theo thứ tự thời gian (`make run-all` đã làm vậy); nạp một kỳ muộn trước kỳ sớm hơn sẽ chặn oan dòng perf |
| 7 | Model `base_orig`, `base_perf` (ép kiểu, đổi mã thiếu thành null) sinh từ `conf/schema` bằng `scripts/gen_dbt_staging.py`; unit test kiểm file sinh ra luôn khớp conf | Viết tay 66 cột với mã thiếu sẽ lệch ngay khi sửa conf. Số tiền dùng `DECIMAL(20, 4)` để tổng dư nợ ở Gold khớp chính xác Bronze (AC-05) |
| 8 | `sat_loan_termination` chỉ nhận dòng có sự kiện kết thúc (`zero_balance_code` hoặc `defect_settlement_date` có giá trị) | Các tháng khác có mọi cột kết thúc đều null; nếu đưa vào, mỗi khoản vay có thêm một phiên bản "toàn null" vô nghĩa |
| 9 | `link` viết lại cùng lõi với `hub` (`_spark_insert_new_keys`), không dùng `QUALIFY` (tiếp R-26) | Hai macro chỉ khác điều kiện khóa ngoại khác null |
| 10 | dbt cài trong virtualenv riêng `/opt/dbt-venv` của image Airflow | dbt-core và Airflow ràng buộc khác nhau trên thư viện dùng chung |
| 11 | `dbt-core-experimental-parser` (phụ thuộc của dbt-core 1.12) chỉ có sdist, lúc cài tải wheel 55 MB từ GitHub Releases. Wheel được tải sẵn vào `docker/airflow/wheels/` (kiểm sha256 theo `assets.json` của gói, không đưa vào git) và cài qua `--find-links` | Mạng tới GitHub Releases ngày 30/10 chỉ khoảng 40 KB/s, build treo. Thư mục rỗng thì pip tải như thường, nên không mất tính tái lập |
| 12 | Một kỳ chỉ được coi là đã nạp xong khi có lần chạy SUCCESS đã qua cổng chất lượng (`rows_clean` có giá trị) | Các lần chạy của DAG giai đoạn 1 chưa có cổng chất lượng và Raw Vault; `make run-all` phải chạy lại chúng |
| 13 | Unit test hash (FR-06) chạy trên SQL thật do automate_dv sinh ra (seed `hash_cases` và test `assert_hash_rules`), không viết lại thuật toán bằng Python | Viết lại bằng Python chỉ chứng minh bản Python đúng, không chứng minh dbt đúng |

**R-30. Staging lưu thành bảng thay vì view.**

| Vấn đề | Quyết định |
| --- | --- |
| Từ kỳ thứ hai, `sat_loan_property` và `sat_loan_origination` (incremental) chạy hơn 3 phút rồi làm Thrift Server tràn heap 3 GB và tắt (hai lần ngày 30/10, kỳ 2019Q2), dù dữ liệu của kỳ chỉ vài chục nghìn dòng. Riêng `EXPLAIN` (chỉ lập kế hoạch) đã mất 63 giây và đẩy bộ nhớ Thrift lên gần 3 GB. Nguyên nhân: Spark không lưu tạm CTE và view mà chép cây biểu thức gốc ở mỗi chỗ tham chiếu. Macro `sat` incremental tham chiếu stage 5 lần, mỗi bản chép mang theo 31 biểu thức `CASE` của `base_*` và các hash `CONCAT_WS` nhiều cột | `stg_orig`, `stg_perf`, `stg_perf_termination` là bảng Delta ghi lại mỗi lần chạy (chỉ chứa kỳ đang nạp); `base_*` vẫn là view. `EXPLAIN` cùng câu lệnh còn 3 giây. Hash chỉ tính một lần cho cả 10 model Raw Vault |
| Spike C0 không bắt được lỗi này | Staging của spike chỉ hash 9 cột và không có lớp `base` ép kiểu. Bài học cho C3 (PIT, Business Vault): model incremental nào tham chiếu nguồn nhiều lần thì nguồn đó phải là bảng |

Kèm theo: giới hạn lịch sử truy vấn của Spark UI (`spark.sql.ui.retainedExecutions` và các cấu hình liên quan trong `docker/spark/conf/spark-defaults.conf`). Đây là biện pháp phòng ngừa cho Thrift Server chạy lâu, không phải nguyên nhân của lần tràn heap trên; chẩn đoán ban đầu "do tích dồn lịch sử" là chưa đúng.

Kế hoạch mục 3 ghi "Staging là view dbt, không lưu bền": nay staging của Raw Vault là bảng tạm, ghi đè mỗi lần chạy, vẫn không giữ lịch sử.
