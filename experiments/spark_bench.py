"""Thực nghiệm PySpark chạy trong container scheduler của stack thực nghiệm (R-38): TN4 và TN7.

- TN4: trạng thái khoản vay tại mốc thời gian qua PIT (equi-join) so với join trực tiếp Satellite theo as-of
  (load_date lớn nhất không vượt mốc). Hai cách phải ra cùng checksum; đo thời gian và độ phức tạp kế hoạch.
- TN7: kỹ thuật nạp TXT → landing → Bronze: (a) chi phí dựng landing một lần; (b) cắt lát Bronze một kỳ đọc thẳng
  TXT so với đọc landing phân vùng theo tháng; (c) reader text + split so với reader CSV, về thời gian và khả năng
  giữ bằng chứng sai số trường; (d) dung lượng và số file từng tầng.

Quy tắc đo (Kế hoạch mục 8): lần 0 là khởi động, bị loại khi tổng hợp; lần 1..N được đo. Bấm giờ quanh action
(ghi format noop hoặc aggregate collect). Không cache DataFrame; xóa cache Spark trước mỗi lần.

Chạy: python -m experiments.spark_bench tn4|tn7 [--reps 3]
"""
import argparse
import contextlib
import csv
import io
import json
import shutil
import time
from datetime import datetime
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType

from experiments.queries import SATS, SCENARIOS, direct_query, pit_query, plan_stats, sql_stats
from ingestion import bronze, landing
from ingestion.config import Config
from ingestion.periods import months_in_period
from ingestion.spark import get_spark

RESULTS = Path("/opt/project/experiments/results")
PLANS = RESULTS / "plans"
SCRATCH = Path("/lake/exp_scratch")


class Recorder:
    """Ghi từng dòng kết quả ngay khi đo xong vào <name>.csv.partial; đổi tên khi xong cả thực nghiệm."""

    def __init__(self, name: str):
        RESULTS.mkdir(parents=True, exist_ok=True)
        self.final = RESULTS / f"{name}.csv"
        self.path = RESULTS / f"{name}.csv.partial"
        self.path.unlink(missing_ok=True)
        self.fields: list[str] | None = None

    def add(self, **row) -> None:
        row = {"measured_at": datetime.now().isoformat(timespec="seconds"), **row}
        new = self.fields is None
        if new:
            self.fields = list(row)
        with self.path.open("a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.fields)
            if new:
                writer.writeheader()
            writer.writerow(row)
        print(json.dumps(row, default=str), flush=True)

    def done(self) -> None:
        self.path.replace(self.final)


def timed(action) -> tuple[float, object]:
    start = time.perf_counter()
    result = action()
    return round(time.perf_counter() - start, 3), result


def plan_text(df: DataFrame) -> str:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        df.explain(mode="formatted")
    return buffer.getvalue()


def noop(df: DataFrame) -> None:
    df.write.format("noop").mode("overwrite").save()


# ---------------------------------------------------------------- TN4

def checksum(spark: SparkSession, sql: str) -> DataFrame:
    columns = ", ".join(["LOAN_HK", "AS_OF_DATE"] + [col for _, col, _ in SATS])
    return spark.sql(f"SELECT COUNT(*) AS n, SUM(CAST(xxhash64({columns}) AS DECIMAL(38, 0))) AS h FROM ({sql}) AS q")


def tn4(spark: SparkSession, reps: int) -> None:
    rec = Recorder("tn4_pit")
    PLANS.mkdir(parents=True, exist_ok=True)
    for scenario, as_of in SCENARIOS.items():
        for method, build in (("pit", pit_query), ("direct", direct_query)):
            sql = build(as_of)
            df = checksum(spark, sql)
            plan = plan_text(df)
            (PLANS / f"tn4_{scenario}_{method}.txt").write_text(sql + "\n\n" + plan)
            stats = {**sql_stats(sql), **plan_stats(plan)}
            for run in range(reps + 1):
                spark.catalog.clearCache()
                seconds, row = timed(lambda: checksum(spark, sql).collect()[0])
                rec.add(experiment="TN4", scenario=scenario, method=method, run=run, warmup=run == 0,
                        seconds=seconds, rows=row["n"], checksum=str(row["h"]), **stats)
    rec.done()


# ---------------------------------------------------------------- TN7

def direct_bronze_slices(spark: SparkSession, cfg: Config, period: str) -> tuple[DataFrame, DataFrame]:
    """Cách trước R-28: mỗi kỳ đọc thẳng TXT, quét cả file perf để lấy lát tháng và tháng perf đầu tiên."""
    months = months_in_period(period)
    month, loan = cfg.perf.column_with_role("reporting_period"), cfg.perf.column_with_role("loan_key")
    perf = landing.read_txt(spark, cfg, cfg.perf)
    perf_slice = perf.where(F.col(month).isin(months)).withColumn("load_date", bronze.load_date_of(F.col(month), cfg.lag_months))
    first = (perf.groupBy(loan).agg(F.min(month).alias("first_month"))
             .where(F.col("first_month").isin(months)).withColumnRenamed(loan, "_loan"))
    orig_slice = (landing.read_txt(spark, cfg, cfg.orig)
                  .join(first, F.col(cfg.orig.column_with_role("loan_key")) == F.col("_loan"), "inner")
                  .withColumn("load_date", bronze.load_date_of(F.col("first_month"), cfg.lag_months))
                  .drop("_loan", "first_month"))
    return orig_slice, perf_slice


def landing_bronze_slices(spark: SparkSession, cfg: Config, period: str) -> tuple[DataFrame, DataFrame]:
    return bronze.orig_slice(spark, cfg, period), bronze.perf_slice(spark, cfg, period)


def build_landing_at(spark: SparkSession, cfg: Config, root: Path) -> None:
    """Giống landing.ensure() nhưng ghi vào thư mục tạm theo đường dẫn, không đụng bảng landing thật."""
    month, loan = cfg.perf.column_with_role("reporting_period"), cfg.perf.column_with_role("loan_key")
    landing.read_txt(spark, cfg, cfg.orig).write.format("delta").mode("overwrite").save(str(root / "orig"))
    (landing.read_txt(spark, cfg, cfg.perf).repartition(month).write.format("delta").mode("overwrite")
     .partitionBy(month).save(str(root / "perf")))
    perf = spark.read.format("delta").load(str(root / "perf"))
    (perf.groupBy(loan).agg(F.min(month).alias("first_month")).write.format("delta").mode("overwrite")
     .save(str(root / "loan_first_month")))


def csv_reader(spark: SparkSession, path: str, field_count: int) -> DataFrame:
    schema = StructType([StructField(f"c{i}", StringType()) for i in range(1, field_count + 1)]
                        + [StructField("_corrupt", StringType())])
    return (spark.read.schema(schema).option("sep", "|").option("mode", "PERMISSIVE")
            .option("columnNameOfCorruptRecord", "_corrupt").csv(path))


def fault_file(cfg: Config, target: Path, lines: int = 2000, faults: int = 10) -> dict:
    """File perf giả lập: dòng thật đầu file, cài `faults` dòng thiếu một trường và `faults` dòng thừa một trường."""
    source = Path(cfg.raw_files(cfg.perf))
    rows = []
    with source.open() as f:
        for _ in range(lines):
            rows.append(f.readline().rstrip("\n"))
    for i in range(faults):
        rows[10 + i * 7] = rows[10 + i * 7].rsplit("|", 2)[0] + "|"      # thiếu một trường
        rows[500 + i * 7] = rows[500 + i * 7] + "X|"                      # thừa một trường
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(rows) + "\n")
    return {"lines": lines, "short": faults, "long": faults}


