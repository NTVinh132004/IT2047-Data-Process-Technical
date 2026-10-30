"""Bảng điều khiển của pipeline (FR-01, FR-02, FR-21; review R-33).

Mỗi tầng một job (DAG Airflow chạy định kỳ). Job đọc bảng điều khiển để chọn kỳ đủ điều kiện, xử lý, rồi ghi trạng thái:

- control.period_request: yêu cầu xử lý một kỳ (make run-all, make run PERIOD=..., make correction). Job chỉ xử lý
  kỳ đã được yêu cầu; force = xử lý lại mọi tầng kể cả tầng đã xong (kiểm idempotent, AC-02).
- control.layer_run: mỗi lần một tầng xử lý một kỳ một dòng (PENDING không dùng; RUNNING, SUCCESS, FAILED).
- view control.load_control: mỗi kỳ một dòng, trạng thái mới nhất của từng tầng (báo cáo G5).

Một tầng sẵn sàng cho kỳ P khi (ready_periods):
  1. P có yêu cầu mà tầng này chưa đáp ứng: chưa từng SUCCESS (yêu cầu thường), hoặc chưa SUCCESS sau thời điểm yêu
     cầu (yêu cầu force);
  2. tầng trên của P đã đáp ứng yêu cầu đó (tầng đầu không có điều kiện này);
  3. với tầng cần thứ tự thời gian, kỳ liền trước của P đã xong tầng này. Raw Vault: bộ lọc kỹ thuật của Satellite bỏ
     dòng có load_date cũ hơn phiên bản mới nhất, nạp lùi sẽ mất dữ liệu. Business Vault: "hạt giống" lấy từ kỳ trước;
  4. không có lần chạy RUNNING còn hạn thuê, và số lần thất bại kể từ yêu cầu chưa tới giới hạn.
Dòng RUNNING quá hạn thuê (job chết, máy tắt) được đánh FAILED để nhặt lại.

Chạy (trong container airflow-scheduler):
  python -m ingestion.control request --all | --period 2020Q1 [--force] [--options '{"inject_test_failure": true}']
  python -m ingestion.control status [--period P]      -> JSON trạng thái từng tầng của các kỳ đã yêu cầu
  python -m ingestion.control invalidate --layers raw_vault,business_vault --reason "..."  -> tầng phải dựng lại
"""
import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import psycopg2
import psycopg2.extras

from ingestion.config import Config
from ingestion.periods import periods_between

LAYERS = ("ingest", "quality", "raw_vault", "business_vault")
UPSTREAM = {"quality": "ingest", "raw_vault": "quality", "business_vault": "raw_vault"}
CHRONOLOGICAL = {"raw_vault", "business_vault"}
MAX_ATTEMPTS = 3
LEASE = timedelta(hours=1)


@dataclass(frozen=True)
class Run:
    period: str
    layer: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    lease_until: datetime | None


@dataclass(frozen=True)
class Request:
    period: str
    requested_at: datetime
    force: bool
    options: dict


def ordered_periods(cfg: Config) -> list[str]:
    """Thứ tự thời gian: các quý trong dải của conf, rồi các đợt sửa dữ liệu (nạp sau kỳ cuối)."""
    p = cfg.pipeline["periods"]
    return periods_between(p["first"], p["last"]) + list(cfg.pipeline.get("corrections", {}))


def _succeeded_since(runs: list[Run], period: str, layer: str, since: datetime | None) -> bool:
    return any(r.period == period and r.layer == layer and r.status == "SUCCESS"
               and (since is None or r.finished_at >= since) for r in runs)


def _done(runs: list[Run], requests: dict[str, Request], period: str, layer: str) -> bool:
    """Tầng đã đáp ứng yêu cầu mới nhất của kỳ: yêu cầu thường thì SUCCESS bất kỳ lúc nào cũng tính (tầng đã xong không
    xử lý lại, R-32); yêu cầu force thì chỉ tính SUCCESS sau thời điểm yêu cầu."""
    req = requests[period]
    return _succeeded_since(runs, period, layer, req.requested_at if req.force else None)


