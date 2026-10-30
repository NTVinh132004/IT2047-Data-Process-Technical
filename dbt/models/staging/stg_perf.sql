{#- Hash key, hash_diff cho Hub, Link và Satellite nguồn perf (từ điển dữ liệu mục 3) -#}
{%- set yaml_metadata -%}
source_model: base_perf
hashed_columns:
  LOAN_HK: loan_id
  SERVICER_HK: servicer_name
  LOAN_SERVICER_HK: [loan_id, servicer_name]
  BALANCE_HASHDIFF:
    is_hashdiff: true
    columns: [current_upb, interest_bearing_upb, non_interest_bearing_upb, current_interest_rate, loan_age,
              remaining_months, eltv, cumulative_modification_cost, current_modification_cost]
  DELINQUENCY_HASHDIFF:
    is_hashdiff: true
    columns: [delinquency_status, modification_flag, interest_rate_step_flag, payment_deferral_flag,
              borrower_assistance_plan, disaster_delinquency_flag, mi_cancellation_flag]
  TERMINATION_HASHDIFF:
    is_hashdiff: true
    columns: [zero_balance_code, zero_balance_date, zero_balance_removal_upb, ddlpi, defect_settlement_date,
              net_sales_proceeds, mi_recoveries, non_mi_recoveries, total_expenses, legal_costs,
              maintenance_costs, taxes_insurance, misc_expenses, delinquent_accrued_interest, actual_loss,
              bankruptcy_cramdown_costs]
{%- endset -%}
{% set metadata = fromyaml(yaml_metadata) %}
{{ automate_dv.stage(include_source_columns=true, source_model=metadata['source_model'],
                     hashed_columns=metadata['hashed_columns'], derived_columns=none,
                     null_columns=none, ranked_columns=none) }}
