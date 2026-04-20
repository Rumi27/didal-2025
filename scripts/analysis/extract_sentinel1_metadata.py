#!/usr/bin/env python3
"""
Extract complete Sentinel-1 acquisition details and offset-tracking parameters.
Creates a comprehensive metadata document for the paper.
"""

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import re
import json
from datetime import datetime
import pandas as pd

sentinel1_dir = Path('satellite_data/sentinel1')
processed_dir = Path('satellite_data/sentinel1/processed')

print('=' * 80)
print('EXTRACTING COMPLETE SENTINEL-1 METADATA')
print('=' * 80)

# Find all Sentinel-1 products
zip_files = sorted(sentinel1_dir.glob('*.SAFE.zip'))

acquisitions = []

for zip_file in zip_files:
    filename = zip_file.name
    # Parse filename: S1A_IW_GRDH_1SDV_20250907T012223_20250907T012248_060875_0794A5_8F34.SAFE.zip
    parts = filename.split('_')
    
    mission = parts[0]  # S1A
    mode = parts[1]  # IW
    product_type = parts[2]  # GRDH
    level = parts[3]  # 1SDV
    date1_str = parts[5]  # 20250907T012223
    date2_str = parts[6]  # 20250907T012248
    relative_orbit = parts[7]  # 060875 (6 digits)
    
    # Parse dates
    date1 = datetime.strptime(date1_str, '%Y%m%dT%H%M%S')
    
    acquisition = {
        'filename': filename,
        'mission': mission,
        'mode': mode,
        'product_type': product_type,
        'level': level,
        'relative_orbit': relative_orbit,
        'acquisition_date': date1.strftime('%Y-%m-%d'),
        'acquisition_time': date1.strftime('%H:%M:%S'),
        'datetime': date1.isoformat(),
    }
    
    # Extract additional metadata from manifest and annotation files
    try:
        with zipfile.ZipFile(zip_file, 'r') as z:
            # Check manifest
            manifest_files = [f for f in z.namelist() if 'manifest.safe' in f.lower()]
            if manifest_files:
                manifest_data = z.read(manifest_files[0]).decode('utf-8', errors='ignore')
                
                # Orbit direction
                if 'ascending' in manifest_data.lower():
                    acquisition['orbit_direction'] = 'ASCENDING'
                elif 'descending' in manifest_data.lower():
                    acquisition['orbit_direction'] = 'DESCENDING'
                
                # Try to extract more details from annotation files
                ann_files = [f for f in z.namelist() if 'annotation' in f.lower() and '.xml' in f and 'vv' in f.lower()]
                
                if ann_files:
                    ann_data = z.read(ann_files[0]).decode('utf-8', errors='ignore')
                    
                    # Incidence angle
                    inc_matches = re.findall(r'incidenceAngle[^>]*>([0-9.]+)', ann_data)
                    if inc_matches:
                        inc_angles = [float(x) for x in inc_matches]
                        acquisition['incidence_angle_min'] = min(inc_angles)
                        acquisition['incidence_angle_max'] = max(inc_angles)
                        acquisition['incidence_angle_mean'] = sum(inc_angles) / len(inc_angles)
                    
                    # Look for burst information
                    burst_matches = re.findall(r'burst\s*[^>]*>([^<]+)', ann_data, re.IGNORECASE)
                    if burst_matches:
                        acquisition['burst_count'] = len(burst_matches)
                    
                    # Look for swath information
                    if 'IW1' in ann_data:
                        acquisition['swath'] = 'IW1'
                    elif 'IW2' in ann_data:
                        acquisition['swath'] = 'IW2'
                    elif 'IW3' in ann_data:
                        acquisition['swath'] = 'IW3'
                    
    except Exception as e:
        print(f"  Warning: Could not extract full metadata from {filename}: {e}")
    
    acquisitions.append(acquisition)

# Sort by date
acquisitions.sort(key=lambda x: x['datetime'])

# Count pairs
print(f'\nTotal acquisitions: {len(acquisitions)}')
usable_pairs = len(acquisitions) - 1
print(f'Usable consecutive pairs: {usable_pairs}')

# Analyze orbits
relative_orbits = [a['relative_orbit'] for a in acquisitions]
unique_orbits = sorted(set(relative_orbits))
print(f'\nRelative orbits: {unique_orbits}')
print(f'Number of unique orbits: {len(unique_orbits)}')

# Analyze orbit directions
orbit_directions = [a.get('orbit_direction', 'UNKNOWN') for a in acquisitions]
unique_directions = sorted(set(orbit_directions))
print(f'Orbit directions: {unique_directions}')

