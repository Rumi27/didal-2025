#!/usr/bin/env python3
"""
Extract glacier velocities from same-track Sentinel-1 ENVI .img files.

This script:
1. Finds Velocity_slv1_*.img files in DIM .data directories
2. Masks each velocity raster to glacier outline polygon
3. Extracts statistics (mean, max, std, median, n_pixels) from glacier area only
4. Outputs CSV file with results for all 8 same-track pairs

Usage:
    python extract_glacier_velocities.py

Output:
    glacier_velocities_extracted_sametrack.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import re
import sys

try:
    import rasterio
    from rasterio.mask import mask
    from rasterio.warp import calculate_default_transform, reproject, Resampling
    import geopandas as gpd
    from shapely.geometry import mapping
    LIBRARIES_AVAILABLE = True
except ImportError as e:
    LIBRARIES_AVAILABLE = False
    print(f"❌ ERROR: Required libraries not available: {e}")
    print("   Install with: pip install rasterio geopandas shapely")
    sys.exit(1)

# ============================================================================
# CONFIGURATION - ADJUST THESE PATHS IF NEEDED
# ============================================================================

# Directory containing processed Sentinel-1 data
# Script will search recursively for Velocity_slv1_*.img files
VELOCITY_DIR = Path("satellite_data/sentinel1/processed")

# Glacier outline shapefile (must include .shp, .shx, .dbf, .prj files)
GLACIER_OUTLINE = Path("Didal_Glacier_GIS_Data/Glacier_Outline/didal_glacier_outline.shp")

# Output CSV file
OUTPUT_CSV = Path("processed_data/velocity_validation/same_track/glacier_velocities_extracted_sametrack.csv")

# Create output directory if it doesn't exist
OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

# ============================================================================
# SAME-TRACK PAIR DEFINITIONS
# ============================================================================

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


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def find_velocity_img_files(velocity_dir):
    """
    Find all Velocity_slv1_*.img files in DIM .data directories.
    
    Returns:
        list of Path objects to .img files
    """
    velocity_files = []
    
    # Search recursively for ENVI .img files
    for img_file in velocity_dir.rglob("Velocity_slv1_*.img"):
        # Verify .hdr file exists
        hdr_file = img_file.with_suffix('.hdr')
        if hdr_file.exists():
            velocity_files.append(img_file)
        else:
            print(f"⚠️  Warning: {img_file.name} found but no .hdr file")
    
    return sorted(velocity_files)


def match_file_to_pair(img_file, pairs):
    """
    Match a velocity .img file to a same-track pair based on filename/directory.
    
    Handles multiple date formats:
    - YYYYMMDD (e.g., 20250913)
    - DDMonYYYY (e.g., 13Sep2025)
    - ISO format (e.g., 2025-09-13)
    
    Returns:
        dict: Pair info if matched, None otherwise
    """
    filename = img_file.name
    parent_dir = img_file.parent.parent.name  # Get directory name (e.g., ..._Stack_vel.data)
    
    # Extract dates from filename or directory - try multiple formats
    date_matches = []
    
    # Format 1: YYYYMMDD (8 digits)
    date_matches.extend(re.findall(r'(\d{8})', filename + parent_dir))
    
    # Format 2: DDMonYYYY (e.g., 13Sep2025)
    month_map = {'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
                 'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
                 'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'}
    
    for month_name, month_num in month_map.items():
        pattern = r'(\d{2})' + month_name + r'(\d{4})'
        matches = re.findall(pattern, filename + parent_dir)
        for day, year in matches:
            date_matches.append(f"{year}{month_num}{day}")
    
    # Format 3: ISO format (YYYY-MM-DD)
    iso_matches = re.findall(r'(\d{4})-(\d{2})-(\d{2})', filename + parent_dir)
    for year, month, day in iso_matches:
        date_matches.append(f"{year}{month}{day}")
    
    # Now try to match to pairs
    for pair in pairs:
        master_pattern = pair['master_pattern']  # e.g., '20250907'
        slave_pattern = pair['slave_pattern']    # e.g., '20250919'
        
        # Check if both dates appear in extracted dates
        master_found = master_pattern in date_matches
        slave_found = slave_pattern in date_matches
        
        if master_found and slave_found:
            return pair
        
        # Also check if slave date matches (end date of pair) - this is the velocity product date
        if slave_found:
            # Check parent directory for master date to confirm it's the right pair
            if master_pattern in parent_dir:
                return pair
            # If only slave date found, it's likely the velocity product for that pair
            # (velocity products are typically named after the slave/end date)
            return pair
    
    return None


def extract_glacier_velocity(img_file, glacier_outline_shp):
    """
    Extract velocity statistics from ENVI .img file, masked to glacier area.
    
    Args:
        img_file: Path to Velocity_slv1_*.img file
        glacier_outline_shp: Path to glacier outline shapefile
    
    Returns:
        dict with mean, max, min, std, median, n_pixels, status
    """
    try:
        # Load glacier outline
        glacier_gdf = gpd.read_file(glacier_outline_shp)
        
        # Convert to list of geometries for rasterio.mask
        glacier_geoms = [mapping(glacier_gdf.geometry.iloc[0])]
        
        # Open velocity raster
        with rasterio.open(img_file) as src:
            # Get raster CRS - handle case where CRS is None (unreferenced)
            raster_crs = src.crs
            
            # If raster has no CRS, try to infer from DIM file or use UTM zone 42N (typical for this region)
            if raster_crs is None:
                # Check parent directory for DIM file that might have CRS info
                dim_file = img_file.parent.parent / (img_file.parent.parent.stem + '.dim')
                if dim_file.exists():
                    # Try to read CRS from DIM metadata (would need XML parsing)
                    # For now, assume UTM 42N (EPSG:32642) which is standard for this region
                    from rasterio import crs as rio_crs
                    raster_crs = rio_crs.CRS.from_epsg(32642)
                else:
                    # Default to UTM 42N for Tajikistan region
                    from rasterio import crs as rio_crs
                    raster_crs = rio_crs.CRS.from_epsg(32642)
            
            # Reproject glacier outline if needed
            if glacier_gdf.crs != raster_crs:
                if raster_crs is not None:
                    glacier_gdf_reproj = glacier_gdf.to_crs(raster_crs)
                    glacier_geoms = [mapping(glacier_gdf_reproj.geometry.iloc[0])]
                else:
                    # If still no CRS, use glacier outline as-is (may cause issues)
                    print(f"   ⚠️  Warning: Raster has no CRS, using glacier outline CRS directly")
                    glacier_geoms = [mapping(glacier_gdf.geometry.iloc[0])]
            
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
                    'mean': np.nan,
                    'max': np.nan,
                    'min': np.nan,
                    'std': np.nan,
                    'median': np.nan,
                    'n_pixels': 0,
                    'status': 'NO_DATA'
                }
            
            # Compute statistics
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
        print(f"   ❌ Error processing {img_file.name}: {e}")
        import traceback
        traceback.print_exc()
        return {
            'mean': np.nan,
            'max': np.nan,
            'min': np.nan,
            'std': np.nan,
            'median': np.nan,
            'n_pixels': 0,
            'status': f'ERROR: {str(e)[:50]}'
        }


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("=" * 70)
    print("GLACIER VELOCITY EXTRACTION FROM ENVI .img FILES")
    print("=" * 70)
    print()
    
    # Step 1: Find velocity files
    print(f"[1/4] Searching for velocity files in {VELOCITY_DIR}...")
    velocity_files = find_velocity_img_files(VELOCITY_DIR)
    
    if len(velocity_files) == 0:
        print(f"❌ ERROR: No Velocity_slv1_*.img files found in {VELOCITY_DIR}")
        print("   Check that:")
        print("   1. SNAP processing completed successfully")
        print("   2. Files are in DIM .data subdirectories")
        print("   3. VELOCITY_DIR path is correct")
        return False
    
    print(f"✓ Found {len(velocity_files)} velocity files")
    print()
    
    # Step 2: Load glacier outline
    print(f"[2/4] Loading glacier outline from {GLACIER_OUTLINE}...")
    if not GLACIER_OUTLINE.exists():
        print(f"❌ ERROR: Glacier outline not found: {GLACIER_OUTLINE}")
        print("   Check that GLACIER_OUTLINE path is correct")
        return False
    
    try:
        glacier_gdf = gpd.read_file(GLACIER_OUTLINE)
        print(f"✓ Glacier outline loaded ({len(glacier_gdf)} features)")
        print(f"  CRS: {glacier_gdf.crs}")
    except Exception as e:
        print(f"❌ ERROR: Could not load glacier outline: {e}")
        return False
    print()
    
    # Step 3: Extract velocities
    print("[3/4] Extracting velocities from glacier area...")
    print()
    
    results = []
    matched_pairs = set()
    
    for i, img_file in enumerate(velocity_files, 1):
        # Match file to pair
        pair_info = match_file_to_pair(img_file, SAME_TRACK_PAIRS)
        
        if pair_info is None:
            print(f"  [{i}/{len(velocity_files)}] {img_file.name}")
            print(f"     ⚠️  Could not match to same-track pair, skipping")
            continue
        
        pair_key = f"Track{pair_info['track']}_{pair_info['master']}_{pair_info['slave']}"
        if pair_key in matched_pairs:
            print(f"  [{i}/{len(velocity_files)}] {img_file.name}")
            print(f"     ⚠️  Already processed this pair, skipping duplicate")
            continue
        
        matched_pairs.add(pair_key)
        
        print(f"  [{i}/{len(velocity_files)}] Processing: {img_file.name}")
        print(f"     Pair: Track {pair_info['track']}, {pair_info['master']} → {pair_info['slave']}")
        
        # Extract velocities
        stats = extract_glacier_velocity(img_file, GLACIER_OUTLINE)
        
        if stats['status'] == 'OK':
            print(f"     ✓ Extracted: Mean={stats['mean']:.1f}, Max={stats['max']:.1f}, "
                  f"Std={stats['std']:.1f}, N={stats['n_pixels']}")
            
            # Check if values are realistic
            if stats['mean'] < 10:
                print(f"     ⚠️  WARNING: Mean velocity very low ({stats['mean']:.2f} m/day)")
                print(f"        Expected range: 100-500 m/day for surge-type glacier")
        else:
            print(f"     ❌ {stats['status']}")
        
        # Add to results
        midpoint_date = datetime.strptime(pair_info['master'], '%Y-%m-%d') + \
                       pd.Timedelta(days=pair_info['baseline']/2)
        
        results.append({
            'track': pair_info['track'],
            'date_start': pair_info['master'],
            'date_end': pair_info['slave'],
            'date_midpoint': midpoint_date.strftime('%Y-%m-%d'),
            'baseline_days': pair_info['baseline'],
            'file': img_file.name,
            'file_path': str(img_file),
            'mean': stats['mean'],
            'max': stats['max'],
            'min': stats['min'],
            'std': stats['std'],
            'median': stats['median'],
            'n_pixels': stats['n_pixels'],
            'status': stats['status']
        })
        print()
    
    # Step 4: Save results
    print("[4/4] Saving results...")
    
    if len(results) == 0:
        print("❌ ERROR: No velocities extracted")
        return False
    
    df = pd.DataFrame(results)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"✓ Results saved to {OUTPUT_CSV}")
    print()
    
    # Summary statistics
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
        
        # Check for unrealistic values
        if successful['mean'].mean() < 50:
            print("  ⚠️  WARNING: Mean velocities are very low (<50 m/day)")
            print("     Expected range for surge-type glacier: 100-500 m/day")
            print("     This may indicate:")
            print("     - Wrong files (whole-image averages instead of glacier-masked)")
            print("     - Units are wrong (m/year instead of m/day)")
            print("     - Glacier outline doesn't cover the glacier area")
    
    print("=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)
    print()
    print(f"Output file: {OUTPUT_CSV}")
    print()
    print("Next steps:")
    print("  1. Verify velocities are in realistic range (100-500 m/day)")
    print("  2. Check that all 8 pairs were processed (status=OK)")
    print("  3. Proceed to validation analysis (Q2)")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
