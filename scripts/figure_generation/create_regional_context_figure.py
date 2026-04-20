#!/usr/bin/env python3
"""
Create multi-panel figure similar to reference image:
- Top/Left: Main detailed view of Didal Glacier area (DEM/hillshade + RGI outline + red point)
- Bottom Right: Tajikistan inset map with red point
- Bottom: Two satellite images with red outlines (like HIN and SIM)
"""

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Rectangle, Circle
from matplotlib.patches import FancyBboxPatch
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import numpy as np
import rasterio
from rasterio.plot import show
from rasterio.warp import transform as rasterio_transform
from rasterio.windows import from_bounds
from pyproj import Transformer
from PIL import Image
import os

# --- Configuration ---
GLACIER_LAT, GLACIER_LON = 38.97, 70.75
DEM_HILLSHADE = 'satellite_data/dem/processed/hillshade.tif'
GLACIER_OUTLINE = 'satellite_data/dem/processed/didal_glacier_rgi_outline.shp'
PLANET_IMAGE_1 = 'planet_images/visualizations/2025-09-17_20250917_064328_46_24b7_rgb.png'  # Before
PLANET_IMAGE_2 = 'planet_images/visualizations/2025-10-25_20251025_062608_36_251d_rgb.png'  # After
OUTPUT_FILE = 'processed_data/analysis_results/figure_regional_context.png'

def load_dem_hillshade(dem_path, glacier_lon, glacier_lat, buffer_m=3000):
    """Load DEM/hillshade and crop to area around glacier."""
    try:
        with rasterio.open(dem_path) as src:
            # Transform glacier location to DEM CRS
            transformer = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
            glacier_x, glacier_y = transformer.transform(glacier_lon, glacier_lat)
            
            # Define crop bounds
            crop_left = glacier_x - buffer_m
            crop_right = glacier_x + buffer_m
            crop_bottom = glacier_y - buffer_m
            crop_top = glacier_y + buffer_m
            
            # Clip to image bounds
            crop_left = max(crop_left, src.bounds.left)
            crop_right = min(crop_right, src.bounds.right)
            crop_bottom = max(crop_bottom, src.bounds.bottom)
            crop_top = min(crop_top, src.bounds.top)
            
            # Read data
            crop_window = from_bounds(crop_left, crop_bottom, crop_right, crop_top, src.transform)
            dem_data = src.read(1, window=crop_window)
            
            # Get transform for cropped area
            transform = src.window_transform(crop_window)
            bounds = (crop_left, crop_bottom, crop_right, crop_top)
            
            return dem_data, transform, bounds, src.crs
            
    except Exception as e:
        print(f"Error loading DEM: {e}")
        return None, None, None, None

