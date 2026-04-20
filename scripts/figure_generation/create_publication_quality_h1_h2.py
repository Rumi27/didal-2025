#!/usr/bin/env python3
"""
Generate updated H1/H2 figure:

(a) Velocity time series
    - 6-day cross-track raw (with saturated/failed pairs flagged)
    - 6-day Vindex debiased ± empirical sigma (stable-ground)
    - 12-day same-track Orbit1/Orbit2 debiased ± sigma (if available)

(b) ROS occurrence (computed here) and precipitation anomalies (same window)

Outputs:
  processed_data/h1_h2_analysis/h1_h2_analysis_updated.png
  processed_data/h1_h2_analysis/h1_h2_analysis_updated.pdf
"""

import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from datetime import timedelta
import warnings
warnings.filterwarnings("ignore")

# -----------------------
# Paths (match your repo)
# -----------------------
CROSS_TRACK_6D_CSV = Path("satellite_data/sentinel1/processed/velocity_timeseries_python.csv")
VINDEX_6D_CSV = Path("processed_data/stable_ground_debiasing/vindex_before_after.csv")
ORBIT1_12D_CSV = Path("processed_data/same_track_12day_comparison/orbit1_12day_debiased.csv")
ORBIT2_12D_CSV = Path("processed_data/same_track_12day_comparison/orbit2_12day_debiased.csv")
CLIMATE_CSV = Path("satellite_data/era5_land/processed/climate_derivatives_timeseries.csv")

OUT_DIR = Path("processed_data/h1_h2_analysis")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PNG = OUT_DIR / "h1_h2_analysis_updated.png"
OUT_PDF = OUT_DIR / "h1_h2_analysis_updated.pdf"

# Saturation rule for 6-day cross-track
SATURATION_PX_LIMIT = 200  # your original search limit in px

# Style
DPI = 600
FIGSIZE = (12, 10)  # Increased from (7.2, 7.2) for better readability
MONTH_ABBR_EN = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

def fmt_day_mon_en(x, pos=None):
    d = mdates.num2date(x)
    return f"{d.day:02d} {MONTH_ABBR_EN[d.month-1]}"

def require_file(p: Path):
    if not p.exists():
        raise FileNotFoundError(f"Missing file: {p}")

def load_cross_track_6d():
    require_file(CROSS_TRACK_6D_CSV)
    df = pd.read_csv(CROSS_TRACK_6D_CSV)
    # expected: date, date1, date2, velocity_m_per_day, row_offset_px, col_offset_px, correlation
    for c in ["date", "date1", "date2"]:
        df[c] = pd.to_datetime(df[c])
    df = df.sort_values("date").reset_index(drop=True)

    df["is_saturated"] = (
        df["correlation"].fillna(0) <= 0
        ) | (df["row_offset_px"].abs() >= SATURATION_PX_LIMIT
        ) | (df["col_offset_px"].abs() >= SATURATION_PX_LIMIT)
    return df

def load_vindex_6d():
    """
    Expect columns like:
      date1, date2, vindex_m_per_day_debiased, vindex_sigma_m_per_day
    If your column names differ, adjust mapping below.
    """
    require_file(VINDEX_6D_CSV)
    v = pd.read_csv(VINDEX_6D_CSV)
    v["date1"] = pd.to_datetime(v["date1"])
    v["date2"] = pd.to_datetime(v["date2"])
    v["date_mid"] = v["date1"] + (v["date2"] - v["date1"]) / 2

    # Column mapping (robust)
    y_candidates = ["vindex_m_per_day_debiased", "vindex_debiased", "vindex_debiased_m_per_day"]
    s_candidates = ["vindex_sigma_m_per_day", "vindex_sigma", "sigma_m_per_day"]

    ycol = next((c for c in y_candidates if c in v.columns), None)
    scol = next((c for c in s_candidates if c in v.columns), None)

    if ycol is None:
        raise KeyError(f"Could not find debiased Vindex column in {VINDEX_6D_CSV}. "
                       f"Tried: {y_candidates}. Found: {list(v.columns)}")
    if scol is None:
        raise KeyError(f"Could not find Vindex sigma column in {VINDEX_6D_CSV}. "
                       f"Tried: {s_candidates}. Found: {list(v.columns)}")

    v = v.rename(columns={ycol: "vindex_debiased", scol: "vindex_sigma"})
    return v[["date1","date2","date_mid","vindex_debiased","vindex_sigma"]].sort_values("date_mid")

