#!/usr/bin/env python3
"""
Bias correction of ERA5-Land data using Javshangoz station observations.

Implements:
1. Terink temperature correction (Terink et al., 2010)
2. Monthly mean scaling for precipitation
3. Optional: LOCI method for precipitation (future work)

Input: Excel file with ERA5-Land and station data
Output: Bias-corrected time series and validation plots
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from datetime import datetime

# ==========================================
# CONFIGURATION
# ==========================================
# Input files (actual data in this project)
ERA5_CSV = Path("satellite_data/era5_land/processed/climate_derivatives_timeseries.csv")
STATION_XLS = Path("actual station measurmetns/open source/38744.01.02.2005.15.01.2026.1.0.0.ru.utf8.00000000.xls")

# Output directory
OUTPUT_DIR = Path("processed_data/bias_correction")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Reference period for calibration
# NOTE: We only have ERA5-Land for 2025 in this project, so we use the
# full overlapping 2025 period as the reference instead of 2000–2019.
REF_START = "2025-01-01"
REF_END = "2025-12-31"

# Unified column names used later in the script
DATE_COL_ERA = "Data time"
T_ERA_COL = "temp(degC)"
P_ERA_COL = "prec(mm)"

DATE_COL_OBS = "Date"
T_OBS_COL = "Javshangoz temp"   # actually Lakhsh station temperature
P_OBS_COL = "Precipitation"     # actually Lakhsh station precipitation

# ==========================================
# 1. READ & MERGE DATA (ERA5-LAND + LAKHSH STATION)
# ==========================================
print("=" * 70)
print("ERA5-LAND BIAS CORRECTION")
print("=" * 70)
print(f"\nReading ERA5-Land CSV: {ERA5_CSV}")
print(f"Reading station XLS:   {STATION_XLS}")

if not ERA5_CSV.exists():
    print(f"❌ ERA5-Land file not found: {ERA5_CSV}")
    exit(1)

if not STATION_XLS.exists():
    print(f"❌ Station file not found: {STATION_XLS}")
    exit(1)

# ---- ERA5-Land (from climate_derivatives_timeseries.csv) ----
df_era_raw = pd.read_csv(ERA5_CSV)
df_era_raw["datetime"] = pd.to_datetime(df_era_raw["datetime"])

# Aggregate ERA5 to daily values (mean T, sum P)
df_era_daily = (
    df_era_raw
    .set_index("datetime")
    .resample("D")
    .agg({
        "temperature_C": "mean",
        "precipitation_mm": "sum",
    })
    .reset_index()
)

df_era_daily = df_era_daily.rename(columns={
    "datetime": DATE_COL_ERA,
    "temperature_C": T_ERA_COL,
    "precipitation_mm": P_ERA_COL,
})

print(f"✅ ERA5-Land daily series: {len(df_era_daily)} days "
      f"from {df_era_daily[DATE_COL_ERA].min()} to {df_era_daily[DATE_COL_ERA].max()}")

# ---- Lakhsh station (hourly) ----
# Header row is at index 6 (row 7 in Excel), as inspected earlier
df_station_raw = pd.read_excel(STATION_XLS, sheet_name=0, header=6)

# Parse local time, temperature T (°C), and RRR (precipitation code)
station_time_col = "Местное время в Лахше"
station_t_col = "T"
station_p_col = "RRR"

df_station_raw[station_time_col] = pd.to_datetime(
    df_station_raw[station_time_col],
    dayfirst=True,
    errors="coerce",
)

# Ensure numeric types for temperature and precipitation
df_station_raw[station_t_col] = pd.to_numeric(df_station_raw[station_t_col], errors="coerce")
df_station_raw[station_p_col] = pd.to_numeric(df_station_raw[station_p_col], errors="coerce")

# Drop rows without valid datetime
df_station_raw = df_station_raw.dropna(subset=[station_time_col])

# Aggregate to daily means/sums
df_station_daily = (
    df_station_raw
    .set_index(station_time_col)
    .resample("D")
    .agg({
        station_t_col: "mean",   # daily mean T
        station_p_col: "sum",    # daily sum of RRR
    })
    .reset_index()
)

df_station_daily = df_station_daily.rename(columns={
    station_time_col: DATE_COL_OBS,
    station_t_col: T_OBS_COL,
    station_p_col: P_OBS_COL,
})

print(f"✅ Station daily series (Lakhsh): {len(df_station_daily)} days "
      f"from {df_station_daily[DATE_COL_OBS].min()} to {df_station_daily[DATE_COL_OBS].max()}")

# ---- Merge ERA5 and station on daily dates ----
df = pd.merge(
    df_era_daily,
    df_station_daily[[DATE_COL_OBS, T_OBS_COL, P_OBS_COL]],
    left_on=DATE_COL_ERA,
    right_on=DATE_COL_OBS,
    how="left",
)

DATE_COL = DATE_COL_ERA

# Remove leap days (February 29)
is_leap_day = (df[DATE_COL].dt.month == 2) & (df[DATE_COL].dt.day == 29)
df = df.loc[~is_leap_day].reset_index(drop=True)

# Add time indices
df["year"] = df[DATE_COL].dt.year
df["doy"] = df[DATE_COL].dt.dayofyear
df["month"] = df[DATE_COL].dt.month

print(f"\nTotal merged data: {len(df)} rows")
print(f"Date range: {df[DATE_COL].min()} to {df[DATE_COL].max()}")

# ==========================================
# 2. TEMPERATURE BIAS CORRECTION (TERINK)
# ==========================================
print("\n" + "=" * 70)
print("TEMPERATURE BIAS CORRECTION (Terink Method)")
print("=" * 70)

# Reference period
mask_ref = (df[DATE_COL] >= REF_START) & (df[DATE_COL] <= REF_END)
df_ref = df.loc[mask_ref].copy()
print(f"Reference period: {len(df_ref)} days ({REF_START} to {REF_END})")

# Block structure: 73 blocks of 5 days each
N_BLOCKS = 73
BLOCK_LEN = 5

def doy_to_block(doy):
    """Convert day-of-year to 5-day block index (0-72)."""
    return (doy - 1) // BLOCK_LEN

def circular_diff(d1, d2, n=365):
    """Calculate circular difference on day-of-year circle."""
    diff = np.abs(d1 - d2)
    return np.minimum(diff, n - diff)

# Add block index
df["block"] = doy_to_block(df["doy"])
df_ref["block"] = doy_to_block(df_ref["doy"])

# Initialize parameter arrays
t_mean_obs = np.full(N_BLOCKS, np.nan)
t_std_obs = np.full(N_BLOCKS, np.nan)
t_mean_era = np.full(N_BLOCKS, np.nan)
t_std_era = np.full(N_BLOCKS, np.nan)

print("\nEstimating temperature parameters for each 5-day block...")
print("(Using 65-day moving windows centered on each block)")

for b in range(N_BLOCKS):
    # Center of block (day 3 of 5-day block)
    d_center = b * BLOCK_LEN + 3
    
    # 65-day window: 30 days before + 5-day block + 30 days after
    window_mask = circular_diff(df_ref["doy"].values, d_center) <= 32
    idx = df_ref.index[window_mask]
    
    if len(idx) < 30:
        continue
    
    # Extract temperature values
    t_era = df_ref.loc[idx, T_ERA_COL].values
    t_obs = df_ref.loc[idx, T_OBS_COL].values
    
    # Valid data mask
    valid_t = np.isfinite(t_era) & np.isfinite(t_obs)
    
    if valid_t.sum() >= 10:  # At least 10 valid days
        t_mean_obs[b] = np.mean(t_obs[valid_t])
        t_std_obs[b] = np.std(t_obs[valid_t], ddof=1)
        t_mean_era[b] = np.mean(t_era[valid_t])
        t_std_era[b] = np.std(t_era[valid_t], ddof=1)

# Count blocks with valid parameters
valid_blocks = np.sum(np.isfinite(t_mean_obs))
print(f"Valid blocks: {valid_blocks} of {N_BLOCKS}")

# Apply correction
print("\nApplying temperature correction...")
t_corr = np.zeros(len(df))

for b in range(N_BLOCKS):
    block_mask = df["block"] == b
    if not block_mask.any():
        continue
    
    # Check if parameters are valid
    if (
        np.isfinite(t_mean_obs[b]) and np.isfinite(t_std_obs[b]) and
        np.isfinite(t_mean_era[b]) and np.isfinite(t_std_era[b]) and
        t_std_era[b] > 0
    ):
        # Terink correction formula
        t_era_block = df.loc[block_mask, T_ERA_COL].values
        t_corr_block = (
            t_mean_obs[b]
            + (t_std_obs[b] / t_std_era[b]) * (t_era_block - t_mean_era[b])
        )
        t_corr[block_mask] = t_corr_block
    else:
        # Retain original ERA5-Land values
        t_corr[block_mask] = df.loc[block_mask, T_ERA_COL].values

df["temp_Terink_corr"] = t_corr

print("✅ Temperature correction complete")

# ==========================================
# 3. PRECIPITATION BIAS CORRECTION (MONTHLY SCALING)
# ==========================================
print("\n" + "=" * 70)
print("PRECIPITATION BIAS CORRECTION (Monthly Mean Scaling)")
print("=" * 70)

p_scaled = np.zeros(len(df))

print("\nComputing monthly scaling factors...")
for m in range(1, 13):
    # Wet days in reference period for this month
    mask_ref_m = (
        (df["month"] == m) &
        (df[DATE_COL] >= REF_START) &
        (df[DATE_COL] <= REF_END) &
        (df[P_OBS_COL] > 0)  # Station precipitation > 0
    )
    
    era_ref = df.loc[mask_ref_m, P_ERA_COL].values
    obs_ref = df.loc[mask_ref_m, P_OBS_COL].values
    
    # All days in this month (all years)
    month_mask = df["month"] == m
    era_month = df.loc[month_mask, P_ERA_COL].values
    p_corr_month = era_month.copy()
    
    # Compute scaling factor if enough wet days
    if len(era_ref) >= 3 and len(obs_ref) >= 3:
        mu_era = np.nanmean(era_ref)
        mu_obs = np.nanmean(obs_ref)
        if mu_era > 0:
            s = mu_obs / mu_era
            print(f"  Month {m:2d}: s = {s:.3f} (μ_obs={mu_obs:.2f} mm, μ_era={mu_era:.2f} mm)")
            
            # Apply scaling to wet days only
            wet_full = era_month > 0
            p_corr_month[wet_full] = era_month[wet_full] * s
        else:
            print(f"  Month {m:2d}: No scaling (μ_era = 0)")
    else:
        print(f"  Month {m:2d}: Insufficient data ({len(obs_ref)} wet days)")
    
    p_scaled[month_mask] = p_corr_month

df["prec_monthScale_corr"] = p_scaled

print("✅ Precipitation correction complete")

# ==========================================
# 4. SAVE RESULTS
# ==========================================
print("\n" + "=" * 70)
print("SAVING RESULTS")
print("=" * 70)

output_file = OUTPUT_DIR / "ERA5_bias_corrected.csv"
df.to_csv(output_file, index=False)
print(f"✅ Saved: {output_file}")

# Also save Excel format
output_excel = OUTPUT_DIR / "ERA5_bias_corrected.xlsx"
df.to_excel(output_excel, index=False)
print(f"✅ Saved: {output_excel}")

# ==========================================
# 5. VALIDATION PLOTS
# ==========================================
print("\n" + "=" * 70)
print("CREATING VALIDATION PLOTS")
print("=" * 70)

# Plot 1: Daily temperature (raw vs corrected)
fig, ax = plt.subplots(figsize=(14, 5))
ax.plot(df[DATE_COL], df[T_ERA_COL], label="ERA5-Land T (raw)", 
        color="tab:red", alpha=0.4, linewidth=0.5)
ax.plot(df[DATE_COL], df["temp_Terink_corr"], label="ERA5-Land T (corrected)", 
        color="tab:green", alpha=0.7, linewidth=0.5)
if T_OBS_COL in df.columns:
    ax.scatter(df[DATE_COL], df[T_OBS_COL], label="Javshangoz T (obs)", 
              color="k", s=1, alpha=0.3)
ax.set_title("Daily Temperature: Raw vs Terink-Corrected ERA5-Land")
ax.set_ylabel("Temperature (°C)")
ax.set_xlabel("Date")
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "temperature_raw_vs_corrected.png", dpi=300, bbox_inches='tight')
print(f"✅ Saved: {OUTPUT_DIR / 'temperature_raw_vs_corrected.png'}")
plt.close()

# Plot 2: Temperature bias (raw vs corrected)
if T_OBS_COL in df.columns:
    df["bias_raw_T"] = df[T_ERA_COL] - df[T_OBS_COL]
    df["bias_corr_T"] = df["temp_Terink_corr"] - df[T_OBS_COL]
    
    # Filter to reference period for bias plot
    df_bias = df.loc[mask_ref].copy()
    
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(df_bias[DATE_COL], df_bias["bias_raw_T"],
            label="Raw ERA5 Bias", color="tab:red", alpha=0.5, linewidth=0.5)
    ax.plot(df_bias[DATE_COL], df_bias["bias_corr_T"],
            label="Corrected Bias", color="tab:green", alpha=0.7, linewidth=0.5)
    ax.axhline(0, color="k", lw=0.8, linestyle="--")
    ax.set_title(f"Temperature Bias Correction (Reference Period: {REF_START} to {REF_END})")
    ax.set_ylabel("Temperature Bias (°C)\n(Model - Obs)")
    ax.set_xlabel("Date")
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "temperature_bias_correction.png", dpi=300, bbox_inches='tight')
    print(f"✅ Saved: {OUTPUT_DIR / 'temperature_bias_correction.png'}")
    plt.close()
    
    # Calculate bias statistics
    print("\nTemperature Bias Statistics (Reference Period):")
    print(f"  Raw ERA5:")
    print(f"    Mean bias: {df_bias['bias_raw_T'].mean():.3f} °C")
    print(f"    RMSE: {np.sqrt((df_bias['bias_raw_T']**2).mean()):.3f} °C")
    print(f"  Corrected:")
    print(f"    Mean bias: {df_bias['bias_corr_T'].mean():.3f} °C")
    print(f"    RMSE: {np.sqrt((df_bias['bias_corr_T']**2).mean()):.3f} °C")

# Plot 3: Monthly precipitation (raw vs corrected)
if P_OBS_COL in df.columns:
    monthly = df.set_index(DATE_COL)[[P_ERA_COL, "prec_monthScale_corr", P_OBS_COL]].resample("M").sum()
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    
    # Raw ERA5 vs Obs
    ax1.plot(monthly.index, monthly[P_ERA_COL], label="ERA5-Land P (raw)", 
             color="tab:blue", marker="o", markersize=3)
    ax1.plot(monthly.index, monthly[P_OBS_COL], label="Javshangoz P (obs)", 
             color="tab:green", marker="s", markersize=3)
    ax1.set_ylabel("Monthly Precipitation (mm)")
    ax1.set_title("Monthly Precipitation: Raw ERA5 vs Observations")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Corrected ERA5 vs Obs
    ax2.plot(monthly.index, monthly["prec_monthScale_corr"], label="ERA5-Land P (corrected)", 
             color="tab:blue", marker="o", markersize=3)
    ax2.plot(monthly.index, monthly[P_OBS_COL], label="Javshangoz P (obs)", 
             color="tab:green", marker="s", markersize=3)
    ax2.set_ylabel("Monthly Precipitation (mm)")
    ax2.set_xlabel("Date")
    ax2.set_title("Monthly Precipitation: Corrected ERA5 vs Observations")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "precipitation_monthly_comparison.png", dpi=300, bbox_inches='tight')
    print(f"✅ Saved: {OUTPUT_DIR / 'precipitation_monthly_comparison.png'}")
    plt.close()
    
    # Calculate monthly bias
    monthly_ref = monthly.loc[(monthly.index >= REF_START) & (monthly.index <= REF_END)]
    if len(monthly_ref) > 0:
        bias_raw = (monthly_ref[P_ERA_COL] - monthly_ref[P_OBS_COL]).mean()
        bias_corr = (monthly_ref["prec_monthScale_corr"] - monthly_ref[P_OBS_COL]).mean()
        print(f"\nMonthly Precipitation Bias (Reference Period):")
        print(f"  Raw ERA5: {bias_raw:.2f} mm/month")
        print(f"  Corrected: {bias_corr:.2f} mm/month")

print("\n" + "=" * 70)
print("✅ BIAS CORRECTION COMPLETE")
print("=" * 70)
print(f"\nOutput files saved to: {OUTPUT_DIR}")
print("\nNext steps:")
print("  1. Use 'temp_Terink_corr' for all temperature-based derivatives (PDD)")
print("  2. Use 'prec_monthScale_corr' for precipitation-based derivatives (ROS)")
print("  3. See validation plots for quality assessment")

