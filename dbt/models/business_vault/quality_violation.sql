{# Sinh tự động bằng scripts/gen_dbt_staging.py từ conf/schema, đừng sửa tay.
   Quality layer của Business Vault (DV-02, DV-12, R-35): mỗi vi phạm soft rule của một phiên bản Satellite là một
   dòng. Soft rule không chặn dữ liệu: Raw Vault giữ mọi dòng qua hard rule. Mã thiếu không phải vi phạm.
   View (Business Vault ảo): chỉ đọc Raw Vault, không lưu, không model incremental nào tham chiếu (SP-03). #}
{{ config(materialized='view') }}

WITH violations AS (
    SELECT LOAN_HK, load_date, 'sat_loan_balance' AS satellite, v
    FROM {{ ref('sat_loan_balance') }}
    LATERAL VIEW explode(filter(array(
            IF(current_upb IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'current_upb', 'value', CAST(current_upb AS STRING)), NULL),
            IF(current_upb IS NOT NULL AND (current_upb < 0), named_struct('rule', 'ngoai_mien', 'column_name', 'current_upb', 'value', CAST(current_upb AS STRING)), NULL),
            IF(loan_age IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'loan_age', 'value', CAST(loan_age AS STRING)), NULL),
            IF(remaining_months IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'remaining_months', 'value', CAST(remaining_months AS STRING)), NULL),
            IF(current_interest_rate IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'current_interest_rate', 'value', CAST(current_interest_rate AS STRING)), NULL),
            IF(non_interest_bearing_upb IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'non_interest_bearing_upb', 'value', CAST(non_interest_bearing_upb AS STRING)), NULL),
            IF(cumulative_modification_cost IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'cumulative_modification_cost', 'value', CAST(cumulative_modification_cost AS STRING)), NULL),
            IF(eltv IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'eltv', 'value', CAST(eltv AS STRING)), NULL),
            IF(eltv IS NOT NULL AND CAST(eltv AS STRING) NOT IN ('999') AND (eltv < 1 OR eltv > 998), named_struct('rule', 'ngoai_mien', 'column_name', 'eltv', 'value', CAST(eltv AS STRING)), NULL),
            IF(interest_bearing_upb IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'interest_bearing_upb', 'value', CAST(interest_bearing_upb AS STRING)), NULL)
        ), e -> e IS NOT NULL)) checks AS v
    WHERE LOAN_HK <> '0000000000000000000000000000000000000000000000000000000000000000'
    UNION ALL
    SELECT LOAN_HK, load_date, 'sat_loan_delinquency' AS satellite, v
    FROM {{ ref('sat_loan_delinquency') }}
    LATERAL VIEW explode(filter(array(
            IF(delinquency_status IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'delinquency_status', 'value', CAST(delinquency_status AS STRING)), NULL),
            IF(delinquency_status IS NOT NULL AND CAST(delinquency_status AS STRING) NOT IN ('XX') AND NOT (CAST(delinquency_status AS STRING) RLIKE '^(\\d{2}|RA)$'), named_struct('rule', 'ngoai_mien', 'column_name', 'delinquency_status', 'value', CAST(delinquency_status AS STRING)), NULL),
            IF(modification_flag IS NOT NULL AND CAST(modification_flag AS STRING) NOT IN ('Y', 'P'), named_struct('rule', 'ngoai_mien', 'column_name', 'modification_flag', 'value', CAST(modification_flag AS STRING)), NULL),
            IF(interest_rate_step_flag IS NOT NULL AND CAST(interest_rate_step_flag AS STRING) NOT IN ('Y', 'N'), named_struct('rule', 'ngoai_mien', 'column_name', 'interest_rate_step_flag', 'value', CAST(interest_rate_step_flag AS STRING)), NULL),
            IF(payment_deferral_flag IS NOT NULL AND CAST(payment_deferral_flag AS STRING) NOT IN ('C', 'P'), named_struct('rule', 'ngoai_mien', 'column_name', 'payment_deferral_flag', 'value', CAST(payment_deferral_flag AS STRING)), NULL),
            IF(disaster_delinquency_flag IS NOT NULL AND CAST(disaster_delinquency_flag AS STRING) NOT IN ('Y'), named_struct('rule', 'ngoai_mien', 'column_name', 'disaster_delinquency_flag', 'value', CAST(disaster_delinquency_flag AS STRING)), NULL),
            IF(borrower_assistance_plan IS NOT NULL AND CAST(borrower_assistance_plan AS STRING) NOT IN ('F', 'R', 'T'), named_struct('rule', 'ngoai_mien', 'column_name', 'borrower_assistance_plan', 'value', CAST(borrower_assistance_plan AS STRING)), NULL),
            IF(mi_cancellation_flag IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'mi_cancellation_flag', 'value', CAST(mi_cancellation_flag AS STRING)), NULL),
            IF(mi_cancellation_flag IS NOT NULL AND CAST(mi_cancellation_flag AS STRING) NOT IN ('7') AND CAST(mi_cancellation_flag AS STRING) NOT IN ('Y', 'N'), named_struct('rule', 'ngoai_mien', 'column_name', 'mi_cancellation_flag', 'value', CAST(mi_cancellation_flag AS STRING)), NULL)
        ), e -> e IS NOT NULL)) checks AS v
    WHERE LOAN_HK <> '0000000000000000000000000000000000000000000000000000000000000000'
    UNION ALL
    SELECT LOAN_HK, load_date, 'sat_loan_origination' AS satellite, v
    FROM {{ ref('sat_loan_origination') }}
    LATERAL VIEW explode(filter(array(
            IF(credit_score IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'credit_score', 'value', CAST(credit_score AS STRING)), NULL),
            IF(credit_score IS NOT NULL AND CAST(credit_score AS STRING) NOT IN ('9999') AND (credit_score < 300 OR credit_score > 850), named_struct('rule', 'ngoai_mien', 'column_name', 'credit_score', 'value', CAST(credit_score AS STRING)), NULL),
            IF(first_payment_date IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'first_payment_date', 'value', CAST(first_payment_date AS STRING)), NULL),
            IF(first_time_homebuyer_flag IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'first_time_homebuyer_flag', 'value', CAST(first_time_homebuyer_flag AS STRING)), NULL),
            IF(first_time_homebuyer_flag IS NOT NULL AND CAST(first_time_homebuyer_flag AS STRING) NOT IN ('9') AND CAST(first_time_homebuyer_flag AS STRING) NOT IN ('Y', 'N'), named_struct('rule', 'ngoai_mien', 'column_name', 'first_time_homebuyer_flag', 'value', CAST(first_time_homebuyer_flag AS STRING)), NULL),
            IF(maturity_date IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'maturity_date', 'value', CAST(maturity_date AS STRING)), NULL),
            IF(mi_pct IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'mi_pct', 'value', CAST(mi_pct AS STRING)), NULL),
            IF(mi_pct IS NOT NULL AND CAST(mi_pct AS STRING) NOT IN ('999') AND (mi_pct < 0 OR mi_pct > 55), named_struct('rule', 'ngoai_mien', 'column_name', 'mi_pct', 'value', CAST(mi_pct AS STRING)), NULL),
            IF(orig_cltv IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'orig_cltv', 'value', CAST(orig_cltv AS STRING)), NULL),
            IF(orig_cltv IS NOT NULL AND CAST(orig_cltv AS STRING) NOT IN ('999') AND (orig_cltv < 1 OR orig_cltv > 998), named_struct('rule', 'ngoai_mien', 'column_name', 'orig_cltv', 'value', CAST(orig_cltv AS STRING)), NULL),
            IF(orig_dti IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'orig_dti', 'value', CAST(orig_dti AS STRING)), NULL),
            IF(orig_dti IS NOT NULL AND CAST(orig_dti AS STRING) NOT IN ('999') AND (orig_dti < 0 OR orig_dti > 65), named_struct('rule', 'ngoai_mien', 'column_name', 'orig_dti', 'value', CAST(orig_dti AS STRING)), NULL),
            IF(orig_upb IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'orig_upb', 'value', CAST(orig_upb AS STRING)), NULL),
            IF(orig_upb IS NOT NULL AND (orig_upb < 0), named_struct('rule', 'ngoai_mien', 'column_name', 'orig_upb', 'value', CAST(orig_upb AS STRING)), NULL),
            IF(orig_ltv IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'orig_ltv', 'value', CAST(orig_ltv AS STRING)), NULL),
            IF(orig_ltv IS NOT NULL AND CAST(orig_ltv AS STRING) NOT IN ('999') AND (orig_ltv < 1 OR orig_ltv > 998), named_struct('rule', 'ngoai_mien', 'column_name', 'orig_ltv', 'value', CAST(orig_ltv AS STRING)), NULL),
            IF(orig_interest_rate IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'orig_interest_rate', 'value', CAST(orig_interest_rate AS STRING)), NULL),
            IF(orig_interest_rate IS NOT NULL AND (orig_interest_rate < 0 OR orig_interest_rate > 20), named_struct('rule', 'ngoai_mien', 'column_name', 'orig_interest_rate', 'value', CAST(orig_interest_rate AS STRING)), NULL),
            IF(channel IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'channel', 'value', CAST(channel AS STRING)), NULL),
            IF(channel IS NOT NULL AND CAST(channel AS STRING) NOT IN ('9') AND CAST(channel AS STRING) NOT IN ('R', 'B', 'C', 'T'), named_struct('rule', 'ngoai_mien', 'column_name', 'channel', 'value', CAST(channel AS STRING)), NULL),
            IF(loan_purpose IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'loan_purpose', 'value', CAST(loan_purpose AS STRING)), NULL),
            IF(loan_purpose IS NOT NULL AND CAST(loan_purpose AS STRING) NOT IN ('9') AND CAST(loan_purpose AS STRING) NOT IN ('P', 'C', 'N', 'R'), named_struct('rule', 'ngoai_mien', 'column_name', 'loan_purpose', 'value', CAST(loan_purpose AS STRING)), NULL),
            IF(orig_loan_term IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'orig_loan_term', 'value', CAST(orig_loan_term AS STRING)), NULL),
            IF(orig_loan_term IS NOT NULL AND (orig_loan_term < 1 OR orig_loan_term > 480), named_struct('rule', 'ngoai_mien', 'column_name', 'orig_loan_term', 'value', CAST(orig_loan_term AS STRING)), NULL),
            IF(number_of_borrowers IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'number_of_borrowers', 'value', CAST(number_of_borrowers AS STRING)), NULL),
            IF(number_of_borrowers IS NOT NULL AND CAST(number_of_borrowers AS STRING) NOT IN ('99') AND (number_of_borrowers < 1 OR number_of_borrowers > 10), named_struct('rule', 'ngoai_mien', 'column_name', 'number_of_borrowers', 'value', CAST(number_of_borrowers AS STRING)), NULL),
            IF(super_conforming_flag IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'super_conforming_flag', 'value', CAST(super_conforming_flag AS STRING)), NULL),
            IF(super_conforming_flag IS NOT NULL AND CAST(super_conforming_flag AS STRING) NOT IN ('Y', 'N'), named_struct('rule', 'ngoai_mien', 'column_name', 'super_conforming_flag', 'value', CAST(super_conforming_flag AS STRING)), NULL),
            IF(special_eligibility_program IS NOT NULL AND CAST(special_eligibility_program AS STRING) NOT IN ('H', 'F', 'R'), named_struct('rule', 'ngoai_mien', 'column_name', 'special_eligibility_program', 'value', CAST(special_eligibility_program AS STRING)), NULL)
        ), e -> e IS NOT NULL)) checks AS v
    WHERE LOAN_HK <> '0000000000000000000000000000000000000000000000000000000000000000'
    UNION ALL
    SELECT LOAN_HK, load_date, 'sat_loan_property' AS satellite, v
    FROM {{ ref('sat_loan_property') }}
    LATERAL VIEW explode(filter(array(
            IF(number_of_units IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'number_of_units', 'value', CAST(number_of_units AS STRING)), NULL),
            IF(number_of_units IS NOT NULL AND CAST(number_of_units AS STRING) NOT IN ('99') AND (number_of_units < 1 OR number_of_units > 4), named_struct('rule', 'ngoai_mien', 'column_name', 'number_of_units', 'value', CAST(number_of_units AS STRING)), NULL),
            IF(occupancy_status IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'occupancy_status', 'value', CAST(occupancy_status AS STRING)), NULL),
            IF(occupancy_status IS NOT NULL AND CAST(occupancy_status AS STRING) NOT IN ('9') AND CAST(occupancy_status AS STRING) NOT IN ('P', 'I', 'S'), named_struct('rule', 'ngoai_mien', 'column_name', 'occupancy_status', 'value', CAST(occupancy_status AS STRING)), NULL),
            IF(property_state IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'property_state', 'value', CAST(property_state AS STRING)), NULL),
            IF(property_type IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'property_type', 'value', CAST(property_type AS STRING)), NULL),
            IF(property_type IS NOT NULL AND CAST(property_type AS STRING) NOT IN ('99') AND CAST(property_type AS STRING) NOT IN ('CP', 'CO', 'PU', 'SF', 'MH'), named_struct('rule', 'ngoai_mien', 'column_name', 'property_type', 'value', CAST(property_type AS STRING)), NULL),
            IF(postal_code IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'postal_code', 'value', CAST(postal_code AS STRING)), NULL),
            IF(property_valuation_method IS NULL, named_struct('rule', 'ngoai_mien', 'column_name', 'property_valuation_method', 'value', CAST(property_valuation_method AS STRING)), NULL),
            IF(property_valuation_method IS NOT NULL AND CAST(property_valuation_method AS STRING) NOT IN ('7') AND CAST(property_valuation_method AS STRING) NOT IN ('1', '2', '3', '4'), named_struct('rule', 'ngoai_mien', 'column_name', 'property_valuation_method', 'value', CAST(property_valuation_method AS STRING)), NULL)
        ), e -> e IS NOT NULL)) checks AS v
    WHERE LOAN_HK <> '0000000000000000000000000000000000000000000000000000000000000000'
    UNION ALL
    SELECT LOAN_HK, load_date, 'sat_loan_termination' AS satellite, v
    FROM {{ ref('sat_loan_termination') }}
    LATERAL VIEW explode(filter(array(
            IF(zero_balance_code IS NOT NULL AND CAST(zero_balance_code AS STRING) NOT IN ('01', '02', '03', '09', '15', '16', '96'), named_struct('rule', 'ngoai_mien', 'column_name', 'zero_balance_code', 'value', CAST(zero_balance_code AS STRING)), NULL)
        ), e -> e IS NOT NULL)) checks AS v
    WHERE LOAN_HK <> '0000000000000000000000000000000000000000000000000000000000000000'
    UNION ALL
    -- Perf không có orig: khoản vay xuất hiện ở nguồn perf mà chưa có phiên bản khởi tạo (không tính ghost record)
    SELECT x.LOAN_HK, MIN(x.load_date) AS load_date, 'xts_loan' AS satellite,
           named_struct('rule', 'mo_coi', 'column_name', 'loan_id', 'value', CAST(NULL AS STRING)) AS v
    FROM {{ ref('xts_loan') }} AS x
    WHERE x.SATELLITE_NAME = 'perf'
      AND NOT EXISTS (SELECT 1 FROM {{ ref('sat_loan_origination') }} AS o WHERE o.LOAN_HK = x.LOAN_HK)
    GROUP BY x.LOAN_HK
)

SELECT LOAN_HK, load_date, satellite, v.rule AS rule, v.column_name AS column_name, v.value AS value,
       'business_vault.quality_violation' AS record_source
FROM violations
