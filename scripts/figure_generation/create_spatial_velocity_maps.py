#!/usr/bin/env python3
"""
Create spatial velocity maps for representative epochs.
Addresses reviewer concern: "No spatial velocity maps presented"

Generates multi-panel figure showing:
- Velocity magnitude maps
- Glacier outline, Ω mask, and stable-ground mask overlays
- Quality (PCR) maps
- Representative epochs (best, typical, early surge)
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import colors as mcolors
from matplotlib.patches import Rectangle
from osgeo import gdal, osr
import geopandas as gpd
from pathlib import Path
import pandas as pd

# Paths
BASE_DIR = Path("/home/chunlab/Desktop/writing_paper/tajikistan/Didal_Glacier")
VEL_DIR = BASE_DIR / "satellite_data/sentinel1/processed/velocity_maps"
STATS_FILE = BASE_DIR / "processed_data/stable_ground_debiasing/pairwise_stable_ground_stats.csv"
GLACIER_SHP = BASE_DIR / "Didal_Glacier_GIS_Data/Glacier_Outline/didal_glacier_manual.shp"
STABLE_SHP = BASE_DIR / "stable_ground_mask.shp"
OUTPUT_DIR = BASE_DIR / "figures"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Font sizes (matching other figures)
FONT_SIZE_LABEL = 14
FONT_SIZE_TITLE = 16
FONT_SIZE_TICK = 12
FONT_SIZE_COLORBAR = 12

def read_geotiff(filepath):
    """Read GeoTIFF and return data array + geo info."""
    ds = gdal.Open(str(filepath))
    if ds is None:
        raise FileNotFoundError(f"Cannot open {filepath}")
    
    band = ds.GetRasterBand(1)
    data = band.ReadAsArray()
    nodata = band.GetNoDataValue()
    
    # Mask nodata
    if nodata is not None:
        data = np.ma.masked_equal(data, nodata)
    else:
        data = np.ma.masked_equal(data, -9999)
    
    # Get geotransform
    gt = ds.GetGeoTransform()
    proj = ds.GetProjection()
    
    # Create extent
    xmin = gt[0]
    ymax = gt[3]
    xmax = xmin + gt[1] * ds.RasterXSize
    ymin = ymax + gt[5] * ds.RasterYSize
    extent = [xmin, xmax, ymin, ymax]
    
    ds = None
    return data, extent, proj

def select_representative_epochs(stats_df, available_vel_files):
    """
    Select 3 representative epochs from available velocity files:
    1. Best quality non-saturated (highest PCR)
    2. Typical surge phase (mid-range)
    3. Early surge phase
    """
    # Extract available dates from filenames
    available_dates = set()
    for vf in available_vel_files:
        # filename pattern: velocity_YYYYMMDD_YYYYMMDD.tif (date1 repeated)
        parts = vf.stem.split('_')
        if len(parts) >= 2:
            available_dates.add(pd.to_datetime(parts[1]))
    
    print(f"Available velocity files for dates: {sorted(available_dates)}")
    
    # Filter to valid pairs with available velocity files
    valid = stats_df[
        (stats_df['stable_ground_status'] == 'ok') &
        (stats_df['vindex_corr_median'] > 0.05) &
        (stats_df['date1'].isin(available_dates))
    ].copy()
    
    if len(valid) == 0:
        print("WARNING: No valid pairs with velocity files found")
        # Try any available
        valid = stats_df[stats_df['date1'].isin(available_dates)].copy()
    
    if len(valid) == 0:
        print("ERROR: No matching pairs found!")
        return []
    
    # Sort by PCR quality
    valid = valid.sort_values('vindex_corr_median', ascending=False)
    print(f"Found {len(valid)} valid pairs with velocity files")
    
    # Epoch selection
    epochs = []
    
    # 1. Best quality (highest PCR)
    best_idx = valid.iloc[0]
    epochs.append({
        'date1': best_idx['date1'],
        'date2': best_idx['date2'],
        'label': f"Best quality ({best_idx['date1'].strftime('%Y-%m-%d')} to {best_idx['date2'].strftime('%Y-%m-%d')})",
        'vindex': best_idx['vindex_m_per_day_debiased'],
        'pcr': best_idx['vindex_corr_median'],
        'letter': 'b'
    })
    
    # 2. Mid-range (typical) if available
    if len(valid) >= 3:
        mid_idx = valid.iloc[len(valid)//2]
        epochs.append({
            'date1': mid_idx['date1'],
            'date2': mid_idx['date2'],
            'label': f"Typical ({mid_idx['date1'].strftime('%Y-%m-%d')} to {mid_idx['date2'].strftime('%Y-%m-%d')})",
            'vindex': mid_idx['vindex_m_per_day_debiased'],
            'pcr': mid_idx['vindex_corr_median'],
            'letter': 'c'
        })
    
    # 3. Early surge phase (earliest valid) if different from above
    if len(valid) >= 2:
        early_idx = valid.iloc[-1]  # Last in sorted list (lowest PCR but still valid)
        if early_idx['date1'] != best_idx['date1']:
            epochs.append({
                'date1': early_idx['date1'],
                'date2': early_idx['date2'],
                'label': f"Early surge ({early_idx['date1'].strftime('%Y-%m-%d')} to {early_idx['date2'].strftime('%Y-%m-%d')})",
                'vindex': early_idx['vindex_m_per_day_debiased'],
                'pcr': early_idx['vindex_corr_median'],
                'letter': 'd' if len(epochs) == 2 else 'c'
            })
    
    return epochs

def create_spatial_map_panel(ax, data, extent, glacier_gdf, stable_gdf, 
                             title, vmin, vmax, cmap='viridis', show_colorbar=True):
    """Create a single spatial map panel with overlays."""
    
    # Plot velocity data
    im = ax.imshow(data, extent=extent, origin='upper', 
                   cmap=cmap, vmin=vmin, vmax=vmax,
                   interpolation='nearest', alpha=0.9)
    
    # Overlay masks
    if glacier_gdf is not None:
        glacier_gdf.boundary.plot(ax=ax, color='red', linewidth=2, label='Glacier outline')
    
    if stable_gdf is not None:
        stable_gdf.boundary.plot(ax=ax, color='cyan', linewidth=1.5, 
                                linestyle='--', label='Stable ground', alpha=0.7)
    
    # Formatting
    ax.set_xlabel('Longitude (°E)', fontsize=FONT_SIZE_LABEL)
    ax.set_ylabel('Latitude (°N)', fontsize=FONT_SIZE_LABEL)
    ax.set_title(title, fontsize=FONT_SIZE_TITLE, pad=10)
    ax.tick_params(labelsize=FONT_SIZE_TICK)
    ax.set_aspect('equal')
    
    # Grid
    ax.grid(True, alpha=0.3, linestyle=':', linewidth=0.5)
    
    # Colorbar
    if show_colorbar:
        cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('Velocity (m d$^{-1}$)', fontsize=FONT_SIZE_COLORBAR)
        cbar.ax.tick_params(labelsize=FONT_SIZE_TICK)
    
    return im

def create_mask_overview_panel(ax, extent, glacier_gdf, stable_gdf):
    """Create a panel showing mask geometry overview."""
    
    # Background (blank)
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    ax.set_facecolor('#f0f0f0')
    
    # Plot masks
    if glacier_gdf is not None:
        glacier_gdf.plot(ax=ax, facecolor='lightcoral', edgecolor='red', 
                        linewidth=2, alpha=0.5, label='Glacier (Ω)')
    
    if stable_gdf is not None:
        stable_gdf.plot(ax=ax, facecolor='lightblue', edgecolor='cyan', 
                       linewidth=1.5, linestyle='--', alpha=0.4, 
                       label='Stable ground')
    
    # Formatting
    ax.set_xlabel('Longitude (°E)', fontsize=FONT_SIZE_LABEL)
    ax.set_ylabel('Latitude (°N)', fontsize=FONT_SIZE_LABEL)
    ax.set_title('(a) Sampling regions', fontsize=FONT_SIZE_TITLE, pad=10)
    ax.tick_params(labelsize=FONT_SIZE_TICK)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3, linestyle=':', linewidth=0.5)
    ax.legend(loc='upper right', fontsize=FONT_SIZE_TICK-1, framealpha=0.9)

def main():
    print("Creating spatial velocity maps...")
    
    # Load stats
    stats_df = pd.read_csv(STATS_FILE)
    stats_df['date1'] = pd.to_datetime(stats_df['date1'])
    stats_df['date2'] = pd.to_datetime(stats_df['date2'])
    
    # Load shapefiles
    try:
        glacier_gdf = gpd.read_file(GLACIER_SHP)
        print(f"Loaded glacier outline: {len(glacier_gdf)} features, CRS: {glacier_gdf.crs}")
    except Exception as e:
        print(f"WARNING: Cannot load glacier shapefile: {e}")
        glacier_gdf = None
    
    try:
        stable_gdf = gpd.read_file(STABLE_SHP)
        print(f"Loaded stable ground: {len(stable_gdf)} features, CRS: {stable_gdf.crs}")
    except Exception as e:
        print(f"WARNING: Cannot load stable ground shapefile: {e}")
        stable_gdf = None
    
    # Get available velocity files
    vel_files = sorted(VEL_DIR.glob("velocity_*.tif"))
    if len(vel_files) == 0:
        print("ERROR: No velocity GeoTIFF files found!")
        return
    
    print(f"Found {len(vel_files)} velocity GeoTIFF files")
    
    # Select representative epochs
    epochs = select_representative_epochs(stats_df, vel_files)
    if len(epochs) == 0:
        print("ERROR: No valid epochs selected!")
        return
    
    print(f"\nSelected {len(epochs)} representative epochs:")
    for ep in epochs:
        print(f"  {ep['label']}: Vindex={ep['vindex']:.1f} m/d, PCR={ep['pcr']:.3f}")
    
    # Create figure: 1 mask overview + N velocity maps
    n_panels = len(epochs) + 1
    fig, axes = plt.subplots(1, n_panels, figsize=(5*n_panels, 5.5))
    if n_panels == 1:
        axes = [axes]
    
    # Panel (a): Mask overview
    print("\nCreating mask overview panel...")
    
    # Use extent from first available velocity raster
    _, extent, _ = read_geotiff(vel_files[0])
    
    create_mask_overview_panel(axes[0], extent, glacier_gdf, stable_gdf)
    
    # Panels (b), (c), (d): Velocity maps
    for idx, epoch in enumerate(epochs):
        ax = axes[idx + 1]
        
        # Find matching velocity file (files use date1 twice in name)
        date1_str = epoch['date1'].strftime('%Y%m%d')
        vel_file = VEL_DIR / f"velocity_{date1_str}_{date1_str}.tif"
        
        if not vel_file.exists():
            print(f"WARNING: Velocity file not found: {vel_file}")
            print(f"  Expected: velocity_{date1_str}_{date1_str}.tif")
            ax.text(0.5, 0.5, f"Data not available\n{date1_str}",
                   ha='center', va='center', transform=ax.transAxes,
                   fontsize=FONT_SIZE_LABEL)
            ax.set_aspect('equal')
            continue
        
        print(f"Reading: {vel_file.name}")
        data, extent, proj = read_geotiff(vel_file)
        
        # Reproject shapefiles to match raster CRS if needed
        raster_crs = osr.SpatialReference(wkt=proj).GetAttrValue('AUTHORITY', 1)
        if glacier_gdf is not None and str(glacier_gdf.crs.to_epsg()) != raster_crs:
            glacier_gdf_proj = glacier_gdf.to_crs(epsg=int(raster_crs))
        else:
            glacier_gdf_proj = glacier_gdf
        
        if stable_gdf is not None and str(stable_gdf.crs.to_epsg()) != raster_crs:
            stable_gdf_proj = stable_gdf.to_crs(epsg=int(raster_crs))
        else:
            stable_gdf_proj = stable_gdf
        
        # Create panel
        title = (f"({epoch['letter']}) {epoch['date1'].strftime('%b %d')}–{epoch['date2'].strftime('%b %d')}\n"
                f"Vindex={epoch['vindex']:.1f} m d$^{{-1}}$, PCR={epoch['pcr']:.3f}")
        
        # Use consistent color scale
        vmin, vmax = 0, 300  # m/d
        
        create_spatial_map_panel(
            ax, data, extent, glacier_gdf_proj, stable_gdf_proj,
            title, vmin, vmax, cmap='plasma', show_colorbar=True
        )
    
    plt.tight_layout()
    
    # Save figure
    output_file = OUTPUT_DIR / "fig_spatial_velocity_maps.pdf"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Saved: {output_file}")
    
    output_file_png = OUTPUT_DIR / "fig_spatial_velocity_maps.png"
    plt.savefig(output_file_png, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file_png}")
    
    plt.close()
    
    # Create summary table
    summary = pd.DataFrame(epochs)
    summary_file = OUTPUT_DIR / "spatial_maps_summary.csv"
    summary.to_csv(summary_file, index=False)
    print(f"✓ Saved: {summary_file}")
    
    print("\n=== Spatial velocity maps generation complete ===")
    print(f"Output files:")
    print(f"  - {output_file}")
    print(f"  - {output_file_png}")
    print(f"  - {summary_file}")

if __name__ == "__main__":
    main()
