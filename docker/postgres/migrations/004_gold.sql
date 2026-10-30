-- Migration idempotente, giữ nguyên dữ liệu và nhật ký cũ.
ALTER TABLE control.layer_run DROP CONSTRAINT IF EXISTS layer_run_layer_check;
ALTER TABLE control.layer_run ADD CONSTRAINT layer_run_layer_check
 CHECK (layer IN ('ingest','quality','raw_vault','business_vault','gold','export'));
CREATE SCHEMA IF NOT EXISTS serving;
CREATE SCHEMA IF NOT EXISTS export_stage;
