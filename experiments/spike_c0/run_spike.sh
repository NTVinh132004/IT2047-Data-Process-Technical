#!/usr/bin/env bash
# Spike C0: kiểm R-01 (nhiều load_date trong một stage) và R-08 (chạy lại kỳ cũ sinh 0 dòng).
# Chạy: bash experiments/spike_c0/run_spike.sh   (cần docker compose up -d trong thư mục này; make gate N=0 tự làm)
# Ghi kết quả vào results.json; thoát mã 1 nếu một kiểm thử trượt.
set -euo pipefail
cd "$(dirname "$0")"
TWO='{months: [201904, 201905]}'
dbt() { docker compose exec -T dbt dbt "$@"; }
counts() { dbt run-operation spike_counts --vars "$TWO" | grep '^{'; }
load() { dbt run "$@" | grep -E "Done\." ; }

for _ in $(seq 1 60); do docker compose logs thrift 2>&1 | grep -q "ThriftBinaryCLIService on port 10000" && break; sleep 3; done
dbt deps >/dev/null
dbt run-operation create_raw >/dev/null

# Kịch bản 1 (R-01): hai tháng trong cùng một stage
load --full-refresh --vars "$TWO"
s1=$(counts)
# Kịch bản 2 (R-08): chạy lại tháng 201904 sau khi đã có 201905
load --vars '{months: [201904]}'
s2=$(counts)
# Kịch bản 3 (R-08): nạp từng tháng, rồi chạy lại tháng đầu
load --full-refresh --vars '{months: [201904]}'
load --vars '{months: [201905]}'
s3a=$(counts)
load --vars '{months: [201904]}'
s3b=$(counts)

python3 - "$s1" "$s2" "$s3a" "$s3b" <<'PY'
import json, sys
s1, s2, s3a, s3b = (json.loads(a) for a in sys.argv[1:])
checks = {
    "R-01: Satellite = số dòng perf 2 tháng": s1["sat_rows"] == s1["perf_rows"],
    "R-01: không trùng (hash_key, load_date)": s1["sat_dup_keys"] == 0 and s1["sat_load_dates"] == 2,
    "Hub: mỗi khoản vay một dòng": s1["hub_rows"] == s1["hub_distinct_nk"],
    "R-08: chạy lại 201904 sau 201905 sinh 0 dòng (nạp 2 tháng một lần)": s2["sat_rows"] == s1["sat_rows"] and s2["sat_dup_keys"] == 0,
    "Nạp từng tháng cho cùng kết quả": s3a["sat_rows"] == s1["sat_rows"],
    "R-08: chạy lại 201904 sau 201905 sinh 0 dòng (nạp từng tháng)": s3b["sat_rows"] == s3a["sat_rows"] and s3b["sat_dup_keys"] == 0,
}
json.dump({"counts": {"s1": s1, "s2": s2, "s3a": s3a, "s3b": s3b}, "checks": checks},
          open("results.json", "w"), ensure_ascii=False, indent=2)
for name, ok in checks.items():
    print("PASS" if ok else "FAIL", name)
sys.exit(0 if all(checks.values()) else 1)
PY
