"""Cổng C0, phần spike (Kế hoạch mục 6): dbt-spark + automate-dv nạp hub_loan và sat_loan_balance 2 tháng.

Test tự bật container của spike (experiments/spike_c0), chạy run_spike.sh rồi tắt container để trả RAM.
Phần còn lại của C0 (từ điển dữ liệu, điều kiện chốt) do review tài liệu, không tự động.
"""
import json

import pytest

from tests.gates.conftest import ROOT, save_gate_result, sh

SPIKE = ROOT / "experiments/spike_c0"

CHECKS = [
    "R-01: Satellite = số dòng perf 2 tháng",
    "R-01: không trùng (hash_key, load_date)",
    "Hub: mỗi khoản vay một dòng",
    "R-08: chạy lại 201904 sau 201905 sinh 0 dòng (nạp 2 tháng một lần)",
    "Nạp từng tháng cho cùng kết quả",
    "R-08: chạy lại 201904 sau 201905 sinh 0 dòng (nạp từng tháng)",
]


@pytest.fixture(scope="module")
def spike():
    # Không ép --build: compose tự build khi chưa có image; ép build làm test phụ thuộc mạng tới Docker Hub
    sh("docker", "compose", "up", "-d", cwd=SPIKE)
    try:
        sh("bash", str(SPIKE / "run_spike.sh"), check=False, timeout=1800)
    finally:
        sh("docker", "compose", "down", cwd=SPIKE, check=False)
    results_file = SPIKE / "results.json"
    if not results_file.exists():
        pytest.fail("run_spike.sh không sinh results.json")
    results = json.loads(results_file.read_text())
    save_gate_result("C0", results)
    return results


@pytest.mark.parametrize("check", CHECKS)
def test_spike(spike, check):
    assert spike["checks"][check], json.dumps(spike["counts"], ensure_ascii=False)
