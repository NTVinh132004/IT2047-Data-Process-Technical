{#- reporting_period: ngày nghiệp vụ (applied date) của tháng phiên bản bắt đầu hiệu lực; không tính vào
    hash_diff (R-33). Nạp Raw Vault chỉ có điều kiện kỹ thuật, không lọc nghiệp vụ. -#}
{{ automate_dv.sat(src_pk='LOAN_HK', src_hashdiff='BALANCE_HASHDIFF', src_ldts='load_date', src_source='record_source',
                   src_payload=['reporting_period', 'current_upb', 'interest_bearing_upb', 'non_interest_bearing_upb', 'current_interest_rate',
                                'loan_age', 'remaining_months', 'eltv', 'cumulative_modification_cost',
                                'current_modification_cost'],
                   src_eff=none, source_model='stg_perf') }}
