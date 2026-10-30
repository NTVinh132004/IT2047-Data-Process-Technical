"""Thực thi notebook, chỉ lưu bản có kết quả dưới data/ (không commit dữ liệu thật)."""
from pathlib import Path
import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]

def run(output: Path | None = None):
    book = nbformat.read(ROOT / 'notebooks/rui_ro_tin_dung.ipynb', as_version=4)
    NotebookClient(book, timeout=600, kernel_name='python3', resources={'metadata': {'path': str(ROOT)}}).execute()
    output = output or ROOT / 'data/reports/rui_ro_tin_dung.executed.ipynb'
    output.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(book, output)
    return book

if __name__ == '__main__':
    run()
