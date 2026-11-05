"""Kiểm nguồn đầy đủ, lưu manifest tổng hợp; không lưu khóa khoản vay."""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT / 'data/raw/historical_2019'
    report = {'source': str(source.resolve()), 'files': [], 'passed': False}
    for kind, fields in [('orig', 31), ('perf', 35)]:
        files = sorted(source.glob(f'{kind}_2019Q?.txt'))
        if len(files) != 4:
            raise RuntimeError(f'{kind}: cần đúng 4 file, có {len(files)}')
        for path in files:
            digest, counts, months = hashlib.sha256(), Counter(), Counter()
            before = path.stat()
            with path.open('rb') as stream:
                for line in stream:
                    digest.update(line)
                    counts[len(line.rstrip(b'\r\n').split(b'|'))] += 1
                    if kind == 'perf':
                        month = line.split(b'|', 2)[1].decode('ascii')
                        months[month] += 1
            after = path.stat()
            valid = (set(counts) == {fields} and before.st_size == after.st_size
                     and before.st_mtime_ns == after.st_mtime_ns)
            if months:
                valid &= all(len(m) == 6 and m.isdigit() and '01' <= m[4:] <= '12'
                             and '201901' <= m <= '202603' for m in months)
            entry = dict(name=path.name, bytes=after.st_size, sha256=digest.hexdigest(),
                         rows=sum(counts.values()), field_counts=dict(counts),
                         months=dict(sorted(months.items())), passed=bool(valid))
            report['files'].append(entry)
            print(path.name, entry['rows'], 'PASS' if valid else 'FAIL', flush=True)
    report['passed'] = all(f['passed'] for f in report['files'])
    target = ROOT / 'data/reports/historical/source-manifest.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2))
    if not report['passed']:
        raise SystemExit('Nguồn chưa đạt preflight; xem manifest.')
    print('Manifest:', target)


if __name__ == '__main__':
    main()
