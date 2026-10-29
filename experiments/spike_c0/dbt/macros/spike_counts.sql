{# In một dòng JSON với các số đếm dùng để kiểm R-01 và R-08 (đọc bởi run_spike.sh) #}
{% macro spike_counts() %}
  {% set sql %}
    select
      (select count(*) from raw.perf where reporting_period in ({{ var('months') | join(', ') }})) as perf_rows,
      (select count(*) from {{ ref('hub_loan') }}) as hub_rows,
      (select count(distinct loan_id) from {{ ref('hub_loan') }}) as hub_distinct_nk,
      (select count(*) from {{ ref('sat_loan_balance') }}) as sat_rows,
      (select count(*) from (select loan_hk, load_date from {{ ref('sat_loan_balance') }}
                             group by loan_hk, load_date having count(*) > 1)) as sat_dup_keys,
      (select count(distinct load_date) from {{ ref('sat_loan_balance') }}) as sat_load_dates
  {% endset %}
  {% set row = run_query(sql).rows[0] %}
  {{ print(tojson(dict(zip(row.keys(), row.values())))) }}
{% endmacro %}
