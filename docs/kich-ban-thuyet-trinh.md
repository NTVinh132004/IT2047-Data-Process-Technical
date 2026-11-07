# Kịch bản thuyết trình

Kịch bản cho bộ slide 20 trang (`data/reports/sample-report/bao-cao-sample.pptx`, sinh bằng `uv run python -m scripts.build_sample_slides`). Cách mở slide và tái sinh: [huong-dan-slide.md](huong-dan-slide.md). Số liệu lấy từ [báo cáo](bao-cao-do-an.md); khi được hỏi chi tiết, mở mục báo cáo ghi trong ngoặc.

**Cách dùng tài liệu này.** Mỗi trang có bốn phần: *Chỉ vào* (vùng trên slide cần trỏ khi nói), *Lời nói* (gợi ý để nói tự nhiên, không đọc nguyên văn; câu **in đậm** là ý bắt buộc), *Ví dụ* (khi khái niệm khó, dùng ví dụ để người nghe hình dung), *Nếu bị hỏi ngay* (câu hỏi hay bị chen vào ở đúng trang đó). Mục 4 có định nghĩa nghiệp vụ và công thức; mục 5 có câu hỏi vấn đáp theo chủ đề; mục 6 là bảng thuật ngữ.

## 1. Phân bổ thời gian

| Phần | Trang | Thời gian | Mục đích |
| --- | --- | ---: | --- |
| Mở đầu | 1–4 | 3 phút | Người nghe hiểu bài toán trước khi nghe giải pháp |
| Chương 1 | 5–7 | 3 phút | Medallion, bảng Delta và Data Vault: đủ để theo được chương 3 |
| Chương 2 | 8–9 | 2 phút 30 | Mỗi vấn đề dữ liệu dẫn tới một quyết định thiết kế |
| Chương 3 | 10–13 | 5 phút | Trọng tâm kỹ thuật xử lý dữ liệu |
| Chương 4 | 14–18 | 5 phút | Bằng chứng: kiểm chứng, thực nghiệm, kết quả phân tích |
| Chương 5 | 19 | 1 phút | Kết luận và hạn chế, nói thẳng |
| Demo | 20 | 5 phút | Chứng minh hệ thống chạy thật và giữ được lịch sử |
| **Tổng** | | **khoảng 24 phút** | |

**Nếu bị giới hạn 15 phút:** nói lướt trang 5 và 7, giữ trang 6 (1 phút 30); trang 12–13 mỗi trang 40 giây; gộp trang 15–16 (2 phút); chiếu video demo 2 phút thay vì demo trực tiếp.

**Nếu bị giới hạn 10 phút:** chỉ giữ trang 1, 3, 9, 10, 11, 14, 16, 19 và kết quả FR-14 trong demo (ảnh chụp sẵn).

## 2. Câu mở, câu chuyển và cách xử lý câu hỏi

- **Câu mở** (trang 1): giới thiệu tên, đề tài, rồi một câu về bài toán: "dữ liệu khoản vay đến theo đợt, có lỗi và bị sửa, em xây hệ thống giữ được toàn bộ lịch sử đó và vẫn trả lời được các câu hỏi rủi ro tín dụng."
- **Câu chuyển giữa các chương** (đã ghi cuối mỗi chương bên dưới): mỗi câu trả lời câu hỏi "vì sao phải nghe tiếp phần sau".
- **Khi bị hỏi giữa chừng:** trả lời ngắn trong 1–2 câu; nếu câu hỏi thuộc trang sau, nói "em xin trả lời ở trang ... ngay sau đây".
- **Khi không chắc câu trả lời:** không đoán. Nói "phần này em ghi trong báo cáo mục ..., em xin phép kiểm lại" hoặc "em chưa đo điều này; theo em hiểu thì ..., nhưng đó là suy luận, chưa có số đo".
- **Câu kết** (trang 19–20): nhắc lại một câu giá trị chính (giữ lịch sử, chạy lại an toàn, có số đo) rồi mời câu hỏi.

## 3. Lời nói theo từng trang

### Mở đầu

**Trang 1 · Bìa (20 giây)**

*Lời nói:*
> Em xin chào thầy cô. Em là Nguyễn Thế Vĩnh, MSHV 26848266. Đề tài của em là xây dựng Data Lakehouse kết hợp Data Vault 2.0 trên Apache Spark cho phân tích rủi ro tín dụng khoản vay thế chấp, dùng dữ liệu công khai của Freddie Mac. Nói ngắn gọn: dữ liệu khoản vay đến theo đợt, có lỗi và có thể bị sửa; em xây hệ thống giữ được toàn bộ lịch sử đó và vẫn trả lời được các câu hỏi rủi ro tín dụng.

**Trang 2 · Lý do chọn đề tài (50 giây)**

*Chỉ vào:* ba cột, lần lượt trái sang phải; cuối cùng là dòng chữ xanh dưới cùng.

*Lời nói:*
> Dữ liệu tín dụng có ba đặc điểm khó. Thứ nhất, nó **đến theo đợt**: mỗi khoản vay có một dòng trạng thái mỗi tháng, nên hệ thống phải nạp tăng dần, không thể nạp lại toàn bộ mỗi lần. Thứ hai, nó **có lỗi và có thể bị sửa** ở đợt sau; riêng Release 47 tháng 7/2026 Freddie Mac còn đổi tên cột. Thứ ba, kiểm toán cần **truy vết**: một khoản vay ở trạng thái nào tại tháng X, theo dữ liệu của đợt nạp nào.
>
> **Một bảng phẳng hay star schema ghi đè sẽ mất lịch sử khi dữ liệu bị sửa.** Vì vậy em khảo sát Data Vault 2.0, một mô hình được thiết kế để lưu lịch sử, đặt trên kiến trúc Lakehouse.

*Nếu bị hỏi ngay:* "Freddie Mac là gì?" — Freddie Mac là doanh nghiệp được Chính phủ Mỹ bảo trợ, mua lại khoản vay thế chấp từ ngân hàng; họ công bố dữ liệu từng khoản vay (Single-Family Loan-Level Dataset) để nghiên cứu rủi ro tín dụng.

**Trang 3 · Bài toán (50 giây)**

*Chỉ vào:* ô Đầu vào → Xử lý → Đầu ra; rồi dòng Q1–Q5 phía dưới.

*Lời nói:*
> Bài toán cụ thể: **đầu vào** là hai file TXT, orig và perf, gồm 50.000 khoản vay và gần 1,93 triệu dòng tháng. **Yêu cầu xử lý** là nạp tăng dần theo kỳ, giữ đủ lịch sử, chạy lại an toàn và chặn dòng lỗi kỹ thuật. **Đầu ra** là kho Data Vault có lịch sử, các mart trên PostgreSQL và notebook phân tích.
>
> Đầu ra phải trả lời được năm câu hỏi rủi ro tín dụng ở dưới: quá hạn theo thời gian, ảnh hưởng của điểm tín dụng và tỷ lệ vay, khác biệt theo bang và bên bán, kết cục sau hoãn trả thời COVID, và trả trước hạn. Em dùng chính năm câu này để kiểm tra kết quả ở chương 4.

