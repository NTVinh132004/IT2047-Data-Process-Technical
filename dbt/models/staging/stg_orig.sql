{#- Hash key, hash_diff cho Hub, Link và Satellite nguồn orig (từ điển dữ liệu mục 3) -#}
{%- set yaml_metadata -%}
source_model: base_orig
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
{{ automate_dv.stage(include_source_columns=true, source_model=metadata['source_model'],
                     hashed_columns=metadata['hashed_columns'], derived_columns=none,
                     null_columns=none, ranked_columns=none) }}
