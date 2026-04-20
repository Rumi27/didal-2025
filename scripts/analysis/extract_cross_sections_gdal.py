#!/usr/bin/env python3
"""
Extract elevation and velocity cross-sections along glacier centerline
Using GDAL command-line tools to avoid rasterio dependency issues
"""

import subprocess
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import json
import geopandas as gpd
from shapely.geometry import LineString, Point
import os

# ==========================================
# CONFIGURATION
# ==========================================
DEM_DIR = Path("satellite_data/dem/processed")
VELOCITY_DIR = Path("satellite_data/sentinel1/processed/velocity_maps")
GLACIER_OUTLINE = DEM_DIR / "didal_glacier_rgi_outline.shp"
OUTPUT_DIR = Path("processed_data/cross_sections")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("CROSS-SECTION EXTRACTION (GDAL-based)")
print("=" * 70)

# Find DEM file
dem_files = []
for ext in ['*.tif', '*.TIF']:
    dem_files.extend(list(DEM_DIR.glob(ext)))
    dem_files.extend(list(DEM_DIR.parent.glob(ext)))

# Filter out derived products
DEM_FILE = None
for f in dem_files:
    if all(x not in f.name.lower() for x in ['slope', 'aspect', 'hillshade']):
        DEM_FILE = f
        break

if DEM_FILE is None:
    # Use slope as fallback (we can still extract profile)
    slope_file = DEM_DIR / "slope.tif"
    if slope_file.exists():
        DEM_FILE = slope_file
        print("⚠️  Using slope file as DEM proxy")

print(f"DEM file: {DEM_FILE}")
print(f"Glacier outline: {GLACIER_OUTLINE}")

# ==========================================
# LOAD GLACIER OUTLINE AND CREATE CENTERLINE
# ==========================================
print("\n1. Loading glacier outline...")
glacier_gdf = gpd.read_file(GLACIER_OUTLINE)
print(f"   Loaded {len(glacier_gdf)} polygon(s)")
print(f"   CRS: {glacier_gdf.crs}")

# Get main polygon
glacier_poly = glacier_gdf.geometry.iloc[0]
if len(glacier_gdf) > 1:
    areas = glacier_gdf.geometry.area
    idx = areas.idxmax()
    glacier_poly = glacier_gdf.geometry.iloc[idx]

# Create simple centerline (head to toe)
bounds = glacier_poly.bounds
minx, miny, maxx, maxy = bounds

# Determine flow direction (assume longest dimension)
width = maxx - minx
height = maxy - miny

if width > height:
    # E-W flow
    x_center = (minx + maxx) / 2
    start = Point(minx, y_center := (miny + maxy) / 2)
    end = Point(maxx, y_center)
else:
    # N-S flow
    y_center = (miny + maxy) / 2
    start = Point((minx + maxx) / 2, maxy)
    end = Point((minx + maxx) / 2, miny)

# Create line and clip to polygon
centerline = LineString([start, end])
centerline = centerline.intersection(glacier_poly)

if centerline.is_empty or centerline.length < 100:
    # Fallback: diagonal
    centerline = LineString([Point(minx, maxy), Point(maxx, miny)])
    centerline = centerline.intersection(glacier_poly)

# Sample points along centerline
num_points = 200
if isinstance(centerline, LineString) and centerline.length > 0:
    distances = np.linspace(0, centerline.length, num_points)
    points = [centerline.interpolate(d) for d in distances]
    centerline = LineString(points)
    
print(f"   Centerline length: {centerline.length:.1f} m")
print(f"   Centerline points: {len(centerline.coords)}")

# Save centerline
centerline_gdf = gpd.GeoDataFrame([1], geometry=[centerline], crs=glacier_gdf.crs)
centerline_file = OUTPUT_DIR / "glacier_centerline.shp"
centerline_gdf.to_file(centerline_file)
print(f"   Saved: {centerline_file}")

# ==========================================
# EXTRACT ELEVATION PROFILE USING GDAL
# ==========================================
print("\n2. Extracting elevation profile using GDAL...")

