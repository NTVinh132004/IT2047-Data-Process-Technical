"""Cổng chất lượng cho một kỳ (FR-07), chạy sau Bronze và trước dbt.

Tách luật theo chuẩn Data Vault 2.0 (review R-33, docs/tu-dien-du-lieu.md mục 5): trước Raw Vault chỉ áp hard rule,
soft rule không được chặn dữ liệu.

- Hard rule (sai_so_truong, sai_khoa, sai_kieu): dòng vào error mart <x>_quarantine kèm _reject_reason, _reject_column.
  Mỗi dòng mang một lý do chính theo thứ tự đó.
- Trùng khóa (khoản vay ở orig; khoản vay × tháng ở perf) giữa các dòng đã qua hard rule: các bản giống hệt được khử
  trùng lặp (giữ một, các bản còn lại vào <x>_dedup); các bản khác giá trị không nạp được vì trùng khóa Satellite nên
  mọi bản vào error mart với lý do trung_khoa.
- Soft rule (ngoai_mien theo domain/values/pattern/nullable của conf/schema; mo_coi: perf không có orig ở Bronze):
  dòng vẫn vào <x>_clean; mỗi vi phạm thành một dòng ở báo cáo <x>_soft_violation.

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


def soft_checks(schema: SourceSchema) -> list[tuple[str, str, SparkColumn]]:
    """Soft rule trên từng dòng (chỉ báo cáo, không chặn): (luật, cột, điều kiện vi phạm)."""
    checks = []
    for c in schema.columns:
        if c.role == "loan_key":
            continue
        value = F.col(c.name)
        present = _present(value, c.spec.get("missing", []))
        if not c.spec.get("nullable"):
            checks.append(("ngoai_mien", c.name, value.isNull() | (value == "")))
        if "domain" in c.spec:
            lo, hi = c.spec["domain"]
            number = value.cast("double")
            out = (number < lo if lo is not None else F.lit(False)) | (number > hi if hi is not None else F.lit(False))
            checks.append(("ngoai_mien", c.name, present & value.rlike(TYPE_PATTERNS.get(c.type, ".*")) & out))
        if "values" in c.spec:
            checks.append(("ngoai_mien", c.name, present & ~value.isin([str(v) for v in c.spec["values"]])))
        if "pattern" in c.spec:
            checks.append(("ngoai_mien", c.name, present & ~value.rlike(c.spec["pattern"])))
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


def soft_violations(clean: DataFrame, schema: SourceSchema, key_columns: list[str],
                    orig_loans: DataFrame | None) -> DataFrame:
    """Mỗi vi phạm soft rule của một dòng sạch thành một dòng báo cáo."""
    entries = [F.when(cond, F.struct(F.lit(rule).alias("rule"), F.lit(col).alias("column"),
                                     F.col(col).cast("string").alias("value")))
               for rule, col, cond in soft_checks(schema)]
    df = clean
    if orig_loans is not None:
        loan = key_columns[0]
        df = df.join(orig_loans.select(F.col(loan).alias("_orig_loan")).distinct(), F.col(loan) == F.col("_orig_loan"), "left")
        entries.append(F.when(F.col("_orig_loan").isNull(),
                              F.struct(F.lit("mo_coi").alias("rule"), F.lit(loan).alias("column"),
                                       F.col(loan).alias("value"))))
    violations = F.filter(F.array(*entries), lambda x: x.isNotNull())
    return (df.select(*key_columns, "period", F.explode(violations).alias("v"))
              .select(*key_columns, "v.rule", "v.column", "v.value", "period"))


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
    # Mồ côi chỉ còn là báo cáo (soft rule) nên so với orig ở Bronze của mọi kỳ, không phụ thuộc thứ tự nạp
    all_orig = spark.table(orig_table).withColumnRenamed(orig_key[0], perf_key[0])

    counts = {}
    for kind, table, schema, key, orig_loans in (
        ("orig", orig_table, cfg.orig, orig_key, None),
        ("perf", perf_table, cfg.perf, perf_key, all_orig),
    ):
        classified = classify(spark.table(table).where(F.col("period") == period), schema, key).cache()
        base = f"{database}.{kind}"
        clean = classified.where(F.col("_reject_reason").isNull() & ~F.col("_is_duplicate_copy"))
        write_slice(clean.drop("_reject_reason", "_reject_column", "_is_duplicate_copy"), f"{base}_clean", period)
        write_slice(classified.where(F.col("_reject_reason").isNotNull()).drop("_is_duplicate_copy"), f"{base}_quarantine", period)
        write_slice(classified.where(F.col("_is_duplicate_copy")).drop("_reject_reason", "_reject_column", "_is_duplicate_copy"),
                    f"{base}_dedup", period)
        write_slice(soft_violations(spark.table(f"{base}_clean").where(F.col("period") == period), schema, key, orig_loans),
                    f"{base}_soft_violation", period)
        classified.unpersist()
        for suffix in ("clean", "quarantine", "dedup", "soft_violation"):
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
