# Kịch bản thuyết trình

Kịch bản cho bộ slide 20 trang (`data/reports/sample-report/bao-cao-sample.pptx`, sinh bằng `uv run python -m scripts.build_sample_slides`). Cách mở slide và tái sinh: [huong-dan-slide.md](huong-dan-slide.md). Số liệu lấy từ [báo cáo](bao-cao-do-an.md); khi được hỏi chi tiết, mở mục báo cáo ghi trong ngoặc.

## Phân bổ thời gian

| Phần | Trang | Thời gian | Mục đích |
| --- | --- | ---: | --- |
| Mở đầu | 1–4 | 3 phút | Người nghe hiểu bài toán trước khi nghe giải pháp |
| Chương 1 | 5–7 | 2 phút 30 | Đủ khái niệm để theo được chương 3; không giảng lý thuyết dài |
| Chương 2 | 8–9 | 2 phút 30 | Mỗi vấn đề dữ liệu dẫn tới một quyết định thiết kế |
| Chương 3 | 10–13 | 5 phút | Trọng tâm kỹ thuật xử lý dữ liệu |
| Chương 4 | 14–18 | 5 phút | Bằng chứng: kiểm chứng, thực nghiệm, kết quả phân tích |
| Chương 5 | 19 | 1 phút | Kết luận và hạn chế, nói thẳng |
| Demo | 20 | 5 phút | Chứng minh hệ thống chạy thật và giữ được lịch sử |
| **Tổng** | | **khoảng 24 phút** | Rút gọn: bỏ demo trực tiếp, chiếu video; bớt chương 1 |

Nếu học phần giới hạn 15 phút: nói lướt trang 5–7 (1 phút), gộp trang 15–16 (2 phút), chiếu video demo thay vì demo trực tiếp.

## Lời nói theo từng trang

Lời dưới đây là gợi ý để nói tự nhiên, không đọc nguyên văn. Câu **in đậm** là ý bắt buộc phải nói.

### Mở đầu

**Trang 1 · Bìa (20 giây)**

> Em xin chào thầy cô. Em là Nguyễn Thế Vĩnh, MSHV 26848266. Đề tài của em là xây dựng Data Lakehouse kết hợp Data Vault 2.0 trên Apache Spark cho phân tích rủi ro tín dụng khoản vay thế chấp, dùng dữ liệu công khai của Freddie Mac.

**Trang 2 · Lý do chọn đề tài (50 giây)**

> Dữ liệu tín dụng có ba đặc điểm khó. Thứ nhất, nó đến theo đợt: mỗi khoản vay có một dòng trạng thái mỗi tháng, nên hệ thống phải nạp tăng dần. Thứ hai, nó có lỗi và có thể bị sửa ở đợt sau; riêng Release 47 tháng 7/2026 đã đổi tên cột. Thứ ba, kiểm toán cần biết một khoản vay ở trạng thái nào tại tháng X, theo dữ liệu của đợt nạp nào.
>
> **Một bảng phẳng hay star schema ghi đè sẽ mất lịch sử khi dữ liệu bị sửa.** Vì vậy em khảo sát Data Vault 2.0, một mô hình thiết kế để lưu lịch sử, đặt trên kiến trúc Lakehouse.

**Trang 3 · Bài toán (50 giây)**

> Bài toán cụ thể: **đầu vào** là hai file TXT, orig và perf, gồm 50.000 khoản vay và gần 1,93 triệu dòng tháng. **Yêu cầu xử lý** là nạp tăng dần theo kỳ, giữ đủ lịch sử, chạy lại an toàn và chặn dòng lỗi kỹ thuật. **Đầu ra** là kho Data Vault có lịch sử, các mart trên PostgreSQL và notebook phân tích.
>
> Đầu ra phải trả lời được năm câu hỏi rủi ro tín dụng ở dưới. Em sẽ dùng chính năm câu này để kiểm tra kết quả ở chương 4.

**Trang 4 · Mục tiêu và phạm vi (40 giây)**

> Bốn mục tiêu, mỗi mục tiêu đo được bằng tiêu chí nghiệm thu. Về phạm vi, em làm trên **bộ mẫu** vintage 2019, chạy trên một máy RAM 12 GB. Bộ đầy đủ 8,2 GB, mô hình học máy, streaming và cloud nằm ngoài phạm vi; em sẽ nói lại ở phần hạn chế.

