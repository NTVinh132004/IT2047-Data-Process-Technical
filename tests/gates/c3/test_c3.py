"""Cổng C3 (Kế hoạch mục 6): Business Vault, PIT và đợt sửa dữ liệu.

- FR-12: chỉ số Business Vault của 20 khoản vay khớp cách tính độc lập bằng Python thuần trên file TXT (oracle.py),
  ở mọi tháng. 20 khoản vay chọn theo seed, 4 khoản mỗi nhóm: vỡ nợ, từng 90+ nhưng chưa vỡ nợ, hoãn trả nợ COVID,
  trả trước hạn, luôn đúng hạn
- AC-04: với 100 khoản vay ngẫu nhiên (seed cố định), trạng thái qua PIT tại tháng m khớp dòng perf tháng m ở Bronze
- AC-09: sau đợt sửa CORR1, Satellite khởi tạo có phiên bản mới cho đúng các khoản vay bị sửa, phiên bản cũ còn
  nguyên; PIT trước và sau load_date của đợt sửa trả về giá trị cũ và mới; bảng đối chứng ghi đè chỉ còn giá trị mới
- dbt test Business Vault đạt 100%; chạy lại kỳ cũ và đợt sửa sinh 0 dòng mới ở PIT và Business Vault

Lần đầu chạy lại mọi kỳ qua DAG có tầng Business Vault (khoảng 1,5 giờ trên bộ mẫu).
"""
import hashlib

import pytest

from ingestion.config import Config
from tests.gates.c2.test_c2 import spark_sql
from tests.gates.c3 import oracle
from tests.gates.conftest import save_gate_result, sh

CORRECTION = "CORR1"
RERUN_PERIOD = "2020Q1"
RESULT: dict = {}


def pick(loans, n: int, salt: str) -> list[str]:
    return sorted(loans, key=lambda loan: hashlib.sha256(f"{loan}{salt}".encode()).hexdigest())[:n]


def counts(tables: list[str]) -> dict[str, int]:
    union = " UNION ALL ".join(f"SELECT '{t}' AS t, COUNT(*) AS n FROM {t}" for t in tables)
    return {r["t"]: int(r["n"]) for r in spark_sql(union)}


BV_TABLES = ["business_vault.as_of_dates", "business_vault.pit_loan_monthly", "business_vault.bsat_loan_risk",
             "business_vault.bsat_loan_lifecycle", "raw_vault.sat_loan_origination", "raw_vault.xts_loan",
             "baseline.baseline_dim_loan_overwrite"]


@pytest.fixture(scope="module")
def cfg() -> Config:
    return Config()


@pytest.fixture(scope="module")
def loaded(cfg):
    sh("make", "up", timeout=1800)
    sh("make", "run-all", timeout=6 * 3600)


@pytest.fixture(scope="module", autouse=True)
def record_results():
    yield
    save_gate_result("C3", RESULT)


@pytest.fixture(scope="module")
def corrected(loaded, cfg):
    sh("make", "correction", timeout=3600)
    return [r["loan_id"] for r in spark_sql(f"SELECT loan_id FROM bronze.orig WHERE period = '{CORRECTION}'")]


