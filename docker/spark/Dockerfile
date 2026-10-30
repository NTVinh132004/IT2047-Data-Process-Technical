# Spark Thrift Server cho dbt. Spark 3.5.7 làm hỏng CREATE OR REPLACE TABLE AS SELECT của Delta 3.3.2,
# nên dùng 3.5.5 (review R-26). Jar Delta nằm trong /opt/spark/jars vì Thrift Server không thấy class nạp bằng --packages.
FROM apache/spark:3.5.5-scala2.12-java17-python3-ubuntu
USER root
ARG MAVEN=https://repo1.maven.org/maven2/io/delta
RUN cd /opt/spark/jars \
 && curl -fsSLO $MAVEN/delta-spark_2.12/3.3.2/delta-spark_2.12-3.3.2.jar \
 && curl -fsSLO $MAVEN/delta-storage/3.3.2/delta-storage-3.3.2.jar
# Mọi container chạy uid 1000 để dùng chung data/lake (R-27); Java cần user có thư mục home
RUN useradd --uid 1000 --gid 0 --create-home --shell /bin/bash lakehouse \
 && mkdir -p /opt/spark/logs /opt/spark/work-dir \
 && chown -R 1000:0 /opt/spark/logs /opt/spark/work-dir
USER 1000
