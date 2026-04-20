#!/usr/bin/env python3
"""
Create refined Figure 1 with professional styling and proper georeferencing.
Includes improvements:
- Proper coordinate system handling (rasterio.plot.show)
- Geopandas plotting (instead of manual patches)
- Accurate scale bar calculation
- Professional visual styling
- Optional inset map layout (like Kofler)
"""

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.plot import show
import json
import os
import math

# Study area parameters
GLACIER_LAT = 38.97
GLACIER_LON = 70.75

# File paths
DEM_FILE = 'satellite_data/SRTM1_Arc_Second_Global/n38_e070_1arc_v3.tif'
DEM_HILLSHADE = 'satellite_data/dem/processed/hillshade.tif'
GLACIER_OUTLINE = 'satellite_data/dem/processed/didal_glacier_rgi_outline.shp'
CATCHMENT_BOUNDARY = 'satellite_data/dem/processed/catchment_boundary.shp'
OUTPUT_FILE = 'processed_data/analysis_results/figure1_refined.png'

def load_dem():
    """Load DEM and return data, transform, and bounds."""
    with rasterio.open(DEM_FILE) as src:
        data = src.read(1)
        transform = src.transform
        bounds = src.bounds
        crs = src.crs
    return data, transform, bounds, crs

def generate_contours(data, bounds, interval=50, smoothing=None):
    """Generate contour lines from DEM."""
    from scipy import ndimage
    
    if smoothing:
        data = ndimage.gaussian_filter(data, sigma=smoothing)
    
    min_elev = np.nanmin(data)
    max_elev = np.nanmax(data)
    levels = np.arange(
        np.floor(min_elev / interval) * interval,
        np.ceil(max_elev / interval) * interval + interval,
        interval
    )
    
    height, width = data.shape
    x = np.linspace(bounds.left, bounds.right, width)
    y = np.linspace(bounds.bottom, bounds.top, height)
    X, Y = np.meshgrid(x, y)
    
    return X, Y, data, levels

def load_vector_file(filepath):
    """Load vector file (shapefile/GeoJSON) and return GeoDataFrame."""
    try:
        import geopandas as gpd
        if os.path.exists(filepath):
            gdf = gpd.read_file(filepath)
            # Convert to WGS84 if needed
            if gdf.crs and gdf.crs.to_string() != 'EPSG:4326':
                gdf = gdf.to_crs('EPSG:4326')
            return gdf
        return None
    except ImportError:
        return None
    except Exception as e:
        print(f"Warning: Could not load {filepath}: {e}")
        return None

def create_regional_context(ax, use_inset=False):
    """
    Create regional context map.
    If use_inset=True, designed to be used as inset map.
    """
    regional_extent = [
        GLACIER_LON - 2.0, GLACIER_LON + 2.0,
        GLACIER_LAT - 2.0, GLACIER_LAT + 2.0
    ]
    
    ax.set_xlim(regional_extent[0], regional_extent[2])
    ax.set_ylim(regional_extent[1], regional_extent[3])
    
    # Country boundaries
    tajikistan_lon = [67.5, 71.5, 73.5, 73.0, 71.0, 67.5]
    tajikistan_lat = [36.5, 36.0, 37.5, 40.5, 40.5, 37.0]
    ax.plot(tajikistan_lon, tajikistan_lat, 'k-', linewidth=1.5, zorder=2)
    ax.fill(tajikistan_lon, tajikistan_lat, alpha=0.2, color='lightgray', zorder=1)
    
    # Mark glacier location
    ax.plot(GLACIER_LON, GLACIER_LAT, 'r*', markersize=20 if use_inset else 25, 
            markeredgecolor='yellow', markeredgewidth=2, zorder=5)
    
    if not use_inset:
        ax.text(GLACIER_LON + 0.3, GLACIER_LAT + 0.15, 'Didal Glacier',
                fontsize=11 if not use_inset else 9, weight='bold',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='white', 
                         edgecolor='red', linewidth=2, alpha=0.9), zorder=6)
        
        ax.text(0.02, 0.98, 'Pamir Mountains\nTajikistan', 
                transform=ax.transAxes, fontsize=11 if not use_inset else 9, weight='bold',
                verticalalignment='top',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='white', 
                         edgecolor='black', linewidth=1.5, alpha=0.9), zorder=6)
    
    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5, zorder=1)
    ax.set_xlabel('Longitude (°E)', fontsize=11 if not use_inset else 9, weight='bold')
    ax.set_ylabel('Latitude (°N)', fontsize=11 if not use_inset else 9, weight='bold')
    ax.set_aspect('equal', adjustable='box')
    
    if not use_inset:
        ax.set_title('(a) Regional context of study; location of failure site, meteorological data source, and registered hazard events', 
                    fontsize=11, weight='bold', pad=10)

