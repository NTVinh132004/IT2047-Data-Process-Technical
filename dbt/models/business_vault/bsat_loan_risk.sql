{#- Satellite tính toán về rủi ro (FR-12), một dòng mỗi khoản vay mỗi tháng có perf. Định nghĩa theo
    docs/tu-dien-du-lieu.md mục 4:
    - delinquency_bucket: CURRENT (00), D30 (01), D60 (02), D90_PLUS (03 trở lên hoặc RA), NA (XX)
    - months_delinquent_consecutive: số tháng liên tiếp đến tháng này có mã khác 00 (XX không tính là quá hạn)
    - ever_d90: đã từng thuộc nhóm 90+ đến tháng này
    - default_load_date: load_date của tháng vỡ nợ đầu tiên: quá hạn 180+ ngày (mã 06 trở lên) ở tháng không có
      forbearance (R-23), hoặc RA, hoặc Zero Balance Code 02/03/09

    Chỉ đọc Raw Vault (R-33): lưới khoản vay × tháng là các lần xuất hiện nguồn perf trong xts_loan chưa có trong bảng
    này; các Satellite lấy qua con trỏ của PIT bằng equi-join (ghost record khi chưa có phiên bản).
    Mỗi lần chạy chỉ tính các tháng mới. Trạng thái nối tiếp qua ranh giới kỳ lấy từ dòng cuối cùng trước kỳ trong chính
    bảng này ("hạt giống"), nên phải nạp các kỳ theo thứ tự thời gian, giống luật mồ côi (R-29). Chuỗi quá hạn được
    đánh mã bằng tổng tích lũy số tháng không quá hạn; tháng thuộc chuỗi đầu kỳ (mã 0) cộng thêm số tháng của hạt giống. -#}

WITH month_keys AS (
    SELECT DISTINCT x.LOAN_HK, x.load_date
    FROM {{ ref('xts_loan') }} AS x
    WHERE x.SATELLITE_NAME = 'perf'
    {%- if is_incremental() %}
      AND NOT EXISTS (SELECT 1 FROM {{ this }} AS e WHERE e.LOAN_HK = x.LOAN_HK AND e.load_date = x.load_date)
    {%- endif %}
),

month_state AS (
    SELECT
        p.LOAN_HK,
        p.AS_OF_DATE AS load_date,
        d.delinquency_status,
        d.borrower_assistance_plan,
        t.zero_balance_code
    FROM {{ ref('pit_loan_monthly') }} AS p
    JOIN month_keys AS k ON k.LOAN_HK = p.LOAN_HK AND k.load_date = p.AS_OF_DATE
    JOIN {{ ref('sat_loan_delinquency') }} AS d
        ON d.LOAN_HK = p.SAT_LOAN_DELINQUENCY_PK AND d.load_date = p.SAT_LOAN_DELINQUENCY_LDTS
    JOIN {{ ref('sat_loan_termination') }} AS t
        ON t.LOAN_HK = p.SAT_LOAN_TERMINATION_PK AND t.load_date = p.SAT_LOAN_TERMINATION_LDTS
),

flags AS (
    SELECT
        *,
        delinquency_status IS NOT NULL AND delinquency_status <> '00' AS is_delinquent,
        delinquency_status = 'RA'
            OR (delinquency_status RLIKE '^[0-9]+$' AND CAST(delinquency_status AS INT) >= 3) AS is_d90,
        (delinquency_status RLIKE '^[0-9]+$' AND CAST(delinquency_status AS INT) >= 6
            AND COALESCE(borrower_assistance_plan, '') <> 'F')
            OR delinquency_status = 'RA'
            OR zero_balance_code IN ('02', '03', '09') AS is_default_event
    FROM month_state
),

{% if is_incremental() %}
seed AS (
    SELECT LOAN_HK, months_delinquent_consecutive AS seed_consecutive, ever_d90 AS seed_ever_d90,
           default_load_date AS seed_default_load_date
    FROM (
        SELECT r.*, ROW_NUMBER() OVER (PARTITION BY r.LOAN_HK ORDER BY r.load_date DESC) AS rn
        FROM {{ this }} AS r
        LEFT SEMI JOIN month_keys AS k ON k.LOAN_HK = r.LOAN_HK
        WHERE r.load_date < (SELECT MIN(load_date) FROM month_keys)
    ) AS q
    WHERE q.rn = 1
),
{% endif %}

runs AS (
    SELECT
        f.*,
        {%- if is_incremental() %}
        s.seed_consecutive, s.seed_ever_d90, s.seed_default_load_date,
        {%- else %}
        CAST(NULL AS INT) AS seed_consecutive, CAST(NULL AS BOOLEAN) AS seed_ever_d90,
        CAST(NULL AS DATE) AS seed_default_load_date,
        {%- endif %}
        SUM(CASE WHEN f.is_delinquent THEN 0 ELSE 1 END) OVER (
            PARTITION BY f.LOAN_HK ORDER BY f.load_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS run_id
    FROM flags AS f
    {%- if is_incremental() %}
    LEFT JOIN seed AS s ON s.LOAN_HK = f.LOAN_HK
    {%- endif %}
),

computed AS (
    SELECT
        LOAN_HK,
        load_date,
        CASE
            WHEN delinquency_status IS NULL THEN 'NA'
            WHEN delinquency_status = '00' THEN 'CURRENT'
            WHEN delinquency_status = '01' THEN 'D30'
            WHEN delinquency_status = '02' THEN 'D60'
            ELSE 'D90_PLUS'
        END AS delinquency_bucket,
        CASE
            WHEN NOT is_delinquent THEN 0
            WHEN run_id = 0 THEN ROW_NUMBER() OVER (PARTITION BY LOAN_HK, run_id ORDER BY load_date)
                                 + COALESCE(seed_consecutive, 0)
            ELSE ROW_NUMBER() OVER (PARTITION BY LOAN_HK, run_id ORDER BY load_date) - 1
        END AS months_delinquent_consecutive,
        COALESCE(seed_ever_d90, FALSE)
            OR MAX(CAST(is_d90 AS INT)) OVER (
                PARTITION BY LOAN_HK ORDER BY load_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) = 1 AS ever_d90,
        COALESCE(seed_default_load_date,
                 MIN(CASE WHEN is_default_event THEN load_date END) OVER (
                     PARTITION BY LOAN_HK ORDER BY load_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW))
            AS default_load_date
    FROM runs
)

SELECT
    c.LOAN_HK,
    c.load_date,
    c.delinquency_bucket,
    c.months_delinquent_consecutive,
    c.ever_d90,
    c.default_load_date,
    c.default_load_date IS NOT NULL AS is_defaulted,
    'business_vault.bsat_loan_risk' AS record_source
FROM computed AS c
