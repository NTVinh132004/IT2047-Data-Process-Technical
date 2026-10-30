SELECT DISTINCT ADD_MONTHS(load_date, -{{ var('load_lag_months', 1) }}) AS reporting_date,
 YEAR(ADD_MONTHS(load_date, -{{ var('load_lag_months', 1) }})) AS year,
 MONTH(ADD_MONTHS(load_date, -{{ var('load_lag_months', 1) }})) AS month,
 QUARTER(ADD_MONTHS(load_date, -{{ var('load_lag_months', 1) }})) AS quarter
FROM {{ ref('xts_loan') }} WHERE SATELLITE_NAME = 'perf'
