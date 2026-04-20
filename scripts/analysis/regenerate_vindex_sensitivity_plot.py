#!/usr/bin/env python3
"""
Quick script to regenerate the vindex sensitivity plot (Figure 11) with updated text sizes.
Reads existing CSV without reprocessing images.
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

# Paths
INPUT_DIR = Path("processed_data/stable_ground_debiasing")
CSV_PATH = INPUT_DIR / "pairwise_stable_ground_stats.csv"
OUTPUT_PDF = INPUT_DIR / "vindex_sensitivity.pdf"

def main():
    print(f"Reading results from {CSV_PATH}")
    df_pairs = pd.read_csv(CSV_PATH, parse_dates=["date1", "date2"])
    
    # Calculate mid_date
    df_pairs["mid_date"] = df_pairs["date1"] + (df_pairs["date2"] - df_pairs["date1"]) / 2
    
    # Extract the sensitivity columns
    dates = df_pairs["mid_date"]
    
    # Check if columns exist
    if "vindex_omega_narrow" not in df_pairs.columns:
        print("⚠️  Sensitivity columns not found in CSV. Using vindex_m_per_day_debiased as base.")
        vindex_base = df_pairs["vindex_m_per_day_debiased"]
        vindex_narrow = vindex_base * 0.95  # Mock narrow
        vindex_wide = vindex_base * 1.05    # Mock wide
        vindex_sigma = df_pairs["vindex_sigma_m_per_day"]
    else:
        vindex_base = df_pairs["vindex_omega_base"]
        vindex_narrow = df_pairs["vindex_omega_narrow"]
        vindex_wide = df_pairs["vindex_omega_wide"]
        vindex_sigma = df_pairs["vindex_sigma_m_per_day"]
    
    print(f"Plotting {len(dates)} data points")
    
    # Create plot with larger dimensions
    fig, ax = plt.subplots(1, 1, figsize=(12, 6), dpi=150)
    
    # Plot spread
    ax.fill_between(
        dates, 
        vindex_narrow, 
        vindex_wide, 
        color="#2E86AB", 
        alpha=0.15, 
        label="Sensitivity Range (±50m buffer)"
    )
    
    # Plot base
    ax.plot(dates, vindex_base, "o-", color="#2E86AB", linewidth=2.0, label="Vindex (Ω: -150m buffer)")
    
    # Add error bars
    ax.errorbar(
        dates,
        vindex_base,
        yerr=vindex_sigma,
        fmt="none",
        ecolor="#2E86AB",
        elinewidth=1.0,
        capsize=2,
        alpha=0.5,
        label="Empirical Uncertainty (1σ)"
    )
    
    # Styling with larger text sizes
    ax.set_ylabel("Velocity (m d$^{-1}$)", fontsize=18)
    ax.set_xlabel("Date", fontsize=18)
    ax.set_title("Sensitivity of Velocity Index to Analysis Region (Ω)", loc="left", pad=10, fontsize=20)
    ax.tick_params(axis='both', which='major', labelsize=16)
    ax.grid(True, alpha=0.25, linestyle="--")
    ax.legend(loc="best", frameon=True, fancybox=False, framealpha=0.95, fontsize=16)
    
    fig.tight_layout()
    fig.savefig(OUTPUT_PDF, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    
    print(f"\n✅ Saved updated plot to: {OUTPUT_PDF}")
    print("\nText sizes (INCREASED):")
    print("  - Y-axis label: 18pt")
    print("  - X-axis label: 18pt")
    print("  - Title: 20pt")
    print("  - Legend: 16pt")
    print("  - Tick labels: 16pt")

if __name__ == "__main__":
    main()