def load_same_track_12d(p: Path, label: str):
    require_file(p)
    df = pd.read_csv(p)
    df["date1"] = pd.to_datetime(df["date1"])
    df["date2"] = pd.to_datetime(df["date2"])
    df["date_mid"] = df["date1"] + (df["date2"] - df["date1"]) / 2

    # Prefer Vindex if present; fallback to glacier_speed
    if "vindex_m_per_day_debiased" in df.columns:
        y = df["vindex_m_per_day_debiased"].astype(float)
        s = df.get("vindex_sigma_m_per_day", np.nan)
    else:
        y = df["glacier_speed_m_per_day_debiased"].astype(float)
        s = df.get("glacier_speed_sigma_m_per_day", np.nan)

    out = pd.DataFrame({
        "date1": df["date1"], "date2": df["date2"], "date_mid": df["date_mid"],
        "y": y, "sigma": pd.to_numeric(s, errors="coerce"), "status": df.get("stable_ground_status", "unknown")
    })
    out["series"] = label
    return out.sort_values("date_mid")

def load_climate_daily():
    require_file(CLIMATE_CSV)
    c = pd.read_csv(CLIMATE_CSV)
    c["datetime"] = pd.to_datetime(c["datetime"])
    c = c.sort_values("datetime").reset_index(drop=True)

    # if hourly, aggregate
    if len(c) > 370:
        c["date"] = c["datetime"].dt.date
        cd = c.groupby("date").agg(
            temperature_C=("temperature_C","mean"),
            precipitation_mm=("precipitation_mm","sum"),
            swe_mm=("swe_mm","mean"),
        ).reset_index()
        cd["datetime"] = pd.to_datetime(cd["date"])
    else:
        cd = c.copy()

    # compute ROS occurrence HERE (transparent)
    # ROS day: T>0.5C, P>0.1mm, SWE>0.1mm
    cd["ros"] = ((cd["temperature_C"] > 0.5) & (cd["precipitation_mm"] > 0.1) & (cd["swe_mm"] > 0.1)).astype(int)
    return cd

