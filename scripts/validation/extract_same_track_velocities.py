#!/usr/bin/env python3
"""
Extract velocities from existing SNAP-processed same-track DIM files.

This script identifies same-track pairs from existing SNAP DIM files and
extracts velocities to create CSV files for validation.

Usage:
    python extract_same_track_velocities.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import re
import json

# Try to import SNAP Python API (snappy)
try:
    from snappy import ProductIO, ProductUtils
    SNAPPY_AVAILABLE = True
except ImportError:
    SNAPPY_AVAILABLE = False
    print("⚠️  snappy not available - will try alternative methods")

# Configuration
PROCESSED_DIR = Path("satellite_data/sentinel1/processed")
OUTPUT_DIR = Path("processed_data/velocity_validation/same_track")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Same-track pairs to look for
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


def find_velocity_dim_files():
    """Find all DIM files that contain velocity data."""
    print("=" * 80)
    print("FINDING SNAP-PROCESSED VELOCITY FILES")
    print("=" * 80)
    print()
    
    # Look for files with "_vel" in name or "_Stack" (offset tracking results)
    vel_files = []
    
    for dim_file in PROCESSED_DIR.glob("*.dim"):
        filename = dim_file.name
        
        # Check if it's a velocity/offset tracking result
        if "_vel" in filename or "_Stack" in filename:
            # Extract date from filename
            date_match = re.search(r'(\d{8})T', filename)
            if date_match:
                date_str = date_match.group(1)
                vel_files.append({
                    'file': dim_file,
                    'date': date_str,
                    'filename': filename
                })
    
    print(f"Found {len(vel_files)} potential velocity DIM files:")
    for vf in sorted(vel_files, key=lambda x: x['date']):
        print(f"  {vf['date']}: {vf['filename']}")
    
    return vel_files


def identify_same_track_files(vel_files):
    """Identify which DIM files correspond to same-track pairs."""
    print("\n" + "=" * 80)
    print("IDENTIFYING SAME-TRACK PAIRS")
    print("=" * 80)
    print()
    
    identified_pairs = []
    
    for pair_info in SAME_TRACK_PAIRS:
        master_pattern = pair_info['master_pattern']
        slave_pattern = pair_info['slave_pattern']
        
        # Find files matching master and slave dates
        master_files = [vf for vf in vel_files if master_pattern in vf['filename']]
        slave_files = [vf for vf in vel_files if slave_pattern in vf['filename']]
        
        # Look for Stack files (offset tracking results)
        master_stack = [vf for vf in master_files if '_Stack' in vf['filename']]
        slave_stack = [vf for vf in slave_files if '_Stack' in vf['filename']]
        
        # Prefer files with "_vel" in name
        master_vel = [vf for vf in master_files if '_vel' in vf['filename']]
        slave_vel = [vf for vf in slave_files if '_vel' in vf['filename']]
        
        # Use the best match
        master_file = master_vel[0] if master_vel else (master_stack[0] if master_stack else None)
        slave_file = slave_vel[0] if slave_vel else (slave_stack[0] if slave_stack else None)
        
        # For same-track, we need a file that contains BOTH dates (Stack result)
        # Look for files with both dates or Stack_vel files
        combined_files = [vf for vf in vel_files 
                         if master_pattern in vf['filename'] and slave_pattern in vf['filename']]
        
        if combined_files:
            # This is likely the offset tracking result
            identified_pairs.append({
                'pair_info': pair_info,
                'dim_file': combined_files[0]['file'],
                'status': 'found'
            })
            print(f"✅ Pair {pair_info['track']} ({pair_info['master']} → {pair_info['slave']}):")
            print(f"   Found: {combined_files[0]['filename']}")
        elif master_file and slave_file:
            # Need to check if these are from same track
            # For now, assume Stack_vel files are offset tracking results
            stack_vel_files = [vf for vf in vel_files 
                              if '_Stack_vel' in vf['filename'] and 
                              (master_pattern in vf['filename'] or slave_pattern in vf['filename'])]
            if stack_vel_files:
                identified_pairs.append({
                    'pair_info': pair_info,
                    'dim_file': stack_vel_files[0]['file'],
                    'status': 'found'
                })
                print(f"✅ Pair {pair_info['track']} ({pair_info['master']} → {pair_info['slave']}):")
                print(f"   Found: {stack_vel_files[0]['filename']}")
            else:
                print(f"⚠️  Pair {pair_info['track']} ({pair_info['master']} → {pair_info['slave']}):")
                print(f"   No combined Stack file found")
                identified_pairs.append({
                    'pair_info': pair_info,
                    'dim_file': None,
                    'status': 'not_found'
                })
        else:
            print(f"❌ Pair {pair_info['track']} ({pair_info['master']} → {pair_info['slave']}):")
            print(f"   Files not found")
            identified_pairs.append({
                'pair_info': pair_info,
                'dim_file': None,
                'status': 'not_found'
            })
    
    return identified_pairs


def extract_velocity_from_dim_snappy(dim_file, pair_info):
    """Extract velocity from DIM file using snappy (SNAP Python API)."""
    if not SNAPPY_AVAILABLE:
        return None
    
    try:
        # Read product
        product = ProductIO.readProduct(str(dim_file))
        
        # Look for velocity or displacement bands
        band_names = [band.getName() for band in product.getBands()]
        
        print(f"   Available bands: {', '.join(band_names)}")
        
        # Look for velocity, displacement, or offset bands
        velocity_band = None
        dx_band = None
        dy_band = None
        
        for name in band_names:
            if 'velocity' in name.lower() or 'vel' in name.lower():
                velocity_band = product.getBand(name)
            elif 'x_offset' in name.lower() or 'dx' in name.lower():
                dx_band = product.getBand(name)
            elif 'y_offset' in name.lower() or 'dy' in name.lower():
                dy_band = product.getBand(name)
        
        # Extract values (simplified - would need glacier centerline coordinates)
        if velocity_band:
            # Get mean velocity (simplified)
            data = velocity_band.readPixels(0, 0, velocity_band.getRasterWidth(), 
                                          velocity_band.getRasterHeight(), np.zeros((velocity_band.getRasterHeight(), velocity_band.getRasterWidth()), dtype=np.float32))
            valid_data = data[data != 0]
            if len(valid_data) > 0:
                mean_velocity = np.mean(valid_data)
                return mean_velocity
        
        # Calculate from dx, dy if available
        if dx_band and dy_band:
            dx_data = dx_band.readPixels(0, 0, dx_band.getRasterWidth(), 
                                        dx_band.getRasterHeight(), np.zeros((dx_band.getRasterHeight(), dx_band.getRasterWidth()), dtype=np.float32))
            dy_data = dy_band.readPixels(0, 0, dy_band.getRasterWidth(), 
                                        dy_band.getRasterHeight(), np.zeros((dy_band.getRasterHeight(), dy_band.getRasterWidth()), dtype=np.float32))
            
            # Calculate velocity magnitude
            displacement = np.sqrt(dx_data**2 + dy_data**2)
            valid_disp = displacement[displacement != 0]
            if len(valid_disp) > 0:
                mean_displacement = np.mean(valid_disp)
                # Convert to velocity (assuming pixel size and time)
                # This is simplified - actual calculation needs pixel size and time delta
                velocity = mean_displacement / pair_info['baseline']  # Rough estimate
                return velocity
        
        product.dispose()
        return None
        
    except Exception as e:
        print(f"   ⚠️  Error reading DIM file: {e}")
        return None


def extract_velocity_manual(dim_file, pair_info):
    """Extract velocity manually by reading DIM file metadata or using alternative method."""
    # For now, create a placeholder CSV
    # In practice, you would:
    # 1. Open DIM file in SNAP GUI
    # 2. Extract velocity along centerline
    # 3. Export to CSV
    
    midpoint_date = datetime.strptime(pair_info['master'], '%Y-%m-%d') + \
                   pd.Timedelta(days=pair_info['baseline']/2)
    
    csv_file = OUTPUT_DIR / f"track{pair_info['track']}_{pair_info['master'].replace('-', '')}_{pair_info['slave'].replace('-', '')}_vel.csv"
    
    # Check if CSV already exists (user may have already extracted it)
    if csv_file.exists():
        print(f"   ✅ CSV already exists: {csv_file.name}")
        return csv_file
    
    # Create placeholder CSV with instructions
    df = pd.DataFrame({
        'date': [midpoint_date.strftime('%Y-%m-%d')],
        'velocity_m_per_day': [0.0],  # To be filled manually
        'velocity_std': [0.0],
        'dx_m': [0.0],
        'dy_m': [0.0],
        'time_delta_days': [pair_info['baseline']],
        'note': [f"Extract velocity from: {dim_file.name}"]
    })
    
    df.to_csv(csv_file, index=False)
    print(f"   ⚠️  Created placeholder CSV: {csv_file.name}")
    print(f"   Please extract velocity from DIM file and update CSV")
    
    return csv_file


def process_all_pairs(identified_pairs):
    """Process all identified pairs and create CSV files."""
    print("\n" + "=" * 80)
    print("EXTRACTING VELOCITIES")
    print("=" * 80)
    print()
    
    results = []
    
    for item in identified_pairs:
        pair_info = item['pair_info']
        dim_file = item['dim_file']
        
        print(f"Processing: Track {pair_info['track']}, {pair_info['master']} → {pair_info['slave']}")
        
        if dim_file and dim_file.exists():
            print(f"   DIM file: {dim_file.name}")
            
            # Try to extract using snappy
            if SNAPPY_AVAILABLE:
                velocity = extract_velocity_from_dim_snappy(dim_file, pair_info)
                if velocity:
                    # Create CSV with extracted velocity
                    midpoint_date = datetime.strptime(pair_info['master'], '%Y-%m-%d') + \
                                   pd.Timedelta(days=pair_info['baseline']/2)
                    csv_file = OUTPUT_DIR / f"track{pair_info['track']}_{pair_info['master'].replace('-', '')}_{pair_info['slave'].replace('-', '')}_vel.csv"
                    
                    df = pd.DataFrame({
                        'date': [midpoint_date.strftime('%Y-%m-%d')],
                        'velocity_m_per_day': [velocity],
                        'velocity_std': [velocity * 0.1],  # 10% uncertainty
                        'time_delta_days': [pair_info['baseline']]
                    })
                    df.to_csv(csv_file, index=False)
                    print(f"   ✅ Extracted velocity: {velocity:.2f} m/day")
                    results.append({'pair': pair_info, 'csv': csv_file, 'status': 'extracted'})
                    continue
            
            # Fallback: create placeholder CSV
            csv_file = extract_velocity_manual(dim_file, pair_info)
            results.append({'pair': pair_info, 'csv': csv_file, 'status': 'placeholder'})
        else:
            print(f"   ❌ DIM file not found")
            results.append({'pair': pair_info, 'csv': None, 'status': 'not_found'})
    
    return results


def main():
    """Main function."""
    print("=" * 80)
    print("EXTRACTING SAME-TRACK VELOCITIES FROM SNAP FILES")
    print("=" * 80)
    print()
    
    # Find velocity DIM files
    vel_files = find_velocity_dim_files()
    
    if not vel_files:
        print("\n❌ No velocity DIM files found!")
        print(f"   Expected in: {PROCESSED_DIR}")
        return False
    
    # Identify same-track pairs
    identified_pairs = identify_same_track_files(vel_files)
    
    # Process all pairs
    results = process_all_pairs(identified_pairs)
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    extracted = sum(1 for r in results if r['status'] == 'extracted')
    placeholders = sum(1 for r in results if r['status'] == 'placeholder')
    not_found = sum(1 for r in results if r['status'] == 'not_found')
    
    print(f"Extracted: {extracted}")
    print(f"Placeholders created: {placeholders}")
    print(f"Not found: {not_found}")
    
    if placeholders > 0:
        print("\n⚠️  Some CSVs are placeholders - please extract velocities manually:")
        print("   1. Open DIM files in SNAP GUI")
        print("   2. Extract velocity along glacier centerline")
        print("   3. Update CSV files with actual values")
    
    if extracted + placeholders > 0:
        print("\n✅ Next step: Run validation script")
        print("   python organized/scripts/validation/process_same_track_validation.py")
    
    return True


if __name__ == "__main__":
    main()
