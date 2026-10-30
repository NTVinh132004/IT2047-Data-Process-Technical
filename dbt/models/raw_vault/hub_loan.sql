{#- Khoản vay vào Hub ở kỳ đầu tiên nó xuất hiện, từ orig hoặc perf (PRD mục 6) -#}
{{ automate_dv.hub(src_pk='LOAN_HK', src_nk='loan_id', src_ldts='load_date', src_source='record_source',
                   source_model=['stg_orig', 'stg_perf']) }}
