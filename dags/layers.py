"""Mỗi tầng một DAG (FR-21, review R-33): layer_ingest, layer_quality, layer_raw_vault, layer_business_vault.

Mỗi DAG chạy định kỳ (5 phút) và khi tầng trên vừa xử lý xong việc (task nudge_next). Mỗi lượt: nhận kỳ sẵn sàng sớm
nhất từ bảng điều khiển (ingestion/control.py), xử lý, ghi trạng thái, lặp đến khi hết kỳ sẵn sàng. Kỳ lỗi được ghi
FAILED rồi task báo lỗi để thấy trên Airflow UI; lượt sau thử lại đến giới hạn số lần. Pool chặn hai job Spark (ingest,
quality) hoặc hai lệnh dbt chạy cùng lúc trong container scheduler và Thrift Server.
"""
from datetime import datetime, timedelta, timezone

from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.sdk import dag, get_current_context, task

from ingestion.control import LAYERS

POOL = {"ingest": "spark_local", "quality": "spark_local", "raw_vault": "dbt", "business_vault": "dbt"}
BUDGET = timedelta(minutes=50)


def make_layer_dag(layer: str, next_layer: str | None):
    @dag(dag_id=f"layer_{layer}", schedule="*/5 * * * *", start_date=datetime(2026, 10, 1, tzinfo=timezone.utc),
         catchup=False, max_active_runs=1, tags=["lakehouse", "layer"],
         doc_md=f"Tầng **{layer}**: xử lý các kỳ sẵn sàng theo bảng điều khiển `control.layer_run`.")
    def layer_dag():
        @task(pool=POOL[layer])
        def process() -> int:
            from ingestion import control, layers
            from ingestion.config import Config

            cfg = Config()
            run_id = get_current_context()["dag_run"].run_id
            deadline = datetime.now(timezone.utc) + BUDGET
            processed = 0
            while datetime.now(timezone.utc) < deadline:
                claimed = control.claim(cfg, layer, run_id)
                if claimed is None:
                    break
                row_id, request = claimed
                print(f"Tầng {layer}: xử lý kỳ {request.period} (force={request.force})")
                try:
                    counts = layers.run(layer, request.period, request.options)
                except Exception as exc:
                    control.finish(row_id, "FAILED", error=str(exc)[-4000:])
                    raise
                control.finish(row_id, "SUCCESS", counts=counts)
                processed += 1
            return processed

        processed = process()
        if next_layer:
            @task.short_circuit
            def did_work(n: int) -> bool:
                return n > 0

            did_work(processed) >> TriggerDagRunOperator(task_id="nudge_next", trigger_dag_id=f"layer_{next_layer}")

    return layer_dag()


for i, name in enumerate(LAYERS):
    make_layer_dag(name, LAYERS[i + 1] if i + 1 < len(LAYERS) else None)
