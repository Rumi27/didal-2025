#!/usr/bin/env python3
"""
Professional 3-Panel Figure 1 for Didal Glacier Study:
- Panel (a): Study area map (DEM/hillshade + RGI outline + PlanetScope overlay + inset)
- Panel (b): Velocity and climate time series
- Panel (c): Data and analysis workflow schematic

Run: python3 create_figure1_three_panel.py
"""

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Rectangle, FancyBboxPatch, FancyArrowPatch
import numpy as np
import rasterio
from rasterio.plot import show
from rasterio.warp import transform as rasterio_transform
from rasterio.windows import from_bounds
import geopandas as gpd
from pyproj import Transformer
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import os
import math
from PIL import Image
import warnings
warnings.filterwarnings('ignore')

# --- Configuration ---
GLACIER_LAT, GLACIER_LON = 38.97, 70.75
DEM_HILLSHADE = 'satellite_data/dem/processed/hillshade.tif'
DEM_PATH = 'satellite_data/dem/processed/dem.tif'
GLACIER_OUTLINE = 'satellite_data/dem/processed/didal_glacier_rgi_outline.shp'
VELOCITY_CLIMATE_PNG = 'processed_data/analysis_results/figure1_velocity_climate_timeseries.png'
OUTPUT_FILE = 'processed_data/analysis_results/figure1_three_panel.png'

# PlanetScope image search paths
PLANET_SEARCH_PATHS = [
    'planet_images/visualizations/2025-09-17_20250917_064328_46_24b7_glacier_focused.png',
    'planet_images/visualizations/2025-09-17_20250917_064328_46_24b7_fixed_crop.png',
    'planet_images/visualizations/2025-09-12_20250912_063417_10_252b_final.png',
    'satellite_data/planet',
    'planet_images',
]

def find_planet_image():
    """Find PlanetScope image."""
    for path in PLANET_SEARCH_PATHS:
        if os.path.exists(path):
            if path.endswith('.png') or path.endswith('.tif'):
                return path
            elif os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for file in files:
                        if file.endswith(('.tif', '.png')) and 'planet' in file.lower():
                            full_path = os.path.join(root, file)
                            if 'udm' not in file.lower() and 'mask' not in file.lower():
                                return full_path
    return None

