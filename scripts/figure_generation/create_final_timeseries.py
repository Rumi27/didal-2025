#!/usr/bin/env python3
"""
Create final time series visualization with all available dates:
- September 12: Before initial movement
- October 25: Second movement
- November 1-3: Continued movement
"""

import os
import glob
import numpy as np
import rasterio
from rasterio.warp import transform as transform_coords
from rasterio.crs import CRS as CRS_class
from rasterio.windows import from_bounds
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from datetime import datetime
from PIL import Image

# Glacier location
GLACIER_LAT = 39.0005
GLACIER_LON = 70.7385

# Crop size (same as November images)
CROP_SIZE_M = 5000  # 5 km

OUTPUT_DIR = "planet_images/visualizations"

# Target dates and their event labels
TARGET_DATES = {
    "2025-09-12": {
        "label": "Before Initial Movement",
        "event": "Baseline (5 days before initial movement on Sept 17)"
    },
    "2025-10-25": {
        "label": "Second Movement",
        "event": "Second movement event"
    },
    "2025-11-01": {
        "label": "Continued Movement",
        "event": "Continued movement"
    },
    "2025-11-02": {
        "label": "Continued Movement",
        "event": "Continued movement"
    },
    "2025-11-03": {
        "label": "Earthquake Day",
        "event": "Earthquake occurred (magnitude 4-6)"
    }
}

def extract_date_from_filename(filename):
    """Extract date from Planet filename."""
    basename = os.path.basename(filename)
    date_str = basename[:8]
    try:
        date = datetime.strptime(date_str, "%Y%m%d")
        return date
    except:
        return None

def get_glacier_utm_coords(glacier_lon, glacier_lat, target_crs):
    """Convert glacier location to UTM coordinates."""
    x, y = transform_coords(
        CRS_class.from_epsg(4326),
        target_crs,
        [glacier_lon], [glacier_lat]
    )
    return x[0], y[0]

def find_all_images():
    """Find all images for target dates."""
    print("Searching for images...")
    print()
    
    # Search locations
    search_dirs = [
        "planet_images/newa_planet",
        "planet_images/new_september",
        "planet_images/new_september/didal_glacier_september_2025/files/PSScene",
        "planet_images/new_september/extracted",
        "planet_images/sep_2025"
    ]
    
    all_images = []
    for search_dir in search_dirs:
        if os.path.exists(search_dir):
            pattern = os.path.join(search_dir, "**", "*_3B_AnalyticMS_SR.tif")
            all_images.extend(glob.glob(pattern, recursive=True))
    
    # Filter for target dates
    target_images = []
    for img_file in all_images:
        date = extract_date_from_filename(img_file)
        if date:
            date_str = date.strftime("%Y-%m-%d")
            if date_str in TARGET_DATES:
                target_images.append((date, img_file))
    
    # Sort by date
    target_images.sort(key=lambda x: x[0])
    
    print(f"Found {len(target_images)} images for target dates:")
    for date, img_file in target_images:
        date_str = date.strftime("%Y-%m-%d")
        print(f"  {date_str}: {os.path.basename(img_file)}")
    print()
    
    return target_images

