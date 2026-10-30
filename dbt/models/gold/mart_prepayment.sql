WITH monthly AS (
 SELECT reporting_date, COUNT(*) AS loan_count,
 SUM(CASE WHEN is_active THEN current_upb ELSE 0 END) AS active_upb,
 SUM(CASE WHEN lifecycle_status='PREPAID' THEN 1 ELSE 0 END) AS prepaid_count,
 SUM(CASE WHEN lifecycle_status='PREPAID' THEN COALESCE(zero_balance_removal_upb, 0) ELSE 0 END) AS prepaid_upb
 FROM {{ ref('fact_loan_month') }} GROUP BY reporting_date
), smm AS (
 SELECT m.*, prev.active_upb AS previous_active_upb,
 CAST(m.prepaid_upb AS DOUBLE) / NULLIF(CAST(prev.active_upb AS DOUBLE), 0) AS smm
 FROM monthly m LEFT JOIN monthly prev ON prev.reporting_date=ADD_MONTHS(m.reporting_date, -1)
)
SELECT *, 1 - POWER(1 - smm, 12) AS cpr FROM smm
