-- Ba database tách vai trò: metadata Hive, metadata Airflow, và analytics (mart xuất ra + load_control)
CREATE DATABASE metastore;
CREATE DATABASE airflow;
CREATE DATABASE analytics;
\connect analytics
CREATE SCHEMA control;
-- FR-02: mỗi lần chạy DAG một dòng. load_control là nhật ký chạy, không thuộc phép kiểm idempotent (R-02)
CREATE TABLE control.load_control (
    run_id          BIGSERIAL PRIMARY KEY,
    period          TEXT        NOT NULL,
    status          TEXT        NOT NULL CHECK (status IN ('RUNNING', 'SUCCESS', 'FAILED')),
    dataset         TEXT        NOT NULL,
    airflow_run_id  TEXT,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    duration_s      NUMERIC(10, 1),
    rows_in         BIGINT,
    rows_clean      BIGINT,
    rows_rejected   BIGINT,
    bronze_orig_rows BIGINT,
    bronze_perf_rows BIGINT,
    error           TEXT
);
CREATE INDEX ON control.load_control (period, status);
