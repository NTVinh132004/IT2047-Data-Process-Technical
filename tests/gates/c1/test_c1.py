"""Cổng C1 (Kế hoạch mục 6): hạ tầng và Bronze.

- docker compose up: mọi service healthy
- AC-01 ở mọi kỳ của bộ mẫu: số dòng Bronze bằng số dòng nguồn của lát kỳ (đếm độc lập bằng Python thuần)
- load_date theo tháng đúng quy tắc periods.load_date_for (R-01)
- Chạy lại một kỳ: số dòng Bronze không đổi, control.layer_run thêm đúng 1 dòng cho mỗi tầng (R-33)
- Đổi tên một cột chỉ trong conf/ thì pipeline vẫn đọc đúng (FR-03, FR-05)
- Có số đo thời gian baseline

Lần chạy đầu nạp toàn bộ 29 kỳ của bộ mẫu (make run-all, khoảng 20–30 phút); các lần sau chỉ nạp kỳ chưa SUCCESS.
"""
import json
import shutil
import time
from collections import Counter, defaultdict
from glob import glob
from pathlib import Path

import psycopg
import pyarrow as pa
import pytest
import yaml
from deltalake import DeltaTable

from ingestion.config import Config
from ingestion.periods import load_date_for, period_of, periods_between
from tests.gates.conftest import ROOT, dotenv, save_gate_result, sh

RERUN_PERIOD = "2020Q1"
RENAME_PERIOD = "2019Q2"
RESULT: dict = {}


def host_path(container_path: Path) -> Path:
    """/data/raw/... trong container ứng với ./data/raw/... trên máy (docker-compose.yml)."""
    return ROOT / "data/raw" / Path(container_path).relative_to("/data/raw")


def bronze_table(cfg: Config, kind: str, database: str | None = None) -> DeltaTable:
    database = database or cfg.bronze["database"]
    return DeltaTable(str(ROOT / "data/lake/warehouse" / f"{database}.db" / cfg.bronze[f"{kind}_table"]))


def rows_per_period(table: DeltaTable) -> dict[str, int]:
    """Đếm từ thống kê file trong Delta log, không đọc dữ liệu."""
    # deltalake 1.x trả về bảng arro3; pa.table() chuyển sang pyarrow qua giao thức Arrow C stream
    actions = pa.table(table.get_add_actions(flatten=True)).to_pydict()
    counts: Counter = Counter()
    for period, n in zip(actions["partition.period"], actions["num_records"]):
        counts[period] += n
    return dict(counts)


def expected_slices(cfg: Config) -> tuple[dict[str, int], dict[str, int]]:
    """Số dòng nguồn của lát perf và lát orig theo kỳ, đếm thẳng từ file thô."""
    perf_loan = next(c.pos for c in cfg.perf.columns if c.role == "loan_key") - 1
    month = next(c.pos for c in cfg.perf.columns if c.role == "reporting_period") - 1
    orig_loan = next(c.pos for c in cfg.orig.columns if c.role == "loan_key") - 1
    perf_rows: Counter = Counter()
    first_month: dict[str, str] = {}
    for path in sorted(glob(str(host_path(cfg.raw_files(cfg.perf))))):
        with open(path) as f:
            for line in f:
                fields = line.rstrip("\n").split("|")
                perf_rows[period_of(fields[month])] += 1
                loan = fields[perf_loan]
                if loan not in first_month or fields[month] < first_month[loan]:
                    first_month[loan] = fields[month]
    orig_rows: Counter = Counter()
    for path in sorted(glob(str(host_path(cfg.raw_files(cfg.orig))))):
        with open(path) as f:
            for line in f:
                loan = line.split("|")[orig_loan]
                if loan in first_month:
                    orig_rows[period_of(first_month[loan])] += 1
    return dict(perf_rows), dict(orig_rows)


def analytics():
    env = dotenv()
    return psycopg.connect(host="127.0.0.1", port=5432, dbname="analytics",
                           user=env["POSTGRES_USER"], password=env["POSTGRES_PASSWORD"])


