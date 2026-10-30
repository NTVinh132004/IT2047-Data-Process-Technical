{{ automate_dv.sat(src_pk='LOAN_HK', src_hashdiff='ORIGINATION_HASHDIFF', src_ldts='load_date', src_source='record_source',
                   src_payload=['credit_score', 'first_payment_date', 'maturity_date', 'first_time_homebuyer_flag', 'mi_pct',
                                'orig_cltv', 'orig_ltv', 'orig_dti', 'orig_upb', 'orig_interest_rate', 'orig_loan_term',
                                'channel', 'loan_purpose', 'number_of_borrowers', 'super_conforming_flag',
                                'special_eligibility_program'],
                   src_eff=none, source_model='stg_orig') }}