def table_storage(spark: SparkSession, table: str) -> dict:
    detail = spark.sql(f"DESCRIBE DETAIL {table}").collect()[0]
    return {"table": table, "rows": spark.table(table).count(), "size_bytes": detail["sizeInBytes"],
            "num_files": detail["numFiles"], "partition_columns": ",".join(detail["partitionColumns"])}


STORAGE_TABLES = [
    "landing.sample_orig", "landing.sample_perf", "landing.sample_loan_first_month",
    "bronze.orig", "bronze.perf", "quality.orig_clean", "quality.perf_clean",
    "staging.stg_orig", "staging.stg_perf",
    "raw_vault.hub_loan", "raw_vault.hub_seller", "raw_vault.hub_servicer", "raw_vault.link_loan_seller",
    "raw_vault.link_loan_servicer", "raw_vault.sat_loan_origination", "raw_vault.sat_loan_property",
    "raw_vault.sat_loan_balance", "raw_vault.sat_loan_delinquency", "raw_vault.sat_loan_termination",
    "raw_vault.xts_loan", "raw_vault.xts_loan_servicer",
    "business_vault.pit_loan_monthly", "business_vault.bsat_loan_risk", "business_vault.bsat_loan_lifecycle",
    "gold.fact_loan_month", "gold.dim_loan", "gold.mart_delinquency", "gold.mart_prepayment",
    "gold.mart_covid_forbearance",
]
TN7_PERIODS = ["2019Q1", "2020Q2", "2023Q1", "2026Q1"]


