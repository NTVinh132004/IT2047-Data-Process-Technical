"""Kiểm nhanh luồng landing → Bronze → cổng chất lượng trên bộ fixture giả lập (make smoke).

Dùng bản sao conf/ trỏ tới tests/fixtures/quality và các database *_smoke, nên không đụng dữ liệu thật.
So error mart (khoản vay, tháng, lý do), bản sao bị khử trùng lặp và số dòng sạch với tests/fixtures/quality/expected.yml.
Dòng chỉ vi phạm soft rule phải vào bảng sạch; soft rule được kiểm ở Business Vault (dbt unit test, R-35).
Thoát mã 1 nếu lệch. Chạy trong container airflow-scheduler: python -m ingestion.smoke
"""
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

import yaml
from pyspark.sql import functions as F

from ingestion import bronze, landing, quality
from ingestion.config import Config
from ingestion.spark import get_spark

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests/fixtures/quality"


def smoke_conf() -> Path:
    conf = ROOT / "data/tmp/smoke_conf"
    shutil.rmtree(conf, ignore_errors=True)
    shutil.copytree(ROOT / "conf", conf)
    pipeline = yaml.safe_load((conf / "pipeline.yml").read_text())
    pipeline["dataset"]["source"] = "sample"
    pipeline["paths"]["raw"]["sample"] = str(FIXTURE)
    for layer in ("landing", "bronze", "quality"):
        pipeline[layer]["database"] = f"{layer}_smoke"
    (conf / "pipeline.yml").write_text(yaml.safe_dump(pipeline, allow_unicode=True))
    return conf


def main() -> int:
    expected = yaml.safe_load((FIXTURE / "expected.yml").read_text())
    period = expected["period"]
    conf = smoke_conf()
    cfg = Config(conf)
    spark = get_spark("smoke")
    landing.ensure(cfg, force=True, spark=spark)
    bronze.run(period, conf, spark=spark)
    counts = quality.run(period, conf, spark=spark)

    def table_rows(kind: str, suffix: str) -> list:
        return spark.table(f"quality_smoke.{kind}_{suffix}").where(F.col("period") == period).collect()

    def key(r, kind: str) -> tuple:
        return (r["loan_id"], r["reporting_period"] if kind == "perf" else None)

    problems = []
    for kind in ("orig", "perf"):
        def want(section: str, fields: tuple) -> Counter:
            return Counter((x["loan_id"], x.get("reporting_period"), *(x[f] for f in fields))
                           for x in expected[section] if x["table"] == kind)

        got = {
            "quarantine": Counter((*key(r, kind), r["_reject_reason"]) for r in table_rows(kind, "quarantine")),
            "dedup": Counter(key(r, kind) for r in table_rows(kind, "dedup")),
        }
        wanted = {"quarantine": want("quarantine", ("reason",)), "dedup": want("dedup", ())}
        for section in wanted:
            if got[section] != wanted[section]:
                problems.append({f"{kind}_{section}": {"thiếu": list((wanted[section] - got[section]).elements()),
                                                       "thừa": list((got[section] - wanted[section]).elements())}})
        if counts[f"{kind}_clean"] != expected["summary"][kind]["clean_rows"]:
            problems.append({kind: f"dòng sạch {counts[f'{kind}_clean']}, mong đợi {expected['summary'][kind]['clean_rows']}"})
    print(json.dumps({"counts": counts, "problems": problems}, ensure_ascii=False, default=str))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
