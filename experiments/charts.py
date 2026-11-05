"""Biểu đồ thực nghiệm C5 (R-38) từ experiments/results/*.csv: trung vị 3 lần đo, vạch min–max.

Bảng màu: ba vị trí đầu của bảng màu tham chiếu (đã kiểm mọi cặp, chế độ sáng); aqua dưới 3:1 nên mọi cột có
nhãn giá trị. Một trục y mỗi biểu đồ; hai đại lượng khác thang đo thì tách hai biểu đồ con.

Chạy: uv run python -m experiments.charts
"""
import csv
from collections import defaultdict
from statistics import median

import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from experiments.run import RESULTS, TN2_CHECKPOINTS  # noqa: E402

SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
SURFACE, TEXT, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
    "text.color": TEXT, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 10, "axes.titlesize": 12,
    "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.titlepad": 24, "legend.frameon": False,
})


def load(name: str) -> list[dict]:
    with (RESULTS / f"{name}.csv").open() as f:
        return [r for r in csv.DictReader(f)]


def measured(data: list[dict]) -> list[dict]:
    return [r for r in data if r.get("warmup") != "True"]


def stats(values: list[float]) -> tuple[float, float, float]:
    return median(values), min(values), max(values)


def fmt(v: float) -> str:
    text = f"{v:,.2f}" if v < 10 else f"{v:,.1f}" if v < 100 else f"{v:,.0f}"
    return text.replace(",", " ").replace(".", ",")


def legend_on_top(ax, handles=None, labels=None) -> None:
    """Chú giải nằm trên vùng vẽ, bên phải tiêu đề, không đè lên cột."""
    args = (handles, labels) if handles else ()
    ax.legend(*args, loc="lower right", bbox_to_anchor=(1, 1.0), ncol=4, fontsize=9)


def grouped_bars(ax, groups: list[str], series: dict[str, list[list[float]]], unit: str = "giây",
                 label_size: int = 8) -> None:
    """Cột nhóm, mỗi series một màu theo thứ tự cố định; trung vị kèm vạch min–max và nhãn giá trị."""
    n = len(series)
    width = 0.8 / n
    for i, (name, per_group) in enumerate(series.items()):
        xs = [g + (i - (n - 1) / 2) * width for g in range(len(groups))]
        meds = [stats(v) for v in per_group]
        heights = [m[0] for m in meds]
        err = [[m[0] - m[1] for m in meds], [m[2] - m[0] for m in meds]]
        ax.bar(xs, heights, width * 0.92, color=SERIES[i], label=name, edgecolor=SURFACE, linewidth=2)
        ax.errorbar(xs, heights, yerr=err, fmt="none", ecolor=TEXT, elinewidth=1, capsize=3)
        for x, h, top in zip(xs, heights, [m[2] for m in meds]):
            ax.annotate(fmt(h), (x, top), textcoords="offset points", xytext=(0, 3), ha="center", fontsize=label_size, color=TEXT)
    ax.set_xticks(range(len(groups)), groups)
    ax.set_ylabel(unit)
    if n > 1:
        legend_on_top(ax)


def save(fig, name: str, note: str) -> None:
    comma = matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}".replace(".", ","))
    for ax in fig.axes:
        ax.yaxis.set_major_formatter(comma)
        if ax.get_xlabel() == "MiB":
            ax.xaxis.set_major_formatter(comma)
    fig.text(0.01, 0.01, note, fontsize=8, color=MUTED, ha="left")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(RESULTS / f"{name}.png", dpi=150)
    plt.close(fig)


NOTE = "Trung vị 3 lần đo, vạch là min–max. Nguồn: experiments/results/"


def tn1() -> None:
    data = load("tn1_scale")
    subsets = ["p25", "p50", "p100"]
    labels = {s: f"{s[1:]}%\n{int(next(r for r in data if r['subset'] == s)['source_perf']) / 1e6:.2f} tr dòng"
              .replace(".", ",") for s in subsets}
    fig, (left, right) = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1, 1.6]})
    grouped_bars(left, [labels[s] for s in subsets],
                 {"End-to-end": [[float(r["end_to_end_s"]) for r in data if r["subset"] == s] for s in subsets]})
    left.set_title("TN1. Thời gian toàn pipeline theo quy mô")
    left.tick_params(axis="x", labelsize=9)
    layers = ["ingest", "quality", "raw_vault", "business_vault", "gold", "export"]
    grouped_bars(right, layers, {f"{s[1:]}%": [[float(r[f"{l}_s"]) for r in data if r["subset"] == s]
                                             for l in layers] for s in subsets}, label_size=7)
    right.set_title("Thời gian bận từng tầng (control.layer_run)")
    save(fig, "tn1_scale", NOTE + "tn1_scale.csv. Mỗi lần đo dựng stack và lake mới.")


