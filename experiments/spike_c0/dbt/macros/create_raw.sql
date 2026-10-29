{# Bảng nguồn thô đọc thẳng file perf của bộ mẫu. Tên cột theo conf/schema/perf.yml (Release 47).
   Ở pipeline thật, vai trò này thuộc về Bronze (PySpark). #}
{% macro create_raw() %}
  {% set cols = "loan_id,reporting_period,current_upb,delinquency_status,loan_age,remaining_months,defect_settlement_date,modification_flag,zero_balance_code,zero_balance_date,current_interest_rate,non_interest_bearing_upb,ddlpi,mi_recoveries,net_sales_proceeds,non_mi_recoveries,total_expenses,legal_costs,maintenance_costs,taxes_insurance,misc_expenses,actual_loss,cumulative_modification_cost,interest_rate_step_flag,payment_deferral_flag,eltv,zero_balance_removal_upb,delinquent_accrued_interest,disaster_delinquency_flag,borrower_assistance_plan,current_modification_cost,interest_bearing_upb,mi_cancellation_flag,servicer_name,bankruptcy_cramdown_costs".split(",") %}
  {% do adapter.execute("create schema if not exists raw") %}
  {% do adapter.execute("drop table if exists raw.perf") %}
  {% set ddl %}
    create table raw.perf ({% for c in cols %}{{ c }} string{{ "," if not loop.last }}{% endfor %})
    using csv options (path '/data/sample_perf_2019.txt', sep '|', header 'false')
  {% endset %}
  {% do adapter.execute(ddl) %}
{% endmacro %}
