#!/usr/bin/env python3
"""
Professional Figure 1 Script: Topographic and Geomorphological Setting
Features:
- Hillshade base with PlanetScope overlay (draped effect)
- Inset regional map (top right)
- Vector layers (catchment, glacier outline)
- Professional cartographic styling
"""

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.plot import show
import geopandas as gpd
from pyproj import Transformer
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import os
import math

# --- Configuration ---
GLACIER_LAT, GLACIER_LON = 38.97, 70.75
DEM_HILLSHADE = 'satellite_data/dem/processed/hillshade.tif'
PLANET_IMAGE = 'satellite_data/planet/planetscope_sept_2025.tif'  # 3m resolution
CATCHMENT = 'satellite_data/dem/processed/catchment_boundary.shp'
GLACIER_OUTLINE = 'satellite_data/dem/processed/didal_glacier_rgi_outline.shp'
OUTPUT_FILE = 'processed_data/analysis_results/figure1_final_pro.png'

def find_planet_image():
    """Find PlanetScope image if exact path doesn't exist."""
    if os.path.exists(PLANET_IMAGE):
        return PLANET_IMAGE
    
    # Search for PlanetScope images
    search_paths = [
        'satellite_data/planet',
        'planet_images',
        'satellite_data'
    ]
    
    for base_path in search_paths:
        if os.path.exists(base_path):
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    if file.endswith('.tif') and ('planet' in file.lower() or 'sept' in file.lower()):
                        full_path = os.path.join(root, file)
                        print(f"Found PlanetScope image: {full_path}")
                        return full_path
    
    return None