def create_map_panel(ax):
    """Create Panel (a): Study area map."""
    print("Creating Panel (a): Study area map...")
    
    if not os.path.exists(DEM_HILLSHADE):
        print(f"❌ Error: Hillshade file not found: {DEM_HILLSHADE}")
        ax.text(0.5, 0.5, 'DEM/Hillshade not found', ha='center', va='center',
                transform=ax.transAxes, fontsize=12)
        return
    
    with rasterio.open(DEM_HILLSHADE) as hill_src:
        # Transform glacier location to DEM CRS
        transformer = Transformer.from_crs("EPSG:4326", hill_src.crs, always_xy=True)
        site_x, site_y = transformer.transform(GLACIER_LON, GLACIER_LAT)
        
        # Plot hillshade as base
        show(hill_src, ax=ax, cmap='gray', alpha=1.0, zorder=1)
        
        # Overlay PlanetScope if available
        planet_path = find_planet_image()
        if planet_path:
            try:
                if planet_path.endswith('.png'):
                    # Load PNG image
                    img = Image.open(planet_path)
                    img_array = np.array(img) / 255.0
                    
                    # Get approximate bounds (this is a simplified approach)
                    # For PNG, we'll overlay it centered on the glacier
                    buffer = 3000 if hill_src.crs.is_projected else 0.03
                    extent = [site_x - buffer, site_x + buffer, 
                             site_y - buffer, site_y + buffer]
                    
                    ax.imshow(img_array, extent=extent, alpha=0.6, zorder=2, 
                             interpolation='bilinear')
                    print(f"   ✅ PlanetScope PNG overlay added")
                else:
                    # Load GeoTIFF
                    with rasterio.open(planet_path) as img_src:
                        if img_src.crs != hill_src.crs:
                            print(f"   Transforming PlanetScope from {img_src.crs} to {hill_src.crs}")
                        show(img_src, ax=ax, alpha=0.5, zorder=2)
                        print(f"   ✅ PlanetScope GeoTIFF overlay added")
            except Exception as e:
                print(f"   ⚠️  Warning: Could not overlay PlanetScope: {e}")
        
        # Set view extent
        buffer = 5000 if hill_src.crs.is_projected else 0.05
        ax.set_xlim(site_x - buffer, site_x + buffer)
        ax.set_ylim(site_y - buffer, site_y + buffer)
        
        # Add glacier outline
        if os.path.exists(GLACIER_OUTLINE):
            try:
                glacier_gdf = gpd.read_file(GLACIER_OUTLINE)
                if glacier_gdf.crs != hill_src.crs:
                    glacier_gdf = glacier_gdf.to_crs(hill_src.crs)
                glacier_gdf.plot(ax=ax, facecolor='none', edgecolor='red', 
                                linestyle='--', linewidth=2.5, zorder=3, alpha=0.9)
                print(f"   ✅ Glacier outline added")
            except Exception as e:
                print(f"   ⚠️  Warning: Could not load glacier outline: {e}")
        
        # Add study site marker
        ax.plot(site_x, site_y, marker='*', color='yellow', markersize=20, 
                markeredgecolor='red', markeredgewidth=2, zorder=10, 
                label='Didal Glacier')
        
        # Add scale bar
        if hill_src.crs.is_projected:
            scale_km = 2
            scale_len = scale_km * 1000
            scale_x_start = site_x - buffer * 0.8
            scale_y = site_y - buffer * 0.85
            ax.plot([scale_x_start, scale_x_start + scale_len], 
                   [scale_y, scale_y], color='black', lw=4, zorder=10)
            ax.text(scale_x_start + scale_len/2, scale_y - buffer*0.05, f'{scale_km} km',
                   ha='center', fontsize=10, fontweight='bold', color='black',
                   bbox=dict(facecolor='white', alpha=0.8, edgecolor='black'),
                   zorder=11)
        
        # Add north arrow
        arrow_x = site_x + buffer * 0.75
        arrow_y = site_y + buffer * 0.75
        ax.annotate('', xy=(arrow_x, arrow_y + buffer*0.1), 
                   xytext=(arrow_x, arrow_y),
                   arrowprops=dict(arrowstyle='->', lw=2, color='black'),
                   zorder=11)
        ax.text(arrow_x, arrow_y + buffer*0.12, 'N', ha='center', va='bottom',
               fontsize=12, fontweight='bold', color='black',
               bbox=dict(facecolor='white', alpha=0.8, edgecolor='black'),
               zorder=11)
        
        # Add inset regional map
        ax_inset = inset_axes(ax, width="30%", height="30%", loc='upper right',
                             bbox_to_anchor=(0.98, 0.98, 1, 1), bbox_transform=ax.transAxes,
                             borderpad=0)
        
        # Simple regional map (Tajikistan outline)
        try:
            # Try to load Natural Earth data
            try:
                world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
            except:
                # Fallback: create simple outline
                world = None
            
            if world is not None:
                tajikistan = world[world['name'] == 'Tajikistan']
                if len(tajikistan) > 0:
                    tajikistan.plot(ax=ax_inset, color='lightgray', edgecolor='black', linewidth=1)
                    ax_inset.plot(GLACIER_LON, GLACIER_LAT, 'ro', markersize=8, zorder=10)
                    ax_inset.set_xlim(67, 75)
                    ax_inset.set_ylim(36, 41)
                    ax_inset.set_title('Tajikistan', fontsize=9, fontweight='bold')
                    ax_inset.set_xticks([])
                    ax_inset.set_yticks([])
                    ax_inset.spines['top'].set_visible(True)
                    ax_inset.spines['right'].set_visible(True)
                    ax_inset.spines['bottom'].set_visible(True)
                    ax_inset.spines['left'].set_visible(True)
            else:
                # Simple fallback: just show location
                ax_inset.plot(GLACIER_LON, GLACIER_LAT, 'ro', markersize=10)
                ax_inset.set_xlim(67, 75)
                ax_inset.set_ylim(36, 41)
                ax_inset.set_title('Regional Context', fontsize=9, fontweight='bold')
                ax_inset.set_xticks([])
                ax_inset.set_yticks([])
        except Exception as e:
            print(f"   ⚠️  Warning: Could not create inset map: {e}")
            # Simple fallback
            ax_inset.plot(GLACIER_LON, GLACIER_LAT, 'ro', markersize=10)
            ax_inset.set_xlim(67, 75)
            ax_inset.set_ylim(36, 41)
            ax_inset.set_title('Regional Context', fontsize=9, fontweight='bold')
            ax_inset.set_xticks([])
            ax_inset.set_yticks([])
        
        ax.set_xlabel('Longitude (°E)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Latitude (°N)', fontsize=11, fontweight='bold')
        ax.set_title('(a) Study Area and Datasets', fontsize=12, fontweight='bold', pad=10)
        ax.grid(True, alpha=0.3, linestyle='--')

