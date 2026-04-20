#!/usr/bin/env python3
"""
Create updated velocity time series figure (Figure 5: fig:h1_h2) with:
- Separate Track 78 and Track 173 time series
- De-biased velocities (V_corrected = V_raw - μ_stable)
- Empirical uncertainty error bars (±σ_stable)
- Search range fix (400+ pixels)

This script will be used after Tasks 1, 2, and 3 are complete.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from pathlib import Path

# Configuration
TRACK78_CSV = "processed_data/velocity_timeseries/track78_velocity_timeseries.csv"
TRACK173_CSV = "processed_data/velocity_timeseries/track173_velocity_timeseries.csv"
OUTPUT_FIGURE = "processed_data/h1_h2_analysis/h1_h2_analysis_updated.png"
OUTPUT_DIR = Path(OUTPUT_FIGURE).parent
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_track_data(csv_path):
    """Load velocity time series for a track."""
    if not Path(csv_path).exists():
        raise FileNotFoundError(f"Time series file not found: {csv_path}")
    
    df = pd.read_csv(csv_path)
    
    # Expected columns:
    # date, velocity_corrected, uncertainty, correlation, etc.
    
    # Convert date to datetime
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    elif 'midpoint_date' in df.columns:
        df['date'] = pd.to_datetime(df['midpoint_date'])
    else:
        raise ValueError(f"Date column not found in {csv_path}")
    
    return df

def create_velocity_timeseries_plot(track78_df, track173_df, output_path):
    """Create velocity time series plot with both tracks."""
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plot Track 78
    if 'velocity_corrected' in track78_df.columns:
        vel_col = 'velocity_corrected'
    elif 'velocity' in track78_df.columns:
        vel_col = 'velocity'
    else:
        raise ValueError("Velocity column not found in Track 78 data")
    
    if 'uncertainty' in track78_df.columns:
        unc_col = 'uncertainty'
    elif 'sigma_stable' in track78_df.columns:
        unc_col = 'sigma_stable'
    else:
        unc_col = None
    
    ax.errorbar(
        track78_df['date'],
        track78_df[vel_col],
        yerr=track78_df[unc_col] if unc_col else None,
        fmt='o-',
        color='#2E86AB',  # Blue
        label='Track 78 (Orbit 78)',
        markersize=8,
        capsize=5,
        capthick=2,
        linewidth=2,
        alpha=0.8
    )
    
    # Plot Track 173
    if 'velocity_corrected' in track173_df.columns:
        vel_col = 'velocity_corrected'
    elif 'velocity' in track173_df.columns:
        vel_col = 'velocity'
    else:
        raise ValueError("Velocity column not found in Track 173 data")
    
    if 'uncertainty' in track173_df.columns:
        unc_col = 'uncertainty'
    elif 'sigma_stable' in track173_df.columns:
        unc_col = 'sigma_stable'
    else:
        unc_col = None
    
    ax.errorbar(
        track173_df['date'],
        track173_df[vel_col],
        yerr=track173_df[unc_col] if unc_col else None,
        fmt='s-',
        color='#A23B72',  # Purple
        label='Track 173 (Orbit 173)',
        markersize=8,
        capsize=5,
        capthick=2,
        linewidth=2,
        alpha=0.8
    )
    
    # Formatting
    ax.set_xlabel('Date', fontsize=12, fontweight='bold')
    ax.set_ylabel('Velocity (m day$^{-1}$)', fontsize=12, fontweight='bold')
    ax.set_title('Didal Glacier Velocity Time Series\nSeparate Track Processing with Empirical Uncertainty', 
                 fontsize=14, fontweight='bold', pad=20)
    
    ax.legend(loc='best', fontsize=11, framealpha=0.9)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.tick_params(axis='both', labelsize=10)
    
    # Format x-axis dates
    fig.autofmt_xdate()
    
    # Add text annotation about processing
    textstr = (
        'Processing: Same-track pairs only (no cross-track mixing)\n'
        'Search range: ≥400 pixels (Max velocity >800 m/d)\n'
        'Bias correction: Applied (V_corrected = V_raw - μ_stable)\n'
        'Uncertainty: Empirical from stable ground (±σ_stable)'
    )
    ax.text(0.02, 0.98, textstr, transform=ax.transAxes,
            fontsize=9, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"✓ Saved updated velocity time series figure: {output_path}")

def main():
    """Main execution."""
    print("=" * 80)
    print("CREATING UPDATED VELOCITY TIME SERIES FIGURE")
    print("=" * 80)
    print("\nThis script creates Figure 5 (fig:h1_h2) with:")
    print("  - Separate Track 78 and Track 173 time series")
    print("  - De-biased velocities")
    print("  - Empirical uncertainty error bars")
    print("  - Search range fix (400+ pixels)")
    print("\n" + "=" * 80)
    
    # Check if data files exist
    if not Path(TRACK78_CSV).exists():
        print(f"\n⚠️  WARNING: Track 78 data not found: {TRACK78_CSV}")
        print("   This script requires re-processed data from Tasks 1, 2, and 3.")
        print("   Please complete SNAP re-processing first.")
        return
    
    if not Path(TRACK173_CSV).exists():
        print(f"\n⚠️  WARNING: Track 173 data not found: {TRACK173_CSV}")
        print("   This script requires re-processed data from Tasks 1, 2, and 3.")
        print("   Please complete SNAP re-processing first.")
        return
    
    # Load data
    print(f"\nLoading Track 78 data: {TRACK78_CSV}")
    track78_df = load_track_data(TRACK78_CSV)
    print(f"  Loaded {len(track78_df)} measurements")
    
    print(f"\nLoading Track 173 data: {TRACK173_CSV}")
    track173_df = load_track_data(TRACK173_CSV)
    print(f"  Loaded {len(track173_df)} measurements")
    
    # Create plot
    print(f"\nCreating velocity time series plot...")
    create_velocity_timeseries_plot(track78_df, track173_df, OUTPUT_FIGURE)
    
    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)
    print(f"\nFigure saved to: {OUTPUT_FIGURE}")
    print("\nNext steps:")
    print("  1. Review the figure")
    print("  2. Update main.tex Figure 5 caption if needed")
    print("  3. Replace processed_data/h1_h2_analysis/h1_h2_analysis.png with this file")

if __name__ == "__main__":
    main()
