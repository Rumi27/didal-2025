#!/usr/bin/env python3
"""
Create a proper visualization from the September 17 full image.
Since the glacier is just outside the image, we'll show the full image
and mark where the glacier would be.
"""

import os
import numpy as np
import rasterio
from rasterio.warp import transform as transform_coords
from rasterio.crs import CRS as CRS_class
import matplotlib.pyplot as plt

# Glacier location
GLACIER_LAT = 39.0005
GLACIER_LON = 70.7385

OUTPUT_DIR = "planet_images/visualizations"

def create_sept_full_image():
    """Create visualization from full September 17 image."""
    image_path = "planet_images/newa_planet/20250917_064328_46_24b7_3B_AnalyticMS_SR.tif"
    
    print("Processing September 17 full image...")
    print("Note: Glacier location is just outside image bounds (2.3 m below).")
    print("Showing full image with glacier location marked.\n")
    
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
        print(f"Image size: {src.width} x {src.height} pixels")
        print()
        print(f"Glacier location (UTM): {glacier_x:.1f}E, {glacier_y:.1f}N")
        print(f"Glacier is {glacier_y - bounds.bottom:.1f} m below image bottom")
        print()
        
        # Read full image
        blue = src.read(1).astype(np.float32)
        green = src.read(2).astype(np.float32)
        red = src.read(3).astype(np.float32)
        
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
        if os.path.exists(udm2_file):
            try:
                with rasterio.open(udm2_file) as udm2_src:
                    cloud_band = udm2_src.read(6)
                    rgb[cloud_band == 1] = rgb[cloud_band == 1] * 0.3
            except:
                pass
        
        # Create visualization
        fig, ax = plt.subplots(figsize=(15, 15))
        
        ax.imshow(rgb, interpolation='bilinear')
        
        # Mark where glacier would be (just below image)
        img_height, img_width = rgb.shape[:2]
        
        # Convert glacier location to pixel coordinates
        # Glacier is outside, so mark at bottom edge
        x_frac = (glacier_x - bounds.left) / (bounds.right - bounds.left)
        x_pixel = x_frac * img_width
        
        # Mark at bottom of image with arrow pointing down
        ax.plot(x_pixel, img_height - 10, 'r+', markersize=25, markeredgewidth=4, 
                label='Didal Glacier (just below image)')
        ax.plot(x_pixel, img_height - 10, 'ro', markersize=20, fillstyle='none', 
                markeredgewidth=3)
        
        # Add arrow pointing down
        ax.arrow(x_pixel, img_height - 10, 0, 30, 
               head_width=30, head_length=20, fc='red', ec='red', lw=3)
        
        # Add text annotation
        ax.text(x_pixel, img_height - 50, 
               f'Glacier location\n({GLACIER_LAT:.4f}°N, {GLACIER_LON:.4f}°E)\n~2.3 m below image', 
               ha='center', va='top', fontsize=11, color='red', fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.8, edgecolor='red', lw=2))
        
        # Add scale and info
        ax.text(50, 50, 
               f'Image bounds: {bounds.left:.0f}E to {bounds.right:.0f}E\n'
               f'              {bounds.bottom:.0f}N to {bounds.top:.0f}N\n'
               f'Image size: {src.width} x {src.height} pixels\n'
               f'Coverage: {(bounds.right - bounds.left)/1000:.1f} km x {(bounds.top - bounds.bottom)/1000:.1f} km',
               ha='left', va='top', fontsize=10,
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        ax.set_title("Didal Glacier - 2025-09-17 (Before Initial Movement)\n"
                    "Full PlanetScope Scene - Glacier location is just outside image bounds (2.3 m below)", 
                    fontsize=14, fontweight='bold')
        ax.legend(loc='upper right', fontsize=11)
        ax.axis('off')
        
        output_file = os.path.join(OUTPUT_DIR, "2025-09-17_20250917_064328_46_24b7_full_scene.png")
        plt.savefig(output_file, dpi=300, bbox_inches='tight', pad_inches=0.1, facecolor='white')
        plt.close()
        
        print(f"✓ Saved: {output_file}")
        print()
        print("This image shows the full scene. The glacier location is marked")
        print("at the bottom edge, just outside the image bounds.")

if __name__ == "__main__":
    create_sept_full_image()