# Date range
dates = [a['acquisition_date'] for a in acquisitions]
print(f'\nDate range: {dates[0]} to {dates[-1]}')

# Calculate revisit interval
if len(acquisitions) >= 2:
    intervals = []
    for i in range(1, len(acquisitions)):
        d1 = datetime.fromisoformat(acquisitions[i-1]['datetime'])
        d2 = datetime.fromisoformat(acquisitions[i]['datetime'])
        delta = (d2 - d1).days
        intervals.append(delta)
    
    avg_interval = sum(intervals) / len(intervals)
    print(f'Average revisit interval: {avg_interval:.1f} days')

# Check processing scripts for offset-tracking parameters
print('\n' + '=' * 80)
print('OFFSET-TRACKING PARAMETERS (from processing scripts)')
print('=' * 80)

# Parameters from process_sentinel1_velocity.py
params_from_velocity_script = {
    'window_sizes': [32, 64, 128],  # pixels
    'search_range': 100,  # pixels
    'min_correlation': 0.3,
    'stable_bedrock_threshold': 0.1,  # m/day
}

# Parameters from calculate_velocity_python.py
params_from_calc_script = {
    'window_size': 128,  # pixels (primary)
    'search_range': 200,  # pixels
    'step_size': 40,  # pixels (grid spacing)
}

print('\nFrom process_sentinel1_velocity.py:')
print(f'  Window sizes (ensemble): {params_from_velocity_script["window_sizes"]} pixels')
print(f'  Search range: {params_from_velocity_script["search_range"]} pixels')
print(f'  Minimum correlation: {params_from_velocity_script["min_correlation"]}')
print(f'  Stable bedrock threshold: {params_from_velocity_script["stable_bedrock_threshold"]} m/day')

print('\nFrom calculate_velocity_python.py:')
print(f'  Window size (primary): {params_from_calc_script["window_size"]} pixels')
print(f'  Search range: {params_from_calc_script["search_range"]} pixels')
print(f'  Step size (grid spacing): {params_from_calc_script["step_size"]} pixels')

# Check if velocity time series exists to verify number of pairs
ts_file = processed_dir / 'velocity_timeseries_python.csv'
if ts_file.exists():
    df = pd.read_csv(ts_file)
    print(f'\nFrom velocity_timeseries_python.csv:')
    print(f'  Number of velocity measurements: {len(df)}')
    print(f'  Date range: {df["date"].min()} to {df["date"].max()}')

# Save complete metadata
output_file = processed_dir / 'sentinel1_acquisition_metadata.json'
with open(output_file, 'w') as f:
    json.dump({
        'acquisitions': acquisitions,
        'summary': {
            'total_acquisitions': len(acquisitions),
            'usable_pairs': usable_pairs,
            'relative_orbits': unique_orbits,
            'orbit_directions': unique_directions,
            'date_range': {'start': dates[0], 'end': dates[-1]},
            'average_revisit_interval_days': avg_interval if len(acquisitions) >= 2 else None,
        },
        'offset_tracking_parameters': {
            'window_sizes_pixels': params_from_velocity_script['window_sizes'],
            'search_range_range_pixels': params_from_calc_script['search_range'],
            'search_range_azimuth_pixels': params_from_calc_script['search_range'],
            'step_size_pixels': params_from_calc_script['step_size'],
            'min_correlation': params_from_velocity_script['min_correlation'],
            'matching_metric': 'Normalized Cross-Correlation (NCC)',
            'multilooking': 'Applied during terrain correction (GRDH products are already multilooked)',
            'oversampling': 'Not explicitly applied - using pixel-level matching',
        }
    }, f, indent=2)

print(f'\n✅ Complete metadata saved to: {output_file}')

# Print formatted summary
print('\n' + '=' * 80)
print('COMPLETE ACQUISITION DETAILS')
print('=' * 80)
for i, acq in enumerate(acquisitions, 1):
    print(f"\n{i:2d}. {acq['acquisition_date']} {acq['acquisition_time']} UTC")
    print(f"    Mission: {acq['mission']} | Mode: {acq['mode']} | Product: {acq['product_type']}")
    print(f"    Relative Orbit: {acq['relative_orbit']} | Direction: {acq.get('orbit_direction', 'Unknown')}")
    if 'incidence_angle_mean' in acq:
        print(f"    Incidence Angle: {acq['incidence_angle_min']:.2f}° - {acq['incidence_angle_max']:.2f}° (mean: {acq['incidence_angle_mean']:.2f}°)")
    if 'swath' in acq:
        print(f"    Swath: {acq['swath']}")

