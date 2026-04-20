#!/usr/bin/env python3
"""
Create a proper crop from September 17 image.
Since glacier is just outside, we'll crop to the bottom part of the image
(where the glacier would be if it were in the image).
"""

import os
import numpy as np
import rasterio
from rasterio.warp import transform as transform_coords
from rasterio.crs import CRS as CRS_class
from rasterio.windows import from_bounds
import matplotlib.pyplot as plt

# Glacier location
GLACIER_LAT = 39.0005
GLACIER_LON = 70.7385

# Crop size (same as November images)
CROP_SIZE_M = 5000  # 5 km

OUTPUT_DIR = "planet_images/visualizations"

def create_sept_proper_crop():
    """Create a proper crop from September 17 image."""
    image_path = "planet_images/newa_planet/20250917_064328_46_24b7_3B_AnalyticMS_SR.tif"
    
    print("Creating proper crop from September 17 image...")
    print("Note: Glacier is 2.3 m below image, so cropping to bottom area.\n")
    
    with rasterio.open(image_path) as src:
        bounds = src.bounds
        crs = src.crs
        
        # Convert glacier location to UTM
        glacier_x, glacier_y = transform_coords(
            CRS_class.from_epsg(4326),
            crs,
            [GLACIER_LON], [GLACIER_LAT]
        )
        glacier_x = glacier_x[0]
        glacier_y = glacier_y[0]
        
        print(f"Image bounds: {bounds.left:.1f}E to {bounds.right:.1f}E")
        print(f"              {bounds.bottom:.1f}N to {bounds.top:.1f}N")
        print(f"Glacier location: {glacier_x:.1f}E, {glacier_y:.1f}N")
        print(f"Glacier is {glacier_y - bounds.bottom:.1f} m below image bottom")
        print()
        
        # Create crop area: bottom part of image, centered horizontally on glacier
        crop_left = max(bounds.left, glacier_x - CROP_SIZE_M / 2)
        crop_right = min(bounds.right, glacier_x + CROP_SIZE_M / 2)
        crop_bottom = bounds.bottom  # Start at image bottom
        crop_top = min(bounds.top, bounds.bottom + CROP_SIZE_M)  # 5 km up from bottom
        
        print(f"Crop area (within image bounds):")
        print(f"  {crop_left:.1f}E to {crop_right:.1f}E")
        print(f"  {crop_bottom:.1f}N to {crop_top:.1f}N")
        print(f"  Size: {(crop_right - crop_left)/1000:.1f} km x {(crop_top - crop_bottom)/1000:.1f} km")
        print()
        
        # Create crop window
        crop_window = from_bounds(
            crop_left, crop_bottom, crop_right, crop_top,
            src.transform
        )
        
        # Read cropped data
        blue = src.read(1, window=crop_window).astype(np.float32)
        green = src.read(2, window=crop_window).astype(np.float32)
        red = src.read(3, window=crop_window).astype(np.float32)
        
        print(f"Cropped image size: {red.shape[1]} x {red.shape[0]} pixels")
        print(f"Data range - Red: {red.min()} to {red.max()}")
        print(f"Data range - Green: {green.min()} to {green.max()}")
        print(f"Data range - Blue: {blue.min()} to {blue.max()}")
        print()
        
        # Check if we have valid data
        if red.size == 0 or red.max() == 0:
            print("ERROR: No valid data in crop!")
            return
        
        # Apply scale factor
        scale = 0.0001
        blue_scaled = blue * scale
        green_scaled = green * scale
        red_scaled = red * scale
        
        # Stretch bands (same as November images)
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
            stretched = np.power(stretched, 1/1.5)  # Gamma correction
            return stretched
        
        red_display = stretch_band(red_scaled)
        green_display = stretch_band(green_scaled)
        blue_display = stretch_band(blue_scaled)
        
        # Create RGB
        rgb = np.dstack([red_display, green_display, blue_display])
        rgb = np.clip(rgb, 0, 1)
        
        # Apply cloud mask if available
        udm2_file = image_path.replace('_3B_AnalyticMS_SR.tif', '_3B_udm2.tif')
        if os.path.exists(udm2_file):
            try:
                with rasterio.open(udm2_file) as udm2_src:
                    cloud_band = udm2_src.read(6, window=crop_window)
                    rgb[cloud_band == 1] = rgb[cloud_band == 1] * 0.3
            except:
                pass
        
        # Create visualization
        fig, ax = plt.subplots(figsize=(10, 10))
        
        ax.imshow(rgb, interpolation='bilinear')
        
        # Mark where glacier would be (just below the crop)
        img_height, img_width = rgb.shape[:2]
        
        # Glacier X position in crop
        x_frac = (glacier_x - crop_left) / (crop_right - crop_left)
        x_pixel = x_frac * img_width
        
        # Mark at bottom of crop with arrow pointing down
        ax.plot(x_pixel, img_height - 10, 'r+', markersize=20, markeredgewidth=3, 
                label='Didal Glacier (2.3 m below)')
        ax.plot(x_pixel, img_height - 10, 'ro', markersize=15, fillstyle='none', 
                markeredgewidth=2)
        
        # Add arrow pointing down
        ax.arrow(x_pixel, img_height - 10, 0, 20, 
               head_width=25, head_length=15, fc='red', ec='red', lw=2)
        
        # Add text annotation
        ax.text(x_pixel, img_height - 40, 
               'Glacier location\n~2.3 m below', 
               ha='center', va='top', fontsize=10, color='red', fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.8, edgecolor='red', lw=2))
        
        ax.set_title("Didal Glacier - 2025-09-17 (Before Initial Movement)\n"
                    "Crop from bottom of image - Glacier location is 2.3 m below this view\n"
                    f"Crop area: {(crop_right - crop_left)/1000:.1f} km x {(crop_top - crop_bottom)/1000:.1f} km", 
                    fontsize=12, fontweight='bold')
        ax.legend(loc='upper right')
        ax.axis('off')
        
        output_file = os.path.join(OUTPUT_DIR, "2025-09-17_20250917_064328_46_24b7_fixed_crop.png")
        plt.savefig(output_file, dpi=300, bbox_inches='tight', pad_inches=0.1, facecolor='white')
        plt.close()
        
        print(f"✓ Saved: {output_file}")
        print()
        print("This crop shows the area closest to the glacier location.")
        print("The glacier itself is just 2.3 m below the bottom of this view.")

if __name__ == "__main__":
    create_sept_proper_crop()

