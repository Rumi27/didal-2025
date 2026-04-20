#!/usr/bin/env python3
"""
Phase 2: Extract Velocity Maps from SNAP .dim Products

This script:
1. Finds all *_Stack_vel.dim products
2. Extracts velocity bands from .data folders
3. Converts to GeoTIFF format
4. Creates a velocity map stack for spatial analysis

Run: python3 extract_velocity_maps.py
"""

import os
import glob
from pathlib import Path
import rasterio
from rasterio.transform import from_bounds
import numpy as np
from datetime import datetime
import re
import json

# Directories
PROCESSED_DIR = Path("satellite_data/sentinel1/processed")
OUTPUT_DIR = Path("satellite_data/sentinel1/processed/velocity_maps")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Glacier location for verification
GLACIER_LAT = 38.97
GLACIER_LON = 70.75

def find_velocity_products():
    """Find all velocity product .dim files."""
    print("=" * 70)
    print("FINDING VELOCITY PRODUCTS")
    print("=" * 70)
    
    pattern = str(PROCESSED_DIR / "*_Stack_vel.dim")
    products = sorted(glob.glob(pattern))
    
    print(f"\nFound {len(products)} velocity products:")
    for p in products:
        print(f"  - {os.path.basename(p)}")
    
    return products

def extract_dates_from_filename(filename):
    """Extract date pair from filename."""
    filename_str = str(filename)
    
    # Find all date patterns (YYYYMMDD)
    dates = re.findall(r'(\d{8})', filename_str)
    
    if len(dates) >= 2:
        try:
            date1 = datetime.strptime(dates[0], '%Y%m%d')
            date2 = datetime.strptime(dates[1], '%Y%m%d')
            return date1, date2
        except ValueError:
            pass
    
    return None, None

def find_velocity_image_in_data_folder(dim_file):
    """Find velocity .img file in the .data folder."""
    data_folder = dim_file.replace('.dim', '.data')
    
    if not os.path.exists(data_folder):
        return None
    
    # Look for velocity image files
    # SNAP typically names them: Velocity_slv1_*.img or similar
    velocity_patterns = [
        os.path.join(data_folder, 'Velocity_slv1_*.img'),
        os.path.join(data_folder, '*Velocity*.img'),
        os.path.join(data_folder, 'velocity*.img'),
    ]
    
    for pattern in velocity_patterns:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]  # Return first match
    
    # Alternative: look for any .img file (might be velocity)
    all_img = glob.glob(os.path.join(data_folder, '*.img'))
    if all_img:
        # Prefer files with 'velocity' or 'vel' in name
        for img in all_img:
            if 'velocity' in img.lower() or 'vel' in img.lower():
                return img
        # Otherwise return first .img file
        return all_img[0]
    
    return None

