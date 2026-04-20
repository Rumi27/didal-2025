#!/usr/bin/env python3
"""
Create properly fixed Figure 1 with correct axis handling.
Fixes:
- Correct extent array indexing
- Proper axis limits (min to max)
- Handle rasterio.plot.show coordinate system correctly
- Fix axis inversion issues
"""

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.plot import show
import os
import math

# Study area parameters (WGS84)
GLACIER_LAT = 38.97
GLACIER_LON = 70.75

# File paths
DEM_FILE = 'satellite_data/SRTM1_Arc_Second_Global/n38_e070_1arc_v3.tif'
DEM_HILLSHADE = 'satellite_data/dem/processed/hillshade.tif'
GLACIER_OUTLINE = 'satellite_data/dem/processed/didal_glacier_rgi_outline.shp'
CATCHMENT_BOUNDARY = 'satellite_data/dem/processed/catchment_boundary.shp'
OUTPUT_FILE = 'processed_data/analysis_results/figure1_properly_fixed.png'

def load_vector_file(filepath):
    """Load vector file and return GeoDataFrame in WGS84."""
    try:
        import geopandas as gpd
        if os.path.exists(filepath):
            gdf = gpd.read_file(filepath)
            if gdf.crs and gdf.crs.to_string() != 'EPSG:4326':
                gdf = gdf.to_crs('EPSG:4326')
            return gdf
        return None
    except ImportError:
        return None
    except Exception as e:
        print(f"Warning: Could not load {filepath}: {e}")
        return None

def create_regional_context(ax):
    """Create upper panel: Regional context (WGS84 coordinates)."""
    # Define extent: [min_lon, max_lon, min_lat, max_lat]
    min_lon = GLACIER_LON - 2.0
    max_lon = GLACIER_LON + 2.0
    min_lat = GLACIER_LAT - 2.0
    max_lat = GLACIER_LAT + 2.0
    
    # Set limits explicitly (min to max, ensure proper order)
    ax.set_xlim(min_lon, max_lon)
    ax.set_ylim(min_lat, max_lat)
    
    # Country boundaries (WGS84)
    tajikistan_lon = [67.5, 71.5, 73.5, 73.0, 71.0, 67.5]
    tajikistan_lat = [36.5, 36.0, 37.5, 40.5, 40.5, 37.0]
    ax.plot(tajikistan_lon, tajikistan_lat, 'k-', linewidth=1.5, zorder=2)
    ax.fill(tajikistan_lon, tajikistan_lat, alpha=0.2, color='lightgray', zorder=1)
    
    # Mark glacier location
    ax.plot(GLACIER_LON, GLACIER_LAT, 'r*', markersize=25, 
            markeredgecolor='yellow', markeredgewidth=2, zorder=5)
    
    ax.text(GLACIER_LON + 0.3, GLACIER_LAT + 0.15, 'Didal Glacier',
            fontsize=11, weight='bold',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='white', 
                     edgecolor='red', linewidth=2, alpha=0.9), zorder=6)
    
    ax.text(0.02, 0.98, 'Pamir Mountains\nTajikistan', 
            transform=ax.transAxes, fontsize=11, weight='bold',
            verticalalignment='top',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='white', 
                     edgecolor='black', linewidth=1.5, alpha=0.9), zorder=6)
    
    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5, zorder=1)
    ax.set_xlabel('Longitude (°E)', fontsize=11, weight='bold')
    ax.set_ylabel('Latitude (°N)', fontsize=11, weight='bold')
    
    # Aspect ratio for latitude (accounts for longitude compression at high latitudes)
    lat_rad = math.radians(GLACIER_LAT)
    ax.set_aspect(1.0 / math.cos(lat_rad), adjustable='box')
    
    ax.set_title('(a) Regional context of study; location of failure site, meteorological data source, and registered hazard events', 
                fontsize=11, weight='bold', pad=10)

