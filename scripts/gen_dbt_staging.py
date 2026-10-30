"""Sinh từ conf/schema (FR-03) các file dbt sau:

- dbt/models/staging/base_orig.sql, base_perf.sql: ép kiểu theo `type`; chuỗi rỗng thành null (điều chỉnh kỹ thuật).
  Không diễn giải mã thiếu (9999, 999, XX...): đó là soft rule, Raw Vault giữ giá trị như nguồn giao (DV-02, R-35).
- dbt/macros/missing_codes.sql: macro missing_to_null(cột, biểu thức) cho Business Vault và Gold diễn giải mã thiếu.
- dbt/models/business_vault/quality_violation.sql: báo cáo vi phạm soft rule (domain, values, pattern, nullable của
  conf/schema; perf không có orig) trên dữ liệu Raw Vault, ở Business Vault theo DV-02 (R-35).

Sinh từ conf thay vì viết tay để đổi tên hay thêm cột chỉ cần sửa conf/schema; tests/unit/test_dbt_staging.py kiểm file
sinh ra luôn khớp conf. View không lọc theo kỳ: bộ lọc nằm ở bảng stg_*, vì trong view nó bị đóng băng (R-31).

Chạy: uv run python -m scripts.gen_dbt_staging
"""
from pathlib import Path

from ingestion.config import Config, SourceSchema

ROOT = Path(__file__).resolve().parent.parent
SQL_TYPES = {"int": "INT", "decimal": "DECIMAL(20, 4)", "string": "STRING", "yyyymm": "STRING"}
# Cột kỹ thuật của Bronze đi kèm mỗi dòng (ingestion/bronze.py)
TECHNICAL = ["load_date", "record_source", "source_file", "period"]


def column_sql(name: str, sql_type: str) -> str:
    value = f"NULLIF(TRIM({name}), '')"
    return f"CAST({value} AS {sql_type}) AS {name}" if sql_type != "STRING" else f"{value} AS {name}"


def render(schema: SourceSchema) -> str:
    cols = [column_sql(c.name, SQL_TYPES[c.type]) for c in schema.columns]
    select = ",\n    ".join(cols + TECHNICAL)
    return (
        f"-- Sinh tự động bằng scripts/gen_dbt_staging.py từ conf/schema/{schema.kind}.yml, đừng sửa tay.\n"
        f"-- Ép kiểu, chuỗi rỗng thành null; giữ nguyên mã thiếu (DV-02). Đã qua cổng chất lượng nên ép kiểu không lỗi.\n"
        f"SELECT\n    {select}\n"
        f"FROM {{{{ source('quality', '{schema.kind}_clean') }}}}\n"
    )


def render_missing_macro(cfg: Config) -> str:
    codes = {c.name: [str(m) for m in c.spec["missing"]]
             for schema in (cfg.orig, cfg.perf) for c in schema.columns if c.spec.get("missing")}
    cases = "\n".join(
        f"  {{%- {'if' if i == 0 else 'elif'} column == '{name}' -%}}{{%- set codes = {values!r} -%}}"
        for i, (name, values) in enumerate(sorted(codes.items())))
    return (
        "{# Sinh tự động bằng scripts/gen_dbt_staging.py từ conf/schema, đừng sửa tay.\n"
        "   Diễn giải mã thiếu (soft rule) ở Business Vault và Gold; Raw Vault giữ giá trị như nguồn giao (DV-02, R-35). #}\n"
        "{% macro missing_to_null(column, expression) -%}\n"
        f"{cases}\n"
        "  {%- else -%}{%- set codes = [] -%}\n"
        "  {%- endif -%}\n"
        "  {%- if codes -%}CASE WHEN CAST({{ expression }} AS STRING) IN ({% for c in codes %}'{{ c }}'{{ ', ' if not loop.last }}{% endfor %})"
        " THEN NULL ELSE {{ expression }} END{%- else -%}{{ expression }}{%- endif -%}\n"
        "{%- endmacro %}\n"
    )


ZERO_KEY = "'" + "0" * 64 + "'"


def _sql_str(value: str) -> str:
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"


