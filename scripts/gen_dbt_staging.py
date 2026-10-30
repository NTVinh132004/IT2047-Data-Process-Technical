"""Sinh dbt/models/staging/base_orig.sql và base_perf.sql từ conf/schema (FR-03).

Bronze và bảng clean giữ giá trị nguồn dạng chuỗi. Model base ép kiểu theo `type` và đổi mã thiếu (`missing`) cùng
chuỗi rỗng thành null, đúng quy tắc ở docs/tu-dien-du-lieu.md mục 5. Sinh từ conf thay vì viết tay để đổi tên hay
thêm cột chỉ cần sửa conf/schema; tests/unit/test_dbt_staging.py kiểm file sinh ra luôn khớp conf.
View không lọc theo kỳ: bộ lọc var('period') nằm ở bảng stg_*, vì trong view nó bị đóng băng lúc tạo view (R-31).

Chạy: uv run python -m scripts.gen_dbt_staging
"""
from pathlib import Path

from ingestion.config import Config, SourceSchema

ROOT = Path(__file__).resolve().parent.parent
SQL_TYPES = {"int": "INT", "decimal": "DECIMAL(20, 4)", "string": "STRING", "yyyymm": "STRING"}
# Cột kỹ thuật của Bronze đi kèm mỗi dòng (ingestion/bronze.py)
TECHNICAL = ["load_date", "record_source", "source_file", "period"]


def column_sql(name: str, sql_type: str, missing: list[str]) -> str:
    empty = [""] + [str(m) for m in missing]
    codes = ", ".join(f"'{m}'" for m in empty)
    value = f"CASE WHEN TRIM({name}) IN ({codes}) THEN NULL ELSE TRIM({name}) END"
    return f"CAST({value} AS {sql_type}) AS {name}" if sql_type != "STRING" else f"{value} AS {name}"


def render(schema: SourceSchema) -> str:
    cols = [column_sql(c.name, SQL_TYPES[c.type], c.spec.get("missing", [])) for c in schema.columns]
    select = ",\n    ".join(cols + TECHNICAL)
    return (
        f"-- Sinh tự động bằng scripts/gen_dbt_staging.py từ conf/schema/{schema.kind}.yml, đừng sửa tay.\n"
        f"-- Ép kiểu và đổi mã thiếu thành null; giá trị đã qua cổng chất lượng nên ép kiểu không lỗi.\n"
        f"SELECT\n    {select}\n"
        f"FROM {{{{ source('quality', '{schema.kind}_clean') }}}}\n"
    )


def outputs(cfg: Config | None = None) -> dict[Path, str]:
    cfg = cfg or Config()
    return {ROOT / f"dbt/models/staging/base_{s.kind}.sql": render(s) for s in (cfg.orig, cfg.perf)}


def main() -> None:
    for path, sql in outputs().items():
        path.write_text(sql)
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
