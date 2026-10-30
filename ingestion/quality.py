"""Cổng chất lượng cho một kỳ (FR-07), chạy sau Bronze và trước dbt.

Tách luật theo chuẩn Data Vault 2.0 (review R-33, docs/tu-dien-du-lieu.md mục 5): trước Raw Vault chỉ áp hard rule,
soft rule không được chặn dữ liệu.

- Hard rule (sai_so_truong, sai_khoa, sai_kieu): dòng vào error mart <x>_quarantine kèm _reject_reason, _reject_column.
  Mỗi dòng mang một lý do chính theo thứ tự đó.
- Trùng khóa (khoản vay ở orig; khoản vay × tháng ở perf) giữa các dòng đã qua hard rule: các bản giống hệt được khử
  trùng lặp (giữ một, các bản còn lại vào <x>_dedup); các bản khác giá trị không nạp được vì trùng khóa Satellite nên
  mọi bản vào error mart với lý do trung_khoa.
- Soft rule (ngoài miền, perf không có orig) không xử lý ở đây: chúng là luật nghiệp vụ, tính ở Business Vault trên
  dữ liệu Raw Vault (business_vault.quality_violation, DV-02, R-35).

Lát của kỳ được ghi đè bằng replaceWhere ở mọi bảng, nên chạy lại kỳ không đổi số dòng (R-09). Với mỗi kỳ:
clean + quarantine + dedup = Bronze (AC-06). Mã thiếu (missing) không phải lỗi.

Chạy: python -m ingestion.quality --period 2020Q1 [--conf-dir DIR]
"""
import argparse
import json
from functools import reduce

from pyspark.sql import Column as SparkColumn
from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F

from ingestion.config import Config, SourceSchema
from ingestion.spark import get_spark

TYPE_PATTERNS = {
    "int": r"^-?\d+$",
    "decimal": r"^-?\d+(\.\d+)?$",
    "yyyymm": r"^\d{4}(0[1-9]|1[0-2])$",
}


def _present(value: SparkColumn, missing: list) -> SparkColumn:
    """Có giá trị thật: không null, không rỗng, không phải mã thiếu."""
    cond = value.isNotNull() & (value != "")
    return cond & ~value.isin([str(m) for m in missing]) if missing else cond


def hard_checks(schema: SourceSchema) -> list[tuple[str, str, SparkColumn]]:
    """Hard rule trên từng dòng, xếp theo ưu tiên: (lý do, cột, điều kiện vi phạm)."""
    checks = [("sai_so_truong", "_field_count", F.col("_field_count") != schema.field_count)]
    key = next(c for c in schema.columns if c.role == "loan_key")
    checks.append(("sai_khoa", key.name, F.col(key.name).isNull() | ~F.col(key.name).rlike(key.spec["pattern"])))
    for c in schema.columns:
        if c.type in TYPE_PATTERNS:
            value = F.col(c.name)
            checks.append(("sai_kieu", c.name, _present(value, c.spec.get("missing", [])) & ~value.rlike(TYPE_PATTERNS[c.type])))
    return checks


def _first_failure(checks: list[tuple[str, str, SparkColumn]]) -> tuple[SparkColumn, SparkColumn]:
    reason = reduce(lambda acc, c: acc.when(c[2], F.lit(c[0])), checks[1:], F.when(checks[0][2], F.lit(checks[0][0])))
    column = reduce(lambda acc, c: acc.when(c[2], F.lit(c[1])), checks[1:], F.when(checks[0][2], F.lit(checks[0][1])))
    return reason, column