def extract_velocity_to_geotiff(velocity_img, output_geotiff, date1, date2):
    """Extract velocity image and convert to GeoTIFF."""
    try:
        # Try to open with rasterio
        # SNAP .img files might need special handling
        with rasterio.open(velocity_img) as src:
            # Read velocity data
            velocity_data = src.read(1)  # Read first band
            
            # Get georeferencing
            transform = src.transform
            crs = src.crs
            
            # Get metadata
            width = src.width
            height = src.height
            bounds = src.bounds
            
            print(f"    Image size: {width} x {height} pixels")
            print(f"    CRS: {crs}")
            print(f"    Bounds: {bounds}")
            
            # Check for valid velocity values
            valid_mask = ~np.isnan(velocity_data) & (velocity_data != 0)
            if valid_mask.any():
                valid_values = velocity_data[valid_mask]
                print(f"    Valid pixels: {valid_mask.sum()} / {velocity_data.size}")
                print(f"    Velocity range: {valid_values.min():.2f} to {valid_values.max():.2f} m/d")
            else:
                print(f"    ⚠️  Warning: No valid velocity values found")
            
            # Write to GeoTIFF
            with rasterio.open(
                output_geotiff,
                'w',
                driver='GTiff',
                height=height,
                width=width,
                count=1,
                dtype=velocity_data.dtype,
                crs=crs,
                transform=transform,
                compress='lzw',
                nodata=-9999
            ) as dst:
                dst.write(velocity_data, 1)
                
                # Add metadata
                dst.update_tags(
                    date1=date1.strftime('%Y-%m-%d'),
                    date2=date2.strftime('%Y-%m-%d'),
                    source_file=os.path.basename(velocity_img),
                    glacier_location=f"{GLACIER_LAT}°N, {GLACIER_LON}°E"
                )
            
            print(f"    ✅ Saved: {os.path.basename(output_geotiff)}")
            return True
            
    except Exception as e:
        print(f"    ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_velocity_map_stack(geotiff_files):
    """Create a summary of velocity maps for easy access."""
    print("\n" + "=" * 70)
    print("CREATING VELOCITY MAP STACK SUMMARY")
    print("=" * 70)
    
    stack_info = []
    
    for geotiff in sorted(geotiff_files):
        try:
            with rasterio.open(geotiff) as src:
                # Read metadata
                tags = src.tags()
                date1 = tags.get('date1', 'Unknown')
                date2 = tags.get('date2', 'Unknown')
                
                # Get statistics
                data = src.read(1)
                valid_data = data[~np.isnan(data) & (data != -9999) & (data != 0)]
                
                if len(valid_data) > 0:
                    stats = {
                        'file': os.path.basename(geotiff),
                        'date1': date1,
                        'date2': date2,
                        'mean_velocity': float(np.mean(valid_data)),
                        'max_velocity': float(np.max(valid_data)),
                        'min_velocity': float(np.min(valid_data)),
                        'std_velocity': float(np.std(valid_data)),
                        'valid_pixels': int(len(valid_data)),
                        'crs': str(src.crs),
                        'bounds': {
                            'left': float(src.bounds.left),
                            'bottom': float(src.bounds.bottom),
                            'right': float(src.bounds.right),
                            'top': float(src.bounds.top)
                        }
                    }
                    stack_info.append(stats)
        except Exception as e:
            print(f"  ⚠️  Error reading {geotiff}: {e}")
    
    # Save stack info
    stack_info_file = OUTPUT_DIR / "velocity_map_stack_info.json"
    with open(stack_info_file, 'w') as f:
        json.dump(stack_info, f, indent=2)
    
    print(f"\n✅ Stack info saved: {stack_info_file}")
    print(f"   Total maps: {len(stack_info)}")
    
    return stack_info

def main():
    """Main function."""
    print("=" * 70)
    print("PHASE 2: EXTRACT VELOCITY MAPS FROM SNAP PRODUCTS")
    print("=" * 70)
    print()
    
    # Find velocity products
    products = find_velocity_products()
    
    if not products:
        print("❌ No velocity products found!")
        return
    
    print(f"\nProcessing {len(products)} products...")
    print()
    
    extracted_geotiffs = []
    
    for i, dim_file in enumerate(products, 1):
        print(f"[{i}/{len(products)}] Processing: {os.path.basename(dim_file)}")
        
        # Extract dates
        date1, date2 = extract_dates_from_filename(dim_file)
        if date1 and date2:
            print(f"    Dates: {date1.strftime('%Y-%m-%d')} to {date2.strftime('%Y-%m-%d')}")
        else:
            print(f"    ⚠️  Could not extract dates from filename")
            continue
        
        # Find velocity image
        velocity_img = find_velocity_image_in_data_folder(dim_file)
        if not velocity_img:
            print(f"    ❌ No velocity image found in .data folder")
            continue
        
        print(f"    Found velocity image: {os.path.basename(velocity_img)}")
        
        # Create output filename
        output_name = f"velocity_{date1.strftime('%Y%m%d')}_{date2.strftime('%Y%m%d')}.tif"
        output_geotiff = OUTPUT_DIR / output_name
        
        # Extract to GeoTIFF
        if extract_velocity_to_geotiff(velocity_img, output_geotiff, date1, date2):
            extracted_geotiffs.append(output_geotiff)
        
        print()
    
    # Create stack summary
    if extracted_geotiffs:
        stack_info = create_velocity_map_stack(extracted_geotiffs)
        
        print("\n" + "=" * 70)
        print("✅ VELOCITY MAP EXTRACTION COMPLETE!")
        print("=" * 70)
        print(f"\nExtracted {len(extracted_geotiffs)} velocity maps:")
        for geotiff in extracted_geotiffs:
            print(f"  - {os.path.basename(geotiff)}")
        print(f"\nOutput directory: {OUTPUT_DIR}")
        print(f"\nNext steps:")
        print(f"  1. Use these maps for spatial velocity analysis")
        print(f"  2. Extract velocity along glacier centerline")
        print(f"  3. Create velocity evolution animations")
    else:
        print("\n⚠️  No velocity maps extracted successfully")

if __name__ == "__main__":
    main()

