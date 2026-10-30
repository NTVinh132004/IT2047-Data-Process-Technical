"""Sinh đợt sửa dữ liệu giả lập vào Bronze (FR-14, AC-09).

Một đợt sửa mang giá trị khởi tạo đã sửa của vài khoản vay, đến sau kỳ cuối với load_date mới và record_source
riêng. Khai báo trong conf/pipeline.yml mục corrections. Khoản vay được chọn theo seed từ orig ở Bronze (chỉ khoản vay
có đủ giá trị cho các cột sửa và giá trị sau sửa còn trong miền), nên không cần lưu dữ liệu thật trong repo; chạy lại cho cùng kết quả.

Đợt sửa được nạp như một kỳ: bronze.run() gọi write() khi kỳ là tên một đợt sửa; các tầng sau xử lý như kỳ thường.
"""
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from ingestion.config import Config


def slice_for(spark: SparkSession, cfg: Config, name: str) -> DataFrame:
    spec = cfg.pipeline["corrections"][name]
    table = f"{cfg.bronze['database']}.{cfg.bronze['orig_table']}"
    loan = cfg.orig.column_with_role("loan_key")
    columns = {c.name: c for c in cfg.orig.columns}
    orig = spark.table(table).where(~F.col("period").startswith("CORR"))
    for col, delta in spec["changes"].items():
        missing = columns[col].spec.get("missing", [])
        orig = orig.where(F.col(col).isNotNull() & ~F.col(col).isin(missing) & (F.col(col) != ""))
        # Chỉ chọn khoản vay mà giá trị sau sửa vẫn trong miền: giá trị cũ và mới chắc chắn khác nhau (AC-09)
        lo, hi = columns[col].spec.get("domain", [None, None])
        shifted = F.col(col).cast("int") + F.lit(delta)
        if lo is not None:
            orig = orig.where(shifted >= lo)
        if hi is not None:
            orig = orig.where(shifted <= hi)
    picked = orig.orderBy(F.sha2(F.concat(F.col(loan), F.lit(str(spec["seed"]))), 256)).limit(spec["loans"])
    for col, delta in spec["changes"].items():
        picked = picked.withColumn(col, (F.col(col).cast("int") + F.lit(delta)).cast("string"))
    return (picked.drop("period")
            .withColumn("load_date", F.to_date(F.lit(spec["load_date"])))
            .withColumn("source_file", F.lit(f"correction:{name}")))


def write(spark: SparkSession, cfg: Config, name: str) -> dict:
    from ingestion.bronze import write_slice

    database = cfg.bronze["database"]
    write_slice(slice_for(spark, cfg, name), f"{database}.{cfg.bronze['orig_table']}", name,
                cfg.pipeline["corrections"][name]["record_source"])
    rows = spark.table(f"{database}.{cfg.bronze['orig_table']}").where(F.col("period") == name).count()
    return {"bronze_orig_rows": rows, "bronze_perf_rows": 0}