def classify(df: DataFrame, schema: SourceSchema, key_columns: list[str]) -> DataFrame:
    """Thêm _reject_reason (hard rule, trung_khoa), _reject_column và _is_duplicate_copy (bản sao bị khử trùng lặp)."""
    reason, column = _first_failure(hard_checks(schema))
    df = df.withColumn("_reject_reason", reason).withColumn("_reject_column", column)

    # Trùng khóa chỉ xét giữa các dòng đã qua hard rule; so nội dung toàn bộ cột nguồn để tách bản sao giống hệt
    passed = F.col("_reject_reason").isNull()
    payload = F.sha2(F.concat_ws("\u0001", *[F.coalesce(F.col(c.name), F.lit("\u0000")) for c in schema.columns]), 256)
    by_key = Window.partitionBy(*key_columns)
    df = (df.withColumn("_payload", F.when(passed, payload))
            .withColumn("_copies", F.count(F.col("_payload")).over(by_key))
            .withColumn("_variants", F.size(F.collect_set(F.col("_payload")).over(by_key))))
    conflicting = passed & (F.col("_variants") > 1)
    df = (df.withColumn("_reject_column", F.when(conflicting, F.lit(",".join(key_columns))).otherwise(F.col("_reject_column")))
            .withColumn("_reject_reason", F.when(conflicting, F.lit("trung_khoa")).otherwise(F.col("_reject_reason"))))
    copy_rank = F.row_number().over(by_key.orderBy(F.col("_payload"), F.col("source_file")))
    df = df.withColumn("_is_duplicate_copy",
                       F.col("_reject_reason").isNull() & (F.col("_copies") > 1) & (F.col("_variants") == 1) & (copy_rank > 1))
    return df.drop("_payload", "_copies", "_variants")


def write_slice(df: DataFrame, table: str, period: str) -> None:
    (df.write.format("delta").mode("overwrite").option("replaceWhere", f"period = '{period}'")
     .partitionBy("period").saveAsTable(table))


def run(period: str, conf_dir: str | None = None, spark: SparkSession | None = None) -> dict:
    cfg = Config(conf_dir)
    spark = spark or get_spark(f"quality-{period}")
    bronze, database = cfg.bronze, cfg.pipeline["quality"]["database"]
    spark.sql(f"CREATE DATABASE IF NOT EXISTS {database}")
    orig_table = f"{bronze['database']}.{bronze['orig_table']}"
    perf_table = f"{bronze['database']}.{bronze['perf_table']}"
    orig_key = [cfg.orig.column_with_role("loan_key")]
    perf_key = [cfg.perf.column_with_role("loan_key"), cfg.perf.column_with_role("reporting_period")]

    counts = {}
    for kind, table, schema, key in (("orig", orig_table, cfg.orig, orig_key), ("perf", perf_table, cfg.perf, perf_key)):
        classified = classify(spark.table(table).where(F.col("period") == period), schema, key).cache()
        base = f"{database}.{kind}"
        clean = classified.where(F.col("_reject_reason").isNull() & ~F.col("_is_duplicate_copy"))
        write_slice(clean.drop("_reject_reason", "_reject_column", "_is_duplicate_copy"), f"{base}_clean", period)
        write_slice(classified.where(F.col("_reject_reason").isNotNull()).drop("_is_duplicate_copy"), f"{base}_quarantine", period)
        write_slice(classified.where(F.col("_is_duplicate_copy")).drop("_reject_reason", "_reject_column", "_is_duplicate_copy"),
                    f"{base}_dedup", period)
        classified.unpersist()
        for suffix in ("clean", "quarantine", "dedup"):
            counts[f"{kind}_{suffix}"] = spark.table(f"{base}_{suffix}").where(F.col("period") == period).count()
    counts["rows_clean"] = counts["orig_clean"] + counts["perf_clean"]
    counts["rows_rejected"] = counts["orig_quarantine"] + counts["perf_quarantine"]
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--period", required=True, help="Kỳ nạp, ví dụ 2020Q1")
    parser.add_argument("--conf-dir", help="Thư mục cấu hình, mặc định conf/")
    args = parser.parse_args()
    print(json.dumps(run(args.period, args.conf_dir)))


if __name__ == "__main__":
    main()
