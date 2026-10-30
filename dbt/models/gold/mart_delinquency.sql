WITH observations AS (
 SELECT *, (delinquency_status RLIKE '^[0-9]{2}$' OR delinquency_status='RA') AS known_delinquency
 FROM {{ ref('fact_loan_month') }}
), counts AS (
SELECT f.reporting_date, g.property_state, s.seller_name, d.credit_score_band, d.ltv_band, d.dti_band,
 COUNT(*) AS loan_count, SUM(f.current_upb) AS total_upb,
 SUM(CASE WHEN f.is_active AND f.known_delinquency THEN 1 ELSE 0 END) AS eligible_count,
 SUM(CASE WHEN f.is_active AND f.known_delinquency THEN f.current_upb ELSE 0 END) AS eligible_upb,
 {% for bucket in ['D30','D60','D90_PLUS'] %}
 SUM(CASE WHEN f.is_active AND f.known_delinquency AND f.delinquency_bucket='{{ bucket }}' THEN 1 ELSE 0 END) AS {{ bucket | lower }}_count,
 SUM(CASE WHEN f.is_active AND f.known_delinquency AND f.delinquency_bucket='{{ bucket }}' THEN f.current_upb ELSE 0 END) AS {{ bucket | lower }}_upb{{ ',' if not loop.last }}
 {% endfor %}
FROM observations f
JOIN {{ ref('dim_loan') }} d ON d.loan_version_key=f.loan_version_key
JOIN {{ ref('dim_geography') }} g ON g.geography_key=f.geography_key
LEFT JOIN {{ ref('dim_seller') }} s ON s.seller_key=f.seller_key
GROUP BY f.reporting_date, g.property_state, s.seller_name, d.credit_score_band, d.ltv_band, d.dti_band
)
SELECT *, {% for bucket in ['d30','d60','d90_plus'] %}
 {{ bucket }}_count / NULLIF(eligible_count, 0) AS {{ bucket }}_rate,
 {{ bucket }}_upb / NULLIF(eligible_upb, 0) AS {{ bucket }}_upb_rate{{ ',' if not loop.last }}
{% endfor %} FROM counts
