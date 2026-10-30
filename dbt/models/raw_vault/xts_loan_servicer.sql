{#- Record tracking satellite cho link_loan_servicer (R-33): cặp khoản vay–servicer có mặt ở mỗi lần nạp perf, nên biết
    servicer của tháng m mà không cần effectivity satellite (FR-11 đã cắt). Khóa chính là LOAN_HK (khoản vay là driving
    key); HASHDIFF là hash key của Link, cùng lý do như xts_loan. -#}
{{ automate_dv.xts(src_pk='LOAN_HK',
                   src_satellite={'link_loan_servicer': {'sat_name': {'SATELLITE_NAME': 'TRACK_LINK_LOAN_SERVICER'},
                                                         'hashdiff': {'HASHDIFF': 'LOAN_SERVICER_HK'}}},
                   src_ldts='load_date', src_source='record_source',
                   source_model='stg_perf') }}
