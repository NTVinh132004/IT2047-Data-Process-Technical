"""Cổng C2 (Kế hoạch mục 6): cổng chất lượng và Raw Vault.

- Unit test hash (FR-06), chạy trên SQL thật do automate_dv sinh ra
- Cổng chất lượng chặn đúng từng dòng lỗi của bộ fixture giả lập (make smoke)
- AC-06 ở mọi kỳ: dòng sạch + quarantine (hard rule) + bản sao khử trùng lặp = dòng Bronze; không dòng quarantine nào
  vào Raw Vault; dòng vi phạm soft rule vẫn vào Raw Vault (FR-07, R-33)
- AC-03: số khoản vay trong hub_loan
- AC-02: chạy lại kỳ gần nhất và một kỳ cũ sinh 0 dòng mới ở Hub, Link, Satellite
- 100% dòng Raw Vault có load_date, record_source
- dbt test Raw Vault đạt 100%; một test cố ý sai làm DAG dừng (FR-22)

Lần đầu chạy lại mọi kỳ qua DAG mới (khoảng 45 phút trên bộ mẫu); các lần sau chỉ chạy kỳ chưa xong.
"""
import csv
import io
import json
import re
from collections import Counter

import pyarrow as pa
import pytest
from deltalake import DeltaTable

from ingestion.config import Config
from ingestion.periods import periods_between
from tests.gates.conftest import ROOT, dotenv, save_gate_result, sh

LATEST, OLDER = "2026Q1", "2020Q1"
INJECT_PERIOD = "2019Q3"
HUBS = ["hub_loan", "hub_seller", "hub_servicer"]
LINKS = ["link_loan_seller", "link_loan_servicer"]
SATS = ["sat_loan_origination", "sat_loan_property", "sat_loan_balance", "sat_loan_delinquency", "sat_loan_termination"]
XTS = ["xts_loan", "xts_loan_servicer"]
RAW_VAULT = HUBS + LINKS + SATS + XTS
RESULT: dict = {}


def spark_sql(query: str) -> list[dict]:
    """Chạy SQL qua Spark Thrift Server (beeline), trả về danh sách dòng."""
    out = sh("docker", "compose", "exec", "-T", "spark-thrift", "/opt/spark/bin/beeline", "-u",
             "jdbc:hive2://localhost:10000", "-n", "lakehouse", "--silent=true", "--outputformat=csv2",
             "-e", query).stdout
    # Dòng tiêu đề cột dính liền dấu nhắc của beeline ("0: jdbc:hive2://...> t,n"): bóc dấu nhắc, giữ nội dung
    lines = [re.sub(r"^\d+: jdbc:hive2://\S+> ?", "", line) for line in out.splitlines()]
    rows = csv.DictReader(io.StringIO("\n".join(line for line in lines if line)))
    # beeline in null thành chuỗi NULL
    return [{k: (None if v == "NULL" else v) for k, v in row.items()} for row in rows]


def delta_rows_per_period(database: str, table: str) -> Counter:
    dt = DeltaTable(str(ROOT / "data/lake/warehouse" / f"{database}.db" / table))
    actions = pa.table(dt.get_add_actions(flatten=True)).to_pydict()
    counts: Counter = Counter()
    for period, n in zip(actions["partition.period"], actions["num_records"]):
        counts[period] += n
    return counts


def raw_vault_counts() -> dict[str, int]:
    union = " UNION ALL ".join(f"SELECT '{t}' AS t, COUNT(*) AS n FROM raw_vault.{t}" for t in RAW_VAULT)
    return {r["t"]: int(r["n"]) for r in spark_sql(union)}


def layer_runs_since(cfg: Config, run_id: int) -> list[dict]:
    import psycopg

    env = dotenv()
    with psycopg.connect(host="127.0.0.1", dbname="analytics", user=env["POSTGRES_USER"],
                         password=env["POSTGRES_PASSWORD"]) as conn, conn.cursor() as cur:
        cur.execute("SELECT run_id, period, layer, status FROM control.layer_run WHERE dataset = %s AND run_id > %s"
                    " ORDER BY run_id", (cfg.source, run_id))
        return [dict(zip(("run_id", "period", "layer", "status"), row)) for row in cur.fetchall()]


@pytest.fixture(scope="module")
def cfg() -> Config:
    return Config()


@pytest.fixture(scope="module")
def loaded(cfg):
    sh("make", "up", timeout=1800)
    sh("make", "run-all", timeout=4 * 3600)


@pytest.fixture(scope="module", autouse=True)
def record_results():
    yield
    save_gate_result("C2", RESULT)


def test_hash_rules_fr06(loaded):
    out = sh("docker", "compose", "exec", "-T", "airflow-scheduler", "bash", "-c",
             "cd /opt/project/dbt && /opt/dbt-venv/bin/dbt build --select +tag:hash_test", check=False)
    RESULT["hash_rules"] = out.returncode == 0
    assert out.returncode == 0, out.stdout[-3000:]


def test_quality_gate_on_fixture(loaded):
    out = sh("make", "smoke", check=False, timeout=1800)
    json_lines = [line for line in out.stdout.splitlines() if line.startswith("{")]
    assert json_lines, f"make smoke không in kết quả JSON:\n{out.stdout[-2000:]}\n{out.stderr[-2000:]}"
    report = json.loads(json_lines[-1])
    RESULT["smoke"] = report
    assert out.returncode == 0 and not report["problems"], report