def layer_runs(cfg: Config) -> list[dict]:
    with analytics() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM control.layer_run WHERE dataset = %s ORDER BY run_id", (cfg.source,))
        names = [d.name for d in cur.description]
        return [dict(zip(names, row)) for row in cur.fetchall()]


@pytest.fixture(scope="module")
def cfg() -> Config:
    return Config()


@pytest.fixture(scope="module")
def stack():
    sh("make", "up", timeout=1800)


@pytest.fixture(scope="module")
def loaded(stack, cfg):
    start = time.monotonic()
    sh("make", "run-all", timeout=3 * 3600)
    RESULT['end_to_end_seconds'] = round(time.monotonic() - start, 1)
    return expected_slices(cfg)


@pytest.fixture(scope="module", autouse=True)
def record_results():
    yield
    save_gate_result("C1", RESULT)


def test_services_healthy(stack):
    services = [json.loads(line) for line in sh("docker", "compose", "ps", "--all", "--format", "json").stdout.splitlines()]
    states = {s["Service"]: (s["State"], s.get("Health", ""), s.get("ExitCode")) for s in services}
    RESULT["services"] = states
    assert states.pop("airflow-init")[2] == 0
    unhealthy = {name: st for name, st in states.items() if st[:2] != ("running", "healthy")}
    assert not unhealthy, unhealthy


def test_ac01_every_period(loaded, cfg):
    expected_perf, expected_orig = loaded
    periods = periods_between(cfg.pipeline["periods"]["first"], cfg.pipeline["periods"]["last"])
    actual_perf = rows_per_period(bronze_table(cfg, "perf"))
    actual_orig = rows_per_period(bronze_table(cfg, "orig"))
    RESULT["ac01"] = {p: {"perf": [actual_perf.get(p, 0), expected_perf.get(p, 0)],
                          "orig": [actual_orig.get(p, 0), expected_orig.get(p, 0)]} for p in periods}
    mismatches = {p: v for p, v in RESULT["ac01"].items() if v["perf"][0] != v["perf"][1] or v["orig"][0] != v["orig"][1]}
    assert not mismatches, f"Bronze lệch nguồn ([Bronze, nguồn]): {mismatches}"
    # Dải kỳ trong conf phải phủ hết dữ liệu nguồn, nếu không có dòng không bao giờ vào Bronze
    assert set(expected_perf) <= set(periods), f"Có tháng nguồn ngoài dải kỳ: {set(expected_perf) - set(periods)}"


def test_load_date_by_month(loaded, cfg):
    pairs = (bronze_table(cfg, "perf").to_pyarrow_table(columns=["reporting_period", "load_date"])
             .group_by(["reporting_period", "load_date"]).aggregate([]).to_pylist())
    by_month = defaultdict(set)
    for p in pairs:
        by_month[p["reporting_period"]].add(p["load_date"])
    wrong = {m: d for m, d in by_month.items() if d != {load_date_for(m, cfg.lag_months)}}
    assert not wrong, f"load_date sai quy tắc: {dict(list(wrong.items())[:5])}"


def test_rerun_period_idempotent(loaded, cfg):
    before_rows = (rows_per_period(bronze_table(cfg, "perf")), rows_per_period(bronze_table(cfg, "orig")))
    before_log = layer_runs(cfg)
    sh("make", "run", f"PERIOD={RERUN_PERIOD}", timeout=3600)
    after_rows = (rows_per_period(bronze_table(cfg, "perf")), rows_per_period(bronze_table(cfg, "orig")))
    new_runs = layer_runs(cfg)[len(before_log):]
    RESULT["rerun"] = {"period": RERUN_PERIOD, "new_layer_runs": [(r["layer"], r["status"]) for r in new_runs]}
    assert after_rows == before_rows, "Chạy lại kỳ làm đổi số dòng Bronze"
    # Mỗi tầng đúng một lần chạy mới, đều SUCCESS (lần FAILED rồi thử lại cũng được ghi, nên chỉ đếm SUCCESS)
    success = sorted(r["layer"] for r in new_runs if r["status"] == "SUCCESS" and r["period"] == RERUN_PERIOD)
    from ingestion.control import LAYERS
    assert success == sorted(LAYERS), new_runs