def tn2() -> None:
    data = measured(load("tn2_incremental"))
    fig, ax = plt.subplots(figsize=(8, 4.6))
    for i, method in enumerate(("incremental", "full_refresh")):
        points = [k for k in TN2_CHECKPOINTS if any(int(r["periods_loaded"]) == k for r in data)]
        meds = [stats([float(r["wall_s"]) for r in data if r["method"] == method and int(r["periods_loaded"]) == k])
                for k in points]
        ys = [m[0] for m in meds]
        ax.plot(points, ys, color=SERIES[i], linewidth=2, marker="o", markersize=8,
                markeredgecolor=SURFACE, markeredgewidth=2, label={"incremental": "Incremental (1 kỳ mới)",
                                                                    "full_refresh": "Full refresh (mọi kỳ)"}[method])
        ax.fill_between(points, [m[1] for m in meds], [m[2] for m in meds], color=SERIES[i], alpha=0.15, linewidth=0)
        ax.annotate(fmt(ys[-1]), (points[-1], ys[-1]), textcoords="offset points", xytext=(6, 0),
                    va="center", fontsize=8, color=TEXT)
    ax.set_xticks(TN2_CHECKPOINTS)
    ax.set_xlabel("số kỳ đã có trong Raw Vault sau lần nạp")
    ax.set_ylabel("giây (dbt run Raw Vault gồm staging)")
    ax.set_ylim(bottom=0)
    legend_on_top(ax)
    ax.set_title("TN2. Nạp Raw Vault: incremental so với full refresh")
    save(fig, "tn2_incremental", "Trung vị 3 lần đo, dải màu là min–max. Nguồn: experiments/results/tn2_incremental.csv.")


def tn4() -> None:
    data = measured(load("tn4_pit"))
    scenarios = {"all_months": "Mọi khoản vay × mọi tháng", "one_month": "Một mốc (07/2020)"}
    fig, ax = plt.subplots(figsize=(8, 4.6))
    grouped_bars(ax, list(scenarios.values()),
                 {label: [[float(r["seconds"]) for r in data if r["scenario"] == s and r["method"] == m] for s in scenarios]
                  for m, label in (("pit", "PIT (equi-join)"), ("direct", "Join as-of trực tiếp"))})
    ax.set_title("TN4. Truy vấn trạng thái tại mốc thời gian, 4 Satellite")
    save(fig, "tn4_pit", NOTE + "tn4_pit.csv. Hai cách cùng checksum.")


def tn6() -> None:
    storage = load("tn6_storage")
    fig, (left, right) = plt.subplots(1, 2, figsize=(12, 4.6))
    names = [r["table"].replace("exp_", "").replace("sat_loan_", "") for r in storage]
    colors = [SERIES[0] if r["design"] == "split" else SERIES[1] for r in storage]
    for ax, field, scale, unit, title in ((left, "rows", 1e6, "triệu dòng", "TN6. Số dòng"),
                                          (right, "size_bytes", 2 ** 20, "MiB", "Dung lượng Delta")):
        values = [int(r[field]) / scale for r in storage]
        ax.bar(names, values, color=colors, edgecolor=SURFACE, linewidth=2)
        for x, v in enumerate(values):
            ax.annotate(fmt(v) if v >= 1 else f"{v:.3f}".replace(".", ","), (x, v), textcoords="offset points",
                        xytext=(0, 3), ha="center", fontsize=8)
        ax.set_ylabel(unit)
        ax.set_title(title)
    handles = [plt.Rectangle((0, 0), 1, 1, color=SERIES[i]) for i in range(2)]
    legend_on_top(right, handles, ["3 Satellite tách", "1 Satellite gộp"])
    save(fig, "tn6_split", "Nguồn: experiments/results/tn6_storage.csv (snapshot hiện hành, DESCRIBE DETAIL).")


def tn7() -> None:
    data = measured(load("tn7_bronze_slice"))
    periods = sorted({r["period"] for r in data})
    fig, (left, right) = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1.6, 1]})
    grouped_bars(left, periods, {label: [[float(r["seconds"]) for r in data if r["period"] == p and r["method"] == m]
                                         for p in periods]
                                 for m, label in (("txt_direct", "Đọc thẳng TXT"), ("landing", "Landing Delta"))})
    left.set_title("TN7. Cắt lát Bronze một kỳ")
    reader = measured(load("tn7_reader"))
    build = measured(load("tn7_landing_build"))
    steps = [("Đọc perf\ntext + split", [float(r["seconds"]) for r in reader if r["method"] == "text_split"]),
             ("Đọc perf\nreader CSV", [float(r["seconds"]) for r in reader if r["method"] == "csv_reader"]),
             ("Dựng landing\n(một lần)", [float(r["seconds"]) for r in build])]
    grouped_bars(right, [s for s, _ in steps], {"": [v for _, v in steps]})
    right.set_title("Reader và chi phí dựng landing")
    save(fig, "tn7_ingestion", NOTE + "tn7_*.csv.")
    storage = [r for r in load("tn7_storage")]
    fig, ax = plt.subplots(figsize=(9, 8))
    labels = [r["table"] for r in storage][::-1]
    values = [int(r["size_bytes"]) / 2 ** 20 for r in storage][::-1]
    ax.barh(labels, values, color=SERIES[0], edgecolor=SURFACE, linewidth=2)
    for y, v in enumerate(values):
        ax.annotate(fmt(v), (v, y), textcoords="offset points", xytext=(4, 0), va="center", fontsize=8)
    ax.set_xlabel("MiB")
    ax.tick_params(axis="y", labelsize=8)
    ax.set_title("TN7. Dung lượng từng bảng từ TXT tới Gold")
    save(fig, "tn7_storage", "Nguồn: experiments/results/tn7_storage.csv. Delta: snapshot hiện hành (DESCRIBE DETAIL).")


def main() -> None:
    for chart in (tn1, tn2, tn4, tn6, tn7):
        try:
            chart()
            print(f"Đã vẽ {chart.__name__}")
        except FileNotFoundError as exc:
            print(f"Bỏ qua {chart.__name__}: thiếu {exc.filename}")


if __name__ == "__main__":
    main()
