"""Unit test cho phần thuần Python của thực nghiệm C5 (R-38): tập con lồng nhau, SQL TN4, đếm plan."""
from experiments.queries import SATS, direct_query, pit_query, plan_stats, sql_stats
from experiments.subset import FRACTIONS, bucket


def test_subsets_are_nested_and_deterministic():
    loans = [f"F19Q299{i:05d}" for i in range(2000)]  # mã giả lập như tests/fixtures
    p25 = {loan for loan in loans if bucket(loan) < FRACTIONS["p25"]}
    p50 = {loan for loan in loans if bucket(loan) < FRACTIONS["p50"]}
    assert p25 < p50 < set(loans)
    assert 0.2 < len(p25) / len(loans) < 0.3 and 0.45 < len(p50) / len(loans) < 0.55
    assert bucket("F19Q29900001") == bucket("F19Q29900001")


def test_pit_query_uses_only_equi_joins():
    sql = pit_query(None)
    assert sql_stats(sql)["sql_joins"] == len(SATS)
    assert "<=" not in sql and "ROW_NUMBER" not in sql
    assert "AS_OF_DATE = DATE'2020-07-01'" in pit_query("2020-07-01")


def test_direct_query_finds_latest_version_not_after_snapshot():
    sql = direct_query("2020-07-01")
    assert sql.count("s.load_date <= g.AS_OF_DATE") == len(SATS)
    assert sql.count("ORDER BY s.load_date DESC") == len(SATS) and sql.count("rn = 1") == len(SATS)
    assert "load_date = DATE'2020-07-01'" in sql


def test_plan_stats_counts_only_the_tree():
    plan = ("== Physical Plan ==\n* HashAggregate (5)\n+- Exchange (4)\n   +- * SortMergeJoin Inner (3)\n"
            "      :- * Scan parquet a (1)\n      +- Window (2)\n\n\n(1) Scan parquet a\nExchange details")
    assert plan_stats(plan) == {"exchange": 1, "sort_merge_join": 1, "broadcast_hash_join": 0, "window": 1, "scan": 1}
