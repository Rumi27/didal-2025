#!/usr/bin/env python3
"""
Professional Triple-Panel Figure 1:
- Panel (a): Regional context (Tajikistan with red circle marking glacier)
- Panel (b): High-resolution DEM/hillshade
- Panel (c): PlanetScope satellite image (3m resolution)
"""

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import rasterio
from rasterio.plot import show
from rasterio.warp import transform as rasterio_transform
from rasterio.windows import from_bounds
import geopandas as gpd
from pyproj import Transformer
import numpy as np
import os

# --- Parameters ---
GLACIER_LAT, GLACIER_LON = 38.97, 70.75
DEM_PATH = 'satellite_data/dem/processed/hillshade.tif'
OUTPUT_FILE = 'processed_data/analysis_results/figure1_multipanel.png'

def find_planet_image():
    """Find PlanetScope image if exact path doesn't exist."""
    # Try exact path first
    exact_path = 'satellite_data/planet/planetscope_sept_2025.tif'
    if os.path.exists(exact_path):
        return exact_path
    
    # Search for PlanetScope images
    search_paths = [
        'satellite_data/planet',
        'planet_images',
        'planet_images/from_website',
        'planet_images/newa_planet',
        'satellite_data'
    ]
    
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
                            return full_path
    return None

def crop_and_normalize_planet_image(image_path, glacier_lon, glacier_lat, crop_size_meters=3000):
    """Crop PlanetScope image to area around glacier and normalize for display."""
    try:
        with rasterio.open(image_path) as src:
            # Transform glacier location to image CRS
            glacier_x, glacier_y = rasterio_transform(
                "EPSG:4326", src.crs,
                [glacier_lon], [glacier_lat]
            )
            glacier_x, glacier_y = glacier_x[0], glacier_y[0]
            
            # Define crop window in meters (if projected) or degrees
            if src.crs.is_projected:
                crop_size = crop_size_meters
            else:
                crop_size = crop_size_meters / 111000  # Convert meters to degrees
            
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
            
            # Read and normalize RGB bands
            if src.count >= 3:
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
                
                # Get bounds for extent
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
                return data, bounds, src.crs
            else:
                return None
    except Exception as e:
        print(f"   ⚠️  Warning: Could not crop PlanetScope image: {e}")
        return None