*Chuyển ý:* "Trước khi vào thiết kế, em điểm qua các khái niệm và công nghệ được dùng."

### Chương 1 · Cơ sở lý thuyết và công nghệ

**Trang 5 · Lakehouse, Medallion, Delta Lake (50 giây)**

> Lakehouse tổ chức dữ liệu qua ba lớp: Bronze giữ nguyên nguồn, Silver làm sạch và tích hợp, Gold phục vụ phân tích. Trong đồ án, lớp Silver chính là Data Vault. Dữ liệu lưu bằng **Delta Lake: các file Parquet cộng một nhật ký giao dịch**, cho phép ghi nguyên tử, ghi đè đúng một lát dữ liệu và xem phiên bản cũ.

**Trang 6 · Data Vault 2.0 (60 giây)**

> Data Vault tách dữ liệu thành bốn loại đối tượng. **Hub** giữ danh sách khóa nghiệp vụ, ví dụ mã khoản vay. **Link** giữ quan hệ, ví dụ khoản vay với bên bán. **Satellite** giữ thuộc tính có lịch sử. **PIT** là bảng con trỏ để lấy nhanh trạng thái tại một mốc.
>
> **Điểm cốt lõi: Satellite chỉ thêm dòng khi thuộc tính thay đổi, phát hiện bằng hash_diff, và không bao giờ sửa hay xóa.** Nhờ đó mọi phiên bản đều còn.

**Trang 7 · Công nghệ (40 giây)**

> PySpark xử lý file và kiểm tra kỹ thuật. dbt cùng package AutomateDV mô hình hóa Data Vault bằng SQL. Delta Lake lưu trên đĩa cục bộ, truy cập qua Spark Thrift Server. Airflow điều phối, mỗi tầng một DAG. PostgreSQL phục vụ mart cho notebook. Tất cả chạy bằng Docker Compose.

*Chuyển ý:* "Vì sao thiết kế như vậy? Câu trả lời nằm ở đặc điểm của chính dữ liệu."

### Chương 2 · Phân tích hiện trạng và dữ liệu

**Trang 8 · Bộ dữ liệu (50 giây)**

> Bộ mẫu có 50.000 khoản vay, 1.934.614 dòng khoản vay–tháng, trải 87 tháng từ 01/2019 đến 03/2026. File orig có 31 trường lúc giải ngân như điểm tín dụng, LTV, DTI. File perf có 35 trường mỗi tháng như dư nợ, số tháng quá hạn, hoãn trả. Cả hai là TXT không tiêu đề, phân tách bằng dấu gạch đứng.
>
> Để kiểm chứng việc giữ lịch sử, em tạo thêm một **đợt sửa giả lập CORR1**: 20 khoản vay được sửa điểm tín dụng và DTI, nạp sau kỳ cuối.

**Trang 9 · Vấn đề dữ liệu → yêu cầu thiết kế (100 giây, trang quan trọng)**

> Đây là cầu nối sang thiết kế. Mỗi vấn đề dẫn tới một quyết định.
>
> Một: **file chia theo quý khởi tạo, nhưng phân tích cần theo tháng báo cáo.** Nên em thêm tầng landing, phân vùng theo tháng.
>
> Hai: dữ liệu có dòng sai số trường, mã thiếu như 9999, và tên cột từng đổi. Nên em đọc file dạng text rồi tự tách trường để giữ bằng chứng lỗi, chặn lỗi kỹ thuật trước khi vào Vault, và khai báo schema trong file cấu hình.
>
> Ba: **dữ liệu bị sửa ở đợt sau.** Nên Satellite chỉ thêm phiên bản, và mỗi tháng có một load_date riêng.
>
> Bốn: hệ thống phải chạy lại được khi lỗi giữa chừng. Nên mọi tầng ghi đè đúng lát của kỳ, bỏ qua dòng đã có, và chạy như job độc lập có thử lại.

### Chương 3 · Thiết kế hệ thống và xây dựng mô hình

**Trang 10 · Kiến trúc (60 giây)**

> Dữ liệu đi từ trái sang phải: Bronze, cổng chất lượng, Silver gồm Raw Vault và Business Vault, Gold, rồi xuất sang PostgreSQL. **Mỗi tầng là một DAG Airflow độc lập**, đọc bảng điều khiển để biết kỳ nào đã sẵn sàng. Tầng nào lỗi thì thử lại tầng đó, không chạy lại tầng dưới.