*Nếu bị hỏi ngay:* "Chạy lại an toàn nghĩa là gì?" — chạy lại một kỳ bất kỳ, kể cả kỳ cũ, không làm thay đổi số dòng ở bảng nào; hệ thống gọi là idempotent (AC-02).

**Trang 4 · Mục tiêu và phạm vi (40 giây)**

*Chỉ vào:* cột Mục tiêu, rồi dòng "Ngoài phạm vi" ở cột Phạm vi.

*Lời nói:*
> Bốn mục tiêu, mỗi mục tiêu đo được bằng tiêu chí nghiệm thu, không bằng nhận xét. Về phạm vi, em làm trên **bộ mẫu** vintage 2019, chạy trên một máy RAM 12 GB. Bộ đầy đủ 8,2 GB, mô hình học máy, streaming và cloud nằm ngoài phạm vi; em sẽ nói lại ở phần hạn chế.

*Nếu bị hỏi ngay:* "Sao không làm bộ đầy đủ?" — em đã thử nạp bộ đầy đủ tới tầng Raw Vault, nhưng ổ đĩa không đủ chỗ cho cả dữ liệu lẫn các lần chạy thực nghiệm; em chốt phạm vi ở bộ mẫu và ghi rõ thành hạn chế (R-37, R-38). Hạ tầng chạy bộ đầy đủ vẫn có trong repo.

*Chuyển ý:* "Trước khi vào thiết kế, em điểm qua ba khái niệm nền."

### Chương 1 · Cơ sở lý thuyết và công nghệ

**Trang 5 · Lakehouse và Medallion (40 giây)**

*Chỉ vào:* ba ô Bronze → Silver → Gold; dòng chữ xanh phía dưới.

*Lời nói:*
> Lakehouse kết hợp kho dữ liệu với data lake: dữ liệu nằm ở dạng file mở, nhưng vẫn có bảng, giao dịch và SQL như kho dữ liệu. Medallion tổ chức dữ liệu qua ba lớp: **Bronze** giữ nguyên nguồn, **Silver** làm sạch và tích hợp, **Gold** phục vụ phân tích. **Trong đồ án, lớp Silver chính là Data Vault.** Mọi tầng đều lưu dưới dạng bảng Delta trên ổ đĩa cục bộ.

**Trang 6 · Delta Lake và bảng Delta (70 giây)**

*Chỉ vào:* cây thư mục bên trái (dòng `_delta_log`, dòng `"predicate"`, các thư mục `period=`), rồi năm ý bên phải.

*Lời nói:*
> Bảng Delta không phải một định dạng file mới. **Dữ liệu vẫn là file Parquet nén theo cột; Delta thêm một thư mục `_delta_log` ghi lại từng lần thay đổi.** Bên trái là bảng `bronze.perf` thật của đồ án: 29 thư mục, mỗi kỳ một thư mục, và 41 commit trong nhật ký. Mỗi commit là một file JSON liệt kê file nào được thêm, file nào bị bỏ.
>
> Nhờ nhật ký này, Delta có giao dịch ACID: người đọc luôn thấy một phiên bản hoàn chỉnh, job chết giữa chừng không để lại bảng dở. **Tính năng em dùng nhiều nhất là `replaceWhere`**: commit thứ hai ghi rõ "chỉ thay dữ liệu của kỳ 2019Q1", nên chạy lại một kỳ chỉ thay đúng lát đó, không bị trùng. Delta còn cho xem lịch sử bảng và quay về phiên bản cũ bằng `RESTORE`; em dùng nó trong thực nghiệm TN2.
>
> Cần phân biệt: lịch sử của Delta là lịch sử vật lý của bảng, có thể bị dọn. Lịch sử nghiệp vụ, tức giá trị nào đúng tại tháng nào, theo đợt nạp nào, do Satellite của Data Vault giữ.

*Ví dụ:* 29 kỳ nhưng 41 commit, vì có những kỳ được chạy lại trong kiểm thử; mỗi lần chạy lại là một commit mới thay đúng lát của kỳ đó, tổng số dòng không đổi.

*Nếu bị hỏi ngay:* "Parquet khác TXT thế nào?" — Parquet lưu theo cột và nén, nên nhỏ hơn và đọc nhanh hơn: file perf 211 MiB dạng TXT còn 49 MiB dạng Parquet. Spark chỉ cần đọc những cột và những thư mục cần thiết.

**Trang 7 · Data Vault 2.0 (60 giây)**

*Chỉ vào:* bốn cột Hub, Link, Satellite, PIT; dòng chữ xanh dưới cùng.

*Lời nói:*
> Data Vault tách dữ liệu thành bốn loại đối tượng. **Hub** giữ danh sách khóa nghiệp vụ, ví dụ mã khoản vay, mỗi khóa một dòng. **Link** giữ quan hệ giữa các khóa, ví dụ khoản vay với bên bán. **Satellite** giữ thuộc tính có lịch sử, ví dụ dư nợ, trạng thái quá hạn. **PIT** là bảng con trỏ để lấy nhanh trạng thái tại một mốc thời gian.
>
> **Điểm cốt lõi: Satellite chỉ thêm dòng khi thuộc tính thay đổi, phát hiện bằng hash_diff, và không bao giờ sửa hay xóa.** Nhờ đó mọi phiên bản đều còn. Quy tắc nghiệp vụ không nằm ở đây mà ở Business Vault, nên đổi luật không phải nạp lại dữ liệu gốc.

*Nếu bị hỏi ngay:* "Khác star schema ở đâu?" — star schema tối ưu cho truy vấn phân tích; Data Vault tối ưu cho việc nạp tăng dần và giữ lịch sử. Đồ án dùng cả hai: Data Vault ở Silver để lưu, star schema ở Gold để phân tích.

*Chuyển ý:* "Vì sao thiết kế như vậy? Câu trả lời nằm ở đặc điểm của chính dữ liệu."

### Chương 2 · Phân tích hiện trạng và dữ liệu

**Trang 8 · Bộ dữ liệu (50 giây)**

*Chỉ vào:* ba thẻ số; ba dòng mô tả file; dòng CORR1 dưới cùng.

*Lời nói:*
> Bộ mẫu có 50.000 khoản vay, 1.934.614 dòng khoản vay–tháng, trải 87 tháng từ 01/2019 đến 03/2026. **"Vintage 2019" nghĩa là các khoản vay giải ngân năm 2019**; file perf theo dõi chúng hằng tháng tới bản phát hành gần nhất, nên dữ liệu kéo dài tới 2026. File orig có 31 trường lúc giải ngân như điểm tín dụng, LTV, DTI. File perf có 35 trường mỗi tháng như dư nợ, số tháng quá hạn, hoãn trả. Cả hai là TXT không tiêu đề, phân tách bằng dấu gạch đứng.
>
> Để kiểm chứng việc giữ lịch sử, em tạo thêm một **đợt sửa giả lập CORR1**: 20 khoản vay được tăng điểm tín dụng thêm 20 và giảm DTI 5 điểm, nạp sau kỳ cuối.