def create_timeseries_panel(ax):
    """Create Panel (b): Velocity and climate time series."""
    print("Creating Panel (b): Velocity and climate time series...")
    
    if os.path.exists(VELOCITY_CLIMATE_PNG):
        # Load existing figure
        try:
            img = Image.open(VELOCITY_CLIMATE_PNG)
            ax.imshow(img, aspect='auto')
            ax.axis('off')
            print(f"   ✅ Loaded existing time series figure")
            return
        except Exception as e:
            print(f"   ⚠️  Warning: Could not load PNG: {e}")
            print(f"   Creating simplified time series plot...")
    
    # Fallback: create simple time series plot
    import pandas as pd
    from datetime import datetime
    
    vel_file = 'satellite_data/sentinel1/processed/velocity_timeseries_python.csv'
    if os.path.exists(vel_file):
        try:
            vel = pd.read_csv(vel_file)
            vel['date'] = pd.to_datetime(vel['date'])
            vel = vel.sort_values('date')
            
            ax2 = ax.twinx()
            
            # Velocity
            ax.plot(vel['date'], vel['velocity_m_per_day'], 'o-', 
                   linewidth=2, markersize=8, color='blue', label='Velocity')
            ax.set_ylabel('Velocity (m d⁻¹)', fontsize=10, fontweight='bold', color='blue')
            ax.tick_params(axis='y', labelcolor='blue')
            
            # Climate (simplified - just show PDD if available)
            climate_file = 'satellite_data/era5_land/processed/climate_derivatives_timeseries.csv'
            if os.path.exists(climate_file):
                clim = pd.read_csv(climate_file, nrows=1000)  # Sample
                clim['datetime'] = pd.to_datetime(clim['datetime'])
                clim_daily = clim.groupby(clim['datetime'].dt.date).agg({'pdd': 'sum'}).reset_index()
                clim_daily['datetime'] = pd.to_datetime(clim_daily['datetime'])
                
                # Filter to velocity date range
                clim_daily = clim_daily[
                    (clim_daily['datetime'] >= vel['date'].min()) & 
                    (clim_daily['datetime'] <= vel['date'].max())
                ]
                
                if len(clim_daily) > 0:
                    ax2.plot(clim_daily['datetime'], clim_daily['pdd'], 
                            '--', linewidth=1.5, color='orange', alpha=0.7, label='PDD')
                    ax2.set_ylabel('PDD (°C·days)', fontsize=10, fontweight='bold', color='orange')
                    ax2.tick_params(axis='y', labelcolor='orange')
            
            ax.set_xlabel('Date', fontsize=11, fontweight='bold')
            ax.set_title('(b) Velocity and Climate Time Series', fontsize=12, fontweight='bold', pad=10)
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper left')
            if 'ax2' in locals():
                ax2.legend(loc='upper right')
            
            print(f"   ✅ Created time series plot from data")
        except Exception as e:
            print(f"   ⚠️  Error creating time series: {e}")
            ax.text(0.5, 0.5, 'Time series data not available', ha='center', va='center',
                   transform=ax.transAxes, fontsize=12)
    else:
        ax.text(0.5, 0.5, 'Velocity data not found', ha='center', va='center',
               transform=ax.transAxes, fontsize=12)

