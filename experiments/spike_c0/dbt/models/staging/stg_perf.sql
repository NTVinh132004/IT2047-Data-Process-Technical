{%- set yaml_metadata -%}
source_model: base_perf
derived_columns:
  RECORD_SOURCE: "!sample_perf_2019"
  # load_date = ngày 1 của tháng sau tháng báo cáo (PRD mục 6, R-01); cùng quy tắc với ingestion/periods.py::load_date_for
  LOAD_DATE: "add_months(to_date(concat(reporting_period, '01'), 'yyyyMMdd'), 1)"
hashed_columns:
  LOAN_HK: loan_id
  BALANCE_HASHDIFF:
    is_hashdiff: true
    columns:
      - current_upb
      - interest_bearing_upb
      - non_interest_bearing_upb
      - current_interest_rate
      - loan_age
      - remaining_months
      - eltv
      - cumulative_modification_cost
      - current_modification_cost
{%- endset -%}

{% set metadata = fromyaml(yaml_metadata) %}

{{ automate_dv.stage(include_source_columns=true,
                     source_model=metadata['source_model'],
                     derived_columns=metadata['derived_columns'],
                     null_columns=none,
                     hashed_columns=metadata['hashed_columns'],
                     ranked_columns=none) }}