def create_regional_context_figure():
    """Create multi-panel figure with regional context."""
    
    fig = plt.figure(figsize=(16, 12))
    gs = gridspec.GridSpec(3, 3, figure=fig, 
                          height_ratios=[2, 1, 1], 
                          width_ratios=[2, 1, 1],
                          hspace=0.3, wspace=0.3)
    
    # --- TOP/LEFT PANEL: Main detailed view ---
    ax_main = fig.add_subplot(gs[0, :2])
    
    # Load DEM/hillshade
    if os.path.exists(DEM_HILLSHADE):
        dem_data, transform, bounds, crs = load_dem_hillshade(DEM_HILLSHADE, GLACIER_LON, GLACIER_LAT)
        if dem_data is not None:
            # Display hillshade
            im = ax_main.imshow(dem_data, cmap='gray', 
                               extent=[bounds[0], bounds[2], bounds[1], bounds[3]],
                               origin='upper', interpolation='bilinear')
            
            # Transform glacier location for plotting
            if crs:
                transformer = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
                site_x, site_y = transformer.transform(GLACIER_LON, GLACIER_LAT)
                
                # Add red point for study site
                ax_main.plot(site_x, site_y, 'ro', markersize=12, 
                           markeredgecolor='red', markeredgewidth=2,
                           markerfacecolor='red', label='Study Site')
                ax_main.plot(site_x, site_y, 'r+', markersize=15, 
                           markeredgewidth=2)
            
            # Load and plot RGI outline if available
            if os.path.exists(GLACIER_OUTLINE):
                try:
                    import geopandas as gpd
                    glacier_gdf = gpd.read_file(GLACIER_OUTLINE)
                    if glacier_gdf.crs != crs:
                        glacier_gdf = glacier_gdf.to_crs(crs)
                    glacier_gdf.plot(ax=ax_main, facecolor='none', 
                                   edgecolor='red', linewidth=2, 
                                   linestyle='--', label='Didal Glacier Outline')
                except Exception as e:
                    print(f"Warning: Could not load RGI outline: {e}")
            
            ax_main.set_xlabel("Easting (m)", fontsize=11)
            ax_main.set_ylabel("Northing (m)", fontsize=11)
            ax_main.set_title("(a) Didal Glacier - Study Site", 
                            fontsize=14, fontweight='bold', loc='left')
            ax_main.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
            ax_main.legend(loc='upper left', fontsize=9)
        else:
            ax_main.text(0.5, 0.5, "DEM/Hillshade\nNot Available", 
                        ha='center', va='center', fontsize=14)
            ax_main.set_title("(a) Didal Glacier - Study Site", 
                            fontsize=14, fontweight='bold', loc='left')
    else:
        ax_main.text(0.5, 0.5, "DEM/Hillshade\nNot Found", 
                    ha='center', va='center', fontsize=14)
        ax_main.set_title("(a) Didal Glacier - Study Site", 
                        fontsize=14, fontweight='bold', loc='left')
    
    # Add north arrow and scale bar (simplified)
    # North arrow
    ax_main.annotate('', xy=(0.95, 0.95), xycoords='axes fraction',
                    xytext=(0.95, 0.85), textcoords='axes fraction',
                    arrowprops=dict(arrowstyle='->', lw=2, color='black'))
    ax_main.text(0.95, 0.96, 'N', ha='center', va='bottom', 
                fontsize=12, fontweight='bold', transform=ax_main.transAxes)
    
    # --- BOTTOM RIGHT: Tajikistan inset map ---
    ax_inset = fig.add_subplot(gs[0, 2])
    
    # Simple approach: Use approximate Tajikistan boundaries
    # Tajikistan approximate boundaries: 67.4-75.1°E, 36.7-41.0°N
    tajikistan_box = {
        'lon': [67.4, 75.1, 75.1, 67.4, 67.4],
        'lat': [36.7, 36.7, 41.0, 41.0, 36.7]
    }
    
    # Draw approximate Tajikistan outline
    ax_inset.plot(tajikistan_box['lon'], tajikistan_box['lat'], 
                  color='black', linewidth=1.5, zorder=1)
    ax_inset.fill(tajikistan_box['lon'], tajikistan_box['lat'], 
                  color='#e0e0e0', alpha=0.5, zorder=0)
    
    # Add red point for Didal Glacier
    ax_inset.plot(GLACIER_LON, GLACIER_LAT, 'ro', markersize=12, 
                 markeredgecolor='red', markeredgewidth=2,
                 markerfacecolor='red', zorder=5, label='Didal Glacier')
    ax_inset.plot(GLACIER_LON, GLACIER_LAT, 'r+', markersize=15, 
                 markeredgewidth=2, zorder=5)
    
    # Set extent to show Tajikistan and surrounding area
    ax_inset.set_xlim(66, 76)
    ax_inset.set_ylim(36, 42)
    ax_inset.set_aspect('equal', adjustable='box')
    ax_inset.set_title('Regional Context', fontsize=11, fontweight='bold')
    ax_inset.set_xlabel('Longitude (°E)', fontsize=9)
    ax_inset.set_ylabel('Latitude (°N)', fontsize=9)
    ax_inset.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
    ax_inset.legend(loc='lower right', fontsize=8)
    
    # --- BOTTOM LEFT: Satellite image 1 (Before) ---
    ax_sat1 = fig.add_subplot(gs[1, 0])
    
    if os.path.exists(PLANET_IMAGE_1):
        try:
            img1 = Image.open(PLANET_IMAGE_1)
            ax_sat1.imshow(img1, interpolation='bilinear')
            
            # Add red outline (rectangle around center)
            img_width, img_height = img1.size
            rect = Rectangle((img_width*0.1, img_height*0.1), 
                           img_width*0.8, img_height*0.8,
                           linewidth=3, edgecolor='red', 
                           facecolor='none', linestyle='--')
            ax_sat1.add_patch(rect)
            
            ax_sat1.set_title("(b) September 17, 2025\n(Initial Movement)", 
                            fontsize=12, fontweight='bold', loc='left')
        except Exception as e:
            print(f"Warning: Could not load satellite image 1: {e}")
            ax_sat1.text(0.5, 0.5, "Satellite Image 1\n(Not Available)", 
                        ha='center', va='center', fontsize=12,
                        transform=ax_sat1.transAxes)
            ax_sat1.set_title("(b) September 17, 2025", 
                            fontsize=12, fontweight='bold', loc='left')
    else:
        ax_sat1.text(0.5, 0.5, "Satellite Image 1\n(Not Found)", 
                    ha='center', va='center', fontsize=12,
                    transform=ax_sat1.transAxes)
        ax_sat1.set_title("(b) September 17, 2025", 
                        fontsize=12, fontweight='bold', loc='left')
    
    ax_sat1.axis('off')
    
    # --- BOTTOM MIDDLE: Satellite image 2 (After) ---
    ax_sat2 = fig.add_subplot(gs[1, 1])
    
    if os.path.exists(PLANET_IMAGE_2):
        try:
            img2 = Image.open(PLANET_IMAGE_2)
            ax_sat2.imshow(img2, interpolation='bilinear')
            
            # Add red outline (rectangle around center)
            img_width, img_height = img2.size
            rect = Rectangle((img_width*0.1, img_height*0.1), 
                           img_width*0.8, img_height*0.8,
                           linewidth=3, edgecolor='red', 
                           facecolor='none', linestyle='--')
            ax_sat2.add_patch(rect)
            
            ax_sat2.set_title("(c) October 25, 2025\n(Second Movement)", 
                            fontsize=12, fontweight='bold', loc='left')
        except Exception as e:
            print(f"Warning: Could not load satellite image 2: {e}")
            ax_sat2.text(0.5, 0.5, "Satellite Image 2\n(Not Available)", 
                        ha='center', va='center', fontsize=12,
                        transform=ax_sat2.transAxes)
            ax_sat2.set_title("(c) October 25, 2025", 
                            fontsize=12, fontweight='bold', loc='left')
    else:
        ax_sat2.text(0.5, 0.5, "Satellite Image 2\n(Not Found)", 
                    ha='center', va='center', fontsize=12,
                    transform=ax_sat2.transAxes)
        ax_sat2.set_title("(c) October 25, 2025", 
                        fontsize=12, fontweight='bold', loc='left')
    
    ax_sat2.axis('off')
    
    # --- BOTTOM RIGHT: Add third panel or leave empty for symmetry ---
    ax_extra = fig.add_subplot(gs[1, 2])
    ax_extra.axis('off')
    
    # Save figure
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"✅ Figure saved: {OUTPUT_FILE}")
    return True

if __name__ == "__main__":
    create_regional_context_figure()

