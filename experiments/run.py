"""Điều phối thực nghiệm C5 trên stack thực nghiệm riêng (scripts/experiment.sh, R-38).

- TN1 mở rộng quy mô: p25, p50, p100 của sample; mỗi lần dựng stack và lake mới, chạy make run-all, đo end-to-end
  và thời gian bận từng tầng từ control.layer_run, kiểm AC-01, AC-05, AC-06 của lần chạy.
- TN2 nạp Raw Vault: incremental một kỳ so với --full-refresh mọi kỳ đã có, tại các mốc số kỳ; số dòng hai cách
  phải bằng nhau. Lần incremental lặp lại được nhờ RESTORE Delta về phiên bản trước lần đo.
- TN4, TN7: PySpark trong container (experiments/spark_bench.py).
- TN6 Satellite tách và gộp: dựng lại ba Satellite perf và Satellite gộp (dbt/models/experiments) bằng full refresh.

Lake sample báo cáo không bị đụng. Mọi kết quả thô ở experiments/results/*.csv, không chứa dữ liệu khoản vay.

Chạy: uv run python -m experiments.run all | tn1 | tn2 | tn4 | tn6 | tn7 [--reps 3]
"""
import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

from ingestion.config import Config
from ingestion.periods import periods_between

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "experiments/results"
LAKE = ROOT / "data/lake-exp"
SUBSETS = ("p25", "p50", "p100")
RAW_VAULT = sorted(p.stem for p in (ROOT / "dbt/models/raw_vault").glob("*.sql"))
TN2_CHECKPOINTS = (4, 12, 20, 29)
# Chạy thử nhỏ (EP-04): EXP_TN2_CHECKPOINTS=4 uv run python -m experiments.run tn2 --reps 1


# Code quyết định kết quả thực nghiệm; cổng C5 so digest này với digest lúc đo (EP-06). charts.py chỉ vẽ, không tính
CODE_PATHS = ("experiments", "ingestion", "dbt/models", "dbt/macros", "dbt/dbt_project.yml", "conf", "docker",
              "dags", "scripts/experiment.sh", "scripts/run_all.sh", "scripts/wait_periods.sh", "docker-compose.yml")


