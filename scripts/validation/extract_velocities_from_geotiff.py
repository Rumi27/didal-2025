#!/usr/bin/env python3
"""
Extract same-track velocities from velocity GeoTIFF files, masking to glacier area only.

This script:
1. Loads velocity GeoTIFF files
2. Masks to glacier outline
3. Extracts velocities along centerline or from glacier area
4. Creates CSV files for validation

Usage:
    python extract_velocities_from_geotiff.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import re

try:
    import rasterio
    from rasterio.mask import mask
    import geopandas as gpd
    from shapely.geometry import mapping
    RASTERIO_AVAILABLE = True
except ImportError as e:
    RASTERIO_AVAILABLE = False
    print(f"⚠️  rasterio/geopandas not available: {e}")
    print("   Install with: pip install rasterio geopandas")

# Configuration
VELOCITY_MAPS_DIR = Path("Didal_Glacier_GIS_Data/Velocity_Maps")
GLACIER_OUTLINE = Path("Didal_Glacier_GIS_Data/Glacier_Outline/didal_glacier_outline.shp")
OUTPUT_DIR = Path("processed_data/velocity_validation/same_track")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Glacier centerline location (approximate)
GLACIER_LAT = 38.97
GLACIER_LON = 70.72

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


def find_velocity_geotiff_files():
    """Find velocity GeoTIFF files."""
    velocity_files = []
    
    for tif_file in VELOCITY_MAPS_DIR.glob("velocity_*.tif"):
        # Extract dates from filename: velocity_YYYYMMDD_YYYYMMDD.tif
        date_match = re.findall(r'(\d{8})', tif_file.stem)
        
        if len(date_match) >= 2:
            velocity_files.append({
                'file': tif_file,
                'date1': date_match[0],
                'date2': date_match[1]
            })
        elif len(date_match) == 1:
            velocity_files.append({
                'file': tif_file,
                'date1': date_match[0],
                'date2': date_match[0]  # Same date (single-date map)
            })
    
    return sorted(velocity_files, key=lambda x: x['date1'])


def extract_glacier_velocities(tif_file, glacier_outline_shp):
    """Extract velocities from GeoTIFF, masked to glacier area."""
    if not RASTERIO_AVAILABLE:
        return None
    
    try:
        # Load glacier outline
        glacier_gdf = gpd.read_file(glacier_outline_shp)
        glacier_geom = [mapping(glacier_gdf.geometry.iloc[0])]
        
        # Open velocity raster
        with rasterio.open(tif_file) as src:
            # Mask to glacier area
            masked_data, masked_transform = mask(src, glacier_geom, crop=True, nodata=np.nan)
            
            # Get velocity band (usually first band)
            velocity_band = masked_data[0]
            
            # Filter valid values (not NaN, not 0, positive)
            valid_velocities = velocity_band[(velocity_band > 0) & np.isfinite(velocity_band)]
            
            if len(valid_velocities) > 0:
                return {
                    'mean': float(np.mean(valid_velocities)),
                    'median': float(np.median(valid_velocities)),
                    'std': float(np.std(valid_velocities)),
                    'count': len(valid_velocities),
                    'min': float(np.min(valid_velocities)),
                    'max': float(np.max(valid_velocities))
                }
        
        return None
        
    except Exception as e:
        print(f"   ⚠️  Error processing {tif_file.name}: {e}")
        import traceback
        traceback.print_exc()
        return None


def match_files_to_pairs(velocity_files, pair_info):
    """Match velocity GeoTIFF files to same-track pairs."""
    master_pattern = pair_info['master_pattern']
    slave_pattern = pair_info['slave_pattern']
    
    # Look for files with both dates (pair result)
    matching_files = []
    
    for vf in velocity_files:
        # Check if both dates match
        if vf['date1'] == master_pattern and vf['date2'] == slave_pattern:
            matching_files.append(vf)
        # Or if slave date matches (end date of pair)
        elif vf['date2'] == slave_pattern:
            matching_files.append(vf)
    
    return matching_files


def process_all_pairs():
    """Process all same-track pairs."""
    print("=" * 80)
    print("EXTRACTING SAME-TRACK VELOCITIES FROM GEOTIFF FILES")
    print("=" * 80)
    print()
    
    if not RASTERIO_AVAILABLE:
        print("❌ rasterio/geopandas not available")
        print("   Install with: pip install rasterio geopandas")
        return False
    
    # Find velocity GeoTIFF files
    velocity_files = find_velocity_geotiff_files()
    print(f"Found {len(velocity_files)} velocity GeoTIFF files")
    for vf in velocity_files:
        print(f"  {vf['date1']} → {vf['date2']}: {vf['file'].name}")
    print()
    
    # Check glacier outline
    if not GLACIER_OUTLINE.exists():
        print(f"❌ Glacier outline not found: {GLACIER_OUTLINE}")
        return False
    
    print(f"✅ Glacier outline found: {GLACIER_OUTLINE.name}")
    print()
    
    results = []
    
    for pair_info in SAME_TRACK_PAIRS:
        print(f"Processing: Track {pair_info['track']}, {pair_info['master']} → {pair_info['slave']}")
        
        # Find matching files
        matching_files = match_files_to_pairs(velocity_files, pair_info)
        
        if not matching_files:
            print(f"   ❌ No matching GeoTIFF file found")
            results.append({'pair': pair_info, 'status': 'not_found'})
            continue
        
        # Process first matching file
        vf = matching_files[0]
        print(f"   Using: {vf['file'].name}")
        
        # Extract velocities
        velocity_data = extract_glacier_velocities(vf['file'], GLACIER_OUTLINE)
        
        if velocity_data:
            print(f"   ✅ Extracted: {velocity_data['mean']:.2f} m/day (n={velocity_data['count']})")
            print(f"      Range: {velocity_data['min']:.2f} to {velocity_data['max']:.2f} m/day")
            
            # Create CSV
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
                'n_pixels': [velocity_data['count']],
                'time_delta_days': [pair_info['baseline']],
                'source_file': [vf['file'].name]
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
            print(f"   ⚠️  No valid velocity data extracted")
            results.append({'pair': pair_info, 'status': 'no_data'})
        
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
    
    return extracted > 0


if __name__ == "__main__":
    process_all_pairs()
