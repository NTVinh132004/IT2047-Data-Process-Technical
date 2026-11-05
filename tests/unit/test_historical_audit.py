"""Đối soát phải phát hiện mất dòng và thiếu kỳ, chấp nhận dedup có ghi nhận."""
from scripts.audit_historical_bronze import differences, quarter


def test_source_months_map_to_quarter_boundaries():
    assert quarter(b'201903') == '2019Q1'
    assert quarter('201904') == '2019Q2'
    assert quarter('202603') == '2026Q1'


def test_conservation_includes_quarantine_and_duplicates():
    expected = {'orig': {'2019Q1': 10}, 'perf': {'2019Q1': 20}}
    quality = {'orig_clean': {'2019Q1': 8}, 'orig_quarantine': {'2019Q1': 1},
               'orig_dedup': {'2019Q1': 1}, 'perf_clean': {'2019Q1': 17},
               'perf_quarantine': {'2019Q1': 2}, 'perf_dedup': {'2019Q1': 1}}
    assert differences(expected, expected, quality) == []
    quality['perf_clean']['2019Q1'] = 16
    assert differences(expected, expected, quality) == [
        {'kind': 'perf', 'period': '2019Q1', 'source': 20, 'bronze': 20, 'classified': 19}]


def test_missing_bronze_period_is_reported():
    expected = {'orig': {}, 'perf': {'2026Q1': 3}}
    bronze = {'orig': {}, 'perf': {}}
    quality = {f'{kind}_{suffix}': {} for kind in ('orig', 'perf')
               for suffix in ('clean', 'quarantine', 'dedup')}
    assert differences(expected, bronze, quality) == [
        {'kind': 'perf', 'period': '2026Q1', 'source': 3, 'bronze': 0, 'classified': 0}]