*Nếu bị hỏi ngay:* "LTV, DTI là gì?" — LTV là tỷ lệ khoản vay trên giá trị tài sản; DTI là tỷ lệ nợ trên thu nhập của người vay. Cả hai càng cao thì rủi ro thường càng cao (xem mục 4).

**Trang 9 · Vấn đề dữ liệu → yêu cầu thiết kế (100 giây, trang quan trọng)**

*Chỉ vào:* từng hàng, ô bên trái (vấn đề) rồi mũi tên sang bên phải (giải pháp).

*Lời nói:*
> Đây là cầu nối sang thiết kế. Mỗi vấn đề dẫn tới một quyết định.
>
> Một: **file chia theo quý khởi tạo, nhưng phân tích cần theo tháng báo cáo.** Khoản vay giải ngân quý 1/2019 có dòng ở mọi tháng tới 2026, nằm chung một file. Muốn nạp dữ liệu theo từng quý báo cáo thì phải cắt lại. Nên em thêm tầng landing, phân vùng theo tháng.
>
> Hai: dữ liệu có dòng sai số trường, mã thiếu như 9999 cho điểm tín dụng, và tên cột từng đổi. Nên em đọc file dạng text rồi tự tách trường để giữ bằng chứng lỗi, chặn lỗi kỹ thuật trước khi vào Vault, và khai báo schema trong file cấu hình.
>
> Ba: **dữ liệu bị sửa ở đợt sau.** Nên Satellite chỉ thêm phiên bản, và mỗi tháng có một load_date riêng.
>
> Bốn: hệ thống phải chạy lại được khi lỗi giữa chừng. Nên mọi tầng ghi đè đúng lát của kỳ, bỏ qua dòng đã có, và chạy như job độc lập có thử lại.

*Nếu bị hỏi ngay:* "Mã thiếu 9999 có bị coi là lỗi không?" — không. Đó là mã chuẩn của Freddie Mac cho "không có giá trị"; em giữ nguyên tới Raw Vault, Business Vault mới đổi thành null. Chỉ lỗi kỹ thuật (sai số trường, sai khóa, sai kiểu) mới bị chặn.

### Chương 3 · Thiết kế hệ thống và xây dựng mô hình

**Trang 10 · Kiến trúc (60 giây)**

*Chỉ vào:* năm ô từ trái sang phải; dòng Airflow; dòng phiên bản công nghệ.

*Lời nói:*
> Dữ liệu đi từ trái sang phải: Bronze, cổng chất lượng, Silver gồm Raw Vault và Business Vault, Gold, rồi xuất sang PostgreSQL. **Mỗi tầng là một DAG Airflow độc lập**, đọc bảng điều khiển `control.layer_run` để biết kỳ nào đã sẵn sàng: tầng trên của kỳ đó đã xong và tầng mình của kỳ trước đã xong. Tầng nào lỗi thì thử lại tầng đó, tối đa 3 lần, không chạy lại tầng dưới.
>
> Công nghệ ghi dưới mỗi tầng: PySpark cho Bronze, cổng chất lượng và xuất dữ liệu; dbt cùng AutomateDV mô hình hóa Vault và Gold bằng SQL; PostgreSQL phục vụ notebook. Tất cả chạy bằng Docker Compose trên một máy.

*Nếu bị hỏi ngay:* "Sao không làm một DAG duy nhất?" — một DAG lớn thì lỗi ở giữa làm hỏng cả chuỗi và phải chạy lại từ đầu. Mỗi tầng một job, ghi trạng thái riêng, nên lỗi được khoanh vùng và các tầng đã xong không bị chạy lại (PL-01, PL-03).

**Trang 11 · Kỹ thuật nạp TXT → landing → Bronze (90 giây, trọng tâm)**

*Chỉ vào:* bốn ô từ trái sang phải (đọc phần chữ dưới mỗi ô); dòng chữ xanh đậm; dòng xám cuối.

*Lời nói:*
> Đây là kỹ thuật xử lý chính ở đầu pipeline, gồm bốn bước.
>
> Bước một: file TXT được **đọc dạng text rồi tự tách theo dấu gạch đứng**. Mọi giá trị giữ dạng chuỗi, kèm số trường thực tế của dòng và nguyên văn dòng nếu sai. Em đã đo: reader CSV mặc định của Spark không phát hiện được dòng nào trong 20 dòng sai số trường cài sẵn, vì nó tự lấp hoặc cắt trường; cách tách thủ công phát hiện đủ 20.
>
> Bước hai: landing ghi thành **bảng Delta phân vùng theo tháng**: 211 MiB TXT còn khoảng 49 MiB Parquet, 87 file, mỗi tháng một file. Việc này làm một lần cho cả 29 kỳ.
>
> Bước ba: Bronze cắt lát theo kỳ. Spark chỉ mở đúng 3 thư mục tháng của quý đó. **Cắt lát Bronze một kỳ nhanh hơn 4 đến 8 lần** so với đọc thẳng TXT. Bronze ghi đè đúng lát của kỳ bằng replaceWhere, nên chạy lại không bị trùng.
>
> Bước bốn: cổng chất lượng chia mỗi dòng vào đúng một trong ba bảng: sạch, cách ly kèm lý do, hoặc bản sao bị loại. Tổng ba bảng luôn bằng số dòng Bronze.

*Ví dụ:* kỳ 2020Q2 gồm tháng 202004–202006; điều kiện lọc trên cột phân vùng khiến Spark bỏ qua 84 thư mục tháng còn lại mà không cần đọc.

*Nếu bị hỏi ngay:*
- "Cổng chất lượng chặn những gì?" — ba luật kỹ thuật theo thứ tự: sai số trường, sai định dạng mã khoản vay, sai kiểu dữ liệu. Thêm trùng khóa: bản sao giống hệt thì giữ một, bản sao khác nội dung thì cách ly cả hai vì không biết bản nào đúng.
- "Bộ mẫu có dòng lỗi không?" — bộ mẫu sạch, 0 dòng bị cách ly. Khả năng bắt lỗi được kiểm bằng dữ liệu giả lập cài lỗi (`make smoke`, test cổng C2).

**Trang 12 · Mô hình Raw Vault (70 giây)**

*Chỉ vào:* ba Hub ở hàng trên; hai Link; khối 5 Satellite; dòng chữ xanh dưới cùng.

*Lời nói:*
> Raw Vault có 3 Hub: khoản vay, bên bán, bên quản lý khoản vay. 2 Link nối khoản vay với hai bên đó. 5 Satellite trên khoản vay, **tách theo tốc độ thay đổi**: thông tin giải ngân và tài sản gần như không đổi; dư nợ đổi mỗi tháng; trạng thái quá hạn và thông tin kết thúc ít đổi.
>
> Khóa và hash_diff dùng SHA-256 theo một quy tắc cố định. Mỗi tháng báo cáo nhận load_date là ngày 1 của tháng sau; nếu dùng một load_date cho cả quý, ba tháng của cùng khoản vay sẽ trùng khóa và Satellite mất hai trong ba tháng.

