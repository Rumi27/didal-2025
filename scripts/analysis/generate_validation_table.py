#!/usr/bin/env python3
"""
Generate a LaTeX validation table comparing 6-day cross-track vs 12-day same-track statistics.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Paths
CROSS_6D_CSV = Path("satellite_data/sentinel1/processed/velocity_timeseries_python.csv")
STABLE_6D_TEX = Path("processed_data/stable_ground_debiasing/pairwise_stable_ground_stats_table.tex")
ORBIT1_12D_CSV = Path("processed_data/same_track_12day_comparison/orbit1_12day_debiased.csv")
ORBIT2_12D_CSV = Path("processed_data/same_track_12day_comparison/orbit2_12day_debiased.csv")

def parse_stable_tex(path):
    """Parse the existing stable ground stats table for 6-day series."""
    with open(path) as f:
        lines = f.readlines()
    
    data = []
    for line in lines:
        if "2025-" in line:
            parts = line.split("&")
            # Pair, BiasE, BiasN, SlopesE, SlopesN, NMAD_E, NMAD_N, ValidFrac, MedianMatch
            date_pair = parts[0].strip()
            nmad_e = parts[5].strip()
            nmad_n = parts[6].strip()
            valid_frac = parts[7].strip()
            median_match = parts[8].strip().replace(r"\\", "")
            data.append({
                "pair": date_pair,
                "nmad_e": float(nmad_e) if "NA" not in nmad_e else np.nan,
                "nmad_n": float(nmad_n) if "NA" not in nmad_n else np.nan,
                "valid_frac": float(valid_frac) if "NA" not in valid_frac else np.nan
            })
    return pd.DataFrame(data)

def main():
    # 1. Load 6-day stats
    # The CSV has correlation per date. The Tex has NMAD/ValidFrac.
    df_6d_corr = pd.read_csv(CROSS_6D_CSV)
    df_6d_corr["pair"] = df_6d_corr["date1"] + "--" + df_6d_corr["date2"]
    
    df_6d_stable = parse_stable_tex(STABLE_6D_TEX)
    
    # Merge
    df_6d = pd.merge(df_6d_corr, df_6d_stable, on="pair", how="left")
    
    # Calculate representative 6-day stats
    stats_6d = {
        "Type": "6-day Cross-track",
        "Median Corr.": df_6d["correlation"].median(),
        "Valid Frac.": df_6d["valid_frac"].median(),
        "NMAD (m/d)": np.nanmedian(df_6d[["nmad_e", "nmad_n"]].values) 
    }
    
    # 2. Load 12-day stats
    orb1 = pd.read_csv(ORBIT1_12D_CSV)
    orb2 = pd.read_csv(ORBIT2_12D_CSV)
    
    # Orbit 1 stats
    # NMAD in CSV is likely displacement (m). Convert to m/d?
    # Actually, let's assume it IS displacement since it's "resid_nmad_E_m". 
    # Velocity NMAD = NMAD_m / 12 days.
    nmad_1 = np.nanmedian(orb1[["resid_nmad_E_m", "resid_nmad_N_m"]].values) / 12.0
    stats_orb1 = {
        "Type": "12-day Same-track (Orbit 78)",
        "Median Corr.": orb1["stable_corr_median"].median(),
        "Valid Frac.": orb1["valid_fraction"].median(),
        "NMAD (m/d)": nmad_1
    }
    
    nmad_2 = np.nanmedian(orb2[["resid_nmad_E_m", "resid_nmad_N_m"]].values) / 12.0
    stats_orb2 = {
        "Type": "12-day Same-track (Orbit 173)",
        "Median Corr.": orb2["stable_corr_median"].median(),
        "Valid Frac.": orb2["valid_fraction"].median(),
        "NMAD (m/d)": nmad_2
    }
    
    # 3. Build Table
    rows = [stats_6d, stats_orb1, stats_orb2]
    print("\\begin{table}[ht]")
    print("\\centering")
    print("\\caption{Comparison of validation statistics for cross-track vs. same-track integrity. Note the high stable-ground correlation for same-track (indicating lock) contrasts with their failed velocity retrieval (wall-locking).}")
    print("\\label{tab:validation_stats}")
    print("\\begin{tabular}{lccc}")
    print("\\toprule")
    print("\\textbf{Series} & \\textbf{Median Corr.} & \\textbf{Valid Fraction} & \\textbf{NMAD} (m d$^{-1}$) \\\\")
    print("\\midrule")
    
    for r in rows:
        print(f"{r['Type']} & {r['Median Corr.']:.2f} & {r['Valid Frac.']:.2f} & {r['NMAD (m/d)']:.2f} \\\\")
        
    print("\\bottomrule")
    print("\\end{tabular}")
    print("\\end{table}")

if __name__ == "__main__":
    main()