def soft_checks(column) -> list[tuple[str, str]]:
    """Điều kiện vi phạm soft rule của một cột trong Satellite (đã ép kiểu, mã thiếu giữ nguyên)."""
    c, spec = column.name, column.spec
    as_text = f"CAST({c} AS STRING)"
    missing = ", ".join(_sql_str(m) for m in spec.get("missing", []))
    present = f"{c} IS NOT NULL" + (f" AND {as_text} NOT IN ({missing})" if missing else "")
    checks = []
    if not spec.get("nullable"):
        checks.append(("ngoai_mien", f"{c} IS NULL"))
    if "domain" in spec:
        lo, hi = spec["domain"]
        bounds = [f"{c} < {lo}"] * (lo is not None) + [f"{c} > {hi}"] * (hi is not None)
        checks.append(("ngoai_mien", f"{present} AND ({' OR '.join(bounds)})"))
    if "values" in spec:
        values = ", ".join(_sql_str(v) for v in spec["values"])
        checks.append(("ngoai_mien", f"{present} AND {as_text} NOT IN ({values})"))
    if "pattern" in spec:
        checks.append(("ngoai_mien", f"{present} AND NOT ({as_text} RLIKE {_sql_str(spec['pattern'])})"))
    return checks


def render_quality_view(cfg: Config) -> str:
    by_sat: dict[str, list] = {}
    for schema in (cfg.orig, cfg.perf):
        for c in schema.columns:
            target = c.spec.get("target")
            if isinstance(target, str) and target.startswith("sat_") and not c.role:
                by_sat.setdefault(target, []).append(c)
    blocks = []
    for sat, columns in sorted(by_sat.items()):
        entries = ",\n".join(
            f"            IF({cond}, named_struct('rule', '{rule}', 'column_name', '{c.name}', "
            f"'value', CAST({c.name} AS STRING)), NULL)"
            for c in columns for rule, cond in soft_checks(c))
        blocks.append(
            f"    SELECT LOAN_HK, load_date, '{sat}' AS satellite, v\n"
            f"    FROM {{{{ ref('{sat}') }}}}\n"
            f"    LATERAL VIEW explode(filter(array(\n{entries}\n        ), e -> e IS NOT NULL)) checks AS v\n"
            f"    WHERE LOAN_HK <> {ZERO_KEY}")
    blocks.append(
        "    -- Perf không có orig: khoản vay xuất hiện ở nguồn perf mà chưa có phiên bản khởi tạo (không tính ghost record)\n"
        "    SELECT x.LOAN_HK, MIN(x.load_date) AS load_date, 'xts_loan' AS satellite,\n"
        "           named_struct('rule', 'mo_coi', 'column_name', 'loan_id', 'value', CAST(NULL AS STRING)) AS v\n"
        "    FROM {{ ref('xts_loan') }} AS x\n"
        "    WHERE x.SATELLITE_NAME = 'perf'\n"
        "      AND NOT EXISTS (SELECT 1 FROM {{ ref('sat_loan_origination') }} AS o WHERE o.LOAN_HK = x.LOAN_HK)\n"
        "    GROUP BY x.LOAN_HK")
    union = "\n    UNION ALL\n".join(blocks)
    return (
        "{# Sinh tự động bằng scripts/gen_dbt_staging.py từ conf/schema, đừng sửa tay.\n"
        "   Quality layer của Business Vault (DV-02, DV-12, R-35): mỗi vi phạm soft rule của một phiên bản Satellite là một\n"
        "   dòng. Soft rule không chặn dữ liệu: Raw Vault giữ mọi dòng qua hard rule. Mã thiếu không phải vi phạm.\n"
        "   View (Business Vault ảo): chỉ đọc Raw Vault, không lưu, không model incremental nào tham chiếu (SP-03). #}\n"
        "{{ config(materialized='view') }}\n\n"
        f"WITH violations AS (\n{union}\n)\n\n"
        "SELECT LOAN_HK, load_date, satellite, v.rule AS rule, v.column_name AS column_name, v.value AS value,\n"
        "       'business_vault.quality_violation' AS record_source\n"
        "FROM violations\n"
    )


def outputs(cfg: Config | None = None) -> dict[Path, str]:
    cfg = cfg or Config()
    files = {ROOT / f"dbt/models/staging/base_{s.kind}.sql": render(s) for s in (cfg.orig, cfg.perf)}
    files[ROOT / "dbt/macros/missing_codes.sql"] = render_missing_macro(cfg)
    files[ROOT / "dbt/models/business_vault/quality_violation.sql"] = render_quality_view(cfg)
    return files


def main() -> None:
    for path, sql in outputs().items():
        path.write_text(sql)
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
