#!/usr/bin/env python3
"""
Python-based offset tracking for Sentinel-1 velocity calculation.

This script performs offset tracking directly from terrain-corrected Sentinel-1 products
using normalized cross-correlation (NCC) template matching.

Alternative to SNAP Offset Tracking.
"""

import rasterio
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from scipy import ndimage
from scipy.ndimage import uniform_filter
import warnings
warnings.filterwarnings('ignore')

# Glacier location
GLACIER_LAT = 38.97
GLACIER_LON = 70.75

# Directories
PROCESSED_DIR = Path("satellite_data/sentinel1/processed")
OUTPUT_CSV = PROCESSED_DIR / "velocity_timeseries_python.csv"

# Offset tracking parameters
WINDOW_SIZE = 128  # Template window size (pixels)
SEARCH_RANGE = 200  # Maximum search range (pixels)
STEP_SIZE = 40  # Grid spacing (pixels)


def load_terrain_corrected_product(product_path):
    """Load terrain-corrected Sentinel-1 product."""
    # Try to find the actual image file in .data folder
    data_folder = product_path.with_suffix('.data')
    
    if not data_folder.exists():
        return None, None
    
    # Look for sigma0 bands (terrain-corrected backscatter)
    # SNAP creates: Sigma0_VH.img, Sigma0_VV.img
    vv_file = list(data_folder.glob('Sigma0_VV.img'))
    vh_file = list(data_folder.glob('Sigma0_VH.img'))
    
    # Prefer VV polarization (better for glacier tracking)
    if vv_file:
        image_file = vv_file[0]
    elif vh_file:
        image_file = vh_file[0]
    else:
        # Try other patterns as fallback
        image_files = list(data_folder.glob('*Sigma0*.img'))
        if len(image_files) == 0:
            image_files = list(data_folder.glob('*Gamma0*.img'))
        if len(image_files) == 0:
            image_files = list(data_folder.glob('Intensity*.img'))
        if len(image_files) == 0:
            print(f"    No image files found in {data_folder}")
            return None, None
        image_file = image_files[0]
    
    try:
        with rasterio.open(image_file) as src:
            data = src.read(1).astype(np.float32)
            transform = src.transform
            crs = src.crs
            return data, (transform, crs)
    except Exception as e:
        print(f"  Error loading {image_file.name}: {e}")
        return None, None


def extract_date_from_filename(filename):
    """Extract date from Sentinel-1 filename."""
    import re
    dates = re.findall(r'(\d{8})', str(filename))
    if dates:
        try:
            return datetime.strptime(dates[0], '%Y%m%d')
        except:
            pass
    return None


def normalized_cross_correlation(template, image):
    """
    Compute normalized cross-correlation between template and image.
    
    Returns correlation map with values in range [-1, 1]
    """
    # Normalize template
    template_mean = np.mean(template)
    template_std = np.std(template)
    if template_std == 0:
        return np.zeros_like(image)
    template_norm = (template - template_mean) / template_std
    
    # Compute correlation using convolution
    # This is an approximation - for exact NCC, use scipy.ndimage.correlate
    image_mean = uniform_filter(image.astype(float), size=template.shape)
    image_std = np.sqrt(uniform_filter((image.astype(float) - image_mean)**2, size=template.shape))
    
    # Avoid division by zero
    image_std[image_std == 0] = 1
    
    # Normalized correlation
    correlation = uniform_filter(
        (image.astype(float) - image_mean) * template_norm,
        size=template.shape
    ) / image_std
    
    return correlation


