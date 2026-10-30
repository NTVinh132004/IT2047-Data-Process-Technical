{#- Satellite tính toán về vòng đời (FR-12), một dòng mỗi khoản vay mỗi tháng có perf. Trạng thái theo thứ tự ưu tiên ở
    docs/tu-dien-du-lieu.md mục 4: DEFECT (ZBC 96), LIQUIDATED (02, 03, 09), SOLD (15, 16), PREPAID (01, trước ngày đáo
    hạn), MATURED (01, từ ngày đáo hạn), DEFAULTED (đã vỡ nợ, chưa kết thúc), FORBEARANCE (đang hoãn trả nợ),
    DELINQUENT (mã quá hạn khác 00), CURRENT. Dựa trên bsat_loan_risk của cùng tháng và các Satellite qua PIT
    (equi-join tới ghost record khi chưa có phiên bản); chỉ đọc Raw Vault và Business Vault (R-33). -#}

WITH new_rows AS (
    SELECT r.LOAN_HK, r.load_date, r.is_defaulted, r.delinquency_bucket
    FROM {{ ref('bsat_loan_risk') }} AS r
    {%- if is_incremental() %}
    LEFT ANTI JOIN {{ this }} AS e ON e.LOAN_HK = r.LOAN_HK AND e.load_date = r.load_date
    {%- endif %}
),

month_state AS (
    SELECT
        r.LOAN_HK,
        r.load_date,
        r.is_defaulted,
        r.delinquency_bucket,
        d.borrower_assistance_plan,
        t.zero_balance_code,
        t.zero_balance_date,
        o.maturity_date
    FROM new_rows AS r
    JOIN {{ ref('pit_loan_monthly') }} AS p ON p.LOAN_HK = r.LOAN_HK AND p.AS_OF_DATE = r.load_date
    JOIN {{ ref('sat_loan_delinquency') }} AS d
        ON d.LOAN_HK = p.SAT_LOAN_DELINQUENCY_PK AND d.load_date = p.SAT_LOAN_DELINQUENCY_LDTS
    JOIN {{ ref('sat_loan_termination') }} AS t
        ON t.LOAN_HK = p.SAT_LOAN_TERMINATION_PK AND t.load_date = p.SAT_LOAN_TERMINATION_LDTS
    JOIN {{ ref('sat_loan_origination') }} AS o
        ON o.LOAN_HK = p.SAT_LOAN_ORIGINATION_PK AND o.load_date = p.SAT_LOAN_ORIGINATION_LDTS
),

computed AS (
    SELECT
        LOAN_HK,
        load_date,
        CASE
            WHEN zero_balance_code = '96' THEN 'DEFECT'
            WHEN zero_balance_code IN ('02', '03', '09') THEN 'LIQUIDATED'
            WHEN zero_balance_code IN ('15', '16') THEN 'SOLD'
            WHEN zero_balance_code = '01' AND zero_balance_date < maturity_date THEN 'PREPAID'
            WHEN zero_balance_code = '01' THEN 'MATURED'
            WHEN is_defaulted THEN 'DEFAULTED'
            WHEN borrower_assistance_plan = 'F' THEN 'FORBEARANCE'
            WHEN delinquency_bucket IN ('D30', 'D60', 'D90_PLUS') THEN 'DELINQUENT'
            ELSE 'CURRENT'
        END AS lifecycle_status,
        borrower_assistance_plan = 'F' AS in_forbearance,
        'business_vault.bsat_loan_lifecycle' AS record_source
    FROM month_state
)

SELECT c.* FROM computed AS c