def ready_periods(layer: str, order: list[str], requests: dict[str, Request], runs: list[Run], now: datetime,
                  max_attempts: int = MAX_ATTEMPTS) -> list[str]:
    """Các kỳ tầng này được phép xử lý ngay, theo thứ tự thời gian (xem docstring của module)."""
    ready = []
    for i, period in enumerate(order):
        req = requests.get(period)
        if req is None or _done(runs, requests, period, layer):
            continue
        upstream = UPSTREAM.get(layer)
        if upstream and not _done(runs, requests, period, upstream):
            continue
        if layer in CHRONOLOGICAL and i > 0:
            prev = order[i - 1]
            # Kỳ trước chưa từng được yêu cầu thì chưa có gì để chờ; đã yêu cầu thì phải xong tầng này trước
            if prev in requests and not _done(runs, requests, prev, layer):
                continue
        mine = [r for r in runs if r.period == period and r.layer == layer]
        if any(r.status == "RUNNING" and r.lease_until and r.lease_until > now for r in mine):
            continue
        limit = req.options.get("max_attempts", max_attempts)
        if sum(1 for r in mine if r.status == "FAILED" and r.started_at >= req.requested_at) >= limit:
            continue
        ready.append(period)
    return ready


def ready_batch(layer: str, order: list[str], requests: dict[str, Request], runs: list[Run], now: datetime,
                max_periods: int, corrections: set[str] = frozenset()) -> list[str]:
    """Lô kỳ xử lý trong một lần chạy (R-34): bắt đầu từ kỳ sẵn sàng sớm nhất, nối tiếp các kỳ liền sau theo thứ tự
    thời gian mà cũng sẽ sẵn sàng nếu các kỳ trước trong lô đã xong (đã yêu cầu, tầng trên đã xong, chưa xong tầng
    này, không đang chạy, chưa hết số lần thử). Tầng không cần thứ tự thời gian xử lý từng kỳ. Đợt sửa dữ liệu luôn
    đi riêng: gom chung với kỳ gốc thì một khoản vay có hai dòng nguồn trong cùng lần nạp."""
    ready = ready_periods(layer, order, requests, runs, now)
    if not ready:
        return []
    first = ready[0]
    if layer not in CHRONOLOGICAL or first in corrections:
        return [first]
    batch = [first]
    for period in order[order.index(first) + 1:]:
        if len(batch) >= max_periods or period in corrections:
            break
        assumed = runs + [Run(p, layer, "SUCCESS", now, now, None) for p in batch]
        if ready_periods(layer, [batch[-1], period], requests, assumed, now)[-1:] != [period]:
            break
        batch.append(period)
    return batch


def connect():
    return psycopg2.connect(os.environ["ANALYTICS_DSN"])


def _load(cur, dataset: str) -> tuple[dict[str, Request], list[Run]]:
    cur.execute("SELECT DISTINCT ON (period) period, requested_at, force, options FROM control.period_request"
                " WHERE dataset = %s ORDER BY period, requested_at DESC", (dataset,))
    requests = {p: Request(p, t, f, o or {}) for p, t, f, o in cur.fetchall()}
    cur.execute("SELECT period, layer, status, started_at, finished_at, lease_until FROM control.layer_run"
                " WHERE dataset = %s", (dataset,))
    return requests, [Run(*row) for row in cur.fetchall()]


def request(cfg: Config, periods: list[str], force: bool, options: dict | None = None) -> None:
    with connect() as conn, conn.cursor() as cur:
        for period in periods:
            cur.execute("INSERT INTO control.period_request (period, dataset, force, options) VALUES (%s, %s, %s, %s)",
                        (period, cfg.source, force, json.dumps(options or {})))


def claim(cfg: Config, layer: str, airflow_run_id: str | None = None) -> list[tuple[int, Request]]:
    """Nhận lô kỳ sẵn sàng của tầng (ready_batch): mỗi kỳ một dòng RUNNING có hạn thuê. Khóa advisory theo tầng chống
    nhận trùng. Trả về rỗng nếu không có kỳ nào sẵn sàng."""
    now = datetime.now(timezone.utc)
    with connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"layer_run:{layer}",))
        cur.execute("UPDATE control.layer_run SET status = 'FAILED', finished_at = now(), error = 'Hết hạn thuê (job chết?)'"
                    " WHERE layer = %s AND status = 'RUNNING' AND lease_until < now()", (layer,))
        requests, runs = _load(cur, cfg.source)
        batch = ready_batch(layer, ordered_periods(cfg), requests, runs, now,
                            cfg.pipeline.get("orchestration", {}).get("max_periods_per_batch", 1),
                            set(cfg.pipeline.get("corrections", {})))
        # Mọi kỳ trong lô dùng chung tùy chọn của lần build (ví dụ inject_test_failure, FR-22): cắt lô ở kỳ có tùy chọn khác
        batch = [p for i, p in enumerate(batch)
                 if all(requests[q].options == requests[batch[0]].options for q in batch[:i + 1])]
        claimed = []
        for period in batch:
            cur.execute("INSERT INTO control.layer_run (period, layer, status, dataset, lease_until, airflow_run_id)"
                        " VALUES (%s, %s, 'RUNNING', %s, now() + %s, %s) RETURNING run_id",
                        (period, layer, cfg.source, LEASE, airflow_run_id))
            claimed.append((cur.fetchone()[0], requests[period]))
        return claimed


