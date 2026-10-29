"""Khám phá bộ mẫu 2019 (giai đoạn 0), chỉ dùng thư viện chuẩn để chạy được khi chưa có Spark.

Chạy: python3 experiments/kham_pha_bo_mau.py [thư mục dữ liệu]
Vị trí cột theo File Layout Release 47 (docs/tu-dien-du-lieu.md). Kết quả in ra là số tổng hợp,
được phép đưa vào tài liệu; không in dòng dữ liệu thô.
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

RAW = Path(sys.argv[1] if len(sys.argv) > 1 else "data/raw/sample_2019")

# Vị trí (bắt đầu từ 0) của các cột cần khám phá
O_FICO, O_FIRST_PAY, O_MI_PCT, O_CLTV, O_DTI, O_LTV = 0, 1, 5, 8, 9, 11
O_STATE, O_ZIP, O_LOAN_ID, O_PURPOSE, O_SELLER = 16, 18, 19, 20, 23
O_SPECIAL, O_VS4 = 26, 30
P_LOAN_ID, P_PERIOD, P_UPB, P_DLQ, P_MOD, P_ZBC, P_ZB_DATE = 0, 1, 2, 3, 7, 8, 9
P_DEFERRAL, P_ELTV, P_DISASTER, P_ASSIST, P_MI_CANCEL, P_SERVICER = 24, 25, 28, 29, 32, 33


def top(counter, n=12):
    return ", ".join(f"{'<rỗng>' if k == '' else k}={v}" for k, v in counter.most_common(n))


def quarter(period):
    return f"{period[:4]}Q{(int(period[4:]) - 1) // 3 + 1}"


def profile_orig():
    fields = Counter()
    seen = Counter()
    cols = defaultdict(Counter)
    first_pay = {}
    with open(RAW / "sample_orig_2019.txt") as f:
        for line in f:
            r = line.rstrip("\n").split("|")
            fields[len(r)] += 1
            seen[r[O_LOAN_ID]] += 1
            first_pay[r[O_LOAN_ID]] = r[O_FIRST_PAY]
            # Mã thiếu theo File Layout: điểm tín dụng 9999, tỷ lệ 999; MI 0 = không có MI
            for name, i, missing in [("fico", O_FICO, "9999"), ("vs4", O_VS4, "9999"),
                                     ("mi_pct", O_MI_PCT, "999"), ("cltv", O_CLTV, "999"),
                                     ("dti", O_DTI, "999"), ("ltv", O_LTV, "999")]:
                v = r[i]
                cols[name]["" if v == "" else v if v in (missing, "0") else "giá trị"] += 1
            for name, i in [("purpose", O_PURPOSE), ("seller", O_SELLER),
                            ("special_program", O_SPECIAL), ("zip_len", O_ZIP)]:
                cols[name][r[i] if name != "zip_len" else len(r[i])] += 1
            cols["state"][r[O_STATE]] += 1
            cols["loan_prefix"][r[O_LOAN_ID][:5]] += 1
    print("== ORIG ==")
    print("số trường/dòng:", dict(fields))
    print("số dòng:", sum(seen.values()), "| mã khoản vay khác nhau:", len(seen),
          "| mã trùng:", sum(1 for c in seen.values() if c > 1))
    for name, c in cols.items():
        print(f"{name} ({len(c)} giá trị):", top(c, 8 if name == "state" else 12))
    return set(seen), first_pay


def profile_perf(orig_ids, first_pay):
    fields = Counter()
    keys = Counter()
    per_loan_periods = defaultdict(list)
    servicers = defaultdict(set)
    rows_by_q = Counter()
    rows_by_period = Counter()
    cols = defaultdict(Counter)
    with open(RAW / "sample_perf_2019.txt") as f:
        for line in f:
            r = line.rstrip("\n").split("|")
            fields[len(r)] += 1
            loan, period = r[P_LOAN_ID], r[P_PERIOD]
            keys[(loan, period)] += 1
            per_loan_periods[loan].append(period)
            servicers[loan].add(r[P_SERVICER])
            rows_by_q[quarter(period)] += 1
            rows_by_period[period] += 1
            for name, i in [("dlq_status", P_DLQ), ("mod_flag", P_MOD), ("zbc", P_ZBC),
                            ("payment_deferral", P_DEFERRAL), ("disaster", P_DISASTER),
                            ("assistance_plan", P_ASSIST), ("mi_cancel", P_MI_CANCEL),
                            ("servicer", P_SERVICER)]:
                cols[name][r[i]] += 1
            cols["eltv"]["" if r[P_ELTV] == "" else r[P_ELTV] if r[P_ELTV] == "999" else "giá trị"] += 1
            cols["upb"]["" if r[P_UPB] == "" else "giá trị"] += 1
    print("\n== PERF ==")
    print("số trường/dòng:", dict(fields))
    print("số dòng:", sum(keys.values()), "| khoản vay:", len(per_loan_periods),
          "| khóa (loan, tháng) trùng:", sum(1 for c in keys.values() if c > 1))
    periods = sorted(rows_by_period)
    print("tháng báo cáo:", periods[0], "->", periods[-1], f"({len(periods)} tháng)")
    print("số kỳ (quý báo cáo):", len(rows_by_q))
    print("dòng theo quý:", ", ".join(f"{q}={n}" for q, n in sorted(rows_by_q.items())))
    perf_ids = set(per_loan_periods)
    print("mồ côi (perf không có orig):", len(perf_ids - orig_ids),
          "| orig không có perf:", len(orig_ids - perf_ids))
    for name, c in cols.items():
        print(f"{name} ({len(c)} giá trị):", top(c))
    dlq = cols["dlq_status"]
    print("dlq_status không phải số:", {k: v for k, v in dlq.items() if not k.isdigit()},
          "| lớn nhất:", max(int(k) for k in dlq if k.isdigit()))
    # Tính liên tục của chuỗi tháng và tháng perf đầu tiên so với ngày trả góp đầu tiên
    gaps = 0
    first_vs_pay = Counter()
    first_q = Counter()
    for loan, ps in per_loan_periods.items():
        ps.sort()
        months = [int(p[:4]) * 12 + int(p[4:]) for p in ps]
        gaps += any(b - a != 1 for a, b in zip(months, months[1:]))
        if loan in first_pay:
            fp = first_pay[loan]
            first_vs_pay[months[0] - (int(fp[:4]) * 12 + int(fp[4:]))] += 1
        first_q[quarter(ps[0])] += 1
    print("khoản vay có tháng bị hở:", gaps)
    print("tháng perf đầu tiên - first payment date (tháng):", top(first_vs_pay))
    print("khoản vay theo quý perf đầu tiên (lát orig của kỳ):",
          ", ".join(f"{q}={n}" for q, n in sorted(first_q.items())))
    changed = sum(1 for s in servicers.values() if len(s) > 1)
    print("khoản vay đổi servicer ít nhất 1 lần:", changed)


if __name__ == "__main__":
    ids, fp = profile_orig()
    profile_perf(ids, fp)
