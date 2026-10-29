# Từ điển dữ liệu và định nghĩa nghiệp vụ

Oct 27, 2026 · @Vĩnh · Đầu ra giai đoạn 0, cổng C0

Tài liệu này chốt cách hiểu dữ liệu Freddie Mac theo File Layout Release 47 (07/2026). Nó gồm: cột nào vào Satellite nào, các mã đặc biệt, và định nghĩa quá hạn, trả trước hạn, vỡ nợ, hoãn trả nợ dùng cho FR-12 và FR-16. Vị trí, kiểu dữ liệu và mã thiếu của từng cột nằm trong `conf/schema/orig.yml` và `conf/schema/perf.yml`; tài liệu này không chép lại toàn bộ mà giải thích ý nghĩa. Mọi số liệu ở đây là số tổng hợp từ bộ mẫu 2019, sinh bằng `python3 experiments/kham_pha_bo_mau.py`.

Nguồn: General User Guide Release 47 và Disclosure Changes Summary (07/2026), liên kết ở mục 13 Kế hoạch.

## 1. Kết quả khám phá bộ mẫu 2019

Bộ mẫu sạch hơn dự kiến: không trùng khóa, không mồ côi, không hở tháng. Điều này có nghĩa cổng chất lượng (FR-07) sẽ hầu như không chặn dòng nào trên dữ liệu thật; để kiểm thử nó cần dữ liệu lỗi cố ý (mục 5).

| Chỉ số | orig | perf |
| --- | --- | --- |
| Số trường mỗi dòng | 31 (mọi dòng) | 35 (mọi dòng) |
| Số dòng | 50.000 | 1.934.614 |
| Số khoản vay | 50.000, không trùng | 50.000 |
| Khóa trùng | 0 | 0 cặp (khoản vay, tháng) |
| Mồ côi | 0 khoản vay orig không có perf | 0 khoản vay perf không có orig |
| Tháng báo cáo | — | 201901 → 202603, 87 tháng liên tục, không khoản vay nào bị hở tháng |
| Số kỳ nạp (quý báo cáo) | — | 29 (2019Q1 → 2026Q1) |

**Lát orig theo kỳ** (khoản vay vào Hub ở quý có tháng perf đầu tiên): 2019Q1 6.957; Q2 13.164; Q3 12.144; Q4 13.115; 2020Q1 4.531; các quý sau tổng 89. Từ 2021Q3 trở đi, kỳ nạp chỉ có perf.

**Số dòng perf theo kỳ:** thấp nhất 10.150 (2019Q1), cao nhất 140.961 (2020Q1), sau đó giảm dần do khoản vay trả hết (còn 43.190 ở 2026Q1).

**Tháng perf đầu tiên** thường là tháng trước ngày trả góp đầu tiên (45.767 khoản vay); 2.874 khoản vay bắt đầu đúng tháng trả góp đầu tiên và 1.359 khoản vay bắt đầu muộn hơn 1–10 tháng. Dòng perf trước kỳ trả góp đầu tiên có trạng thái `00`.

**Phân bố đáng chú ý:**

- Mã thiếu ở orig rất ít: điểm FICO 18 dòng `9999`, DTI 31 dòng `999`, CLTV 1 dòng `999`. VantageScore 4.0 là `9999` ở cả 50.000 dòng (vintage 2019 chưa có), nên không dùng.
- `amortization_type` toàn `FRM`, `prepayment_penalty_flag` và `interest_only_flag` toàn `N`; ba cột này không mang thông tin, không đưa vào Satellite.
- Seller: 28 giá trị, trong đó `OTHER` chiếm 16.863 khoản vay (33,7%). Servicer: 41 giá trị, `OTHER` chiếm 30% số dòng perf.
- Trạng thái quá hạn: `00` chiếm 97,4% dòng; lớn nhất là `63`; có 137 dòng `RA`; không có `XX`.
- Zero Balance Code ở dòng cuối: `01` 35.551; `96` 123; `16` 31; `02` 18; `09` 14; `15` 13; `03` 4. Còn 14.246 khoản vay đang hoạt động ở 202603.
- Hoãn trả nợ: 3.479 khoản vay có ít nhất một tháng `borrower_assistance_plan = F`; 3.310 trong số đó rơi vào 202003–202112.

## 2. Ảnh hưởng tới thiết kế

