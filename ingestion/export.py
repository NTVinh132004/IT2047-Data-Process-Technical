"""FR-17: JDBC từ Gold Delta sang PostgreSQL, công bố ba mart trong một transaction.

Bảng trung gian độc lập với serving. Lỗi ghi/đối soát không thay đổi bản đang phục vụ;
retry ghi đè bảng trung gian. Khóa publication dùng chung với job Gold (ingestion.layers).
"""
import os

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import parse_dsn

from ingestion.config import Config


def publish(dsn: str, marts: list[str]) -> None:
    """Công bố cùng lúc hoặc rollback toàn bộ, giữ bản phục vụ trước khi lỗi."""
    with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
        for name in marts:
            ident = sql.Identifier(name)
            cur.execute(sql.SQL('CREATE TABLE IF NOT EXISTS serving.{} (LIKE export_stage.{} INCLUDING ALL)').format(ident, ident))
            cur.execute(sql.SQL('DELETE FROM serving.{}').format(ident))
            cur.execute(sql.SQL('INSERT INTO serving.{} SELECT * FROM export_stage.{}').format(ident, ident))


def run() -> dict:
    from ingestion.spark import get_spark
    cfg = Config().pipeline['export']
    dsn = os.environ['ANALYTICS_DSN']
    connection = parse_dsn(dsn)
    url = f"jdbc:postgresql://{connection['host']}:{connection.get('port', '5432')}/{connection['dbname']}"
    spark = get_spark('export-gold')
    counts = {}
    try:
        with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
            for schema in ('export_stage', 'serving'):
                cur.execute(sql.SQL('CREATE SCHEMA IF NOT EXISTS {}').format(sql.Identifier(schema)))
        for name in cfg['marts']:
            frame = spark.table(f"{cfg['database']}.{name}").cache()
            try:
                expected = frame.count()
                frame.coalesce(1).write.format('jdbc').option('url', url).option('dbtable', f'export_stage.{name}').option(
                    'user', connection['user']).option('password', connection['password']).option(
                    'driver', 'org.postgresql.Driver').mode('overwrite').save()
                with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
                    cur.execute(sql.SQL('SELECT COUNT(*) FROM export_stage.{}').format(sql.Identifier(name)))
                    actual = cur.fetchone()[0]
                    if actual != expected:
                        raise ValueError(f'{name}: Delta={expected}, JDBC={actual}')
                counts[name] = expected
            finally:
                frame.unpersist()
        # Giữ nguyên bảng serving (và quyền truy cập) khi công bố bản mới.
        publish(dsn, cfg['marts'])
        return {'rows_in': sum(counts.values()), 'marts': counts}
    finally:
        spark.stop()


if __name__ == '__main__':
    print(run())
