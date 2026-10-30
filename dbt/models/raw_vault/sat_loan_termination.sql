{{ automate_dv.sat(src_pk='LOAN_HK', src_hashdiff='TERMINATION_HASHDIFF', src_ldts='load_date', src_source='record_source',
                   src_payload=['zero_balance_code', 'zero_balance_date', 'zero_balance_removal_upb', 'ddlpi',
                                'defect_settlement_date', 'net_sales_proceeds', 'mi_recoveries', 'non_mi_recoveries',
                                'total_expenses', 'legal_costs', 'maintenance_costs', 'taxes_insurance', 'misc_expenses',
                                'delinquent_accrued_interest', 'actual_loss', 'bankruptcy_cramdown_costs'],
                   src_eff=none, source_model='stg_perf_termination') }}
