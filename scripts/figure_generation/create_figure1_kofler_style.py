#!/usr/bin/env python3
"""
Create Figure 1 in Kofler et al. (2021) style for Didal Glacier paper.
Two panels:
(a) Upper: Regional context showing location, stations, events
(b) Lower: Detailed view of study area with DEM and glacier location
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch
from matplotlib.dates import DateFormatter, WeekdayLocator
import numpy as np
import rasterio
from rasterio.plot import show
from datetime import datetime
import os

# Try to import cartopy (optional)
try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    HAS_CARTOPY = True
except ImportError:
    HAS_CARTOPY = False

# Study area parameters
GLACIER_LAT = 38.97
GLACIER_LON = 70.75

# ERA5-Land grid cell (approximate center)
ERA5_LAT = 38.97  # Same as glacier (grid cell containing glacier)
ERA5_LON = 70.75

# Key event locations (if different from glacier location)
# For now, we'll use the same location as the glacier
EVENT_LOCATIONS = {
    'initial_movement': {'lat': 38.97, 'lon': 70.75, 'date': '2025-09-19', 'label': 'Initial movement'},
    'second_movement': {'lat': 38.97, 'lon': 70.75, 'date': '2025-10-25', 'label': 'Second movement'},
    'earthquake': {'lat': 38.97, 'lon': 70.75, 'date': '2025-11-03', 'label': 'Earthquake'}
}

# File paths
DEM_HILLSHADE = 'satellite_data/dem/processed/hillshade.tif'
OUTPUT_FILE = 'processed_data/analysis_results/figure1_study_area_kofler_style.png'

def create_regional_context(ax):
    """
    Create upper panel: Regional context map showing location, stations, events.
    Similar to Kofler Figure 1 upper panel.
    """
    if HAS_CARTOPY:
        # Use cartopy if available
        ax.set_extent([68, 74, 36, 42], crs=ccrs.PlateCarree())
        ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
        ax.add_feature(cfeature.BORDERS, linewidth=0.5, linestyle='--')
        ax.add_feature(cfeature.LAND, alpha=0.5, facecolor='lightgray')
        ax.add_feature(cfeature.OCEAN, alpha=0.3, facecolor='lightblue')
        
        # Mark glacier location
        ax.plot(GLACIER_LON, GLACIER_LAT, 'r*', markersize=20, 
                transform=ccrs.PlateCarree(), zorder=5, 
                markeredgecolor='yellow', markeredgewidth=2,
                label='Didal Glacier')
        
        # Add text label
        ax.text(GLACIER_LON + 0.3, GLACIER_LAT + 0.1, 'Didal Glacier',
                transform=ccrs.PlateCarree(), fontsize=11, weight='bold',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='white', 
                         edgecolor='red', linewidth=2, alpha=0.9))
        
        # Add gridlines
        gl = ax.gridlines(draw_labels=True, linewidth=0.5, color='gray', 
                         alpha=0.5, linestyle='--', zorder=1)
        gl.top_labels = False
        gl.right_labels = False
    else:
        # Simplified version without cartopy
        ax.set_xlim(68, 74)
        ax.set_ylim(36, 42)
        
        # Draw simplified country boundaries (Tajikistan approximate)
        tajikistan_lon = [67.5, 71.5, 73.5, 73.0, 71.0, 67.5]
        tajikistan_lat = [36.5, 36.0, 37.5, 40.5, 40.5, 37.0]
        ax.plot(tajikistan_lon, tajikistan_lat, 'k-', linewidth=1.5, 
                label='Tajikistan border', zorder=2)
        ax.fill(tajikistan_lon, tajikistan_lat, alpha=0.3, color='lightgray', zorder=1)
        
        # Mark glacier location (main site)
        ax.plot(GLACIER_LON, GLACIER_LAT, 'r*', markersize=25, 
                markeredgecolor='yellow', markeredgewidth=2.5, 
                label='Didal Glacier', zorder=5)
        
        # Mark ERA5-Land grid cell location (if different)
        if abs(ERA5_LAT - GLACIER_LAT) > 0.01 or abs(ERA5_LON - GLACIER_LON) > 0.01:
            ax.plot(ERA5_LON, ERA5_LAT, 'bs', markersize=12, 
                    markeredgecolor='black', markeredgewidth=1.5,
                    label='ERA5-Land grid cell', zorder=4)
        
        # Mark event locations
        for event_key, event_info in EVENT_LOCATIONS.items():
            if event_key != 'initial_movement':  # Initial movement is at glacier location
                ax.plot(event_info['lon'], event_info['lat'], 'o', 
                       markersize=10, color=event_info.get('color', 'orange'),
                       markeredgecolor='black', markeredgewidth=1.5,
                       zorder=4)
        
        # Add text labels
        ax.text(GLACIER_LON + 0.3, GLACIER_LAT + 0.15, 'Didal Glacier',
                fontsize=11, weight='bold',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='white', 
                         edgecolor='red', linewidth=2, alpha=0.9), zorder=6)
        
        # Add location text box
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
    
    # Add title
    ax.set_title('(a) Regional context of study; location of failure site, meteorological data source, and registered hazard events', 
                fontsize=11, weight='bold', pad=10)
    
    # Add legend
    legend_elements = [
        plt.Line2D([0], [0], marker='*', color='w', markerfacecolor='red', 
                  markersize=15, markeredgecolor='yellow', markeredgewidth=2,
                  label='Didal Glacier'),
    ]
    if abs(ERA5_LAT - GLACIER_LAT) > 0.01 or abs(ERA5_LON - GLACIER_LON) > 0.01:
        legend_elements.append(
            plt.Line2D([0], [0], marker='s', color='w', markerfacecolor='blue', 
                      markersize=10, markeredgecolor='black', markeredgewidth=1.5,
                      label='ERA5-Land grid cell')
        )
    ax.legend(handles=legend_elements, loc='lower right', fontsize=9, 
             framealpha=0.9, frameon=True)

def create_detailed_view(ax):
    """
    Create lower panel: Detailed view of study area with DEM hillshade.
    Similar to Kofler Figure 1 lower panel.
    """
    # Read DEM hillshade
    if not os.path.exists(DEM_HILLSHADE):
        print(f"Warning: {DEM_HILLSHADE} not found. Creating placeholder.")
        ax.text(0.5, 0.5, 'DEM data not available', 
                transform=ax.transAxes, ha='center', va='center', fontsize=12)
        ax.set_title('(b) Detailed view of the study area', fontsize=11, weight='bold', pad=10)
        return
    
    with rasterio.open(DEM_HILLSHADE) as src:
        # Get bounds
        bounds = src.bounds
        extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
        
        # Read data
        data = src.read(1)
        
        # Plot hillshade
        im = ax.imshow(data, extent=extent, cmap='gray', origin='upper', 
                      interpolation='bilinear', vmin=0, vmax=255, zorder=1)
        
        # Mark glacier location with prominent marker
        ax.plot(GLACIER_LON, GLACIER_LAT, 'r*', markersize=25, 
                markeredgecolor='yellow', markeredgewidth=3, 
                label='Didal Glacier', zorder=5)
        
        # Add text label for glacier
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
        
        # Zoom to area around glacier (±0.3 degrees for detailed view)
        ax.set_xlim(GLACIER_LON - 0.3, GLACIER_LON + 0.3)
        ax.set_ylim(GLACIER_LAT - 0.3, GLACIER_LAT + 0.3)
        
        # Add scale bar (approximate)
        # At this latitude, 1 degree ≈ 111 km
        scale_length_deg = 0.1  # ~11 km
        scale_x = GLACIER_LON - 0.25
        scale_y = GLACIER_LAT - 0.25
        ax.plot([scale_x, scale_x + scale_length_deg], 
               [scale_y, scale_y], 'k-', linewidth=3, zorder=6)
        ax.text(scale_x + scale_length_deg/2, scale_y - 0.02, '~11 km',
                ha='center', fontsize=9, weight='bold',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8), zorder=6)
        
        # Add north arrow (simple)
        arrow_x = GLACIER_LON + 0.25
        arrow_y = GLACIER_LAT + 0.25
        ax.annotate('', xy=(arrow_x, arrow_y + 0.02), 
                   xytext=(arrow_x, arrow_y),
                   arrowprops=dict(arrowstyle='->', lw=2, color='black'), zorder=6)
        ax.text(arrow_x, arrow_y + 0.03, 'N', ha='center', fontsize=10, 
               weight='bold', zorder=6)
    
    # Add title
    ax.set_title('(b) Detailed view of the study area. Glacier location: 38.97°N, 70.75°E', 
                fontsize=11, weight='bold', pad=10)

def create_figure1_kofler_style():
    """
    Create complete Figure 1 in Kofler et al. (2021) style with two panels.
    """
    # Create figure with two panels (upper and lower)
    fig = plt.figure(figsize=(12, 10))
    
    # Upper panel: Regional context
    if HAS_CARTOPY:
        ax1 = plt.subplot(2, 1, 1, projection=ccrs.PlateCarree())
    else:
        ax1 = plt.subplot(2, 1, 1)
    create_regional_context(ax1)
    
    # Lower panel: Detailed view
    ax2 = plt.subplot(2, 1, 2)
    create_detailed_view(ax2)
    
    # Adjust layout
    plt.tight_layout(pad=2.0)
    
    # Save figure
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"✅ Figure 1 (Kofler style) saved to: {OUTPUT_FILE}")
    
    return fig

if __name__ == "__main__":
    # Create figure
    fig = create_figure1_kofler_style()
    plt.close(fig)
    print("✅ Figure 1 (Kofler style) created successfully!")

