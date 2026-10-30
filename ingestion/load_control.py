"""Bảng control.load_control trong database analytics (FR-02): mỗi lần chạy DAG một dòng.

Một dòng gắn với một DAG run của Airflow (airflow_run_id). Chạy lại một task lỗi trong cùng DAG run cập nhật
dòng đó; chạy lại cả kỳ (DAG run mới) thêm dòng mới.

Chạy: python -m ingestion.load_control pending   -> in các kỳ chưa SUCCESS, theo thứ tự (cho make run-all)
"""
import os
import sys

import psycopg2

from ingestion.config import Config
from ingestion.periods import periods_between


def connect():
    return psycopg2.connect(os.environ["ANALYTICS_DSN"])


def start(period: str, dataset: str, airflow_run_id: str) -> int:
    """Ghi dòng RUNNING; nếu DAG run này đã có dòng (task được chạy lại) thì mở lại dòng đó."""
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE control.load_control SET status = 'RUNNING', error = NULL, finished_at = NULL"
            " WHERE airflow_run_id = %s RETURNING run_id",
            (airflow_run_id,),
        )
        row = cur.fetchone()
        if row is None:
            cur.execute(
                "INSERT INTO control.load_control (period, status, dataset, airflow_run_id)"
                " VALUES (%s, 'RUNNING', %s, %s) RETURNING run_id",
                (period, dataset, airflow_run_id),
            )
            row = cur.fetchone()
        return row[0]


def finish(airflow_run_id: str, status: str, error: str | None = None, **counts: int | None) -> None:
    allowed = {"rows_in", "rows_clean", "rows_rejected", "bronze_orig_rows", "bronze_perf_rows"}
    if unknown := set(counts) - allowed:
        raise ValueError(f"Cột không có trong load_control: {unknown}")
    sets = "".join(f", {name} = %({name})s" for name in counts)
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE control.load_control SET status = %(status)s, error = %(error)s, finished_at = now(),"
            " duration_s = EXTRACT(EPOCH FROM now() - started_at)" + sets +
            " WHERE airflow_run_id = %(airflow_run_id)s",
            {"status": status, "error": error, "airflow_run_id": airflow_run_id, **counts},
        )


def pending_periods(cfg: Config | None = None) -> list[str]:
    """Các kỳ trong conf chưa có lần chạy SUCCESS, theo thứ tự thời gian (FR-01).

    Lần chạy chỉ tính khi đã qua cổng chất lượng (rows_clean có giá trị): lần chạy của DAG giai đoạn 1, chưa có
    cổng chất lượng và Raw Vault, không được coi là đã nạp xong kỳ.
    """
    cfg = cfg or Config()
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT period FROM control.load_control"
            " WHERE status = 'SUCCESS' AND rows_clean IS NOT NULL AND dataset = %s",
            (cfg.source,),
        )
        done = {r[0] for r in cur.fetchall()}
    periods = cfg.pipeline["periods"]
    return [p for p in periods_between(periods["first"], periods["last"]) if p not in done]


if __name__ == "__main__":
    if sys.argv[1:] != ["pending"]:
        sys.exit("Dùng: python -m ingestion.load_control pending")
    for period in pending_periods():
        print(period)
