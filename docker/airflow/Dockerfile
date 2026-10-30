# Airflow 3 (LocalExecutor): task chạy trong container scheduler, nên image cần Java và PySpark
# để chạy job Spark local mode (review R-27). Phiên bản Spark/Delta khớp với Thrift Server.
FROM apache/airflow:3.3.2-python3.11
USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends openjdk-17-jre-headless procps \
 && rm -rf /var/lib/apt/lists/*
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
# dbt trong virtualenv riêng: dbt-core và Airflow ràng buộc khác nhau trên thư viện dùng chung (pydantic, protobuf...).
# wheels/: wheel tải sẵn (không nằm trong git). dbt-core-experimental-parser chỉ có sdist, lúc cài tải 55 MB từ
# GitHub Releases; mạng chậm thì build treo. Có wheel trong wheels/ thì pip dùng nó, không có thì tải như thường.
COPY wheels/ /tmp/wheels/
RUN python -m venv /opt/dbt-venv \
 && /opt/dbt-venv/bin/pip install --no-cache-dir --find-links /tmp/wheels "dbt-core==1.12.5" "dbt-spark[PyHive]==1.11.0"
USER airflow
RUN pip install --no-cache-dir "pyspark==3.5.5" "delta-spark==3.3.2" \
 && cd "$(python -c 'import pyspark, os; print(os.path.dirname(pyspark.__file__))')/jars" \
 && curl -fsSLO https://repo1.maven.org/maven2/io/delta/delta-spark_2.12/3.3.2/delta-spark_2.12-3.3.2.jar \
 && curl -fsSLO https://repo1.maven.org/maven2/io/delta/delta-storage/3.3.2/delta-storage-3.3.2.jar
