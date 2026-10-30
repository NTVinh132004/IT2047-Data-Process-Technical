{# Sinh tự động bằng scripts/gen_dbt_staging.py từ conf/schema, đừng sửa tay.
   Diễn giải mã thiếu (soft rule) ở Business Vault và Gold; Raw Vault giữ giá trị như nguồn giao (DV-02, R-35). #}
{% macro missing_to_null(column, expression) -%}
  {%- if column == 'channel' -%}{%- set codes = ['9'] -%}
  {%- elif column == 'credit_score' -%}{%- set codes = ['9999'] -%}
  {%- elif column == 'delinquency_status' -%}{%- set codes = ['XX'] -%}
  {%- elif column == 'eltv' -%}{%- set codes = ['999'] -%}
  {%- elif column == 'first_time_homebuyer_flag' -%}{%- set codes = ['9'] -%}
  {%- elif column == 'loan_purpose' -%}{%- set codes = ['9'] -%}
  {%- elif column == 'mi_cancellation_flag' -%}{%- set codes = ['7'] -%}
  {%- elif column == 'mi_pct' -%}{%- set codes = ['999'] -%}
  {%- elif column == 'number_of_borrowers' -%}{%- set codes = ['99'] -%}
  {%- elif column == 'number_of_units' -%}{%- set codes = ['99'] -%}
  {%- elif column == 'occupancy_status' -%}{%- set codes = ['9'] -%}
  {%- elif column == 'orig_cltv' -%}{%- set codes = ['999'] -%}
  {%- elif column == 'orig_dti' -%}{%- set codes = ['999'] -%}
  {%- elif column == 'orig_ltv' -%}{%- set codes = ['999'] -%}
  {%- elif column == 'postal_code' -%}{%- set codes = ['000'] -%}
  {%- elif column == 'property_type' -%}{%- set codes = ['99'] -%}
  {%- elif column == 'property_valuation_method' -%}{%- set codes = ['7'] -%}
  {%- elif column == 'vantage_score_4' -%}{%- set codes = ['9999'] -%}
  {%- else -%}{%- set codes = [] -%}
  {%- endif -%}
  {%- if codes -%}CASE WHEN CAST({{ expression }} AS STRING) IN ({% for c in codes %}'{{ c }}'{{ ', ' if not loop.last }}{% endfor %}) THEN NULL ELSE {{ expression }} END{%- else -%}{{ expression }}{%- endif -%}
{%- endmacro %}
