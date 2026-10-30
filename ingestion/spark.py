"""SparkSession cho job PySpark. Cấu hình (Delta, Hive Metastore, warehouse) nằm ở SPARK_CONF_DIR,
dùng chung với Thrift Server: docker/spark/conf/."""
from pyspark.sql import SparkSession


def get_spark(app_name: str) -> SparkSession:
    return SparkSession.builder.appName(app_name).enableHiveSupport().getOrCreate()
