{#- Bảng đối chứng kiểu star schema ghi đè (SCD1), FR-14: mỗi khoản vay một dòng, lần nạp sau ghi đè lần trước.
    Cùng đợt sửa dữ liệu được nạp vào đây và vào Data Vault; AC-09 so hai bên: Data Vault còn cả giá trị cũ và mới,
    bảng này chỉ còn giá trị mới. Không dùng cho phân tích. -#}
{{ config(materialized='incremental', incremental_strategy='merge', unique_key='LOAN_HK') }}

SELECT
    LOAN_HK,
    loan_id,
    credit_score,
    orig_dti,
    orig_ltv,
    orig_cltv,
    orig_upb,
    orig_interest_rate,
    first_payment_date,
    maturity_date,
    seller_name,
    load_date AS last_load_date,
    record_source
FROM {{ ref('stg_orig') }}
