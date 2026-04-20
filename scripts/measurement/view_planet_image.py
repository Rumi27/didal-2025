#!/usr/bin/env python3
"""
Script to properly view and process the Planet image.
Converts the 16-bit analytic image to a viewable RGB composite.
"""

import os
import numpy as np
try:
    import rasterio
    from rasterio.plot import show
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
except ImportError:
    print("Required packages not installed.")
    print("Install with: pip install rasterio matplotlib")
    exit(1)

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
    print("Viewing Planet Image - Full Resolution")
    print("=" * 60)
    print()
    
    # Open image
    with rasterio.open(IMAGE_FILE) as src:
        print(f"Image: {IMAGE_FILE}")
        print(f"Dimensions: {src.width} x {src.height} pixels")
        print(f"Resolution: {src.res[0]:.2f} m per pixel")
        print(f"Coordinate system: EPSG:{src.crs.to_epsg()}")
        print(f"Bands: {src.count}")
        print(f"Data type: {src.dtypes[0]}")
        print()
        
        # Read bands (PlanetScope: Blue, Green, Red, NIR)
        blue = src.read(1)
        green = src.read(2)
        red = src.read(3)
        nir = src.read(4)
        
        print("Band statistics:")
        print(f"  Blue:  min={blue.min()}, max={blue.max()}, mean={blue.mean():.1f}")
        print(f"  Green: min={green.min()}, max={green.max()}, mean={green.mean():.1f}")
        print(f"  Red:   min={red.min()}, max={red.max()}, mean={red.mean():.1f}")
        print(f"  NIR:   min={nir.min()}, max={nir.max()}, mean={nir.mean():.1f}")
        print()
        
        # Apply scale factor (Planet uses scale: 0.0001)
        scale = 0.0001
        blue_scaled = blue.astype(np.float32) * scale
        green_scaled = green.astype(np.float32) * scale
        red_scaled = red.astype(np.float32) * scale
        nir_scaled = nir.astype(np.float32) * scale
        
        # Create RGB composite (stretch to 0-1 range for display)
        # Use percentile stretching to handle outliers
        def stretch_band(band, lower_percentile=1, upper_percentile=99):
            # Get valid (non-zero) pixels
            valid = band[band > 0]
            if len(valid) == 0:
                print(f"  Warning: All values are zero in band")
                return np.zeros_like(band)
            
            lower = np.percentile(valid, lower_percentile)
            upper = np.percentile(valid, upper_percentile)
            
            if upper == lower:
                # All values are the same
                return np.ones_like(band) if upper > 0 else np.zeros_like(band)
            
            stretched = np.clip((band - lower) / (upper - lower), 0, 1)
            return stretched
        
        print("Stretching bands for display...")
        red_display = stretch_band(red_scaled)
        green_display = stretch_band(green_scaled)
        blue_display = stretch_band(blue_scaled)
        
        print(f"Display value ranges:")
        print(f"  Red:   {red_display.min():.3f} to {red_display.max():.3f}")
        print(f"  Green: {green_display.min():.3f} to {green_display.max():.3f}")
        print(f"  Blue:  {blue_display.min():.3f} to {blue_display.max():.3f}")
        print()
        
        # Create RGB array
        rgb = np.dstack([red_display, green_display, blue_display])
        
        # Apply cloud mask if UDM2 available (but don't mask everything)
        if os.path.exists(UDM2_FILE):
            print("Checking cloud mask from UDM2...")
            with rasterio.open(UDM2_FILE) as udm2_src:
                cloud_band = udm2_src.read(6)  # Cloud band (0=no cloud, 1=cloud)
                cloud_pixels = np.sum(cloud_band == 1)
                total_pixels = cloud_band.size
                cloud_percent = (cloud_pixels / total_pixels) * 100
                print(f"  Cloud coverage: {cloud_percent:.1f}%")
                
                # Only mask if reasonable cloud coverage
                if cloud_percent < 50:  # Don't mask if more than 50% clouds
                    rgb[cloud_band == 1] = [0.1, 0.1, 0.1]  # Dark gray instead of black
                    print("  Applied cloud masking")
                else:
                    print("  Skipping cloud mask (too much cloud coverage)")
        print()
        
        # Display image
        print("Creating display version...")
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # Show RGB image
        ax.imshow(rgb, extent=[src.bounds.left, src.bounds.right, 
                               src.bounds.bottom, src.bounds.top])
        ax.set_title(f"Didal Glacier - October 28, 2025\nFull Resolution (3 m/pixel)", fontsize=14)
        ax.set_xlabel("Easting (m, UTM Zone 42N)")
        ax.set_ylabel("Northing (m, UTM Zone 42N)")
        
        # Save display version
        output_file = "planet_images/from_website/glacier_display_rgb.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✓ Saved display version to: {output_file}")
        
        # Don't show interactively, just save
        plt.close()
        
        # Also create a smaller preview for quick viewing
        print()
        print("Creating preview version...")
        # Downsample for preview (every 10th pixel)
        preview = rgb[::10, ::10]
        preview_file = "planet_images/from_website/glacier_preview_rgb.png"
        plt.figure(figsize=(8, 8))
        plt.imshow(preview)
        plt.axis('off')
        plt.title("Didal Glacier - Preview (downsampled)")
        plt.savefig(preview_file, dpi=150, bbox_inches='tight')
        print(f"Saved preview to: {preview_file}")
        plt.close()
        
        print()
        print("=" * 60)
        print("Image viewing complete!")
        print("=" * 60)
        print()
        print("The downloaded TIFF is FULL-RESOLUTION scientific data.")
        print("The Planet website shows a processed/visualized version.")
        print("Your file is actually HIGHER QUALITY for scientific analysis!")


if __name__ == "__main__":
    view_planet_image()

