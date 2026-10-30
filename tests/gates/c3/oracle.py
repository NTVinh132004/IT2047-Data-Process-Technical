"""Tính độc lập các chỉ số Business Vault (FR-12) từ file TXT gốc, bằng Python thuần.

Cài lại định nghĩa ở docs/tu-dien-du-lieu.md mục 4 mà không dùng chung code với dbt, để cổng C3 so hai cách tính.
Đọc file perf và orig của bộ dữ liệu đang chọn trong conf/pipeline.yml (đường dẫn trên máy, không qua Spark).
"""
from collections import defaultdict
from dataclasses import dataclass
from glob import glob
from pathlib import Path

from ingestion.config import Config
from ingestion.periods import load_date_for

ROOT = Path(__file__).resolve().parents[3]


@dataclass
class MonthState:
    reporting_period: str
    delinquency_bucket: str
    months_delinquent_consecutive: int
    ever_d90: bool
    default_reporting_period: str | None
    lifecycle_status: str
    in_forbearance: bool


def _host(path: str) -> list[str]:
    return sorted(glob(str(ROOT / "data/raw" / Path(path).relative_to("/data/raw"))))


def _bucket(status: str | None) -> str:
    if status is None:
        return "NA"
    return {"00": "CURRENT", "01": "D30", "02": "D60"}.get(status, "D90_PLUS")


def _number(status: str | None) -> int | None:
    return int(status) if status is not None and status.isdigit() else None


def compute(cfg: Config, loan_ids: set[str] | None = None) -> dict[str, list[MonthState]]:
    """Chuỗi trạng thái theo tháng của từng khoản vay (chỉ các khoản vay trong loan_ids nếu có)."""
    pos = {c.name: c.pos - 1 for c in cfg.perf.columns}
    opos = {c.name: c.pos - 1 for c in cfg.orig.columns}
    maturity = {}
    for path in _host(cfg.raw_files(cfg.orig)):
        with open(path) as f:
            for line in f:
                r = line.rstrip("\n").split("|")
                if loan_ids is None or r[opos["loan_id"]] in loan_ids:
                    maturity[r[opos["loan_id"]]] = r[opos["maturity_date"]]

    rows = defaultdict(list)
    for path in _host(cfg.raw_files(cfg.perf)):
        with open(path) as f:
            for line in f:
                r = line.rstrip("\n").split("|")
                if loan_ids is None or r[pos["loan_id"]] in loan_ids:
                    rows[r[pos["loan_id"]]].append(r)

    result = {}
    for loan, perf in rows.items():
        perf.sort(key=lambda r: r[pos["reporting_period"]])
        consecutive, ever_d90, default_month, states = 0, False, None, []
        for r in perf:
            month = r[pos["reporting_period"]]
            status = None if r[pos["delinquency_status"]] in ("", "XX") else r[pos["delinquency_status"]]
            plan = r[pos["borrower_assistance_plan"]] or None
            zbc = r[pos["zero_balance_code"]] or None
            number = _number(status)
            delinquent = status is not None and status != "00"
            consecutive = consecutive + 1 if delinquent else 0
            ever_d90 = ever_d90 or status == "RA" or (number is not None and number >= 3)
            is_default = (number is not None and number >= 6 and plan != "F") or status == "RA" or zbc in ("02", "03", "09")
            if default_month is None and is_default:
                default_month = month
            zb_date = r[pos["zero_balance_date"]] or None
            if zbc == "96":
                life = "DEFECT"
            elif zbc in ("02", "03", "09"):
                life = "LIQUIDATED"
            elif zbc in ("15", "16"):
                life = "SOLD"
            elif zbc == "01":
                life = "PREPAID" if zb_date and zb_date < maturity.get(loan, "999999") else "MATURED"
            elif default_month is not None:
                life = "DEFAULTED"
            elif plan == "F":
                life = "FORBEARANCE"
            elif delinquent:
                life = "DELINQUENT"
            else:
                life = "CURRENT"
            states.append(MonthState(month, _bucket(status), consecutive, ever_d90, default_month, life, plan == "F"))
        result[loan] = states
    return result


def load_date_of(cfg: Config, reporting_period: str | None):
    return None if reporting_period is None else load_date_for(reporting_period, cfg.lag_months)
