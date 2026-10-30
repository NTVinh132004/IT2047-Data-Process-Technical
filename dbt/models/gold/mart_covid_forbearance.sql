{# Một khoản vay trong cohort COVID chỉ đóng góp một kết cục; không đủ cửa sổ thì UNKNOWN. #}
WITH cohort AS (
 SELECT LOAN_HK, MAX(CASE WHEN in_forbearance THEN reporting_date END) AS last_forbearance_date,
 MAX(CASE WHEN in_forbearance AND reporting_date BETWEEN DATE'2020-03-01' AND DATE'2021-12-01' THEN 1 ELSE 0 END) AS covid
 FROM {{ ref('fact_loan_month') }} GROUP BY LOAN_HK
), outcomes AS (
 SELECT c.LOAN_HK, c.last_forbearance_date,
 MAX(CASE WHEN f.reporting_date > c.last_forbearance_date AND f.reporting_date <= ADD_MONTHS(c.last_forbearance_date,12)
               AND f.default_reporting_date=f.reporting_date THEN 1 ELSE 0 END) AS defaulted,
 MAX(CASE WHEN f.reporting_date > c.last_forbearance_date AND f.reporting_date <= ADD_MONTHS(c.last_forbearance_date,12) AND f.lifecycle_status='PREPAID' THEN 1 ELSE 0 END) AS prepaid,
 MAX(CASE WHEN f.reporting_date > c.last_forbearance_date AND f.reporting_date <= ADD_MONTHS(c.last_forbearance_date,12) AND f.modification_flag='Y' THEN 1 ELSE 0 END) AS modified,
 MAX(CASE WHEN f.reporting_date=ADD_MONTHS(c.last_forbearance_date,12) THEN f.delinquency_status END) AS final_status,
 MAX(CASE WHEN f.payment_deferral_flag IN ('C','P') THEN 1 ELSE 0 END) AS deferral
 FROM cohort c JOIN {{ ref('fact_loan_month') }} f ON f.LOAN_HK=c.LOAN_HK WHERE c.covid=1
 GROUP BY c.LOAN_HK, c.last_forbearance_date
), classified AS (
 SELECT *, CASE WHEN defaulted=1 THEN 'DEFAULTED' WHEN prepaid=1 THEN 'PREPAID' WHEN modified=1 THEN 'MODIFIED'
 WHEN final_status='00' THEN 'RECOVERED' WHEN final_status IS NULL THEN 'UNKNOWN' ELSE 'DELINQUENT' END AS outcome
 FROM outcomes
)
SELECT last_forbearance_date, outcome, COUNT(*) AS loan_count, SUM(deferral) AS deferral_count
FROM classified GROUP BY last_forbearance_date, outcome
