"""Kiểm nhanh luồng landing → Bronze → cổng chất lượng trên bộ fixture giả lập (make smoke).

Dùng bản sao conf/ trỏ tới tests/fixtures/quality và các database *_smoke, nên không đụng dữ liệu thật.
So từng dòng bị chặn (khoản vay, tháng, lý do) và số dòng sạch với tests/fixtures/quality/expected.yml.
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

    def rejected(kind: str) -> Counter:
        rows = spark.table(f"quality_smoke.{kind}_quarantine").where(F.col("period") == period).collect()
        return Counter((r["loan_id"], r["reporting_period"] if kind == "perf" else None, r["_reject_reason"]) for r in rows)

    problems = []
    for kind in ("orig", "perf"):
        want = Counter((r["loan_id"], r.get("reporting_period"), r["reason"]) for r in expected["rejected"] if r["table"] == kind)
        got = rejected(kind)
        if got != want:
            problems.append({kind: {"thiếu": list((want - got).elements()), "thừa": list((got - want).elements())}})
        if counts[f"{kind}_clean"] != expected["summary"][kind]["clean_rows"]:
            problems.append({kind: f"dòng sạch {counts[f'{kind}_clean']}, mong đợi {expected['summary'][kind]['clean_rows']}"})
    print(json.dumps({"counts": counts, "problems": problems}, ensure_ascii=False, default=str))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
