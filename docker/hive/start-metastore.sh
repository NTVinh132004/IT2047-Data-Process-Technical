#!/bin/bash
# Entrypoint gốc của apache/hive:3.1.3 chạy -initSchema mỗi lần khởi động và thoát khi schema đã có.
# Script này chỉ khởi tạo khi schematool -info báo chưa có schema, nên container khởi động lại được.
set -euo pipefail
export HIVE_CONF_DIR=$HIVE_HOME/conf
export HADOOP_CLIENT_OPTS="${HADOOP_CLIENT_OPTS:-} -Xmx512m ${SERVICE_OPTS}"
if ! "$HIVE_HOME/bin/schematool" -dbType postgres -info >/dev/null 2>&1; then
  "$HIVE_HOME/bin/schematool" -dbType postgres -initSchema
fi
exec "$HIVE_HOME/bin/hive" --skiphadoopversion --skiphbasecp --service metastore
