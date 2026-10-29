{# Sinh tự động bằng experiments/spike_c0/gen_shim.py, đừng sửa tay. #}

{% macro spark__bridge(src_pk, src_extra_columns, as_of_dates_table, bridge_walk, stage_tables_ldts, src_ldts, source_model) %}
  {{ return(automate_dv.databricks__bridge(src_pk=src_pk, src_extra_columns=src_extra_columns, as_of_dates_table=as_of_dates_table, bridge_walk=bridge_walk, stage_tables_ldts=stage_tables_ldts, src_ldts=src_ldts, source_model=source_model)) }}
{% endmacro %}

{% macro spark__cast_date(column_str, as_string=false, alias=none) %}
  {{ return(automate_dv.databricks__cast_date(column_str=column_str, as_string=as_string, alias=alias)) }}
{% endmacro %}

{% macro spark__cast_datetime(column_str, as_string=false, alias=none, date_type=none) %}
  {{ return(automate_dv.databricks__cast_datetime(column_str=column_str, as_string=as_string, alias=alias, date_type=date_type)) }}
{% endmacro %}

{% macro spark__concat_ws(string_list, separator="||") %}
  {{ return(automate_dv.databricks__concat_ws(string_list=string_list, separator=separator)) }}
{% endmacro %}

{% macro spark__eff_sat(src_pk, src_dfk, src_sfk, src_extra_columns, src_start_date, src_end_date, src_eff, src_ldts, src_source, source_model) %}
  {{ return(automate_dv.databricks__eff_sat(src_pk=src_pk, src_dfk=src_dfk, src_sfk=src_sfk, src_extra_columns=src_extra_columns, src_start_date=src_start_date, src_end_date=src_end_date, src_eff=src_eff, src_ldts=src_ldts, src_source=src_source, source_model=source_model)) }}
{% endmacro %}

{% macro spark__get_escape_characters() %}
  {{ return(automate_dv.databricks__get_escape_characters()) }}
{% endmacro %}

{% macro spark__get_period_boundaries(target_relation, timestamp_field, start_date, stop_date, period) %}
  {{ return(automate_dv.databricks__get_period_boundaries(target_relation=target_relation, timestamp_field=timestamp_field, start_date=start_date, stop_date=stop_date, period=period)) }}
{% endmacro %}

{% macro spark__get_period_of_load(period, offset, start_timestamp) %}
  {{ return(automate_dv.databricks__get_period_of_load(period=period, offset=offset, start_timestamp=start_timestamp)) }}
{% endmacro %}

{% macro spark__hash(columns, alias, is_hashdiff, columns_to_escape) %}
  {{ return(automate_dv.databricks__hash(columns=columns, alias=alias, is_hashdiff=is_hashdiff, columns_to_escape=columns_to_escape)) }}
{% endmacro %}

{% macro spark__hash_alg_md5() %}
  {{ return(automate_dv.databricks__hash_alg_md5()) }}
{% endmacro %}

{% macro spark__hash_alg_sha1() %}
  {{ return(automate_dv.databricks__hash_alg_sha1()) }}
{% endmacro %}

{% macro spark__hash_alg_sha256() %}
  {{ return(automate_dv.databricks__hash_alg_sha256()) }}
{% endmacro %}

{% macro spark__incremental_bridge_replace(tmp_relation, target_relation, statement_name="main") %}
  {{ return(automate_dv.databricks__incremental_bridge_replace(tmp_relation=tmp_relation, target_relation=target_relation, statement_name=statement_name)) }}
{% endmacro %}

{% macro spark__incremental_pit_replace(tmp_relation, target_relation, statement_name="main") %}
  {{ return(automate_dv.databricks__incremental_pit_replace(tmp_relation=tmp_relation, target_relation=target_relation, statement_name=statement_name)) }}
{% endmacro %}

{% macro spark__link(src_pk, src_fk, src_extra_columns, src_ldts, src_source, source_model) %}
  {{ return(automate_dv.databricks__link(src_pk=src_pk, src_fk=src_fk, src_extra_columns=src_extra_columns, src_ldts=src_ldts, src_source=src_source, source_model=source_model)) }}
{% endmacro %}

{% macro spark__log_relation_sources(relation, source_count) %}
  {{ return(automate_dv.databricks__log_relation_sources(relation=relation, source_count=source_count)) }}
{% endmacro %}

{% macro spark__ma_sat(src_pk, src_cdk, src_hashdiff, src_payload, src_extra_columns, src_eff, src_ldts, src_source, source_model) %}
  {{ return(automate_dv.databricks__ma_sat(src_pk=src_pk, src_cdk=src_cdk, src_hashdiff=src_hashdiff, src_payload=src_payload, src_extra_columns=src_extra_columns, src_eff=src_eff, src_ldts=src_ldts, src_source=src_source, source_model=source_model)) }}
{% endmacro %}

{% macro spark__nh_link(src_pk, src_fk, src_payload, src_extra_columns, src_eff, src_ldts, src_source, source_model) %}
  {{ return(automate_dv.databricks__nh_link(src_pk=src_pk, src_fk=src_fk, src_payload=src_payload, src_extra_columns=src_extra_columns, src_eff=src_eff, src_ldts=src_ldts, src_source=src_source, source_model=source_model)) }}
{% endmacro %}

{% macro spark__pit(src_pk, src_extra_columns, as_of_dates_table, satellites, stage_tables_ldts, src_ldts, source_model) %}
  {{ return(automate_dv.databricks__pit(src_pk=src_pk, src_extra_columns=src_extra_columns, as_of_dates_table=as_of_dates_table, satellites=satellites, stage_tables_ldts=stage_tables_ldts, src_ldts=src_ldts, source_model=source_model)) }}
{% endmacro %}

{% macro spark__ref_table(src_pk, src_extra_columns, src_ldts, src_source, source_model) %}
  {{ return(automate_dv.databricks__ref_table(src_pk=src_pk, src_extra_columns=src_extra_columns, src_ldts=src_ldts, src_source=src_source, source_model=source_model)) }}
{% endmacro %}

{% macro spark__standard_column_wrapper(hash_content_casing) %}
  {{ return(automate_dv.databricks__standard_column_wrapper(hash_content_casing=hash_content_casing)) }}
{% endmacro %}

{% macro spark__type_binary(for_dbt_compare=false) %}
  {{ return(automate_dv.databricks__type_binary(for_dbt_compare=for_dbt_compare)) }}
{% endmacro %}

{% macro spark__type_string() %}
  {{ return(automate_dv.databricks__type_string()) }}
{% endmacro %}

{% macro spark__xts(src_pk, src_satellite, src_extra_columns, src_ldts, src_source, source_model) %}
  {{ return(automate_dv.databricks__xts(src_pk=src_pk, src_satellite=src_satellite, src_extra_columns=src_extra_columns, src_ldts=src_ldts, src_source=src_source, source_model=source_model)) }}
{% endmacro %}