*Ví dụ (số giả lập để minh họa):* một khoản vay trong ba tháng.

| Tháng báo cáo | load_date | Dư nợ | Quá hạn | Satellite dư nợ | Satellite quá hạn |
| --- | --- | ---: | --- | --- | --- |
| 01/2020 | 01/02/2020 | 200.000 | 00 | thêm dòng | thêm dòng (lần đầu) |
| 02/2020 | 01/03/2020 | 199.500 | 00 | thêm dòng | **không thêm** (hash_diff như cũ) |
| 03/2020 | 01/04/2020 | 199.000 | 01 | thêm dòng | thêm dòng (quá hạn đổi) |

Trên bộ mẫu thật: Satellite dư nợ có 1.934.615 dòng (gần bằng số dòng perf), Satellite quá hạn chỉ 109.998 dòng (5,7%).

*Nếu bị hỏi ngay:* "Sao lại băm khóa?" — khóa băm có độ dài cố định, tính được độc lập ở mọi tầng mà không cần tra bảng khác, nên các bảng nạp song song được. Quy tắc băm chốt một lần (trim, viết hoa, null thành `^^`, nối bằng `||`) và không đổi sau khi đã nạp.

**Trang 13 · Business Vault, PIT, Gold, điều phối (60 giây)**

*Chỉ vào:* bốn cột; dòng Export dưới cùng.

*Lời nói:*
> **PIT** lưu con trỏ tới phiên bản hiệu lực tại mỗi mốc; chưa có phiên bản thì trỏ tới một dòng "ma" (ghost record), nên **mọi truy vấn trạng thái chỉ cần equi-join**. **Business Vault** tính các chỉ số nghiệp vụ: số tháng quá hạn liên tiếp, từng quá hạn 90 ngày hay chưa, vòng đời khoản vay. **Gold** dựng bảng fact theo khoản vay × tháng, năm dimension và ba mart. **Airflow** điều phối với lease và thử lại có giới hạn.
>
> Khi xuất sang PostgreSQL, em ghi vào bảng trung gian, đối soát số dòng, rồi thay dữ liệu phục vụ trong một transaction: lỗi giữa chừng không làm hỏng bản đang dùng.

*Ví dụ (tiếp ví dụ trang 12):* PIT tại mốc 01/03/2020 trỏ Satellite dư nợ tới phiên bản 01/03/2020 và Satellite quá hạn tới phiên bản 01/02/2020 (vì tháng 02 không có phiên bản mới). Truy vấn chỉ cần nối bằng đúng cặp (khoản vay, load_date) đó.

*Nếu bị hỏi ngay:* "Business Vault có được kiểm không?" — logic được đối chiếu với một chương trình Python viết riêng, đọc thẳng file TXT, không dùng chung code với pipeline: 20 khoản vay, 983 tháng, 0 sai lệch (EP-05).

*Chuyển ý:* "Thiết kế như vậy có đúng và có đáng không? Em chứng minh bằng kiểm chứng và thực nghiệm."

### Chương 4 · Triển khai thực nghiệm và đánh giá

**Trang 14 · Kiểm chứng (60 giây)**

*Chỉ vào:* ba thẻ số; đoạn FR-14; dòng AC-02.

*Lời nói:*
> Hệ thống đạt **9/9 tiêu chí nghiệm thu**. Toàn bộ **89 kiểm tra chạy lại đạt trên một bản clone sạch**, tức tải repo về thư mục mới, dựng database và lake trống, nạp lại từ đầu. Tổng dư nợ từng tháng ở Gold khớp chính xác với file TXT, 87 tháng không lệch.
>
> **Bằng chứng chính cho Data Vault là FR-14**: sau đợt sửa CORR1, Satellite có phiên bản mới cho đúng 20 khoản vay, bản cũ vẫn còn, PIT trước và sau đợt sửa trả về giá trị cũ và mới. Bảng đối chứng kiểu ghi đè chỉ còn giá trị mới. Em sẽ demo phần này ở cuối.

*Nếu bị hỏi ngay:* "89 kiểm tra gồm những gì?" — các cổng C0 đến C5 (hạ tầng, Bronze, Raw Vault, Business Vault, Gold, thực nghiệm) và unit test; mỗi cổng có kết quả lưu trong `tests/gates/results/` kèm commit.

**Trang 15 · TN1 mở rộng quy mô (60 giây)**

*Chỉ vào:* biểu đồ trái (ba cột end-to-end); biểu đồ phải, nhóm raw_vault (cột xanh dương cao nhất).

*Cách đọc biểu đồ:* chiều cao cột là trung vị 3 lần chạy; vạch đen là khoảng nhỏ nhất–lớn nhất. Biểu đồ phải tách thời gian bận của từng tầng.

*Lời nói:*
> Em chạy toàn bộ pipeline trên 25%, 50% và 100% bộ mẫu, mỗi mức ba lần, mỗi lần dựng lại môi trường từ đầu. **Dữ liệu tăng 3,9 lần nhưng thời gian chỉ tăng khoảng 11%**, từ 715 lên 795 giây. Ở quy mô mẫu, phần lớn thời gian là chi phí cố định: khởi động Spark, lập kế hoạch truy vấn, khoảng 100 câu SQL mỗi lần chạy dbt.
>
> Một phát hiện thú vị ở biểu đồ phải: tầng Raw Vault đi theo số lô chứ không theo dữ liệu. Tập 25% lại chậm nhất vì bị chia thành 6 lô, mỗi lô trả chi phí cố định; tập 100% chỉ 2 lô. Các tầng tăng theo dữ liệu là Business Vault, Gold và export. Cả 9 lần chạy đều đạt các phép đối soát.

*Nếu bị hỏi ngay:* "Vậy có kết luận về bộ đầy đủ không?" — không. Ở quy mô mẫu chi phí cố định lấn át nên chưa thấy xu hướng theo dữ liệu; bộ đầy đủ lớn gấp khoảng 36 lần cần đo riêng.

**Trang 16 · TN2, TN4, TN6 (90 giây)**

*Chỉ vào:* biểu đồ trái (đường cam đi lên, đường xanh nằm ngang); biểu đồ phải (cột cam cao gấp nhiều lần cột xanh ở nhóm trái); dòng TN6 dưới cùng.

*Lời nói:*
> Ba thực nghiệm cho ba quyết định Data Vault, **mỗi thực nghiệm có phép kiểm đúng** để tốc độ không che một kết quả sai.
>
> TN2, biểu đồ trái: nạp tăng dần một kỳ mới **giữ khoảng 35 giây** dù lịch sử dài ra, còn dựng lại toàn bộ tăng từ 25 lên 67 giây khi có 29 kỳ. Ở mốc 4 kỳ, dựng lại còn nhanh hơn vì lịch sử ngắn; điểm giao nằm giữa 4 và 12 kỳ. Hai cách cho đúng cùng số dòng ở mọi mốc.
>
> TN4, biểu đồ phải: lấy trạng thái mọi khoản vay ở mọi mốc qua **PIT nhanh hơn khoảng 5,6 lần** so với join trực tiếp, câu SQL ngắn hơn 6 lần, và hai cách cho cùng checksum. Hỏi một mốc thì hai cách gần ngang nhau, nên PIT có lợi nhất cho truy vấn quét nhiều mốc như dựng bảng fact.
>
> TN6, kết quả trái giả thuyết và em giữ nguyên: **tách Satellite không tiết kiệm dung lượng** trên Parquet, vì nén cột xử lý tốt giá trị lặp, còn ba bảng tách mỗi bảng phải lưu lại khóa băm. Lợi ích thật là truy vấn lịch sử quá hạn nhanh hơn khoảng 2,3 lần và mô hình rõ ràng hơn.

