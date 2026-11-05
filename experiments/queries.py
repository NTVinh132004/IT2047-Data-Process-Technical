"""SQL của TN4 và phép đếm độ phức tạp, tách khỏi PySpark để kiểm bằng unit test (R-38)."""
import re


def plan_stats(plan: str) -> dict:
    """Đếm nút của physical plan (phần trước mục chi tiết của explain formatted)."""
    tree = plan.split("\n\n(1)")[0]
    nodes = {"exchange": r"Exchange", "sort_merge_join": r"SortMergeJoin", "broadcast_hash_join": r"BroadcastHashJoin",
             "window": r"\bWindow\b", "scan": r"Scan "}
    return {k: len(re.findall(p, tree)) for k, p in nodes.items()}


def sql_stats(sql: str) -> dict:
    lines = [line for line in sql.splitlines() if line.strip()]
    return {"sql_lines": len(lines), "sql_joins": len(re.findall(r"\bJOIN\b", sql, re.I))}


SATS = [  # (Satellite, cột payload lấy ra, cột con trỏ trong PIT)
    ("raw_vault.sat_loan_balance", "current_upb", "SAT_LOAN_BALANCE"),
    ("raw_vault.sat_loan_delinquency", "delinquency_status", "SAT_LOAN_DELINQUENCY"),
    ("raw_vault.sat_loan_termination", "zero_balance_code", "SAT_LOAN_TERMINATION"),
    ("raw_vault.sat_loan_origination", "credit_score", "SAT_LOAN_ORIGINATION"),
]
SCENARIOS = {"all_months": None, "one_month": "2020-07-01"}  # một mốc: tháng báo cáo 06/2020 (COVID)


def pit_query(as_of: str | None) -> str:
    joins = "\n".join(
        f"JOIN {sat} AS s{i} ON s{i}.LOAN_HK = p.{ptr}_PK AND s{i}.load_date = p.{ptr}_LDTS"
        for i, (sat, _, ptr) in enumerate(SATS))
    where = f"WHERE p.AS_OF_DATE = DATE'{as_of}'" if as_of else ""
    columns = ", ".join(f"s{i}.{col}" for i, (_, col, _) in enumerate(SATS))
    return f"""SELECT p.LOAN_HK, p.AS_OF_DATE, {columns}
FROM business_vault.pit_loan_monthly AS p
{joins}
{where}"""


def direct_query(as_of: str | None) -> str:
    """Không có PIT: với mỗi (khoản vay, mốc) tìm phiên bản có load_date lớn nhất không vượt mốc ở từng Satellite.
    Lưới (khoản vay, mốc) lấy từ record tracking satellite, giống lưới của PIT."""
    where = f"WHERE load_date = DATE'{as_of}'" if as_of else ""
    ctes = [f"grid AS (SELECT DISTINCT LOAN_HK, load_date AS AS_OF_DATE FROM raw_vault.xts_loan {where})"]
    for i, (sat, col, _) in enumerate(SATS):
        ctes.append(f"""v{i} AS (
    SELECT LOAN_HK, AS_OF_DATE, {col} FROM (
        SELECT g.LOAN_HK, g.AS_OF_DATE, s.{col},
               ROW_NUMBER() OVER (PARTITION BY g.LOAN_HK, g.AS_OF_DATE ORDER BY s.load_date DESC) AS rn
        FROM grid AS g
        JOIN {sat} AS s ON s.LOAN_HK = g.LOAN_HK AND s.load_date <= g.AS_OF_DATE
    ) AS ranked WHERE rn = 1)""")
    joins = "\n".join(f"LEFT JOIN v{i} ON v{i}.LOAN_HK = g.LOAN_HK AND v{i}.AS_OF_DATE = g.AS_OF_DATE"
                      for i in range(len(SATS)))
    columns = ", ".join(f"v{i}.{col}" for i, (_, col, _) in enumerate(SATS))
    return "WITH " + ",\n".join(ctes) + f"\nSELECT g.LOAN_HK, g.AS_OF_DATE, {columns}\nFROM grid AS g\n{joins}"
