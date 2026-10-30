"""Tóm tắt JSON của `python -m ingestion.control status` thành một dòng "<TRẠNG THÁI>|<mô tả>" cho wait_periods.sh."""
import json
import sys

rows = json.load(sys.stdin)
LAYERS = [key for key in rows[0] if key != 'period'] if rows else []
done = sum(all(r[layer] == "SUCCESS" for layer in LAYERS) for r in rows)
gave_up = [f"{r['period']}:{layer}" for r in rows for layer in LAYERS if r[layer] == "GAVE_UP"]
running = [f"{r['period']}:{layer}" for r in rows for layer in LAYERS if r[layer] == "RUNNING"]
if gave_up:
    state = "GAVE_UP " + ",".join(gave_up)
elif rows and done == len(rows):
    state = "DONE"
else:
    state = "WAIT"
print(f"{state}|{done}/{len(rows)} kỳ xong; đang chạy: {','.join(running) or '-'}")
