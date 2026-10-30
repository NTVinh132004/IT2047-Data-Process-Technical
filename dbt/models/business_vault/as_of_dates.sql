{#- Snapshot table (R-33): mỗi lần nạp tháng là một mốc PIT. Lấy từ record tracking satellite nên chỉ đọc Raw Vault.
    Mốc của đợt sửa dữ liệu (FR-14) cũng là một mốc, để PIT trả về trạng thái trước và sau đợt sửa. -#}
SELECT DISTINCT x.load_date AS AS_OF_DATE
FROM {{ ref('xts_loan') }} AS x
{%- if is_incremental() %}
LEFT ANTI JOIN {{ this }} AS existing ON existing.AS_OF_DATE = x.load_date
{%- endif %}
