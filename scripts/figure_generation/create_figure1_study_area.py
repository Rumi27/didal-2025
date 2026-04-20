#!/usr/bin/env python3
"""
Create Figure 1: Study Area + Timeline for Didal Glacier paper.
Three panels:
(a) Regional context map (Pamir Mountains, Tajikistan)
(b) Hillshade DEM with glacier location
(c) Timeline with Sentinel-1 dates and key events
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle, Circle
from matplotlib.dates import DateFormatter, WeekdayLocator
import numpy as np
import rasterio
from rasterio.plot import show
from datetime import datetime, timedelta
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

# Sentinel-1 acquisition dates (from file names)
SENTINEL1_DATES = [
    '2025-09-07',
    '2025-09-13',
    '2025-09-19',
    '2025-09-25',
    '2025-10-01',
    '2025-10-07',
    '2025-10-13',
    '2025-10-19',
    '2025-10-25',
    '2025-10-31'
]

# Key event dates
KEY_EVENTS = {
    '2025-09-13': {'label': 'Peak velocity', 'color': 'red'},
    '2025-09-19': {'label': 'Initial movement', 'color': 'orange'},
    '2025-10-25': {'label': 'Second movement', 'color': 'darkorange'},
    '2025-11-03': {'label': 'Earthquake', 'color': 'purple'}
}

# File paths
DEM_HILLSHADE = 'satellite_data/dem/processed/hillshade.tif'
OUTPUT_FILE = 'processed_data/analysis_results/figure1_study_area.png'

def parse_date(date_str):
    """Parse date string to datetime object."""
    return datetime.strptime(date_str, '%Y-%m-%d')

def create_regional_map(ax):
    """
    Create panel (a): Regional context map showing location in Pamir Mountains.
    """
    if HAS_CARTOPY:
        # Use cartopy if available
        ax.set_extent([68, 74, 36, 42], crs=ccrs.PlateCarree())
        ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
        ax.add_feature(cfeature.BORDERS, linewidth=0.5, linestyle='--')
        ax.add_feature(cfeature.LAND, alpha=0.5, facecolor='lightgray')
        ax.add_feature(cfeature.OCEAN, alpha=0.3, facecolor='lightblue')
        ax.plot(GLACIER_LON, GLACIER_LAT, 'r*', markersize=15, 
                transform=ccrs.PlateCarree(), zorder=5, label='Didal Glacier')
        ax.text(GLACIER_LON + 0.3, GLACIER_LAT + 0.1, 'Didal Glacier',
                transform=ccrs.PlateCarree(), fontsize=10, weight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
        gl = ax.gridlines(draw_labels=True, linewidth=0.5, color='gray', 
                         alpha=0.5, linestyle='--', zorder=1)
        gl.top_labels = False
        gl.right_labels = False
    else:
        # Simplified version without cartopy
        # Create a simple map showing location
        ax.set_xlim(68, 74)
        ax.set_ylim(36, 42)
        
        # Draw simple country boundaries (approximate)
        # Tajikistan approximate boundary
        tajikistan_lon = [67.5, 71.5, 73.5, 73.0, 71.0, 67.5]
        tajikistan_lat = [36.5, 36.0, 37.5, 40.5, 40.5, 37.0]
        ax.plot(tajikistan_lon, tajikistan_lat, 'k-', linewidth=1.5, label='Tajikistan border')
        ax.fill(tajikistan_lon, tajikistan_lat, alpha=0.3, color='lightgray')
        
        # Mark glacier location
        ax.plot(GLACIER_LON, GLACIER_LAT, 'r*', markersize=20, 
                markeredgecolor='yellow', markeredgewidth=2, 
                label='Didal Glacier', zorder=5)
        
        # Add text label
        ax.text(GLACIER_LON + 0.3, GLACIER_LAT + 0.15, 'Didal Glacier',
                fontsize=11, weight='bold',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='white', 
                         edgecolor='red', linewidth=2, alpha=0.9))
        
        # Add location text
        ax.text(0.02, 0.98, 'Pamir Mountains\nTajikistan', 
                transform=ax.transAxes, fontsize=11, weight='bold',
                verticalalignment='top',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.8))
        
        # Add grid
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
        ax.set_xlabel('Longitude (°E)', fontsize=10, weight='bold')
        ax.set_ylabel('Latitude (°N)', fontsize=10, weight='bold')
        ax.set_aspect('equal', adjustable='box')
    
    ax.set_title('(a) Regional Context', fontsize=12, weight='bold', pad=10)

def create_dem_map(ax):
    """
    Create panel (b): Hillshade DEM with glacier location.
    """
    # Read DEM hillshade
    if not os.path.exists(DEM_HILLSHADE):
        print(f"Warning: {DEM_HILLSHADE} not found. Creating placeholder.")
        ax.text(0.5, 0.5, 'DEM data not available', 
                transform=ax.transAxes, ha='center', va='center')
        ax.set_title('(b) Study Area', fontsize=12, weight='bold', pad=10)
        return
    
    with rasterio.open(DEM_HILLSHADE) as src:
        # Get bounds
        bounds = src.bounds
        extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
        
        # Read data
        data = src.read(1)
        
        # Plot hillshade
        im = ax.imshow(data, extent=extent, cmap='gray', origin='upper', 
                      interpolation='bilinear', vmin=0, vmax=255)
        
        # Mark glacier location
        ax.plot(GLACIER_LON, GLACIER_LAT, 'r*', markersize=20, 
                markeredgecolor='yellow', markeredgewidth=2, 
                label='Didal Glacier', zorder=5)
        
        # Add coordinate labels
        ax.set_xlabel('Longitude (°E)', fontsize=10)
        ax.set_ylabel('Latitude (°N)', fontsize=10)
        
        # Add grid
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
        
        # Set equal aspect ratio
        ax.set_aspect('equal', adjustable='box')
        
        # Zoom to area around glacier (±0.5 degrees)
        ax.set_xlim(GLACIER_LON - 0.5, GLACIER_LON + 0.5)
        ax.set_ylim(GLACIER_LAT - 0.5, GLACIER_LAT + 0.5)
    
    ax.set_title('(b) Study Area', fontsize=12, weight='bold', pad=10)

def create_timeline(ax):
    """
    Create panel (c): Timeline showing Sentinel-1 dates and key events.
    """
    # Parse dates
    s1_dates = [parse_date(d) for d in SENTINEL1_DATES]
    key_event_dates = {parse_date(k): v for k, v in KEY_EVENTS.items()}
    
    # Create timeline
    start_date = parse_date('2025-09-01')
    end_date = parse_date('2025-11-15')
    
    # Plot Sentinel-1 dates
    y_pos = 1.0
    for date in s1_dates:
        ax.axvline(date, color='blue', linewidth=2, alpha=0.6, zorder=2)
    
    # Add Sentinel-1 label at top
    ax.scatter(s1_dates, [y_pos] * len(s1_dates), color='blue', 
              marker='|', s=200, linewidths=3, label='Sentinel-1 acquisitions', zorder=3)
    
    # Plot key events
    y_event = 0.7
    for date, event_info in sorted(key_event_dates.items()):
        color = event_info['color']
        label = event_info['label']
        ax.axvline(date, color=color, linewidth=2.5, linestyle='--', 
                  alpha=0.8, zorder=3)
        ax.scatter(date, y_event, color=color, marker='o', s=100, 
                  edgecolor='black', linewidth=1.5, zorder=4)
        ax.text(date, y_event - 0.15, label, fontsize=9, ha='center', 
               weight='bold', color=color)
    
    # Set limits
    ax.set_xlim(start_date, end_date)
    ax.set_ylim(0, 1.3)
    
    # Format x-axis (use numeric format to avoid font issues)
    ax.xaxis.set_major_formatter(DateFormatter('%m/%d'))
    ax.xaxis.set_major_locator(WeekdayLocator(interval=1))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # Labels
    ax.set_xlabel('Date (2025)', fontsize=10, weight='bold')
    ax.set_ylabel('', fontsize=10)
    ax.set_title('(c) Observation Timeline', fontsize=12, weight='bold', pad=10)
    
    # Legend
    legend_elements = [
        plt.Line2D([0], [0], color='blue', linewidth=3, label='Sentinel-1 acquisitions'),
        plt.Line2D([0], [0], color='red', linewidth=2.5, linestyle='--', label='Peak velocity'),
        plt.Line2D([0], [0], color='orange', linewidth=2.5, linestyle='--', label='Initial movement'),
        plt.Line2D([0], [0], color='darkorange', linewidth=2.5, linestyle='--', label='Second movement'),
        plt.Line2D([0], [0], color='purple', linewidth=2.5, linestyle='--', label='Earthquake')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=9, framealpha=0.9)
    
    # Grid
    ax.grid(True, alpha=0.3, linestyle='--', axis='x')

def create_figure1():
    """
    Create complete Figure 1 with three panels.
    """
    # Create figure with subplots
    fig = plt.figure(figsize=(14, 10))
    
    # Panel (a): Regional map
    if HAS_CARTOPY:
        ax1 = plt.subplot(2, 2, 1, projection=ccrs.PlateCarree())
    else:
        ax1 = plt.subplot(2, 2, 1)
    create_regional_map(ax1)
    
    # Panel (b): DEM hillshade
    ax2 = plt.subplot(2, 2, 2)
    create_dem_map(ax2)
    
    # Panel (c): Timeline (spans both columns in bottom row)
    ax3 = plt.subplot(2, 1, 2)
    create_timeline(ax3)
    
    # Adjust layout
    plt.tight_layout(pad=2.0)
    
    # Save figure
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"✅ Figure 1 saved to: {OUTPUT_FILE}")
    
    return fig

if __name__ == "__main__":
    # Create figure
    fig = create_figure1()
    plt.close(fig)
    print("✅ Figure 1 (Study Area) created successfully!")

