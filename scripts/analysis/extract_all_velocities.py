#!/usr/bin/env python3
"""
Extract velocity time series from all SNAP Offset Tracking products.

This script:
1. Finds all *_Stack_vel.dim products
2. Extracts velocity from Velocity_slv1_*.img files in .data folders
3. Samples at glacier location (38.97°N, 70.75°E)
4. Builds CSV time series with dates and velocities
"""

import rasterio
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import re

# Glacier location
GLACIER_LAT = 38.97
GLACIER_LON = 70.75

# Directories
PROCESSED_DIR = Path("satellite_data/sentinel1/processed")
OUTPUT_CSV = PROCESSED_DIR / "velocity_timeseries.csv"

# Window size for averaging (5x5 pixels)
WINDOW_SIZE = 5


def extract_dates_from_filename(filename):
    """Extract date pair from SNAP velocity product filename.
    
    Format: S1A_IW_GRDH_1SDV_20250907T012223_..._Orb_Cal_TC_Stack_vel.dim
    Returns: (date1, date2) as datetime objects
    """
    filename_str = str(filename)
    
    # Find all date patterns (YYYYMMDD)
    dates = re.findall(r'(\d{8})', filename_str)
    
    if len(dates) >= 2:
        try:
            # First date is master, second is slave
            date1 = datetime.strptime(dates[0], '%Y%m%d')
            date2 = datetime.strptime(dates[1], '%Y%m%d')
            return date1, date2
        except ValueError:
            pass
    
    # Alternative: look for T pattern (YYYYMMDDTHHMMSS)
    dates_full = re.findall(r'(\d{8}T\d{6})', filename_str)
    if len(dates_full) >= 2:
        try:
            date1 = datetime.strptime(dates_full[0][:8], '%Y%m%d')
            date2 = datetime.strptime(dates_full[1][:8], '%Y%m%d')
            return date1, date2
        except ValueError:
            pass
    
    return None, None


def find_velocity_image(vel_product_dim):
    """Find the velocity .img file in the .data folder."""
    data_folder = vel_product_dim.with_suffix('.data')
    
    if not data_folder.exists():
        return None
    
    # Look for Velocity_slv1_*.img files
    velocity_files = list(data_folder.glob('Velocity_slv1_*.img'))
    
    if len(velocity_files) == 0:
        # Try alternative patterns
        velocity_files = list(data_folder.glob('*Velocity*.img'))
    
    if len(velocity_files) > 0:
        return velocity_files[0]  # Return first match
    
    return None


def extract_velocity_at_location(velocity_img, date1, date2):
    """Extract velocity at glacier location from velocity image."""
    try:
        with rasterio.open(velocity_img) as src:
            # Get pixel coordinates for glacier location
            row, col = src.index(GLACIER_LON, GLACIER_LAT)
            
            # Check if coordinates are within bounds
            if row < 0 or row >= src.height or col < 0 or col >= src.width:
                print(f"  ⚠️  Glacier location outside image bounds (row={row}, col={col})")
                return None
            
            # Read a window around the glacier location
            half_window = WINDOW_SIZE // 2
            row_start = max(0, row - half_window)
            row_end = min(src.height, row + half_window + 1)
            col_start = max(0, col - half_window)
            col_end = min(src.width, col + half_window + 1)
            
            # Read the data for the window
            window = rasterio.windows.Window(
                col_start, row_start,
                col_end - col_start, row_end - row_start
            )
            velocity_data = src.read(1, window=window).astype(float)
            
            # Calculate statistics
            # Note: SNAP Offset Tracking outputs velocity in m/day
            v_mean = float(np.nanmean(velocity_data))
            v_std = float(np.nanstd(velocity_data))
            v_median = float(np.median(velocity_data[~np.isnan(velocity_data)]))
            
            # Time delta in days
            time_delta = (date2 - date1).total_seconds() / 86400.0
            
            return {
                'date1': date1.strftime('%Y-%m-%d'),
                'date2': date2.strftime('%Y-%m-%d'),
                'date': date2.strftime('%Y-%m-%d'),  # Use end date for time series
                'velocity_m_per_day': v_mean,
                'velocity_median': v_median,
                'velocity_std': v_std,
                'time_delta_days': time_delta,
                'pixel_row': int(row),
                'pixel_col': int(col),
                'window_size': WINDOW_SIZE
            }
            
    except Exception as e:
        print(f"  ❌ Error reading velocity image: {e}")
        return None


def main():
    """Main extraction function."""
    print("=" * 70)
    print("Extracting Velocity Time Series from SNAP Products")
    print("=" * 70)
    print()
    
    # Find all velocity products
    vel_products = sorted(PROCESSED_DIR.glob("*_Stack_vel.dim"))
    
    if len(vel_products) == 0:
        print("❌ No velocity products found!")
        print(f"   Expected files in: {PROCESSED_DIR}")
        print("   Pattern: *_Stack_vel.dim")
        return False
    
    print(f"Found {len(vel_products)} velocity products")
    print()
    
    results = []
    
    for vel_product in vel_products:
        print(f"Processing: {vel_product.name}")
        
        # Extract dates
        date1, date2 = extract_dates_from_filename(vel_product)
        if date1 is None or date2 is None:
            print(f"  ⚠️  Could not extract dates from filename")
            continue
        
        print(f"  Dates: {date1.strftime('%Y-%m-%d')} → {date2.strftime('%Y-%m-%d')}")
        
        # Find velocity image
        velocity_img = find_velocity_image(vel_product)
        if velocity_img is None:
            print(f"  ⚠️  Could not find velocity image in .data folder")
            continue
        
        print(f"  Velocity image: {velocity_img.name}")
        
        # Extract velocity
        result = extract_velocity_at_location(velocity_img, date1, date2)
        if result:
            results.append(result)
            print(f"  ✅ Velocity: {result['velocity_m_per_day']:.3f} ± {result['velocity_std']:.3f} m/day")
        else:
            print(f"  ⚠️  Could not extract velocity")
        print()
    
    if len(results) == 0:
        print("❌ No velocity data extracted")
        return False
    
    # Create DataFrame
    df = pd.DataFrame(results)
    df = df.sort_values('date')
    
    # Save to CSV
    df.to_csv(OUTPUT_CSV, index=False)
    
    print("=" * 70)
    print("✅ Velocity Time Series Extracted!")
    print("=" * 70)
    print()
    print(f"Saved: {OUTPUT_CSV}")
    print(f"Records: {len(df)}")
    print()
    print("Summary Statistics:")
    print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"  Mean velocity: {df['velocity_m_per_day'].mean():.3f} m/day")
    print(f"  Median velocity: {df['velocity_m_per_day'].median():.3f} m/day")
    print(f"  Max velocity: {df['velocity_m_per_day'].max():.3f} m/day")
    print(f"  Min velocity: {df['velocity_m_per_day'].min():.3f} m/day")
    print(f"  Std velocity: {df['velocity_m_per_day'].std():.3f} m/day")
    print()
    print("Time Series Preview:")
    print(df[['date', 'velocity_m_per_day', 'velocity_std', 'time_delta_days']].to_string(index=False))
    print()
    print("=" * 70)
    print("Next Steps:")
    print("=" * 70)
    print("1. Run change-point detection:")
    print("   python3 apply_changepoint_detection.py")
    print()
    print("2. Test mechanisms:")
    print("   python3 test_mechanism_integration.py")
    print()
    print("3. Align change-points with climate:")
    print("   python3 align_changepoints_climate.py")
    print()
    print("4. Run complete analysis:")
    print("   python3 run_complete_analysis.py")
    print()
    
    return True


if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)

