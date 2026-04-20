#!/usr/bin/env python3
"""
Fixed script to properly view and process the Planet image.
Better handling of contrast and cloud masking.
"""

import os
import numpy as np
import rasterio
import matplotlib.pyplot as plt

# Image file
IMAGE_FILE = "planet_images/from_website/glacier_psscene_analytic_sr_udm2/PSScene/20251028_062851_61_2500_3B_AnalyticMS_SR_clip.tif"
UDM2_FILE = "planet_images/from_website/glacier_psscene_analytic_sr_udm2/PSScene/20251028_062851_61_2500_3B_udm2_clip.tif"

def view_planet_image():
    """
    Open and display the Planet image properly.
    """
    if not os.path.exists(IMAGE_FILE):
        print(f"Error: Image file not found: {IMAGE_FILE}")
        return
    
    print("=" * 60)
    print("Viewing Planet Image - Full Resolution (Fixed)")
    print("=" * 60)
    print()
    
    # Open image
    with rasterio.open(IMAGE_FILE) as src:
        print(f"Image: {IMAGE_FILE}")
        print(f"Dimensions: {src.width} x {src.height} pixels")
        print(f"Resolution: {src.res[0]:.2f} m per pixel")
        print()
        
        # Read bands (PlanetScope: Blue, Green, Red, NIR)
        blue = src.read(1).astype(np.float32)
        green = src.read(2).astype(np.float32)
        red = src.read(3).astype(np.float32)
        
        # Apply scale factor (Planet uses scale: 0.0001)
        scale = 0.0001
        blue_scaled = blue * scale
        green_scaled = green * scale
        red_scaled = red * scale
        
        print("Scaled reflectance values:")
        print(f"  Red:   {red_scaled.min():.4f} to {red_scaled.max():.4f}")
        print(f"  Green: {green_scaled.min():.4f} to {green_scaled.max():.4f}")
        print(f"  Blue:  {blue_scaled.min():.4f} to {blue_scaled.max():.4f}")
        print()
        
        # Create RGB composite with better stretching
        # Use min-max stretching with a small buffer
        def stretch_band(band):
            valid = band[band > 0]
            if len(valid) == 0:
                return np.zeros_like(band)
            
            # Use 1st and 99th percentile for better contrast
            p1 = np.percentile(valid, 1)
            p99 = np.percentile(valid, 99)
            
            # Stretch to 0-1 range
            stretched = (band - p1) / (p99 - p1)
            stretched = np.clip(stretched, 0, 1)
            
            # Apply gamma correction for better visualization (gamma=1.5)
            stretched = np.power(stretched, 1/1.5)
            
            return stretched
        
        print("Stretching bands with gamma correction...")
        red_display = stretch_band(red_scaled)
        green_display = stretch_band(green_scaled)
        blue_display = stretch_band(blue_scaled)
        
        print(f"Display ranges after stretching:")
        print(f"  Red:   {red_display.min():.3f} to {red_display.max():.3f}")
        print(f"  Green: {green_display.min():.3f} to {green_display.max():.3f}")
        print(f"  Blue:  {blue_display.min():.3f} to {blue_display.max():.3f}")
        print()
        
        # Create RGB array
        rgb = np.dstack([red_display, green_display, blue_display])
        
        # Check cloud mask but don't apply it aggressively
        if os.path.exists(UDM2_FILE):
            print("Checking cloud mask...")
            with rasterio.open(UDM2_FILE) as udm2_src:
                cloud_band = udm2_src.read(6)  # Cloud band
                clear_band = udm2_src.read(1)   # Clear band (1=clear, 0=not clear)
                
                cloud_pixels = np.sum(cloud_band == 1)
                clear_pixels = np.sum(clear_band == 1)
                total_pixels = cloud_band.size
                
                print(f"  Cloud pixels: {cloud_pixels:,} ({cloud_pixels/total_pixels*100:.1f}%)")
                print(f"  Clear pixels: {clear_pixels:,} ({clear_pixels/total_pixels*100:.1f}%)")
                print()
                
                # Only mask obvious clouds, keep everything else
                # Make clouds slightly darker but not black
                rgb[cloud_band == 1] = rgb[cloud_band == 1] * 0.3  # Darken clouds by 70%
        
        # Ensure RGB values are in correct range
        rgb = np.clip(rgb, 0, 1)
        
        # Create display version
        print("Creating display version...")
        fig, ax = plt.subplots(figsize=(14, 10))
        
        # Display RGB image
        ax.imshow(rgb, extent=[src.bounds.left, src.bounds.right, 
                               src.bounds.bottom, src.bounds.top],
                 aspect='auto', interpolation='bilinear')
        
        ax.set_title("Didal Glacier - October 28, 2025\nFull Resolution (3 m/pixel)", 
                     fontsize=16, fontweight='bold')
        ax.set_xlabel("Easting (m, UTM Zone 42N)", fontsize=12)
        ax.set_ylabel("Northing (m, UTM Zone 42N)", fontsize=12)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # Save high-quality version
        output_file = "planet_images/from_website/glacier_display_rgb.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"✓ Saved display version to: {output_file}")
        plt.close()
        
        # Create preview version (downsampled)
        print("Creating preview version...")
        downsample = 5  # Every 5th pixel
        preview = rgb[::downsample, ::downsample]
        
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.imshow(preview, interpolation='bilinear')
        ax.set_title("Didal Glacier - Preview", fontsize=14)
        ax.axis('off')
        
        preview_file = "planet_images/from_website/glacier_preview_rgb.png"
        plt.savefig(preview_file, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"✓ Saved preview to: {preview_file}")
        plt.close()
        
        # Also create a simple RGB composite without axes for direct use
        print("Creating simple RGB composite...")
        fig, ax = plt.subplots(figsize=(12, 10))
        ax.imshow(rgb, interpolation='bilinear')
        ax.axis('off')
        
        simple_file = "planet_images/from_website/glacier_rgb_simple.png"
        plt.savefig(simple_file, dpi=300, bbox_inches='tight', pad_inches=0, facecolor='black')
        print(f"✓ Saved simple RGB to: {simple_file}")
        plt.close()
        
        print()
        print("=" * 60)
        print("Image processing complete!")
        print("=" * 60)
        print()
        print("Generated files:")
        print(f"  1. {output_file} - Full display with axes")
        print(f"  2. {preview_file} - Quick preview")
        print(f"  3. {simple_file} - Simple RGB (no axes, for figures)")
        print()
        print("These images should now be visible and properly colored!")


if __name__ == "__main__":
    view_planet_image()