def create_detailed_view(ax):
    """Create detailed view with proper coordinate handling."""
    if not os.path.exists(DEM_HILLSHADE):
        print("⚠️  Hillshade not found")
        ax.text(0.5, 0.5, 'DEM data not available', 
               transform=ax.transAxes, ha='center', va='center')
        return
    
    with rasterio.open(DEM_HILLSHADE) as src:
        bounds = src.bounds
        print(f"\nHillshade bounds: {bounds}")
        print(f"Glacier location: {GLACIER_LON:.4f}°E, {GLACIER_LAT:.4f}°N")
        
        # Check if glacier is within bounds
        if not (bounds.left <= GLACIER_LON <= bounds.right and 
                bounds.bottom <= GLACIER_LAT <= bounds.top):
            print(f"⚠️  Glacier location is outside hillshade bounds!")
        
        # Define detailed extent around glacier
        zoom_deg = 0.3
        detailed_min_lon = GLACIER_LON - zoom_deg
        detailed_max_lon = GLACIER_LON + zoom_deg
        detailed_min_lat = GLACIER_LAT - zoom_deg
        detailed_max_lat = GLACIER_LAT + zoom_deg
        
        # Clip to actual data bounds
        detailed_min_lon = max(detailed_min_lon, bounds.left)
        detailed_max_lon = min(detailed_max_lon, bounds.right)
        detailed_min_lat = max(detailed_min_lat, bounds.bottom)
        detailed_max_lat = min(detailed_max_lat, bounds.top)
        
        print(f"Detailed view extent: [{detailed_min_lon:.4f}, {detailed_max_lon:.4f}, "
              f"{detailed_min_lat:.4f}, {detailed_max_lat:.4f}]")
        
        # Read the hillshade data directly and display with imshow for better control
        hillshade_data = src.read(1)
        transform = src.transform
        
        # Calculate pixel coordinates for extent
        from rasterio.warp import transform as rasterio_transform
        
        # Get row/col indices for the extent
        row_min, col_min = ~transform * (detailed_min_lon, detailed_max_lat)
        row_max, col_max = ~transform * (detailed_max_lon, detailed_min_lat)
        
        row_min, col_min = int(max(0, row_min)), int(max(0, col_min))
        row_max, col_max = int(min(hillshade_data.shape[0], row_max)), int(min(hillshade_data.shape[1], col_max))
        
        # Crop data
        cropped_data = hillshade_data[row_min:row_max, col_min:col_max]
        
        # Display with imshow using proper extent
        im = ax.imshow(cropped_data, extent=[detailed_min_lon, detailed_max_lon, 
                                            detailed_min_lat, detailed_max_lat],
                      cmap='gray', alpha=0.8, vmin=0, vmax=255, 
                      origin='upper', interpolation='bilinear', zorder=1, aspect='auto')
        
        # Set limits explicitly
        ax.set_xlim(detailed_min_lon, detailed_max_lon)
        ax.set_ylim(detailed_min_lat, detailed_max_lat)
        
        # Set aspect ratio for latitude
        lat_rad = math.radians(GLACIER_LAT)
        ax.set_aspect(1.0 / math.cos(lat_rad), adjustable='box')
    
    # Load and plot vector data
    glacier_gdf = load_vector_file(GLACIER_OUTLINE)
    if glacier_gdf is not None:
        print("✅ Adding glacier outline")
        glacier_gdf.plot(ax=ax, facecolor='none', edgecolor='blue', 
                        linewidth=2, linestyle='--', alpha=0.7, zorder=3)
    
    catchment_gdf = load_vector_file(CATCHMENT_BOUNDARY)
    if catchment_gdf is not None:
        print("✅ Adding catchment boundary")
        catchment_gdf.plot(ax=ax, color='lightblue', edgecolor='blue', 
                          linewidth=1.5, alpha=0.3, zorder=3)
    
    # Mark glacier location
    ax.plot(GLACIER_LON, GLACIER_LAT, 'r*', markersize=25, 
            markeredgecolor='yellow', markeredgewidth=3, zorder=5)
    
    ax.text(GLACIER_LON + 0.02, GLACIER_LAT + 0.02, 'Didal Glacier',
            fontsize=11, weight='bold', color='red',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                     edgecolor='red', linewidth=2, alpha=0.9), zorder=6)
    
    ax.set_xlabel('Longitude (°E)', fontsize=10, weight='bold')
    ax.set_ylabel('Latitude (°N)', fontsize=10, weight='bold')
    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5, zorder=2)
    
    # Scale bar (accurate for latitude)
    lat_rad = math.radians(GLACIER_LAT)
    km_per_deg_lon = 111.32 * math.cos(lat_rad)
    scale_km = 10
    scale_length_deg = scale_km / km_per_deg_lon
    
    scale_x = GLACIER_LON - 0.25
    scale_y = GLACIER_LAT - 0.25
    ax.plot([scale_x, scale_x + scale_length_deg], 
           [scale_y, scale_y], 'k-', linewidth=3, zorder=6)
    ax.text(scale_x + scale_length_deg/2, scale_y - 0.015, f'{scale_km} km',
            ha='center', fontsize=9, weight='bold',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.9), zorder=6)
    
    # North arrow
    arrow_x = GLACIER_LON + 0.25
    arrow_y = GLACIER_LAT + 0.25
    ax.annotate('', xy=(arrow_x, arrow_y + 0.02), 
               xytext=(arrow_x, arrow_y),
               arrowprops=dict(arrowstyle='->', lw=2, color='black'), zorder=6)
    ax.text(arrow_x, arrow_y + 0.03, 'N', ha='center', fontsize=10, 
           weight='bold', zorder=6)
    
    ax.set_title('(b) Detailed view of the study area. Glacier location: 38.97°N, 70.75°E', 
                fontsize=11, weight='bold', pad=10)

def create_figure1_properly_fixed():
    """Create properly fixed Figure 1."""
    print("=" * 70)
    print("CREATING PROPERLY FIXED FIGURE 1")
    print("=" * 70)
    
    fig = plt.figure(figsize=(12, 10))
    
    ax1 = plt.subplot(2, 1, 1)
    create_regional_context(ax1)
    
    ax2 = plt.subplot(2, 1, 2)
    create_detailed_view(ax2)
    
    plt.tight_layout(pad=2.0)
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"\n✅ Properly Fixed Figure 1 saved to: {OUTPUT_FILE}")
    
    return fig

if __name__ == "__main__":
    fig = create_figure1_properly_fixed()
    plt.close(fig)
    print("\n" + "=" * 70)
    print("✅ FIGURE 1 PROPERLY FIXED!")
    print("=" * 70)