def test_rename_column_in_conf_only(loaded, cfg):
    """Đổi tên cột current_upb trong một bản sao conf/, nạp vào database riêng, Bronze phải có tên mới."""
    conf_copy = ROOT / "data/tmp/c1_conf_rename"
    shutil.rmtree(conf_copy, ignore_errors=True)
    shutil.copytree(ROOT / "conf", conf_copy)
    schema_file = conf_copy / "schema/perf.yml"
    schema = yaml.safe_load(schema_file.read_text())
    for col in schema["columns"]:
        if col["name"] == "current_upb":
            col["name"] = "current_actual_upb"
    schema_file.write_text(yaml.safe_dump(schema, allow_unicode=True))
    # Landing và Bronze của bản sao conf ghi vào database riêng, không đụng dữ liệu đang dùng
    pipeline_file = conf_copy / "pipeline.yml"
    pipeline = yaml.safe_load(pipeline_file.read_text())
    database = "bronze_c1_rename"
    pipeline["bronze"]["database"] = database
    pipeline["landing"]["database"] = "landing_c1_rename"
    pipeline_file.write_text(yaml.safe_dump(pipeline, allow_unicode=True))
    try:
        out = sh("docker", "compose", "exec", "-T", "airflow-scheduler", "python", "-m", "ingestion.bronze",
                 "--period", RENAME_PERIOD, "--conf-dir", f"/opt/project/{conf_copy.relative_to(ROOT)}",
                 timeout=1800).stdout
        counts = json.loads(out.strip().splitlines()[-1])
        columns = [f.name for f in bronze_table(cfg, "perf", database).schema().fields]
        assert "current_actual_upb" in columns and "current_upb" not in columns
        expected_perf, _ = loaded
        assert counts["bronze_perf_rows"] == expected_perf[RENAME_PERIOD]
    finally:
        sh("docker", "compose", "exec", "-T", "spark-thrift", "/opt/spark/bin/beeline", "-u",
           "jdbc:hive2://localhost:10000", "-n", "lakehouse", "-e",
           f"DROP DATABASE IF EXISTS {database} CASCADE; DROP DATABASE IF EXISTS landing_c1_rename CASCADE", check=False)
        shutil.rmtree(conf_copy, ignore_errors=True)


def test_landing_one_file_per_month(loaded, cfg):
    """Landing perf phải có đúng một file mỗi tháng; file vụn làm chậm mọi lần đọc sau (R-28)."""
    table = DeltaTable(str(ROOT / "data/lake/warehouse/landing.db" / f"{cfg.source}_perf"))
    files = Counter(pa.table(table.get_add_actions(flatten=True)).to_pydict()["partition.reporting_period"])
    RESULT["landing_files_per_month_max"] = max(files.values())
    assert set(files.values()) == {1}, {m: n for m, n in files.items() if n != 1}


def test_baseline_recorded(loaded, cfg):
    latest = {}
    # Baseline Bronze: thời gian tầng ingest (landing + Bronze) của mỗi kỳ, lần SUCCESS gần nhất
    for row in layer_runs(cfg):
        if row["status"] == "SUCCESS" and row["layer"] == "ingest":
            latest[row["period"]] = float(row["duration_s"])
    periods = periods_between(cfg.pipeline["periods"]["first"], cfg.pipeline["periods"]["last"])
    latest = {p: d for p, d in latest.items() if p in periods}  # bỏ đợt sửa dữ liệu (CORR*)
    RESULT["baseline_seconds"] = {"per_period": latest, "total": round(sum(latest.values()), 1),
                                  "max": max(latest.values(), default=None)}
    assert set(latest) == set(periods), f"Kỳ chưa có lần chạy SUCCESS: {set(periods) - set(latest)}"
