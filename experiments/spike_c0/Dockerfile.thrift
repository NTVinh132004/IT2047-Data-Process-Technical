# Jar Delta phải nằm trong /opt/spark/jars: nạp bằng --packages thì Thrift Server không thấy class Delta
# Spark 3.5.7 làm hỏng CREATE OR REPLACE TABLE AS SELECT của Delta 3.3.2 (dbt-spark cần lệnh này); 3.5.5 chạy đúng
FROM apache/spark:3.5.5-scala2.12-java17-python3-ubuntu
USER root
ARG MAVEN=https://repo1.maven.org/maven2/io/delta
RUN cd /opt/spark/jars \
 && curl -fsSLO $MAVEN/delta-spark_2.12/3.3.2/delta-spark_2.12-3.3.2.jar \
 && curl -fsSLO $MAVEN/delta-storage/3.3.2/delta-storage-3.3.2.jar