def finish(run_id: int, status: str, error: str | None = None, counts: dict | None = None) -> None:
    counts = counts or {}
    columns = {k: counts.get(k) for k in ("rows_in", "rows_clean", "rows_rejected", "bronze_orig_rows", "bronze_perf_rows")}
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE control.layer_run SET status = %s, error = %s, finished_at = now(), lease_until = NULL,"
            " duration_s = EXTRACT(EPOCH FROM now() - started_at), details = %s,"
            " rows_in = %s, rows_clean = %s, rows_rejected = %s, bronze_orig_rows = %s, bronze_perf_rows = %s"
            " WHERE run_id = %s",
            (status, error, json.dumps(counts, default=str), *columns.values(), run_id))


def invalidate(cfg: Config, layers: list[str], reason: str) -> int:
    """Đánh dấu SUPERSEDED mọi lần SUCCESS của các tầng phải dựng lại (ví dụ đổi model Raw Vault). Không xóa nhật ký;
    job coi các tầng đó là chưa xong nên make run-all chỉ chạy lại chúng, không chạy lại tầng dưới (PL-03)."""
    unknown = set(layers) - set(LAYERS)
    if unknown:
        raise ValueError(f"Tầng không hợp lệ: {unknown}")
    with connect() as conn, conn.cursor() as cur:
        cur.execute("UPDATE control.layer_run SET status = 'SUPERSEDED', error = %s"
                    " WHERE dataset = %s AND layer = ANY(%s) AND status = 'SUCCESS'", (reason, cfg.source, layers))
        return cur.rowcount


def status(cfg: Config, period: str | None = None) -> list[dict]:
    """Trạng thái từng tầng của các kỳ đã yêu cầu, tính theo yêu cầu mới nhất."""
    with connect() as conn, conn.cursor() as cur:
        requests, runs = _load(cur, cfg.source)
    out = []
    for p in ordered_periods(cfg):
        if p not in requests or (period and p != period):
            continue
        req = requests[p]
        row = {"period": p}
        for layer in LAYERS:
            mine = sorted((r for r in runs if r.period == p and r.layer == layer), key=lambda r: r.started_at)
            failures = sum(1 for r in mine if r.status == "FAILED" and r.started_at >= req.requested_at)
            if _done(runs, requests, p, layer):
                row[layer] = "SUCCESS"
            elif failures >= req.options.get("max_attempts", MAX_ATTEMPTS):
                row[layer] = "GAVE_UP"
            elif mine and mine[-1].status == "RUNNING":
                row[layer] = "RUNNING"
            else:
                row[layer] = "WAITING"
        out.append(row)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Bảng điều khiển pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)
    req = sub.add_parser("request")
    target = req.add_mutually_exclusive_group(required=True)
    target.add_argument("--all", action="store_true", help="Mọi kỳ trong dải của conf (không gồm đợt sửa)")
    target.add_argument("--period")
    req.add_argument("--force", action="store_true", help="Xử lý lại mọi tầng kể cả tầng đã xong")
    req.add_argument("--options", default="{}", help='JSON, ví dụ {"inject_test_failure": true}')
    inv = sub.add_parser("invalidate", help="Đánh dấu các tầng phải dựng lại")
    inv.add_argument("--layers", required=True, help="Danh sách tầng, cách nhau bằng dấu phẩy")
    inv.add_argument("--reason", required=True)
    st = sub.add_parser("status")
    st.add_argument("--period")
    args = parser.parse_args()
    cfg = Config()
    if args.cmd == "invalidate":
        print(f"Đã đánh dấu {invalidate(cfg, args.layers.split(','), args.reason)} lần chạy SUPERSEDED")
    elif args.cmd == "request":
        p = cfg.pipeline["periods"]
        periods = periods_between(p["first"], p["last"]) if args.all else [args.period]
        request(cfg, periods, args.force, json.loads(args.options))
    else:
        print(json.dumps(status(cfg, args.period)))


if __name__ == "__main__":
    sys.exit(main())