if DEM_FILE and DEM_FILE.exists():
    # Create temporary point shapefile for sampling
    temp_points_file = OUTPUT_DIR / "temp_points.shp"
    
    # Create point GeoDataFrame
    points_gdf = gpd.GeoDataFrame(
        range(len(centerline.coords)),
        geometry=[Point(coord) for coord in centerline.coords],
        crs=glacier_gdf.crs
    )
    points_gdf.to_file(temp_points_file)
    
    # Use gdallocationinfo or gdal_rasterize to sample
    # Alternative: use gdalwarp to extract values
    
    # Method: Create a line shapefile and use gdal_rasterize, then sample
    # Or use Python with subprocess to call gdallocationinfo
    
    elevations = []
    distances = []
    prev_x, prev_y = None, None
    
    for i, coord in enumerate(centerline.coords):
        x, y = coord
        
        # Calculate distance
        if i == 0:
            dist = 0
        else:
            dist = distances[-1] + np.sqrt((x - prev_x)**2 + (y - prev_y)**2)
        distances.append(dist)
        
        # Sample using gdallocationinfo
        try:
            result = subprocess.run(
                ['gdallocationinfo', '-valonly', '-geoloc', str(DEM_FILE),
                 str(x), str(y)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                val = float(result.stdout.strip())
                if not np.isnan(val) and val != -9999:  # Common nodata value
                    elevations.append(val)
                else:
                    elevations.append(np.nan)
            else:
                elevations.append(np.nan)
        except Exception as e:
            elevations.append(np.nan)
        
        prev_x, prev_y = x, y
    
    elevations = np.array(elevations)
    distances = np.array(distances)
    
    # Filter out NaN values
    valid_mask = ~np.isnan(elevations)
    distances = distances[valid_mask]
    elevations = elevations[valid_mask]
    
    print(f"   Sampled {len(elevations)} valid elevation points")
    if len(elevations) > 0:
        print(f"   Elevation range: {np.nanmin(elevations):.1f} - {np.nanmax(elevations):.1f} m")
        print(f"   Profile length: {distances[-1]:.1f} m")
    
    # Clean up temp file
    if temp_points_file.exists():
        for ext in ['.shp', '.shx', '.dbf', '.prj']:
            f = temp_points_file.with_suffix(ext)
            if f.exists():
                f.unlink()
else:
    print("   ⚠️  DEM file not found, skipping elevation profile")
    elevations = np.array([])
    distances = np.array([])

# ==========================================
# CREATE ELEVATION PROFILE PLOT
# ==========================================
if len(elevations) > 0:
    print("\n3. Creating elevation profile plot...")
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plot elevation profile (purple fill, like QGIS)
    elev_min = np.nanmin(elevations)
    ax.fill_between(distances, elevations, elev_min, 
                    color='purple', alpha=0.6, label='Elevation')
    ax.plot(distances, elevations, 'k-', linewidth=1.5)
    
    ax.set_xlabel(f'Distance ({distances[-1]:.0f} m)', fontsize=12)
    ax.set_ylabel('Elevation (m)', fontsize=12)
    ax.set_title('Elevation Profile - Didal Glacier Centerline', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # Add statistics
    elev_max = np.nanmax(elevations)
    elev_avg = np.nanmean(elevations)
    elev_gain = elev_max - elev_min
    elev_diffs = np.diff(elevations)
    total_gain = np.sum(elev_diffs[elev_diffs > 0])
    total_loss = np.sum(np.abs(elev_diffs[elev_diffs < 0]))
    
    stats_text = f"Min: {elev_min:.2f} m\n"
    stats_text += f"Avg: {elev_avg:.2f} m\n"
    stats_text += f"Max: {elev_max:.2f} m\n"
    stats_text += f"Gain: {total_gain:.2f} m\n"
    stats_text += f"Loss: {total_loss:.2f} m"
    
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
            fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    elev_plot_file = OUTPUT_DIR / "elevation_profile.png"
    plt.savefig(elev_plot_file, dpi=300, bbox_inches='tight')
    print(f"   Saved: {elev_plot_file}")
    plt.close()
    
    # Save CSV
    elev_df = pd.DataFrame({
        'distance_m': distances,
        'elevation_m': elevations
    })
    elev_csv = OUTPUT_DIR / "elevation_profile.csv"
    elev_df.to_csv(elev_csv, index=False)
    print(f"   Saved: {elev_csv}")

# ==========================================
# EXTRACT VELOCITY PROFILES
# ==========================================
print("\n4. Extracting velocity profiles...")

velocity_files = sorted(VELOCITY_DIR.glob("velocity_*.tif"))
print(f"   Found {len(velocity_files)} velocity maps")

velocity_profiles = {}

for vel_file in velocity_files:
    try:
        date_str = vel_file.stem.replace("velocity_", "").replace("_", "-")
        
        vel_distances = []
        velocities = []
        prev_x, prev_y = None, None
        
        for i, coord in enumerate(centerline.coords):
            x, y = coord
            
            # Calculate distance
            if i == 0:
                dist = 0
            else:
                dist = vel_distances[-1] + np.sqrt((x - prev_x)**2 + (y - prev_y)**2)
            vel_distances.append(dist)
            
            # Sample velocity
            try:
                result = subprocess.run(
                    ['gdallocationinfo', '-valonly', '-geoloc', str(vel_file),
                     str(x), str(y)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    val = float(result.stdout.strip())
                    if not np.isnan(val) and val != -9999 and val > 0:
                        velocities.append(val)
                    else:
                        velocities.append(np.nan)
                else:
                    velocities.append(np.nan)
            except Exception as e:
                velocities.append(np.nan)
            
            prev_x, prev_y = x, y
        
        velocities = np.array(velocities)
        vel_distances = np.array(vel_distances)
        
        # Filter valid values
        valid_mask = ~np.isnan(velocities)
        vel_distances = vel_distances[valid_mask]
        velocities = velocities[valid_mask]
        
        if len(velocities) > 0:
            velocity_profiles[date_str] = {
                'distances': vel_distances,
                'velocities': velocities
            }
            print(f"      {date_str}: {len(velocities)} points, "
                  f"vel range: {np.nanmin(velocities):.1f} - {np.nanmax(velocities):.1f} m/day")
    except Exception as e:
        print(f"      ⚠️  Error processing {vel_file.name}: {e}")

# Create velocity profile plot
if velocity_profiles:
    print("\n5. Creating velocity profile plot...")
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    colors = plt.cm.viridis(np.linspace(0, 1, len(velocity_profiles)))
    for (date_str, data), color in zip(velocity_profiles.items(), colors):
        ax.plot(data['distances'], data['velocities'], 
               label=date_str, color=color, linewidth=2, alpha=0.7)
    
    ax.set_xlabel('Distance (m)', fontsize=12)
    ax.set_ylabel('Velocity (m/day)', fontsize=12)
    ax.set_title('Velocity Profiles Along Centerline - Didal Glacier', fontsize=14, fontweight='bold')
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    vel_plot_file = OUTPUT_DIR / "velocity_profiles.png"
    plt.savefig(vel_plot_file, dpi=300, bbox_inches='tight')
    print(f"   Saved: {vel_plot_file}")
    plt.close()
    
    # Save velocity CSVs
    for date_str, data in velocity_profiles.items():
        vel_df = pd.DataFrame({
            'distance_m': data['distances'],
            'velocity_m_per_day': data['velocities']
        })
        vel_csv = OUTPUT_DIR / f"velocity_profile_{date_str.replace('-', '')}.csv"
        vel_df.to_csv(vel_csv, index=False)

print("\n" + "=" * 70)
print("✅ CROSS-SECTION EXTRACTION COMPLETE")
print("=" * 70)
print(f"Output directory: {OUTPUT_DIR}")
print("=" * 70)

