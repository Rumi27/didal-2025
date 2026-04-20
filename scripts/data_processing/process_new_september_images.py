#!/usr/bin/env python3
"""
Process new September Planet images that actually cover the glacier location.
These images are from a different collection and should cover the glacier properly.
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
import json

# Glacier location
GLACIER_LAT = 39.0005
GLACIER_LON = 70.7385

# Crop size (same as November images)
CROP_SIZE_M = 5000  # 5 km

OUTPUT_DIR = "planet_images/visualizations"

# Collection info
COLLECTION_ID = "38647acb-8696-4a10-af32-56e41f5d8141"
DELIVERY_ID = "df00030d-eb45-4feb-9efa-0932b0827ca6"

# Image IDs from the new collection
NEW_SEPT_IMAGE_IDS = [
    "20250914_063119_12_252d",
    "20250914_062418_62_24f0",
    "20250913_063820_03_24d5",
    "20250913_063818_16_24d5",
    "20250913_062702_66_2516",
    "20250912_063959_56_24fb",
    "20250912_063417_10_252b",
    "20250909_063919_68_24ed",
    "20250909_063917_61_24ed"
]

def extract_date_from_filename(filename):
    """Extract date from Planet filename."""
    basename = os.path.basename(filename)
    date_str = basename[:8]
    try:
        date = datetime.strptime(date_str, "%Y%m%d")
        return date
    except:
        return None

def find_new_september_images():
    """Find the new September images."""
    print("Searching for new September images...")
    print()
    
    # Search in common locations
    search_dirs = [
        ".",
        "planet_images",
        "planet_images/sep_2025",
        "planet_images/sep_2025/didal_glacier_september_2025/files/PSScene",
        "planet_images/new_september",
        "planet_images/newa_planet",
        "planet_images/from_website",
        "satellite_data/planet",
        "Downloads",
        "~/Downloads"
    ]
    
    found_images = []
    
    for img_id in NEW_SEPT_IMAGE_IDS:
        # Try different filename patterns and folder structures
        patterns = [
            f"**/{img_id}*_3B_AnalyticMS_SR.tif",
            f"**/{img_id}*AnalyticMS_SR.tif",
            f"**/{img_id}*.tif",
            f"**/*{img_id}*.tif",
            f"{img_id}*_3B_AnalyticMS_SR.tif",
            f"{img_id}*AnalyticMS_SR.tif",
            f"{img_id}*.tif",
            # Planet order structure
            f"**/{img_id}/**/*_3B_AnalyticMS_SR.tif",
            f"**/{img_id}/analytic_sr_udm2/*_3B_AnalyticMS_SR.tif"
        ]
        
        for search_dir in search_dirs:
            for pattern in patterns:
                matches = glob.glob(os.path.join(search_dir, pattern), recursive=True)
                if matches:
                    found_images.extend(matches)
                    break
            if matches:
                break
    
    # Remove duplicates
    found_images = sorted(list(set(found_images)))
    
    print(f"Found {len(found_images)} new September images:")
    for img_file in found_images:
        date = extract_date_from_filename(img_file)
        date_str = date.strftime("%Y-%m-%d") if date else "unknown"
        print(f"  {date_str}: {os.path.basename(img_file)}")
    print()
    
    return found_images

def get_glacier_utm_coords(glacier_lon, glacier_lat, target_crs):
    """Convert glacier location to UTM coordinates."""
    x, y = transform_coords(
        CRS_class.from_epsg(4326),  # WGS84 geographic
        target_crs,  # Image CRS
        [glacier_lon], [glacier_lat]
    )
    return x[0], y[0]

def process_image_with_crop(image_path, crop_left, crop_right, crop_bottom, crop_top):
    """Process image with fixed crop window."""
    print(f"Processing: {os.path.basename(image_path)}")
    
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
                # Try alternative naming
                udm2_file = image_path.replace('AnalyticMS_SR.tif', 'udm2.tif')
            if os.path.exists(udm2_file):
                try:
                    with rasterio.open(udm2_file) as udm2_src:
                        cloud_band = udm2_src.read(6, window=crop_window)
                        rgb[cloud_band == 1] = rgb[cloud_band == 1] * 0.3
                except:
                    pass
            
            return {
                'rgb': rgb,
                'date': extract_date_from_filename(image_path),
                'filename': os.path.basename(image_path),
                'glacier_in_bounds': in_bounds,
                'glacier_location_utm': (glacier_x, glacier_y)
            }
    
    except Exception as e:
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main function."""
    print("=" * 70)
    print("Process New September Planet Images")
    print("=" * 70)
    print()
    print(f"Collection ID: {COLLECTION_ID}")
    print(f"Delivery ID: {DELIVERY_ID}")
    print(f"Glacier location: {GLACIER_LAT:.6f}°N, {GLACIER_LON:.6f}°E")
    print()
    
    # Find images
    image_files = find_new_september_images()
    
    if not image_files:
        print("No new September images found!")
        print()
        print("Please ensure images are in one of these locations:")
        print("  - Current directory")
        print("  - planet_images/")
        print("  - planet_images/newa_planet/")
        print("  - satellite_data/planet/")
        print()
        print("Looking for files matching these IDs:")
        for img_id in NEW_SEPT_IMAGE_IDS[:5]:
            print(f"  - {img_id}*")
        return
    
    # Determine crop window from a good November image (reference)
    print("Determining crop window from November reference image...")
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
    
    # Process all new September images
    print("Processing new September images...")
    images_data = []
    for img_file in image_files:
        img_data = process_image_with_crop(
            img_file, crop_left, crop_right, crop_bottom, crop_top
        )
        if img_data:
            images_data.append(img_data)
    
    print(f"\nSuccessfully processed {len(images_data)} images")
    print()
    
    # Create visualizations
    if images_data:
        print("Creating visualizations...")
        for img_data in images_data:
            if img_data is None:
                continue
            
            date_str = img_data['date'].strftime("%Y-%m-%d") if img_data['date'] else "unknown"
            filename_base = img_data['filename'].replace('_3B_AnalyticMS_SR.tif', '').replace('AnalyticMS_SR.tif', '')
            
            fig, ax = plt.subplots(figsize=(10, 10))
            
            ax.imshow(img_data['rgb'], interpolation='bilinear')
            
            # Mark glacier location
            img_height, img_width = img_data['rgb'].shape[:2]
            ax.plot(img_width/2, img_height/2, 'r+', markersize=20, markeredgewidth=3, 
                    label='Didal Glacier')
            ax.plot(img_width/2, img_height/2, 'ro', markersize=15, fillstyle='none', 
                    markeredgewidth=2)
            
            status = "✓ Glacier in image" if img_data['glacier_in_bounds'] else "⚠️ Glacier near edge"
            
            ax.set_title(f"Didal Glacier - {date_str}\n{filename_base}\n"
                        f"{status} - Fixed crop (5 km x 5 km)", 
                        fontsize=12, fontweight='bold')
            ax.legend(loc='upper right')
            ax.axis('off')
            
            output_file = os.path.join(OUTPUT_DIR, f"{date_str}_{filename_base}_fixed_crop.png")
            plt.savefig(output_file, dpi=300, bbox_inches='tight', pad_inches=0.1, facecolor='white')
            plt.close()
            
            print(f"  ✓ Saved: {output_file}")
        
        # Create time series
        print("\nCreating time series comparison...")
        valid_images = [img for img in images_data if img is not None and img['date'] is not None]
        valid_images.sort(key=lambda x: x['date'])
        
        if valid_images:
            n_images = len(valid_images)
            cols = min(3, n_images)
            rows = (n_images + cols - 1) // cols
            
            fig = plt.figure(figsize=(15, 5 * rows))
            gs = GridSpec(rows, cols, figure=fig, hspace=0.3, wspace=0.2)
            
            for i, img_data in enumerate(valid_images):
                row = i // cols
                col = i % cols
                ax = fig.add_subplot(gs[row, col])
                
                ax.imshow(img_data['rgb'], interpolation='bilinear')
                
                img_height, img_width = img_data['rgb'].shape[:2]
                ax.plot(img_width/2, img_height/2, 'r+', markersize=15, markeredgewidth=2)
                ax.plot(img_width/2, img_height/2, 'ro', markersize=10, fillstyle='none', markeredgewidth=1.5)
                
                date_str = img_data['date'].strftime("%Y-%m-%d")
                ax.set_title(f"{date_str}", fontsize=11, fontweight='bold')
                ax.axis('off')
            
            fig.suptitle("New September Images - Didal Glacier\n"
                        f"Collection: {COLLECTION_ID[:8]}...\n"
                        "Fixed crop window (5 km x 5 km)", 
                        fontsize=14, fontweight='bold', y=0.98)
            
            output_file = os.path.join(OUTPUT_DIR, "september_new_timeseries.png")
            plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
            plt.close()
            
            print(f"  ✓ Saved: {output_file}")
        
        print()
        print("=" * 70)
        print("Complete!")
        print("=" * 70)
        print()
        print("New September images processed and visualized.")
        print("These images should properly cover the glacier location!")

if __name__ == "__main__":
    main()