*Nếu bị hỏi ngay:* "Join trực tiếp chậm vì sao?" — không có PIT, mỗi (khoản vay, mốc) phải ghép với mọi phiên bản có load_date không vượt mốc rồi xếp hạng để giữ bản mới nhất; với dư nợ đổi hằng tháng, một khoản vay m tháng sinh khoảng m²/2 cặp trung gian.

**Trang 17 · Kết quả Q1–Q3 (60 giây)**

*Chỉ vào:* biểu đồ trái, đỉnh đường đỏ đầu 2021; biểu đồ phải, cột 620–679; dòng chú thích dưới (Q3).

*Cách đọc biểu đồ:* biểu đồ trái là tỷ lệ quá hạn theo tháng, ba đường cho 30–59, 60–89 và 90+ ngày; biểu đồ phải là tỷ lệ 90+ gộp toàn thời gian theo nhóm điểm tín dụng.

*Lời nói:*
> Câu 1: tỷ lệ quá hạn 90 ngày trở lên tăng mạnh từ giữa 2020, **đỉnh 3,57% vào tháng 2/2021**, tức 1.073 trên 30.067 khoản vay hợp lệ, rồi giảm dần còn 0,94% ở tháng 3/2026. Câu 2: nhóm điểm tín dụng 620–679 có tỷ lệ 3,49%, nhóm từ 780 chỉ 0,38%. Câu 3: trong các bang có đủ quan sát, New Jersey 2,52%, Nevada 2,04%, New York 1,91% cao nhất.
>
> **Đây là thống kê mô tả trên bộ mẫu, không phải quan hệ nhân quả.**

*Nếu bị hỏi ngay:* "Nhóm dưới 620 sao lại thấp hơn 620–679?" — nhóm đó chỉ có 1.744 quan sát, quá ít để rút xu hướng; em ghi rõ điều này trong báo cáo.

**Trang 18 · Kết quả Q4–Q5 (50 giây)**

*Chỉ vào:* biểu đồ trái (cột RECOVERED và PREPAID dài nhất); biểu đồ phải (đỉnh đường cam đầu 2021, và điểm cao bất thường đầu 2019).

*Lời nói:*
> Câu 4: 3.310 khoản vay từng được hoãn trả thời COVID. Xét 12 tháng sau lần hoãn trả cuối: 43% hồi phục, 36% trả trước hạn, 16% vỡ nợ lần đầu. Câu 5: tỷ lệ trả trước hạn năm hóa **đạt đỉnh 52,8% vào tháng 3/2021**, giai đoạn lãi suất thấp. Dữ liệu không ghi lý do trả trước, nên em không khẳng định tất cả là tái cấp vốn.

*Nếu bị hỏi ngay:* "Điểm cao 73% đầu 2019 là gì?" — tháng 01/2019 chỉ có 30 khoản vay đang hoạt động, mẫu số quá nhỏ nên tỷ lệ năm hóa rất nhạy; không phải mức điển hình.

### Chương 5 · Kết luận

**Trang 19 · Kết luận (60 giây)**

*Chỉ vào:* ba cột lần lượt.

*Lời nói:*
> Tóm lại, em đã xây dựng pipeline từ TXT tới PostgreSQL chạy bằng một lệnh, giữ đủ lịch sử, chạy lại an toàn, đạt mọi cổng kiểm thử và trả lời đủ năm câu hỏi.
>
> Hạn chế em nói thẳng: **kết quả trên bộ mẫu một máy, không suy ra hiệu năng bộ đầy đủ**; load_date là thời điểm đến giả lập; đối chứng FR-14 chỉ so với bảng ghi đè, một mô hình chiều có lưu lịch sử cũng giữ được bản cũ; phân tích là mô tả, không nhân quả.
>
> Hướng phát triển: chạy bộ đầy đủ với hạ tầng đã có sẵn, tối ưu Gold nạp tăng dần, và xây mô hình dự báo vỡ nợ 12 tháng trên đặc trưng lấy từ PIT, vì PIT bảo đảm không dùng thông tin tương lai.

**Trang 20 · Demo và hỏi đáp**

> Em xin demo nhanh hệ thống. *(Theo kịch bản demo bên dưới.)* Em cảm ơn thầy cô đã lắng nghe và mong nhận câu hỏi.

## 4. Định nghĩa nghiệp vụ và công thức

| Khái niệm | Định nghĩa trong đồ án | Nguồn |
| --- | --- | --- |
| Khoản vay hợp lệ (mẫu số) | Khoản vay đang hoạt động trong tháng và có mã quá hạn hợp lệ (hai chữ số hoặc `RA`) | `mart_delinquency.sql` |
| Quá hạn 30–59 / 60–89 / 90+ ngày | Mã `01` / `02` / `03` trở lên hoặc `RA`; `00` là đúng hạn, `XX` là không xác định | `bsat_loan_risk.sql` |
| Tỷ lệ gộp nhiều tháng | Cộng tử số và mẫu số rồi chia, không lấy trung bình các tỷ lệ | Báo cáo 6.1 |
| Cohort hoãn trả COVID | Khoản vay có ít nhất một tháng mã hỗ trợ `F` (hoãn trả) trong 03/2020–12/2021 | `mart_covid_forbearance.sql` |
| Kết cục sau hoãn trả | Xét 12 tháng sau tháng `F` cuối cùng, ưu tiên: vỡ nợ lần đầu → trả trước → sửa đổi khoản vay; nếu không có, mã `00` ở cuối cửa sổ là hồi phục; thiếu quan sát là UNKNOWN | Báo cáo 6.5 |
| SMM (tỷ lệ trả trước tháng) | Dư nợ của khoản vay trả hết trước hạn (mã kết thúc `01`) chia dư nợ đang hoạt động tháng trước | `mart_prepayment.sql` |
| CPR (tỷ lệ trả trước năm hóa) | CPR = 1 − (1 − SMM)^12 | Báo cáo 6.6 |
| LTV | Khoản vay chia giá trị tài sản thế chấp, tính bằng % | Từ điển dữ liệu |
| DTI | Tổng nợ hằng tháng chia thu nhập hằng tháng của người vay, tính bằng % | Từ điển dữ liệu |
| Điểm tín dụng | Điểm FICO lúc giải ngân (300–850); `9999` là thiếu | `conf/schema/orig.yml` |

## 5. Kịch bản demo (khoảng 5 phút)

### 5.1. Chuẩn bị (ít nhất 15 phút trước)

