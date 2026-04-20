#!/usr/bin/env python3
"""
Apply bias correction to velocity time series.

This script applies empirical bias correction:
- V_corrected = V_raw - μ_stable
- Uncertainty = ±σ_stable

Usage:
    python apply_bias_correction.py
"""

import pandas as pd
import os
from pathlib import Path

# Configuration
TRACK78_CSV = "processed_data/velocity_timeseries/track78_velocity_timeseries.csv"
TRACK173_CSV = "processed_data/velocity_timeseries/track173_velocity_timeseries.csv"
STATISTICS_CSV = "processed_data/stable_ground_statistics.csv"
OUTPUT_DIR = "processed_data/velocity_timeseries/"

def load_data(track_csv, stats_csv):
    """Load velocity time series and stable ground statistics."""
    if not os.path.exists(track_csv):
        raise FileNotFoundError(f"Velocity time series not found: {track_csv}")
    
    if not os.path.exists(stats_csv):
        raise FileNotFoundError(f"Stable ground statistics not found: {stats_csv}")
    
    velocities = pd.read_csv(track_csv)
    stats = pd.read_csv(stats_csv)
    
    return velocities, stats

def apply_bias_correction(velocities, stats):
    """Apply bias correction to velocities."""
    # Merge statistics with velocities based on date range
    # This assumes statistics CSV has date1 and date2 columns matching velocity pairs
    
    corrected = velocities.copy()
    
    # Try to match statistics to velocities
    if 'date1' in velocities.columns and 'date2' in velocities.columns:
        # Merge on date range
        merged = velocities.merge(
            stats,
            on=['date1', 'date2'],
            how='left',
            suffixes=('', '_stats')
        )
    else:
        # Try to match by pair number or other identifier
        # For now, assume statistics are in same order as velocities
        if len(stats) == len(velocities):
            merged = pd.concat([velocities, stats[['mu_stable', 'sigma_stable']]], axis=1)
        else:
            raise ValueError("Cannot match statistics to velocities. Check date ranges or pair IDs.")
    
    # Apply correction
    if 'velocity' in merged.columns:
        vel_col = 'velocity'
    elif 'velocity_mean' in merged.columns:
        vel_col = 'velocity_mean'
    else:
        raise ValueError("Velocity column not found. Expected 'velocity' or 'velocity_mean'")
    
    # Calculate corrected velocity
    merged['velocity_corrected'] = merged[vel_col] - merged['mu_stable']
    merged['uncertainty'] = merged['sigma_stable']
    
    # Calculate LOD
    merged['lod'] = merged['mu_stable'] + 2 * merged['sigma_stable']
    
    return merged

def main():
    """Main execution."""
    print("=" * 80)
    print("APPLYING BIAS CORRECTION TO VELOCITY TIME SERIES")
    print("=" * 80)
    
    # Check if files exist
    files_exist = {
        'track78': os.path.exists(TRACK78_CSV),
        'track173': os.path.exists(TRACK173_CSV),
        'statistics': os.path.exists(STATISTICS_CSV)
    }
    
    print("\nFile Status:")
    for name, exists in files_exist.items():
        status = "✓" if exists else "✗"
        print(f"  {status} {name}: {exists}")
    
    if not files_exist['statistics']:
        print("\n⚠️  Stable ground statistics not found.")
        print("   Please run: python extract_stable_ground_statistics.py")
        print("   (Requires stable ground mask first)")
        return
    
    # Process Track 78
    if files_exist['track78']:
        print(f"\nProcessing Track 78: {TRACK78_CSV}")
        try:
            velocities, stats = load_data(TRACK78_CSV, STATISTICS_CSV)
            corrected = apply_bias_correction(velocities, stats)
            
            output_path = os.path.join(OUTPUT_DIR, "track78_velocity_timeseries_corrected.csv")
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            corrected.to_csv(output_path, index=False)
            
            print(f"  ✓ Bias correction applied")
            print(f"  ✓ Saved to: {output_path}")
            print(f"\n  Statistics:")
            print(f"    Mean bias: {corrected['mu_stable'].mean():.3f} m/day")
            print(f"    Mean uncertainty: {corrected['uncertainty'].mean():.3f} m/day")
            print(f"    Mean LOD: {corrected['lod'].mean():.3f} m/day")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
    else:
        print(f"\n⚠️  Track 78 data not found: {TRACK78_CSV}")
        print("   This requires SNAP re-processing first")
    
    # Process Track 173
    if files_exist['track173']:
        print(f"\nProcessing Track 173: {TRACK173_CSV}")
        try:
            velocities, stats = load_data(TRACK173_CSV, STATISTICS_CSV)
            corrected = apply_bias_correction(velocities, stats)
            
            output_path = os.path.join(OUTPUT_DIR, "track173_velocity_timeseries_corrected.csv")
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            corrected.to_csv(output_path, index=False)
            
            print(f"  ✓ Bias correction applied")
            print(f"  ✓ Saved to: {output_path}")
            print(f"\n  Statistics:")
            print(f"    Mean bias: {corrected['mu_stable'].mean():.3f} m/day")
            print(f"    Mean uncertainty: {corrected['uncertainty'].mean():.3f} m/day")
            print(f"    Mean LOD: {corrected['lod'].mean():.3f} m/day")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
    else:
        print(f"\n⚠️  Track 173 data not found: {TRACK173_CSV}")
        print("   This requires SNAP re-processing first")
    
    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
