{#- Hash key, hash_diff cho Hub, Link và Satellite nguồn orig (từ điển dữ liệu mục 3) -#}
{%- set yaml_metadata -%}
source_model: base_orig
derived_columns:
  # Nguồn của lần xuất hiện, ghi vào record tracking satellite xts_loan (R-33)
  TRACK_SOURCE: "!orig"
null_columns:
  # Khóa nghiệp vụ thiếu thay bằng '-1' trước khi băm, giữ gốc ở seller_name_ORIGINAL: không bỏ dòng khỏi Hub/Link
  # (DV-10, cơ chế null_columns của automate_dv theo DV-13)
  required: [seller_name]
hashed_columns:
  LOAN_HK: loan_id
  SELLER_HK: seller_name
  LOAN_SELLER_HK: [loan_id, seller_name]
  ORIGINATION_HASHDIFF:
    is_hashdiff: true
    columns: [credit_score, first_payment_date, maturity_date, first_time_homebuyer_flag, mi_pct, orig_cltv,
              orig_ltv, orig_dti, orig_upb, orig_interest_rate, orig_loan_term, channel, loan_purpose,
              number_of_borrowers, super_conforming_flag, special_eligibility_program]
  PROPERTY_HASHDIFF:
    is_hashdiff: true
    columns: [property_state, postal_code, msa_code, property_type, number_of_units, occupancy_status,
              property_valuation_method]
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
