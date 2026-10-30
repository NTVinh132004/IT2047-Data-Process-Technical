"""Landing: chuyển file nguồn TXT sang Delta (Parquet) một lần cho mỗi bộ dữ liệu (review R-28).

File TXT của Freddie Mac là một khối không phân vùng: muốn lấy 3 tháng của một kỳ vẫn phải đọc cả file. Landing
đọc TXT một lần, giữ nguyên nội dung (mọi cột dạng chuỗi, _field_count, _raw, source_file; không ép kiểu để cổng
chất lượng còn thấy giá trị sai) và ghi:

- <source>_orig: file orig
- <source>_perf: file perf, phân vùng theo tháng báo cáo, mỗi tháng một file
- <source>_loan_first_month: tháng perf đầu tiên của từng khoản vay, để Bronze cắt lát orig (R-10)

"Dấu vân tay" của nguồn (tên, kích thước, thời điểm sửa của file TXT và nội dung conf/schema) được lưu trong file
_state_<source>.json nằm trong thư mục database landing. ensure() so dấu vân tay mà không cần khởi động Spark và chỉ
dựng lại khi nó đổi. Xóa database landing thì file trạng thái mất theo, nên landing không bao giờ trỏ vào bảng đã xóa.

Chạy: python -m ingestion.landing [--force] [--conf-dir DIR]
"""
import argparse
import hashlib
import json
from glob import glob
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from ingestion.config import Config, SourceSchema
from ingestion.spark import get_spark



def read_txt(spark: SparkSession, cfg: Config, schema: SourceSchema) -> DataFrame:
    """Đọc file TXT dạng text rồi tách theo dấu |. Reader CSV với schema cố định tự lấp null hoặc cắt bớt khi
    số trường lệch, làm mất bằng chứng cho luật "sai số trường" (R-27)."""
    lines = spark.read.text(cfg.raw_files(schema))
    fields = F.split("value", r"\|", -1)
    return lines.select(
        *[fields.getItem(c.pos - 1).alias(c.name) for c in schema.columns],
        F.size(fields).alias("_field_count"),
        F.when(F.size(fields) != schema.field_count, F.col("value")).alias("_raw"),
        F.input_file_name().alias("source_file"),
    )


def fingerprint(cfg: Config, schema: SourceSchema) -> str:
    files = sorted(glob(cfg.raw_files(schema)))
    if not files:
        raise FileNotFoundError(f"Không có file nguồn khớp {cfg.raw_files(schema)}")
    stats = [(Path(f).name, Path(f).stat().st_size, Path(f).stat().st_mtime_ns) for f in files]
    schema_text = (cfg.conf_dir / "schema" / f"{schema.kind}.yml").read_text()
    return hashlib.sha256(json.dumps([stats, schema_text]).encode()).hexdigest()


def table_names(cfg: Config) -> dict[str, str]:
    database = cfg.pipeline["landing"]["database"]
    return {kind: f"{database}.{cfg.source}_{kind}" for kind in ("orig", "perf", "loan_first_month")}


def state_file(cfg: Config) -> Path:
    """Trong thư mục database landing (warehouse của metastore, docker/spark/conf/hive-site.xml)."""
    database = cfg.pipeline["landing"]["database"]
    return Path(cfg.pipeline["paths"]["lake"]) / "warehouse" / f"{database}.db" / f"_state_{cfg.source}.json"


def read_state(cfg: Config) -> dict:
    path = state_file(cfg)
    return json.loads(path.read_text()) if path.exists() else {}


def write(df: DataFrame, table: str, partition_by: str | None = None) -> None:
    writer = df.write.format("delta").mode("overwrite").option("overwriteSchema", "true")
    if partition_by:
        writer = writer.partitionBy(partition_by)
    writer.saveAsTable(table)


def ensure(cfg: Config | None = None, force: bool = False, spark: SparkSession | None = None) -> dict:
    """Dựng lại các bảng landing nếu nguồn hoặc schema đã đổi. Trả về bảng nào được dựng lại."""
    cfg = cfg or Config()
    state = read_state(cfg)
    current = {"orig": fingerprint(cfg, cfg.orig), "perf": fingerprint(cfg, cfg.perf)}
    rebuilt = {kind: force or state.get(kind) != fp for kind, fp in current.items()}
    if not any(rebuilt.values()):
        return rebuilt

    spark = spark or get_spark("landing")
    tables = table_names(cfg)
    spark.sql(f"CREATE DATABASE IF NOT EXISTS {cfg.pipeline['landing']['database']}")
    month = cfg.perf.column_with_role("reporting_period")
    loan = cfg.perf.column_with_role("loan_key")
    if rebuilt["orig"]:
        write(read_txt(spark, cfg, cfg.orig), tables["orig"])
    if rebuilt["perf"]:
        # Mỗi tháng một file: không repartition thì mỗi khối đọc ghi một file nhỏ vào mọi tháng nó gặp
        write(read_txt(spark, cfg, cfg.perf).repartition(month), tables["perf"], partition_by=month)
        first = spark.table(tables["perf"]).groupBy(loan).agg(F.min(month).alias("first_month"))
        write(first, tables["loan_first_month"])
    # Ghi trạng thái sau cùng: nếu job chết giữa chừng, lần sau sẽ dựng lại
    state_file(cfg).write_text(json.dumps(current))
    return rebuilt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="Dựng lại kể cả khi nguồn không đổi")
    parser.add_argument("--conf-dir", help="Thư mục cấu hình, mặc định conf/")
    args = parser.parse_args()
    print(json.dumps(ensure(Config(args.conf_dir), args.force)))


if __name__ == "__main__":
    main()
