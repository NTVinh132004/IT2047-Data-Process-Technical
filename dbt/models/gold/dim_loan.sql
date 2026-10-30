WITH versions AS (
SELECT LOAN_HK, load_date,
       {{ missing_to_null('credit_score', 'credit_score') }} AS credit_score,
       {{ missing_to_null('orig_ltv', 'orig_ltv') }} AS orig_ltv,
       {{ missing_to_null('orig_dti', 'orig_dti') }} AS orig_dti,
       maturity_date, orig_upb, orig_interest_rate, orig_loan_term, loan_purpose
FROM {{ ref('sat_loan_origination') }}
)
SELECT CONCAT(LOAN_HK, ':', CAST(load_date AS STRING)) AS loan_version_key, *,
 CASE WHEN credit_score IS NULL THEN 'N/A' WHEN credit_score < 620 THEN '<620'
 WHEN credit_score < 680 THEN '620–679' WHEN credit_score < 740 THEN '680–739'
 WHEN credit_score < 780 THEN '740–779' ELSE '>=780' END AS credit_score_band,
 CASE WHEN orig_ltv IS NULL THEN 'N/A' WHEN orig_ltv <= 60 THEN '<=60' WHEN orig_ltv <= 80 THEN '61–80'
 WHEN orig_ltv <= 90 THEN '81–90' WHEN orig_ltv <= 95 THEN '91–95' ELSE '>95' END AS ltv_band,
 CASE WHEN orig_dti IS NULL THEN 'N/A' WHEN orig_dti <= 20 THEN '<=20' WHEN orig_dti <= 30 THEN '21–30'
 WHEN orig_dti <= 36 THEN '31–36' WHEN orig_dti <= 43 THEN '37–43' WHEN orig_dti <= 50 THEN '44–50' ELSE '>50' END AS dti_band
FROM versions
