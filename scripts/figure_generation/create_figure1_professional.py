#!/usr/bin/env python3
"""
Professional Figure 1: High-quality satellite imagery with regional context
Layout:
- Main panel: High-quality satellite image (PlanetScope) or DEM hillshade of glacier area
- Inset (top right): Small country map with red circle marking glacier location
- Bottom: Two satellite images showing glacier location
"""

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.plot import show
from rasterio.warp import transform as rasterio_transform
from rasterio.windows import from_bounds
import geopandas as gpd
from pyproj import Transformer
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import os
import math

# --- Configuration ---
GLACIER_LAT, GLACIER_LON = 38.97, 70.75
DEM_HILLSHADE = 'satellite_data/dem/processed/hillshade.tif'
OUTPUT_FILE = 'processed_data/analysis_results/figure1_professional.png'

def find_planet_images():
    """Find available PlanetScope images."""
    search_paths = [
        'satellite_data/planet',
        'planet_images',
        'planet_images/from_website',
        'planet_images/newa_planet',
        'satellite_data'
    ]
    
    found_images = []
    for base_path in search_paths:
        if os.path.exists(base_path):
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    if file.endswith('.tif') and ('planet' in file.lower() or 
                                                  'analytic' in file.lower() or
                                                  file.startswith('2025')):
                        full_path = os.path.join(root, file)
                        # Check if it's a valid image (not a mask)
                        if 'udm' not in file.lower() and 'mask' not in file.lower():
                            found_images.append(full_path)
    
    return sorted(found_images)

