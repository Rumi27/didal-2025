#!/usr/bin/env python3
"""
Extract velocity time series from Sentinel-1 processing results.

This script can work with:
1. SNAP offset tracking results (displacement maps)
2. Pre-processed velocity/displacement data
3. Manual velocity measurements

Usage:
    python3 extract_velocity_from_snap.py
"""

import rasterio
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import json
import re

# Glacier location
GLACIER_LAT = 38.97
GLACIER_LON = 70.75

# Directories
SENTINEL1_DIR = Path("satellite_data/sentinel1")
PROCESSED_DIR = Path("satellite_data/sentinel1/processed")
OUTPUT_CSV = PROCESSED_DIR / "velocity_timeseries.csv"

# Create processed directory
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def extract_date_from_filename(filename):
    """Extract date from Sentinel-1 filename."""
    # Format: S1A_IW_GRDH_1SDV_20250907T012223_...
    parts = str(filename).split('_')
    for part in parts:
        if 'T' in part and len(part) == 15:
            try:
                date = datetime.strptime(part, '%Y%m%dT%H%M%S')
                return date
            except:
                pass
    return None


def extract_velocity_from_displacement_map(displacement_file, date1, date2):
    """Extract velocity from displacement map (dx, dy bands)."""
    try:
        with rasterio.open(displacement_file) as src:
            # Get pixel coordinates for glacier location
            row, col = src.index(GLACIER_LON, GLACIER_LAT)
            
            # Check if coordinates are within bounds
            if row < 0 or row >= src.height or col < 0 or col >= src.width:
                print(f"  ⚠️  Glacier location outside image bounds")
                return None
            
            # Read displacement bands
            # Band 1: dx (East-West), Band 2: dy (North-South)
            if src.count >= 2:
                dx = src.read(1)
                dy = src.read(2)
            else:
                # Single band - assume it's magnitude
                dx = src.read(1)
                dy = np.zeros_like(dx)
            
            # Get pixel size (meters)
            pixel_size = abs(src.transform[0])
            
            # Extract at glacier location
            dx_m = float(dx[row, col]) * pixel_size
            dy_m = float(dy[row, col]) * pixel_size
            
            # Calculate velocity
            time_delta = (date2 - date1).total_seconds() / 86400.0  # days
            if time_delta <= 0:
                return None
            
            velocity = np.sqrt(dx_m**2 + dy_m**2) / time_delta
            
            # Estimate uncertainty (10% of velocity, or use correlation if available)
            velocity_std = velocity * 0.1
            
            return {
                'date': date2.strftime('%Y-%m-%d'),
                'velocity_m_per_day': float(velocity),
                'velocity_std': float(velocity_std),
                'dx_m': float(dx_m),
                'dy_m': float(dy_m),
                'time_delta_days': float(time_delta)
            }
    except Exception as e:
        print(f"  ❌ Error reading {displacement_file.name}: {e}")
        return None


def find_displacement_maps():
    """Find displacement maps in processed directory."""
    # Look for common patterns
    patterns = [
        "offset_*.tif",
        "displacement_*.tif",
        "*_offset.tif",
        "*_displacement.tif",
        "*_dx_dy.tif"
    ]
    
    files = []
    for pattern in patterns:
        files.extend(PROCESSED_DIR.glob(pattern))
    
    return sorted(set(files))