**Trang 11 · Kỹ thuật nạp TXT → landing → Bronze (90 giây, trọng tâm)**

> Đây là kỹ thuật xử lý chính ở đầu pipeline. File TXT được **đọc dạng text rồi tự tách theo dấu gạch đứng**, giữ mọi giá trị là chuỗi, kèm số trường thực tế và nguyên văn dòng lỗi. Em đã đo: reader CSV mặc định của Spark không phát hiện được dòng nào trong 20 dòng sai số trường cài sẵn, còn cách tách thủ công phát hiện đủ 20.
>
> Sau đó landing ghi thành **bảng Delta phân vùng theo tháng**: 211 MiB TXT còn khoảng 49 MiB Parquet, 87 file, mỗi tháng một file. Khi nạp một kỳ, Spark chỉ mở đúng 3 thư mục tháng. **Cắt lát Bronze một kỳ nhanh hơn 4 đến 8 lần** so với đọc thẳng TXT. Bronze ghi đè đúng lát của kỳ bằng replaceWhere, nên chạy lại không bị trùng.

**Trang 12 · Mô hình Raw Vault (70 giây)**

> Raw Vault có 3 Hub, 2 Link và 5 Satellite trên khoản vay. Satellite được **tách theo tốc độ thay đổi**: dư nợ đổi mỗi tháng nằm riêng, trạng thái quá hạn ít đổi nằm riêng.
>
> Khóa và hash_diff dùng SHA-256 theo một quy tắc cố định. Mỗi tháng báo cáo nhận load_date là ngày 1 của tháng sau; nếu dùng một load_date cho cả quý, ba tháng của cùng khoản vay sẽ trùng khóa.

**Trang 13 · Business Vault, PIT, Gold, điều phối (60 giây)**

> PIT lưu con trỏ tới phiên bản hiệu lực tại mỗi mốc; chưa có phiên bản thì trỏ tới ghost record, nên **mọi truy vấn trạng thái chỉ cần equi-join**. Business Vault tính số tháng quá hạn liên tiếp và vòng đời khoản vay. Gold dựng bảng fact theo khoản vay × tháng, năm dimension và ba mart. Khi xuất sang PostgreSQL, em ghi vào bảng trung gian, đối soát số dòng, rồi thay dữ liệu phục vụ trong một transaction: lỗi giữa chừng không làm hỏng bản đang dùng.

*Chuyển ý:* "Thiết kế như vậy có đúng và có đáng không? Em chứng minh bằng kiểm chứng và thực nghiệm."

### Chương 4 · Triển khai thực nghiệm và đánh giá

**Trang 14 · Kiểm chứng (60 giây)**

> Hệ thống đạt **9/9 tiêu chí nghiệm thu**. Toàn bộ **89 kiểm tra chạy lại đạt trên một bản clone sạch** với lake và volume mới. Tổng dư nợ từng tháng ở Gold khớp chính xác với file TXT, 87 tháng không lệch.
>
> **Bằng chứng chính cho Data Vault là FR-14**: sau đợt sửa CORR1, Satellite có phiên bản mới cho đúng 20 khoản vay, bản cũ vẫn còn, PIT trước và sau đợt sửa trả về giá trị cũ và mới. Bảng đối chứng kiểu ghi đè chỉ còn giá trị mới. Em sẽ demo phần này ở cuối.

**Trang 15 · TN1 mở rộng quy mô (60 giây)**

> Em chạy toàn bộ pipeline trên 25%, 50% và 100% bộ mẫu, mỗi mức ba lần, mỗi lần dựng lại môi trường từ đầu. **Dữ liệu tăng 3,9 lần nhưng thời gian chỉ tăng khoảng 11%**, từ 715 lên 795 giây. Ở quy mô mẫu, phần lớn thời gian là chi phí cố định của Spark và dbt.
>
> Một phát hiện thú vị: tầng Raw Vault đi theo số lô chứ không theo dữ liệu. Tập nhỏ lại chậm hơn vì bị chia thành 6 lô, mỗi lô trả chi phí cố định. Cả 9 lần chạy đều đạt các phép đối soát.

**Trang 16 · TN2, TN4, TN6 (90 giây)**