```bash
cd ~/projects/mortgage-datavault
make up            # bật stack; khoảng 1–2 phút, đợi các service healthy
make status        # 29 quý và CORR1 phải SUCCESS đủ 6 tầng
grep AIRFLOW_ADMIN .env   # tài khoản đăng nhập Airflow (không chiếu lên màn hình)
```

Mở sẵn bốn thứ, mỗi thứ một tab hoặc cửa sổ:

1. Airflow UI `http://localhost:8080`, đã đăng nhập, ở trang danh sách DAG.
2. Terminal ở thư mục repo, chữ cỡ lớn (Ctrl + `+`), đã có file `demo.sql` (mục 5.3).
3. JupyterLab (`make notebook-ui`, mở URL kèm token), đang ở notebook đã chạy, cuộn sẵn tới biểu đồ Q1.
4. File Explorer ở `experiments/results/`.

Kiểm tra: tắt thông báo trên máy; chế độ ngủ của Windows đang tắt; không mở file TXT, bảng có mã khoản vay hay file `.env` trên màn hình (video và slide chỉ được có số tổng hợp, C7).

### 5.2. Các bước

| Bước | Thời gian | Thao tác | Màn hình sẽ thấy | Nói |
| --- | ---: | --- | --- | --- |
| 1 | 45 giây | Airflow: danh sách DAG, rồi bấm vào `layer_raw_vault` → tab Grid | 6 DAG `layer_*`; ô xanh là lần chạy thành công | "Mỗi tầng một DAG, chạy định kỳ 5 phút và khi tầng trên xong. Đây là các lần chạy của tầng Raw Vault." |
| 2 | 45 giây | Terminal: `make status` | Bảng các kỳ, mỗi kỳ 6 tầng SUCCESS | "Bảng điều khiển ghi từng lần chạy: 29 quý cộng đợt sửa CORR1 đều thành công ở 6 tầng." |
| 3 | 90 giây | Terminal: chạy `demo.sql` (mục 5.3) | Ba bảng kết quả nhỏ | "Đây là bằng chứng giữ lịch sử." Giải thích theo bảng kết quả mong đợi bên dưới |
| 4 | 60 giây | JupyterLab: biểu đồ Q1, cuộn tới Q4 | Đường quá hạn tăng vọt 2020–2021; cột kết cục COVID | "Notebook đọc mart PostgreSQL, trả lời năm câu hỏi." |
| 5 | 30 giây | File Explorer: `experiments/results/` | Các file CSV, PNG, `manifest.json` | "Kết quả thô của năm thực nghiệm, mỗi file gắn với digest code lúc đo, kiểm bằng cổng C5." |

### 5.3. Truy vấn FR-14

Chép vào file `demo.sql` ở thư mục repo. Chỉ in số tổng hợp, không in mã khoản vay:

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

Chạy:

```bash
docker compose cp demo.sql spark-thrift:/tmp/demo.sql
docker compose exec -T spark-thrift /opt/spark/bin/beeline -u jdbc:hive2://localhost:10000 \
  -n lakehouse --silent=true -f /tmp/demo.sql
```

Kết quả mong đợi trên bộ mẫu (đã chạy thử 06/11/2026; mất khoảng 20–40 giây):

| Truy vấn | Kết quả | Nói |
| --- | --- | --- |
| 1 | Bản gốc: 20 phiên bản, điểm TB 747,2 · bản sửa: 20 phiên bản, điểm TB 767,2 | "Cả hai phiên bản cùng tồn tại; Satellite không ghi đè. Điểm sửa tăng đúng 20." |
| 2 | 2026-05-01: 767,2 (20 khoản vay) · 2026-04-01: 743,7 | "Hỏi trạng thái trước đợt sửa vẫn ra giá trị cũ; sau đợt sửa ra giá trị mới." |
| 3 | 20 dòng, điểm TB 767,2 | "Bảng ghi đè chỉ còn giá trị mới, giá trị cũ mất hẳn. Đó là lý do chọn Data Vault." |

Ở truy vấn 2, mốc 2026-04-01 chỉ có những khoản vay còn hoạt động tại tháng đó (7 trong 20), nên trung bình khác 747,2; điều cần chỉ ra là giá trị trước mốc sửa là giá trị gốc. Dòng chữ `null` lẫn trong kết quả là thông báo của beeline, bỏ qua.

### 5.4. Khi demo gặp sự cố

| Hiện tượng | Xử lý nhanh |
| --- | --- |
| `make up` báo trùng cổng (8080, 5432, 10000) | Stack thực nghiệm hoặc ứng dụng khác đang chiếm cổng: `scripts/experiment.sh down`, rồi `make up` lại |
| Airflow chưa hiện DAG | Đợi 30–60 giây cho dag-processor nạp DAG, tải lại trang |
| beeline treo hoặc báo không kết nối được | Thrift chưa sẵn sàng: `docker compose ps` xem `spark-thrift` đã `healthy` chưa; đợi thêm 30 giây |
| Notebook báo lỗi kết nối PostgreSQL | Chưa `make up`, hoặc PostgreSQL chưa healthy; mở bản đã chạy sẵn (không chạy lại cell) |
| Mọi thứ đều chậm | Chuyển sang video demo quay sẵn hoặc ảnh chụp ba kết quả truy vấn |

## 6. Câu hỏi vấn đáp theo chủ đề

### 6.1. Lựa chọn kiến trúc và công nghệ

| Câu hỏi | Ý trả lời | Mở khi cần |
| --- | --- | --- |
| Vì sao chọn Data Vault mà không làm star schema trực tiếp? | Dữ liệu bị sửa ở đợt sau; star schema ghi đè mất bản cũ, Data Vault giữ mọi phiên bản và nguồn gốc (FR-14, demo). Star schema vẫn có ở Gold để phân tích. SCD2 cũng giữ được lịch sử, đồ án không khẳng định Data Vault luôn tốt hơn | Báo cáo 1.4, 4.10 |
| Sao không dùng Delta time travel thay Data Vault? | Time travel là lịch sử vật lý của bảng, bị dọn khi vacuum, không gắn với thời điểm nghiệp vụ hay nguồn giao. Satellite lưu lịch sử nghiệp vụ có `load_date`, `record_source`, giữ vĩnh viễn | Báo cáo 2.4; slide 6 |
| Dữ liệu mẫu chỉ 222 MB, cần Spark làm gì? | Thiết kế để mở rộng tới bộ đầy đủ 8,2 GB (khoảng 36 lần); Spark cũng là nền chạy Delta và dbt qua Thrift Server. TN1 cho thấy ở quy mô mẫu, chi phí cố định của Spark chiếm phần lớn, em ghi rõ điều này | Báo cáo 5.3 |
| Vì sao dùng dbt và AutomateDV? | dbt cho mô hình hóa bằng SQL có kiểm thử, phụ thuộc, tài liệu; AutomateDV là package chuẩn sinh Hub, Link, Satellite theo Data Vault, tránh tự viết sai chuẩn | Báo cáo 4.5–4.6 |
| AutomateDV có chạy thẳng trên Spark không? | Không hoàn toàn: bản Databricks dùng `QUALIFY`, Spark mã nguồn mở không có. Em viết lại ba macro hub, link, sat bằng subquery, giữ nguyên logic, và ghi thành ngoại lệ DEV-01 | `principles.md` mục 7 |
| Vì sao Airflow chia mỗi tầng một DAG? | Lỗi được khoanh vùng theo tầng và kỳ; tầng đã xong không chạy lại; các tầng cần thứ tự thời gian xử lý đúng thứ tự; có lease và thử lại tối đa 3 lần | Báo cáo 4.9 |
| Tại sao xuất sang PostgreSQL mà không đọc thẳng Delta? | Người phân tích và notebook làm việc với PostgreSQL quen thuộc hơn; mart nhỏ (khoảng 1 triệu dòng). Công bố trong một transaction để không ai đọc phải dữ liệu dở | Báo cáo 4.8 |

