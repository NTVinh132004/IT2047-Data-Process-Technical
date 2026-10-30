-- Ba database tách vai trò: metadata Hive, metadata Airflow, và analytics (mart xuất ra + bảng điều khiển)
CREATE DATABASE metastore;
CREATE DATABASE airflow;
CREATE DATABASE analytics;
\connect analytics
CREATE SCHEMA control;

-- Yêu cầu xử lý một kỳ (make run-all, make run PERIOD=..., make correction). Job theo tầng chỉ xử lý kỳ đã được yêu
-- cầu; force = xử lý lại mọi tầng kể cả tầng đã xong (ingestion/control.py, review R-33)
CREATE TABLE control.period_request (
    request_id    BIGSERIAL PRIMARY KEY,
    period        TEXT        NOT NULL,
    dataset       TEXT        NOT NULL,
    force         BOOLEAN     NOT NULL DEFAULT FALSE,
    options       JSONB       NOT NULL DEFAULT '{}',
    requested_at  TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX ON control.period_request (dataset, period, requested_at);

-- FR-02: mỗi lần một tầng xử lý một kỳ một dòng. Là nhật ký chạy nên không thuộc phép kiểm idempotent (R-02)
CREATE TABLE control.layer_run (
    run_id           BIGSERIAL PRIMARY KEY,
    period           TEXT        NOT NULL,
    layer            TEXT        NOT NULL CHECK (layer IN ('ingest', 'quality', 'raw_vault', 'business_vault', 'gold', 'export')),
    -- SUPERSEDED: lần SUCCESS bị vô hiệu vì tầng phải dựng lại (python -m ingestion.control invalidate); giữ để kiểm toán
    status           TEXT        NOT NULL CHECK (status IN ('RUNNING', 'SUCCESS', 'FAILED', 'SUPERSEDED')),
    dataset          TEXT        NOT NULL,
    started_at       TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    finished_at      TIMESTAMPTZ,
    lease_until      TIMESTAMPTZ,
    duration_s       NUMERIC(10, 1),
    rows_in          BIGINT,
    rows_clean       BIGINT,
    rows_rejected    BIGINT,
    bronze_orig_rows BIGINT,
    bronze_perf_rows BIGINT,
    details          JSONB,
    error            TEXT,
    airflow_run_id   TEXT
);
CREATE INDEX ON control.layer_run (dataset, period, layer, status);

-- Mỗi kỳ một dòng: lần SUCCESS gần nhất của từng tầng, số dòng của Bronze và cổng chất lượng (báo cáo G5)
CREATE VIEW control.load_control AS
WITH latest AS (
    SELECT DISTINCT ON (dataset, period, layer) *
    FROM control.layer_run
    WHERE status = 'SUCCESS'
    ORDER BY dataset, period, layer, finished_at DESC
)
SELECT
    dataset,
    period,
    MAX(finished_at) FILTER (WHERE layer = 'ingest')         AS ingest_at,
    MAX(finished_at) FILTER (WHERE layer = 'quality')        AS quality_at,
    MAX(finished_at) FILTER (WHERE layer = 'raw_vault')      AS raw_vault_at,
    MAX(finished_at) FILTER (WHERE layer = 'business_vault') AS business_vault_at,
    SUM(duration_s)                                          AS duration_s,
    MAX(rows_in)        FILTER (WHERE layer = 'ingest')      AS rows_in,
    MAX(rows_clean)     FILTER (WHERE layer = 'quality')     AS rows_clean,
    MAX(rows_rejected)  FILTER (WHERE layer = 'quality')     AS rows_rejected
FROM latest
GROUP BY dataset, period;
