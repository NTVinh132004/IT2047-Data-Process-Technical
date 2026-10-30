{#- Mọi cặp khoản vay × servicer đã từng xuất hiện trong perf (R-21) -#}
{{ automate_dv.link(src_pk='LOAN_SERVICER_HK', src_fk=['LOAN_HK', 'SERVICER_HK'], src_ldts='load_date',
                    src_source='record_source', source_model='stg_perf') }}