> Ba thực nghiệm cho ba quyết định Data Vault, **mỗi thực nghiệm có phép kiểm đúng** để tốc độ không che một kết quả sai.
>
> TN2: nạp tăng dần một kỳ mới **giữ khoảng 35 giây** dù lịch sử dài ra, còn dựng lại toàn bộ tăng lên 67 giây ở 29 kỳ; hai cách cho cùng số dòng.
>
> TN4: lấy trạng thái mọi khoản vay ở mọi mốc qua **PIT nhanh hơn khoảng 5,6 lần** so với join trực tiếp, câu SQL ngắn hơn 6 lần, cùng checksum. Hỏi một mốc thì hai cách gần ngang nhau.
>
> TN6, kết quả trái giả thuyết và em giữ nguyên: **tách Satellite không tiết kiệm dung lượng** trên Parquet, vì nén cột xử lý tốt giá trị lặp. Lợi ích thật là truy vấn lịch sử quá hạn nhanh hơn khoảng 2,3 lần và mô hình rõ ràng hơn.

**Trang 17 · Kết quả Q1–Q3 (60 giây)**

> Câu 1: tỷ lệ quá hạn 90 ngày trở lên tăng mạnh giai đoạn COVID, **đỉnh 3,57% vào tháng 2/2021**. Câu 2: nhóm điểm tín dụng 620–679 có tỷ lệ 3,49%, nhóm từ 780 chỉ 0,38%. Câu 3: trong các bang đủ lớn, New Jersey, Nevada, New York cao nhất.
>
> **Đây là thống kê mô tả trên bộ mẫu, không phải quan hệ nhân quả.**

**Trang 18 · Kết quả Q4–Q5 (50 giây)**

> Câu 4: 3.310 khoản vay từng hoãn trả thời COVID; sau đó 43% hồi phục, 36% trả trước hạn, 16% vỡ nợ lần đầu. Câu 5: tỷ lệ trả trước hạn năm hóa **đạt đỉnh 52,8% vào tháng 3/2021**, giai đoạn lãi suất thấp. Dữ liệu không ghi lý do trả trước, nên em không khẳng định tất cả là tái cấp vốn.

### Chương 5 · Kết luận

**Trang 19 · Kết luận (60 giây)**

> Tóm lại, em đã xây dựng pipeline từ TXT tới PostgreSQL chạy bằng một lệnh, giữ đủ lịch sử, chạy lại an toàn, đạt mọi cổng kiểm thử và trả lời đủ năm câu hỏi.
>
> Hạn chế em nói thẳng: **kết quả trên bộ mẫu một máy, không suy ra hiệu năng bộ đầy đủ**; load_date là thời điểm đến giả lập; đối chứng FR-14 chỉ so với bảng ghi đè, một mô hình chiều có lưu lịch sử cũng giữ được bản cũ. Hướng phát triển: chạy bộ đầy đủ với hạ tầng đã có sẵn, tối ưu Gold, và xây mô hình dự báo vỡ nợ trên đặc trưng lấy từ PIT.

**Trang 20 · Demo và hỏi đáp**

> Em xin demo nhanh hệ thống. *(Theo kịch bản demo bên dưới.)* Em cảm ơn thầy cô đã lắng nghe và mong nhận câu hỏi.

## Kịch bản demo (khoảng 5 phút)

**Chuẩn bị trước buổi trình bày** (ít nhất 10 phút trước):

```bash
cd ~/projects/mortgage-datavault
make up            # bật stack; đợi các service healthy
make status        # 29 quý và CORR1 phải SUCCESS đủ 6 tầng
```

Mở sẵn: Airflow UI `http://localhost:8080` (tài khoản trong `.env`), một terminal ở thư mục repo, notebook đã chạy (`make notebook-ui`, URL kèm token in ở terminal). Tắt thông báo trên máy. Không mở file TXT hay bảng có mã khoản vay trên màn hình: video và slide chỉ được có số tổng hợp (C7).

| Bước | Thời gian | Thao tác | Nói |
| --- | ---: | --- | --- |
| 1 | 45 giây | Airflow UI: danh sách 6 DAG `layer_*` | "Mỗi tầng một DAG, chạy định kỳ và khi tầng trên xong." |
| 2 | 45 giây | Terminal: `make status` | "Bảng điều khiển ghi từng lần chạy: 29 quý cộng đợt sửa CORR1 đều thành công ở 6 tầng." |
| 3 | 90 giây | Terminal: chạy truy vấn FR-14 bên dưới | "Đây là bằng chứng giữ lịch sử." (giải thích ba kết quả) |
| 4 | 60 giây | JupyterLab: biểu đồ Q1 và Q4 | "Notebook đọc mart PostgreSQL, trả lời năm câu hỏi." |
| 5 | 30 giây | Mở `experiments/results/` | "Kết quả thô của năm thực nghiệm, mỗi file gắn với digest code lúc đo." |