def create_detailed_view(ax, dem_data, dem_bounds, contour_interval=20, add_planetscope=False):
    """
    Create detailed view with proper georeferencing and professional styling.
    """
    # 1. Use rasterio.plot.show for better georeferencing (handles coordinate system automatically)
    if os.path.exists(DEM_HILLSHADE):
        with rasterio.open(DEM_HILLSHADE) as src:
            # Use rasterio's show for proper georeferencing
            # Set alpha to 0.8 if adding PlanetScope overlay, otherwise 1.0
            alpha = 0.7 if add_planetscope else 0.8
            rasterio.plot.show(src, ax=ax, cmap='gray', alpha=alpha, 
                             vmin=0, vmax=255, zorder=1)
            # Get extent from source
            bounds = src.bounds
            detailed_extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
    else:
        # Fallback to manual extent
        detailed_extent = [
            GLACIER_LON - 0.3, GLACIER_LON + 0.3,
            GLACIER_LAT - 0.3, GLACIER_LAT + 0.3
        ]
        ax.set_xlim(detailed_extent[0], detailed_extent[2])
        ax.set_ylim(detailed_extent[1], detailed_extent[3])
    
    # 2. Generate contours with smoothing (reduces SRTM artifacts)
    X, Y, data, levels = generate_contours(dem_data, dem_bounds, 
                                          interval=contour_interval, smoothing=0.5)
    
    # Plot contours (every other to avoid clutter)
    contour_levels = levels[::2]
    contours = ax.contour(X, Y, data, levels=contour_levels, colors='gray', 
                         alpha=0.4, linewidths=0.5, zorder=2)
    # Sparse contour labels
    ax.clabel(contours, inline=True, fontsize=7, fmt='%d', colors='gray')
    
    # 3. Simplified Geopandas Plotting (handles multi-part polygons automatically)
    glacier_gdf = load_vector_file(GLACIER_OUTLINE)
    if glacier_gdf is not None:
        print("✅ Adding glacier outline from RGI")
        glacier_gdf.plot(ax=ax, facecolor='none', edgecolor='blue', 
                        linewidth=2, linestyle='--', alpha=0.7, zorder=3, 
                        label='Glacier Outline')
    
    catchment_gdf = load_vector_file(CATCHMENT_BOUNDARY)
    if catchment_gdf is not None:
        print("✅ Adding catchment boundary")
        catchment_gdf.plot(ax=ax, color='lightblue', edgecolor='blue', 
                          linewidth=1.5, alpha=0.3, zorder=3, label='Catchment')
    
    # 4. Mark glacier location
    ax.plot(GLACIER_LON, GLACIER_LAT, 'r*', markersize=25, 
            markeredgecolor='yellow', markeredgewidth=3, zorder=5)
    
    ax.text(GLACIER_LON + 0.02, GLACIER_LAT + 0.02, 'Didal Glacier',
            fontsize=11, weight='bold', color='red',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                     edgecolor='red', linewidth=2, alpha=0.9), zorder=6)
    
    # 5. Labels and grid
    ax.set_xlabel('Longitude (°E)', fontsize=10, weight='bold')
    ax.set_ylabel('Latitude (°N)', fontsize=10, weight='bold')
    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5, zorder=2)
    
    # Set extent (zoom to detailed view)
    if os.path.exists(DEM_HILLSHADE):
        # Use actual bounds but zoom in
        center_lon = (bounds.left + bounds.right) / 2
        center_lat = (bounds.bottom + bounds.top) / 2
        zoom = 0.3  # degrees
        ax.set_xlim(center_lon - zoom, center_lon + zoom)
        ax.set_ylim(center_lat - zoom, center_lat + zoom)
    else:
        ax.set_xlim(detailed_extent[0], detailed_extent[2])
        ax.set_ylim(detailed_extent[1], detailed_extent[3])
    
    # 6. Dynamic Scale Bar (accurate for latitude)
    # At 38.97°N: 1° longitude ≈ 86.6 km, 1° latitude ≈ 111 km
    lat_rad = math.radians(GLACIER_LAT)
    km_per_deg_lon = 111.32 * math.cos(lat_rad)  # ~86.6 km at 38.97°N
    
    scale_km = 10  # 10 km scale bar
    scale_length_deg = scale_km / km_per_deg_lon
    
    scale_x = GLACIER_LON - 0.25
    scale_y = GLACIER_LAT - 0.25
    ax.plot([scale_x, scale_x + scale_length_deg], 
           [scale_y, scale_y], 'k-', linewidth=3, zorder=6)
    ax.text(scale_x + scale_length_deg/2, scale_y - 0.015, f'{scale_km} km',
            ha='center', fontsize=9, weight='bold',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.9), zorder=6)
    
    # 7. North arrow
    arrow_x = GLACIER_LON + 0.25
    arrow_y = GLACIER_LAT + 0.25
    ax.annotate('', xy=(arrow_x, arrow_y + 0.02), 
               xytext=(arrow_x, arrow_y),
               arrowprops=dict(arrowstyle='->', lw=2, color='black'), zorder=6)
    ax.text(arrow_x, arrow_y + 0.03, 'N', ha='center', fontsize=10, 
           weight='bold', zorder=6)
    
    # 8. Title
    ax.set_title('(b) Detailed view of the study area. Glacier location: 38.97°N, 70.75°E', 
                fontsize=11, weight='bold', pad=10)