def main():
    vel6 = load_cross_track_6d()
    vindex6 = load_vindex_6d()
    orb1 = load_same_track_12d(ORBIT1_12D_CSV, "12-day same-track Orbit1")
    orb2 = load_same_track_12d(ORBIT2_12D_CSV, "12-day same-track Orbit2")
    clim = load_climate_daily()

    # Window to plot (based on 6-day pairs)
    start = min(vel6["date1"].min(), vindex6["date1"].min()) - pd.Timedelta(days=6)
    end = max(vel6["date2"].max(), vindex6["date2"].max()) + pd.Timedelta(days=6)
    clim_win = clim[(clim["datetime"] >= start) & (clim["datetime"] <= end)].copy()

    # precip anomaly relative to annual mean
    precip_mean = float(clim["precipitation_mm"].mean())
    clim_win["precip_anom_mm"] = clim_win["precipitation_mm"] - precip_mean

    # -----------------------
    # Plot
    # -----------------------
    colors = dict(
        raw="#2E86AB",
        sat="#C73E1D",
        shade="#C73E1D",
        vindex="black",
        orbit1="#2D6A4F",
        orbit2="#A23B72",
        precip="#6C757D",
        ros="#2D6A4F",
        grid="#E0E0E0",
        decorr="#B0B0B0", # Grey for decorrelated/unreliable data
    )

    fig = plt.figure(figsize=FIGSIZE, dpi=120)
    gs = fig.add_gridspec(2, 1, height_ratios=[1.15, 0.85], hspace=0.3)

    # ---- (a) velocity
    ax1 = fig.add_subplot(gs[0, 0])
    # ---- (b) precip anomaly + ROS (share x)
    ax2 = fig.add_subplot(gs[1, 0], sharex=ax1)

    sat = vel6[vel6["is_saturated"]].copy()
    non_sat = vel6[~vel6["is_saturated"]].copy()
    
    # 1. Plot Velocity Data (ax1)
    # Shade ALL 6-day velocity pair intervals (non-saturated: light gray; saturated: red)
    for _, r in non_sat.iterrows():
        ax1.axvspan(r["date1"], r["date2"], alpha=0.08, color="#CCCCCC", linewidth=0, zorder=0)
    for _, r in sat.iterrows():
        ax1.axvspan(r["date1"], r["date2"], alpha=0.15, color=colors["shade"], linewidth=0, zorder=0)

    # 6-day Cross-track raw
    ax1.plot(vel6["date"], vel6["velocity_m_per_day"], "-", color=colors["raw"], alpha=0.85, label="6-day cross-track (raw)")
    ax1.scatter(vel6["date"], vel6["velocity_m_per_day"], s=55, facecolors="white", edgecolors=colors["raw"], linewidths=1.8, zorder=3)

    if len(sat) > 0:
        ax1.scatter(sat["date"], sat["velocity_m_per_day"], s=80, marker="x", color=colors["sat"], linewidths=2.2, zorder=4,
                    label="Saturated/failed pair (6-day raw)")

    # 6-day debiased Vindex ± sigma
    ax1.errorbar(
        vindex6["date_mid"], vindex6["vindex_debiased"], yerr=vindex6["vindex_sigma"],
        fmt="o", color=colors["vindex"], ecolor=colors["vindex"], elinewidth=1.6,
        capsize=4, markersize=8, label="6-day Vindex (debiased ± empirical σ)", zorder=5
    )

    # 12-day same-track (Decorrelated/Unreliable)
    for df, m, lab in [
        (orb1, "s", "12-day same-track Orbit1 (decorrelated/unreliable)"),
        (orb2, "^", "12-day same-track Orbit2 (decorrelated/unreliable)"),
    ]:
        df_ok = df[df["status"].astype(str).eq("ok")].copy()
        if len(df_ok) == 0:
            continue
        ax1.errorbar(
            df_ok["date_mid"], df_ok["y"], yerr=df_ok["sigma"],
            fmt=m, color=colors["decorr"], ecolor=colors["decorr"], elinewidth=1.4, capsize=3,
            markersize=6, markerfacecolor="none", markeredgewidth=1.5, label=lab, zorder=2
        )

    ax1.set_ylabel("Velocity (m d$^{-1}$)", fontsize=18)
    ax1.set_title("(a) Velocity time series (sampled at pair midpoints; shaded regions = SAR pair windows)", loc="left", pad=10, fontsize=20)
    ax1.tick_params(axis='both', which='major', labelsize=16)
    ax1.grid(True, alpha=0.3, linestyle="--", linewidth=0.8, color=colors["grid"])
    # X-axis handling moved to end for consistency

    # 2. Plot Climate Data (ax2)
    # Shade ALL velocity pair intervals (same as panel a) to show SAR pair windows
    for _, r in non_sat.iterrows():
        ax2.axvspan(r["date1"], r["date2"], alpha=0.08, color="#CCCCCC", linewidth=0, zorder=0)
    for _, r in sat.iterrows():
        ax2.axvspan(r["date1"], r["date2"], alpha=0.15, color=colors["shade"], linewidth=0, zorder=0)
    
    ax2.bar(
        clim_win["datetime"], clim_win["precip_anom_mm"], width=0.85,
        color=colors["precip"], alpha=0.35, edgecolor="none", label="Precipitation anomaly (mm)", zorder=1
    )
    ax2.axhline(0, color="#444444", linewidth=1.0, alpha=0.8, zorder=2)

    ax2r = ax2.twinx()
    ros_dates = clim_win.loc[clim_win["ros"].astype(int) == 1, "datetime"]
    if len(ros_dates) > 0:
        ax2r.scatter(ros_dates, np.ones(len(ros_dates)), marker="|", s=350, color=colors["ros"], linewidths=3.0, label="ROS day", zorder=4)
    ax2r.set_ylim(-0.05, 1.25)
    ax2r.set_yticks([0, 1])
    ax2r.set_ylabel("ROS occurrence (0/1)", fontsize=18)
    ax2r.tick_params(axis='both', which='major', labelsize=16)

    ax2.set_ylabel("Precipitation anomaly (mm)", fontsize=18)
    ax2.set_xlabel("Date", fontsize=18)
    ax2.set_title("(b) Daily ROS occurrence and precipitation anomalies (shaded regions = SAR pair windows)", loc="left", pad=10, fontsize=20)
    ax2.tick_params(axis='both', which='major', labelsize=16)
    # Identical x-limits
    ax1.set_xlim(start, end)
    ax2.set_xlim(start, end)
    # Identical formatters/locators (every 6 days to match velocity sampling)
    for ax in (ax1, ax2):
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_day_mon_en))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=6))

    # Hide x-labels on top panel to prevent overlap
    plt.setp(ax1.get_xticklabels(), visible=False)

     # Legends (inside, upper right)
    ax1.legend(loc='upper right', frameon=True, framealpha=0.95, edgecolor='none', fontsize=16)
    
    h1, l1 = ax2.get_legend_handles_labels()
    h2, l2 = ax2r.get_legend_handles_labels()
    ax2.legend(h1 + h2, l1 + l2, loc='upper right', frameon=True, framealpha=0.95, edgecolor='none', fontsize=16)

    plt.savefig(OUT_PNG, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.savefig(OUT_PDF, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"Saved: {OUT_PNG}")
    print(f"Saved: {OUT_PDF}")

if __name__ == "__main__":
    main()
