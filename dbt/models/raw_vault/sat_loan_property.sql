{{ automate_dv.sat(src_pk='LOAN_HK', src_hashdiff='PROPERTY_HASHDIFF', src_ldts='load_date', src_source='record_source',
                   src_payload=['property_state', 'postal_code', 'msa_code', 'property_type', 'number_of_units',
                                'occupancy_status', 'property_valuation_method'],
                   src_eff=none, source_model='stg_orig') }}
