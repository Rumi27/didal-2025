#!/usr/bin/env python3
"""
Create fixed Figure 1 with proper coordinate system handling.
Fixes:
- CRS mismatch (DEM vs WGS84)
- Axis inversion issues
- Proper extent handling
- Better georeferencing
"""

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.plot import show
from rasterio.warp import transform as rasterio_transform
from rasterio.crs import CRS
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
OUTPUT_FILE = 'processed_data/analysis_results/figure1_fixed.png'

def check_crs_bounds():
    """Check CRS and bounds of DEM and hillshade."""
    print("=" * 70)
    print("CHECKING CRS AND BOUNDS")
    print("=" * 70)
    
    with rasterio.open(DEM_FILE) as src:
        print(f"\nDEM CRS: {src.crs}")
        print(f"DEM Bounds: {src.bounds}")
        print(f"DEM Shape: {src.shape}")
    
    if os.path.exists(DEM_HILLSHADE):
        with rasterio.open(DEM_HILLSHADE) as src:
            print(f"\nHillshade CRS: {src.crs}")
            print(f"Hillshade Bounds: {src.bounds}")
            print(f"Hillshade Shape: {src.shape}")
    
    print("=" * 70)

def transform_coords_to_crs(lon, lat, target_crs):
    """Transform WGS84 coordinates to target CRS."""
    try:
        from pyproj import Transformer
        transformer = Transformer.from_crs("EPSG:4326", target_crs, always_xy=True)
        x, y = transformer.transform(lon, lat)
        return x, y
    except ImportError:
        # Fallback: try rasterio
        try:
            x, y = rasterio_transform(
                "EPSG:4326",
                target_crs,
                [lon], [lat]
            )
            return x[0], y[0]
        except:
            return lon, lat  # Return as-is if transform fails

def load_vector_file(filepath):
    """Load vector file and return GeoDataFrame in WGS84."""
    try:
        import geopandas as gpd
        if os.path.exists(filepath):
            gdf = gpd.read_file(filepath)
            # Convert to WGS84
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
    # Explicit extent in WGS84 (longitude, latitude)
    regional_extent = [
        GLACIER_LON - 2.0,  # min lon
        GLACIER_LON + 2.0,  # max lon
        GLACIER_LAT - 2.0,  # min lat
        GLACIER_LAT + 2.0   # max lat
    ]
    
    # Set limits explicitly (min to max)
    ax.set_xlim(min(regional_extent[0], regional_extent[1]), 
                max(regional_extent[0], regional_extent[1]))
    ax.set_ylim(min(regional_extent[2], regional_extent[3]), 
                max(regional_extent[2], regional_extent[3]))
    
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
    
    # Ensure proper aspect ratio (account for latitude)
    import math
    lat_rad = math.radians(GLACIER_LAT)
    ax.set_aspect(1.0 / math.cos(lat_rad), adjustable='box')
    
    ax.set_title('(a) Regional context of study; location of failure site, meteorological data source, and registered hazard events', 
                fontsize=11, weight='bold', pad=10)

