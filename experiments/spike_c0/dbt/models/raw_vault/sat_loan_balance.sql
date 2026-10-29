{{ automate_dv.sat(src_pk='LOAN_HK', src_hashdiff='BALANCE_HASHDIFF',
                   src_payload=['current_upb', 'interest_bearing_upb', 'non_interest_bearing_upb',
                                'current_interest_rate', 'loan_age', 'remaining_months', 'eltv',
                                'cumulative_modification_cost', 'current_modification_cost'],
                   src_eff=none, src_ldts='LOAD_DATE', src_source='RECORD_SOURCE',
                   source_model='stg_perf') }}