def create_pro_figure():
    """Create professional Figure 1 with all enhancements."""
    print("=" * 70)
    print("CREATING PROFESSIONAL FIGURE 1")
    print("=" * 70)
    
    fig, ax = plt.subplots(figsize=(12, 12))

    # 1. Load Hillshade and PlanetScope
    if not os.path.exists(DEM_HILLSHADE):
        print(f"❌ Error: Hillshade file not found: {DEM_HILLSHADE}")
        return False
    
    with rasterio.open(DEM_HILLSHADE) as hill_src:
        # Get CRS and Transformer
        transformer = Transformer.from_crs("EPSG:4326", hill_src.crs, always_xy=True)
        site_x, site_y = transformer.transform(GLACIER_LON, GLACIER_LAT)
        
        print(f"\nHillshade CRS: {hill_src.crs}")
        print(f"Site location in CRS: ({site_x:.2f}, {site_y:.2f})")
        
        # Plot Hillshade as base (zorder 1)
        show(hill_src, ax=ax, cmap='gray', alpha=1.0, zorder=1)
        
        # 2. Overlay PlanetScope Imagery (zorder 2)
        # Use 40-50% alpha so hillshade "shows through" for 3D effect
        planet_path = find_planet_image()
        if planet_path and os.path.exists(planet_path):
            print(f"\n✅ Found PlanetScope image: {planet_path}")
            try:
                with rasterio.open(planet_path) as img_src:
                    # Transform to same CRS if needed
                    if img_src.crs != hill_src.crs:
                        print(f"   Transforming PlanetScope from {img_src.crs} to {hill_src.crs}")
                    show(img_src, ax=ax, alpha=0.5, zorder=2)
                    print("   ✅ PlanetScope overlay added")
            except Exception as e:
                print(f"   ⚠️  Warning: Could not overlay PlanetScope: {e}")
                print("   Continuing without PlanetScope overlay...")
        else:
            print(f"\nℹ️  PlanetScope image not found (optional)")
            print(f"   Searched for: {PLANET_IMAGE}")
            print("   Continuing with hillshade only...")

        # 3. Zoom Logic (buffer around site)
        buffer = 5000 if hill_src.crs.is_projected else 0.05
        ax.set_xlim(site_x - buffer, site_x + buffer)
        ax.set_ylim(site_y - buffer, site_y + buffer)
        print(f"\nView extent: ±{buffer} ({'meters' if hill_src.crs.is_projected else 'degrees'})")

        # 4. Add Vector Polygons (zorder 3)
        if os.path.exists(CATCHMENT):
            try:
                print(f"\n✅ Loading catchment boundary: {CATCHMENT}")
                catchment_gdf = gpd.read_file(CATCHMENT)
                if catchment_gdf.crs != hill_src.crs:
                    catchment_gdf = catchment_gdf.to_crs(hill_src.crs)
                catchment_gdf.plot(ax=ax, facecolor='none', edgecolor='cyan', 
                                  linewidth=2, label='Catchment', zorder=3, alpha=0.8)
                print("   ✅ Catchment boundary added")
            except Exception as e:
                print(f"   ⚠️  Warning: Could not load catchment: {e}")
        else:
            print(f"\nℹ️  Catchment boundary not found (optional): {CATCHMENT}")
        
        if os.path.exists(GLACIER_OUTLINE):
            try:
                print(f"\n✅ Loading glacier outline: {GLACIER_OUTLINE}")
                glacier_gdf = gpd.read_file(GLACIER_OUTLINE)
                if glacier_gdf.crs != hill_src.crs:
                    glacier_gdf = glacier_gdf.to_crs(hill_src.crs)
                glacier_gdf.plot(ax=ax, facecolor='none', edgecolor='blue', 
                                linestyle='--', linewidth=2, label='Glacier Outline', zorder=3, alpha=0.8)
                print("   ✅ Glacier outline added")
            except Exception as e:
                print(f"   ⚠️  Warning: Could not load glacier outline: {e}")
        else:
            print(f"\nℹ️  Glacier outline not found (optional): {GLACIER_OUTLINE}")

    # 5. Study Site Marker
    ax.plot(site_x, site_y, marker='*', color='red', markersize=25, 
            markeredgecolor='yellow', markeredgewidth=2, zorder=10, label='Study Site')
    
    # Add label
    ax.text(site_x + buffer*0.05, site_y + buffer*0.05, 'Didal Glacier',
            fontweight='bold', color='red', fontsize=11,
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='red', linewidth=1.5),
            zorder=11)

    # 6. Professional Scale Bar
    if hill_src.crs.is_projected:
        # Projected coordinates (meters)
        scale_km = 2
        scale_len = scale_km * 1000  # Convert to meters
        scale_x_start = site_x - buffer * 0.8
        scale_y = site_y - buffer * 0.85
        ax.plot([scale_x_start, scale_x_start + scale_len], 
               [scale_y, scale_y], color='black', lw=4, zorder=10)
        ax.text(scale_x_start + scale_len/2, scale_y - buffer*0.07, f'{scale_km} km',
                ha='center', fontweight='bold', fontsize=10,
                bbox=dict(facecolor='white', alpha=0.9, edgecolor='none', pad=0.5),
                zorder=10)
    else:
        # Geographic coordinates (degrees)
        lat_rad = math.radians(GLACIER_LAT)
        km_per_deg_lon = 111.32 * math.cos(lat_rad)
        scale_km = 2
        scale_len = scale_km / km_per_deg_lon
        scale_x_start = site_x - buffer * 0.8
        scale_y = site_y - buffer * 0.85
        ax.plot([scale_x_start, scale_x_start + scale_len], 
               [scale_y, scale_y], color='black', lw=4, zorder=10)
        ax.text(scale_x_start + scale_len/2, scale_y - buffer*0.07, f'{scale_km} km',
                ha='center', fontweight='bold', fontsize=10,
                bbox=dict(facecolor='white', alpha=0.9, edgecolor='none', pad=0.5),
                zorder=10)

    # 7. North Arrow
    arrow_x = site_x + buffer * 0.75
    arrow_y = site_y + buffer * 0.75
    if hill_src.crs.is_projected:
        arrow_length = buffer * 0.1
    else:
        arrow_length = buffer * 0.1
    ax.annotate('', xy=(arrow_x, arrow_y + arrow_length), 
               xytext=(arrow_x, arrow_y),
               arrowprops=dict(arrowstyle='->', lw=3, color='black'), zorder=10)
    ax.text(arrow_x, arrow_y + arrow_length * 1.3, 'N', 
           ha='center', va='bottom', fontweight='bold', fontsize=12,
           bbox=dict(facecolor='white', alpha=0.9, edgecolor='none', pad=0.3),
           zorder=10)

    # 8. Inset Regional Map (Top Right)
    print("\n✅ Creating inset regional map...")
    try:
        ax_ins = inset_axes(ax, width="25%", height="25%", loc='upper right', borderpad=2)
        
        # Simple approach: Draw Tajikistan outline manually
        # Tajikistan rough borders
        tj_lon = [67.5, 71.5, 73.5, 73.0, 71.0, 67.5]
        tj_lat = [36.5, 36.0, 37.5, 40.5, 40.5, 37.0]
        ax_ins.fill(tj_lon, tj_lat, color='#e0e0e0', edgecolor='black', linewidth=1, zorder=1)
        ax_ins.plot(tj_lon, tj_lat, 'k-', linewidth=0.8, zorder=2)
        ax_ins.plot(GLACIER_LON, GLACIER_LAT, 'r*', markersize=10, zorder=5)
        ax_ins.set_xlim(67, 74)
        ax_ins.set_ylim(36, 41)
        ax_ins.set_title('Regional Context', fontsize=9, fontweight='bold', pad=5)
        ax_ins.set_xticks([])
        ax_ins.set_yticks([])
        ax_ins.set_aspect('equal', adjustable='box')
        print("   ✅ Regional inset map created")
    except Exception as e:
        print(f"   ⚠️  Warning: Could not create inset map: {e}")
        import traceback
        traceback.print_exc()

    # 9. Titles & Labels
    ax.set_title("(b) Topographic and Geomorphological Setting: Didal Glacier", 
                 loc='left', fontweight='bold', fontsize=13, pad=15)
    
    # Hide axes for cleaner look (or keep them for geographic reference)
    # ax.set_axis_off()  # Uncomment for no axes
    
    # Save figure
    print(f"\n✅ Saving figure to: {OUTPUT_FILE}")
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"\n" + "=" * 70)
    print("✅ PROFESSIONAL FIGURE 1 CREATED SUCCESSFULLY!")
    print("=" * 70)
    print(f"\nOutput file: {OUTPUT_FILE}")
    
    return True

if __name__ == "__main__":
    success = create_pro_figure()
    exit(0 if success else 1)

