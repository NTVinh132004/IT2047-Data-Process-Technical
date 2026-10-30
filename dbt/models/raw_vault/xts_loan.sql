{#- Record tracking satellite (R-33): mỗi lần khoản vay xuất hiện trong một lần nạp, từ orig hoặc perf.
    Satellite chỉ thêm dòng khi hash_diff đổi nên không cho biết khoản vay có báo cáo tháng nào; bảng này ghi điều đó
    để PIT và Business Vault chỉ đọc Raw Vault (datavault4dbt: "track the appearance of a hashkey").
    Giá trị theo dõi (HASHDIFF) là chính hash key: xts chống trùng theo (HASHDIFF, load_date, SATELLITE_NAME), dùng hash
    payload thì hai khoản vay có payload giống nhau ở cùng lần nạp sẽ va nhau. SATELLITE_NAME là nguồn: 'orig' / 'perf'. -#}
{{ automate_dv.xts(src_pk='LOAN_HK',
                   src_satellite={'presence': {'sat_name': {'SATELLITE_NAME': 'TRACK_SOURCE'},
                                               'hashdiff': {'HASHDIFF': 'LOAN_HK'}}},
                   src_ldts='load_date', src_source='record_source',
                   source_model=['stg_orig', 'stg_perf']) }}
