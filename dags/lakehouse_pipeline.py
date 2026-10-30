"""DAG nạp một kỳ (FR-01, FR-21).

Trigger với conf {"period": "2020Q1"} (make run PERIOD=2020Q1). Chỉ một lượt chạy cùng lúc, task retry 2 lần.
Mỗi DAG run ghi một dòng control.load_control.

Thứ tự: landing (chuyển TXT sang Delta, chỉ chạy khi nguồn đổi, R-28) → Bronze → cổng chất lượng (FR-07) →
dbt build tầng Raw Vault: model rồi dbt test của tầng; test lỗi thì task lỗi và DAG dừng trước tầng sau (FR-22).
Business Vault, Gold và xuất PostgreSQL được thêm ở các giai đoạn sau, sau khi cổng trước đạt.
"""
from datetime import timedelta

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import Param, dag, get_current_context, task

DBT = "cd /opt/project/dbt && /opt/dbt-venv/bin/dbt"
DBT_VARS = (
    "--vars '{\"period\": \"{{ params.period }}\", "
    "\"inject_test_failure\": {{ params.inject_test_failure | tojson }}}'"
)


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
    params={
        "period": Param(type="string", pattern=r"^\d{4}Q[1-4]$", description="Kỳ nạp (quý báo cáo), ví dụ 2020Q1"),
        "inject_test_failure": Param(False, type="boolean",
                                     description="Bật một dbt test cố ý sai để kiểm DAG dừng (FR-22, cổng C2)"),
    },
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
    def quality() -> dict:
        from ingestion import quality as quality_job

        return quality_job.run(get_current_context()["params"]["period"])

    raw_vault = BashOperator(
        task_id="raw_vault",
        bash_command=f"{DBT} build --select +raw_vault --exclude tag:hash_test {DBT_VARS}",
    )

    @task
    def finish_run(bronze_counts: dict, quality_counts: dict) -> None:
        from ingestion import load_control

        load_control.finish(
            get_current_context()["dag_run"].run_id, "SUCCESS",
            rows_in=bronze_counts["bronze_orig_rows"] + bronze_counts["bronze_perf_rows"],
            rows_clean=quality_counts["rows_clean"], rows_rejected=quality_counts["rows_rejected"],
            **bronze_counts,
        )

    bronze_counts = bronze()
    quality_counts = quality()
    start_run() >> landing() >> bronze_counts >> quality_counts >> raw_vault
    raw_vault >> finish_run(bronze_counts, quality_counts)


lakehouse_pipeline()