def test_ac06_every_period(loaded, cfg):
    periods = periods_between(cfg.pipeline["periods"]["first"], cfg.pipeline["periods"]["last"])
    bronze, quality = cfg.bronze["database"], cfg.pipeline["quality"]["database"]
    mismatches, totals = {}, Counter()
    for kind in ("orig", "perf"):
        b = delta_rows_per_period(bronze, cfg.bronze[f"{kind}_table"])
        c = delta_rows_per_period(quality, f"{kind}_clean")
        q = delta_rows_per_period(quality, f"{kind}_quarantine")
        d = delta_rows_per_period(quality, f"{kind}_dedup")
        v = delta_rows_per_period(quality, f"{kind}_soft_violation")
        for p in periods:
            totals[f"{kind}_bronze"] += b[p]
            totals[f"{kind}_clean"] += c[p]
            totals[f"{kind}_quarantine"] += q[p]
            totals[f"{kind}_dedup"] += d[p]
            totals[f"{kind}_soft_violation"] += v[p]
            if b[p] != c[p] + q[p] + d[p]:
                mismatches[f"{kind} {p}"] = {"bronze": b[p], "clean": c[p], "quarantine": q[p], "dedup": d[p]}
    RESULT["ac06_totals"] = dict(totals)
    assert not mismatches, mismatches


def test_no_quarantined_row_in_raw_vault(loaded):
    """Dòng perf bị chặn không được có phiên bản Satellite ở đúng (khoản vay, load_date) của nó."""
    rows = spark_sql(
        "SELECT COUNT(*) AS n FROM quality.perf_quarantine q JOIN raw_vault.sat_loan_balance s"
        " ON s.LOAN_HK = UPPER(SHA2(UPPER(TRIM(q.loan_id)), 256)) AND s.load_date = q.load_date"
    )
    RESULT["quarantine_in_raw_vault"] = int(rows[0]["n"])
    assert RESULT["quarantine_in_raw_vault"] == 0


def test_ac03_hub_loan(loaded):
    """hub_loan = số khoản vay orig có ít nhất một dòng perf, trừ khoản vay bị chặn hết mọi dòng."""
    row = spark_sql(
        "SELECT (SELECT COUNT(*) FROM raw_vault.hub_loan) AS hub,"
        " (SELECT COUNT(DISTINCT loan_id) FROM bronze.orig) AS orig_with_perf,"
        " (SELECT COUNT(DISTINCT loan_id) FROM (SELECT loan_id FROM quality.orig_clean UNION SELECT loan_id FROM quality.perf_clean)) AS loans_with_clean_rows"
    )[0]
    RESULT["ac03"] = row
    # bronze.orig chỉ chứa khoản vay có perf (lát orig cắt theo tháng perf đầu tiên, R-10)
    assert int(row["hub"]) == int(row["loans_with_clean_rows"])
    assert int(row["hub"]) <= int(row["orig_with_perf"])


def test_audit_columns_not_null(loaded):
    union = " UNION ALL ".join(
        f"SELECT '{t}' AS t, COUNT(*) AS n FROM raw_vault.{t} WHERE load_date IS NULL OR record_source IS NULL"
        for t in RAW_VAULT
    )
    missing = {r["t"]: int(r["n"]) for r in spark_sql(union) if int(r["n"])}
    assert not missing, missing


def test_dbt_tests_raw_vault_all_pass(loaded):
    out = sh("docker", "compose", "exec", "-T", "airflow-scheduler", "bash", "-c",
             "cd /opt/project/dbt && /opt/dbt-venv/bin/dbt test --select raw_vault", check=False)
    RESULT["dbt_test_raw_vault"] = out.stdout.strip().splitlines()[-1] if out.stdout else ""
    assert out.returncode == 0, out.stdout[-3000:]


def test_ac02_rerun_latest_and_older_period(loaded):
    before = raw_vault_counts()
    for period in (LATEST, OLDER):
        sh("make", "run", f"PERIOD={period}", timeout=3600)
    after = raw_vault_counts()
    RESULT["ac02"] = {"before": before, "after": after}
    assert after == before, {t: (before[t], after[t]) for t in RAW_VAULT if before[t] != after[t]}


def test_failing_dbt_test_stops_dag(loaded, cfg):
    """FR-22: bật một dbt test cố ý sai, tầng Raw Vault phải thất bại và tầng Business Vault không được chạy."""
    before = raw_vault_counts()
    last = max((r["run_id"] for r in layer_runs_since(cfg, 0)), default=0)
    out = sh("scripts/run_period.sh", INJECT_PERIOD, '{"inject_test_failure": true, "max_attempts": 1}',
             check=False, timeout=3600)
    runs = layer_runs_since(cfg, last)
    RESULT["fr22"] = {"exit_code": out.returncode, "runs": runs}
    assert out.returncode != 0
    assert [(r["layer"], r["status"]) for r in runs if r["layer"] == "raw_vault"] == [("raw_vault", "FAILED")]
    assert not any(r["layer"] == "business_vault" for r in runs)
    assert raw_vault_counts() == before
    # Chạy lại bình thường để kỳ không bị coi là chưa xong
    sh("make", "run", f"PERIOD={INJECT_PERIOD}", timeout=3600)
