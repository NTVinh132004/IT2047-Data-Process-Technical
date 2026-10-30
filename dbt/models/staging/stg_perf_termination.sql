-- Chỉ dòng mang sự kiện kết thúc. Các tháng khác có mọi cột kết thúc đều null; nếu đưa vào, mỗi khoản vay
-- có thêm một phiên bản "toàn null" vô nghĩa ở sat_loan_termination (từ điển dữ liệu mục 3).
SELECT *
FROM {{ ref('stg_perf') }}
WHERE zero_balance_code IS NOT NULL OR defect_settlement_date IS NOT NULL
