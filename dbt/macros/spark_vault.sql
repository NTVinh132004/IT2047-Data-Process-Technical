{# Bản Spark mã nguồn mở của automate_dv.databricks__hub, __link và __sat (automate_dv 0.11.5), review R-26.
   Spark 3.5 và 4.1 không có QUALIFY (cú pháp riêng của Databricks SQL), nên mỗi QUALIFY được thay bằng truy vấn
   con tính cột cửa sổ rồi lọc bằng WHERE. Logic còn lại giữ như bản gốc; bỏ các nhánh dự án không dùng:
   vault_insert_by_rank/period, ghost record, BigQuery. Macro tiện ích (prefix, multikey...) vẫn của automate_dv. #}


{#- Lõi chung của hub và link: mỗi khóa một dòng (load_date sớm nhất, hòa thì theo record_source), chỉ chèn khóa
    chưa có trong bảng đích. not_null_cols: hub kiểm khóa chính, link kiểm thêm các khóa ngoại. #}
{%- macro _spark_insert_new_keys(source_cols, src_pk, not_null_cols, src_ldts, src_source, source_model) -%}

WITH
{%- for src in source_model %}
row_rank_{{ loop.index }} AS (
    SELECT {{ automate_dv.alias_all(source_cols, 'q') }}
    FROM (
        SELECT {{ automate_dv.prefix(source_cols, 'rr') }},
               ROW_NUMBER() OVER (
                   PARTITION BY {{ automate_dv.prefix([src_pk], 'rr') }}
                   ORDER BY {{ automate_dv.prefix([src_ldts], 'rr') }}
               ) AS rn
        FROM {{ ref(src) }} AS rr
        WHERE {{ automate_dv.multikey(not_null_cols, prefix='rr', condition='IS NOT NULL') }}
    ) AS q
    WHERE q.rn = 1
),
{%- endfor %}

stage_union AS (
    {%- for src in source_model %}
    SELECT * FROM row_rank_{{ loop.index }}
    {%- if not loop.last %}
    UNION ALL
    {%- endif %}
    {%- endfor %}
),

row_rank_union AS (
    SELECT {{ automate_dv.alias_all(source_cols, 'q') }}
    FROM (
        SELECT ru.*,
               ROW_NUMBER() OVER (
                   PARTITION BY {{ automate_dv.prefix([src_pk], 'ru') }}
                   ORDER BY {{ automate_dv.prefix([src_ldts], 'ru') }}, {{ automate_dv.prefix([src_source], 'ru') }} ASC
               ) AS rn
        FROM stage_union AS ru
    ) AS q
    WHERE q.rn = 1
),

records_to_insert AS (
    SELECT {{ automate_dv.prefix(source_cols, 'a', alias_target='target') }}
    FROM row_rank_union AS a
    {%- if automate_dv.is_any_incremental() %}
    LEFT ANTI JOIN {{ this }} AS d
    ON {{ automate_dv.multikey(src_pk, prefix=['a','d'], condition='=') }}
    {%- endif %}
)

SELECT * FROM records_to_insert

{%- endmacro -%}


{%- macro spark__hub(src_pk, src_nk, src_extra_columns, src_ldts, src_source, source_model) -%}
{%- set source_cols = automate_dv.expand_column_list(columns=[src_pk, src_nk, src_extra_columns, src_ldts, src_source]) -%}
{{ _spark_insert_new_keys(source_cols, src_pk, automate_dv.expand_column_list([src_pk]), src_ldts, src_source, source_model) }}
{%- endmacro -%}


{%- macro spark__link(src_pk, src_fk, src_extra_columns, src_ldts, src_source, source_model) -%}
{%- set source_cols = automate_dv.expand_column_list(columns=[src_pk, src_fk, src_extra_columns, src_ldts, src_source]) -%}
{%- set not_null_cols = automate_dv.expand_column_list([src_pk]) + automate_dv.expand_column_list([src_fk]) -%}
{{ _spark_insert_new_keys(source_cols, src_pk, not_null_cols, src_ldts, src_source, source_model) }}
{%- endmacro -%}


{%- macro spark__sat(src_pk, src_hashdiff, src_payload, src_extra_columns, src_eff, src_ldts, src_source, source_model) -%}

{%- set apply_source_filter = automate_dv.config_meta_get('apply_source_filter', false) -%}
{%- set source_cols = automate_dv.expand_column_list(columns=[src_pk, src_hashdiff, src_payload, src_extra_columns, src_eff, src_ldts, src_source]) -%}
{%- set window_cols = automate_dv.expand_column_list(columns=[src_pk, src_hashdiff, src_ldts]) -%}
{%- set is_incremental = automate_dv.is_any_incremental() -%}
{%- set lag_default = automate_dv.cast_binary('FFFFFFFF', quote=true) -%}

WITH source_data AS (
    SELECT {{ automate_dv.prefix(source_cols, 'a', alias_target='source') }}
    FROM {{ ref(source_model) }} AS a
    WHERE {{ automate_dv.multikey(src_pk, prefix='a', condition='IS NOT NULL') }}
),

{%- if is_incremental %}

{#- Phiên bản mới nhất trong Satellite của các khóa có mặt trong stage #}
latest_records AS (
    SELECT {{ automate_dv.alias_all(window_cols, 'q') }}
    FROM (
        SELECT {{ automate_dv.prefix(window_cols, 'current_records', alias_target='target') }},
               ROW_NUMBER() OVER (
                   PARTITION BY {{ automate_dv.prefix([src_pk], 'current_records') }}
                   ORDER BY {{ automate_dv.prefix([src_ldts], 'current_records') }} DESC
               ) AS rn
        FROM {{ this }} AS current_records
        LEFT SEMI JOIN source_data AS source_records
            ON {{ automate_dv.multikey(src_pk, prefix=['source_records','current_records'], condition='=') }}
    ) AS q
    WHERE q.rn = 1
),

{%- if apply_source_filter %}

{#- Chỉ cho đi tiếp dòng của khóa mới, hoặc dòng có load_date sau phiên bản mới nhất (R-08).
    Chạy lại kỳ cũ vì vậy sinh 0 dòng. Dòng đến trễ của một tháng cũ cũng bị bỏ: nếu chèn nó, LAG sẽ so
    với phiên bản mới nhất thay vì tháng liền trước và có thể sinh phiên bản sai (review R-26). #}
valid_stg AS (
    SELECT {{ automate_dv.prefix(source_cols, 's', alias_target='source') }}
    FROM source_data AS s
    LEFT JOIN latest_records AS lr
        ON {{ automate_dv.multikey(src_pk, prefix=['s', 'lr'], condition='=') }}
    WHERE {{ automate_dv.multikey(src_pk, prefix='lr', condition='IS NULL') }}
       OR {{ automate_dv.prefix([src_ldts], 's') }} > {{ automate_dv.prefix([src_ldts], 'lr') }}
),
{%- endif %}

{%- endif %}

{%- set source_table = 'valid_stg' if (is_incremental and apply_source_filter) else 'source_data' -%}

{#- Giữ dòng có hash_diff khác phiên bản liền trước: trong stage theo load_date,
    còn dòng đầu tiên của mỗi khóa thì so với phiên bản mới nhất đã có trong Satellite #}
unique_source_records AS (
    SELECT {{ automate_dv.alias_all(source_cols, 'q') }}
    FROM (
        SELECT {{ automate_dv.prefix(source_cols, 'sd', alias_target='source') }},
               LAG({{ automate_dv.prefix([src_hashdiff], 'sd', alias_target='source') }}, 1,
                   {%- if is_incremental %}
                   COALESCE({{ automate_dv.prefix([src_hashdiff], 'lr', alias_target='target') }}, {{ lag_default }})
                   {%- else %}
                   {{ lag_default }}
                   {%- endif %}
               ) OVER (
                   PARTITION BY {{ automate_dv.prefix([src_pk], 'sd', alias_target='source') }}
                   ORDER BY {{ automate_dv.prefix([src_ldts], 'sd', alias_target='source') }} ASC
               ) AS prev_hashdiff
        FROM {{ source_table }} AS sd
        {%- if is_incremental %}
        LEFT OUTER JOIN latest_records AS lr
            ON {{ automate_dv.multikey(src_pk, prefix=['sd','lr'], condition='=') }}
        {%- endif %}
    ) AS q
    WHERE {{ automate_dv.prefix([src_hashdiff], 'q') }} != q.prev_hashdiff
)

SELECT * FROM unique_source_records

{%- endmacro -%}