def create_detailed_view(ax):
    """Create detailed view with proper CRS handling."""
    # Check hillshade CRS first
    if not os.path.exists(DEM_HILLSHADE):
        print("⚠️  Hillshade not found, using fallback")
        ax.text(0.5, 0.5, 'DEM data not available', 
               transform=ax.transAxes, ha='center', va='center')
        return
    
    with rasterio.open(DEM_HILLSHADE) as src:
        hillshade_crs = src.crs
        hillshade_bounds = src.bounds
        
        print(f"\nDetailed View CRS: {hillshade_crs}")
        print(f"Hillshade Bounds: {hillshade_bounds}")
        
        # If DEM is in WGS84 (EPSG:4326), use directly
        if hillshade_crs and str(hillshade_crs) == 'EPSG:4326':
            # Use rasterio.plot.show with explicit extent
            show(src, ax=ax, cmap='gray', alpha=0.8, vmin=0, vmax=255, zorder=1)
            
            # Set extent (explicitly min to max)
            detailed_extent = [
                GLACIER_LON - 0.3,  # min lon
                GLACIER_LON + 0.3,  # max lon
                GLACIER_LAT - 0.3,  # min lat
                GLACIER_LAT + 0.3   # max lat
            ]
            
            ax.set_xlim(min(detailed_extent[0], detailed_extent[1]), 
                       max(detailed_extent[0], detailed_extent[1]))
            ax.set_ylim(min(detailed_extent[2], detailed_extent[3]), 
                       max(detailed_extent[2], detailed_extent[3]))
            
            # Set aspect ratio for latitude
            import math
            lat_rad = math.radians(GLACIER_LAT)
            ax.set_aspect(1.0 / math.cos(lat_rad), adjustable='box')
            
        else:
            # DEM is in projected CRS (e.g., UTM)
            # Transform glacier coordinates to DEM CRS
            glacier_x, glacier_y = transform_coords_to_crs(
                GLACIER_LON, GLACIER_LAT, hillshade_crs
            )
            
            print(f"Glacier in DEM CRS: ({glacier_x:.2f}, {glacier_y:.2f})")
            
            # Use rasterio.plot.show (handles projection automatically)
            show(src, ax=ax, cmap='gray', alpha=0.8, vmin=0, vmax=255, zorder=1)
            
            # Set extent in projected coordinates
            # Use a reasonable zoom (e.g., 30 km = 30000 m for UTM)
            zoom = 30000  # meters
            ax.set_xlim(glacier_x - zoom, glacier_x + zoom)
            ax.set_ylim(glacier_y - zoom, glacier_y + zoom)
            
            # Equal aspect for projected coordinates
            ax.set_aspect('equal', adjustable='box')
    
    # Load and plot vector data (in WGS84, will be transformed by geopandas if needed)
    glacier_gdf = load_vector_file(GLACIER_OUTLINE)
    if glacier_gdf is not None:
        print("✅ Adding glacier outline")
        # Transform to DEM CRS if needed
        if hillshade_crs and str(hillshade_crs) != 'EPSG:4326':
            glacier_gdf_plot = glacier_gdf.to_crs(hillshade_crs)
        else:
            glacier_gdf_plot = glacier_gdf
        glacier_gdf_plot.plot(ax=ax, facecolor='none', edgecolor='blue', 
                            linewidth=2, linestyle='--', alpha=0.7, zorder=3)
    
    catchment_gdf = load_vector_file(CATCHMENT_BOUNDARY)
    if catchment_gdf is not None:
        print("✅ Adding catchment boundary")
        if hillshade_crs and str(hillshade_crs) != 'EPSG:4326':
            catchment_gdf_plot = catchment_gdf.to_crs(hillshade_crs)
        else:
            catchment_gdf_plot = catchment_gdf
        catchment_gdf_plot.plot(ax=ax, color='lightblue', edgecolor='blue', 
                               linewidth=1.5, alpha=0.3, zorder=3)
    
    # Mark glacier location
    if hillshade_crs and str(hillshade_crs) == 'EPSG:4326':
        # Use WGS84 coordinates directly
        ax.plot(GLACIER_LON, GLACIER_LAT, 'r*', markersize=25, 
                markeredgecolor='yellow', markeredgewidth=3, zorder=5)
        label_x, label_y = GLACIER_LON + 0.02, GLACIER_LAT + 0.02
        scale_x, scale_y = GLACIER_LON - 0.25, GLACIER_LAT - 0.25
        arrow_x, arrow_y = GLACIER_LON + 0.25, GLACIER_LAT + 0.25
    else:
        # Use projected coordinates
        ax.plot(glacier_x, glacier_y, 'r*', markersize=25, 
                markeredgecolor='yellow', markeredgewidth=3, zorder=5)
        label_x, label_y = glacier_x + 500, glacier_y + 500  # meters
        scale_x, scale_y = glacier_x - 5000, glacier_y - 5000
        arrow_x, arrow_y = glacier_x + 5000, glacier_y + 5000
    
    ax.text(label_x, label_y, 'Didal Glacier',
            fontsize=11, weight='bold', color='red',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                     edgecolor='red', linewidth=2, alpha=0.9), zorder=6)
    
    ax.set_xlabel('Longitude (°E)' if (hillshade_crs and str(hillshade_crs) == 'EPSG:4326') else 'Easting (m)', 
                  fontsize=10, weight='bold')
    ax.set_ylabel('Latitude (°N)' if (hillshade_crs and str(hillshade_crs) == 'EPSG:4326') else 'Northing (m)', 
                  fontsize=10, weight='bold')
    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5, zorder=2)
    
    # Scale bar
    if hillshade_crs and str(hillshade_crs) == 'EPSG:4326':
        # Calculate scale bar in degrees
        lat_rad = math.radians(GLACIER_LAT)
        km_per_deg_lon = 111.32 * math.cos(lat_rad)
        scale_km = 10
        scale_length_deg = scale_km / km_per_deg_lon
        ax.plot([scale_x, scale_x + scale_length_deg], 
               [scale_y, scale_y], 'k-', linewidth=3, zorder=6)
        ax.text(scale_x + scale_length_deg/2, scale_y - 0.015, f'{scale_km} km',
                ha='center', fontsize=9, weight='bold',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.9), zorder=6)
    else:
        # Scale bar in meters
        scale_m = 10000  # 10 km
        ax.plot([scale_x, scale_x + scale_m], 
               [scale_y, scale_y], 'k-', linewidth=3, zorder=6)
        ax.text(scale_x + scale_m/2, scale_y - 1000, '10 km',
                ha='center', fontsize=9, weight='bold',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.9), zorder=6)
    
    # North arrow
    ax.annotate('', xy=(arrow_x, arrow_y + (2000 if hillshade_crs and str(hillshade_crs) != 'EPSG:4326' else 0.02)), 
               xytext=(arrow_x, arrow_y),
               arrowprops=dict(arrowstyle='->', lw=2, color='black'), zorder=6)
    ax.text(arrow_x, arrow_y + (3000 if hillshade_crs and str(hillshade_crs) != 'EPSG:4326' else 0.03), 'N', 
           ha='center', fontsize=10, weight='bold', zorder=6)
    
    ax.set_title('(b) Detailed view of the study area. Glacier location: 38.97°N, 70.75°E', 
                fontsize=11, weight='bold', pad=10)

def create_figure1_fixed():
    """Create fixed Figure 1 with proper coordinate handling."""
    print("=" * 70)
    print("CREATING FIXED FIGURE 1")
    print("=" * 70)
    
    # Check CRS and bounds first
    check_crs_bounds()
    
    # Create figure
    fig = plt.figure(figsize=(12, 10))
    
    ax1 = plt.subplot(2, 1, 1)
    create_regional_context(ax1)
    
    ax2 = plt.subplot(2, 1, 2)
    create_detailed_view(ax2)
    
    plt.tight_layout(pad=2.0)
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"\n✅ Fixed Figure 1 saved to: {OUTPUT_FILE}")
    
    return fig

if __name__ == "__main__":
    fig = create_figure1_fixed()
    plt.close(fig)
    print("\n" + "=" * 70)
    print("✅ FIGURE 1 FIXED CREATED SUCCESSFULLY!")
    print("=" * 70)

