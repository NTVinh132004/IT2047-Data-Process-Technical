"""Tiện ích chung cho test cổng (Kế hoạch mục 6): ghi kết quả, đọc .env, chạy lệnh trong repo."""
import json
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "tests/gates/results"


def sh(*cmd: str, timeout: int = 3600, check: bool = True, cwd: Path = ROOT) -> subprocess.CompletedProcess:
    # stdin đóng: beeline (và lệnh tương tác khác) chờ stdin sẽ treo vô hạn dù đã chạy xong
    run = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd, stdin=subprocess.DEVNULL)
    if check and run.returncode != 0:
        raise AssertionError(f"Lệnh lỗi ({run.returncode}): {' '.join(cmd)}\n{run.stdout[-3000:]}\n{run.stderr[-3000:]}")
    return run


def save_gate_result(gate: str, data: dict) -> Path:
    """Lưu commit, thời điểm và kết quả của một lần chạy cổng vào tests/gates/results/."""
    commit = sh("git", "rev-parse", "--short", "HEAD", check=False).stdout.strip() or "chua-commit"
    # Bỏ qua thư mục kết quả: chính các file kết quả mới sinh ra không phải là thay đổi code
    dirty = bool(sh("git", "status", "--porcelain", "--", ".", ":(exclude)tests/gates/results", check=False).stdout.strip())
    record = {"gate": gate, "commit": commit, "uncommitted_changes": dirty,
              "ran_at": datetime.now().isoformat(timespec="seconds"), **data}
    path = RESULTS / f"{gate.lower()}-{datetime.now():%Y%m%d-%H%M%S}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2, default=str))
    return path


def dotenv() -> dict[str, str]:
    env_file = ROOT / ".env"
    if not env_file.exists():
        raise AssertionError("Thiếu .env (cp .env.example .env)")
    pairs = (line.split("=", 1) for line in env_file.read_text().splitlines() if "=" in line and not line.startswith("#"))
    return {k.strip(): v.strip() for k, v in pairs}
