"""Chạy câu SQL qua Spark Thrift Server, in kết quả JSON. Dùng trong container scheduler bằng Python của dbt-venv
(có PyHive): /opt/dbt-venv/bin/python -m experiments.thrift_sql < statements.json

Đầu vào: danh sách câu SQL (JSON). Đầu ra: danh sách kết quả, mỗi câu một danh sách dòng (dict).
"""
import json
import sys

from pyhive import hive


def main() -> None:
    statements = json.load(sys.stdin)
    conn = hive.connect(host="spark-thrift", port=10000, username="lakehouse")
    results = []
    with conn.cursor() as cur:
        for sql in statements:
            cur.execute(sql)
            try:
                rows = cur.fetchall() if cur.description else []
            except TypeError:
                # Lệnh như CLEAR CACHE có description nhưng không trả result set qua Thrift (giống DEV-06)
                rows = []
            names = [d[0].split(".")[-1] for d in cur.description or []]
            results.append([dict(zip(names, row)) for row in rows])
    print(json.dumps(results, default=str))


if __name__ == "__main__":
    main()