def test_fr12_business_vault_matches_oracle(loaded, cfg):
    every = oracle.compute(cfg)
    groups = {
        "vo_no": [l for l, s in every.items() if s[-1].default_reporting_period],
        "tung_90_chua_vo_no": [l for l, s in every.items() if s[-1].ever_d90 and not s[-1].default_reporting_period],
        "hoan_tra_covid": [l for l, s in every.items() if any(m.in_forbearance and "202003" <= m.reporting_period <= "202112" for m in s)],
        "tra_truoc_han": [l for l, s in every.items() if s[-1].lifecycle_status == "PREPAID"],
        "luon_dung_han": [l for l, s in every.items() if all(m.delinquency_bucket == "CURRENT" for m in s) and s[-1].lifecycle_status == "CURRENT"],
    }
    chosen: list[str] = []
    for name, loans in groups.items():
        chosen += pick([l for l in loans if l not in chosen], 4, f"c3-{name}")
    assert len(chosen) == 20, {k: len(v) for k, v in groups.items()}
    in_list = ", ".join(f"'{l}'" for l in chosen)
    vault = spark_sql(
        "SELECT h.loan_id, CAST(r.load_date AS STRING) AS load_date, r.delinquency_bucket, r.months_delinquent_consecutive,"
        " CAST(r.ever_d90 AS STRING) AS ever_d90, CAST(r.default_load_date AS STRING) AS default_load_date, l.lifecycle_status"
        " FROM business_vault.bsat_loan_risk r JOIN raw_vault.hub_loan h ON h.LOAN_HK = r.LOAN_HK"
        " JOIN business_vault.bsat_loan_lifecycle l ON l.LOAN_HK = r.LOAN_HK AND l.load_date = r.load_date"
        f" WHERE h.loan_id IN ({in_list})"
    )
    got = {(v["loan_id"], v["load_date"]): v for v in vault}
    mismatches, compared = [], 0
    for loan in chosen:
        for m in every[loan]:
            key = (loan, str(oracle.load_date_of(cfg, m.reporting_period)))
            want = {"delinquency_bucket": m.delinquency_bucket,
                    "months_delinquent_consecutive": str(m.months_delinquent_consecutive),
                    "ever_d90": str(m.ever_d90).lower(),
                    "default_load_date": str(oracle.load_date_of(cfg, m.default_reporting_period) or ""),
                    "lifecycle_status": m.lifecycle_status}
            row = got.get(key)
            compared += 1
            if row is None:
                mismatches.append({"key": key, "thiếu dòng": True})
                continue
            have = {k: (row[k] or "") for k in want}
            if have != want:
                mismatches.append({"key": key, "vault": have, "oracle": want})
    RESULT["fr12"] = {"loans": len(chosen), "months_compared": compared, "mismatches": len(mismatches),
                      "groups": {k: len(v) for k, v in groups.items()}}
    assert not mismatches, mismatches[:5]


def test_ac04_pit_matches_bronze(loaded):
    rows = spark_sql(
        "WITH loans AS (SELECT LOAN_HK, loan_id FROM raw_vault.hub_loan ORDER BY SHA2(CONCAT(loan_id, 'ac04'), 256) LIMIT 100),"
        " via_pit AS (SELECT l.loan_id, p.AS_OF_DATE, b.current_upb, b.loan_age, d.delinquency_status"
        "   FROM business_vault.pit_loan_monthly p JOIN loans l ON l.LOAN_HK = p.LOAN_HK"
        "   JOIN raw_vault.sat_loan_balance b ON b.LOAN_HK = p.LOAN_HK AND b.load_date = p.SAT_LOAN_BALANCE_LDTS"
        "   JOIN raw_vault.sat_loan_delinquency d ON d.LOAN_HK = p.LOAN_HK AND d.load_date = p.SAT_LOAN_DELINQUENCY_LDTS),"
        " bronze AS (SELECT o.loan_id, o.load_date, CAST(o.current_upb AS DECIMAL(20, 4)) AS current_upb,"
        "   CAST(o.loan_age AS INT) AS loan_age, NULLIF(o.delinquency_status, 'XX') AS delinquency_status"
        "   FROM bronze.perf o JOIN loans l ON l.loan_id = o.loan_id)"
        " SELECT COUNT(*) AS bronze_rows,"
        "   SUM(CASE WHEN v.loan_id IS NULL THEN 1 ELSE 0 END) AS missing_in_pit,"
        "   SUM(CASE WHEN v.loan_id IS NOT NULL AND (v.current_upb <> b.current_upb OR v.loan_age <> b.loan_age"
        "        OR NOT (v.delinquency_status <=> b.delinquency_status)) THEN 1 ELSE 0 END) AS mismatched"
        " FROM bronze b LEFT JOIN via_pit v ON v.loan_id = b.loan_id AND v.AS_OF_DATE = b.load_date"
    )[0]
    RESULT["ac04"] = rows
    assert int(rows["bronze_rows"]) > 0
    assert int(rows["missing_in_pit"]) == 0 and int(rows["mismatched"]) == 0, rows


