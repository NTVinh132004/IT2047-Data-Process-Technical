"""Thực thi notebook, chỉ lưu bản có kết quả dưới data/ (không commit dữ liệu thật)."""
from pathlib import Path
import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]

def run(output: Path | None = None, dataset: str = "sample"):
    if dataset not in ("sample", "historical"):
        raise ValueError(dataset)
    book = nbformat.read(ROOT / 'notebooks/rui_ro_tin_dung.ipynb', as_version=4)
    if dataset == 'historical':
        for cell in book.cells:
            if cell.cell_type == 'code':
                cell.source = cell.source.replace('NOTEBOOK_DATASET = "sample"', 'NOTEBOOK_DATASET = "historical"').replace('NOTEBOOK_PG_PORT = "5432"', 'NOTEBOOK_PG_PORT = "5433"')
        output = output or ROOT / 'data/reports/historical/rui_ro_tin_dung.executed.ipynb'
    NotebookClient(book, timeout=600, kernel_name='python3', resources={'metadata': {'path': str(ROOT)}}).execute()
    output = output or ROOT / 'data/reports/rui_ro_tin_dung.executed.ipynb'
    output.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(book, output)
    return book

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', choices=['sample', 'historical'], default='sample')
    run(dataset=parser.parse_args().dataset)