def crop_and_normalize_planet_image(image_path, glacier_lon, glacier_lat, crop_size_deg=0.2):
    """Crop PlanetScope image to area around glacier and normalize for display."""
    try:
        with rasterio.open(image_path) as src:
            # Transform glacier location to image CRS
            glacier_x, glacier_y = rasterio_transform(
                "EPSG:4326", src.crs,
                [glacier_lon], [glacier_lat]
            )
            glacier_x, glacier_y = glacier_x[0], glacier_y[0]
            
            # Convert crop size from degrees to meters (if projected) or degrees
            if src.crs.is_projected:
                crop_size = crop_size_deg * 111000  # Approximate: 1 deg ≈ 111 km
            else:
                crop_size = crop_size_deg
            
            # Define crop window
            crop_left = glacier_x - crop_size / 2
            crop_right = glacier_x + crop_size / 2
            crop_bottom = glacier_y - crop_size / 2
            crop_top = glacier_y + crop_size / 2
            
            # Clip to image bounds
            crop_left = max(crop_left, src.bounds.left)
            crop_right = min(crop_right, src.bounds.right)
            crop_bottom = max(crop_bottom, src.bounds.bottom)
            crop_top = min(crop_top, src.bounds.top)
            
            # Create crop window
            crop_window = from_bounds(crop_left, crop_bottom, crop_right, crop_top, src.transform)
            
            # Read cropped data
            if src.count >= 3:
                # Read RGB bands (PlanetScope: Blue=1, Green=2, Red=3)
                blue = src.read(1, window=crop_window).astype(np.float32)
                green = src.read(2, window=crop_window).astype(np.float32)
                red = src.read(3, window=crop_window).astype(np.float32)
                
                # PlanetScope AnalyticMS_SR uses 0-10000 range, convert to 0-1
                scale_factor = 0.0001
                red_norm = np.clip(red * scale_factor, 0, 1)
                green_norm = np.clip(green * scale_factor, 0, 1)
                blue_norm = np.clip(blue * scale_factor, 0, 1)
                
                # Stack RGB (order: R, G, B for display)
                data = np.dstack([red_norm, green_norm, blue_norm])
                
                # Get transform for cropped area
                transform = src.window_transform(crop_window)
                bounds_tuple = rasterio.transform.array_bounds(
                    crop_window.height, crop_window.width, transform
                )
                bounds = {
                    'left': bounds_tuple[0],
                    'bottom': bounds_tuple[1],
                    'right': bounds_tuple[2],
                    'top': bounds_tuple[3]
                }
                return data, transform, bounds, src.crs
            else:
                # Single band (grayscale)
                data = src.read(1, window=crop_window).astype(np.float32)
                scale_factor = 0.0001
                data = np.clip(data * scale_factor, 0, 1)
                
                transform = src.window_transform(crop_window)
                bounds_tuple = rasterio.transform.array_bounds(
                    crop_window.height, crop_window.width, transform
                )
                bounds = {
                    'left': bounds_tuple[0],
                    'bottom': bounds_tuple[1],
                    'right': bounds_tuple[2],
                    'top': bounds_tuple[3]
                }
                return data, transform, bounds, src.crs
    except Exception as e:
        print(f"   ⚠️  Warning: Could not crop {image_path}: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_professional_figure():
    """Create professional Figure 1 with satellite imagery."""
    print("=" * 70)
    print("CREATING PROFESSIONAL FIGURE 1 WITH SATELLITE IMAGERY")
    print("=" * 70)
    
    # Find PlanetScope images
    print("\nSearching for PlanetScope images...")
    planet_images = find_planet_images()
    # Remove duplicates (same basename)
    unique_images = []
    seen_basenames = set()
    for img in planet_images:
        basename = os.path.basename(img)
        if basename not in seen_basenames:
            unique_images.append(img)
            seen_basenames.add(basename)
    planet_images = unique_images
    
    print(f"Found {len(planet_images)} unique PlanetScope images")
    
    if len(planet_images) >= 2:
        PLANET_IMAGE_1 = planet_images[0]
        PLANET_IMAGE_2 = planet_images[1]
        print(f"  Image 1: {os.path.basename(PLANET_IMAGE_1)}")
        print(f"  Image 2: {os.path.basename(PLANET_IMAGE_2)}")
    elif len(planet_images) == 1:
        PLANET_IMAGE_1 = planet_images[0]
        PLANET_IMAGE_2 = None
        print(f"  Image 1: {os.path.basename(PLANET_IMAGE_1)}")
        print(f"  Image 2: Not found (will use DEM)")
    else:
        PLANET_IMAGE_1 = None
        PLANET_IMAGE_2 = None
        print("  No PlanetScope images found (will use DEM hillshade)")
    
    # Create figure with subplots
    fig = plt.figure(figsize=(14, 12))
    gs = fig.add_gridspec(3, 1, height_ratios=[2, 1, 1], hspace=0.3, wspace=0.1)
    
    # === MAIN PANEL (Top): High-quality satellite image or DEM ===
    ax_main = fig.add_subplot(gs[0, 0])
    
    if PLANET_IMAGE_1 and os.path.exists(PLANET_IMAGE_1):
        print("\n✅ Loading main satellite image (PlanetScope)...")
        try:
            result = crop_and_normalize_planet_image(
                PLANET_IMAGE_1, GLACIER_LON, GLACIER_LAT, crop_size_deg=0.2
            )
            if result:
                cropped_data, transform, bounds, crs = result
                # Display RGB image (already normalized to 0-1)
                if len(cropped_data.shape) == 3:
                    ax_main.imshow(cropped_data, extent=[bounds['left'], bounds['right'], 
                                                      bounds['bottom'], bounds['top']],
                                  origin='upper', zorder=1, interpolation='bilinear')
                    ax_main.set_xlim(bounds['left'], bounds['right'])
                    ax_main.set_ylim(bounds['bottom'], bounds['top'])
                    print(f"   ✅ Satellite image displayed (normalized to 0-1)")
                else:
                    ax_main.imshow(cropped_data, extent=[bounds['left'], bounds['right'],
                                                        bounds['bottom'], bounds['top']],
                                  cmap='gray', origin='upper', zorder=1, interpolation='bilinear')
                    ax_main.set_xlim(bounds['left'], bounds['right'])
                    ax_main.set_ylim(bounds['bottom'], bounds['top'])
                
                # Mark glacier location
                glacier_x, glacier_y = rasterio_transform(
                    "EPSG:4326", crs, [GLACIER_LON], [GLACIER_LAT]
                )
                ax_main.plot(glacier_x[0], glacier_y[0], 'r*', markersize=30,
                           markeredgecolor='yellow', markeredgewidth=3, zorder=10)
            else:
                raise Exception("Crop failed")
        except Exception as e:
            print(f"   ⚠️  Could not load satellite image: {e}")
            print("   Using DEM hillshade instead...")
            PLANET_IMAGE_1 = None
    
    if not PLANET_IMAGE_1 or not os.path.exists(PLANET_IMAGE_1):
        # Fallback: Use DEM hillshade
        print("\nUsing DEM hillshade for main panel...")
        if os.path.exists(DEM_HILLSHADE):
            with rasterio.open(DEM_HILLSHADE) as src:
                show(src, ax=ax_main, cmap='gray', alpha=1.0, zorder=1)
                transformer = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
                site_x, site_y = transformer.transform(GLACIER_LON, GLACIER_LAT)
                buffer = 5000 if src.crs.is_projected else 0.05
                ax_main.set_xlim(site_x - buffer, site_x + buffer)
                ax_main.set_ylim(site_y - buffer, site_y + buffer)
                ax_main.plot(site_x, site_y, 'r*', markersize=30,
                           markeredgecolor='yellow', markeredgewidth=3, zorder=10)
    
    ax_main.set_title("(a) Didal Glacier Location", fontsize=14, fontweight='bold', pad=15)
    ax_main.set_xlabel("Longitude (°E)", fontsize=11, fontweight='bold')
    ax_main.set_ylabel("Latitude (°N)", fontsize=11, fontweight='bold')
    ax_main.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
    
    # === INSET REGIONAL MAP (Top Right) ===
    print("\n✅ Creating inset regional map...")
    ax_inset = inset_axes(ax_main, width="20%", height="20%", loc='upper right', borderpad=2)
    
    # Draw Tajikistan outline
    tj_lon = [67.5, 71.5, 73.5, 73.0, 71.0, 67.5]
    tj_lat = [36.5, 36.0, 37.5, 40.5, 40.5, 37.0]
    ax_inset.fill(tj_lon, tj_lat, color='lightgray', edgecolor='black', linewidth=1, zorder=1)
    ax_inset.plot(tj_lon, tj_lat, 'k-', linewidth=0.8, zorder=2)
    
    # Mark glacier location with red circle
    ax_inset.plot(GLACIER_LON, GLACIER_LAT, 'ro', markersize=10, 
                 markeredgecolor='red', markeredgewidth=2, fillstyle='none',
                 zorder=5, label='Study Site')
    ax_inset.set_xlim(67, 74)
    ax_inset.set_ylim(36, 41)
    ax_inset.set_title('Regional Context', fontsize=9, fontweight='bold', pad=5)
    ax_inset.set_xticks([])
    ax_inset.set_yticks([])
    ax_inset.set_aspect('equal', adjustable='box')
    print("   ✅ Regional inset map created")
    
    # === BOTTOM PANELS: Two satellite images ===
    # Panel 1 (Left bottom)
    ax_bottom1 = fig.add_subplot(gs[1, 0])
    if PLANET_IMAGE_1 and os.path.exists(PLANET_IMAGE_1):
        print(f"\n✅ Loading bottom panel 1: {os.path.basename(PLANET_IMAGE_1)}")
        try:
            result = crop_and_normalize_planet_image(
                PLANET_IMAGE_1, GLACIER_LON, GLACIER_LAT, crop_size_deg=0.15
            )
            if result:
                cropped_data, transform, bounds, crs = result
                if len(cropped_data.shape) == 3:
                    ax_bottom1.imshow(cropped_data, extent=[bounds['left'], bounds['right'],
                                                     bounds['bottom'], bounds['top']],
                                 origin='upper', zorder=1, interpolation='bilinear')
                    ax_bottom1.set_xlim(bounds['left'], bounds['right'])
                    ax_bottom1.set_ylim(bounds['bottom'], bounds['top'])
                    
                    # Mark glacier
                    glacier_x, glacier_y = rasterio_transform(
                        "EPSG:4326", crs, [GLACIER_LON], [GLACIER_LAT]
                    )
                    ax_bottom1.plot(glacier_x[0], glacier_y[0], 'r*', markersize=20,
                                  markeredgecolor='yellow', markeredgewidth=2, zorder=10)
        except Exception as e:
            print(f"   ⚠️  Could not load: {e}")
            if os.path.exists(DEM_HILLSHADE):
                with rasterio.open(DEM_HILLSHADE) as src:
                    show(src, ax=ax_bottom1, cmap='gray', alpha=1.0, zorder=1)
    else:
        if os.path.exists(DEM_HILLSHADE):
            with rasterio.open(DEM_HILLSHADE) as src:
                show(src, ax=ax_bottom1, cmap='gray', alpha=1.0, zorder=1)
    
    ax_bottom1.set_title("(b) Satellite Image 1", fontsize=12, fontweight='bold', pad=10)
    ax_bottom1.set_xlabel("Longitude (°E)", fontsize=10)
    ax_bottom1.set_ylabel("Latitude (°N)", fontsize=10)
    ax_bottom1.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
    
    # Panel 2 (Right bottom)
    ax_bottom2 = fig.add_subplot(gs[2, 0])
    if PLANET_IMAGE_2 and os.path.exists(PLANET_IMAGE_2):
        print(f"\n✅ Loading bottom panel 2: {os.path.basename(PLANET_IMAGE_2)}")
        try:
            result = crop_and_normalize_planet_image(
                PLANET_IMAGE_2, GLACIER_LON, GLACIER_LAT, crop_size_deg=0.15
            )
            if result:
                cropped_data, transform, bounds, crs = result
                if len(cropped_data.shape) == 3:
                    ax_bottom2.imshow(cropped_data, extent=[bounds['left'], bounds['right'],
                                                     bounds['bottom'], bounds['top']],
                                 origin='upper', zorder=1, interpolation='bilinear')
                    ax_bottom2.set_xlim(bounds['left'], bounds['right'])
                    ax_bottom2.set_ylim(bounds['bottom'], bounds['top'])
                    
                    # Mark glacier
                    glacier_x, glacier_y = rasterio_transform(
                        "EPSG:4326", crs, [GLACIER_LON], [GLACIER_LAT]
                    )
                    ax_bottom2.plot(glacier_x[0], glacier_y[0], 'r*', markersize=20,
                                  markeredgecolor='yellow', markeredgewidth=2, zorder=10)
        except Exception as e:
            print(f"   ⚠️  Could not load: {e}")
            if os.path.exists(DEM_HILLSHADE):
                with rasterio.open(DEM_HILLSHADE) as src:
                    show(src, ax=ax_bottom2, cmap='gray', alpha=1.0, zorder=1)
    else:
        if os.path.exists(DEM_HILLSHADE):
            with rasterio.open(DEM_HILLSHADE) as src:
                show(src, ax=ax_bottom2, cmap='gray', alpha=1.0, zorder=1)
    
    ax_bottom2.set_title("(c) Satellite Image 2", fontsize=12, fontweight='bold', pad=10)
    ax_bottom2.set_xlabel("Longitude (°E)", fontsize=10)
    ax_bottom2.set_ylabel("Latitude (°N)", fontsize=10)
    ax_bottom2.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
    
    # Save figure
    print(f"\n✅ Saving figure to: {OUTPUT_FILE}")
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches='tight', facecolor='white')
    
    print("\n" + "=" * 70)
    print("✅ PROFESSIONAL FIGURE 1 CREATED SUCCESSFULLY!")
    print("=" * 70)
    print(f"\nOutput file: {OUTPUT_FILE}")
    print("\nLayout:")
    print("  - Panel (a): High-quality satellite image or DEM of glacier area")
    print("  - Inset (top right): Regional map with red circle marking glacier")
    print("  - Panel (b): Satellite image 1 (glacier location)")
    print("  - Panel (c): Satellite image 2 (glacier location)")
    
    return True

if __name__ == "__main__":
    success = create_professional_figure()
    exit(0 if success else 1)

