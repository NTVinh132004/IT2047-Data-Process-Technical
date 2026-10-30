"""Sinh bộ dữ liệu giả lập cho test cổng chất lượng (FR-07, cổng C2).

Bộ mẫu thật không có dòng lỗi nào (docs/tu-dien-du-lieu.md mục 1), nên test cần dữ liệu cố ý chứa từng loại lỗi
ở mục 5 của từ điển. Mọi giá trị là giả lập; không chứa dữ liệu Freddie Mac.

Chạy lại sau khi đổi conf/schema: uv run python -m tests.fixtures.quality.make_fixture
Sinh ra: sample_orig_2019.txt, sample_perf_2019.txt (cùng tên file với bộ mẫu để dùng chung conf), expected.yml, và
dbt unit test của business_vault.quality_violation (soft rule ở Business Vault, R-35) dùng cùng giá trị mặc định.
Mỗi dòng lỗi mang một lý do chính, theo thứ tự ưu tiên của bảng luật trong từ điển dữ liệu mục 5.
"""
from pathlib import Path

import yaml

from ingestion.config import Config

OUT = Path(__file__).parent
UNIT_TEST = OUT.parents[2] / "dbt/models/business_vault/quality_violation_unit_test.yml"
ZERO_KEY = "0" * 64
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
    orig, perf, quarantine, dedup, soft = [], [], [], [], []

    def record(kind, table, loan_id, month, extra):
        row = {"table": table, "loan_id": loan_id, **({"reporting_period": month} if table == "perf" else {}), **extra}
        {"quarantine": quarantine, "dedup": dedup, "soft": soft}[kind].append(row)

    def add_orig(n, hard=None, drop_last=False, soft_on=None, copy=False, **override):
        orig.append(line(cfg.orig, {**ORIG_DEFAULTS, "loan_id": loan(n), **override}, drop_last))
        if hard:
            record("quarantine", "orig", loan(n), None, {"reason": hard})
        if copy:
            record("dedup", "orig", loan(n), None, {})

    def add_perf(n, month, hard=None, drop_last=False, loan_id=None, soft_on=None, copy=False, **override):
        lid = loan_id or loan(n)
        perf.append(line(cfg.perf, {**PERF_DEFAULTS, "loan_id": lid, "reporting_period": month, **override}, drop_last))
        if hard:
            record("quarantine", "perf", lid, month, {"reason": hard})
        if copy:
            record("dedup", "perf", lid, month, {})

    # 5 khoản vay hợp lệ, đủ 3 tháng
    for n in range(9900001, 9900006):
        add_orig(n)
        for month in MONTHS:
            add_perf(n, month)
    # Mã thiếu không phải lỗi: FICO 9999, DTI 999, tình trạng quá hạn XX
    add_orig(9900006, credit_score="9999", orig_dti="999")
    add_perf(9900006, "201904", delinquency_status="XX")
    # Hard rule: sai_so_truong (thiếu trường cuối) vào error mart
    add_orig(9900007, "sai_so_truong", drop_last=True)
    add_perf(9900007, "201904")  # orig vẫn có ở Bronze nên dòng này không mồ côi
    add_orig(9900008)
    add_perf(9900008, "201904", "sai_so_truong", drop_last=True)
    # Hard rule: sai_khoa (mã sai mẫu); dòng này cũng không có orig nhưng đã vào error mart nên không tính mồ côi
    add_perf(0, "201905", "sai_khoa", loan_id="X19Q2BADKEY1")
    # Hard rule: sai_kieu (số có chữ cái)
    add_orig(9900009, "sai_kieu", orig_upb="25O000")
    add_perf(9900009, "201904")
    add_orig(9900010)
    add_perf(9900010, "201904", "sai_kieu", current_upb="12O000.00")
    # Soft rule: ngoai_mien. Dòng vẫn sạch và vào Raw Vault; vi phạm được báo ở Business Vault (R-35)
    add_orig(9900011, soft_on=("ngoai_mien", "credit_score"), credit_score="200")
    add_perf(9900011, "201904")
    add_orig(9900012, soft_on=("ngoai_mien", "occupancy_status"), occupancy_status="X")
    add_perf(9900012, "201904")
    add_orig(9900013)
    add_perf(9900013, "201905", soft_on=("ngoai_mien", "delinquency_status"), delinquency_status="ZZ")
    # Trùng khóa khác giá trị: không nạp được (trùng khóa Satellite), mọi bản vào error mart
    add_orig(9900014, "trung_khoa")
    add_orig(9900014, "trung_khoa", orig_upb="260000")
    add_perf(9900014, "201904")
    add_orig(9900015)
    add_perf(9900015, "201905", "trung_khoa")
    add_perf(9900015, "201905", "trung_khoa", current_upb="249000.00")
    # Bản sao giống hệt: khử trùng lặp, giữ một bản sạch, bản còn lại vào <x>_dedup
    add_orig(9900016)
    add_orig(9900016, copy=True)
    add_perf(9900016, "201904")
    add_perf(9900016, "201904", copy=True)
    # Soft rule: mo_coi. Perf hợp lệ nhưng khoản vay không có trong orig; vẫn sạch, vi phạm báo ở Business Vault
    add_perf(9900099, "201904", soft_on=("mo_coi", "loan_id"))

    (OUT / "sample_orig_2019.txt").write_text("\n".join(orig) + "\n")
    (OUT / "sample_perf_2019.txt").write_text("\n".join(perf) + "\n")
    summary = {}
    for table, rows in (("orig", orig), ("perf", perf)):
        n_bad = sum(1 for r in quarantine if r["table"] == table)
        n_copy = sum(1 for r in dedup if r["table"] == table)
        summary[table] = {"bronze_rows": len(rows), "quarantine_rows": n_bad, "dedup_rows": n_copy,
                          "clean_rows": len(rows) - n_bad - n_copy}
    expected = {"period": PERIOD, "summary": summary, "quarantine": quarantine, "dedup": dedup}
    (OUT / "expected.yml").write_text(
        "# Sinh bởi make_fixture.py, đừng sửa tay. Kết quả cổng chất lượng mong đợi cho kỳ " + PERIOD + "\n"
        + yaml.safe_dump(expected, allow_unicode=True, sort_keys=False)
    )
    write_unit_test(cfg)
    print(summary)