def tn7(spark: SparkSession, reps: int) -> None:
    cfg = Config()
    # (d) dung lượng: nguồn TXT và các bảng Delta hiện hành (DESCRIBE DETAIL: snapshot hiện tại, không tính file cũ)
    rec = Recorder("tn7_storage")
    for kind in ("orig", "perf"):
        path = Path(cfg.raw_files(getattr(cfg, kind)))
        rec.add(experiment="TN7", layer="source_txt", table=path.name, rows=sum(1 for _ in path.open("rb")),
                size_bytes=path.stat().st_size, num_files=1, partition_columns="")
    for table in STORAGE_TABLES:
        rec.add(experiment="TN7", layer=table.split(".")[0], **table_storage(spark, table))
    rec.done()

    # (a) dựng landing một lần cho cả bộ dữ liệu
    rec = Recorder("tn7_landing_build")
    for run in range(reps + 1):
        root = SCRATCH / f"landing_{run}"
        shutil.rmtree(root, ignore_errors=True)
        spark.catalog.clearCache()
        seconds, _ = timed(lambda: build_landing_at(spark, cfg, root))
        files = sum(1 for p in (root / "perf").rglob("*.parquet"))
        rec.add(experiment="TN7", step="landing_build", run=run, warmup=run == 0, seconds=seconds, perf_files=files)
        shutil.rmtree(root, ignore_errors=True)
    rec.done()

    # (b) cắt lát Bronze một kỳ: TXT trực tiếp vs landing
    rec = Recorder("tn7_bronze_slice")
    PLANS.mkdir(parents=True, exist_ok=True)
    for period in TN7_PERIODS:
        for method, slices in (("txt_direct", direct_bronze_slices), ("landing", landing_bronze_slices)):
            orig, perf = slices(spark, cfg, period)
            (PLANS / f"tn7_{period}_{method}_perf.txt").write_text(plan_text(perf))
            for run in range(reps + 1):
                spark.catalog.clearCache()
                orig, perf = slices(spark, cfg, period)
                seconds, _ = timed(lambda: (noop(orig), noop(perf)))
                counts = (orig.count(), perf.count()) if run == 0 else ("", "")
                rec.add(experiment="TN7", step="bronze_slice", period=period, method=method, run=run, warmup=run == 0,
                        seconds=seconds, orig_rows=counts[0], perf_rows=counts[1],
                        input_files=len(perf.inputFiles()))
    rec.done()

    # (c) reader: thời gian trên cả file perf và khả năng phát hiện sai số trường trên file giả lập
    rec = Recorder("tn7_reader")
    perf_path = cfg.raw_files(cfg.perf)
    for method in ("text_split", "csv_reader"):
        for run in range(reps + 1):
            spark.catalog.clearCache()
            df = landing.read_txt(spark, cfg, cfg.perf) if method == "text_split" else csv_reader(spark, perf_path, cfg.perf.field_count)
            seconds, _ = timed(lambda: noop(df))
            rec.add(experiment="TN7", step="reader_full_perf", method=method, run=run, warmup=run == 0, seconds=seconds)
    rec.done()

    rec = Recorder("tn7_reader_faults")
    fault_path = SCRATCH / "faults" / "perf_faults.txt"
    injected = fault_file(cfg, fault_path)
    text = (spark.read.text(str(fault_path)).select(F.size(F.split("value", r"\|", -1)).alias("n")))
    detected_text = text.where(F.col("n") != cfg.perf.field_count).count()
    csv_df = csv_reader(spark, str(fault_path), cfg.perf.field_count)
    csv_df.cache()  # Spark bắt buộc cache khi chỉ truy vấn cột corrupt record
    detected_csv = csv_df.where(F.col("_corrupt").isNotNull()).count()
    rows_csv = csv_df.count()
    csv_df.unpersist()
    total = injected["short"] + injected["long"]
    rec.add(experiment="TN7", step="reader_faults", method="text_split", injected=total, detected=detected_text,
            rows=text.count(), lines=injected["lines"], signal="_field_count, _raw")
    rec.add(experiment="TN7", step="reader_faults", method="csv_reader", injected=total, detected=detected_csv,
            rows=rows_csv, lines=injected["lines"], signal="_corrupt (cả dòng gốc, các trường vẫn được lấp/cắt)")
    # Cấu hình mặc định: không có cột lỗi, dòng thiếu trường được lấp null, dòng thừa bị cắt; không còn dấu hiệu nào
    plain = (spark.read.schema(StructType([StructField(f"c{i}", StringType()) for i in range(1, cfg.perf.field_count + 1)]))
             .option("sep", "|").csv(str(fault_path)))
    rec.add(experiment="TN7", step="reader_faults", method="csv_default", injected=total, detected=0,
            rows=plain.count(), lines=injected["lines"], signal="không có")
    # FAILFAST: dừng cả lần đọc ở dòng lỗi đầu tiên, không nạp được dòng tốt nào
    try:
        failfast = spark.read.schema(plain.schema).option("sep", "|").option("mode", "FAILFAST").csv(str(fault_path))
        noop(failfast)  # count() không phân tích cột nên không gặp lỗi; ghi noop buộc đọc mọi trường
        rows_failfast, outcome = failfast.count(), "đọc hết"
    except Exception as exc:  # noqa: BLE001 - ghi loại lỗi làm kết quả đo
        rows_failfast, outcome = 0, f"dừng: {type(exc).__name__}"
    rec.add(experiment="TN7", step="reader_faults", method="csv_failfast", injected=total,
            detected="", rows=rows_failfast, lines=injected["lines"], signal=outcome)
    rec.done()
    shutil.rmtree(SCRATCH, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("experiment", choices=["tn4", "tn7"])
    parser.add_argument("--reps", type=int, default=3)
    args = parser.parse_args()
    spark = get_spark(f"experiment-{args.experiment}")
    {"tn4": tn4, "tn7": tn7}[args.experiment](spark, args.reps)


if __name__ == "__main__":
    main()
