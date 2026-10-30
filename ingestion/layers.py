"""Việc của từng tầng cho một kỳ (R-33). Job theo tầng (dags/layers.py) nhận kỳ từ bảng điều khiển rồi gọi run().

- ingest: landing (chuyển TXT sang Delta khi nguồn đổi, R-28) và Bronze (FR-04)
- quality: cổng chất lượng (FR-07)
- raw_vault: dbt build staging, Raw Vault và bảng đối chứng ghi đè cho kỳ, kèm dbt test (FR-08 đến FR-10, FR-14, FR-22)
- business_vault: dbt build snapshot table, PIT, Satellite tính toán, kèm dbt test (FR-12, FR-13, FR-22). Không dùng
  biến periods: Business Vault xử lý mọi mốc có trong Raw Vault mà chưa có trong PIT
Tầng dbt nhận một lô kỳ liền nhau trong một lần build (R-34): chi phí cố định của khoảng 100 câu SQL mỗi lần build
chỉ trả một lần cho cả lô
"""
import json
import subprocess

DBT_DIR = "/opt/project/dbt"
DBT = "/opt/dbt-venv/bin/dbt"
# --indirect-selection cautious: chỉ chạy test mà mọi model cha thuộc tầng đang build. Chế độ mặc định (eager) kéo
# theo cả test của tầng sau có tham chiếu tới tầng này (ví dụ test quan hệ bsat_* → hub_loan) khi tầng sau chưa có
DBT_SELECT = {
    "raw_vault": ["--select", "+raw_vault", "baseline", "--exclude", "tag:hash_test", "--indirect-selection", "cautious"],
    "business_vault": ["--select", "business_vault", "--indirect-selection", "cautious"],
    "gold": ["--select", "gold", "--indirect-selection", "cautious"],
}


def _dbt_build(layer: str, periods: list[str], options: dict) -> dict:
    from ingestion.config import Config
    variables = {"periods": periods, "inject_test_failure": bool(options.get("inject_test_failure", False))}
    variables["load_lag_months"] = Config().lag_months
    cmd = [DBT, "build", *DBT_SELECT[layer], "--vars", json.dumps(variables)]
    run = subprocess.run(cmd, cwd=DBT_DIR, capture_output=True, text=True)
    print(run.stdout[-20000:])  # vào log task Airflow
    if run.returncode != 0:
        raise RuntimeError(f"dbt build {layer} lỗi (mã {run.returncode}):\n{run.stdout[-3000:]}\n{run.stderr[-2000:]}")
    summary = next((line for line in reversed(run.stdout.splitlines()) if "Done. PASS=" in line), "")
    return {"dbt": summary.split("Done. ", 1)[-1].strip()}


def run(layer: str, periods: list[str], options: dict | None = None) -> dict:
    # Gold thay bảng Delta; export phải đọc một bản đã hoàn tất, không đọc giữa hai model.
    if layer in ("gold", "export"):
        from ingestion.control import connect
        from ingestion.config import Config
        conn = connect()
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_lock(hashtext('gold_publication'))")
                cur.execute("CREATE TABLE IF NOT EXISTS control.gold_publication"
                            " (dataset TEXT PRIMARY KEY, ready BOOLEAN NOT NULL)")
                dataset = Config().source
                if layer == 'gold':
                    # Cờ đã commit trước build: nếu job chết hoặc test trượt thì export phải chờ retry.
                    cur.execute("INSERT INTO control.gold_publication VALUES (%s, FALSE)"
                                " ON CONFLICT (dataset) DO UPDATE SET ready=FALSE", (dataset,))
                else:
                    cur.execute("SELECT ready FROM control.gold_publication WHERE dataset=%s", (dataset,))
                    ready = cur.fetchone()
                    if not ready or not ready[0]:
                        raise RuntimeError('Gold chưa có snapshot vượt qua dbt build; chưa công bố mart')
                result = _run(layer, periods, options)
                if layer == 'gold':
                    cur.execute("UPDATE control.gold_publication SET ready=TRUE WHERE dataset=%s", (dataset,))
                return result
        finally:
            conn.close()  # trả cả khóa session khi thành công, lỗi hoặc mất kết nối
    return _run(layer, periods, options)


def _run(layer: str, periods: list[str], options: dict | None = None) -> dict:
    """Xử lý một lô kỳ. Tầng PySpark (ingest, quality) chỉ nhận lô một kỳ; tầng dbt nhận cả lô trong một lần build."""
    options = options or {}
    if layer in DBT_SELECT:
        return _dbt_build(layer, periods, options)
    if layer == "export":
        from ingestion.export import run as export_marts
        return export_marts()
    (period,) = periods
    if layer == "ingest":
        from ingestion import bronze, landing
        from ingestion.config import Config

        cfg = Config()
        if period not in cfg.pipeline.get("corrections", {}):
            landing.ensure(cfg)
        counts = bronze.run(period)
        return {**counts, "rows_in": counts["bronze_orig_rows"] + counts["bronze_perf_rows"]}
    if layer == "quality":
        from ingestion import quality

        return quality.run(period)
    raise ValueError(f"Tầng không hợp lệ: {layer}")
