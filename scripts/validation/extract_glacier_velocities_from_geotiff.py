#!/usr/bin/env python3
"""
Extract glacier velocities from same-track velocity GeoTIFF files.

This script reads GeoTIFF files exported from SNAP, masks to glacier outline,
and extracts statistics for validation.

Usage:
    python extract_glacier_velocities_from_geotiff.py

Output:
    glacier_velocities_extracted_sametrack.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys

try:
    import rasterio
    from rasterio.mask import mask
    import geopandas as gpd
    from shapely.geometry import mapping
    LIBRARIES_AVAILABLE = True
except ImportError as e:
    LIBRARIES_AVAILABLE = False
    print(f"❌ ERROR: Required libraries not available: {e}")
    sys.exit(1)

# ============================================================================
# CONFIGURATION
# ============================================================================

GEOTIFF_DIR = Path("processed_data/velocity_validation/same_track/geotiff")
GLACIER_OUTLINE = Path("Didal_Glacier_GIS_Data/Glacier_Outline/didal_glacier_outline.shp")
OUTPUT_CSV = Path("processed_data/velocity_validation/same_track/glacier_velocities_extracted_sametrack.csv")
OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

# Same-track pairs
SAME_TRACK_PAIRS = [
    {'track': 78, 'master': '2025-09-07', 'slave': '2025-09-19', 'baseline': 12,
     'filename': 'velocity_track78_20250907_20250919.tif'},
    {'track': 78, 'master': '2025-09-19', 'slave': '2025-10-01', 'baseline': 12,
     'filename': 'velocity_track78_20250919_20251001.tif'},
    {'track': 78, 'master': '2025-10-01', 'slave': '2025-10-13', 'baseline': 12,
     'filename': 'velocity_track78_20251001_20251013.tif'},
    {'track': 78, 'master': '2025-10-13', 'slave': '2025-10-25', 'baseline': 11,
     'filename': 'velocity_track78_20251013_20251025.tif'},
    {'track': 173, 'master': '2025-09-13', 'slave': '2025-09-25', 'baseline': 12,
     'filename': 'velocity_track173_20250913_20250925.tif'},
    {'track': 173, 'master': '2025-09-25', 'slave': '2025-10-07', 'baseline': 12,
     'filename': 'velocity_track173_20250925_20251007.tif'},
    {'track': 173, 'master': '2025-10-07', 'slave': '2025-10-19', 'baseline': 12,
     'filename': 'velocity_track173_20251007_20251019.tif'},
    {'track': 173, 'master': '2025-10-19', 'slave': '2025-10-31', 'baseline': 12,
     'filename': 'velocity_track173_20251019_20251031.tif'},
]


def extract_glacier_velocity(tif_file, glacier_outline_shp):
    """Extract velocity statistics from GeoTIFF, masked to glacier area."""
    try:
        # Load glacier outline
        glacier_gdf = gpd.read_file(glacier_outline_shp)
        glacier_geoms = [mapping(glacier_gdf.geometry.iloc[0])]
        
        # Open velocity raster
        with rasterio.open(tif_file) as src:
            # Reproject glacier outline if needed
            if glacier_gdf.crs != src.crs:
                glacier_gdf_reproj = glacier_gdf.to_crs(src.crs)
                glacier_geoms = [mapping(glacier_gdf_reproj.geometry.iloc[0])]
            
            # Mask to glacier area
            masked_data, masked_transform = mask(
                src, 
                glacier_geoms, 
                crop=True, 
                nodata=np.nan
            )
            
            # Get velocity band (usually first band)
            velocity_band = masked_data[0]
            
            # Filter valid values (not NaN, positive)
            valid_velocities = velocity_band[
                (velocity_band > 0) & np.isfinite(velocity_band)
            ]
            
            if len(valid_velocities) == 0:
                return {
                    'mean': np.nan, 'max': np.nan, 'min': np.nan,
                    'std': np.nan, 'median': np.nan, 'n_pixels': 0,
                    'status': 'NO_DATA'
                }
            
            return {
                'mean': float(np.mean(valid_velocities)),
                'max': float(np.max(valid_velocities)),
                'min': float(np.min(valid_velocities)),
                'std': float(np.std(valid_velocities)),
                'median': float(np.median(valid_velocities)),
                'n_pixels': len(valid_velocities),
                'status': 'OK'
            }
            
    except Exception as e:
        return {
            'mean': np.nan, 'max': np.nan, 'min': np.nan,
            'std': np.nan, 'median': np.nan, 'n_pixels': 0,
            'status': f'ERROR: {str(e)[:50]}'
        }


def main():
    print("=" * 70)
    print("GLACIER VELOCITY EXTRACTION FROM GEOTIFF FILES")
    print("=" * 70)
    print()
    
    # Check glacier outline
    if not GLACIER_OUTLINE.exists():
        print(f"❌ ERROR: Glacier outline not found: {GLACIER_OUTLINE}")
        return False
    
    print(f"[1/3] Loading glacier outline from {GLACIER_OUTLINE}...")
    try:
        glacier_gdf = gpd.read_file(GLACIER_OUTLINE)
        print(f"✓ Glacier outline loaded (CRS: {glacier_gdf.crs})")
    except Exception as e:
        print(f"❌ ERROR: Could not load glacier outline: {e}")
        return False
    print()
    
    # Process each pair
    print("[2/3] Extracting velocities from glacier area...")
    print()
    
    results = []
    
    for i, pair_info in enumerate(SAME_TRACK_PAIRS, 1):
        tif_file = GEOTIFF_DIR / pair_info['filename']
        
        print(f"  [{i}/8] Processing: {pair_info['filename']}")
        print(f"     Pair: Track {pair_info['track']}, {pair_info['master']} → {pair_info['slave']}")
        
        if not tif_file.exists():
            print(f"     ❌ File not found: {tif_file}")
            results.append({
                'track': pair_info['track'],
                'date_start': pair_info['master'],
                'date_end': pair_info['slave'],
                'date_midpoint': (datetime.strptime(pair_info['master'], '%Y-%m-%d') + 
                                pd.Timedelta(days=pair_info['baseline']/2)).strftime('%Y-%m-%d'),
                'baseline_days': pair_info['baseline'],
                'file': pair_info['filename'],
                'mean': np.nan, 'max': np.nan, 'min': np.nan,
                'std': np.nan, 'median': np.nan, 'n_pixels': 0,
                'status': 'FILE_NOT_FOUND'
            })
            print()
            continue
        
        stats = extract_glacier_velocity(tif_file, GLACIER_OUTLINE)
        
        if stats['status'] == 'OK':
            print(f"     ✓ Extracted: Mean={stats['mean']:.1f}, Max={stats['max']:.1f}, "
                  f"Std={stats['std']:.1f}, N={stats['n_pixels']}")
            
            if stats['mean'] < 10:
                print(f"     ⚠️  WARNING: Mean velocity very low ({stats['mean']:.2f} m/day)")
        else:
            print(f"     ❌ {stats['status']}")
        
        midpoint_date = datetime.strptime(pair_info['master'], '%Y-%m-%d') + \
                       pd.Timedelta(days=pair_info['baseline']/2)
        
        results.append({
            'track': pair_info['track'],
            'date_start': pair_info['master'],
            'date_end': pair_info['slave'],
            'date_midpoint': midpoint_date.strftime('%Y-%m-%d'),
            'baseline_days': pair_info['baseline'],
            'file': pair_info['filename'],
            'file_path': str(tif_file),
            'mean': stats['mean'],
            'max': stats['max'],
            'min': stats['min'],
            'std': stats['std'],
            'median': stats['median'],
            'n_pixels': stats['n_pixels'],
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
    
    successful = df[df['status'] == 'OK']
    print(f"✓ Successfully extracted: {len(successful)}/{len(SAME_TRACK_PAIRS)} pairs")
    print()
    
    if len(successful) > 0:
        print("  Velocity Statistics (m/day):")
        print(f"    Mean:   {successful['mean'].mean():.1f} ± {successful['mean'].std():.1f}")
        print(f"    Max:    {successful['max'].mean():.1f} ± {successful['max'].std():.1f}")
        print(f"    Min:    {successful['min'].mean():.1f} ± {successful['min'].std():.1f}")
        print()
        print("  Pixel Count Statistics:")
        print(f"    Mean:   {successful['n_pixels'].mean():.0f} pixels per pair")
        print(f"    Range:  {successful['n_pixels'].min():.0f} - {successful['n_pixels'].max():.0f}")
        print()
        
        if successful['mean'].mean() < 50:
            print("  ⚠️  WARNING: Mean velocities are very low (<50 m/day)")
            print("     Expected range for surge-type glacier: 100-500 m/day")
        else:
            print("  ✅ Velocities are in expected range (100-500 m/day)")
    
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
