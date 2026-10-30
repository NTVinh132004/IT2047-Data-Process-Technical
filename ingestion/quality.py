"""Cổng chất lượng cho một kỳ (FR-07), chạy sau Bronze và trước dbt.

Đọc lát Bronze của kỳ, áp các luật ở docs/tu-dien-du-lieu.md mục 5 và ghi hai bảng cho mỗi loại file:
<x>_clean (dòng hợp lệ, cùng cột với Bronze) và <x>_quarantine (dòng bị chặn, thêm _reject_reason và _reject_column).
Lát của kỳ được ghi đè bằng replaceWhere, nên chạy lại kỳ không đổi số dòng (R-09). Số dòng sạch cộng số dòng
quarantine luôn bằng số dòng Bronze của kỳ (AC-06).

Luật đọc từ conf/schema (type, domain, values, missing, pattern, nullable). Mỗi dòng lỗi mang một lý do chính theo
thứ tự ưu tiên: sai_so_truong, sai_khoa, sai_kieu, ngoai_mien, trung_khoa, mo_coi. Mã thiếu (missing) không phải lỗi.

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


def _first_failure(checks: list[tuple[str, str, SparkColumn]]) -> tuple[SparkColumn, SparkColumn]:
    """(lý do, cột) của luật đầu tiên bị vi phạm trong danh sách đã xếp theo ưu tiên; null nếu không vi phạm."""
    reason = reduce(lambda acc, c: acc.when(c[2], F.lit(c[0])), checks[1:], F.when(checks[0][2], F.lit(checks[0][0])))
    column = reduce(lambda acc, c: acc.when(c[2], F.lit(c[1])), checks[1:], F.when(checks[0][2], F.lit(checks[0][1])))
    return reason, column


def row_checks(schema: SourceSchema) -> list[tuple[str, str, SparkColumn]]:
    """Luật trên từng dòng, xếp theo ưu tiên: (lý do, cột, điều kiện vi phạm)."""
    checks = [("sai_so_truong", "_field_count", F.col("_field_count") != schema.field_count)]
    key = next(c for c in schema.columns if c.role == "loan_key")
    checks.append(("sai_khoa", key.name, F.col(key.name).isNull() | ~F.col(key.name).rlike(key.spec["pattern"])))

    typed, domain = [], []
    for c in schema.columns:
        value = F.col(c.name)
        missing = c.spec.get("missing", [])
        present = value.isNotNull() & (value != "") & ~value.isin(missing) if missing else value.isNotNull() & (value != "")
        if c.type in TYPE_PATTERNS:
            typed.append(("sai_kieu", c.name, present & ~value.rlike(TYPE_PATTERNS[c.type])))
        if not c.spec.get("nullable") and c.role != "loan_key":
            domain.append(("ngoai_mien", c.name, value.isNull() | (value == "")))
        if "domain" in c.spec:
            lo, hi = c.spec["domain"]
            number = value.cast("double")
            out = (number < lo if lo is not None else F.lit(False)) | (number > hi if hi is not None else F.lit(False))
            domain.append(("ngoai_mien", c.name, present & value.rlike(TYPE_PATTERNS.get(c.type, ".*")) & out))
        if "values" in c.spec:
            domain.append(("ngoai_mien", c.name, present & ~value.isin([str(v) for v in c.spec["values"]])))
        if "pattern" in c.spec and c.role != "loan_key":
            domain.append(("ngoai_mien", c.name, present & ~value.rlike(c.spec["pattern"])))
    return checks + typed + domain


def evaluate(df: DataFrame, schema: SourceSchema, key_columns: list[str], orig_loans: DataFrame | None) -> DataFrame:
    """Thêm _reject_reason và _reject_column (null nếu dòng hợp lệ)."""
    reason, column = _first_failure(row_checks(schema))
    df = df.withColumn("_reject_reason", reason).withColumn("_reject_column", column)

    # Trùng khóa: mọi bản sao bị chặn (không biết bản nào đúng), chỉ đếm giữa các dòng đã qua luật trên từng dòng
    passed = F.col("_reject_reason").isNull()
    dup_count = F.sum(passed.cast("int")).over(Window.partitionBy(*key_columns))
    df = df.withColumn("_reject_column", F.when(passed & (dup_count > 1), F.lit(",".join(key_columns))).otherwise(F.col("_reject_column")))
    df = df.withColumn("_reject_reason", F.when(passed & (dup_count > 1), F.lit("trung_khoa")).otherwise(F.col("_reject_reason")))

    if orig_loans is not None:
        loan = key_columns[0]
        df = (
            df.join(orig_loans.select(F.col(loan).alias("_orig_loan")).distinct(), F.col(loan) == F.col("_orig_loan"), "left")
            .withColumn("_reject_column", F.when(F.col("_reject_reason").isNull() & F.col("_orig_loan").isNull(), F.lit(loan)).otherwise(F.col("_reject_column")))
            .withColumn("_reject_reason", F.when(F.col("_reject_reason").isNull() & F.col("_orig_loan").isNull(), F.lit("mo_coi")).otherwise(F.col("_reject_reason")))
            .drop("_orig_loan")
        )
    return df


def write_slice(df: DataFrame, table: str, period: str) -> None:
    (df.write.format("delta").mode("overwrite").option("replaceWhere", f"period = '{period}'")
     .partitionBy("period").saveAsTable(table))


def run(period: str, conf_dir: str | None = None, spark: SparkSession | None = None) -> dict:
    cfg = Config(conf_dir)
    spark = spark or get_spark(f"quality-{period}")
    bronze, quality = cfg.bronze, cfg.pipeline["quality"]
    spark.sql(f"CREATE DATABASE IF NOT EXISTS {quality['database']}")
    orig_table = f"{bronze['database']}.{bronze['orig_table']}"
    perf_table = f"{bronze['database']}.{bronze['perf_table']}"

    orig_key = [cfg.orig.column_with_role("loan_key")]
    perf_key = [cfg.perf.column_with_role("loan_key"), cfg.perf.column_with_role("reporting_period")]
    # Mồ côi: so với orig ở Bronze của mọi kỳ đến kỳ hiện tại (từ điển dữ liệu mục 5)
    orig_so_far = spark.table(orig_table).where(F.col("period") <= period).withColumnRenamed(orig_key[0], perf_key[0])

    counts = {}
    for kind, table, schema, key, orig_loans in (
        ("orig", orig_table, cfg.orig, orig_key, None),
        ("perf", perf_table, cfg.perf, perf_key, orig_so_far),
    ):
        evaluated = evaluate(spark.table(table).where(F.col("period") == period), schema, key, orig_loans).cache()
        base = f"{quality['database']}.{kind}"
        write_slice(evaluated.where(F.col("_reject_reason").isNull()).drop("_reject_reason", "_reject_column"), f"{base}_clean", period)
        write_slice(evaluated.where(F.col("_reject_reason").isNotNull()), f"{base}_quarantine", period)
        evaluated.unpersist()
        for suffix in ("clean", "quarantine"):
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
