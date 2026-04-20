#!/usr/bin/env python3
"""
Extract bias correction results from the bias-corrected Excel file.
This script reads the file and calculates bias statistics.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Try to find the bias-corrected file
POSSIBLE_FILES = [
    "clim_72.80_37.40_#457_BiasCorr_T_Terink_P_monthScale.xlsx",
    "clim_72.80_37.40_#457_TerinkBiasCorr.xlsx",
    "clim_72.80_37.40_#457.xlsx"
]

print("=" * 70)
print("EXTRACTING BIAS CORRECTION RESULTS")
print("=" * 70)

# Search for files
found_file = None
for f in POSSIBLE_FILES:
    path = Path(f)
    if path.exists():
        found_file = path
        print(f"\n✅ Found file: {f}")
        break

if not found_file:
    # Search in subdirectories
    print("\nSearching in subdirectories...")
    for pattern in ["**/clim_72*.xlsx", "**/clim_72*.xls", "**/*BiasCorr*.xlsx"]:
        files = list(Path(".").glob(pattern))
        if files:
            found_file = files[0]
            print(f"✅ Found: {found_file}")
            break

if not found_file:
    print("\n❌ Bias-corrected file not found!")
    print("\nExpected files:")
    for f in POSSIBLE_FILES:
        print(f"  • {f}")
    print("\nPlease provide the path to the bias-corrected Excel file.")
    print("The file should contain:")
    print("  - Original ERA5-Land: temp(degC), prec(mm)")
    print("  - Station observations: Javshangoz temp, Precipitation")
    print("  - Corrected series: temp_Terink_corr, prec_monthScale_corr")
    exit(1)

# Read the file
print(f"\nReading: {found_file}")
try:
    # Try reading with header at row 3 (index 2) as mentioned in user's description
    df = pd.read_excel(found_file, sheet_name=0, header=2)
    print(f"✅ Read successfully: {df.shape[0]} rows, {df.shape[1]} columns")
except:
    try:
        df = pd.read_excel(found_file, sheet_name=0)
        print(f"✅ Read with default header: {df.shape[0]} rows, {df.shape[1]} columns")
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        exit(1)

# Check columns
print(f"\nColumns found:")
print(f"  {list(df.columns)[:10]}...")

# Identify key columns
date_col = None
t_era_col = None
t_corr_col = None
t_obs_col = None
p_era_col = None
p_corr_col = None
p_obs_col = None

for col in df.columns:
    col_lower = str(col).lower()
    if 'date' in col_lower or 'time' in col_lower:
        date_col = col
    if 'temp' in col_lower and 'terink' in col_lower:
        t_corr_col = col
    elif 'temp' in col_lower and 'degc' in col_lower:
        t_era_col = col
    elif 'javshangoz' in col_lower and 'temp' in col_lower:
        t_obs_col = col
    if 'prec' in col_lower and 'monthscale' in col_lower:
        p_corr_col = col
    elif 'prec' in col_lower and 'mm' in col_lower:
        p_era_col = col
    elif 'precipitation' in col_lower and 'javshangoz' not in col_lower:
        p_obs_col = col

print(f"\nIdentified columns:")
print(f"  Date: {date_col}")
print(f"  Temperature ERA5: {t_era_col}")
print(f"  Temperature Corrected: {t_corr_col}")
print(f"  Temperature Observed: {t_obs_col}")
print(f"  Precipitation ERA5: {p_era_col}")
print(f"  Precipitation Corrected: {p_corr_col}")
print(f"  Precipitation Observed: {p_obs_col}")

# Parse dates
if date_col:
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.dropna(subset=[date_col])
    print(f"\nDate range: {df[date_col].min()} to {df[date_col].max()}")

# Reference period
REF_START = "2000-01-01"
REF_END = "2019-12-31"
mask_ref = (df[date_col] >= REF_START) & (df[date_col] <= REF_END)
df_ref = df.loc[mask_ref].copy()
print(f"\nReference period (2000-2019): {len(df_ref)} days")

# Calculate temperature bias statistics
if t_era_col and t_corr_col and t_obs_col:
    print("\n" + "=" * 70)
    print("TEMPERATURE BIAS CORRECTION RESULTS")
    print("=" * 70)
    
    # Calculate biases
    df_ref['bias_raw_T'] = df_ref[t_era_col] - df_ref[t_obs_col]
    df_ref['bias_corr_T'] = df_ref[t_corr_col] - df_ref[t_obs_col]
    
    # Statistics
    print("\nRaw ERA5-Land Temperature:")
    mean_bias_raw = df_ref['bias_raw_T'].mean()
    rmse_raw = np.sqrt((df_ref['bias_raw_T']**2).mean())
    std_bias_raw = df_ref['bias_raw_T'].std()
    print(f"  Mean bias: {mean_bias_raw:.3f} °C")
    print(f"  RMSE: {rmse_raw:.3f} °C")
    print(f"  Std dev: {std_bias_raw:.3f} °C")
    print(f"  Min bias: {df_ref['bias_raw_T'].min():.3f} °C")
    print(f"  Max bias: {df_ref['bias_raw_T'].max():.3f} °C")
    
    print("\nCorrected ERA5-Land Temperature (Terink method):")
    mean_bias_corr = df_ref['bias_corr_T'].mean()
    rmse_corr = np.sqrt((df_ref['bias_corr_T']**2).mean())
    std_bias_corr = df_ref['bias_corr_T'].std()
    print(f"  Mean bias: {mean_bias_corr:.3f} °C")
    print(f"  RMSE: {rmse_corr:.3f} °C")
    print(f"  Std dev: {std_bias_corr:.3f} °C")
    print(f"  Min bias: {df_ref['bias_corr_T'].min():.3f} °C")
    print(f"  Max bias: {df_ref['bias_corr_T'].max():.3f} °C")
    
    print("\nImprovement:")
    print(f"  Mean bias reduction: {mean_bias_raw - mean_bias_corr:.3f} °C")
    print(f"  RMSE reduction: {rmse_raw - rmse_corr:.3f} °C")
    print(f"  RMSE improvement: {(1 - rmse_corr/rmse_raw)*100:.1f}%")
    
    # Correlation
    corr_raw = df_ref[t_era_col].corr(df_ref[t_obs_col])
    corr_corr = df_ref[t_corr_col].corr(df_ref[t_obs_col])
    print(f"\nCorrelation with observations:")
    print(f"  Raw ERA5: {corr_raw:.3f}")
    print(f"  Corrected: {corr_corr:.3f}")

# Calculate precipitation bias statistics
if p_era_col and p_corr_col and p_obs_col:
    print("\n" + "=" * 70)
    print("PRECIPITATION BIAS CORRECTION RESULTS")
    print("=" * 70)
    
    # Monthly aggregation
    monthly = df_ref.set_index(date_col)[[p_era_col, p_corr_col, p_obs_col]].resample("M").sum()
    
    # Monthly bias
    monthly['bias_raw_P'] = monthly[p_era_col] - monthly[p_obs_col]
    monthly['bias_corr_P'] = monthly[p_corr_col] - monthly[p_obs_col]
    
    print("\nRaw ERA5-Land Precipitation (Monthly):")
    mean_bias_raw_p = monthly['bias_raw_P'].mean()
    rmse_raw_p = np.sqrt((monthly['bias_raw_P']**2).mean())
    print(f"  Mean bias: {mean_bias_raw_p:.2f} mm/month")
    print(f"  RMSE: {rmse_raw_p:.2f} mm/month")
    
    print("\nCorrected ERA5-Land Precipitation (Monthly scaling):")
    mean_bias_corr_p = monthly['bias_corr_P'].mean()
    rmse_corr_p = np.sqrt((monthly['bias_corr_P']**2).mean())
    print(f"  Mean bias: {mean_bias_corr_p:.2f} mm/month")
    print(f"  RMSE: {rmse_corr_p:.2f} mm/month")
    
    print("\nImprovement:")
    print(f"  Mean bias reduction: {mean_bias_raw_p - mean_bias_corr_p:.2f} mm/month")
    print(f"  RMSE reduction: {rmse_raw_p - rmse_corr_p:.2f} mm/month")
    if rmse_raw_p > 0:
        print(f"  RMSE improvement: {(1 - rmse_corr_p/rmse_raw_p)*100:.1f}%")
    
    # Wet-day mean bias (as mentioned in user's description)
    wet_days_raw = df_ref.loc[df_ref[p_obs_col] > 0]
    wet_days_corr = df_ref.loc[df_ref[p_obs_col] > 0]
    
    if len(wet_days_raw) > 0:
        wet_mean_raw = (wet_days_raw[p_era_col] - wet_days_raw[p_obs_col]).mean()
        wet_mean_corr = (wet_days_corr[p_corr_col] - wet_days_corr[p_obs_col]).mean()
        print(f"\nWet-day mean bias:")
        print(f"  Raw ERA5: {wet_mean_raw:.2f} mm")
        print(f"  Corrected: {wet_mean_corr:.2f} mm")
        print(f"  Improvement: {wet_mean_raw - wet_mean_corr:.2f} mm")

# Save results summary
output_dir = Path("processed_data/bias_correction")
output_dir.mkdir(parents=True, exist_ok=True)

results = {
    "temperature": {
        "raw": {
            "mean_bias_C": float(mean_bias_raw) if 'mean_bias_raw' in locals() else None,
            "rmse_C": float(rmse_raw) if 'rmse_raw' in locals() else None,
            "std_C": float(std_bias_raw) if 'std_bias_raw' in locals() else None
        },
        "corrected": {
            "mean_bias_C": float(mean_bias_corr) if 'mean_bias_corr' in locals() else None,
            "rmse_C": float(rmse_corr) if 'rmse_corr' in locals() else None,
            "std_C": float(std_bias_corr) if 'std_bias_corr' in locals() else None
        },
        "improvement": {
            "mean_bias_reduction_C": float(mean_bias_raw - mean_bias_corr) if 'mean_bias_raw' in locals() and 'mean_bias_corr' in locals() else None,
            "rmse_reduction_C": float(rmse_raw - rmse_corr) if 'rmse_raw' in locals() and 'rmse_corr' in locals() else None,
            "rmse_improvement_percent": float((1 - rmse_corr/rmse_raw)*100) if 'rmse_raw' in locals() and 'rmse_corr' in locals() and rmse_raw > 0 else None
        }
    },
    "precipitation": {
        "raw": {
            "mean_bias_mm_month": float(mean_bias_raw_p) if 'mean_bias_raw_p' in locals() else None,
            "rmse_mm_month": float(rmse_raw_p) if 'rmse_raw_p' in locals() else None
        },
        "corrected": {
            "mean_bias_mm_month": float(mean_bias_corr_p) if 'mean_bias_corr_p' in locals() else None,
            "rmse_mm_month": float(rmse_corr_p) if 'rmse_corr_p' in locals() else None
        },
        "improvement": {
            "mean_bias_reduction_mm_month": float(mean_bias_raw_p - mean_bias_corr_p) if 'mean_bias_raw_p' in locals() and 'mean_bias_corr_p' in locals() else None,
            "rmse_reduction_mm_month": float(rmse_raw_p - rmse_corr_p) if 'rmse_raw_p' in locals() and 'rmse_corr_p' in locals() else None
        },
        "wet_day_mean_bias": {
            "raw_mm": float(wet_mean_raw) if 'wet_mean_raw' in locals() else None,
            "corrected_mm": float(wet_mean_corr) if 'wet_mean_corr' in locals() else None,
            "improvement_mm": float(wet_mean_raw - wet_mean_corr) if 'wet_mean_raw' in locals() and 'wet_mean_corr' in locals() else None
        }
    },
    "reference_period": {
        "start": REF_START,
        "end": REF_END,
        "n_days": len(df_ref)
    }
}

import json
results_file = output_dir / "bias_correction_results.json"
with open(results_file, 'w') as f:
    json.dump(results, f, indent=2)

print("\n" + "=" * 70)
print("✅ RESULTS EXTRACTED")
print("=" * 70)
print(f"\nResults saved to: {results_file}")
print("\nThese results can be added to the manuscript Methods section.")