def create_triple_panel():
    """Create professional triple-panel figure."""
    print("=" * 70)
    print("CREATING PROFESSIONAL TRIPLE-PANEL FIGURE 1")
    print("=" * 70)
    
    fig = plt.figure(figsize=(12, 16))
    gs = gridspec.GridSpec(2, 2, height_ratios=[1, 1.5], hspace=0.3, wspace=0.2)

    # --- PANEL A: Regional Context (Top, spans both columns) ---
    print("\n✅ Creating panel (a): Regional context...")
    ax0 = fig.add_subplot(gs[0, :])
    
    # Tajikistan outline
    tj_lon = [67.5, 71.5, 73.5, 73.0, 71.0, 67.5]
    tj_lat = [36.5, 36.0, 37.5, 40.5, 40.5, 37.0]
    ax0.fill(tj_lon, tj_lat, color='#f0f0f0', edgecolor='black', lw=1.5, zorder=1)
    ax0.plot(tj_lon, tj_lat, 'k-', linewidth=1.5, zorder=2)
    
    # Red Circle for Location
    ax0.scatter(GLACIER_LON, GLACIER_LAT, s=300, facecolors='none', 
               edgecolors='red', lw=3, zorder=5, label='Didal Glacier')
    ax0.text(GLACIER_LON+0.2, GLACIER_LAT, 'Didal Glacier', 
            fontweight='bold', fontsize=12, color='red', zorder=6)
    
    ax0.set_xlim(67, 74)
    ax0.set_ylim(36, 41)
    ax0.set_title("(a) Regional Context: Pamir Mountains, Tajikistan", 
                  loc='left', fontweight='bold', fontsize=13, pad=10)
    ax0.set_xlabel("Longitude (°E)", fontsize=11, fontweight='bold')
    ax0.set_ylabel("Latitude (°N)", fontsize=11, fontweight='bold')
    ax0.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
    ax0.set_aspect('equal', adjustable='box')
    print("   ✅ Regional context panel created")

    # --- PANEL B: High-Res DEM/Hillshade (Bottom Left) ---
    print("\n✅ Creating panel (b): DEM/hillshade...")
    ax1 = fig.add_subplot(gs[1, 0])
    
    if os.path.exists(DEM_PATH):
        with rasterio.open(DEM_PATH) as src:
            # Transform site to DEM units
            transformer = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
            sx, sy = transformer.transform(GLACIER_LON, GLACIER_LAT)
            
            show(src, ax=ax1, cmap='gray', alpha=1.0, zorder=1)
            
            # Sharp Zoom (1.5km buffer for high quality)
            buf = 1500 if src.crs.is_projected else 0.015
            ax1.set_xlim(sx - buf, sx + buf)
            ax1.set_ylim(sy - buf, sy + buf)
            
            # Mark glacier location
            ax1.plot(sx, sy, 'r*', markersize=25, markeredgecolor='yellow', 
                    markeredgewidth=2, zorder=10)
            
            ax1.set_title("(b) Topographic Setting (DEM Hillshade)", 
                         fontweight='bold', fontsize=12, pad=10)
            ax1.set_xlabel("Longitude (°E)", fontsize=10)
            ax1.set_ylabel("Latitude (°N)", fontsize=10)
            ax1.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
            print("   ✅ DEM/hillshade panel created")
    else:
        ax1.text(0.5, 0.5, "DEM Data\nNot Found", ha='center', va='center', fontsize=14)
        ax1.set_title("(b) Topographic Setting (DEM Hillshade)", fontweight='bold', fontsize=12)
        print("   ⚠️  DEM file not found")

    # --- PANEL C: PlanetScope Satellite Image (Bottom Right) ---
    print("\n✅ Creating panel (c): PlanetScope satellite image...")
    ax2 = fig.add_subplot(gs[1, 1])
    
    planet_path = find_planet_image()
    if planet_path and os.path.exists(planet_path):
        print(f"   Using PlanetScope image: {os.path.basename(planet_path)}")
        try:
            result = crop_and_normalize_planet_image(planet_path, GLACIER_LON, GLACIER_LAT, crop_size_meters=3000)
            if result:
                data, bounds, crs = result
                
                # Display normalized RGB image
                ax2.imshow(data, extent=[bounds['left'], bounds['right'], 
                                        bounds['bottom'], bounds['top']],
                          origin='upper', zorder=1, interpolation='bilinear')
                
                # Set extent to match DEM panel
                with rasterio.open(DEM_PATH) as dem_src:
                    transformer = Transformer.from_crs("EPSG:4326", dem_src.crs, always_xy=True)
                    sx, sy = transformer.transform(GLACIER_LON, GLACIER_LAT)
                    buf = 1500 if dem_src.crs.is_projected else 0.015
                    
                    # Transform DEM extent to PlanetScope CRS for matching view
                    if crs != dem_src.crs:
                        # Get DEM extent in PlanetScope CRS
                        dem_bounds = dem_src.bounds
                        dem_corners_lon = [dem_bounds.left, dem_bounds.right, dem_bounds.right, dem_bounds.left]
                        dem_corners_lat = [dem_bounds.bottom, dem_bounds.bottom, dem_bounds.top, dem_bounds.top]
                        planet_corners_x, planet_corners_y = rasterio_transform(
                            dem_src.crs, crs, dem_corners_lon, dem_corners_lat
                        )
                        planet_sx, planet_sy = rasterio_transform(
                            "EPSG:4326", crs, [GLACIER_LON], [GLACIER_LAT]
                        )
                        planet_buf = 1500 if crs.is_projected else 0.015
                        ax2.set_xlim(planet_sx[0] - planet_buf, planet_sx[0] + planet_buf)
                        ax2.set_ylim(planet_sy[0] - planet_buf, planet_sy[0] + planet_buf)
                    else:
                        ax2.set_xlim(sx - buf, sx + buf)
                        ax2.set_ylim(sy - buf, sy + buf)
                
                # Mark glacier location
                glacier_x, glacier_y = rasterio_transform(
                    "EPSG:4326", crs, [GLACIER_LON], [GLACIER_LAT]
                )
                ax2.plot(glacier_x[0], glacier_y[0], 'r*', markersize=25, 
                        markeredgecolor='yellow', markeredgewidth=2, zorder=10)
                
                ax2.set_title("(c) Satellite Surface View (3m PlanetScope)", 
                             fontweight='bold', fontsize=12, pad=10)
                ax2.set_xlabel("Longitude (°E)", fontsize=10)
                ax2.set_ylabel("Latitude (°N)", fontsize=10)
                ax2.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
                print("   ✅ PlanetScope image displayed (normalized)")
            else:
                ax2.text(0.5, 0.5, "Could not\nprocess image", ha='center', va='center', fontsize=14)
                ax2.set_title("(c) Satellite Surface View (3m PlanetScope)", fontweight='bold', fontsize=12)
        except Exception as e:
            print(f"   ⚠️  Error processing PlanetScope image: {e}")
            ax2.text(0.5, 0.5, "Satellite Image\nError", ha='center', va='center', fontsize=14)
            ax2.set_title("(c) Satellite Surface View (3m PlanetScope)", fontweight='bold', fontsize=12)
    else:
        ax2.text(0.5, 0.5, "Satellite Image\nNot Found", ha='center', va='center', fontsize=14)
        ax2.set_title("(c) Satellite Surface View (3m PlanetScope)", fontweight='bold', fontsize=12)
        print("   ⚠️  PlanetScope image not found")

    # Cleanup and Save
    print(f"\n✅ Saving figure to: {OUTPUT_FILE}")
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches='tight', facecolor='white')
    
    print("\n" + "=" * 70)
    print("✅ PROFESSIONAL TRIPLE-PANEL FIGURE 1 CREATED SUCCESSFULLY!")
    print("=" * 70)
    print(f"\nOutput file: {OUTPUT_FILE}")
    print("\nLayout:")
    print("  - Panel (a): Regional context (Tajikistan with red circle)")
    print("  - Panel (b): DEM/hillshade (topographic setting)")
    print("  - Panel (c): PlanetScope satellite image (3m resolution)")

if __name__ == "__main__":
    create_triple_panel()