Bốn phát hiện làm thay đổi hoặc làm rõ thiết kế; R-21 đến R-24 trong `review.md` ghi quyết định.

1. **Servicer Name chuyển từ orig sang perf** (Release 47, vị trí 34). Servicer giờ là thuộc tính theo tháng: 18.774 khoản vay (37,5%) đổi servicer ít nhất một lần, 2.368 khoản vay quay lại servicer cũ (A → B → A). `hub_servicer` và `link_loan_servicer` phải nạp từ perf. Link chỉ ghi nhận cặp đã từng tồn tại, nên servicer của tháng m chỉ lấy đúng được từ `esat_loan_servicer` (FR-11). R-21.
2. **Seller và servicer nhỏ bị gộp thành `OTHER`** (ngưỡng 1% tổng UPB của quý). Rủi ro này ở mục 10 Kế hoạch đã xảy ra. `OTHER` vẫn là một khóa nghiệp vụ hợp lệ trong Hub nhưng không phải một tổ chức; mart và báo cáo phải ghi rõ hạn chế này. R-22.
3. **Trạng thái quá hạn tiếp tục tăng trong thời gian hoãn trả nợ.** Nếu định nghĩa vỡ nợ chỉ là "quá hạn 180 ngày trở lên", 1.701 khoản vay bị tính là vỡ nợ. Nếu bỏ các tháng đang trong forbearance, con số còn 926, vì phần lớn khoản vay hoãn trả do COVID đã hồi phục. Định nghĩa ở mục 4 chọn cách thứ hai. R-23.
4. **Bộ mẫu có 29 kỳ, 87 `load_date`**, nhiều hơn mức kế hoạch ngầm định. Mục tiêu 45 phút end-to-end phải chia cho 29 lần chạy DAG, khoảng 1,5 phút mỗi kỳ. Baseline ở C1 sẽ cho biết có khả thi không. R-24.

## 3. Cột theo bảng đích

Tên cột là tên snake_case trong `conf/schema/`. Cột không có trong bảng dưới (ví dụ `pre_harp_loan_id`, `vantage_score_4`, `amortization_type`) được nạp vào Bronze nhưng không vào Raw Vault.

**Khóa nghiệp vụ**

| Bảng | Khóa | Nguồn | Ghi chú |
| --- | --- | --- | --- |
| `hub_loan` | `loan_id` | orig, perf | Dạng `PYYQnXXXXXXX`; P = F (FRM) hoặc A (ARM), YYQn là quý khởi tạo. Không đổi giữa các release |
| `hub_seller` | `seller_name` | orig | `OTHER` là một khóa (mục 2) |
| `hub_servicer` | `servicer_name` | perf | Từ Release 47 (mục 2) |
| `link_loan_seller` | (`loan_id`, `seller_name`) | orig | Một cặp cho mỗi khoản vay |
| `link_loan_servicer` | (`loan_id`, `servicer_name`) | perf | Mỗi cặp đã từng xuất hiện một dòng |
| `esat_loan_servicer` | hash của link, `load_date` | perf | Should (FR-11): servicer hiệu lực tại từng `load_date` |

**`sat_loan_origination`** (orig, gần như không đổi; đổi khi có đợt sửa FR-14): `credit_score`, `first_payment_date`, `maturity_date`, `first_time_homebuyer_flag`, `mi_pct`, `orig_cltv`, `orig_ltv`, `orig_dti`, `orig_upb`, `orig_interest_rate`, `orig_loan_term`, `channel`, `loan_purpose`, `number_of_borrowers`, `super_conforming_flag`, `special_eligibility_program`.

**`sat_loan_property`** (orig): `property_state`, `postal_code`, `msa_code`, `property_type`, `number_of_units`, `occupancy_status`, `property_valuation_method`.

**`sat_loan_balance`** (perf, đổi hằng tháng): `current_upb`, `interest_bearing_upb`, `non_interest_bearing_upb`, `current_interest_rate`, `loan_age`, `remaining_months`, `eltv`, `cumulative_modification_cost`, `current_modification_cost`.

**`sat_loan_delinquency`** (perf, chỉ đổi khi có sự kiện): `delinquency_status`, `modification_flag`, `interest_rate_step_flag`, `payment_deferral_flag`, `borrower_assistance_plan`, `disaster_delinquency_flag`, `mi_cancellation_flag`.

