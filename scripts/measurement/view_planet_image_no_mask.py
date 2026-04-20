#!/usr/bin/env python3
"""
Create Planet image WITHOUT cloud masking to see full image.
"""

import numpy as np
import rasterio
import matplotlib.pyplot as plt

IMAGE_FILE = "planet_images/from_website/glacier_psscene_analytic_sr_udm2/PSScene/20251028_062851_61_2500_3B_AnalyticMS_SR_clip.tif"

print("=" * 60)
print("Creating Planet Image WITHOUT Cloud Masking")
print("=" * 60)
print()

with rasterio.open(IMAGE_FILE) as src:
    # Read bands
    blue = src.read(1).astype(np.float32)
    green = src.read(2).astype(np.float32)
    red = src.read(3).astype(np.float32)
    
    # Scale
    scale = 0.0001
    blue_scaled = blue * scale
    green_scaled = green * scale
    red_scaled = red * scale
    
    # Stretch with gamma correction
    def stretch_band(band):
        valid = band[band > 0]
        if len(valid) == 0:
            return np.zeros_like(band)
        p1 = np.percentile(valid, 1)
        p99 = np.percentile(valid, 99)
        stretched = (band - p1) / (p99 - p1)
        stretched = np.clip(stretched, 0, 1)
        stretched = np.power(stretched, 1/1.5)  # Gamma correction
        return stretched
    
    red_display = stretch_band(red_scaled)
    green_display = stretch_band(green_scaled)
    blue_display = stretch_band(blue_scaled)
    
    # Create RGB - NO cloud masking
    rgb = np.dstack([red_display, green_display, blue_display])
    rgb = np.clip(rgb, 0, 1)
    
    print("Creating image without cloud mask...")
    
    # Full display
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.imshow(rgb, extent=[src.bounds.left, src.bounds.right, 
                          src.bounds.bottom, src.bounds.top],
             aspect='auto', interpolation='bilinear')
    ax.set_title("Didal Glacier - October 28, 2025\nFull Resolution (No Cloud Mask)", 
                 fontsize=16, fontweight='bold')
    ax.set_xlabel("Easting (m, UTM Zone 42N)", fontsize=12)
    ax.set_ylabel("Northing (m, UTM Zone 42N)", fontsize=12)
    ax.grid(True, alpha=0.3)
    
    output_file = "planet_images/from_website/glacier_no_mask.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"✓ Saved: {output_file}")
    plt.close()
    
    # Simple version
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.imshow(rgb, interpolation='bilinear')
    ax.axis('off')
    
    simple_file = "planet_images/from_website/glacier_no_mask_simple.png"
    plt.savefig(simple_file, dpi=300, bbox_inches='tight', pad_inches=0, facecolor='black')
    print(f"✓ Saved: {simple_file}")
    plt.close()
    
    print()
    print("Images created without cloud masking - should show full detail!")

