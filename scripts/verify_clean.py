"""Chạy toàn bộ cổng trên bản clone tạm, lake và volume riêng; không xóa dữ liệu workspace.

Stack chính được tạm dừng để đủ RAM và tránh trùng cổng. Script luôn bật lại stack chính.
Bản clone nhận snapshot code chưa commit để xác minh đúng thay đổi đang review.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def call(args, cwd=ROOT, env=None, **kw):
    return subprocess.run(args, cwd=cwd, env=env, check=True, **kw)


def source_digest(root, names):
    digest = hashlib.sha256()
    for name in sorted(names):
        path = root / name
        if path.is_file():
            digest.update(name.encode()+b'\0'+path.read_bytes())
    return digest.hexdigest()


def runtime_names(names):
    return [n for n in names if n.startswith(('ingestion/', 'dbt/', 'dags/', 'scripts/', 'conf/', 'docker/', 'tests/', 'notebooks/'))
            and not n.startswith('tests/gates/results/') or n in ('Makefile', 'docker-compose.yml', 'pyproject.toml', 'uv.lock')]


def run():
    target = Path(tempfile.mkdtemp(prefix='mortgage-c4-clean-'))
    project = target.name.replace('_','-')
    names = subprocess.check_output(['git','ls-files','-co','--exclude-standard'],cwd=ROOT,text=True).splitlines()
    names = sorted(set(n for n in names if not n.startswith('tests/gates/results/')))
    runtime = runtime_names(names)
    digest = source_digest(ROOT,runtime)
    call(['git','clone','--no-hardlinks','--quiet',str(ROOT),str(target)])
    for name in names:
        src = ROOT / name
        if src.is_file():
            dst = target / name
            dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(src,dst)
    shutil.copy2(ROOT/'.env',target/'.env')
    (target/'data').mkdir()
    (target/'data/raw').symlink_to((ROOT/'data/raw').resolve(),target_is_directory=True)
    env = {**os.environ,'COMPOSE_PROJECT_NAME':project,'C4_CLEAN_RUN':'1'}
    reports = ROOT/'data/reports'
    reports.mkdir(parents=True,exist_ok=True)
    context = {'project':project,'source_digest':digest,'source_files':runtime,'lake_initially_absent':not (target/'data/lake').exists(),
               'clone':str(target),'started_at':time.time()}
    (target/'data/clean-context.json').write_text(json.dumps(context))
    # Cổng C0 chạy spike trước khi C1 bật stack chính của bản clone.
    call(['docker','compose','stop'])
    result = None
    try:
        call(['docker','compose','down','-v','--remove-orphans'],cwd=target,env=env)
        call(['uv','sync','--frozen'],cwd=target,env=env)
        with (reports/'clean-tests.log').open('w') as log:
            result = subprocess.run(['uv','run','pytest','tests','-v','--junitxml',str(reports/'clean-tests.xml')],
                                    cwd=target,env=env,stdout=log,stderr=subprocess.STDOUT)
        context['passed'] = result.returncode == 0
        context['finished_at'] = time.time()
        context['seconds'] = round(context['finished_at']-context['started_at'],1)
        for file in (target/'tests/gates/results').glob('*.json'):
            # Chỉ lấy kết quả mới của lần chạy này, không sao chép bằng chứng cũ từ lịch sử clone.
            if file.stat().st_mtime >= context['started_at']:
                shutil.copy2(file,ROOT/'tests/gates/results'/file.name)
                record = json.loads(file.read_text())
                if record.get('gate') == 'C1':
                    context['end_to_end_seconds'] = record.get('end_to_end_seconds')
        (reports/'clean-run.json').write_text(json.dumps(context,indent=2)+'\n')
        if result.returncode:
            raise RuntimeError(f'Kiểm thử sạch không đạt; xem {reports / "clean-tests.log"}')
    finally:
        try:
            call(['docker','compose','down','-v','--remove-orphans'],cwd=target,env=env)
        finally:
            call(['docker','compose','start'])
    print(json.dumps(context))


if __name__ == '__main__':
    run()
