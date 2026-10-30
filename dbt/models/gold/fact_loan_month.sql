{# Hạt: một khoản vay có perf trong một tháng báo cáo. CORR1 không phải perf. #}
WITH seller AS (
 SELECT LOAN_HK, SELLER_HK FROM (
 SELECT *, ROW_NUMBER() OVER (PARTITION BY LOAN_HK ORDER BY load_date, LOAN_SELLER_HK) AS rn
 FROM {{ ref('link_loan_seller') }}) s WHERE rn = 1
)
SELECT x.LOAN_HK, x.load_date,
 ADD_MONTHS(x.load_date, -{{ var('load_lag_months', 1) }}) AS reporting_date,
 CONCAT(p.SAT_LOAN_ORIGINATION_PK, ':', CAST(p.SAT_LOAN_ORIGINATION_LDTS AS STRING)) AS loan_version_key,
 s.SELLER_HK AS seller_key, ls.SERVICER_HK AS servicer_key,
 CONCAT(COALESCE(g.property_state, '^^'), ':', COALESCE({{ missing_to_null('postal_code', 'g.postal_code') }}, '^^')) AS geography_key,
 b.current_upb, b.current_interest_rate, b.loan_age,
 {{ missing_to_null('delinquency_status', 'd.delinquency_status') }} AS delinquency_status,
 d.borrower_assistance_plan, d.modification_flag, d.payment_deferral_flag,
 t.zero_balance_code, t.zero_balance_date, t.zero_balance_removal_upb,
 r.delinquency_bucket, r.months_delinquent_consecutive, r.ever_d90, r.is_defaulted,
 ADD_MONTHS(r.default_load_date, -{{ var('load_lag_months', 1) }}) AS default_reporting_date,
 l.lifecycle_status, COALESCE(d.borrower_assistance_plan = 'F', FALSE) AS in_forbearance,
 t.zero_balance_code IS NULL AS is_active,
 x.record_source
FROM {{ ref('xts_loan') }} x
JOIN {{ ref('pit_loan_monthly') }} p ON p.LOAN_HK=x.LOAN_HK AND p.AS_OF_DATE=x.load_date
JOIN {{ ref('sat_loan_balance') }} b ON b.LOAN_HK=p.SAT_LOAN_BALANCE_PK AND b.load_date=p.SAT_LOAN_BALANCE_LDTS
JOIN {{ ref('sat_loan_delinquency') }} d ON d.LOAN_HK=p.SAT_LOAN_DELINQUENCY_PK AND d.load_date=p.SAT_LOAN_DELINQUENCY_LDTS
JOIN {{ ref('sat_loan_termination') }} t ON t.LOAN_HK=p.SAT_LOAN_TERMINATION_PK AND t.load_date=p.SAT_LOAN_TERMINATION_LDTS
JOIN {{ ref('sat_loan_property') }} g ON g.LOAN_HK=p.SAT_LOAN_PROPERTY_PK AND g.load_date=p.SAT_LOAN_PROPERTY_LDTS
JOIN {{ ref('bsat_loan_risk') }} r ON r.LOAN_HK=x.LOAN_HK AND r.load_date=x.load_date
JOIN {{ ref('bsat_loan_lifecycle') }} l ON l.LOAN_HK=x.LOAN_HK AND l.load_date=x.load_date
LEFT JOIN seller s ON s.LOAN_HK=x.LOAN_HK
LEFT JOIN {{ ref('xts_loan_servicer') }} xs ON xs.LOAN_HK=x.LOAN_HK AND xs.load_date=x.load_date
LEFT JOIN {{ ref('link_loan_servicer') }} ls ON ls.LOAN_SERVICER_HK=xs.HASHDIFF
WHERE x.SATELLITE_NAME='perf'