**`sat_loan_termination`** (perf, thường chỉ một phiên bản ở tháng kết thúc): `zero_balance_code`, `zero_balance_date`, `zero_balance_removal_upb`, `ddlpi`, `defect_settlement_date`, `net_sales_proceeds`, `mi_recoveries`, `non_mi_recoveries`, `total_expenses`, `legal_costs`, `maintenance_costs`, `taxes_insurance`, `misc_expenses`, `delinquent_accrued_interest`, `actual_loss`, `bankruptcy_cramdown_costs`. Release 47 đổi dấu: khoản thu hồi ghi âm, chi phí và tổn thất ghi dương. `ddlpi` nằm ở đây vì trên bộ mẫu nó chỉ có giá trị ở 35.718 dòng, gần như trùng với các dòng kết thúc.

**Chiều phân tích dùng ở FR-16**

| Chiều | Cột | Nhóm |
| --- | --- | --- |
| Tháng | `reporting_period` | YYYYMM |
| Bang | `property_state` | 54 giá trị (50 bang và các vùng lãnh thổ) |
| Bên bán | `seller_name` | Như nguồn, kể cả `OTHER` |
| Nhóm điểm tín dụng | `credit_score` | `<620`, `620–679`, `680–739`, `740–779`, `>=780`, `N/A` (9999) |
| Nhóm LTV | `orig_ltv` | `<=60`, `61–80`, `81–90`, `91–95`, `>95`, `N/A` (999) |
| Nhóm DTI | `orig_dti` | `<=20`, `21–30`, `31–36`, `37–43`, `44–50`, `>50`, `N/A` (999) |

## 4. Định nghĩa nghiệp vụ

Các định nghĩa dưới đây là quy tắc cho `bsat_loan_risk`, `bsat_loan_lifecycle` và ba mart. Đổi định nghĩa là thay đổi lớn theo PRD mục 8, vì giá trị tính tay ở `tests/fixtures/` (C3) dựa trên chúng.

**Khoản vay đang hoạt động tại tháng m:** có dòng perf tháng m và `zero_balance_code` rỗng ở dòng đó. Đây là mẫu số của mọi tỷ lệ theo tháng.

**Quá hạn** (từ `delinquency_status`, số tháng chậm trả tính theo DDLPI):

| Mã | Nghĩa | Nhóm |
| --- | --- | --- |
| `00` | Đúng hạn hoặc chậm dưới 30 ngày (kể cả tháng trước kỳ trả góp đầu tiên) | Đúng hạn |
| `01` | Chậm 30–59 ngày | Quá hạn 30 |
| `02` | Chậm 60–89 ngày | Quá hạn 60 |
| `03` trở lên | Chậm 90 ngày trở lên (tối đa `99`) | Quá hạn 90+ |
| `RA` | Đã thu hồi tài sản (REO Acquisition) | Quá hạn 90+ |
| `XX` | Không có dữ liệu | Loại khỏi tử số và mẫu số |

Tỷ lệ quá hạn 30/60/90+ của tháng m bằng số khoản vay đang hoạt động thuộc nhóm đó chia cho số khoản vay đang hoạt động (bỏ `XX`), tính theo số lượng và theo `current_upb`. "Quá hạn 30+" là tổng ba nhóm. `bsat_loan_risk` tính thêm `months_delinquent_consecutive` (số tháng liên tiếp đến tháng m có mã khác `00`) và `ever_d90` (đã từng thuộc nhóm 90+ đến tháng m).

**Trả trước hạn:** khoản vay có `zero_balance_code = 01` và `zero_balance_date` trước `maturity_date`. Tỷ lệ trả trước tháng m tính theo dư nợ: SMM = tổng `zero_balance_removal_upb` của các khoản vay trả trước trong tháng m chia cho tổng `current_upb` tháng m−1 của các khoản vay đang hoạt động ở tháng m−1. CPR = 1 − (1 − SMM)^12. Trả bớt một phần gốc (curtailment) không tính. Dữ liệu không ghi lý do trả trước, nên "do tái cấp vốn" chỉ là diễn giải dựa trên bối cảnh lãi suất; báo cáo phải nêu đây là hạn chế.

**Vỡ nợ:** tháng đầu tiên khoản vay thỏa một trong các điều kiện sau:

- `delinquency_status` từ `06` trở lên (quá hạn 180 ngày) ở tháng **không** có `borrower_assistance_plan = F`
- `delinquency_status = RA`
- `zero_balance_code` thuộc `02` (bán cho bên thứ ba), `03` (bán thiếu hoặc xóa nợ), `09` (thanh lý REO)

