{#- Hash key, hash_diff cho Hub, Link và Satellite nguồn perf (từ điển dữ liệu mục 3) -#}
{%- set yaml_metadata -%}
source_model: base_perf
derived_columns:
  # Nguồn của lần xuất hiện, ghi vào record tracking satellite xts_loan (R-33)
  TRACK_SOURCE: "!perf"
  TRACK_LINK_LOAN_SERVICER: "!link_loan_servicer"
null_columns:
  # Khóa nghiệp vụ thiếu thay bằng '-1' trước khi băm, giữ gốc ở servicer_name_ORIGINAL: không bỏ dòng khỏi Hub/Link
  # (DV-10, cơ chế null_columns của automate_dv theo DV-13)
  required: [servicer_name]
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
{#- Lọc kỳ ở đây (bảng dựng lại mỗi lần chạy), không ở view base_*: bộ lọc trong view bị đóng băng lúc tạo view và
    một lần chạy dbt chọn lọc sẽ đọc nhầm kỳ cũ mà không báo lỗi (R-31). Spark đẩy điều kiện xuống bảng nguồn. -#}
SELECT * FROM (
{{ automate_dv.stage(include_source_columns=true, source_model=metadata['source_model'],
                     hashed_columns=metadata['hashed_columns'], derived_columns=metadata['derived_columns'],
                     null_columns=metadata['null_columns'], ranked_columns=none) }}
) AS staged
{% if var('periods') %}WHERE period IN ({% for p in var('periods') %}'{{ p }}'{{ ', ' if not loop.last }}{% endfor %}){% endif %}
