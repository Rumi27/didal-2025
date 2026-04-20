#!/usr/bin/env python3
"""
Extract stable ground statistics for empirical uncertainty quantification.

This script extracts velocity values from stable bedrock/ridge areas for each
image pair and calculates:
- Mean offset (μ_stable): Systematic bias
- Standard deviation (σ_stable): Random uncertainty
- Level of Detection (LOD): μ_stable + 2×σ_stable

Requirements:
- Stable ground mask shapefile (stable_ground_mask.shp)
- Velocity maps for each pair (GeoTIFF files)
- Rasterio, geopandas, numpy, pandas

Usage:
    python extract_stable_ground_statistics.py
"""

import os
import glob
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask
import geopandas as gpd
from pathlib import Path

# Configuration
STABLE_MASK_PATH = "stable_ground_mask.shp"  # To be created in QGIS
VELOCITY_MAPS_DIR = "satellite_data/sentinel1/processed/velocity_maps/"
OUTPUT_CSV = "processed_data/stable_ground_statistics.csv"

def load_stable_mask(mask_path):
    """Load stable ground mask polygon."""
    if not os.path.exists(mask_path):
        raise FileNotFoundError(
            f"Stable ground mask not found: {mask_path}\n"
            "Please create stable_ground_mask.shp in QGIS first."
        )
    return gpd.read_file(mask_path)

def extract_stable_values(velocity_map_path, stable_mask):
    """Extract velocity values within stable ground polygons."""
    with rasterio.open(velocity_map_path) as src:
        # Ensure CRS match
        if stable_mask.crs != src.crs:
            print(f"Warning: CRS mismatch. Reprojecting stable mask...")
            stable_mask = stable_mask.to_crs(src.crs)
        
        # Extract values within polygons
        all_values = []
        for idx, geom in stable_mask.iterrows():
            try:
                masked_data, _ = mask(src, [geom.geometry], crop=True)
                values = masked_data[0]  # First band
                values = values[~np.isnan(values)]  # Remove NaN
                values = values[values != src.nodata]  # Remove nodata
                all_values.extend(values.flatten())
            except Exception as e:
                print(f"Warning: Could not extract values for polygon {idx}: {e}")
                continue
        
        return np.array(all_values)

def calculate_statistics(values):
    """Calculate mean, std dev, and LOD from stable ground values."""
    if len(values) == 0:
        return None, None, None, 0
    
    mu_stable = np.mean(values)
    sigma_stable = np.std(values, ddof=1)  # Sample std dev
    n_pixels = len(values)
    lod = mu_stable + 2 * sigma_stable
    
    return mu_stable, sigma_stable, lod, n_pixels

def process_all_pairs(velocity_maps_dir, stable_mask, output_csv):
    """Process all velocity maps and extract stable ground statistics."""
    
    # Find all velocity maps
    velocity_files = sorted(glob.glob(os.path.join(velocity_maps_dir, "*.tif")))
    
    if not velocity_files:
        raise FileNotFoundError(f"No velocity maps found in {velocity_maps_dir}")
    
    print(f"Found {len(velocity_files)} velocity maps")
    print("=" * 80)
    
    results = []
    
    for vel_file in velocity_files:
        # Extract date range from filename
        # Expected format: velocity_YYYYMMDD_YYYYMMDD.tif
        basename = os.path.basename(vel_file)
        parts = basename.replace("velocity_", "").replace(".tif", "").split("_")
        
        if len(parts) >= 2:
            date1 = parts[0]
            date2 = parts[1]
        else:
            date1 = "unknown"
            date2 = "unknown"
        
        print(f"\nProcessing: {basename}")
        print(f"  Date range: {date1} → {date2}")
        
        # Extract stable ground values
        try:
            stable_values = extract_stable_values(vel_file, stable_mask)
            
            if len(stable_values) == 0:
                print(f"  Warning: No valid values extracted")
                continue
            
            # Calculate statistics
            mu, sigma, lod, n = calculate_statistics(stable_values)
            
            print(f"  Mean (bias): {mu:.3f} m/day")
            print(f"  Std Dev (uncertainty): {sigma:.3f} m/day")
            print(f"  LOD: {lod:.3f} m/day")
            print(f"  Sample size: {n} pixels")
            
            results.append({
                'pair_id': len(results) + 1,
                'date1': date1,
                'date2': date2,
                'velocity_file': basename,
                'mu_stable': mu,
                'sigma_stable': sigma,
                'lod': lod,
                'n_pixels': n
            })
            
        except Exception as e:
            print(f"  Error processing {basename}: {e}")
            continue
    
    # Save results
    if results:
        df = pd.DataFrame(results)
        
        # Create output directory if needed
        os.makedirs(os.path.dirname(output_csv), exist_ok=True)
        
        df.to_csv(output_csv, index=False)
        print(f"\n{'='*80}")
        print(f"Results saved to: {output_csv}")
        print(f"Total pairs processed: {len(results)}")
        
        # Print summary
        print(f"\nSummary Statistics:")
        print(f"  Mean bias range: {df['mu_stable'].min():.3f} to {df['mu_stable'].max():.3f} m/day")
        print(f"  Mean uncertainty: {df['sigma_stable'].mean():.3f} m/day")
        print(f"  Uncertainty range: {df['sigma_stable'].min():.3f} to {df['sigma_stable'].max():.3f} m/day")
        print(f"  Mean LOD: {df['lod'].mean():.3f} m/day")
    else:
        print("\nNo results to save. Check stable ground mask and velocity maps.")

def main():
    """Main execution."""
    print("=" * 80)
    print("STABLE GROUND STATISTICS EXTRACTION")
    print("=" * 80)
    
    # Check if stable mask exists
    if not os.path.exists(STABLE_MASK_PATH):
        print(f"\nERROR: Stable ground mask not found: {STABLE_MASK_PATH}")
        print("\nPlease create stable_ground_mask.shp first:")
        print("1. Open QGIS")
        print("2. Load satellite imagery and glacier outline")
        print("3. Digitize polygons around stable bedrock/ridge areas")
        print("4. Save as: stable_ground_mask.shp")
        return
    
    # Load stable mask
    print(f"\nLoading stable ground mask: {STABLE_MASK_PATH}")
    stable_mask = load_stable_mask(STABLE_MASK_PATH)
    print(f"  Found {len(stable_mask)} polygon(s)")
    print(f"  CRS: {stable_mask.crs}")
    
    # Process all pairs
    process_all_pairs(VELOCITY_MAPS_DIR, stable_mask, OUTPUT_CSV)

if __name__ == "__main__":
    main()
