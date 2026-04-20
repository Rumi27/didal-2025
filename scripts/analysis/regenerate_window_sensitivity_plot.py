#!/usr/bin/env python3
"""
Quick script to regenerate the window sensitivity plot with updated text sizes.
Reads existing CSV without reprocessing images.
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
from pathlib import Path

# Paths
OUTPUT_DIR = Path("processed_data/window_sensitivity")
CSV_PATH = OUTPUT_DIR / "sensitivity_results.csv"
PLOT_PATH = OUTPUT_DIR / "sensitivity_plot.pdf"

# English date formatter (locale-independent)
mon_en = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def fmt_day_mon_en(x, pos):
    try:
        dt = mdates.num2date(x)
        return f"{dt.day:02d} {mon_en[dt.month - 1]}"
    except:
        return ""

def main():
    print(f"Reading results from {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    
    # Get unique window sizes
    window_sizes = sorted(df['window_size'].unique())
    print(f"Window sizes: {window_sizes}")
    
    # Create plot
    plt.figure(figsize=(10, 6))
    
    for win in window_sizes:
        sub = df[df['window_size'] == win].copy()
        # Remove rows with NaN v_mean
        sub = sub.dropna(subset=['v_mean'])
        
        if not sub.empty:
            dates = pd.to_datetime(sub['date1'])
            plt.plot(dates, sub['v_mean'], 'o-', label=f"Win {win}px", linewidth=2)
            plt.fill_between(dates, 
                             sub['v_mean'] - sub['v_std'], 
                             sub['v_mean'] + sub['v_std'], 
                             alpha=0.1)
            print(f"  Win {win}px: {len(sub)} valid points")
    
    # Styling with significantly increased text sizes
    plt.legend(fontsize=16, frameon=True, framealpha=0.95, loc='best')
    plt.grid(True, alpha=0.3, linestyle='--')
    plt.title("Velocity Sensitivity to Window Size (Strict Masking)", 
              fontsize=20, fontweight='normal', loc='left', pad=10)
    plt.ylabel("Velocity (m d$^{-1}$)", fontsize=18)
    plt.xlabel("Date", fontsize=18)
    
    # Format x-axis with English dates
    ax = plt.gca()
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_day_mon_en))
    ax.tick_params(axis='both', which='major', labelsize=16)
    
    plt.tight_layout()
    plt.savefig(PLOT_PATH, dpi=300, bbox_inches='tight')
    print(f"\n✅ Saved updated plot to: {PLOT_PATH}")
    print("\nText sizes (INCREASED):")
    print("  - Y-axis label: 18pt")
    print("  - X-axis label: 18pt")
    print("  - Title: 20pt")
    print("  - Legend: 16pt")
    print("  - Tick labels: 16pt")

if __name__ == "__main__":
    main()
