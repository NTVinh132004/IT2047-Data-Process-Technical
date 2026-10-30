"""Đối chứng FR-16 bằng Python/Decimal trực tiếp TXT, không dùng SQL/model pipeline."""
from collections import Counter, defaultdict
from decimal import Decimal
from glob import glob

from ingestion.config import Config
from tests.gates.c1.test_c1 import host_path


def rows(cfg, kind):
    schema = getattr(cfg, kind)
    for path in sorted(glob(str(host_path(cfg.raw_files(schema))))):
        with open(path) as stream:
            for line in stream:
                fields = line.rstrip('\n').split('|')
                yield {c.name: fields[c.pos - 1].strip() for c in schema.columns}


def month_index(value):
    return int(value[:4]) * 12 + int(value[4:6]) - 1


def compute(cfg):
    maturity = {r['loan_id']: r['maturity_date'] for r in rows(cfg, 'orig')}
    monthly = defaultdict(lambda: defaultdict(lambda: Decimal(0)))
    states = {}
    for r in rows(cfg, 'perf'):
        loan, month = r['loan_id'], r['reporting_period']
        index = month_index(month)
        s = states.setdefault(loan, {'last_month': -1, 'last_f': None, 'covid': False, 'ever_default': False,
                                    'default': False, 'prepaid': False, 'modified': False, 'final': None})
        assert index > s['last_month'], 'Oracle yêu cầu TXT theo tháng tăng dần cho mỗi khoản vay'
        s['last_month'] = index
        code, status = r['zero_balance_code'], r['delinquency_status']
        forbearance = r['borrower_assistance_plan'] == 'F'
        default = code in ('02', '03', '09') or status == 'RA' or (status.isdigit() and int(status) >= 6 and not forbearance)
        first_default = default and not s['ever_default']
        s['ever_default'] |= default
        prepaid = code == '01' and bool(r['zero_balance_date']) and r['zero_balance_date'] < maturity.get(loan, '')
        m = monthly[month]
        upb = Decimal(r['current_upb'] or '0')
        m['loan_count'] += 1
        m['total_upb'] += upb
        if not code:
            m['active_upb'] += upb
            if status != 'XX' and status:
                m['eligible_count'] += 1
                m['eligible_upb'] += upb
                bucket = 'd30' if status == '01' else 'd60' if status == '02' else 'd90_plus' if status == 'RA' or (status.isdigit() and int(status) >= 3) else None
                if bucket:
                    m[bucket+'_count'] += 1
                    m[bucket+'_upb'] += upb
        if prepaid:
            m['prepaid_count'] += 1
            m['prepaid_upb'] += Decimal(r['zero_balance_removal_upb'] or '0')
        if forbearance:
            s['last_f'] = index
            s.update(default=False, prepaid=False, modified=False, final=None)
            s['covid'] |= '202003' <= month <= '202112'
        elif s['last_f'] is not None and 0 < index - s['last_f'] <= 12:
            s['default'] |= first_default
            s['prepaid'] |= prepaid
            s['modified'] |= r['modification_flag'] == 'Y'
            if index - s['last_f'] == 12:
                s['final'] = status if status != 'XX' else None
    outcomes = Counter()
    for s in states.values():
        if s['covid']:
            result = ('DEFAULTED' if s['default'] else 'PREPAID' if s['prepaid'] else 'MODIFIED' if s['modified']
                      else 'RECOVERED' if s['final'] == '00' else 'UNKNOWN' if s['final'] is None else 'DELINQUENT')
            outcomes[result] += 1
    return monthly, outcomes