def process_displacement_maps():
    """Process all displacement maps and extract velocity."""
    print("=" * 70)
    print("Extracting Velocity from Displacement Maps")
    print("=" * 70)
    print()
    
    displacement_files = find_displacement_maps()
    
    if not displacement_files:
        print("❌ No displacement maps found")
        print()
        print("Expected files in: satellite_data/sentinel1/processed/")
        print("  - offset_*.tif")
        print("  - displacement_*.tif")
        print("  - *_dx_dy.tif")
        print()
        return None
    
    print(f"Found {len(displacement_files)} displacement maps")
    print()
    
    results = []
    
    for disp_file in displacement_files:
        print(f"Processing: {disp_file.name}")
        
        # Try to extract dates from filename
        # Format: offset_20250907_20250913.tif or similar
        date_match = re.findall(r'(\d{8})', disp_file.stem)
        
        if len(date_match) >= 2:
            try:
                date1 = datetime.strptime(date_match[0], '%Y%m%d')
                date2 = datetime.strptime(date_match[1], '%Y%m%d')
            except:
                print(f"  ⚠️  Could not parse dates from filename")
                continue
        else:
            # Try to match with Sentinel-1 products
            products = sorted(SENTINEL1_DIR.glob("*.SAFE.zip"))
            if len(products) >= 2:
                # Use product dates (simplified - assumes sequential)
                idx = displacement_files.index(disp_file)
                if idx < len(products) - 1:
                    date1 = extract_date_from_filename(products[idx])
                    date2 = extract_date_from_filename(products[idx + 1])
                else:
                    print(f"  ⚠️  Could not determine dates")
                    continue
            else:
                print(f"  ⚠️  Could not determine dates")
                continue
        
        result = extract_velocity_from_displacement_map(disp_file, date1, date2)
        if result:
            results.append(result)
            print(f"  ✅ Velocity: {result['velocity_m_per_day']:.3f} m/day")
        else:
            print(f"  ⚠️  Could not extract velocity")
        print()
    
    if results:
        df = pd.DataFrame(results)
        df = df.sort_values('date')
        return df
    else:
        return None


def create_from_template():
    """Create velocity CSV from template using product dates."""
    print("=" * 70)
    print("Creating Velocity Template from Product Dates")
    print("=" * 70)
    print()
    
    products = sorted(SENTINEL1_DIR.glob("*.SAFE.zip"))
    
    if len(products) < 2:
        print("❌ Need at least 2 products for velocity calculation")
        return None
    
    print(f"Found {len(products)} products")
    print()
    
    # Extract dates
    dates = []
    for product in products:
        date = extract_date_from_filename(product)
        if date:
            dates.append((date, product))
        else:
            print(f"⚠️  Could not extract date from: {product.name}")
    
    if len(dates) < 2:
        print("❌ Could not extract enough dates")
        return None
    
    dates.sort(key=lambda x: x[0])
    
    # Create velocity entries
    results = []
    for i in range(len(dates) - 1):
        date1, prod1 = dates[i]
        date2, prod2 = dates[i + 1]
        
        time_delta = (date2 - date1).total_seconds() / 86400.0
        
        results.append({
            'date': date2.strftime('%Y-%m-%d'),
            'velocity_m_per_day': 0.0,  # To be filled manually or from processing
            'velocity_std': 0.0,
            'dx_m': 0.0,
            'dy_m': 0.0,
            'time_delta_days': time_delta,
            'product1': prod1.name,
            'product2': prod2.name
        })
    
    df = pd.DataFrame(results)
    
    print("Created template with product pairs:")
    print()
    for _, row in df.iterrows():
        print(f"  {row['date']}: {row['product1']} → {row['product2']}")
        print(f"    Time delta: {row['time_delta_days']:.1f} days")
    print()
    
    return df


def main():
    """Main extraction function."""
    print("=" * 70)
    print("Sentinel-1 Velocity Extraction")
    print("=" * 70)
    print()
    
    # Try to extract from displacement maps
    df = process_displacement_maps()
    
    if df is None or len(df) == 0:
        print("=" * 70)
        print("No displacement maps found - creating template")
        print("=" * 70)
        print()
        
        df = create_from_template()
        
        if df is not None:
            template_file = PROCESSED_DIR / "velocity_timeseries_template.csv"
            df.to_csv(template_file, index=False)
            print(f"✅ Template saved: {template_file}")
            print()
            print("Next steps:")
            print("  1. Process Sentinel-1 with SNAP/ISCE")
            print("  2. Extract displacement maps")
            print("  3. Re-run this script to extract velocity")
            print()
            print("OR manually fill in velocity values in the template")
            print()
            return False
    
    # Save results
    if df is not None and len(df) > 0:
        df.to_csv(OUTPUT_CSV, index=False)
        print("=" * 70)
        print("✅ Velocity Time Series Extracted!")
        print("=" * 70)
        print()
        print(f"Saved: {OUTPUT_CSV}")
        print(f"Records: {len(df)}")
        print()
        print("Summary:")
        print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"  Mean velocity: {df['velocity_m_per_day'].mean():.3f} m/day")
        print(f"  Max velocity: {df['velocity_m_per_day'].max():.3f} m/day")
        print()
        print("Ready for analysis!")
        print("  python3 run_complete_analysis.py")
        print()
        return True
    else:
        print("❌ No velocity data extracted")
        return False


if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
