"""Điều kiện sẵn sàng của bảng điều khiển (ingestion/control.py: ready_periods), review R-33."""
from datetime import datetime, timedelta, timezone

from ingestion.control import Request, Run, ready_batch, ready_periods

T0 = datetime(2026, 10, 30, 8, 0, tzinfo=timezone.utc)
ORDER = ["2019Q1", "2019Q2", "2019Q3", "CORR1"]


def at(minutes: int) -> datetime:
    return T0 + timedelta(minutes=minutes)


def req(period: str, minute: int = 0, force: bool = False, **options) -> Request:
    return Request(period, at(minute), force, options)


def ok(period: str, layer: str, minute: int) -> Run:
    return Run(period, layer, "SUCCESS", at(minute), at(minute), None)


def failed(period: str, layer: str, minute: int) -> Run:
    return Run(period, layer, "FAILED", at(minute), at(minute), None)


def requests(*items: Request) -> dict[str, Request]:
    return {r.period: r for r in items}


def all_done(period: str, minute: int) -> list[Run]:
    return [ok(period, layer, minute) for layer in ("ingest", "quality", "raw_vault", "business_vault")]


ALL3 = requests(req("2019Q1"), req("2019Q2"), req("2019Q3"))


def test_only_requested_periods_and_first_layer_without_upstream():
    assert ready_periods("ingest", ORDER, ALL3, [], at(1)) == ["2019Q1", "2019Q2", "2019Q3"]
    assert ready_periods("quality", ORDER, ALL3, [], at(1)) == []
    assert ready_periods("ingest", ORDER, {}, [], at(1)) == []


def test_quality_has_no_chronological_constraint():
    runs = [ok("2019Q2", "ingest", 2), ok("2019Q3", "ingest", 3)]
    assert ready_periods("quality", ORDER, ALL3, runs, at(4)) == ["2019Q2", "2019Q3"]


def test_raw_vault_waits_for_previous_period():
    runs = [ok(p, layer, 2) for p in ("2019Q1", "2019Q2", "2019Q3") for layer in ("ingest", "quality")]
    assert ready_periods("raw_vault", ORDER, ALL3, runs, at(3)) == ["2019Q1"]
    runs.append(ok("2019Q1", "raw_vault", 4))
    assert ready_periods("raw_vault", ORDER, ALL3, runs, at(5)) == ["2019Q2"]


def test_business_vault_needs_raw_vault_and_previous_business_vault():
    runs = all_done("2019Q1", 2)[:3] + [ok("2019Q2", layer, 3) for layer in ("ingest", "quality", "raw_vault")]
    assert ready_periods("business_vault", ORDER, ALL3, runs, at(4)) == ["2019Q1"]


def test_done_layers_are_not_reprocessed_by_a_normal_request():
    runs = all_done("2019Q1", 2)
    again = requests(req("2019Q1", minute=10))
    for layer in ("ingest", "quality", "raw_vault", "business_vault"):
        assert ready_periods(layer, ORDER, again, runs, at(11)) == []


def test_force_request_reprocesses_every_layer_in_order():
    runs = all_done("2019Q1", 2) + all_done("2019Q2", 3)
    forced = requests(req("2019Q1"), req("2019Q2", minute=10, force=True))
    assert ready_periods("ingest", ORDER, forced, runs, at(11)) == ["2019Q2"]
    # Tầng sau chờ tầng trên được xử lý lại sau yêu cầu, dù tầng trên đã từng SUCCESS
    assert ready_periods("quality", ORDER, forced, runs, at(11)) == []
    runs.append(ok("2019Q2", "ingest", 12))
    assert ready_periods("quality", ORDER, forced, runs, at(13)) == ["2019Q2"]


def test_correction_runs_after_last_quarter():
    reqs = requests(req("2019Q1"), req("2019Q2"), req("2019Q3"), req("CORR1", minute=20))
    runs = all_done("2019Q1", 2) + all_done("2019Q2", 3) + [ok("2019Q3", l, 4) for l in ("ingest", "quality")]
    runs += [ok("CORR1", l, 21) for l in ("ingest", "quality")]
    assert ready_periods("raw_vault", ORDER, reqs, runs, at(22)) == ["2019Q3"]
    runs.append(ok("2019Q3", "raw_vault", 23))
    assert ready_periods("raw_vault", ORDER, reqs, runs, at(24)) == ["CORR1"]


def test_failures_count_against_attempt_limit():
    runs = [failed("2019Q1", "ingest", m) for m in (1, 2)]
    assert ready_periods("ingest", ORDER, requests(req("2019Q1")), runs, at(3)) == ["2019Q1"]
    runs.append(failed("2019Q1", "ingest", 3))
    assert ready_periods("ingest", ORDER, requests(req("2019Q1")), runs, at(4)) == []
    # Yêu cầu mới thì đếm lại từ đầu
    assert ready_periods("ingest", ORDER, requests(req("2019Q1", minute=5)), runs, at(6)) == ["2019Q1"]


def test_max_attempts_option():
    runs = [failed("2019Q1", "ingest", 1)]
    assert ready_periods("ingest", ORDER, requests(req("2019Q1", max_attempts=1)), runs, at(2)) == []


def test_running_with_valid_lease_blocks_but_expired_does_not():
    running = Run("2019Q1", "ingest", "RUNNING", at(1), None, at(61))
    assert ready_periods("ingest", ORDER, requests(req("2019Q1")), [running], at(30)) == []
    assert ready_periods("ingest", ORDER, requests(req("2019Q1")), [running], at(90)) == ["2019Q1"]


def test_batch_takes_consecutive_ready_periods_up_to_limit():
    runs = [ok(p, l, 2) for p in ("2019Q1", "2019Q2", "2019Q3") for l in ("ingest", "quality")]
    assert ready_batch("raw_vault", ORDER, ALL3, runs, at(3), max_periods=10) == ["2019Q1", "2019Q2", "2019Q3"]
    assert ready_batch("raw_vault", ORDER, ALL3, runs, at(3), max_periods=2) == ["2019Q1", "2019Q2"]


def test_batch_stops_at_period_whose_upstream_is_not_done():
    runs = [ok(p, l, 2) for p in ("2019Q1", "2019Q3") for l in ("ingest", "quality")] + [ok("2019Q2", "ingest", 2)]
    assert ready_batch("raw_vault", ORDER, ALL3, runs, at(3), max_periods=10) == ["2019Q1"]


def test_batch_never_includes_corrections():
    reqs = requests(req("2019Q1"), req("2019Q2"), req("2019Q3"), req("CORR1"))
    runs = [ok(p, l, 2) for p in ("2019Q1", "2019Q2", "2019Q3", "CORR1") for l in ("ingest", "quality")]
    batch = ready_batch("raw_vault", ORDER, reqs, runs, at(3), max_periods=10, corrections={"CORR1"})
    assert batch == ["2019Q1", "2019Q2", "2019Q3"]
    done = runs + [ok(p, "raw_vault", 4) for p in batch]
    assert ready_batch("raw_vault", ORDER, reqs, done, at(5), max_periods=10, corrections={"CORR1"}) == ["CORR1"]


def test_non_chronological_layers_process_one_period():
    assert ready_batch("quality", ORDER, ALL3, [ok(p, "ingest", 1) for p in ("2019Q1", "2019Q2")], at(2), 10) == ["2019Q1"]
