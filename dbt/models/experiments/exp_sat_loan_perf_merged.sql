{#- Thực nghiệm TN6 (R-38): một Satellite gộp thay cho sat_loan_balance, sat_loan_delinquency, sat_loan_termination.
    Cùng macro sat, cùng khóa và quy tắc nạp; chỉ khác hash_diff và payload. Không thuộc pipeline. -#}
{{ config(enabled=var('experiments', false), materialized='incremental') }}
{{ automate_dv.sat(src_pk='LOAN_HK', src_hashdiff='PERF_HASHDIFF', src_ldts='load_date', src_source='record_source',
                   src_payload=['reporting_period', 'current_upb', 'interest_bearing_upb', 'non_interest_bearing_upb',
                                'current_interest_rate', 'loan_age', 'remaining_months', 'eltv',
                                'cumulative_modification_cost', 'current_modification_cost',
                                'delinquency_status', 'modification_flag', 'interest_rate_step_flag',
                                'payment_deferral_flag', 'borrower_assistance_plan', 'disaster_delinquency_flag',
                                'mi_cancellation_flag', 'zero_balance_code', 'zero_balance_date',
                                'zero_balance_removal_upb', 'ddlpi', 'defect_settlement_date', 'net_sales_proceeds',
                                'mi_recoveries', 'non_mi_recoveries', 'total_expenses', 'legal_costs',
                                'maintenance_costs', 'taxes_insurance', 'misc_expenses', 'delinquent_accrued_interest',
                                'actual_loss', 'bankruptcy_cramdown_costs'],
                   src_eff=none, source_model='exp_stg_perf_merged') }}
