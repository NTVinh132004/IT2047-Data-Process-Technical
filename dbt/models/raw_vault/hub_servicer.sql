{#- Servicer lấy từ perf: Release 47 chuyển Servicer Name sang file perf (R-21) -#}
{{ automate_dv.hub(src_pk='SERVICER_HK', src_nk='servicer_name', src_ldts='load_date', src_source='record_source',
                   source_model='stg_perf') }}