### 6.2. Data Vault và mô hình

| Câu hỏi | Ý trả lời | Mở khi cần |
| --- | --- | --- |
| `hash_diff` hoạt động thế nào? | Băm SHA-256 các thuộc tính của Satellite; dòng mới chỉ được chèn khi hash khác phiên bản gần nhất. Null thay bằng `^^` để `('A', null)` khác `(null, 'A')` | Báo cáo 4.5, 4.6 |
| Vì sao tách Satellite theo tốc độ thay đổi? | Thuộc tính ít đổi không bị nhân bản theo dư nợ đổi hằng tháng: ít hơn 94% số dòng, truy vấn lịch sử nhanh hơn 2,3 lần. Trên Parquet không tiết kiệm dung lượng (TN6) | Báo cáo 5.6 |
| `load_date` khác `reporting_period` thế nào? | `load_date` là thời điểm dữ liệu vào kho (giả lập: ngày 1 tháng sau), `reporting_period` là tháng nghiệp vụ. Một kỳ có 3 tháng nên có 3 `load_date`, tránh trùng khóa Satellite | Báo cáo 2.3, 4.3 |
| Sao `load_date` lại là giả lập? | Dữ liệu được tải về một lần; để mô phỏng dữ liệu đến dần theo tháng, em gán thời điểm đến là ngày 1 tháng sau. Đó là ngoại lệ DEV-03, đã ghi vào hạn chế | `principles.md` mục 7 |
| PIT giải quyết vấn đề gì? | Lấy trạng thái tại một mốc bằng equi-join thay vì join theo `<=` rồi xếp hạng; nhanh hơn 5,6 lần khi quét mọi mốc (TN4) | Báo cáo 4.7, 5.5 |
| Ghost record và zero key là gì? | Ghost record: một dòng rỗng trong mỗi Satellite để PIT trỏ tới khi chưa có phiên bản, giữ mọi join là equi-join. Zero key: khóa thay thế khi tên bên quản lý bị thiếu, để dòng vẫn vào Hub thay vì bị bỏ | Báo cáo 4.5, 4.7 |
| Hard rule và soft rule khác nhau thế nào? | Hard rule là lỗi kỹ thuật, chặn trước Vault (sai số trường, sai khóa, sai kiểu). Soft rule là luật nghiệp vụ (ngoài miền giá trị, perf không có orig), không chặn, chỉ báo cáo ở Business Vault để đổi luật không phải nạp lại | Báo cáo 3.2 |
| Dữ liệu đến trễ (một tháng cũ đến sau) thì sao? | Satellite chỉ nhận dòng có `load_date` mới hơn phiên bản đã có; theo chuẩn, dữ liệu trễ đến với `load_date` mới và thời điểm nghiệp vụ nằm trong thuộc tính. Đồ án chưa có kịch bản dữ liệu trễ thật | Báo cáo 2.3 |

### 6.3. Kỹ thuật nạp và chất lượng

| Câu hỏi | Ý trả lời | Mở khi cần |
| --- | --- | --- |
| Vì sao không đọc TXT bằng reader CSV? | CSV mặc định lấp hoặc cắt dòng sai số trường mà không báo (0/20 trong TN7). Có cấu hình cột lỗi thì phát hiện được nhưng giá trị đã bị biến đổi; tách thủ công giữ được giá trị theo vị trí và gắn lý do lỗi theo luật | Báo cáo 4.2 |
| Nạp lại cùng một kỳ hai lần thì sao? | Bronze và quality ghi đè đúng lát kỳ; Satellite bỏ qua dòng có `load_date` không mới hơn phiên bản đã có; kết quả 0 dòng mới (AC-02, kiểm ở C2) | Báo cáo 4.3, 4.6 |
| Freddie Mac đổi tên cột thì xử lý thế nào? | Vị trí và tên cột khai báo ở `conf/schema/`; đổi tên chỉ sửa cấu hình, không sửa code. Có test C1 kiểm điều này | Báo cáo 4.2 |
| Bộ mẫu không có lỗi thì sao biết cổng chất lượng hoạt động? | Kiểm bằng dữ liệu giả lập cài sẵn đủ loại lỗi (`make smoke`, test cổng C2); TN7 cũng cài 20 dòng sai số trường | Báo cáo 4.4 |
| Làm sao biết số liệu đúng? | Đối soát nhiều tầng: Bronze bằng nguồn; Bronze = sạch + cách ly + bản sao; dư nợ Gold khớp TXT 87 tháng; mart PostgreSQL bằng Delta; Business Vault khớp chương trình Python độc lập | Báo cáo 5.1 |

### 6.4. Thực nghiệm

| Câu hỏi | Ý trả lời | Mở khi cần |
| --- | --- | --- |
| Kết quả thực nghiệm có tin được không? | Mỗi cấu hình 3 lần đo, báo trung vị và min–max; mỗi thực nghiệm có phép kiểm đúng; kết quả gắn digest code; một lượt có lỗi được đo lại và ghi lại công khai (R-39) | Báo cáo 5.2, R-39 |
| Vì sao chỉ 3 lần đo? | Theo quy tắc đo đặt từ đầu (Kế hoạch mục 8); mỗi lần TN1 mất 12–15 phút vì dựng môi trường mới. Vạch min–max cho thấy độ dao động | Báo cáo 5.2 |
| Có kết quả nào không như mong đợi? | Hai: tách Satellite không tiết kiệm dung lượng (TN6); reader CSV có thể phát hiện lỗi nếu cấu hình cột lỗi (TN7). Em giữ nguyên và giải thích | Báo cáo 5.8 |
| Đo trên một máy có ảnh hưởng gì? | Không xóa được cache hệ điều hành trong WSL, nên lần đọc sau có thể nhanh hơn; không có cụm nên chưa đánh giá phân tán. Em ghi thành hạn chế | Báo cáo 5.2, 7.1 |

### 6.5. Kết quả phân tích

