#!/usr/bin/env python3
"""
Publication-quality Figure 14: Change-Point Detection
Target journal: The Cryosphere (EGU) — general Q1 compatible.

Output (default stem: figures/fig_changepoint_vindex — matches main_revised_v2.tex)
  fig_changepoint_vindex.pdf / .eps / .png

Usage
  python fig14_changepoint_publication.py
  python fig14_changepoint_publication.py --data my_vindex.csv --out figures/fig14_changepoint
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from datetime import datetime, timedelta

warnings.filterwarnings("ignore", category=UserWarning)

# ── Paths ───────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[3]
FIGURES = ROOT / "figures"

# ════════════════════════════════════════════════════════════════════════════
#  JOURNAL STYLE
# ════════════════════════════════════════════════════════════════════════════
MM_TO_INCH = 1 / 25.4
DOUBLE_COL_MM = 175
DOUBLE_COL_IN = DOUBLE_COL_MM * MM_TO_INCH

FS_BODY = 8
FS_LABEL = 9
FS_TITLE = 9
FS_PANEL = 9

LW_AXIS = 0.6
LW_GRID = 0.4
LW_DATA = 1.5
LW_MARKER = 0.8
LW_REF = 1.0
LW_ANNOT = 0.8

MS_DATA = 5.5
MS_SAT = 7.0

TOL_BLUE = "#4477AA"
TOL_RED = "#EE6677"
TOL_ORANGE = "#CCBB44"
TOL_PURPLE = "#AA3377"
TOL_GREY = "#BBBBBB"
TOL_GREY_D = "#777777"

ALPHA_SAT = 0.12
ALPHA_FILL = 0.20


def apply_journal_rcparams():
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [
                "Arial",
                "Helvetica Neue",
                "Helvetica",
                "Liberation Sans",
                "DejaVu Sans",
            ],
            "font.size": FS_BODY,
            "axes.titlesize": FS_TITLE,
            "axes.labelsize": FS_LABEL,
            "xtick.labelsize": FS_BODY,
            "ytick.labelsize": FS_BODY,
            "legend.fontsize": FS_BODY,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "axes.linewidth": LW_AXIS,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.facecolor": "white",
            "axes.edgecolor": "#333333",
            "xtick.major.width": LW_AXIS,
            "ytick.major.width": LW_AXIS,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "lines.linewidth": LW_DATA,
            "lines.markersize": MS_DATA,
            "legend.frameon": True,
            "legend.framealpha": 0.92,
            "legend.edgecolor": TOL_GREY,
            "figure.dpi": 150,
            "savefig.dpi": 600,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.02,
            "figure.facecolor": "white",
            "mathtext.fontset": "dejavusans",
        }
    )


def load_data(csv_path=None):
    if csv_path:
        import pandas as pd

        df = pd.read_csv(csv_path, parse_dates=["date"])
        dates = df["date"].tolist()
        vindex = df["vindex"].values.astype(float)
        sigma = df["sigma"].values.astype(float)
        saturated = df["saturated"].values.astype(bool)
        return dates, vindex, sigma, saturated

    raw = [
        ("2025-09-07", "2025-09-13", np.nan, np.nan, True),
        ("2025-09-13", "2025-09-19", 156.7, 38.7, False),
        ("2025-09-19", "2025-09-25", np.nan, np.nan, True),
        ("2025-09-25", "2025-10-01", 177.7, 39.7, False),
        ("2025-10-01", "2025-10-07", 97.0, 49.4, False),
        ("2025-10-07", "2025-10-13", 158.4, 58.3, False),
        ("2025-10-13", "2025-10-19", 72.6, 58.6, False),
        ("2025-10-19", "2025-10-25", 160.1, 49.0, False),
        ("2025-10-25", "2025-10-31", np.nan, np.nan, True),
    ]
    dates, vindex_list, sigma_list, sat_list = [], [], [], []
    for r in raw:
        d1 = datetime.strptime(r[0], "%Y-%m-%d")
        d2 = datetime.strptime(r[1], "%Y-%m-%d")
        mid = d1 + (d2 - d1) / 2
        dates.append(mid)
        vindex_list.append(r[2])
        sigma_list.append(r[3])
        sat_list.append(r[4])
    return (
        dates,
        np.array(vindex_list, dtype=float),
        np.array(sigma_list, dtype=float),
        np.array(sat_list, dtype=bool),
    )


def get_saturated_windows(dates, saturated):
    windows = []
    for d, s in zip(dates, saturated):
        if s:
            half = timedelta(days=3)
            windows.append((d - half, d + half))
    return windows


def add_grid(ax, axis="y", color=TOL_GREY, lw=LW_GRID, alpha=0.6, zorder=0):
    ax.grid(True, axis=axis, color=color, linewidth=lw, linestyle=":", alpha=alpha, zorder=zorder)


def panel_label(ax, label, x=-0.10, y=1.04, fontsize=FS_PANEL, bold=True):
    ax.text(
        x,
        y,
        label,
        transform=ax.transAxes,
        fontsize=fontsize,
        fontweight="bold" if bold else "normal",
        va="bottom",
        ha="right",
    )


def clean_spines(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_linewidth(LW_AXIS)
        ax.spines[spine].set_color("#333333")


def plot_vindex_panel(
    ax,
    dates,
    vindex,
    sigma,
    saturated,
    terminus_rate=57.6,
    slow_surge_threshold=30.0,
    detection_limit=333.0,
):
    sat_windows = get_saturated_windows(dates, saturated)
    for ws, we in sat_windows:
        ax.axvspan(ws, we, color=TOL_RED, alpha=ALPHA_SAT, zorder=1, linewidth=0)

    t_start = datetime(2025, 9, 6)
    t_end = datetime(2025, 11, 3)

    ax.axhline(terminus_rate, color=TOL_ORANGE, lw=LW_REF, ls=(0, (6, 3)), zorder=3)
    ax.text(
        t_end + timedelta(days=0.4),
        terminus_rate,
        f"Terminus\nlower bound\n({terminus_rate:.1f} m d$^{{-1}}$)",
        color=TOL_ORANGE,
        fontsize=FS_BODY - 0.5,
        va="center",
        ha="left",
        linespacing=1.3,
    )

    # Plot the three terminus displacement observations as filled triangles
    terminus_dates = [
        datetime(2025, 9, 12),
        datetime(2025, 9, 17),
        datetime(2025, 10, 25),
    ]
    terminus_rates = [0, 60.0, 57.6]  # cumulative rate from Sep 12 anchor
    # Show as downward triangles at the measured rate, with error bars
    ax.errorbar(
        terminus_dates,
        terminus_rates,
        yerr=[0, 1.7, 0.2],  # rate uncertainties from Table 14
        fmt="v",
        color=TOL_ORANGE,
        ecolor=TOL_ORANGE,
        elinewidth=1.2,
        capsize=3,
        markersize=7,
        markeredgecolor="white",
        markeredgewidth=0.8,
        zorder=7,
        label=r"Terminus displacement rate ($\pm$1$\sigma$)",
    )

    ax.axhline(slow_surge_threshold, color=TOL_GREY_D, lw=LW_REF * 0.7, ls=":", zorder=3)
    ax.text(
        datetime(2025, 9, 9),
        slow_surge_threshold + 8,
        "Slow-surge threshold",
        color=TOL_GREY_D,
        fontsize=FS_BODY - 0.5,
        va="bottom",
    )

    sat_dates = [d for d, s in zip(dates, saturated) if s]
    for sd in sat_dates:
        ax.plot(
            sd,
            detection_limit,
            marker=r"$\uparrow$",
            ms=MS_SAT,
            color=TOL_RED,
            zorder=7,
            markeredgewidth=0,
        )

    valid = ~saturated & ~np.isnan(vindex)
    vd = [d for d, v in zip(dates, valid) if v]
    vi = vindex[valid]
    sig = sigma[valid]

    ax.errorbar(
        vd,
        vi,
        yerr=sig,
        fmt="o",
        color=TOL_BLUE,
        ecolor=TOL_BLUE,
        elinewidth=LW_DATA * 0.7,
        capsize=3.0,
        capthick=LW_DATA * 0.7,
        markersize=MS_DATA,
        markeredgewidth=LW_MARKER,
        markeredgecolor="white",
        markerfacecolor=TOL_BLUE,
        zorder=6,
        label=r"$V_\mathrm{index}$ ± 1$\sigma$ (NMAD)",
        clip_on=False,
    )

    if len(vd) > 1:
        vd_num = mdates.date2num(vd)
        ax.fill_between(
            vd_num,
            vi - sig,
            vi + sig,
            color=TOL_BLUE,
            alpha=ALPHA_FILL * 0.5,
            zorder=2,
            linewidth=0,
        )

    min_idx = int(np.argmin(vi))
    min_date, min_vi = vd[min_idx], vi[min_idx]
    ax.annotate(
        f"Minimum valid\n$V_{{\\mathrm{{index}}}}$ = {min_vi:.1f} m d$^{{-1}}$",
        xy=(min_date, min_vi),
        xytext=(min_date - timedelta(days=14), min_vi + 70),
        fontsize=FS_BODY - 0.5,
        color=TOL_BLUE,
        ha="center",
        arrowprops=dict(
            arrowstyle="->", color=TOL_BLUE, lw=LW_ANNOT, connectionstyle="arc3,rad=-0.15"
        ),
        zorder=9,
    )

    ax.set_xlim(t_start, t_end + timedelta(days=8))
    ax.set_ylim(-30, 420)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(100))
    ax.yaxis.set_minor_locator(mticker.MultipleLocator(25))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.xaxis.set_minor_locator(mdates.DayLocator(interval=2))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=35, ha="right", fontsize=FS_BODY)

    ax.set_ylabel("Velocity (m d$^{-1}$)", fontsize=FS_LABEL)
    add_grid(ax, "y")
    add_grid(ax, "x", alpha=0.25)
    clean_spines(ax)

    legend_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=TOL_BLUE,
            markersize=MS_DATA,
            markeredgecolor="white",
            markeredgewidth=LW_MARKER,
            label=r"$V_\mathrm{index}$ ± 1$\sigma$ (NMAD)",
        ),
        Line2D(
            [0],
            [0],
            marker=r"$\uparrow$",
            color="w",
            markerfacecolor=TOL_RED,
            markersize=MS_SAT,
            label=f"Saturated pair ($V \\geq {detection_limit:.0f}$ m d$^{{-1}}$)",
        ),
        Line2D(
            [0],
            [0],
            color=TOL_ORANGE,
            lw=LW_REF,
            linestyle=(0, (6, 3)),
            label=f"Terminus lower bound ({terminus_rate:.1f} m d$^{{-1}}$)",
        ),
        Line2D(
            [0],
            [0],
            marker="v",
            linestyle="None",
            color=TOL_ORANGE,
            markerfacecolor=TOL_ORANGE,
            markeredgecolor="white",
            markeredgewidth=0.8,
            markersize=7,
            label=r"Terminus displacement rate ($\pm$1$\sigma$)",
        ),
        Patch(color=TOL_RED, alpha=ALPHA_SAT * 2, label="Saturated pair window"),
    ]
    leg = ax.legend(
        handles=legend_handles,
        loc="upper right",
        fontsize=FS_BODY,
        framealpha=0.92,
        edgecolor=TOL_GREY,
        handlelength=1.6,
        borderpad=0.5,
    )
    leg.get_frame().set_linewidth(LW_AXIS)

    panel_label(ax, "(a)")
    ax.set_title(
        "De-biased $V_\\mathrm{index}$ time series — PELT: 0 change-points "
        r"($\beta \in \{1, 2, 3, 4, 5, 10, 20, 50, 100\}$)",
        fontsize=FS_TITLE,
        loc="left",
        pad=4,
    )


def plot_penalty_panel(ax, n_valid_pairs=6):
    penalties = [1, 2, 3, 4, 5, 10, 20, 50, 100]
    n_changepoints = [0] * len(penalties)

    ax.plot(
        penalties,
        n_changepoints,
        "s-",
        color=TOL_PURPLE,
        lw=LW_DATA,
        ms=MS_DATA,
        markeredgewidth=LW_MARKER,
        markeredgecolor="white",
        markerfacecolor=TOL_PURPLE,
        zorder=5,
        clip_on=False,
    )

    ax.text(
        50,
        0.85,
        f"0 change-points at all $\\beta$ values\n"
        f"Power-limited: $n = {n_valid_pairs}$ non-saturated pairs\n"
        r"Zero detections $\neq$ absence of regime changes",
        fontsize=FS_BODY - 0.5,
        color=TOL_PURPLE,
        ha="center",
        va="bottom",
        linespacing=1.45,
        bbox=dict(
            boxstyle="round,pad=0.35",
            facecolor="white",
            edgecolor=TOL_PURPLE,
            linewidth=LW_AXIS,
            alpha=0.90,
        ),
    )

    ax.set_xlim(-2, 108)
    ax.set_ylim(-0.25, 2.8)
    ax.set_yticks([0, 1, 2])
    ax.set_xticks(penalties)
    ax.set_xlabel("Penalty parameter ($\\beta$)", fontsize=FS_LABEL)
    ax.set_ylabel("Number of\nchange-points", fontsize=FS_LABEL)
    add_grid(ax, "y", alpha=0.4)
    clean_spines(ax)
    panel_label(ax, "(b)")
    ax.set_title(
        f"PELT penalty sensitivity — power-limited ($n = {n_valid_pairs}$)",
        fontsize=FS_TITLE,
        loc="left",
        pad=4,
    )


def make_figure14(csv_path=None, out_stem: Path | str | None = None):
    apply_journal_rcparams()

    dates, vindex, sigma, saturated = load_data(csv_path)
    n_valid = int((~saturated & ~np.isnan(vindex)).sum())

    if out_stem is None:
        out_stem = FIGURES / "fig_changepoint_vindex"
    out_stem = Path(out_stem)
    out_stem.parent.mkdir(parents=True, exist_ok=True)

    fig_w = DOUBLE_COL_IN
    fig_h = fig_w * 0.62

    fig, axes = plt.subplots(
        2,
        1,
        figsize=(fig_w, fig_h),
        gridspec_kw={"height_ratios": [2.6, 1.0], "hspace": 0.42},
    )

    fig.subplots_adjust(left=0.09, right=0.78, top=0.93, bottom=0.12)

    ax1, ax2 = axes
    plot_vindex_panel(ax1, dates, vindex, sigma, saturated)
    plot_penalty_panel(ax2, n_valid_pairs=n_valid)

    for ext, dpi in [(".pdf", None), (".eps", None), (".png", 600)]:
        kwargs = dict(bbox_inches="tight", pad_inches=0.02)
        if dpi:
            kwargs["dpi"] = dpi
        p = out_stem.with_suffix(ext)
        fig.savefig(p, **kwargs)
        print(f"  Saved: {p}")

    plt.close(fig)
    print("Figure 14 complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate publication-quality Figure 14 (change-point detection)."
    )
    parser.add_argument("--data", default=None, help="CSV: date,vindex,sigma,saturated")
    parser.add_argument(
        "--out",
        default=None,
        help="Output stem without extension (default: figures/fig_changepoint_vindex)",
    )
    args = parser.parse_args()
    make_figure14(csv_path=args.data, out_stem=args.out)
