{#- PIT theo cấu trúc chuẩn (FR-13, R-31, R-33): mỗi khoản vay × mốc trong as_of_dates mà khoản vay có mặt trong lần
    nạp đó (xts_loan), mỗi Satellite một cặp con trỏ (<SAT>_PK, <SAT>_LDTS) tới phiên bản hiệu lực = load_date lớn
    nhất không vượt quá mốc. Chưa có phiên bản thì trỏ tới ghost record (zero key, 1900-01-01), nên mọi join từ PIT là
    equi-join. Chỉ đọc Raw Vault.

    Nạp tăng dần theo dữ liệu: xử lý các mốc của as_of_dates chưa có trong bảng này, không phụ thuộc biến period.
    Với phiên bản trước các mốc mới chỉ lấy phiên bản cuối cùng của mỗi khoản vay, nên khối lượng tăng tuyến tính theo
    dữ liệu. Không dùng macro pit của automate_dv: macro đó dựng tích chéo mọi khoản vay × mọi mốc mỗi lần chạy
    (bộ đầy đủ khoảng 155 triệu dòng). -#}
{%- set satellites = ['sat_loan_origination', 'sat_loan_property', 'sat_loan_balance',
                      'sat_loan_delinquency', 'sat_loan_termination'] -%}
{%- set zero_key = "'" ~ ('0' * 64) ~ "'" -%}

WITH new_snapshots AS (
    SELECT s.AS_OF_DATE
    FROM {{ ref('as_of_dates') }} AS s
    {%- if is_incremental() %}
    LEFT ANTI JOIN (SELECT DISTINCT AS_OF_DATE FROM {{ this }}) AS done ON done.AS_OF_DATE = s.AS_OF_DATE
    {%- endif %}
),

grid AS (
    SELECT DISTINCT x.LOAN_HK, x.load_date AS AS_OF_DATE
    FROM {{ ref('xts_loan') }} AS x
    JOIN new_snapshots AS n ON n.AS_OF_DATE = x.load_date
),

bounds AS (
    SELECT MIN(AS_OF_DATE) AS lo, MAX(AS_OF_DATE) AS hi FROM grid
),

loans AS (
    SELECT DISTINCT LOAN_HK FROM grid
),

{% for sat in satellites %}
versions_{{ loop.index }} AS (
    SELECT s.LOAN_HK, s.load_date
    FROM {{ ref(sat) }} AS s
    CROSS JOIN bounds AS b
    LEFT SEMI JOIN loans AS l ON s.LOAN_HK = l.LOAN_HK
    WHERE s.load_date BETWEEN b.lo AND b.hi
    UNION ALL
    SELECT s.LOAN_HK, MAX(s.load_date)
    FROM {{ ref(sat) }} AS s
    CROSS JOIN bounds AS b
    LEFT SEMI JOIN loans AS l ON s.LOAN_HK = l.LOAN_HK
    WHERE s.load_date < b.lo
    GROUP BY s.LOAN_HK
),

pointer_{{ loop.index }} AS (
    SELECT g.LOAN_HK, g.AS_OF_DATE, MAX(v.load_date) AS ldts
    FROM grid AS g
    JOIN versions_{{ loop.index }} AS v
        ON v.LOAN_HK = g.LOAN_HK AND v.load_date <= g.AS_OF_DATE
    GROUP BY g.LOAN_HK, g.AS_OF_DATE
),
{% endfor %}

pit AS (
    SELECT
        g.LOAN_HK,
        g.AS_OF_DATE,
        {%- for sat in satellites %}
        CASE WHEN p{{ loop.index }}.ldts IS NULL THEN {{ zero_key }} ELSE g.LOAN_HK END AS {{ sat | upper }}_PK,
        COALESCE(p{{ loop.index }}.ldts, DATE'1900-01-01') AS {{ sat | upper }}_LDTS{{ "," if not loop.last }}
        {%- endfor %}
    FROM grid AS g
    {%- for sat in satellites %}
    LEFT JOIN pointer_{{ loop.index }} AS p{{ loop.index }}
        ON p{{ loop.index }}.LOAN_HK = g.LOAN_HK AND p{{ loop.index }}.AS_OF_DATE = g.AS_OF_DATE
    {%- endfor %}
)

SELECT * FROM pit
