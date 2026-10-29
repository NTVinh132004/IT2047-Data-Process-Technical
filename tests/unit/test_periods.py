from datetime import date

import pytest

from ingestion.periods import load_date_for, months_in_period, period_of


def test_months_in_period():
    assert months_in_period("2020Q1") == ["202001", "202002", "202003"]
    assert months_in_period("2019Q4") == ["201910", "201911", "201912"]


def test_period_of():
    assert period_of("202002") == "2020Q1"
    assert period_of("201912") == "2019Q4"


@pytest.mark.parametrize(
    "reporting_period, lag, expected",
    [
        ("202003", 1, date(2020, 4, 1)),
        ("201912", 1, date(2020, 1, 1)),   # sang năm mới
        ("202011", 2, date(2021, 1, 1)),   # lag > 1 vẫn sang năm đúng
        ("202005", 0, date(2020, 5, 1)),
    ],
)
def test_load_date_for(reporting_period, lag, expected):
    assert load_date_for(reporting_period, lag) == expected


def test_load_date_unique_per_month_in_period():
    # Ba tháng của một kỳ phải có ba load_date khác nhau (R-01)
    dates = {load_date_for(m) for m in months_in_period("2020Q1")}
    assert len(dates) == 3
