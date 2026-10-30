# Hive Metastore 3.1.3 (client Hive tích hợp trong Spark 3.5 là 2.3.9, tương thích với metastore 3.1),
# metadata lưu trên PostgreSQL (database metastore). Image không có curl/wget nên tải jar bằng ADD.
FROM apache/hive:3.1.3
ADD --chown=hive:hive https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.4/postgresql-42.7.4.jar /opt/hive/lib/
COPY --chown=hive:hive start-metastore.sh /opt/start-metastore.sh
ENTRYPOINT ["bash", "/opt/start-metastore.sh"]
