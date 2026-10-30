# Đánh giá kiến trúc theo chuẩn Data Vault 2.0

Oct 30, 2026 · @Vĩnh · Căn cứ cho thay đổi R-33

Tài liệu đối chiếu kiến trúc sau cổng C2 (và phần C3 đã viết) với chuẩn Data Vault 2.0 công bố bởi Data Vault Alliance (Dan Linstedt), Scalefree và tài liệu của hai package dbt phổ biến (automate-dv, datavault4dbt). Mục tiêu: tránh tự chế và sai kiến trúc. Kết luận: phần lõi (Hub, Link, Satellite, hash, insert-only, tách Satellite theo tốc độ thay đổi) đúng chuẩn; có hai chỗ lệch nghiêm trọng phải sửa trước khi đi tiếp, và bốn chỗ lệch mức trung bình.

## 1. Nguồn tham khảo

| Nguồn | Nội dung dùng |
| --- | --- |
| [Data Vault Alliance: Understanding Late Arriving Data](https://datavaultalliance.com/news/dv/dv-tips/understanding-late-arriving-data/) | Định nghĩa `load_date`, applied date, dữ liệu đến trễ |
| [Scalefree: How to Deal With Late Arriving Data](https://www.scalefree.com/knowledge/webinars/data-vault-friday/how-to-deal-with-late-arriving-data/) | `load_date` chỉ tiến, ngày nghiệp vụ nằm trong Satellite, PIT theo trục nghiệp vụ |
| [Scalefree: How to Implement Insert Only in Data Vault 2.0](https://www.scalefree.com/blog/data-vault/insert-only-in-data-vault/) | `load_date` không phải ngày nghiệp vụ, gán cho cả lần nạp |
| [Scalefree: Implementing Data Vault 2.0 Ghost Records](https://www.scalefree.com/scalefree-newsletter/implementing-dv2-0-ghost-records/) | PIT là đối tượng hỗ trợ truy vấn ở Business Vault, ghost record, equi-join |
| [Scalefree: Implementing Data Vault 2.0 Zero Keys](https://www.scalefree.com/scalefree-newsletter/implementing-data-vault-2-0-zero-keys/) | Khóa nghiệp vụ null dùng zero key thay vì bỏ dòng |
| [Scalefree: Dealing with Corrupted Loads](https://www.scalefree.com/knowledge/webinars/data-vault-friday/dealing-with-corrupted-loads-in-data-vault/) | Kiểm tra kỹ thuật trước Raw Vault; data lake/PSA giữ mọi thứ |
| [Scalefree: Defining the Error Mart](https://www.scalefree.com/wissen/webinare/data-vault-friday/defining-the-error-mart-in-data-vault/), [Glossary](https://www.scalefree.com/blog/data-vault/data-vault-glossary-hub-link-satellite-business-vault-and-more/) | Error mart cho dòng vi phạm hard rule; quality layer ở Business Vault |
| [Microsoft: Data Vault 2.0 on Azure](https://techcommunity.microsoft.com/blog/analyticsonazure/data-vault-2-0-on-azure/3860665), [Implementing Business Logic using DV 2.0](https://techcommunity.microsoft.com/blog/analyticsonazure/implementing-business-logic-using-data-vault-2-0-on-azure-fabric/4287170) | Hard rule trước Raw Vault, soft rule ở Business Vault |
| [datavault4dbt: How to Track Effectivity](https://www.datavault4dbt.com/documentation/v2.0/general-usage-notes/how-to-track-effectivity/) | Record tracking satellite, effectivity satellite |
| [AutomateDV: Extended Tracking Satellite](https://automate-dv.readthedocs.io/en/latest/tutorial/tut_xts/), [Materialisations](https://automate-dv.readthedocs.io/en/latest/materialisations/) | XTS; nạp lịch sử theo kỳ (`vault_insert_by_period`) |
| Linstedt & Olschimke, *Building a Scalable Data Warehouse with Data Vault 2.0* (Morgan Kaufmann, 2015), chương 4–5, 11–14 | Định nghĩa gốc của các thành phần |

Lưu ý: các nguồn thống nhất về nguyên tắc nhưng khác nhau ở chi tiết (ví dụ applied date ở mức dòng hay mức lần nạp; error mart nhận lỗi hard rule hay cả soft rule). Chỗ nào nguồn khác nhau, tài liệu này ghi rõ và chọn cách gần định nghĩa gốc nhất.

## 2. Đúng chuẩn

| Thành phần | Chuẩn | Hiện trạng |
| --- | --- | --- |
| Phân lớp | Staging → Raw Vault → Business Vault → information mart; Raw Vault chỉ thêm mới | Đúng. Landing và Bronze giữ mọi thứ nhận được, đúng vai trò data lake/PSA "giữ mọi dữ liệu, hợp lệ hay hỏng" (Scalefree) |
| Hub, Link | Khóa nghiệp vụ, hash key, `load_date`, `record_source`; Hub nạp từ nhiều nguồn | Đúng (`hub_loan` từ orig và perf) |
| Satellite | Khóa (`hash_key`, `load_date`), `hash_diff` để phát hiện thay đổi, chỉ thêm mới, không end-date | Đúng |
| Tách Satellite theo tốc độ thay đổi | Khuyến nghị gốc của DV2 | Đúng (P2); `sat_loan_delinquency` chỉ giữ 5,7% số dòng perf |
| Hash | Upper, trim, dấu phân cách, ký hiệu null trước khi hash; DV2.0 dùng MD5 mặc định, SHA chấp nhận được | Đúng (sha2-256, `\|\|`, `^^`), khớp quy ước của automate-dv |
| Business Vault | Satellite tính toán theo khóa Hub, tách khỏi dữ liệu thô, dựng lại được | Đúng về hình thức (`bsat_*`), nhưng sai nguồn đầu vào (mục 3.1) |
| Error mart | Giữ dòng vi phạm hard rule để xử lý và nạp lại | Đúng một phần: bảng quarantine đóng vai trò này, nhưng đang nhận cả lỗi soft rule (mục 3.2) |
| Dùng package chuẩn | Ưu tiên package đã kiểm chứng thay vì tự viết | Đúng: automate-dv, kèm lớp tương thích cho Spark (R-26). Hai macro viết lại giữ nguyên logic gốc |

## 3. Lệch chuẩn nghiêm trọng (phải sửa)

### 3.1. PIT và Business Vault đọc từ staging

**Chuẩn:** Business Vault dựng từ Raw Vault; staging chỉ phục vụ nạp Raw Vault. PIT là đối tượng hỗ trợ truy vấn của Business Vault, dựng từ Hub/Link và các Satellite quanh nó (Scalefree, Ghost Records).

**Hiện trạng:** `pit_loan_monthly`, `bsat_loan_risk`, `bsat_loan_lifecycle` lấy danh sách "khoản vay × tháng có báo cáo" từ `stg_perf`, bảng tạm chỉ chứa kỳ vừa nạp và bị ghi đè mỗi lần chạy. Đây là nguồn của lỗi suýt xảy ra ở R-32 và của rủi ro tranh chấp khi tách tầng (hướng 3).

**Nguyên nhân gốc:** Raw Vault không lưu "khoản vay X có mặt trong lần nạp tháng m": Satellite chỉ thêm dòng khi `hash_diff` đổi.

**Cách đúng chuẩn:** record tracking satellite, dùng khi nguồn không có thông tin hiệu lực và không nạp toàn bộ ("the purpose of a record tracking satellite is to track the appearance of a hashkey", datavault4dbt). automate-dv có `xts` (Extended Tracking Satellite) ghi mọi bản ghi được stage cho từng Satellite ở mỗi lần nạp, kể cả bản ghi không đổi. Sau khi thêm, PIT và Business Vault chỉ đọc Raw Vault.

### 3.2. Soft rule chặn dữ liệu trước Raw Vault

**Chuẩn:** trước Raw Vault chỉ áp hard rule, tức điều chỉnh kỹ thuật không đổi nghĩa dữ liệu (ép kiểu, cột hệ thống, khử trùng lặp). Soft rule (làm sạch, kiểm tra nghiệp vụ, chuẩn hóa) đặt ở Business Vault hoặc quality layer, để đổi luật không phải nạp lại dữ liệu thô. Mục tiêu của nạp Raw Vault là "cover all data, regardless of its quality"; điều kiện duy nhất được phép lúc nạp Raw Vault là điều kiện kỹ thuật (delta check, thay null bằng zero key). Dòng vi phạm hard rule vào error mart; dòng "xấu" về nghiệp vụ được báo cáo qua quality mart.

**Hiện trạng (FR-07):** cổng chất lượng chặn sáu loại lỗi trước Raw Vault và PRD yêu cầu "không dòng lỗi nào vào Raw Vault".

| Luật | Loại theo DV2 | Đánh giá |
| --- | --- | --- |
| `sai_so_truong` (số trường lệch) | Hard rule: không tách được dòng | Chặn là đúng (error mart) |
| `sai_khoa` (mã khoản vay sai mẫu hoặc rỗng) | Hard rule một phần | Khóa rỗng nên dùng zero key thay vì bỏ dòng; khóa sai mẫu có thể chặn (error mart) |
| `sai_kieu` (không ép được kiểu) | Hard rule: ép kiểu | Chặn là đúng (error mart) |
| `trung_khoa` (trùng khoản vay × tháng trong một lần nạp) | Hard rule nếu các bản sao giống hệt (khử trùng lặp); không giải quyết được nếu khác nhau vì trùng khóa Satellite | Bản sao giống hệt: khử trùng lặp rồi nạp; khác nhau: error mart |
| `ngoai_mien` (ngoài miền giá trị, thiếu giá trị bắt buộc) | Soft rule | **Không nên chặn.** Nạp vào Raw Vault, đánh dấu ở quality layer của Business Vault |
| `mo_coi` (perf không có orig) | Soft rule | **Không nên chặn.** `hub_loan` đã nạp từ perf nên Raw Vault không có "mồ côi" về mặt cấu trúc; thiếu orig là vấn đề nghiệp vụ, báo ở quality mart |

**Ảnh hưởng:** đổi FR-07, AC-03 và AC-06 (thay đổi lớn theo PRD mục 8). Trên bộ mẫu không có dòng nào bị chặn, nên dữ liệu hiện tại không đổi; thay đổi nằm ở thiết kế và ở test cổng C2 (bộ fixture).

## 4. Lệch chuẩn mức trung bình

### 4.1. `load_date` mang nghĩa ngày nghiệp vụ

**Chuẩn:** `load_date` "is, was, and always will be the date and time of insert of that piece of data to the target system"; không được đổi nghĩa (Data Vault Alliance); chỉ tiến, không lùi; ngày nghiệp vụ lưu trong Satellite (applied date); PIT và snapshot dựng theo trục nghiệp vụ (Scalefree).

**Hiện trạng:** `load_date` = ngày 1 của tháng sau tháng báo cáo (P3, R-01). Đây là thời điểm đến **giả lập** của lần giao dữ liệu tháng m, không phải thời điểm hệ thống thật sự ghi. Chạy lại kỳ cũ thì "lùi" `load_date`, và bộ lọc R-08 phải bỏ dòng để tránh sai.

**Đánh giá:** chấp nhận được nếu nêu rõ là **phát lại lịch sử** (replay): mỗi tháng là một lần giao, `load_date` là thời điểm đến giả lập, nạp theo đúng thứ tự thời gian. automate-dv có cơ chế tương tự (`vault_insert_by_period`, "for development and testing"). Hai điểm còn lệch phải sửa:
- **Chỉ tiến:** chặn ở bảng điều khiển: một lần giao đã nạp thì chạy lại là không làm gì, không dựa vào bộ lọc trong Satellite. Sửa dữ liệu đi qua lần giao mới với `load_date` mới, như đợt sửa FR-14.
- **Trục nghiệp vụ tường minh:** thêm `reporting_period` vào Satellite perf làm applied date. PIT dùng mốc theo tháng báo cáo; không suy trục nghiệp vụ từ `load_date`.

### 4.2. Lọc nghiệp vụ khi nạp `sat_loan_termination`

**Chuẩn:** khi nạp Raw Vault chỉ cho phép điều kiện kỹ thuật (Scalefree).

**Hiện trạng:** `stg_perf_termination` chỉ giữ dòng có `zero_balance_code` hoặc `defect_settlement_date` (R-29). **Sửa:** bỏ bộ lọc. `hash_diff` tự loại các tháng không đổi, nên mỗi khoản vay chỉ thêm một phiên bản "chưa kết thúc" (khoảng 50.000 dòng trên bộ mẫu).

### 4.3. PIT thiếu snapshot table và ghost record

**Chuẩn:** mốc PIT do người dùng dữ liệu quy định (theo ngày, tuần, tháng) và quản lý trong snapshot table; Satellite có ghost record (zero key, `load_date` sớm nhất, `record_source = SYSTEM`) để mọi join từ PIT là equi-join (Scalefree; datavault4dbt có snapshot table và PIT; automate-dv có `enable_ghost_records`).

**Hiện trạng:** PIT tự viết (R-31), mốc suy từ dữ liệu của kỳ, con trỏ null khi chưa có phiên bản. **Sửa:** thêm snapshot table theo tháng báo cáo; bật ghost record; PIT trỏ tới ghost record thay vì null. Giữ cách nạp tăng dần của R-31 (lý do hiệu năng vẫn đúng) nhưng đầu ra theo đúng cấu trúc PIT chuẩn.

### 4.4. Link khoản vay–servicer không có thông tin hiệu lực

**Chuẩn:** quan hệ thay đổi theo thời gian dùng effectivity satellite (theo driving key) hoặc record tracking satellite (datavault4dbt; Scalefree).

**Hiện trạng:** FR-11 (effectivity satellite) đã cắt ở R-25; `link_loan_servicer` không trả lời được "servicer của tháng m". **Sửa:** record tracking satellite ở mục 3.1 cũng áp cho `link_loan_servicer`, nên có servicer theo tháng mà không cần khôi phục FR-11.

## 5. Lệch nhẹ

| Điểm | Chuẩn | Đề xuất |
| --- | --- | --- |
| Khóa nghiệp vụ null | Zero key (`000…`) thay vì bỏ dòng, giữ toàn vẹn tham chiếu | Bật zero key cho seller, servicer null khi nạp Link (bộ mẫu chưa có trường hợp này) |
| Tên `record_source` của Business Vault | Quy ước `SYSTEM` cho dòng sinh bởi hệ thống | Giữ tên mô tả hiện tại (`business_vault.bsat_loan_risk`), ghi quy ước vào từ điển |

## 6. Điều phối (liên quan hướng 3)

DV2 thiết kế để các bảng Raw Vault nạp song song, không phụ thuộc nhau; chỉ Business Vault và mart phụ thuộc Raw Vault. Điều phối bằng bảng điều khiển, mỗi tầng một job (hướng 3) phù hợp với nguyên tắc này. Sau khi sửa mục 3.1 thì không còn trạng thái dùng chung giữa các tầng.

## 7. Thay đổi đề xuất (R-33)

| Thứ tự | Thay đổi | Mục | Đụng tới PRD |
| --- | --- | --- | --- |
| 1 | Record tracking satellite (`xts` của automate-dv) cho `hub_loan` và `link_loan_servicer`; PIT và Business Vault chỉ đọc Raw Vault | 3.1, 4.4 | FR-10, FR-13 |
| 2 | Tách hard rule và soft rule: hard rule chặn vào error mart; soft rule nạp vào Raw Vault và đánh dấu ở quality layer của Business Vault | 3.2 | FR-07, AC-03, AC-06 |
| 3 | Chặn "chỉ tiến" ở bảng điều khiển; thêm `reporting_period` làm applied date | 4.1 | FR-10 |
| 4 | Bỏ bộ lọc khi nạp `sat_loan_termination` | 4.2 | Không |
| 5 | Snapshot table và ghost record cho PIT | 4.3 | FR-13 |
| 6 | Điều phối hướng 3: bảng điều khiển, mỗi tầng một job | 6 | FR-01, FR-02, FR-21 |

Sau thay đổi phải chạy lại cổng C1–C3. Ước tính: khoảng 1,5–2 ngày làm việc.