def code_digest() -> str:
    """Chỉ băm file git nhìn thấy (đã track hoặc chưa track nhưng không bị ignore), để bản clone sạch ra cùng digest;
    file bị ignore như gói dbt của spike hay wheel không nằm trong clone (C6)."""
    names = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "--", *CODE_PATHS], cwd=ROOT,
                           capture_output=True, text=True, check=True).stdout.splitlines()
    digest = hashlib.sha256()
    for name in sorted(set(names)):
        path = ROOT / name
        if path.is_file() and "results" not in Path(name).parts and path.name != "charts.py":
            digest.update(name.encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()


def mark_done(step: str) -> None:
    manifest_path = RESULTS / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    manifest[step] = {"code_digest": code_digest(), "commit": commit,
                      "finished_at": datetime.now().isoformat(timespec="seconds")}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")


def log(message: str) -> None:
    print(f"{datetime.now():%H:%M:%S} {message}", flush=True)


def exp(*args: str, subset: str = "p100", stdin: str | None = None, timeout: int = 4 * 3600) -> str:
    run = subprocess.run(["scripts/experiment.sh", *args], cwd=ROOT, env={**os.environ, "EXP_SUBSET": subset},
                         input=stdin, capture_output=True, text=True, timeout=timeout)
    if run.returncode != 0:
        raise RuntimeError(f"Lỗi {' '.join(args)} ({run.returncode}):\n{run.stdout[-3000:]}\n{run.stderr[-3000:]}")
    return run.stdout


def in_scheduler(command: str, timeout: int = 4 * 3600) -> str:
    return exp("compose", "exec", "-T", "airflow-scheduler", "bash", "-c", command, timeout=timeout)


def psql_json(sql: str) -> object:
    out = exp("compose", "exec", "-T", "postgres", "sh", "-c",
              'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d analytics -At', stdin=f"SELECT json_build_object('r', ({sql}));")
    return json.loads(out.strip().splitlines()[-1])["r"]


def spark_sql(*statements: str) -> list[list[dict]]:
    out = exp("compose", "exec", "-T", "airflow-scheduler", "bash", "-c",
              "cd /opt/project && /opt/dbt-venv/bin/python -m experiments.thrift_sql", stdin=json.dumps(list(statements)))
    return json.loads(out.strip().splitlines()[-1])


class Recorder:
    def __init__(self, name: str):
        RESULTS.mkdir(parents=True, exist_ok=True)
        self.final, self.path = RESULTS / f"{name}.csv", RESULTS / f"{name}.csv.partial"
        self.path.unlink(missing_ok=True)
        self.fields: list[str] | None = None

    def add(self, **row) -> None:
        row = {"measured_at": datetime.now().isoformat(timespec="seconds"), **row}
        new = self.fields is None
        self.fields = self.fields or list(row)
        with self.path.open("a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.fields)
            if new:
                writer.writeheader()
            writer.writerow(row)
        log(json.dumps(row, default=str))

    def done(self) -> None:
        self.path.replace(self.final)


# ---------------------------------------------------------------- stack

def reset_stack(subset: str) -> float:
    """Dừng stack thực nghiệm, xóa volume và lake của nó, dựng lại. Trả về thời gian khởi động."""
    exp("down", subset=subset)
    shutil.rmtree(LAKE, ignore_errors=True)
    start = time.perf_counter()
    exp("up", subset=subset, timeout=1800)
    # DAG phải được dag-processor nạp trước khi make run-all trigger layer_ingest
    for _ in range(60):
        dags = exp("compose", "exec", "-T", "airflow-scheduler", "airflow", "dags", "list", "-o", "plain", subset=subset)
        if "layer_ingest" in dags and "layer_export" in dags:
            break
        time.sleep(5)
    else:
        raise RuntimeError("DAG chưa được nạp sau 5 phút")
    return round(time.perf_counter() - start, 1)


def source_lines(subset: str) -> dict:
    folder = ROOT / ("data/raw" if subset == "p100" else f"data/raw-exp/{subset}") / "sample_2019"
    return {kind: sum(1 for _ in (folder / f"sample_{kind}_2019.txt").open("rb")) for kind in ("orig", "perf")}


RUN_SUMMARY = """
WITH ok AS (SELECT * FROM control.layer_run WHERE status = 'SUCCESS'),
batches AS (SELECT layer, airflow_run_id, details->>'batch' AS batch, MAX(duration_s) AS d FROM ok GROUP BY 1, 2, 3),
i AS (SELECT * FROM ok WHERE layer = 'ingest'), q AS (SELECT * FROM ok WHERE layer = 'quality')
SELECT json_build_object(
  'bronze_orig', (SELECT SUM(bronze_orig_rows) FROM i),
  'bronze_perf', (SELECT SUM(bronze_perf_rows) FROM i),
  'ac06_bad_periods', (SELECT COUNT(*) FROM i JOIN q USING (period) WHERE
      i.bronze_orig_rows <> (q.details->>'orig_clean')::bigint + (q.details->>'orig_quarantine')::bigint + (q.details->>'orig_dedup')::bigint
   OR i.bronze_perf_rows <> (q.details->>'perf_clean')::bigint + (q.details->>'perf_quarantine')::bigint + (q.details->>'perf_dedup')::bigint),
  'quarantine', (SELECT SUM(rows_rejected) FROM q),
  'periods_complete', (SELECT COUNT(*) FROM (SELECT period FROM ok GROUP BY period HAVING COUNT(DISTINCT layer) = 6) AS c),
  'failed_runs', (SELECT COUNT(*) FROM control.layer_run WHERE status = 'FAILED'),
  'layers', (SELECT json_object_agg(layer, json_build_object('busy_s', busy, 'batches', n))
             FROM (SELECT layer, SUM(d) AS busy, COUNT(*) AS n FROM batches GROUP BY layer) AS b))
"""

AC05 = ("WITH b AS (SELECT reporting_period, COUNT(*) AS n, SUM(CAST(current_upb AS DECIMAL(20,4))) AS upb FROM bronze.perf GROUP BY reporting_period),"
        " f AS (SELECT DATE_FORMAT(reporting_date,'yyyyMM') AS reporting_period, COUNT(*) AS n, SUM(current_upb) AS upb FROM gold.fact_loan_month GROUP BY reporting_date)"
        " SELECT COUNT(*) AS months, SUM(CASE WHEN NOT (b.upb <=> f.upb) OR NOT (b.n <=> f.n) THEN 1 ELSE 0 END) AS wrong"
        " FROM b FULL OUTER JOIN f ON b.reporting_period=f.reporting_period")


def tn1(reps: int) -> None:
    rec = Recorder("tn1_scale")
    for rep in range(1, reps + 1):
        for subset in SUBSETS:  # p100 cuối cùng: lake còn lại là bộ sample đủ cho TN4, TN6, TN7, TN2
            log(f"TN1 lần {rep} {subset}: dựng stack mới")
            startup = reset_stack(subset)
            start = time.perf_counter()
            exp("run-all", subset=subset)
            seconds = round(time.perf_counter() - start, 1)
            summary = psql_json(RUN_SUMMARY)
            ac05 = spark_sql(AC05)[0][0]
            source = source_lines(subset)
            layers = summary["layers"]
            rec.add(experiment="TN1", subset=subset, run=rep, warmup=False, end_to_end_s=seconds, startup_s=startup,
                    source_orig=source["orig"], source_perf=source["perf"],
                    bronze_orig=summary["bronze_orig"], bronze_perf=summary["bronze_perf"],
                    ac01=summary["bronze_orig"] == source["orig"] and summary["bronze_perf"] == source["perf"],
                    ac06=summary["ac06_bad_periods"] == 0, ac05=int(ac05["wrong"]) == 0 and int(ac05["months"]) > 0,
                    quarantine=summary["quarantine"], periods_complete=summary["periods_complete"],
                    failed_runs=summary["failed_runs"],
                    **{f"{layer}_s": layers.get(layer, {}).get("busy_s") for layer in
                       ("ingest", "quality", "raw_vault", "business_vault", "gold", "export")},
                    **{f"{layer}_batches": layers.get(layer, {}).get("batches") for layer in ("raw_vault", "business_vault")})
    rec.done()


# ---------------------------------------------------------------- dbt

def dbt(select: str, variables: dict, full_refresh: bool = False) -> tuple[float, dict]:
    variables = {"inject_test_failure": False, "load_lag_months": Config().lag_months, **variables}
    flags = " --full-refresh" if full_refresh else ""
    command = (f"cd /opt/project/dbt && /opt/dbt-venv/bin/dbt run --select {select} --exclude tag:hash_test"
               f" --vars '{json.dumps(variables)}'{flags}")
    start = time.perf_counter()
    in_scheduler(command)
    seconds = round(time.perf_counter() - start, 1)
    results = json.loads((ROOT / "dbt/target/run_results.json").read_text())["results"]
    models = {r["unique_id"].split(".")[-1]: round(r["execution_time"], 2) for r in results}
    return seconds, models


def table_stats(tables: list[str], schema: str) -> dict:
    statements = []
    for t in tables:
        statements += [f"SELECT COUNT(*) AS n FROM {schema}.{t}", f"DESCRIBE DETAIL {schema}.{t}"]
    out = spark_sql(*statements)
    return {t: {"rows": int(out[2 * i][0]["n"]), "size_bytes": int(out[2 * i + 1][0]["sizeInBytes"]),
                "num_files": int(out[2 * i + 1][0]["numFiles"])} for i, t in enumerate(tables)}


def tn2(reps: int) -> None:
    rec = Recorder("tn2_incremental")
    cfg = Config()
    periods = periods_between(cfg.pipeline["periods"]["first"], cfg.pipeline["periods"]["last"])
    checkpoints = [int(k) for k in os.environ.get("EXP_TN2_CHECKPOINTS", "").split(",") if k] or TN2_CHECKPOINTS
    for k in checkpoints:
        log(f"TN2 mốc {k} kỳ: dựng trạng thái {k - 1} kỳ (không đo)")
        dbt("+raw_vault", {"periods": periods[:k - 1]}, full_refresh=True)
        versions = {t: spark_sql(f"DESCRIBE HISTORY raw_vault.{t} LIMIT 1")[0][0]["version"] for t in RAW_VAULT}
        for run in range(reps + 1):
            seconds, models = dbt("+raw_vault", {"periods": [periods[k - 1]]})
            stats = table_stats(RAW_VAULT, "raw_vault")
            rec.add(experiment="TN2", method="incremental", periods_loaded=k, run=run, warmup=run == 0,
                    wall_s=seconds, raw_vault_s=round(sum(models.get(t, 0) for t in RAW_VAULT), 2),
                    satellites_s=round(sum(v for m, v in models.items() if m.startswith("sat_")), 2),
                    rows=sum(s["rows"] for s in stats.values()), size_bytes=sum(s["size_bytes"] for s in stats.values()),
                    rows_by_table=json.dumps({t: s["rows"] for t, s in stats.items()}), rows_match_incremental="")
            if run < reps:
                spark_sql(*[f"RESTORE TABLE raw_vault.{t} TO VERSION AS OF {v}" for t, v in versions.items()])
        incremental_rows = {t: s["rows"] for t, s in stats.items()}
        for run in range(reps + 1):
            seconds, models = dbt("+raw_vault", {"periods": periods[:k]}, full_refresh=True)
            stats = table_stats(RAW_VAULT, "raw_vault")
            rows = {t: s["rows"] for t, s in stats.items()}
            rec.add(experiment="TN2", method="full_refresh", periods_loaded=k, run=run, warmup=run == 0,
                    wall_s=seconds, raw_vault_s=round(sum(models.get(t, 0) for t in RAW_VAULT), 2),
                    satellites_s=round(sum(v for m, v in models.items() if m.startswith("sat_")), 2),
                    rows=sum(rows.values()), size_bytes=sum(s["size_bytes"] for s in stats.values()),
                    rows_by_table=json.dumps(rows), rows_match_incremental=rows == incremental_rows)
    rec.done()


TN6_SPLIT = ["sat_loan_balance", "sat_loan_delinquency", "sat_loan_termination"]
TN6_MERGED = ["exp_sat_loan_perf_merged"]


DELINQUENCY = ["delinquency_status", "modification_flag", "interest_rate_step_flag", "payment_deferral_flag",
               "borrower_assistance_plan", "disaster_delinquency_flag", "mi_cancellation_flag"]
_DQ = ", ".join(DELINQUENCY)
TN6_QUERIES = {
    # Lịch sử quá hạn: bảng tách đã chỉ chứa phiên bản khi nhóm quá hạn đổi
    "split": f"SELECT COUNT(*) AS n, SUM(CAST(xxhash64(LOAN_HK, load_date, {_DQ}) AS DECIMAL(38, 0))) AS h"
             f" FROM raw_vault.sat_loan_delinquency",
    # Bảng gộp có phiên bản mỗi khi bất kỳ nhóm nào đổi: phải so với dòng trước của khoản vay để lọc ra thay đổi
    "merged": f"SELECT COUNT(*) AS n, SUM(CAST(xxhash64(LOAN_HK, load_date, {_DQ}) AS DECIMAL(38, 0))) AS h FROM ("
              f" SELECT *, LAG(xxhash64({_DQ})) OVER (PARTITION BY LOAN_HK ORDER BY load_date) AS prev"
              f" FROM experiments.exp_sat_loan_perf_merged) AS v"
              f" WHERE prev IS NULL OR prev <> xxhash64({_DQ})",
}


def tn6(reps: int) -> None:
    rec = Recorder("tn6_split")
    select = "+exp_sat_loan_perf_merged " + " ".join(TN6_SPLIT)
    for run in range(reps + 1):
        seconds, models = dbt(select, {"periods": [], "experiments": True}, full_refresh=True)
        rec.add(experiment="TN6", run=run, warmup=run == 0, wall_s=seconds,
                split_sat_s=round(sum(models[m] for m in TN6_SPLIT), 2),
                merged_sat_s=models["exp_sat_loan_perf_merged"], merged_stage_s=models["exp_stg_perf_merged"],
                stg_perf_s=models.get("stg_perf"))
    rec.done()
    rec = Recorder("tn6_storage")
    for design, tables, schema in (("split", TN6_SPLIT, "raw_vault"), ("merged", TN6_MERGED, "experiments")):
        for t, s in table_stats(tables, schema).items():
            rec.add(experiment="TN6", design=design, table=t, **s)
    rec.done()
    rec = Recorder("tn6_query")
    for design, sql in TN6_QUERIES.items():
        for run in range(reps + 1):
            start = time.perf_counter()
            row = spark_sql("CLEAR CACHE", sql)[1][0]
            rec.add(experiment="TN6", query="delinquency_history", design=design, run=run, warmup=run == 0,
                    seconds=round(time.perf_counter() - start, 3), rows=row["n"], checksum=row["h"])
    rec.done()


def bench(name: str, reps: int) -> None:
    in_scheduler(f"cd /opt/project && python -m experiments.spark_bench {name} --reps {reps}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("experiment", choices=["all", "tn1", "tn2", "tn4", "tn6", "tn7"])
    parser.add_argument("--reps", type=int, default=3)
    args = parser.parse_args()
    # Thứ tự của all: TN1 để lại lake p100 đầy đủ; TN2 dựng lại Raw Vault nhiều lần nên chạy cuối
    steps = ["tn1", "tn4", "tn7", "tn6", "tn2"] if args.experiment == "all" else [args.experiment]
    for step in steps:
        log(f"Bắt đầu {step}")
        if step in ("tn4", "tn7"):
            bench(step, args.reps)
        else:
            globals()[step](args.reps)
        mark_done(step)
        log(f"Xong {step}")


if __name__ == "__main__":
    main()