**Truy vấn FR-14** (chép vào `demo.sql`, chạy bằng lệnh ở cuối). Chỉ in số tổng hợp, không in mã khoản vay:

```sql
-- 1. Satellite giữ cả bản gốc và bản sửa của 20 khoản vay
WITH c AS (SELECT LOAN_HK FROM raw_vault.sat_loan_origination
           WHERE record_source = 'freddiemac.sflld.correction_1')
SELECT s.record_source, COUNT(*) AS so_phien_ban, ROUND(AVG(CAST(s.credit_score AS INT)), 1) AS diem_tb
FROM raw_vault.sat_loan_origination s JOIN c ON c.LOAN_HK = s.LOAN_HK
GROUP BY s.record_source;

-- 2. PIT trước và sau đợt sửa trả giá trị cũ và mới
WITH c AS (SELECT LOAN_HK FROM raw_vault.sat_loan_origination
           WHERE record_source = 'freddiemac.sflld.correction_1')
SELECT p.AS_OF_DATE, COUNT(*) AS khoan_vay, ROUND(AVG(CAST(s.credit_score AS INT)), 1) AS diem_tb
FROM business_vault.pit_loan_monthly p JOIN c ON c.LOAN_HK = p.LOAN_HK
JOIN raw_vault.sat_loan_origination s
  ON s.LOAN_HK = p.SAT_LOAN_ORIGINATION_PK AND s.load_date = p.SAT_LOAN_ORIGINATION_LDTS
GROUP BY p.AS_OF_DATE ORDER BY p.AS_OF_DATE DESC LIMIT 3;

-- 3. Bảng đối chứng ghi đè chỉ còn giá trị mới
WITH c AS (SELECT LOAN_HK FROM raw_vault.sat_loan_origination
           WHERE record_source = 'freddiemac.sflld.correction_1')
SELECT COUNT(*) AS dong, ROUND(AVG(CAST(b.credit_score AS INT)), 1) AS diem_tb
FROM baseline.baseline_dim_loan_overwrite b JOIN c ON c.LOAN_HK = b.LOAN_HK;
```

```bash
docker compose cp demo.sql spark-thrift:/tmp/demo.sql
docker compose exec -T spark-thrift /opt/spark/bin/beeline -u jdbc:hive2://localhost:10000 \
  -n lakehouse --silent=true -f /tmp/demo.sql
```

Kết quả mong đợi trên bộ mẫu (đã chạy thử 06/11/2026):

| Truy vấn | Kết quả | Nói |
| --- | --- | --- |
| 1 | Bản gốc: 20 phiên bản, điểm TB 747,2 · bản sửa: 20 phiên bản, điểm TB 767,2 | "Cả hai phiên bản cùng tồn tại; Satellite không ghi đè." |
| 2 | 2026-05-01: 767,2 (20 khoản vay) · 2026-04-01: 743,7 | "Hỏi trạng thái trước đợt sửa vẫn ra giá trị cũ; sau đợt sửa ra giá trị mới." |
| 3 | 20 dòng, điểm TB 767,2 | "Bảng ghi đè chỉ còn giá trị mới, giá trị cũ mất hẳn." |

Ở truy vấn 2, mốc 2026-04-01 chỉ có những khoản vay còn hoạt động tại tháng đó (7 trong 20), nên trung bình khác 747,2; điều cần chỉ ra là giá trị trước mốc sửa là giá trị gốc.

**Phương án dự phòng:** nếu stack không lên kịp, chiếu video demo quay sẵn; nếu truy vấn chậm, chụp sẵn ảnh kết quả ba truy vấn ở bảng trên.

## Câu hỏi vấn đáp thường gặp

