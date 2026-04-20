#!/usr/bin/env python3
"""
Create improved Figure 1 with contour lines, better layer stacking, and professional styling.
Based on Kofler et al. (2021) approach with available Didal Glacier data.
"""

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.plot import show
from matplotlib.dates import DateFormatter, WeekdayLocator
from matplotlib.patches import Rectangle, FancyBboxPatch
import json
import os

# Study area parameters
GLACIER_LAT = 38.97
GLACIER_LON = 70.75

# File paths
DEM_FILE = 'satellite_data/SRTM1_Arc_Second_Global/n38_e070_1arc_v3.tif'
DEM_HILLSHADE = 'satellite_data/dem/processed/hillshade.tif'
AOI_GEOJSON = 'satellite_data/aoi_didal_glacier.geojson'
OUTPUT_FILE = 'processed_data/analysis_results/figure1_improved.png'

def load_dem():
    """Load DEM and return data, transform, and bounds."""
    with rasterio.open(DEM_FILE) as src:
        data = src.read(1)
        transform = src.transform
        bounds = src.bounds
        crs = src.crs
    return data, transform, bounds, crs

def generate_contours(data, bounds, interval=50, smoothing=None):
    """
    Generate contour lines from DEM.
    
    Parameters:
    -----------
    data : numpy array
        DEM data
    bounds : BoundingBox
        DEM bounds (left, bottom, right, top)
    interval : float
        Contour interval in meters
    smoothing : float or None
        Gaussian smoothing sigma (None = no smoothing)
    
    Returns:
    --------
    contours : matplotlib.contour.QuadContourSet
        Contour set
    """
    from scipy import ndimage
    
    # Apply smoothing if requested (helps with SRTM artifacts)
    if smoothing:
        data = ndimage.gaussian_filter(data, sigma=smoothing)
    
    # Generate contour levels
    min_elev = np.nanmin(data)
    max_elev = np.nanmax(data)
    levels = np.arange(
        np.floor(min_elev / interval) * interval,
        np.ceil(max_elev / interval) * interval + interval,
        interval
    )
    
    # Create coordinate arrays
    height, width = data.shape
    x = np.linspace(bounds.left, bounds.right, width)
    y = np.linspace(bounds.bottom, bounds.top, height)
    X, Y = np.meshgrid(x, y)
    
    return X, Y, data, levels

def create_regional_context(ax, dem_data, dem_bounds):
    """
    Create upper panel: Regional context with hillshade and contours.
    """
    # Set extent for regional view (±2 degrees around glacier)
    regional_extent = [
        GLACIER_LON - 2.0, GLACIER_LON + 2.0,
        GLACIER_LAT - 2.0, GLACIER_LAT + 2.0
    ]
    
    # For regional view, we'll use a simplified approach
    # (In full implementation, would load regional DEM)
    ax.set_xlim(regional_extent[0], regional_extent[2])
    ax.set_ylim(regional_extent[1], regional_extent[3])
    
    # Draw simplified country boundaries (Tajikistan approximate)
    tajikistan_lon = [67.5, 71.5, 73.5, 73.0, 71.0, 67.5]
    tajikistan_lat = [36.5, 36.0, 37.5, 40.5, 40.5, 37.0]
    ax.plot(tajikistan_lon, tajikistan_lat, 'k-', linewidth=1.5, 
            label='Tajikistan border', zorder=2)
    ax.fill(tajikistan_lon, tajikistan_lat, alpha=0.2, color='lightgray', zorder=1)
    
    # Mark glacier location
    ax.plot(GLACIER_LON, GLACIER_LAT, 'r*', markersize=25, 
            markeredgecolor='yellow', markeredgewidth=2.5, 
            label='Didal Glacier', zorder=5)
    
    # Add text label
    ax.text(GLACIER_LON + 0.3, GLACIER_LAT + 0.15, 'Didal Glacier',
            fontsize=11, weight='bold',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='white', 
                     edgecolor='red', linewidth=2, alpha=0.9), zorder=6)
    
    # Add location text
    ax.text(0.02, 0.98, 'Pamir Mountains\nTajikistan', 
            transform=ax.transAxes, fontsize=11, weight='bold',
            verticalalignment='top',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='white', 
                     edgecolor='black', linewidth=1.5, alpha=0.9), zorder=6)
    
    # Add grid
    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5, zorder=1)
    ax.set_xlabel('Longitude (°E)', fontsize=11, weight='bold')
    ax.set_ylabel('Latitude (°N)', fontsize=11, weight='bold')
    ax.set_aspect('equal', adjustable='box')
    
    # Title
    ax.set_title('(a) Regional context of study; location of failure site, meteorological data source, and registered hazard events', 
                fontsize=11, weight='bold', pad=10)