def process_image_with_crop(image_path, crop_left, crop_right, crop_bottom, crop_top):
    """Process image with fixed crop window."""
    date = extract_date_from_filename(image_path)
    date_str = date.strftime("%Y-%m-%d") if date else "unknown"
    
    print(f"Processing {date_str}: {os.path.basename(image_path)}")
    
    try:
        with rasterio.open(image_path) as src:
            bounds = src.bounds
            crs = src.crs
            
            # Convert glacier location to UTM
            glacier_x, glacier_y = get_glacier_utm_coords(GLACIER_LON, GLACIER_LAT, crs)
            
            # Check if glacier is in bounds
            in_bounds = (bounds.left <= glacier_x <= bounds.right and 
                        bounds.bottom <= glacier_y <= bounds.top)
            
            if not in_bounds:
                print(f"  ⚠️  Glacier location ({glacier_x:.1f}E, {glacier_y:.1f}N) not in image bounds")
                print(f"     Image bounds: {bounds.left:.1f}E to {bounds.right:.1f}E")
                print(f"                   {bounds.bottom:.1f}N to {bounds.top:.1f}N")
            
            # Clip crop window to image bounds
            actual_left = max(crop_left, bounds.left)
            actual_right = min(crop_right, bounds.right)
            actual_bottom = max(crop_bottom, bounds.bottom)
            actual_top = min(crop_top, bounds.top)
            
            # Create crop window
            crop_window = from_bounds(
                actual_left, actual_bottom, actual_right, actual_top,
                src.transform
            )
            
            # Read cropped data
            blue = src.read(1, window=crop_window).astype(np.float32)
            green = src.read(2, window=crop_window).astype(np.float32)
            red = src.read(3, window=crop_window).astype(np.float32)
            
            # Apply scale factor
            scale = 0.0001
            blue_scaled = blue * scale
            green_scaled = green * scale
            red_scaled = red * scale
            
            # Stretch bands
            def stretch_band(band):
                valid = band[band > 0]
                if len(valid) == 0:
                    return np.zeros_like(band)
                p1 = np.percentile(valid, 1)
                p99 = np.percentile(valid, 99)
                if p99 == p1:
                    return np.ones_like(band) if p99 > 0 else np.zeros_like(band)
                stretched = (band - p1) / (p99 - p1)
                stretched = np.clip(stretched, 0, 1)
                stretched = np.power(stretched, 1/1.5)
                return stretched
            
            red_display = stretch_band(red_scaled)
            green_display = stretch_band(green_scaled)
            blue_display = stretch_band(blue_scaled)
            
            # Create RGB
            rgb = np.dstack([red_display, green_display, blue_display])
            rgb = np.clip(rgb, 0, 1)
            
            # Apply cloud mask if available
            udm2_file = image_path.replace('_3B_AnalyticMS_SR.tif', '_3B_udm2.tif')
            if not os.path.exists(udm2_file):
                # Try alternative paths
                udm2_file = image_path.replace('AnalyticMS_SR.tif', 'udm2.tif')
                # Try in same directory structure
                base_dir = os.path.dirname(image_path)
                if 'analytic_sr_udm2' in base_dir:
                    udm2_file = os.path.join(base_dir, image_path.split('/')[-1].replace('_3B_AnalyticMS_SR.tif', '_3B_udm2.tif'))
            
            if os.path.exists(udm2_file):
                try:
                    with rasterio.open(udm2_file) as udm2_src:
                        cloud_band = udm2_src.read(6, window=crop_window)
                        rgb[cloud_band == 1] = rgb[cloud_band == 1] * 0.3
                except:
                    pass
            
            return {
                'rgb': rgb,
                'date': date,
                'filename': os.path.basename(image_path),
                'glacier_in_bounds': in_bounds
            }
    
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_final_timeseries():
    """Create final time series visualization."""
    print("=" * 70)
    print("Create Final Time Series Visualization")
    print("=" * 70)
    print()
    print(f"Glacier location: {GLACIER_LAT:.6f}°N, {GLACIER_LON:.6f}°E")
    print()
    
    # Find all images
    target_images = find_all_images()
    
    if not target_images:
        print("No images found for target dates!")
        return
    
    # Determine crop window from November reference
    print("Determining crop window from November reference...")
    nov_images = glob.glob("planet_images/newa_planet/2025110*_3B_AnalyticMS_SR.tif")
    
    if not nov_images:
        print("No November reference images found!")
        return
    
    reference_image = sorted(nov_images)[0]
    print(f"Using reference: {os.path.basename(reference_image)}")
    
    with rasterio.open(reference_image) as src:
        crs = src.crs
        glacier_x, glacier_y = get_glacier_utm_coords(GLACIER_LON, GLACIER_LAT, crs)
        
        crop_left = glacier_x - CROP_SIZE_M / 2
        crop_right = glacier_x + CROP_SIZE_M / 2
        crop_bottom = glacier_y - CROP_SIZE_M / 2
        crop_top = glacier_y + CROP_SIZE_M / 2
        
        print(f"Crop window: {crop_left:.1f}E to {crop_right:.1f}E")
        print(f"             {crop_bottom:.1f}N to {crop_top:.1f}N")
        print()
    
    # Process all images
    print("Processing images...")
    images_data = []
    for date, img_file in target_images:
        img_data = process_image_with_crop(
            img_file, crop_left, crop_right, crop_bottom, crop_top
        )
        if img_data:
            images_data.append(img_data)
    
    print()
    print(f"Successfully processed {len(images_data)} images")
    print()
    
    if not images_data:
        print("No images could be processed!")
        return
    
    # Create time series visualization
    print("Creating final time series visualization...")
    
    # Sort by date
    images_data.sort(key=lambda x: x['date'])
    
    n_images = len(images_data)
    cols = min(3, n_images)
    rows = (n_images + cols - 1) // cols
    
    fig = plt.figure(figsize=(18, 6 * rows))
    gs = GridSpec(rows, cols, figure=fig, hspace=0.35, wspace=0.25)
    
    for i, img_data in enumerate(images_data):
        row = i // cols
        col = i % cols
        ax = fig.add_subplot(gs[row, col])
        
        ax.imshow(img_data['rgb'], interpolation='bilinear')
        
        # Mark glacier location (center)
        img_height, img_width = img_data['rgb'].shape[:2]
        ax.plot(img_width/2, img_height/2, 'r+', markersize=20, markeredgewidth=3, 
                label='Didal Glacier')
        ax.plot(img_width/2, img_height/2, 'ro', markersize=15, fillstyle='none', 
                markeredgewidth=2)
        
        date_str = img_data['date'].strftime("%Y-%m-%d")
        date_info = TARGET_DATES.get(date_str, {})
        label = date_info.get("label", "")
        event = date_info.get("event", "")
        
        title = f"{date_str}"
        if label:
            title += f"\n{label}"
        if event:
            title += f"\n({event})"
        
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.legend(loc='upper right', fontsize=9)
        ax.axis('off')
    
    # Overall title
    fig.suptitle("Didal Glacier Time Series - Complete Event Sequence\n"
                "PlanetScope Imagery (3 m resolution) - 5 km × 5 km area centered on glacier\n"
                f"Glacier location: {GLACIER_LAT:.6f}°N, {GLACIER_LON:.6f}°E", 
                fontsize=16, fontweight='bold', y=0.98)
    
    output_file = os.path.join(OUTPUT_DIR, "final_timeseries_complete.png")
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"✓ Saved: {output_file}")
    print()
    
    # Create individual visualizations
    print("Creating individual visualizations...")
    for img_data in images_data:
        date_str = img_data['date'].strftime("%Y-%m-%d")
        date_info = TARGET_DATES.get(date_str, {})
        label = date_info.get("label", "")
        
        fig, ax = plt.subplots(figsize=(12, 12))
        
        ax.imshow(img_data['rgb'], interpolation='bilinear')
        
        img_height, img_width = img_data['rgb'].shape[:2]
        ax.plot(img_width/2, img_height/2, 'r+', markersize=25, markeredgewidth=4, 
                label='Didal Glacier')
        ax.plot(img_width/2, img_height/2, 'ro', markersize=20, fillstyle='none', 
                markeredgewidth=3)
        
        title = f"Didal Glacier - {date_str}"
        if label:
            title += f"\n{label}"
        title += f"\nFixed crop window (5 km × 5 km)"
        
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend(loc='upper right', fontsize=11)
        ax.axis('off')
        
        filename_base = img_data['filename'].replace('_3B_AnalyticMS_SR.tif', '').replace('AnalyticMS_SR.tif', '')
        output_file = os.path.join(OUTPUT_DIR, f"{date_str}_{filename_base}_final.png")
        plt.savefig(output_file, dpi=300, bbox_inches='tight', pad_inches=0.1, facecolor='white')
        plt.close()
        
        print(f"  ✓ Saved: {output_file}")
    
    print()
    print("=" * 70)
    print("Complete!")
    print("=" * 70)
    print()
    print("Final time series created with:")
    for img_data in images_data:
        date_str = img_data['date'].strftime("%Y-%m-%d")
        date_info = TARGET_DATES.get(date_str, {})
        print(f"  - {date_str}: {date_info.get('label', 'N/A')}")
    print()
    print(f"Output files in: {OUTPUT_DIR}/")
    print("  - final_timeseries_complete.png (all dates)")
    print("  - Individual *_final.png files for each date")

if __name__ == "__main__":
    create_final_timeseries()
