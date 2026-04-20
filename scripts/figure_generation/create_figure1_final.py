#!/usr/bin/env python3
"""
Final Figure 1 Script: Regional Context & Detailed Study Site
Improvements: Automatic coordinate transformation, proper axis limits, 
hillshade-contour overlay, and professional cartographic styling.
"""

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.plot import show
import geopandas as gpd
from pyproj import Transformer
import os
import math

# --- Configuration & Parameters ---
GLACIER_LAT, GLACIER_LON = 38.97, 70.75

# File paths
DEM_FILE = 'satellite_data/SRTM1_Arc_Second_Global/n38_e070_1arc_v3.tif'
DEM_HILLSHADE = 'satellite_data/dem/processed/hillshade.tif'
GLACIER_OUTLINE = 'satellite_data/dem/processed/didal_glacier_rgi_outline.shp'
CATCHMENT_BOUNDARY = 'satellite_data/dem/processed/catchment_boundary.shp'
OUTPUT_FILE = 'processed_data/analysis_results/figure1_final.png'

def get_transformer(src_crs):
    """Creates a transformer to convert Lat/Lon to the DEM's CRS."""
    return Transformer.from_crs("EPSG:4326", src_crs, always_xy=True)

def create_regional_context(ax):
    """Upper panel: Regional context for Tajikistan/Pamir."""
    # Define extent (+/- 2.5 degrees)
    ax.set_xlim(GLACIER_LON - 2.5, GLACIER_LON + 2.5)
    ax.set_ylim(GLACIER_LAT - 2.5, GLACIER_LAT + 2.5)
    
    # Rough Tajikistan borders for context
    tj_lon = [67.5, 71.5, 73.5, 73.0, 71.0, 67.5]
    tj_lat = [36.5, 36.0, 37.5, 40.5, 40.5, 37.0]
    ax.fill(tj_lon, tj_lat, alpha=0.15, color='gray', label='Tajikistan', zorder=1)
    ax.plot(tj_lon, tj_lat, 'k-', linewidth=0.8, alpha=0.5, zorder=2)
    
    # Study site marker
    ax.plot(GLACIER_LON, GLACIER_LAT, 'r*', markersize=15, 
            markeredgecolor='white', markeredgewidth=1, zorder=5)
    
    ax.text(GLACIER_LON + 0.2, GLACIER_LAT + 0.2, 'Didal Glacier', 
            fontweight='bold', color='red', fontsize=10,
            bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))

    ax.set_title("(a) Regional Context & Study Site Location", loc='left', fontweight='bold')
    ax.set_xlabel("Longitude (°E)")
    ax.set_ylabel("Latitude (°N)")
    ax.grid(True, linestyle='--', alpha=0.3)

def create_detailed_view(ax):
    """Lower panel: Topographic detail with Hillshade and Contours."""
    if not os.path.exists(DEM_HILLSHADE):
        print("Error: Hillshade file not found.")
        return

    with rasterio.open(DEM_HILLSHADE) as src:
        # 1. Coordinate Transformation
        transformer = get_transformer(src.crs)
        site_x, site_y = transformer.transform(GLACIER_LON, GLACIER_LAT)
        
        # 2. Plot Hillshade
        show(src, ax=ax, cmap='gray', alpha=0.7, zorder=1)
        
        # 3. Handle Vector Layers (using GeoPandas for CRS safety)
        for path, color, style, label in [
            (CATCHMENT_BOUNDARY, 'cyan', '-', 'Catchment'),
            (GLACIER_OUTLINE, 'blue', '--', 'Glacier Outline')
        ]:
            if os.path.exists(path):
                try:
                    gdf = gpd.read_file(path).to_crs(src.crs)
                    gdf.plot(ax=ax, facecolor='none', edgecolor=color, 
                             linestyle=style, linewidth=1.5, zorder=3, label=label)
                except Exception as e:
                    print(f"Warning: Could not load {path}: {e}")

        # 4. Zoom Logic (buffer around site)
        # Check if CRS is in meters (projected) or degrees
        if src.crs.is_projected:
            buffer = 5000  # 5 km in meters
        else:
            buffer = 0.05  # ~5.5 km in degrees at this latitude
        
        ax.set_xlim(site_x - buffer, site_x + buffer)
        ax.set_ylim(site_y - buffer, site_y + buffer)
        
        # Store CRS info for scale bar
        is_projected = src.crs.is_projected
        crs = src.crs

    # 5. Map Elements (Scale Bar & North Arrow)
    ax.plot(site_x, site_y, 'r*', markersize=20, markeredgecolor='yellow', 
            markeredgewidth=2, zorder=10)
    
    # Scale Bar
    scale_km = 10  # 10 km scale bar
    if is_projected:
        # Projected coordinates (meters)
        scale_length = scale_km * 1000  # Convert to meters
        scale_x_start = site_x - buffer * 0.7
        scale_y = site_y - buffer * 0.7
        ax.plot([scale_x_start, scale_x_start + scale_length], 
               [scale_y, scale_y], 'k-', linewidth=3, zorder=10)
        ax.text(scale_x_start + scale_length / 2, scale_y - buffer * 0.05, 
               f'{scale_km} km', ha='center', fontweight='bold', fontsize=9,
               bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'), zorder=10)
    else:
        # Geographic coordinates (degrees)
        lat_rad = math.radians(GLACIER_LAT)
        km_per_deg_lon = 111.32 * math.cos(lat_rad)  # ~86.6 km at 38.97°N
        scale_length_deg = scale_km / km_per_deg_lon
        scale_x_start = site_x - buffer * 0.7
        scale_y = site_y - buffer * 0.7
        ax.plot([scale_x_start, scale_x_start + scale_length_deg], 
               [scale_y, scale_y], 'k-', linewidth=3, zorder=10)
        ax.text(scale_x_start + scale_length_deg / 2, scale_y - buffer * 0.05, 
               f'{scale_km} km', ha='center', fontweight='bold', fontsize=9,
               bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'), zorder=10)
    
    # North Arrow
    arrow_x = site_x + buffer * 0.7
    arrow_y = site_y + buffer * 0.7
    if is_projected:
        arrow_length = buffer * 0.1  # meters
    else:
        arrow_length = buffer * 0.1  # degrees
    ax.annotate('', xy=(arrow_x, arrow_y + arrow_length), 
               xytext=(arrow_x, arrow_y),
               arrowprops=dict(arrowstyle='->', lw=2, color='black', zorder=10))
    ax.text(arrow_x, arrow_y + arrow_length * 1.2, 'N', 
           ha='center', va='bottom', fontweight='bold', fontsize=11, zorder=10)

    ax.set_title("(b) Detailed Geomorphological Setting", loc='left', fontweight='bold')
    # Keep axes for geographic reference (comment out if you prefer axis_off)
    # ax.set_axis_off()  # Professional look: hide axes for the detailed map

def main():
    fig = plt.figure(figsize=(10, 12))
    
    # Panel A
    ax_reg = fig.add_subplot(2, 1, 1)
    create_regional_context(ax_reg)
    
    # Panel B
    ax_det = fig.add_subplot(2, 1, 2)
    create_detailed_view(ax_det)
    
    plt.tight_layout()
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches='tight')
    print(f"Success! Figure saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