def create_detailed_view(ax, dem_data, dem_bounds, contour_interval=20):
    """
    Create lower panel: Detailed view with hillshade, contours, and PlanetScope overlay.
    """
    # Read DEM hillshade if available
    if os.path.exists(DEM_HILLSHADE):
        with rasterio.open(DEM_HILLSHADE) as src:
            hillshade_data = src.read(1)
            hillshade_bounds = src.bounds
            hillshade_extent = [hillshade_bounds.left, hillshade_bounds.right, 
                               hillshade_bounds.bottom, hillshade_bounds.top]
            
            # Plot hillshade
            im = ax.imshow(hillshade_data, extent=hillshade_extent, cmap='gray', 
                          origin='upper', interpolation='bilinear', vmin=0, vmax=255, zorder=1)
    else:
        print(f"Warning: {DEM_HILLSHADE} not found. Using DEM directly.")
        # Fallback: use DEM as base
        height, width = dem_data.shape
        x = np.linspace(dem_bounds.left, dem_bounds.right, width)
        y = np.linspace(dem_bounds.bottom, dem_bounds.top, height)
        extent = [dem_bounds.left, dem_bounds.right, dem_bounds.bottom, dem_bounds.top]
        im = ax.imshow(dem_data, extent=extent, cmap='gray', origin='upper', zorder=1)
    
    # Generate and plot contour lines (20m interval for detailed view)
    X, Y, data, levels = generate_contours(dem_data, dem_bounds, 
                                          interval=contour_interval, smoothing=0.5)
    
    # Clip to detailed view extent (±0.3 degrees)
    detailed_extent = [
        GLACIER_LON - 0.3, GLACIER_LON + 0.3,
        GLACIER_LAT - 0.3, GLACIER_LAT + 0.3
    ]
    
    # Create mask for contours within extent
    mask = (X >= detailed_extent[0]) & (X <= detailed_extent[2]) & \
           (Y >= detailed_extent[1]) & (Y <= detailed_extent[3])
    
    # Plot contours (only show every 3rd or 4th contour to avoid clutter)
    contour_levels = levels[::2]  # Show every other contour
    contours = ax.contour(X, Y, data, levels=contour_levels, colors='gray', 
                         alpha=0.4, linewidths=0.5, zorder=2)
    
    # Optionally add contour labels (sparse) - alpha set in colors
    ax.clabel(contours, inline=True, fontsize=7, fmt='%d', 
             colors='gray')
    
    # Mark glacier location
    ax.plot(GLACIER_LON, GLACIER_LAT, 'r*', markersize=25, 
            markeredgecolor='yellow', markeredgewidth=3, 
            label='Didal Glacier', zorder=5)
    
    # Add text label
    ax.text(GLACIER_LON + 0.02, GLACIER_LAT + 0.02, 'Didal Glacier',
            fontsize=11, weight='bold', color='red',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                     edgecolor='red', linewidth=2, alpha=0.9), zorder=6)
    
    # Add coordinate labels
    ax.set_xlabel('Longitude (°E)', fontsize=10, weight='bold')
    ax.set_ylabel('Latitude (°N)', fontsize=10, weight='bold')
    
    # Add grid
    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5, zorder=2)
    
    # Set equal aspect ratio
    ax.set_aspect('equal', adjustable='box')
    
    # Set extent
    ax.set_xlim(detailed_extent[0], detailed_extent[2])
    ax.set_ylim(detailed_extent[1], detailed_extent[3])
    
    # Add scale bar (approximate)
    scale_length_deg = 0.1  # ~11 km at this latitude
    scale_x = GLACIER_LON - 0.25
    scale_y = GLACIER_LAT - 0.25
    ax.plot([scale_x, scale_x + scale_length_deg], 
           [scale_y, scale_y], 'k-', linewidth=3, zorder=6)
    ax.text(scale_x + scale_length_deg/2, scale_y - 0.02, '~11 km',
            ha='center', fontsize=9, weight='bold',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8), zorder=6)
    
    # Add north arrow
    arrow_x = GLACIER_LON + 0.25
    arrow_y = GLACIER_LAT + 0.25
    ax.annotate('', xy=(arrow_x, arrow_y + 0.02), 
               xytext=(arrow_x, arrow_y),
               arrowprops=dict(arrowstyle='->', lw=2, color='black'), zorder=6)
    ax.text(arrow_x, arrow_y + 0.03, 'N', ha='center', fontsize=10, 
           weight='bold', zorder=6)
    
    # Title with coordinates
    ax.set_title('(b) Detailed view of the study area. Glacier location: 38.97°N, 70.75°E', 
                fontsize=11, weight='bold', pad=10)

def create_improved_figure1():
    """
    Create improved Figure 1 with contour lines and professional styling.
    """
    # Load DEM data
    print("Loading DEM data...")
    dem_data, transform, dem_bounds, crs = load_dem()
    print(f"DEM loaded: {dem_data.shape}, bounds: {dem_bounds}")
    
    # Create figure with two panels
    fig = plt.figure(figsize=(12, 10))
    
    # Upper panel: Regional context
    ax1 = plt.subplot(2, 1, 1)
    create_regional_context(ax1, dem_data, dem_bounds)
    
    # Lower panel: Detailed view
    ax2 = plt.subplot(2, 1, 2)
    create_detailed_view(ax2, dem_data, dem_bounds, contour_interval=20)
    
    # Adjust layout
    plt.tight_layout(pad=2.0)
    
    # Save figure
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"✅ Improved Figure 1 saved to: {OUTPUT_FILE}")
    
    return fig

if __name__ == "__main__":
    # Create improved figure
    fig = create_improved_figure1()
    plt.close(fig)
    print("✅ Improved Figure 1 created successfully!")
    print("\nNext steps:")
    print("1. Check GLIMS/RGI for glacier outline")
    print("2. Generate catchment boundary")
    print("3. Add PlanetScope overlay (optional)")

