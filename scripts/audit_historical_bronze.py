"""Đối soát TXT → Bronze và bảo toàn số dòng quality trên bộ full; không thay C5."""
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
from deltalake import DeltaTable

from ingestion.config import Config

ROOT = Path(__file__).resolve().parents[1]


def quarter(month):
    text = month.decode('ascii') if isinstance(month, bytes) else month
    return f'{text[:4]}Q{(int(text[4:6]) - 1) // 3 + 1}'


def snapshot_counts(path):
    table = DeltaTable(str(path))
    actions = pa.table(table.get_add_actions(flatten=True))
    counts = Counter()
    if actions.num_rows:
        data = actions.to_pydict()
        for period, n in zip(data['partition.period'], data['num_records']):
            if period is None or n is None:
                raise RuntimeError(f'Thiếu thống kê period/num_records: {path}')
            counts[period] += n
    return dict(counts), table.version()


def differences(expected, bronze, quality):
    wrong = []
    for kind in ('orig', 'perf'):
        periods = set(expected[kind]) | set(bronze[kind])
        for name in ('clean', 'quarantine', 'dedup'):
            periods.update(quality[f'{kind}_{name}'])
        for period in sorted(periods):
            source = expected[kind].get(period, 0)
            stored = bronze[kind].get(period, 0)
            classified = sum(quality[f'{kind}_{name}'].get(period, 0)
                             for name in ('clean', 'quarantine', 'dedup'))
            if source != stored or stored != classified:
                wrong.append(dict(kind=kind, period=period, source=source,
                                  bronze=stored, classified=classified))
    return wrong


def main():
    report_dir = ROOT / 'data/reports/historical'
    manifest = json.loads((report_dir / 'source-manifest.json').read_text())
    if not manifest['passed']:
        raise RuntimeError('Preflight nguồn chưa đạt')
    raw = ROOT / 'data/raw/historical_2019'
    known = {entry['name']: entry for entry in manifest['files']}
    actual = {p.name for kind in ('orig', 'perf') for p in raw.glob(f'{kind}_2019Q?.txt')}
    if actual != set(known):
        raise RuntimeError('Danh sách nguồn đã thay đổi sau preflight')
    cfg = Config()
    loan_pos = next(c.pos for c in cfg.perf.columns if c.role == 'loan_key') - 1
    month_pos = next(c.pos for c in cfg.perf.columns if c.role == 'reporting_period') - 1
    orig_pos = next(c.pos for c in cfg.orig.columns if c.role == 'loan_key') - 1
    expected = {'orig': Counter(), 'perf': Counter()}
    first_month = {}
    for kind in ('perf', 'orig'):
        for name in sorted(n for n in known if n.startswith(kind + '_')):
            path = raw / name
            digest = hashlib.sha256()
            before = path.stat()
            with path.open('rb') as stream:
                for line in stream:
                    digest.update(line)
                    if kind == 'perf':
                        fields = line.rstrip(b'\r\n').split(b'|', max(loan_pos, month_pos) + 1)
                        loan, month = fields[loan_pos], fields[month_pos]
                        expected['perf'][quarter(month)] += 1
                        if loan not in first_month or month < first_month[loan]:
                            first_month[loan] = month
                    else:
                        loan = line.rstrip(b'\r\n').split(b'|', orig_pos + 1)[orig_pos]
                        if loan in first_month:
                            expected['orig'][quarter(first_month[loan])] += 1
            after = path.stat()
            if (digest.hexdigest() != known[name]['sha256'] or
                (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)):
                raise RuntimeError(f'Nguồn thay đổi: {name}')
            print('Đã đối chiếu SHA-256 và đếm:', name, flush=True)
    del first_month
    lake = ROOT / 'data/lake-historical/warehouse'
    bronze, quality, versions = {}, {}, {}
    for database, names, target in [('bronze', ['orig', 'perf'], bronze),
            ('quality', [f'{kind}_{suffix}' for kind in ('orig', 'perf')
                         for suffix in ('clean', 'quarantine', 'dedup')], quality)]:
        for name in names:
            target[name], versions[f'{database}.{name}'] = snapshot_counts(lake / f'{database}.db' / name)
    wrong = differences(expected, bronze, quality)
    report = dict(scope='Full TXT → Bronze (AC-01) và bảo toàn dòng quality; không phải C5',
                  measured_at=datetime.now(timezone.utc).isoformat(), passed=not wrong,
                  expected={k: dict(sorted(v.items())) for k, v in expected.items()},
                  bronze=bronze, quality=quality, delta_versions=versions, mismatches=wrong)
    target = report_dir / 'bronze-quality-audit.json'
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print('PASS' if report['passed'] else 'FAIL', target, flush=True)
    if wrong:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
