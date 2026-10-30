{{ automate_dv.sat(src_pk='LOAN_HK', src_hashdiff='BALANCE_HASHDIFF', src_ldts='load_date', src_source='record_source',
                   src_payload=['current_upb', 'interest_bearing_upb', 'non_interest_bearing_upb', 'current_interest_rate',
                                'loan_age', 'remaining_months', 'eltv', 'cumulative_modification_cost',
                                'current_modification_cost'],
                   src_eff=none, source_model='stg_perf') }}
