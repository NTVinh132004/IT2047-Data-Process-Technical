from decimal import Decimal
import pytest
from scripts.collect_sample_report import validate_monthly


def test_monthly_reconciliation_checks_decimal_and_missing_month():
    counts={'202001':2};upb={'202001':Decimal('123.4500')}
    good=[{'reporting_date':'2020-01-01','loan_count':2,'total_upb':'123.45'}]
    validate_monthly(counts,upb,good)
    with pytest.raises(RuntimeError,match='Số dòng hoặc dư nợ'):
        validate_monthly(counts,upb,[dict(good[0],total_upb='123.46')])
    with pytest.raises(RuntimeError,match='Số dòng hoặc dư nợ'):
        validate_monthly(counts,upb,[dict(good[0],loan_count=1)])
    with pytest.raises(RuntimeError,match='Thiếu hoặc thừa tháng'):
        validate_monthly(counts,upb,[])
