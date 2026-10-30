"""Nạp Bronze cho một kỳ (FR-04).

Một kỳ là một quý báo cáo. Lát perf của kỳ là các dòng có tháng báo cáo trong quý; lát orig là các khoản vay
có tháng perf đầu tiên trong quý (R-10). Lát của kỳ được ghi đè bằng Delta replaceWhere, nên chạy lại kỳ
không đổi số dòng.

Bronze đọc từ landing (ingestion/landing.py), nơi file TXT đã được chuyển sang Delta một lần, phân vùng theo
tháng (R-28): mỗi kỳ chỉ đọc 3 thư mục tháng. Giá trị giữ dạng chuỗi, chưa ép kiểu, để cổng chất lượng (FR-07)
còn thấy giá trị sai kiểu.

Chạy: python -m ingestion.bronze --period 2020Q1 [--conf-dir DIR]
"""
import argparse
import json

from pyspark.sql import Column as SparkColumn
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from ingestion import landing
from ingestion.config import Config
from ingestion.periods import months_in_period
from ingestion.spark import get_spark


def load_date_of(reporting_period: SparkColumn, lag_months: int) -> SparkColumn:
    """load_date = ngày 1 của tháng (reporting_period + lag_months); cùng quy tắc với periods.load_date_for."""
    return F.add_months(F.to_date(F.concat(reporting_period, F.lit("01")), "yyyyMMdd"), lag_months)


def perf_slice(spark: SparkSession, cfg: Config, period: str) -> DataFrame:
    month = cfg.perf.column_with_role("reporting_period")
    return (
        spark.table(landing.table_names(cfg)["perf"])
        .where(F.col(month).isin(months_in_period(period)))
        .withColumn("load_date", load_date_of(F.col(month), cfg.lag_months))
    )


def orig_slice(spark: SparkSession, cfg: Config, period: str) -> DataFrame:
    """Khoản vay có tháng perf đầu tiên thuộc kỳ, mang load_date của tháng đó."""
    tables = landing.table_names(cfg)
    orig_loan = cfg.orig.column_with_role("loan_key")
    first = (
        spark.table(tables["loan_first_month"])
        .where(F.col("first_month").isin(months_in_period(period)))
        .withColumnRenamed(cfg.perf.column_with_role("loan_key"), "_loan")
    )
    return (
        spark.table(tables["orig"])
        .join(first, F.col(orig_loan) == F.col("_loan"), "inner")
        .withColumn("load_date", load_date_of(F.col("first_month"), cfg.lag_months))
        .drop("_loan", "first_month")
    )


def write_slice(df: DataFrame, table: str, period: str, record_source: str) -> None:
    (
        df.withColumn("record_source", F.lit(record_source))
        .withColumn("period", F.lit(period))
        .write.format("delta")
        .mode("overwrite")
        .option("replaceWhere", f"period = '{period}'")
        .partitionBy("period")
        .saveAsTable(table)
    )


def run(period: str, conf_dir: str | None = None, spark: SparkSession | None = None) -> dict:
    cfg = Config(conf_dir)
    spark = spark or get_spark(f"bronze-{period}")
    landing.ensure(cfg, spark=spark)
    database = cfg.bronze["database"]
    spark.sql(f"CREATE DATABASE IF NOT EXISTS {database}")
    tables = {"orig": f"{database}.{cfg.bronze['orig_table']}", "perf": f"{database}.{cfg.bronze['perf_table']}"}
    write_slice(orig_slice(spark, cfg, period), tables["orig"], period, cfg.record_source)
    write_slice(perf_slice(spark, cfg, period), tables["perf"], period, cfg.record_source)
    return {
        f"bronze_{kind}_rows": spark.table(table).where(F.col("period") == period).count()
        for kind, table in tables.items()
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--period", required=True, help="Kỳ nạp, ví dụ 2020Q1")
    parser.add_argument("--conf-dir", help="Thư mục cấu hình, mặc định conf/")
    args = parser.parse_args()
    print(json.dumps(run(args.period, args.conf_dir)))


if __name__ == "__main__":
    main()