def find_offset_ncc(master, slave, center_row, center_col, search_range=200):
    """
    Find offset between master and slave images using NCC.
    
    Returns: (row_offset, col_offset, correlation)
    """
    half_window = WINDOW_SIZE // 2
    
    # Extract template from master
    row_start = max(0, center_row - half_window)
    row_end = min(master.shape[0], center_row + half_window)
    col_start = max(0, center_col - half_window)
    col_end = min(master.shape[1], center_col + half_window)
    
    template = master[row_start:row_end, col_start:col_end]
    
    if template.size == 0 or template.shape[0] < WINDOW_SIZE // 2 or template.shape[1] < WINDOW_SIZE // 2:
        return 0, 0, 0.0
    
    # Define search area in slave
    search_row_start = max(0, center_row - search_range)
    search_row_end = min(slave.shape[0], center_row + search_range)
    search_col_start = max(0, center_col - search_range)
    search_col_end = min(slave.shape[1], center_col + search_range)
    
    search_area = slave[search_row_start:search_row_end, search_col_start:search_col_end]
    
    if search_area.size == 0:
        return 0, 0, 0.0
    
    # Compute NCC
    # For efficiency, we'll use a simpler approach: extract patches and compute correlation
    best_corr = -1.0
    best_row_offset = 0
    best_col_offset = 0
    
    # Sample search positions
    step = max(1, search_range // 20)  # Sample every N pixels
    
    for dr in range(-search_range, search_range + 1, step):
        for dc in range(-search_range, search_range + 1, step):
            slave_row = center_row + dr
            slave_col = center_col + dc
            
            if (slave_row - half_window < 0 or slave_row + half_window >= slave.shape[0] or
                slave_col - half_window < 0 or slave_col + half_window >= slave.shape[1]):
                continue
            
            slave_patch = slave[
                slave_row - half_window:slave_row + half_window,
                slave_col - half_window:slave_col + half_window
            ]
            
            if slave_patch.shape != template.shape:
                continue
            
            # Compute correlation
            corr = np.corrcoef(template.flatten(), slave_patch.flatten())[0, 1]
            
            if np.isnan(corr):
                corr = 0.0
            
            if corr > best_corr:
                best_corr = corr
                best_row_offset = dr
                best_col_offset = dc
    
    return best_row_offset, best_col_offset, best_corr


def calculate_velocity_from_pair(master_path, slave_path):
    """Calculate velocity from a pair of terrain-corrected products."""
    print(f"\nProcessing pair:")
    print(f"  Master: {master_path.name}")
    print(f"  Slave: {slave_path.name}")
    
    # Extract dates
    date1 = extract_date_from_filename(master_path)
    date2 = extract_date_from_filename(slave_path)
    
    if not date1 or not date2:
        print("  ⚠️  Could not extract dates")
        return None
    
    print(f"  Dates: {date1.strftime('%Y-%m-%d')} → {date2.strftime('%Y-%m-%d')}")
    
    # Load images
    print("  Loading master image...")
    master_data, master_geo = load_terrain_corrected_product(master_path)
    if master_data is None:
        print("  ❌ Could not load master image")
        return None
    
    print("  Loading slave image...")
    slave_data, slave_geo = load_terrain_corrected_product(slave_path)
    if slave_data is None:
        print("  ❌ Could not load slave image")
        return None
    
    # Check if images have same size (if not, need to resample)
    if master_data.shape != slave_data.shape:
        print(f"  ⚠️  Image sizes differ: {master_data.shape} vs {slave_data.shape}")
        print("  Attempting to resample...")
        # Simple resampling - crop to smaller size
        min_rows = min(master_data.shape[0], slave_data.shape[0])
        min_cols = min(master_data.shape[1], slave_data.shape[1])
        master_data = master_data[:min_rows, :min_cols]
        slave_data = slave_data[:min_rows, :min_cols]
    
    # Get glacier pixel coordinates
    if master_geo:
        transform, crs = master_geo
        row, col = rasterio.transform.rowcol(transform, GLACIER_LON, GLACIER_LAT)
    else:
        # Approximate if no transform available
        print("  ⚠️  No geotransform, using approximate coordinates")
        row = master_data.shape[0] // 2
        col = master_data.shape[1] // 2
    
    print(f"  Glacier pixel: ({row}, {col})")
    
    # Find offset at glacier location
    print("  Computing offset using NCC...")
    row_offset, col_offset, correlation = find_offset_ncc(
        master_data, slave_data, row, col, search_range=SEARCH_RANGE
    )
    
    print(f"  Offset: ({row_offset}, {col_offset}) pixels, correlation: {correlation:.3f}")
    
    # Convert pixel offset to meters
    if master_geo:
        transform, crs = master_geo
        # Check if CRS is geographic (degrees) or projected (meters)
        if crs and crs.is_geographic:
            # Convert degrees to meters
            # At latitude 38.97°N:
            lat_rad = np.radians(GLACIER_LAT)
            meters_per_degree_lat = 111320.0  # constant
            meters_per_degree_lon = 111320.0 * np.cos(lat_rad)
            
            pixel_size_x = abs(transform[0]) * meters_per_degree_lon
            pixel_size_y = abs(transform[4]) * meters_per_degree_lat
        else:
            # Already in meters
            pixel_size_x = abs(transform[0])
            pixel_size_y = abs(transform[4])
    else:
        # Default: assume 10m pixel spacing (from terrain correction)
        pixel_size_x = 10.0
        pixel_size_y = 10.0
    
    # Displacement in meters
    dx_m = col_offset * pixel_size_x
    dy_m = row_offset * pixel_size_y
    displacement_m = np.sqrt(dx_m**2 + dy_m**2)
    
    # Time delta in days
    time_delta_days = (date2 - date1).total_seconds() / 86400.0
    
    # Velocity in m/day
    if time_delta_days > 0:
        velocity_m_per_day = displacement_m / time_delta_days
    else:
        velocity_m_per_day = 0.0
    
    print(f"  Displacement: {displacement_m:.2f} m ({dx_m:.2f} E, {dy_m:.2f} N)")
    print(f"  Time delta: {time_delta_days:.2f} days")
    print(f"  Velocity: {velocity_m_per_day:.3f} m/day")
    
    return {
        'date1': date1.strftime('%Y-%m-%d'),
        'date2': date2.strftime('%Y-%m-%d'),
        'date': date2.strftime('%Y-%m-%d'),
        'velocity_m_per_day': velocity_m_per_day,
        'displacement_m': displacement_m,
        'dx_m': dx_m,
        'dy_m': dy_m,
        'row_offset_px': row_offset,
        'col_offset_px': col_offset,
        'correlation': correlation,
        'time_delta_days': time_delta_days
    }


def main():
    """Main function to calculate velocities for all pairs."""
    print("=" * 70)
    print("Python-Based Offset Tracking for Sentinel-1 Velocity")
    print("=" * 70)
    print()
    print("This script performs offset tracking directly from terrain-corrected")
    print("Sentinel-1 products using normalized cross-correlation.")
    print()
    
    # Find all terrain-corrected products
    tc_products = sorted(PROCESSED_DIR.glob("*_Orb_Cal_TC.dim"))
    
    if len(tc_products) < 2:
        print("❌ Need at least 2 terrain-corrected products")
        return
    
    print(f"Found {len(tc_products)} terrain-corrected products")
    print()
    
    # Process consecutive pairs
    results = []
    
    for i in range(len(tc_products) - 1):
        master = tc_products[i]
        slave = tc_products[i + 1]
        
        result = calculate_velocity_from_pair(master, slave)
        if result:
            results.append(result)
    
    if len(results) == 0:
        print("\n❌ No velocity data calculated")
        return
    
    # Create DataFrame and save
    df = pd.DataFrame(results)
    df = df.sort_values('date')
    df.to_csv(OUTPUT_CSV, index=False)
    
    print("\n" + "=" * 70)
    print("✅ Velocity Time Series Calculated!")
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
    print()
    print("Time Series:")
    print(df[['date', 'velocity_m_per_day', 'displacement_m', 'correlation']].to_string(index=False))
    print()


if __name__ == '__main__':
    main()