def test_dbt_tests_business_vault_all_pass(loaded):
    out = sh("docker", "compose", "exec", "-T", "airflow-scheduler", "bash", "-c",
             "cd /opt/project/dbt && /opt/dbt-venv/bin/dbt test --select business_vault baseline", check=False)
    RESULT["dbt_test_business_vault"] = out.stdout.strip().splitlines()[-1] if out.stdout else ""
    assert out.returncode == 0, out.stdout[-3000:]


def test_rerun_older_period_adds_nothing(loaded):
    before = counts(BV_TABLES)
    sh("make", "run", f"PERIOD={RERUN_PERIOD}", timeout=3600)
    after = counts(BV_TABLES)
    RESULT["rerun"] = {"period": RERUN_PERIOD, "before": before, "after": after}
    assert after == before


def test_ac09_correction_keeps_history(corrected, cfg):
    spec = cfg.pipeline["corrections"][CORRECTION]
    assert len(corrected) == spec["loans"]
    in_list = ", ".join(f"'{l}'" for l in corrected)
    versions = spark_sql(
        "SELECT h.loan_id, COUNT(*) AS n FROM raw_vault.sat_loan_origination s JOIN raw_vault.hub_loan h ON h.LOAN_HK = s.LOAN_HK"
        " GROUP BY h.loan_id HAVING COUNT(*) > 1"
    )
    multi = {v["loan_id"]: int(v["n"]) for v in versions}
    # Đúng các khoản vay bị sửa có phiên bản mới, mỗi khoản đúng 2 phiên bản
    assert multi == {loan: 2 for loan in corrected}, multi

    check = spark_sql(
        f"WITH orig AS (SELECT loan_id, credit_score AS old_score FROM bronze.orig WHERE period <> '{CORRECTION}' AND loan_id IN ({in_list})),"
        f" corr AS (SELECT loan_id, credit_score AS new_score FROM bronze.orig WHERE period = '{CORRECTION}'),"
        " pit AS (SELECT h.loan_id, p.AS_OF_DATE, s.credit_score FROM business_vault.pit_loan_monthly p"
        "   JOIN raw_vault.hub_loan h ON h.LOAN_HK = p.LOAN_HK"
        "   JOIN raw_vault.sat_loan_origination s ON s.LOAN_HK = p.LOAN_HK AND s.load_date = p.SAT_LOAN_ORIGINATION_LDTS"
        f"   WHERE h.loan_id IN ({in_list})),"
        f" before AS (SELECT loan_id, credit_score FROM (SELECT pit.*, ROW_NUMBER() OVER (PARTITION BY loan_id ORDER BY AS_OF_DATE DESC) rn"
        f"   FROM pit WHERE AS_OF_DATE < DATE'{spec['load_date']}') q WHERE rn = 1),"
        f" after AS (SELECT loan_id, credit_score FROM pit WHERE AS_OF_DATE = DATE'{spec['load_date']}')"
        " SELECT o.loan_id, o.old_score, c.new_score, CAST(b.credit_score AS STRING) AS pit_before,"
        "   CAST(a.credit_score AS STRING) AS pit_after, CAST(d.credit_score AS STRING) AS overwrite_table,"
        "   (SELECT COUNT(*) FROM baseline.baseline_dim_loan_overwrite x WHERE x.loan_id = o.loan_id) AS overwrite_rows"
        " FROM orig o JOIN corr c ON c.loan_id = o.loan_id LEFT JOIN before b ON b.loan_id = o.loan_id"
        " LEFT JOIN after a ON a.loan_id = o.loan_id LEFT JOIN baseline.baseline_dim_loan_overwrite d ON d.loan_id = o.loan_id"
    )
    wrong = [r for r in check if not (r["pit_before"] == r["old_score"] and r["pit_after"] == r["new_score"]
                                      and r["overwrite_table"] == r["new_score"] and r["overwrite_rows"] == "1"
                                      and r["old_score"] != r["new_score"])]
    RESULT["ac09"] = {"corrected": len(corrected), "checked": len(check), "wrong": wrong[:5], "sample": check[:3]}
    assert len(check) == len(corrected) and not wrong, wrong[:5]


def test_ac09_rerun_correction_adds_nothing(corrected):
    before = counts(BV_TABLES)
    sh("make", "correction", timeout=3600)
    after = counts(BV_TABLES)
    RESULT["correction_rerun"] = {"before": before, "after": after}
    assert after == before
