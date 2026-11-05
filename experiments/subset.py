"""Tập con của bộ sample theo khoản vay cho thực nghiệm mở rộng quy mô TN1 (R-38).

Khoản vay thuộc tập con khi byte đầu SHA-256 của mã khoản vay < ngưỡng: p25 ⊂ p50 ⊂ p100, chọn tất định, không
phụ thuộc thứ tự dòng. Giữ trọn orig và mọi tháng perf của khoản vay được chọn, nên mọi quy tắc cắt kỳ vẫn đúng.
Kết quả ghi vào data/raw-exp/<tập>/sample_2019/ (không commit, EP-08).

Chạy: uv run python -m experiments.subset
"""
import hashlib
import json
from pathlib import Path

from ingestion.config import Config

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/sample_2019"
TARGET = ROOT / "data/raw-exp"
FRACTIONS = {"p25": 64, "p50": 128}  # ngưỡng trên byte đầu (0–255)


def bucket(loan_id: str) -> int:
    return hashlib.sha256(loan_id.encode()).digest()[0]


def key_position(kind: str) -> int:
    schema = getattr(Config(ROOT / "conf"), kind)
    return next(c.pos for c in schema.columns if c.role == "loan_key") - 1


def build() -> dict:
    keys = {kind: key_position(kind) for kind in ("orig", "perf")}
    summary = {}
    for name, threshold in FRACTIONS.items():
        out = TARGET / name / "sample_2019"
        out.mkdir(parents=True, exist_ok=True)
        counts = {}
        for kind, pos in keys.items():
            source = SOURCE / f"sample_{kind}_2019.txt"
            lines = loans = 0
            seen = set()
            with source.open("rb") as src, (out / source.name).open("wb") as dst:
                for line in src:
                    loan = line.split(b"|", pos + 1)[pos].decode()
                    if bucket(loan) < threshold:
                        dst.write(line)
                        lines += 1
                        seen.add(loan)
            counts[kind] = {"lines": lines, "loans": len(seen)}
        summary[name] = counts
    (TARGET / "subsets.json").write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
