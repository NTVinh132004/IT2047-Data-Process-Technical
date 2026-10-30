"""DAG nạp một kỳ (FR-01, FR-21).

Trigger với conf {"period": "2020Q1"} (make run PERIOD=2020Q1). Chỉ một lượt chạy cùng lúc, task retry 2 lần.
Mỗi DAG run ghi một dòng control.load_control. Giai đoạn 1 có landing (chuyển TXT sang Delta, chỉ chạy khi nguồn
đổi, R-28) và Bronze; cổng chất lượng, dbt và xuất PostgreSQL
được thêm ở các giai đoạn sau, sau khi cổng trước đạt.
"""
from datetime import timedelta

from airflow.sdk import Param, dag, get_current_context, task


def _mark_failed(context) -> None:
    from ingestion import load_control

    dag_run = context["dag_run"]
    load_control.finish(dag_run.run_id, "FAILED", error=str(context.get("reason") or "DAG run thất bại"))


@dag(
    dag_id="lakehouse_pipeline",
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(seconds=30)},
    params={"period": Param(type="string", pattern=r"^\d{4}Q[1-4]$", description="Kỳ nạp (quý báo cáo), ví dụ 2020Q1")},
    on_failure_callback=_mark_failed,
    tags=["lakehouse"],
)
def lakehouse_pipeline():
    @task
    def start_run() -> None:
        from ingestion import load_control
        from ingestion.config import Config

        ctx = get_current_context()
        load_control.start(ctx["params"]["period"], Config().source, ctx["dag_run"].run_id)

    @task
    def landing() -> dict:
        from ingestion import landing as landing_job

        return landing_job.ensure()

    @task
    def bronze() -> dict:
        from ingestion import bronze as bronze_job

        return bronze_job.run(get_current_context()["params"]["period"])

    @task
    def finish_run(counts: dict) -> None:
        from ingestion import load_control

        rows_in = counts["bronze_orig_rows"] + counts["bronze_perf_rows"]
        load_control.finish(get_current_context()["dag_run"].run_id, "SUCCESS", rows_in=rows_in, **counts)

    start_run() >> landing() >> (counts := bronze())
    finish_run(counts)


lakehouse_pipeline()
