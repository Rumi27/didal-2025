#!/usr/bin/env python3
"""
Extract same-track velocities from SNAP Velocity.csv files.

This script reads Velocity.csv files from SNAP DIM data directories,
matches them to same-track pairs, and creates validation CSV files.

Usage:
    python extract_velocities_from_snap_csv.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import re

# Configuration
PROCESSED_DIR = Path("satellite_data/sentinel1/processed")
OUTPUT_DIR = Path("processed_data/velocity_validation/same_track")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Same-track pairs
SAME_TRACK_PAIRS = [
    # Track 78
    {'track': 78, 'master': '2025-09-07', 'slave': '2025-09-19', 'baseline': 12,
     'master_pattern': '20250907', 'slave_pattern': '20250919'},
    {'track': 78, 'master': '2025-09-19', 'slave': '2025-10-01', 'baseline': 12,
     'master_pattern': '20250919', 'slave_pattern': '20251001'},
    {'track': 78, 'master': '2025-10-01', 'slave': '2025-10-13', 'baseline': 12,
     'master_pattern': '20251001', 'slave_pattern': '20251013'},
    {'track': 78, 'master': '2025-10-13', 'slave': '2025-10-25', 'baseline': 11,
     'master_pattern': '20251013', 'slave_pattern': '20251025'},
    # Track 173
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
    """Find all Velocity.csv files in DIM data directories."""
    velocity_files = []
    
    # Search in all subdirectories
    for vel_csv in PROCESSED_DIR.rglob("vector_data/Velocity.csv"):
        # Extract date from any parent directory name
        path_parts = vel_csv.parts
        parent_dir = None
        date_str = None
        
        # Look for directory with date pattern
        for part in path_parts:
            date_match = re.search(r'(\d{8})T', part)
            if date_match:
                date_str = date_match.group(1)
                parent_dir = part
                break
        
        if date_str:
            velocity_files.append({
                'file': vel_csv,
                'date': date_str,
                'parent_dir': parent_dir
            })
    
    return sorted(velocity_files, key=lambda x: x['date'])


def read_velocity_csv(vel_csv_path):
    """Read velocity CSV file and extract velocity values."""
    try:
        # SNAP Velocity.csv files are tab-separated
        # Line 1: CSS styling (starts with #)
        # Line 2: Column headers (tab-separated)
        # Line 3+: Data rows (tab-separated)
        
        with open(vel_csv_path, 'r') as f:
            lines = f.readlines()
        
        if len(lines) < 3:
            return None
        
        # Parse header (line 2, index 1)
        header_line = lines[1].strip()
        headers = header_line.split('\t')
        
        # Find velocity column index - look for "velocity:Double" not just "Velocity"
        velocity_idx = None
        for i, h in enumerate(headers):
            if 'velocity:Double' in h or (h.lower() == 'velocity' and i > 0):  # Skip first "Velocity" column
                velocity_idx = i
                break
        
        if velocity_idx is None:
            print(f"      ⚠️  Could not find velocity column in headers: {headers}")
            return None
        
        # Parse data rows (skip line 0 CSS and line 1 header)
        velocities = []
        for line in lines[2:]:
            line = line.strip()
            if line and not line.startswith('#'):
                parts = line.split('\t')
                if len(parts) > velocity_idx:
                    try:
                        vel = float(parts[velocity_idx])
                        # Accept velocities > 0 (some may be very small)
                        if vel > 0 and np.isfinite(vel):
                            velocities.append(vel)
                    except (ValueError, IndexError):
                        continue
        
        if len(velocities) > 0:
            print(f"      Found {len(velocities)} velocity measurements")
            print(f"      Range: {np.min(velocities):.2f} to {np.max(velocities):.2f} m/day")
            return {
                'mean': np.mean(velocities),
                'median': np.median(velocities),
                'std': np.std(velocities),
                'count': len(velocities),
                'min': np.min(velocities),
                'max': np.max(velocities)
            }
        
        print(f"      No valid velocities found (checked {len(lines)-2} rows)")
        return None
        
    except Exception as e:
        print(f"   ⚠️  Error reading {vel_csv_path.name}: {e}")
        import traceback
        traceback.print_exc()
        return None


def match_files_to_pairs(velocity_files, pair_info):
    """Match velocity files to same-track pairs."""
    master_pattern = pair_info['master_pattern']
    slave_pattern = pair_info['slave_pattern']
    
    # Look for files that contain both dates (Stack result)
    # Or files that match the slave date (end date of pair)
    matching_files = []
    
    for vf in velocity_files:
        filename = vf['parent_dir']
        
        # Check if both dates are in filename (Stack result)
        if master_pattern in filename and slave_pattern in filename:
            matching_files.append(vf)
        # Or check if slave date matches (end date)
        elif slave_pattern in filename:
            matching_files.append(vf)
    
    return matching_files


def process_all_pairs():
    """Process all same-track pairs and extract velocities."""
    print("=" * 80)
    print("EXTRACTING SAME-TRACK VELOCITIES FROM SNAP CSV FILES")
    print("=" * 80)
    print()
    
    # Find all Velocity.csv files
    velocity_files = find_velocity_csv_files()
    print(f"Found {len(velocity_files)} Velocity.csv files")
    print()
    
    results = []
    
    for pair_info in SAME_TRACK_PAIRS:
        print(f"Processing: Track {pair_info['track']}, {pair_info['master']} → {pair_info['slave']}")
        
        # Find matching files
        matching_files = match_files_to_pairs(velocity_files, pair_info)
        
        if not matching_files:
            print(f"   ❌ No matching Velocity.csv file found")
            results.append({'pair': pair_info, 'status': 'not_found', 'velocity': None})
            continue
        
        # Try each matching file
        velocity_data = None
        used_file = None
        
        for vf in matching_files:
            print(f"   Checking: {vf['parent_dir']}")
            vel_data = read_velocity_csv(vf['file'])
            
            if vel_data:
                velocity_data = vel_data
                used_file = vf
                print(f"   ✅ Found velocity data: {vel_data['mean']:.2f} m/day (n={vel_data['count']})")
                break
        
        if velocity_data:
            # Create CSV file
            midpoint_date = datetime.strptime(pair_info['master'], '%Y-%m-%d') + \
                           pd.Timedelta(days=pair_info['baseline']/2)
            
            csv_file = OUTPUT_DIR / f"track{pair_info['track']}_{pair_info['master'].replace('-', '')}_{pair_info['slave'].replace('-', '')}_vel.csv"
            
            df = pd.DataFrame({
                'date': [midpoint_date.strftime('%Y-%m-%d')],
                'velocity_m_per_day': [velocity_data['mean']],
                'velocity_median': [velocity_data['median']],
                'velocity_std': [velocity_data['std']],
                'velocity_min': [velocity_data['min']],
                'velocity_max': [velocity_data['max']],
                'n_points': [velocity_data['count']],
                'time_delta_days': [pair_info['baseline']],
                'source_file': [used_file['parent_dir']]
            })
            
            df.to_csv(csv_file, index=False)
            print(f"   ✅ Saved: {csv_file.name}")
            
            results.append({
                'pair': pair_info,
                'status': 'extracted',
                'velocity': velocity_data['mean'],
                'csv_file': csv_file
            })
        else:
            print(f"   ⚠️  No valid velocity data found")
            results.append({'pair': pair_info, 'status': 'no_data', 'velocity': None})
        
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    extracted = sum(1 for r in results if r['status'] == 'extracted')
    no_data = sum(1 for r in results if r['status'] == 'no_data')
    not_found = sum(1 for r in results if r['status'] == 'not_found')
    
    print(f"✅ Extracted: {extracted}/{len(SAME_TRACK_PAIRS)}")
    print(f"⚠️  No data: {no_data}")
    print(f"❌ Not found: {not_found}")
    
    if extracted > 0:
        print("\n✅ Next step: Run validation script")
        print("   python organized/scripts/validation/process_same_track_validation.py")
    
    return results


if __name__ == "__main__":
    process_all_pairs()
