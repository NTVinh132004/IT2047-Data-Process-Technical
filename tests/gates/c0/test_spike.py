"""Cổng C0, phần spike (Kế hoạch mục 6): dbt-spark + automate-dv nạp hub_loan và sat_loan_balance 2 tháng.

Chạy experiments/spike_c0/run_spike.sh, cần `docker compose up -d` trong experiments/spike_c0.
Phần còn lại của C0 (từ điển dữ liệu, điều kiện chốt) do review tài liệu, không tự động.
"""
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPIKE = ROOT / "experiments/spike_c0"
RESULTS = ROOT / "tests/gates/results"


@pytest.fixture(scope="module")
def spike():
    if shutil.which("docker") is None:
        pytest.fail("Cần Docker để chạy spike C0")
    run = subprocess.run(["bash", str(SPIKE / "run_spike.sh")], capture_output=True, text=True, timeout=1800)
    results_file = SPIKE / "results.json"
    if not results_file.exists():
        pytest.fail(f"run_spike.sh không sinh results.json:\n{run.stdout[-2000:]}\n{run.stderr[-2000:]}")
    results = json.loads(results_file.read_text())
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    record = {"gate": "C0", "commit": commit or "chua-commit", "ran_at": datetime.now().isoformat(timespec="seconds"), **results}
    (RESULTS / f"c0-{datetime.now():%Y%m%d-%H%M%S}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2))
    return results


@pytest.mark.parametrize("check", [
    "R-01: Satellite = số dòng perf 2 tháng",
    "R-01: không trùng (hash_key, load_date)",
    "Hub: mỗi khoản vay một dòng",
    "R-08: chạy lại 201904 sau 201905 sinh 0 dòng (nạp 2 tháng một lần)",
    "Nạp từng tháng cho cùng kết quả",
    "R-08: chạy lại 201904 sau 201905 sinh 0 dòng (nạp từng tháng)",
])
def test_spike(spike, check):
    assert spike["checks"][check], json.dumps(spike["counts"], ensure_ascii=False)