| Câu hỏi | Ý trả lời ngắn | Mở khi cần |
| --- | --- | --- |
| Vì sao chọn Data Vault mà không làm star schema trực tiếp? | Dữ liệu bị sửa ở đợt sau; star schema ghi đè mất bản cũ, Data Vault giữ mọi phiên bản và nguồn gốc (FR-14, demo). Star schema vẫn có ở lớp Gold để phân tích. SCD2 cũng giữ được lịch sử, đồ án không khẳng định Data Vault luôn tốt hơn | Báo cáo 1.4, 4.10 |
| Sao không dùng Delta time travel thay Data Vault? | Time travel là lịch sử vật lý của bảng, bị dọn khi vacuum, không gắn với thời điểm nghiệp vụ hay nguồn giao. Satellite lưu lịch sử nghiệp vụ có `load_date`, `record_source`, giữ vĩnh viễn | Báo cáo 2.4 |
| `hash_diff` hoạt động thế nào? | Băm SHA-256 các thuộc tính của Satellite; dòng mới chỉ được chèn khi hash khác phiên bản gần nhất. Null thay bằng `^^` để `('A', null)` khác `(null, 'A')` | Báo cáo 4.5, 4.6 |
| Vì sao tách Satellite theo tốc độ thay đổi? | Thuộc tính ít đổi (quá hạn) không bị nhân bản theo dư nợ đổi hằng tháng: ít hơn 94% số dòng, truy vấn lịch sử nhanh hơn 2,3 lần. Trên Parquet không tiết kiệm dung lượng (TN6) | Báo cáo 5.6 |
| `load_date` khác `reporting_period` thế nào? | `load_date` là thời điểm dữ liệu vào kho (giả lập: ngày 1 tháng sau), `reporting_period` là tháng nghiệp vụ. Một kỳ có 3 tháng nên có 3 `load_date`, tránh trùng khóa Satellite | Báo cáo 2.3, 4.3 |
| PIT giải quyết vấn đề gì? | Lấy trạng thái tại một mốc bằng equi-join thay vì join theo `<=` rồi xếp hạng; nhanh hơn 5,6 lần khi quét mọi mốc (TN4) | Báo cáo 4.7, 5.5 |
| Nạp lại cùng một kỳ hai lần thì sao? | Bronze và quality ghi đè đúng lát kỳ; Satellite bỏ qua dòng có `load_date` không mới hơn phiên bản đã có; kết quả 0 dòng mới (AC-02, kiểm ở C2) | Báo cáo 4.3, 4.6 |
| Freddie Mac đổi tên cột thì xử lý thế nào? | Vị trí và tên cột khai báo ở `conf/schema/`; đổi tên chỉ sửa cấu hình, không sửa code. Có test C1 kiểm điều này | Báo cáo 4.2 |
| Vì sao không đọc TXT bằng reader CSV? | CSV mặc định lấp hoặc cắt dòng sai số trường mà không báo (0/20 trong TN7); tách thủ công giữ được bằng chứng và gắn lý do lỗi theo luật | Báo cáo 4.2 |
| Có chạy được bộ đầy đủ không? | Hạ tầng đã có (`docs/chay-historical.md`) và đã nạp thử tới Raw Vault, nhưng phạm vi nghiệm thu chốt ở bộ mẫu vì giới hạn ổ đĩa (R-37, R-38). Số đo bộ mẫu không suy ra hiệu năng bộ đầy đủ | Review R-37, R-38 |
| Kết quả thực nghiệm có tin được không? | Mỗi cấu hình 3 lần đo, báo trung vị và min–max; mỗi thực nghiệm có phép kiểm đúng; kết quả gắn digest code; một lượt có lỗi được đo lại và ghi lại công khai (R-39) | Báo cáo 5.2, R-39 |
| Hệ thống xử lý lỗi giữa chừng thế nào? | Mỗi tầng ghi trạng thái vào bảng điều khiển, giữ lease, thử lại có giới hạn; export dùng transaction nên lỗi không làm hỏng mart đang phục vụ | Báo cáo 4.8, 4.9 |

## Lưu ý khi trình bày

- Mở đầu bằng bài toán, không mở đầu bằng công nghệ. Người nghe cần biết "giải quyết cái gì" trước "dùng gì".
- Mỗi con số trên slide đều có nguồn trong báo cáo; nếu không nhớ, nói "trong báo cáo mục ..." thay vì đoán.
- Nói rõ hai kết quả trái giả thuyết (TN6, reader CSV có thể phát hiện lỗi khi cấu hình cột lỗi): đó là điểm cộng về tính trung thực.
- Không dùng từ "chứng minh Data Vault tốt hơn"; dùng "trong bài toán này, Data Vault giữ được lịch sử mà bảng ghi đè làm mất".
- Tập trước với đồng hồ; dừng ở cuối mỗi chương 1–2 giây để người nghe theo kịp.
