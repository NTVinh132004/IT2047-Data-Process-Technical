-- Test cố ý sai (FR-22): chỉ bật khi DAG được kích hoạt với {"inject_test_failure": true}. Trả về một dòng của
-- hub_loan nên luôn lỗi; cổng C2 dùng nó để kiểm DAG dừng khi dbt test lỗi.
{{ config(enabled=var('inject_test_failure', false)) }}
SELECT LOAN_HK FROM {{ ref('hub_loan') }} LIMIT 1