def create_figure1_refined(use_inset=False):
    """
    Create refined Figure 1 with professional styling.
    
    Parameters:
    -----------
    use_inset : bool
        If True, use inset map layout (like Kofler). 
        If False, use vertical panel layout (current).
    """
    print("=" * 70)
    print("CREATING REFINED FIGURE 1 WITH PROFESSIONAL STYLING")
    print("=" * 70)
    
    # Load DEM
    print("\nLoading DEM data...")
    dem_data, transform, dem_bounds, crs = load_dem()
    print(f"✅ DEM loaded: {dem_data.shape}")
    
    # Check for available data
    print("\nChecking for additional data:")
    if os.path.exists(GLACIER_OUTLINE):
        print(f"  ✅ Glacier outline: {GLACIER_OUTLINE}")
    else:
        print(f"  ⚠️  Glacier outline not found (will use point marker)")
    
    if os.path.exists(CATCHMENT_BOUNDARY):
        print(f"  ✅ Catchment boundary: {CATCHMENT_BOUNDARY}")
    else:
        print(f"  ⚠️  Catchment boundary not found (optional)")
    
    # Create figure
    if use_inset:
        # Inset map layout (like Kofler)
        fig = plt.figure(figsize=(10, 8))
        ax_main = plt.subplot(1, 1, 1)
        create_detailed_view(ax_main, dem_data, dem_bounds, contour_interval=20)
        
        # Add inset map
        ax_inset = fig.add_axes([0.65, 0.68, 0.3, 0.3])  # [left, bottom, width, height]
        create_regional_context(ax_inset, use_inset=True)
        ax_inset.set_title('Regional Context', fontsize=9, weight='bold')
    else:
        # Vertical panel layout (current)
        fig = plt.figure(figsize=(12, 10))
        ax1 = plt.subplot(2, 1, 1)
        create_regional_context(ax1, use_inset=False)
        ax2 = plt.subplot(2, 1, 2)
        create_detailed_view(ax2, dem_data, dem_bounds, contour_interval=20)
    
    plt.tight_layout(pad=2.0)
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"\n✅ Refined Figure 1 saved to: {OUTPUT_FILE}")
    
    return fig

if __name__ == "__main__":
    # Create with vertical panels (current layout)
    fig = create_figure1_refined(use_inset=False)
    plt.close(fig)
    print("\n" + "=" * 70)
    print("✅ REFINED FIGURE 1 CREATED SUCCESSFULLY!")
    print("=" * 70)
    print("\nTo use inset map layout (like Kofler), set use_inset=True")