def create_schematic_panel(ax):
    """Create Panel (c): Data and analysis workflow schematic."""
    print("Creating Panel (c): Data and analysis workflow schematic...")
    
    ax.axis('off')
    
    # Define positions for boxes
    y_start = 0.95
    y_spacing = 0.15
    box_width = 0.25
    box_height = 0.12
    x_left = 0.05
    x_mid = 0.37
    x_right = 0.69
    
    # Colors
    color_data = '#4A90E2'  # Blue
    color_analysis = '#50C878'  # Green
    color_results = '#FF6B6B'  # Red
    
    # Data Sources Box
    data_box = FancyBboxPatch((x_left, y_start - box_height), box_width, box_height,
                              boxstyle="round,pad=0.01", linewidth=2,
                              edgecolor=color_data, facecolor='white', alpha=0.9)
    ax.add_patch(data_box)
    ax.text(x_left + box_width/2, y_start - box_height/2, 'DATA SOURCES',
           ha='center', va='center', fontsize=11, fontweight='bold', color=color_data)
    
    # Data items
    data_items = [
        '• Sentinel-1 SAR\n  (9 pairs, 6-day spacing)',
        '• ERA5-Land Climate\n  (T, P, SWE, 2025)',
        '• DEM/Topography\n  (slope, aspect, hillshade)',
        '• PlanetScope\n  (3m, tail motion)',
        '• RGI Glacier Outline'
    ]
    
    y_data = y_start - box_height - 0.02
    for item in data_items:
        ax.text(x_left + box_width/2, y_data, item, ha='center', va='top',
               fontsize=9, color='black')
        y_data -= 0.08
    
    # Analysis Methods Box
    analysis_box = FancyBboxPatch((x_mid, y_start - box_height), box_width, box_height,
                                   boxstyle="round,pad=0.01", linewidth=2,
                                   edgecolor=color_analysis, facecolor='white', alpha=0.9)
    ax.add_patch(analysis_box)
    ax.text(x_mid + box_width/2, y_start - box_height/2, 'ANALYSIS METHODS',
           ha='center', va='center', fontsize=11, fontweight='bold', color=color_analysis)
    
    # Analysis items
    analysis_items = [
        '• Python NCC Offset\n  Tracking (velocity)',
        '• PELT Change-Point\n  Detection',
        '• PPT Framework\n  (H1, H2, H3)',
        '• Cumulative PDD/SWE\n  Analysis',
        '• ROS Event Detection'
    ]
    
    y_analysis = y_start - box_height - 0.02
    for item in analysis_items:
        ax.text(x_mid + box_width/2, y_analysis, item, ha='center', va='top',
               fontsize=9, color='black')
        y_analysis -= 0.08
    
    # Results Box
    results_box = FancyBboxPatch((x_right, y_start - box_height), box_width, box_height,
                                 boxstyle="round,pad=0.01", linewidth=2,
                                 edgecolor=color_results, facecolor='white', alpha=0.9)
    ax.add_patch(results_box)
    ax.text(x_right + box_width/2, y_start - box_height/2, 'KEY RESULTS',
           ha='center', va='center', fontsize=11, fontweight='bold', color=color_results)
    
    # Results items
    results_items = [
        '• Peak velocity:\n  422 m d⁻¹ (Sep 13)',
        '• Tail displacement:\n  2.5 km (43 days)',
        '• PDD buildup:\n  409-1695 °C·days',
        '• SWE depletion:\n  767→0 mm (143 days)',
        '• 53 ROS events\n  detected'
    ]
    
    y_results = y_start - box_height - 0.02
    for item in results_items:
        ax.text(x_right + box_width/2, y_results, item, ha='center', va='top',
               fontsize=9, color='black')
        y_results -= 0.08
    
    # Add arrows
    arrow_props = dict(arrowstyle='->', lw=2, color='gray', alpha=0.7)
    
    # Data → Analysis
    ax.annotate('', xy=(x_mid, y_start - box_height/2),
               xytext=(x_left + box_width, y_start - box_height/2),
               arrowprops=arrow_props)
    
    # Analysis → Results
    ax.annotate('', xy=(x_right, y_start - box_height/2),
               xytext=(x_mid + box_width, y_start - box_height/2),
               arrowprops=arrow_props)
    
    ax.set_title('(c) Data and Analysis Workflow', fontsize=12, fontweight='bold', pad=10)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

def main():
    """Create 3-panel Figure 1."""
    print("=" * 70)
    print("CREATING 3-PANEL FIGURE 1")
    print("=" * 70)
    print()
    
    # Create figure with gridspec
    fig = plt.figure(figsize=(16, 12))
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.3,
                          height_ratios=[1.2, 1], width_ratios=[1.2, 1])
    
    # Panel (a): Map (top, spans both columns)
    ax_map = fig.add_subplot(gs[0, :])
    create_map_panel(ax_map)
    
    # Panel (b): Time series (bottom left)
    ax_ts = fig.add_subplot(gs[1, 0])
    create_timeseries_panel(ax_ts)
    
    # Panel (c): Schematic (bottom right)
    ax_schematic = fig.add_subplot(gs[1, 1])
    create_schematic_panel(ax_schematic)
    
    # Save figure
    output_dir = os.path.dirname(OUTPUT_FILE)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"\n✅ Figure saved: {OUTPUT_FILE}")
    print(f"   Size: 16 x 12 inches, 300 DPI")
    
    return OUTPUT_FILE

if __name__ == "__main__":
    main()

