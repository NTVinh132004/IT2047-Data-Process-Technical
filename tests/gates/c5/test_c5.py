"""Cổng C5 trên bộ mẫu (Kế hoạch mục 6, R-38): kiểm kết quả thô của 5 thực nghiệm, không chạy lại thực nghiệm.

Thực nghiệm chạy bằng `make experiments` (khoảng 4–5 giờ, stack riêng). Cổng này đọc experiments/results/*.csv và
kiểm: đủ 3 lần đo mỗi cấu hình sau lần khởi động, phép kiểm đúng đi kèm từng thực nghiệm đạt, có biểu đồ và plan,
và kết quả được đo trên đúng code hiện tại (digest).
"""
import csv
import json
from collections import Counter, defaultdict
from statistics import median

import pytest

from experiments.run import RESULTS, TN2_CHECKPOINTS, code_digest
from tests.gates.conftest import save_gate_result

REPS = 3
STEPS = ("tn1", "tn2", "tn4", "tn6", "tn7")
RESULT: dict = {}


def rows(name: str) -> list[dict]:
    path = RESULTS / f"{name}.csv"
    assert path.exists(), f"Thiếu {path}; chạy make experiments"
    with path.open() as f:
        return list(csv.DictReader(f))


def measured(data: list[dict]) -> list[dict]:
    return [r for r in data if r.get("warmup") != "True"]


def runs_per_config(data: list[dict], *keys: str) -> Counter:
    return Counter(tuple(r[k] for k in keys) for r in measured(data))


@pytest.fixture(scope="module", autouse=True)
def record():
    yield
    RESULT["passed"] = all(v for k, v in RESULT.items() if k.endswith("_ok"))
    save_gate_result("C5", RESULT)


def test_results_match_current_code():
    manifest = json.loads((RESULTS / "manifest.json").read_text())
    digest = code_digest()
    stale = [s for s in STEPS if manifest.get(s, {}).get("code_digest") != digest]
    RESULT["code_digest"] = digest
    RESULT["digest_ok"] = not stale
    assert not stale, f"Kết quả {stale} đo trên code khác code hiện tại; chạy lại các thực nghiệm này"


def test_tn1_scale_runs_reconcile():
    data = rows("tn1_scale")
    counts = runs_per_config(data, "subset")
    assert set(counts) == {("p25",), ("p50",), ("p100",)} and all(n >= REPS for n in counts.values()), counts
    bad = [r for r in data if not (r["ac01"] == r["ac05"] == r["ac06"] == "True" and r["periods_complete"] == "29"
                                   and r["failed_runs"] == "0")]
    RESULT["tn1"] = {s: median(float(r["end_to_end_s"]) for r in data if r["subset"] == s) for s in ("p25", "p50", "p100")}
    RESULT["tn1_ok"] = not bad
    assert not bad, f"Lần chạy TN1 không đối soát được: {bad}"


def test_tn2_incremental_equals_full_refresh():
    data = rows("tn2_incremental")
    counts = runs_per_config(data, "method", "periods_loaded")
    expected = {(m, str(k)) for m in ("incremental", "full_refresh") for k in TN2_CHECKPOINTS}
    assert set(counts) == expected and all(n >= REPS for n in counts.values()), counts
    mismatch = [r for r in data if r["method"] == "full_refresh" and r["rows_match_incremental"] != "True"]
    RESULT["tn2_ok"] = not mismatch
    assert not mismatch, f"Full refresh khác incremental về số dòng: {mismatch}"


def test_tn4_pit_equals_direct_join():
    data = rows("tn4_pit")
    counts = runs_per_config(data, "scenario", "method")
    assert len(counts) == 4 and all(n >= REPS for n in counts.values()), counts
    by_scenario = defaultdict(set)
    for r in data:
        by_scenario[r["scenario"]].add((r["rows"], r["checksum"]))
    RESULT["tn4_ok"] = all(len(v) == 1 for v in by_scenario.values())
    assert RESULT["tn4_ok"], f"PIT và join trực tiếp ra kết quả khác nhau: {dict(by_scenario)}"
    for name in ("all_months_pit", "all_months_direct", "one_month_pit", "one_month_direct"):
        assert (RESULTS / "plans" / f"tn4_{name}.txt").exists()


def test_tn6_split_and_merged_measured():
    timing, storage = rows("tn6_split"), rows("tn6_storage")
    assert len(measured(timing)) >= REPS
    designs = {r["design"] for r in storage}
    merged = sum(int(r["rows"]) for r in storage if r["design"] == "merged")
    largest_split = max(int(r["rows"]) for r in storage if r["design"] == "split")
    # Satellite gộp có phiên bản mới mỗi khi nhóm thay đổi nhanh nhất đổi, nên không ít dòng hơn Satellite tách lớn nhất
    query = rows("tn6_query")
    same_history = len({(r["rows"], r["checksum"]) for r in query}) == 1
    RESULT["tn6_ok"] = (designs == {"split", "merged"} and merged >= largest_split and same_history
                        and all(n >= REPS for n in runs_per_config(query, "design").values()))
    assert RESULT["tn6_ok"], (designs, merged, largest_split, same_history)


def test_tn7_ingestion_techniques():
    slices = rows("tn7_bronze_slice")
    counts = runs_per_config(slices, "period", "method")
    assert len(counts) == 8 and all(n >= REPS for n in counts.values()), counts
    warm = {(r["period"], r["method"]): (r["orig_rows"], r["perf_rows"]) for r in slices if r["warmup"] == "True"}
    same_rows = all(warm[(p, "txt_direct")] == warm[(p, "landing")] for p, _ in warm)
    faults = {r["method"]: r for r in rows("tn7_reader_faults")}
    text_detects_all = faults["text_split"]["detected"] == faults["text_split"]["injected"]
    reader = runs_per_config(rows("tn7_reader"), "method")
    build = measured(rows("tn7_landing_build"))
    RESULT["tn7"] = {"csv_detected": faults["csv_reader"]["detected"], "injected": faults["text_split"]["injected"]}
    RESULT["tn7_ok"] = same_rows and text_detects_all and len(reader) == 2 and len(build) >= REPS and bool(rows("tn7_storage"))
    assert RESULT["tn7_ok"], (same_rows, text_detects_all, reader, len(build))


def test_charts_exist():
    charts = sorted(p.name for p in RESULTS.glob("*.png"))
    RESULT["charts"] = charts
    RESULT["charts_ok"] = all(any(c.startswith(s) for c in charts) for s in STEPS)
    assert RESULT["charts_ok"], f"Thiếu biểu đồ; chạy make experiment-charts. Có: {charts}"