`15` (bán khoản vay) và `16` (chứng khoán hóa khoản vay tái hoạt động) là kết thúc nhưng không phải vỡ nợ, trừ khi khoản vay đã vỡ nợ trước đó. `96` (lỗi bảo lãnh hoặc lỗi phục vụ) tách thành nhóm riêng, không tính vào tổn thất. Bỏ tháng forbearance khỏi điều kiện 180 ngày vì trong chương trình hoãn trả COVID (CARES Act), trạng thái quá hạn vẫn tăng dù người vay không vi phạm (mục 2, ý 3).

**Hoãn trả nợ (forbearance):** tháng có `borrower_assistance_plan = F`. Khoản vay được tính là hoãn trả do COVID nếu có ít nhất một tháng `F` trong 202003–202112. `disaster_delinquency_flag = Y` và `payment_deferral_flag` (`C` = được hoãn trả trong tháng, `P` = đã được hoãn trả trước đó) là thông tin đi kèm, không dùng để xác định forbearance.

**Kết cục sau hoãn trả (câu hỏi 4):** xét 12 tháng sau tháng `F` cuối cùng và lấy kết cục đầu tiên theo thứ tự ưu tiên: vỡ nợ, trả trước hạn, sửa đổi khoản vay (`modification_flag = Y`). Nếu không có kết cục nào, khoản vay "hồi phục" khi tháng cuối của cửa sổ có mã `00`, ngược lại là "còn quá hạn". Trên bộ mẫu: 3.310 khoản vay gồm hồi phục 1.462, trả trước hạn 1.162, vỡ nợ 603, còn quá hạn 75, sửa đổi 8; có 1.748 khoản vay dùng payment deferral.

**Trạng thái vòng đời** (`bsat_loan_lifecycle`, tại tháng m, theo thứ tự ưu tiên):

| Trạng thái | Điều kiện |
| --- | --- |
| `DEFECT` | `zero_balance_code = 96` |
| `LIQUIDATED` | `zero_balance_code` thuộc `02`, `03`, `09` |
| `SOLD` | `zero_balance_code` thuộc `15`, `16` |
| `PREPAID` | `zero_balance_code = 01` |
| `DEFAULTED` | Đã vỡ nợ đến tháng m nhưng chưa có `zero_balance_code` |
| `FORBEARANCE` | `borrower_assistance_plan = F` |
| `DELINQUENT` | Mã quá hạn khác `00` |
| `CURRENT` | Còn lại |

## 5. Luật chất lượng cho cổng FR-07

Vì bộ mẫu không có lỗi, test cổng C2 cần một tệp fixture nhỏ cố ý chứa từng loại lỗi dưới đây.

| Luật | Áp dụng | Lý do chặn |
| --- | --- | --- |
| Số trường đúng 31 (orig) / 35 (perf) | Mọi dòng | `sai_so_truong` |
| `loan_id` khớp mẫu `^[FA]\d{2}Q[1-4]\d{7}$` | orig, perf | `sai_khoa` |
| Cột kiểu `int`, `decimal`, `yyyymm` ép kiểu được | Theo `conf/schema` | `sai_kieu` |
| Giá trị nằm trong `domain` hoặc `values`, hoặc là mã `missing` | Theo `conf/schema` | `ngoai_mien` |
| Không trùng (`loan_id`) ở orig, (`loan_id`, `reporting_period`) ở perf | Trong lát kỳ | `trung_khoa` |
| Dòng perf có `loan_id` trong orig (Bronze, mọi kỳ đến kỳ hiện tại) | perf | `mo_coi` |

Mã thiếu (`9999`, `999`, `99`, `9`, `7`, `XX`) không phải lỗi: Bronze giữ nguyên, staging đổi thành null.

## 6. File tải trước Release 47

File tải trước 07/2026 có layout khác: orig 32 trường (Servicer Name ở vị trí 25, MI Cancellation Indicator ở vị trí 32), perf 32 trường, và mã quá hạn một chữ số (`0`, `1`, ...). Bộ mẫu trong repo đã là Release 47. Nếu bộ đầy đủ tải về có layout cũ, cần thêm một file schema cũ trong `conf/schema/` và chuẩn hóa sang Release 47 ở Bronze (FR-05); `conf/column_mapping.yml` đã liệt kê các tên đổi.
