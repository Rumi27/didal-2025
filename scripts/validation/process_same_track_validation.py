#!/usr/bin/env python3
"""
Process same-track Sentinel-1 pairs for validation.

This script processes the 8 same-track pairs identified for validation
and compares them with cross-track pairs to quantify biases.

Requirements:
    - SNAP-processed same-track velocity maps (manual processing required)
    - Cross-track velocity time series for comparison
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# Configuration
SAME_TRACK_DIR = Path("processed_data/velocity_validation/same_track")
CROSS_TRACK_FILE = Path("satellite_data/sentinel1/processed/velocity_timeseries_python.csv")
GLACIER_OUTLINE = Path("Didal_Glacier_GIS_Data/Glacier_Outline")
OUTPUT_DIR = Path("processed_data/velocity_validation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SAME_TRACK_DIR.mkdir(parents=True, exist_ok=True)

# Same-track pairs (from identify_same_track_pairs.py)
SAME_TRACK_PAIRS = [
    # Track 78
    {'track': 78, 'master': '2025-09-07', 'slave': '2025-09-19', 'baseline': 12, 'midpoint': '2025-09-13'},
    {'track': 78, 'master': '2025-09-19', 'slave': '2025-10-01', 'baseline': 12, 'midpoint': '2025-10-10'},
    {'track': 78, 'master': '2025-10-01', 'slave': '2025-10-13', 'baseline': 12, 'midpoint': '2025-10-07'},
    {'track': 78, 'master': '2025-10-13', 'slave': '2025-10-25', 'baseline': 11, 'midpoint': '2025-10-19'},
    # Track 173
    {'track': 173, 'master': '2025-09-13', 'slave': '2025-09-25', 'baseline': 12, 'midpoint': '2025-09-19'},
    {'track': 173, 'master': '2025-09-25', 'slave': '2025-10-07', 'baseline': 12, 'midpoint': '2025-10-01'},
    {'track': 173, 'master': '2025-10-07', 'slave': '2025-10-19', 'baseline': 12, 'midpoint': '2025-10-13'},
    {'track': 173, 'master': '2025-10-19', 'slave': '2025-10-31', 'baseline': 12, 'midpoint': '2025-10-25'},
]

def load_same_track_velocity(pair_info):
    """Load velocity from same-track pair CSV file."""
    filename = f"track{pair_info['track']}_{pair_info['master'].replace('-', '')}_{pair_info['slave'].replace('-', '')}_vel.csv"
    filepath = SAME_TRACK_DIR / filename
    
    if not filepath.exists():
        return None
    
    try:
        df = pd.read_csv(filepath)
        # Expected columns: date, velocity_m_per_day (or similar)
        if 'velocity_m_per_day' in df.columns:
            return df['velocity_m_per_day'].mean()
        elif 'velocity' in df.columns:
            return df['velocity'].mean()
        else:
            print(f"   ⚠️  Unknown column format in {filename}")
            return None
    except Exception as e:
        print(f"   ⚠️  Error loading {filename}: {e}")
        return None

def find_overlapping_cross_track(same_track_midpoint, cross_track_df, tolerance_days=3):
    """Find overlapping cross-track measurements."""
    midpoint_date = pd.to_datetime(same_track_midpoint)
    
    # Find nearest cross-track measurement
    cross_track_df['date'] = pd.to_datetime(cross_track_df['date'])
    cross_track_df['date_diff'] = (cross_track_df['date'] - midpoint_date).abs()
    
    nearest = cross_track_df.loc[cross_track_df['date_diff'].idxmin()]
    
    if nearest['date_diff'].days <= tolerance_days:
        return nearest['velocity_m_per_day']
    else:
        return None

def compare_same_track_vs_cross_track():
    """Compare same-track and cross-track velocities."""
    print("=" * 80)
    print("SAME-TRACK VALIDATION: Comparing with Cross-Track Pairs")
    print("=" * 80)
    
    # Load cross-track velocities
    print("\n1. Loading cross-track velocity time series...")
    if not CROSS_TRACK_FILE.exists():
        print(f"   ⚠️  Cross-track file not found: {CROSS_TRACK_FILE}")
        return None
    
    cross_track_df = pd.read_csv(CROSS_TRACK_FILE)
    cross_track_df['date'] = pd.to_datetime(cross_track_df['date'])
    print(f"   Loaded {len(cross_track_df)} cross-track measurements")
    
    # Process same-track pairs
    print("\n2. Processing same-track pairs...")
    comparisons = []
    
    for i, pair in enumerate(SAME_TRACK_PAIRS, 1):
        print(f"\n   Pair {i}: Track {pair['track']}, {pair['master']} → {pair['slave']}")
        
        # Load same-track velocity
        same_track_vel = load_same_track_velocity(pair)
        
        if same_track_vel is None:
            print(f"      ⚠️  Same-track velocity not available (needs SNAP processing)")
            continue
        
        print(f"      Same-track velocity: {same_track_vel:.2f} m/day (12-day baseline)")
        
        # Find overlapping cross-track measurement
        cross_track_vel = find_overlapping_cross_track(pair['midpoint'], cross_track_df)
        
        if cross_track_vel is None:
            print(f"      ⚠️  No overlapping cross-track measurement")
            continue
        
        print(f"      Cross-track velocity: {cross_track_vel:.2f} m/day (6-day baseline)")
        
        # Calculate bias (accounting for temporal baseline difference)
        # Same-track is 12-day, cross-track is 6-day
        # If velocities are similar, same-track should be ~2x cross-track for same displacement
        # But we're comparing velocities (m/day), so they should be similar if motion is steady
        bias = cross_track_vel - same_track_vel
        relative_bias_pct = 100 * bias / same_track_vel if same_track_vel > 0 else np.nan
        
        print(f"      Bias (cross-track - same-track): {bias:.2f} m/day ({relative_bias_pct:.1f}%)")
        
        comparisons.append({
            'track': pair['track'],
            'master_date': pair['master'],
            'slave_date': pair['slave'],
            'midpoint_date': pair['midpoint'],
            'baseline_days': pair['baseline'],
            'same_track_velocity_m_per_day': same_track_vel,
            'cross_track_velocity_m_per_day': cross_track_vel,
            'bias_m_per_day': bias,
            'relative_bias_percent': relative_bias_pct,
        })
    
    if len(comparisons) == 0:
        print("\n   ⚠️  No comparisons available - same-track pairs need to be processed first")
        print("   See: organized/scripts/data_processing/SNAP_REPROCESSING_INSTRUCTIONS.md")
        return None
    
    # Create comparison dataframe
    comparison_df = pd.DataFrame(comparisons)
    
    # Calculate overall statistics
    print("\n3. Validation Statistics:")
    print("=" * 80)
    
    mean_bias = comparison_df['bias_m_per_day'].mean()
    std_bias = comparison_df['bias_m_per_day'].std()
    mean_relative_bias = comparison_df['relative_bias_percent'].mean()
    
    print(f"   Number of comparisons: {len(comparison_df)}")
    print(f"   Mean bias: {mean_bias:.2f} m/day ({mean_relative_bias:.1f}%)")
    print(f"   Std bias: {std_bias:.2f} m/day")
    print(f"   Bias range: {comparison_df['bias_m_per_day'].min():.2f} to {comparison_df['bias_m_per_day'].max():.2f} m/day")
    
    # Check if bias exceeds 10% threshold
    max_relative_bias = comparison_df['relative_bias_percent'].abs().max()
    print(f"\n   Maximum relative bias: {max_relative_bias:.1f}%")
    
    if max_relative_bias > 10:
        print(f"\n   ⚠️  WARNING: Bias exceeds 10% threshold!")
        print(f"   Velocity estimates should be revised.")
    else:
        print(f"\n   ✓ Bias within acceptable range (<10%)")
    
    # Save results
    output_file = OUTPUT_DIR / "same_track_cross_track_comparison.csv"
    comparison_df.to_csv(output_file, index=False)
    print(f"\n   ✅ Comparison results saved: {output_file}")
    
    # Create visualization
    create_validation_plot(comparison_df, mean_bias, std_bias)
    
    # Save summary
    summary = {
        'validation_type': 'same_track_vs_cross_track',
        'n_comparisons': len(comparison_df),
        'mean_bias_m_per_day': float(mean_bias),
        'std_bias_m_per_day': float(std_bias),
        'mean_relative_bias_percent': float(mean_relative_bias),
        'max_relative_bias_percent': float(max_relative_bias),
        'bias_exceeds_threshold': max_relative_bias > 10,
        'validation_status': 'needs_revision' if max_relative_bias > 10 else 'acceptable'
    }
    
    summary_file = OUTPUT_DIR / "same_track_validation_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"   ✅ Summary saved: {summary_file}")
    
    return comparison_df, summary

def create_validation_plot(comparison_df, mean_bias, std_bias):
    """Create validation comparison plot."""
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))
    
    # Plot 1: Velocity comparison
    ax1 = axes[0]
    dates = pd.to_datetime(comparison_df['midpoint_date'])
    ax1.plot(dates, comparison_df['same_track_velocity_m_per_day'], 
            'o-', label='Same-track (12-day)', color='blue', markersize=8, linewidth=2)
    ax1.plot(dates, comparison_df['cross_track_velocity_m_per_day'], 
            's-', label='Cross-track (6-day)', color='red', markersize=8, linewidth=2)
    ax1.set_ylabel('Velocity (m/day)', fontsize=12)
    ax1.set_title('Same-Track vs Cross-Track Velocity Comparison', fontsize=14)
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis='x', rotation=45)
    
    # Plot 2: Bias
    ax2 = axes[1]
    ax2.bar(dates, comparison_df['bias_m_per_day'], 
           color=['red' if abs(b) > 0.1 * v else 'green' 
                  for b, v in zip(comparison_df['bias_m_per_day'], 
                                  comparison_df['same_track_velocity_m_per_day'])],
           alpha=0.7)
    ax2.axhline(y=0, color='black', linestyle='--', linewidth=1)
    ax2.set_ylabel('Bias (m/day)', fontsize=12)
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_title(f'Bias: Cross-Track - Same-Track (Mean: {mean_bias:.2f} ± {std_bias:.2f} m/day)', 
                 fontsize=14)
    ax2.grid(True, alpha=0.3)
    ax2.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plot_file = OUTPUT_DIR / "same_track_validation_comparison.png"
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"   ✅ Validation plot saved: {plot_file}")

def main():
    """Main execution."""
    results = compare_same_track_vs_cross_track()
    
    if results is None:
        print("\n" + "=" * 80)
        print("VALIDATION INCOMPLETE")
        print("=" * 80)
        print("\nSame-track pairs need to be processed in SNAP first.")
        print("See: organized/scripts/data_processing/SNAP_REPROCESSING_INSTRUCTIONS.md")
        print("\nAfter processing, place velocity CSV files in:")
        print(f"  {SAME_TRACK_DIR}")
        print("\nExpected filename format:")
        print("  track{orbit}_YYYYMMDD_YYYYMMDD_vel.csv")
    else:
        print("\n" + "=" * 80)
        print("✅ VALIDATION COMPLETE")
        print("=" * 80)

if __name__ == "__main__":
    main()
