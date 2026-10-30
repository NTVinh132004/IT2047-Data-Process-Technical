"""Kỳ nạp và load_date (PRD mục 6).

Một kỳ nạp là một quý báo cáo, ví dụ "2020Q1". Tháng báo cáo của Freddie Mac
có dạng "YYYYMM". Mỗi tháng báo cáo trong kỳ mang một load_date riêng, để khóa
Satellite (hash_key, load_date) không bị trùng khi một kỳ chứa ba tháng (R-01).
"""
from datetime import date


def months_in_period(period: str) -> list[str]:
    """'2020Q1' -> ['202001', '202002', '202003']."""
    year, quarter = period.split("Q")
    first = (int(quarter) - 1) * 3 + 1
    return [f"{year}{m:02d}" for m in range(first, first + 3)]


def periods_between(first: str, last: str) -> list[str]:
    """'2019Q3', '2020Q2' -> ['2019Q3', '2019Q4', '2020Q1', '2020Q2']."""
    def index(period: str) -> int:
        year, quarter = period.split("Q")
        return int(year) * 4 + int(quarter) - 1

    return [f"{i // 4}Q{i % 4 + 1}" for i in range(index(first), index(last) + 1)]


def period_of(reporting_period: str) -> str:
    """'202002' -> '2020Q1'."""
    year, month = reporting_period[:4], int(reporting_period[4:])
    return f"{year}Q{(month - 1) // 3 + 1}"


def load_date_for(reporting_period: str, lag_months: int = 1) -> date:
    """load_date giả lập của tháng báo cáo: ngày 1 của tháng (reporting_period + lag_months).

    Ví dụ: '202003', lag 1 -> date(2020, 4, 1); '201912', lag 1 -> date(2020, 1, 1).
    """
    year, month = int(reporting_period[:4]), int(reporting_period[4:])
    if not 1 <= month <= 12:
        raise ValueError(f"Tháng báo cáo không hợp lệ: {reporting_period!r}")
    index = year * 12 + (month - 1) + lag_months
    return date(index // 12, index % 12 + 1, 1)
