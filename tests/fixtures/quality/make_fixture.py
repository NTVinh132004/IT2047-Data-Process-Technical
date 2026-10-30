"""Sinh bộ dữ liệu giả lập cho test cổng chất lượng (FR-07, cổng C2).

Bộ mẫu thật không có dòng lỗi nào (docs/tu-dien-du-lieu.md mục 1), nên test cần dữ liệu cố ý chứa từng loại lỗi
ở mục 5 của từ điển. Mọi giá trị là giả lập; không chứa dữ liệu Freddie Mac.

Chạy lại sau khi đổi conf/schema: uv run python -m tests.fixtures.quality.make_fixture
Sinh ra: sample_orig_2019.txt, sample_perf_2019.txt (cùng tên file với bộ mẫu để dùng chung conf) và expected.yml.
Mỗi dòng lỗi mang một lý do chính, theo thứ tự ưu tiên của bảng luật trong từ điển dữ liệu mục 5.
"""
from pathlib import Path

import yaml

from ingestion.config import Config

OUT = Path(__file__).parent
PERIOD = "2019Q2"
MONTHS = ["201904", "201905", "201906"]

ORIG_DEFAULTS = {
    "credit_score": "750", "first_payment_date": "201905", "first_time_homebuyer_flag": "N",
    "maturity_date": "204904", "msa_code": "10180", "mi_pct": "0", "number_of_units": "1",
    "occupancy_status": "P", "orig_cltv": "80", "orig_dti": "35", "orig_upb": "250000", "orig_ltv": "80",
    "orig_interest_rate": "4.5", "channel": "R", "prepayment_penalty_flag": "N", "amortization_type": "FRM",
    "property_state": "TX", "property_type": "SF", "postal_code": "750", "loan_purpose": "P",
    "orig_loan_term": "360", "number_of_borrowers": "2", "seller_name": "OTHER", "super_conforming_flag": "N",
    "pre_harp_loan_id": "", "special_eligibility_program": "", "harp_indicator": "N",
    "property_valuation_method": "2", "interest_only_flag": "N", "vantage_score_4": "9999",
}
PERF_DEFAULTS = {
    "current_upb": "250000.00", "delinquency_status": "00", "loan_age": "1", "remaining_months": "359",
    "current_interest_rate": "4.500", "non_interest_bearing_upb": "0.00", "cumulative_modification_cost": "0.00",
    "eltv": "75", "interest_bearing_upb": "250000.00", "mi_cancellation_flag": "7", "servicer_name": "OTHER",
}


def loan(n: int) -> str:
    return f"F19Q2{n:07d}"  # mã giả lập, chỉ dùng trong bộ fixture riêng, không trộn với dữ liệu thật


def line(schema, values: dict, drop_last: bool = False) -> str:
    fields = [values.get(c.name, "") for c in schema.columns]
    return "|".join(fields[:-1] if drop_last else fields)


def main() -> None:
    cfg = Config()
    orig, perf, rejected = [], [], []

    def add_orig(n, reason=None, drop_last=False, **override):
        orig.append(line(cfg.orig, {**ORIG_DEFAULTS, "loan_id": loan(n), **override}, drop_last))
        if reason:
            rejected.append({"table": "orig", "loan_id": loan(n), "reason": reason})

    def add_perf(n, month, reason=None, drop_last=False, loan_id=None, **override):
        lid = loan_id or loan(n)
        perf.append(line(cfg.perf, {**PERF_DEFAULTS, "loan_id": lid, "reporting_period": month, **override}, drop_last))
        if reason:
            rejected.append({"table": "perf", "loan_id": lid, "reporting_period": month, "reason": reason})

    # 5 khoản vay hợp lệ, đủ 3 tháng
    for n in range(9900001, 9900006):
        add_orig(n)
        for month in MONTHS:
            add_perf(n, month)
    # Mã thiếu không phải lỗi: FICO 9999, DTI 999, tình trạng quá hạn XX
    add_orig(9900006, credit_score="9999", orig_dti="999")
    add_perf(9900006, "201904", delinquency_status="XX")
    # sai_so_truong: thiếu trường cuối
    add_orig(9900007, "sai_so_truong", drop_last=True)
    add_perf(9900007, "201904")
    add_orig(9900008)
    add_perf(9900008, "201904", "sai_so_truong", drop_last=True)
    # sai_khoa: mã khoản vay sai mẫu (dòng perf này cũng không có orig, nhưng lý do chính là sai_khoa)
    add_perf(0, "201905", "sai_khoa", loan_id="X19Q2BADKEY1")
    # sai_kieu: số có chữ cái
    add_orig(9900009, "sai_kieu", orig_upb="25O000")
    add_perf(9900009, "201904")
    add_orig(9900010)
    add_perf(9900010, "201904", "sai_kieu", current_upb="12O000.00")
    # ngoai_mien: giá trị ngoài miền hoặc ngoài danh sách mã
    add_orig(9900011, "ngoai_mien", credit_score="200")
    add_perf(9900011, "201904")
    add_orig(9900012, "ngoai_mien", occupancy_status="X")
    add_perf(9900012, "201904")
    add_orig(9900013)
    add_perf(9900013, "201905", "ngoai_mien", delinquency_status="ZZ")
    # trung_khoa: mọi bản sao của khóa trùng đều bị chặn, vì không biết bản nào đúng
    add_orig(9900014, "trung_khoa")
    add_orig(9900014, "trung_khoa", orig_upb="260000")
    add_perf(9900014, "201904")
    add_orig(9900015)
    add_perf(9900015, "201905", "trung_khoa")
    add_perf(9900015, "201905", "trung_khoa", current_upb="249000.00")
    # mo_coi: perf hợp lệ nhưng khoản vay không có trong orig
    add_perf(9900099, "201904", "mo_coi")
    # Dòng perf của khoản vay có orig bị chặn vẫn sạch: luật mồ côi so với orig ở Bronze (từ điển mục 5)

    (OUT / "sample_orig_2019.txt").write_text("\n".join(orig) + "\n")
    (OUT / "sample_perf_2019.txt").write_text("\n".join(perf) + "\n")
    summary = {}
    for table, rows in (("orig", orig), ("perf", perf)):
        bad = [r for r in rejected if r["table"] == table]
        summary[table] = {"bronze_rows": len(rows), "rejected_rows": len(bad), "clean_rows": len(rows) - len(bad)}
    expected = {"period": PERIOD, "summary": summary, "rejected": rejected}
    (OUT / "expected.yml").write_text(
        "# Sinh bởi make_fixture.py, đừng sửa tay. Kết quả cổng chất lượng mong đợi cho kỳ " + PERIOD + "\n"
        + yaml.safe_dump(expected, allow_unicode=True, sort_keys=False)
    )
    print(summary)


if __name__ == "__main__":
    main()