def sat_columns(cfg: Config) -> dict[str, list[str]]:
    by_sat: dict[str, list[str]] = {}
    for schema in (cfg.orig, cfg.perf):
        for c in schema.columns:
            target = c.spec.get("target")
            if isinstance(target, str) and target.startswith("sat_"):
                by_sat.setdefault(target, []).append(c.name)
    return by_sat


def write_unit_test(cfg: Config) -> None:
    """dbt unit test cho quality_violation: mỗi Satellite một dòng hợp lệ đầy đủ, cộng từng ca vi phạm hoặc không vi phạm."""
    defaults = {**ORIG_DEFAULTS, **PERF_DEFAULTS, "reporting_period": "201904"}
    columns = sat_columns(cfg)

    def row(sat: str, loan_hk: str, **override) -> dict:
        values = {c: defaults[c] for c in columns[sat] if defaults.get(c, "") != ""}  # chuỗi rỗng là null ở Raw Vault
        values.update(override)
        return {"LOAN_HK": loan_hk, "load_date": "2019-05-01", **{k: v for k, v in values.items() if v is not None}}

    ghost = {"LOAN_HK": ZERO_KEY, "load_date": "1900-01-01"}
    given = {
        "sat_loan_origination": [dict(ghost), row("sat_loan_origination", "V1"), row("sat_loan_origination", "Q1", credit_score="200"),
                                 row("sat_loan_origination", "Q3", credit_score="9999")],
        "sat_loan_property": [dict(ghost), row("sat_loan_property", "V1"), row("sat_loan_property", "Q2", occupancy_status="X"),
                              row("sat_loan_property", "Q4", msa_code=None)],
        "sat_loan_balance": [dict(ghost), row("sat_loan_balance", "V1"), row("sat_loan_balance", "Q6", current_upb=None)],
        "sat_loan_delinquency": [dict(ghost), row("sat_loan_delinquency", "V1"),
                                 row("sat_loan_delinquency", "Q5", delinquency_status="ZZ"),
                                 row("sat_loan_delinquency", "V2", delinquency_status="XX")],
        "sat_loan_termination": [dict(ghost), row("sat_loan_termination", "V1")],
        "xts_loan": [{"LOAN_HK": "V1", "load_date": "2019-05-01", "SATELLITE_NAME": "perf"},
                     {"LOAN_HK": "Q7", "load_date": "2019-05-01", "SATELLITE_NAME": "perf"}],
    }
    expect = [
        {"LOAN_HK": "Q1", "satellite": "sat_loan_origination", "rule": "ngoai_mien", "column_name": "credit_score", "value": "200"},
        {"LOAN_HK": "Q2", "satellite": "sat_loan_property", "rule": "ngoai_mien", "column_name": "occupancy_status", "value": "X"},
        {"LOAN_HK": "Q5", "satellite": "sat_loan_delinquency", "rule": "ngoai_mien", "column_name": "delinquency_status", "value": "ZZ"},
        {"LOAN_HK": "Q6", "satellite": "sat_loan_balance", "rule": "ngoai_mien", "column_name": "current_upb", "value": None},
        {"LOAN_HK": "Q7", "satellite": "xts_loan", "rule": "mo_coi", "column_name": "loan_id", "value": None},
    ]
    doc = {"unit_tests": [{
        "name": "quality_violation_soft_rules",
        "description": ("Soft rule ở Business Vault (R-35): ngoài miền (Q1), ngoài danh sách mã (Q2), sai mẫu (Q5), thiếu "
                        "giá trị bắt buộc (Q6), perf không có orig (Q7) là vi phạm; mã thiếu (Q3 9999, V2 XX), cột cho phép "
                        "null (Q4) và ghost record không phải vi phạm"),
        "model": "quality_violation",
        "given": [{"input": f"ref('{name}')", "rows": rows} for name, rows in given.items()],
        "expect": {"rows": expect},
    }]}
    UNIT_TEST.write_text("# Sinh bởi tests/fixtures/quality/make_fixture.py, đừng sửa tay.\n"
                         + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False))


if __name__ == "__main__":
    main()
