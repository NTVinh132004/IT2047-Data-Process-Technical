{#- Áp đúng cấu hình hash của dự án lên các ca kiểm FR-06; tests/assert_hash_rules.sql kiểm kết quả -#}
{{ config(tags=['hash_test']) }}
{{ automate_dv.stage(include_source_columns=true, source_model='hash_cases',
                     hashed_columns={'HK': ['col_a', 'col_b'], 'HD': {'is_hashdiff': true, 'columns': ['col_a', 'col_b']}},
                     derived_columns=none, null_columns=none, ranked_columns=none) }}
