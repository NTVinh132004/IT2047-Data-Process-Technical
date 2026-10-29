"""Sinh dbt/macros/automate_dv_spark_shim.sql: spark__X gọi automate_dv.databricks__X.

automate_dv chỉ có macro databricks__*, còn adapter dbt-spark dispatch tới spark__* rồi default__*
(SQL kiểu Snowflake). Macro dùng QUALIFY được viết tay trong dbt/macros/spark_vault.sql nên bỏ qua ở đây.
Chạy lại sau mỗi lần đổi phiên bản automate_dv: python3 gen_shim.py
"""
import re
from pathlib import Path

DBT = Path(__file__).parent / "dbt"
HANDWRITTEN = {"hub", "sat"}

sigs = set()
for f in (DBT / "dbt_packages/automate_dv/macros").rglob("*.sql"):
    sigs |= set(re.findall(r"macro (databricks__([a-z0-9_]+))\(([^)]*)\)", f.read_text()))

out = ["{# Sinh tự động bằng experiments/spike_c0/gen_shim.py, đừng sửa tay. #}"]
for full, name, params in sorted(sigs, key=lambda s: s[1]):
    if name in HANDWRITTEN:
        continue
    call = ", ".join(f"{n}={n}" for n in (p.split("=")[0].strip() for p in params.split(",")) if n)
    out.append(f"\n{{% macro spark__{name}({params}) %}}\n  {{{{ return(automate_dv.{full}({call})) }}}}\n{{% endmacro %}}")
(DBT / "macros/automate_dv_spark_shim.sql").write_text("\n".join(out) + "\n")
print(f"{len(sigs) - len(HANDWRITTEN)} macro shim")
