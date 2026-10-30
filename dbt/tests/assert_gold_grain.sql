SELECT LOAN_HK, reporting_date FROM {{ ref('fact_loan_month') }}
GROUP BY LOAN_HK, reporting_date HAVING COUNT(*) <> 1