| Câu hỏi | Ý trả lời | Mở khi cần |
| --- | --- | --- |
| Tỷ lệ quá hạn tính trên mẫu số nào? | Khoản vay đang hoạt động có mã quá hạn hợp lệ trong tháng đó; gộp nhiều tháng thì cộng tử và mẫu rồi mới chia | Mục 4; báo cáo 6.1 |
| Có kết luận điểm tín dụng thấp gây vỡ nợ không? | Không; đây là tương quan mô tả trên bộ mẫu, chưa kiểm soát các yếu tố khác | Báo cáo 6.3 |
| Kết cục COVID có chứng minh hoãn trả hiệu quả không? | Không; phân tích hồi cứu, không có nhóm đối chứng | Báo cáo 6.5 |
| Bộ mẫu có đại diện thị trường không? | Không khẳng định; đây là bộ mẫu Freddie Mac công bố cho một vintage, kết quả chỉ mô tả bộ mẫu | Báo cáo 3.1 |

### 6.6. Phạm vi, khó khăn và quá trình làm

| Câu hỏi | Ý trả lời | Mở khi cần |
| --- | --- | --- |
| Có chạy được bộ đầy đủ không? | Hạ tầng đã có (`docs/chay-historical.md`) và đã nạp thử tới Raw Vault, nhưng phạm vi nghiệm thu chốt ở bộ mẫu vì giới hạn ổ đĩa (R-37, R-38). Số đo bộ mẫu không suy ra hiệu năng bộ đầy đủ | Review R-37, R-38 |
| Hệ thống xử lý lỗi giữa chừng thế nào? | Mỗi tầng ghi trạng thái vào bảng điều khiển, giữ lease 1 giờ, thử lại tối đa 3 lần; export dùng transaction nên lỗi không làm hỏng mart đang phục vụ | Báo cáo 4.8, 4.9 |
| Khó khăn lớn nhất là gì? | (1) Bản đầu lệch chuẩn Data Vault, phải đối chiếu tài liệu chuẩn rồi triển khai lại (R-33). (2) AutomateDV không chạy thẳng trên Spark, phải viết lại macro (R-26). (3) View làm tràn bộ nhớ Thrift Server, phải lưu staging thành bảng (R-30). (4) Thrift bị kill vì thiếu bộ nhớ, phải hạ heap (R-39) | Review R-26, R-30, R-33, R-39 |
| Bài học rút ra? | Đối chiếu chuẩn trước khi thiết kế; thử trên một kỳ trước khi chạy dài; mỗi quyết định ghi lại kèm bằng chứng; cổng kiểm thử không nới để cho qua | `principles.md` mục 5 |
| Em có dùng công cụ AI không? | Trả lời trung thực theo thực tế: em có dùng trợ lý AI hỗ trợ viết code, chạy thực nghiệm và soạn tài liệu; các quyết định phạm vi và thiết kế do em chốt; mọi kết quả được kiểm bằng test cổng và đối soát độc lập. Báo cáo ghi điều này ở phụ lục A | Báo cáo phụ lục A |

## 7. Thuật ngữ

| Thuật ngữ | Giải thích ngắn |
| --- | --- |
| Lakehouse | Kiến trúc lưu dữ liệu ở dạng file mở nhưng có bảng, giao dịch và SQL như kho dữ liệu |
| Medallion | Cách chia ba lớp Bronze (nguồn), Silver (làm sạch, tích hợp), Gold (phân tích) |
| Delta Lake / bảng Delta | Định dạng bảng: file Parquet cộng nhật ký giao dịch `_delta_log`; có ACID, `replaceWhere`, time travel |
| Parquet | Định dạng file lưu theo cột, nén tốt, đọc nhanh |
| ACID | Giao dịch toàn vẹn: hoặc ghi xong hết, hoặc như chưa ghi; người đọc không thấy trạng thái dở |
| `replaceWhere` | Ghi đè chỉ phần dữ liệu thỏa điều kiện (ví dụ một kỳ), giữ nguyên phần còn lại |
| Partition pruning | Spark bỏ qua các thư mục phân vùng không thỏa điều kiện lọc, không cần đọc |
| Hub / Link / Satellite | Khóa nghiệp vụ / quan hệ giữa khóa / thuộc tính có lịch sử |
| `hash_diff` | Mã băm các thuộc tính của Satellite, dùng để biết thuộc tính có đổi không |
| `load_date` | Thời điểm dữ liệu vào kho (đồ án: ngày 1 tháng sau tháng báo cáo, giả lập) |
| `reporting_period` | Tháng báo cáo nghiệp vụ của dòng perf |
| PIT | Point-in-time: bảng con trỏ tới phiên bản Satellite hiệu lực tại mỗi mốc |
| Ghost record | Dòng rỗng trong Satellite để PIT trỏ tới khi chưa có phiên bản |
| Business Vault | Lớp tính chỉ số nghiệp vụ từ Raw Vault, dựng lại được bất cứ lúc nào |
| Idempotent | Chạy lại bao nhiêu lần kết quả vẫn như chạy một lần |
| Quarantine (cách ly) | Bảng chứa dòng vi phạm luật kỹ thuật, kèm lý do, để sửa và nạp lại |
| DAG | Đồ thị công việc trong Airflow; đồ án có 6 DAG, mỗi tầng một DAG |
| Vintage | Năm giải ngân của khoản vay; vintage 2019 là các khoản vay giải ngân năm 2019 |
| Trung vị, min–max | Giá trị giữa của 3 lần đo; khoảng nhỏ nhất–lớn nhất |

## 8. Checklist trước buổi trình bày

- [ ] Đã điền tên giảng viên ở trang 1 (sửa trong PowerPoint) và ngày ở chân trang nếu cần.
- [ ] Đã mở PPTX trên đúng máy sẽ chiếu, kiểm phông tiếng Việt và biểu đồ; có sẵn bản PDF dự phòng.
- [ ] Đã tập trọn bài với đồng hồ ít nhất một lần.
- [ ] Đã `make up`, `make status` đủ 30 kỳ SUCCESS; Airflow, terminal, JupyterLab, thư mục kết quả mở sẵn.
- [ ] Đã chạy thử `demo.sql` một lần trong buổi đó.
- [ ] Có video demo hoặc ảnh chụp kết quả dự phòng.
- [ ] Tắt thông báo, tắt chế độ ngủ, sạc đầy pin; không mở `.env` hay dữ liệu chi tiết trên màn hình.

## 9. Lưu ý khi trình bày

- Mở đầu bằng bài toán, không mở đầu bằng công nghệ. Người nghe cần biết "giải quyết cái gì" trước "dùng gì".
- Mỗi con số trên slide đều có nguồn trong báo cáo; nếu không nhớ, nói "trong báo cáo mục ..." thay vì đoán.
- Nói rõ hai kết quả trái giả thuyết (TN6, reader CSV có thể phát hiện lỗi khi cấu hình cột lỗi): đó là điểm cộng về tính trung thực.
- Không dùng từ "chứng minh Data Vault tốt hơn"; dùng "trong bài toán này, Data Vault giữ được lịch sử mà bảng ghi đè làm mất".
- Với số liệu, đọc tròn khi nói (khoảng 5,6 lần, khoảng 11%), số chính xác để trên slide.
- Tập trước với đồng hồ; dừng ở cuối mỗi chương 1–2 giây để người nghe theo kịp.
