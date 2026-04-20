#!/usr/bin/env python3
"""
Extract glacier velocities from Velocity.csv files (alternative method).

Since ENVI .img files lack georeferencing, this script uses the Velocity.csv
files which contain point measurements with lat/lon coordinates.

Usage:
    python extract_glacier_velocities_from_csv.py

Output:
    glacier_velocities_extracted_sametrack.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import re
import sys

# ============================================================================
# CONFIGURATION
# ============================================================================

PROCESSED_DIR = Path("satellite_data/sentinel1/processed")
OUTPUT_CSV = Path("processed_data/velocity_validation/same_track/glacier_velocities_extracted_sametrack.csv")
OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

# Glacier approximate bounds (from Didal Glacier location)
# These should match your glacier outline extent
GLACIER_LAT_MIN = 38.95
GLACIER_LAT_MAX = 39.05
GLACIER_LON_MIN = 70.65
GLACIER_LON_MAX = 70.80

# Same-track pairs
SAME_TRACK_PAIRS = [
    {'track': 78, 'master': '2025-09-07', 'slave': '2025-09-19', 'baseline': 12,
     'master_pattern': '20250907', 'slave_pattern': '20250919'},
    {'track': 78, 'master': '2025-09-19', 'slave': '2025-10-01', 'baseline': 12,
     'master_pattern': '20250919', 'slave_pattern': '20251001'},
    {'track': 78, 'master': '2025-10-01', 'slave': '2025-10-13', 'baseline': 12,
     'master_pattern': '20251001', 'slave_pattern': '20251013'},
    {'track': 78, 'master': '2025-10-13', 'slave': '2025-10-25', 'baseline': 11,
     'master_pattern': '20251013', 'slave_pattern': '20251025'},
    {'track': 173, 'master': '2025-09-13', 'slave': '2025-09-25', 'baseline': 12,
     'master_pattern': '20250913', 'slave_pattern': '20250925'},
    {'track': 173, 'master': '2025-09-25', 'slave': '2025-10-07', 'baseline': 12,
     'master_pattern': '20250925', 'slave_pattern': '20251007'},
    {'track': 173, 'master': '2025-10-07', 'slave': '2025-10-19', 'baseline': 12,
     'master_pattern': '20251007', 'slave_pattern': '20251019'},
    {'track': 173, 'master': '2025-10-19', 'slave': '2025-10-31', 'baseline': 12,
     'master_pattern': '20251019', 'slave_pattern': '20251031'},
]


def find_velocity_csv_files():
    """Find all Velocity.csv files in DIM .data/vector_data directories."""
    csv_files = []
    
    for csv_file in PROCESSED_DIR.rglob("vector_data/Velocity.csv"):
        csv_files.append(csv_file)
    
    return sorted(csv_files)


def read_velocity_csv(csv_path):
    """
    Read Velocity.csv file and extract velocities within glacier bounds.
    
    Returns:
        dict with mean, max, min, std, median, n_points, status
    """
    try:
        with open(csv_path, 'r') as f:
            lines = f.readlines()
        
        if len(lines) < 3:
            return None
        
        # Parse header (line 2, index 1)
        header_line = lines[1].strip()
        headers = header_line.split('\t')
        
        # Find column indices
        velocity_idx = None
        lat_idx = None
        lon_idx = None
        
        for i, h in enumerate(headers):
            if 'velocity:Double' in h or (h.lower() == 'velocity' and i > 0):
                velocity_idx = i
            if 'mst_lat' in h.lower() or ('lat' in h.lower() and 'lon' not in h.lower()):
                lat_idx = i
            if 'mst_lon' in h.lower() or ('lon' in h.lower()):
                lon_idx = i
        
        if velocity_idx is None:
            return None
        
        # Parse data and filter to glacier area
        velocities = []
        for line in lines[2:]:
            line = line.strip()
            if line and not line.startswith('#'):
                parts = line.split('\t')
                if len(parts) > max(velocity_idx, lat_idx or 0, lon_idx or 0):
                    try:
                        vel = float(parts[velocity_idx])
                        
                        # Filter by location if coordinates available
                        if lat_idx is not None and lon_idx is not None:
                            lat = float(parts[lat_idx])
                            lon = float(parts[lon_idx])
                            
                            # Check if within glacier bounds
                            if not (GLACIER_LAT_MIN <= lat <= GLACIER_LAT_MAX and 
                                   GLACIER_LON_MIN <= lon <= GLACIER_LON_MAX):
                                continue  # Skip points outside glacier area
                        
                        # Filter valid velocities (positive, > 0.1 m/day to exclude noise)
                        if vel > 0.1 and np.isfinite(vel):
                            velocities.append(vel)
                    except (ValueError, IndexError):
                        continue
        
        if len(velocities) > 0:
            return {
                'mean': np.mean(velocities),
                'max': np.max(velocities),
                'min': np.min(velocities),
                'std': np.std(velocities),
                'median': np.median(velocities),
                'count': len(velocities),
                'status': 'OK'
            }
        
        return {'status': 'NO_DATA', 'count': 0}
        
    except Exception as e:
        return {'status': f'ERROR: {str(e)[:50]}', 'count': 0}


def match_file_to_pair(csv_file, pairs):
    """Match CSV file to same-track pair based on directory name."""
    parent_dir = csv_file.parent.parent.name
    
    for pair in pairs:
        master_pattern = pair['master_pattern']
        slave_pattern = pair['slave_pattern']
        
        # Check if both dates appear in directory name
        if master_pattern in parent_dir and slave_pattern in parent_dir:
            return pair
        # Or check if slave date matches (end date)
        elif slave_pattern in parent_dir:
            return pair
    
    return None


def main():
    print("=" * 70)
    print("GLACIER VELOCITY EXTRACTION FROM Velocity.csv FILES")
    print("=" * 70)
    print()
    print(f"Glacier bounds: Lat {GLACIER_LAT_MIN}-{GLACIER_LAT_MAX}, Lon {GLACIER_LON_MIN}-{GLACIER_LON_MAX}")
    print()
    
    # Find CSV files
    print(f"[1/3] Searching for Velocity.csv files in {PROCESSED_DIR}...")
    csv_files = find_velocity_csv_files()
    
    if len(csv_files) == 0:
        print(f"❌ ERROR: No Velocity.csv files found")
        return False
    
    print(f"✓ Found {len(csv_files)} Velocity.csv files")
    print()
    
    # Extract velocities
    print("[2/3] Extracting velocities from glacier area...")
    print()
    
    results = []
    matched_pairs = set()
    
    for i, csv_file in enumerate(csv_files, 1):
        pair_info = match_file_to_pair(csv_file, SAME_TRACK_PAIRS)
        
        if pair_info is None:
            continue
        
        pair_key = f"Track{pair_info['track']}_{pair_info['master']}_{pair_info['slave']}"
        if pair_key in matched_pairs:
            continue
        
        matched_pairs.add(pair_key)
        
        print(f"  [{len(matched_pairs)}/8] Processing: {csv_file.parent.parent.name}")
        print(f"     Pair: Track {pair_info['track']}, {pair_info['master']} → {pair_info['slave']}")
        
        stats = read_velocity_csv(csv_file)
        
        if stats and stats.get('status') == 'OK':
            print(f"     ✓ Extracted: Mean={stats['mean']:.1f}, Max={stats['max']:.1f}, "
                  f"Std={stats['std']:.1f}, N={stats['count']}")
            
            if stats['mean'] < 10:
                print(f"     ⚠️  WARNING: Mean velocity very low ({stats['mean']:.2f} m/day)")
        else:
            print(f"     ❌ {stats.get('status', 'UNKNOWN') if stats else 'NO_DATA'}")
        
        midpoint_date = datetime.strptime(pair_info['master'], '%Y-%m-%d') + \
                       pd.Timedelta(days=pair_info['baseline']/2)
        
        if stats and stats.get('status') == 'OK':
            results.append({
                'track': pair_info['track'],
                'date_start': pair_info['master'],
                'date_end': pair_info['slave'],
                'date_midpoint': midpoint_date.strftime('%Y-%m-%d'),
                'baseline_days': pair_info['baseline'],
                'file': csv_file.name,
                'file_path': str(csv_file),
                'mean': stats['mean'],
                'max': stats['max'],
                'min': stats['min'],
                'std': stats['std'],
                'median': stats['median'],
                'n_pixels': stats['count'],
                'status': stats['status']
            })
        print()
    
    # Save results
    print("[3/3] Saving results...")
    
    if len(results) == 0:
        print("❌ ERROR: No velocities extracted")
        return False
    
    df = pd.DataFrame(results)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"✓ Results saved to {OUTPUT_CSV}")
    print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY STATISTICS")
    print("=" * 70)
    print()
    print(f"✓ Successfully extracted: {len(results)}/{len(SAME_TRACK_PAIRS)} pairs")
    print()
    
    if len(results) > 0:
        print("  Velocity Statistics (m/day):")
        print(f"    Mean:   {df['mean'].mean():.1f} ± {df['mean'].std():.1f}")
        print(f"    Max:    {df['max'].mean():.1f} ± {df['max'].std():.1f}")
        print(f"    Min:    {df['min'].mean():.1f} ± {df['min'].std():.1f}")
        print()
        print("  Point Count Statistics:")
        print(f"    Mean:   {df['n_pixels'].mean():.0f} points per pair")
        print(f"    Range:  {df['n_pixels'].min():.0f} - {df['n_pixels'].max():.0f}")
        print()
        
        if df['mean'].mean() < 50:
            print("  ⚠️  WARNING: Mean velocities are very low (<50 m/day)")
            print("     Expected range for surge-type glacier: 100-500 m/day")
    
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
