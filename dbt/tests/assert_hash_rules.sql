-- Unit test quy tắc hash (FR-06) trên SQL thật do automate_dv sinh ra. Mỗi dòng trả về là một quy tắc bị vi phạm.
{{ config(tags=['hash_test']) }}
WITH h AS (SELECT * FROM {{ ref('stg_hash_cases') }}),
c AS (SELECT case_id, HK, HD FROM h)
SELECT 'cung_dau_vao_cung_hash' AS rule FROM c a JOIN c b ON a.case_id = 1 AND b.case_id = 2 WHERE a.HK <> b.HK OR a.HD <> b.HD
UNION ALL
SELECT 'doi_mot_cot_thi_hashdiff_doi' FROM c a JOIN c b ON a.case_id = 1 AND b.case_id = 3 WHERE a.HD = b.HD
UNION ALL
SELECT 'thu_tu_null_khac_hash' FROM c a JOIN c b ON a.case_id = 4 AND b.case_id = 5 WHERE a.HK = b.HK OR a.HD = b.HD
UNION ALL
SELECT 'trim_va_upper_truoc_khi_hash' FROM c a JOIN c b ON a.case_id = 1 AND b.case_id = 6 WHERE a.HK <> b.HK
UNION ALL
SELECT 'sha256_noi_bang_hai_gach' FROM c WHERE case_id = 1 AND HK <> UPPER(SHA2('A||B', 256))
UNION ALL
SELECT 'null_thanh_hai_mu' FROM c WHERE case_id = 4 AND HK <> UPPER(SHA2('A||^^', 256))
UNION ALL
SELECT 'khoa_toan_null_thi_hash_null' FROM c WHERE case_id = 7 AND HK IS NOT NULL
