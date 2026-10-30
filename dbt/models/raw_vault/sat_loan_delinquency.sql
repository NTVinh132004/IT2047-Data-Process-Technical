{#- reporting_period: ngày nghiệp vụ (applied date) của tháng phiên bản bắt đầu hiệu lực; không tính vào
    hash_diff (R-33). Nạp Raw Vault chỉ có điều kiện kỹ thuật, không lọc nghiệp vụ. -#}
{{ automate_dv.sat(src_pk='LOAN_HK', src_hashdiff='DELINQUENCY_HASHDIFF', src_ldts='load_date', src_source='record_source',
                   src_payload=['reporting_period', 'delinquency_status', 'modification_flag', 'interest_rate_step_flag', 'payment_deferral_flag',
                                'borrower_assistance_plan', 'disaster_delinquency_flag', 'mi_cancellation_flag'],
                   src_eff=none, source_model='stg_perf') }}
