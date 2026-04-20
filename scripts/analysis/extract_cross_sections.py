#!/usr/bin/env python3
"""
Extract elevation and velocity cross-sections along glacier centerline
Similar to QGIS elevation profile tool output
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import rasterio
from rasterio.plot import show
import geopandas as gpd
from shapely.geometry import LineString, Point
from shapely.ops import linemerge
import json

# ==========================================
# CONFIGURATION
# ==========================================
DEM_DIR = Path("satellite_data/dem/processed")
VELOCITY_DIR = Path("satellite_data/sentinel1/processed/velocity_maps")
GLACIER_OUTLINE = DEM_DIR / "didal_glacier_rgi_outline.shp"
OUTPUT_DIR = Path("processed_data/cross_sections")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Find DEM file
DEM_FILES = list(DEM_DIR.glob("*.tif"))
DEM_FILE = None
for f in DEM_FILES:
    if "slope" not in f.name and "aspect" not in f.name and "hillshade" not in f.name:
        DEM_FILE = f
        break

if DEM_FILE is None:
    # Try parent directory
    DEM_PARENT = DEM_DIR.parent
    DEM_FILES = list(DEM_PARENT.glob("*.tif"))
    for f in DEM_FILES:
        if "slope" not in f.name and "aspect" not in f.name and "hillshade" not in f.name:
            DEM_FILE = f
            break

print("=" * 70)
print("CROSS-SECTION EXTRACTION")
print("=" * 70)
print(f"DEM file: {DEM_FILE}")
print(f"Glacier outline: {GLACIER_OUTLINE}")
print(f"Velocity maps: {VELOCITY_DIR}")

# ==========================================
# LOAD DATA
# ==========================================
print("\n1. Loading DEM...")
if DEM_FILE and DEM_FILE.exists():
    dem_src = rasterio.open(DEM_FILE)
    dem_data = dem_src.read(1)
    dem_transform = dem_src.transform
    dem_crs = dem_src.crs
    print(f"   DEM: {dem_data.shape}, CRS: {dem_crs}, Bounds: {dem_src.bounds}")
else:
    print("   ⚠️  DEM file not found! Trying to use slope as proxy...")
    slope_file = DEM_DIR / "slope.tif"
    if slope_file.exists():
        dem_src = rasterio.open(slope_file)
        dem_data = dem_src.read(1)
        dem_transform = dem_src.transform
        dem_crs = dem_src.crs
        print(f"   Using slope file as reference: {dem_data.shape}")
    else:
        raise FileNotFoundError("No DEM or slope file found!")

print("\n2. Loading glacier outline...")
if GLACIER_OUTLINE.exists():
    glacier_gdf = gpd.read_file(GLACIER_OUTLINE)
    glacier_gdf = glacier_gdf.to_crs(dem_crs)
    print(f"   Loaded {len(glacier_gdf)} glacier polygon(s)")
    print(f"   CRS: {glacier_gdf.crs}")
    print(f"   Bounds: {glacier_gdf.total_bounds}")
else:
    raise FileNotFoundError(f"Glacier outline not found: {GLACIER_OUTLINE}")

# ==========================================
# EXTRACT CENTERLINE
# ==========================================
print("\n3. Extracting centerline...")

def extract_centerline_from_polygon(polygon, num_points=100):
    """Extract a centerline from a glacier polygon"""
    # Get the boundary
    boundary = polygon.boundary
    
    # For a simple centerline, we'll:
    # 1. Find the longest axis (head to toe)
    # 2. Create a line along that axis
    
    # Get bounding box
    minx, miny, maxx, maxy = polygon.bounds
    
    # Find the longest dimension
    width = maxx - minx
    height = maxy - miny
    
    if width > height:
        # Glacier is wider than tall - flow is likely N-S
        # Create line from top to bottom
        x_center = (minx + maxx) / 2
        start_point = Point(x_center, maxy)
        end_point = Point(x_center, miny)
    else:
        # Glacier is taller than wide - flow is likely E-W
        # Create line from left to right
        y_center = (miny + maxy) / 2
        start_point = Point(minx, y_center)
        end_point = Point(maxx, y_center)
    
    # Create line
    centerline = LineString([start_point, end_point])
    
    # Clip to polygon
    centerline = centerline.intersection(polygon)
    
    if centerline.is_empty:
        # Fallback: use diagonal
        centerline = LineString([Point(minx, maxy), Point(maxx, miny)])
        centerline = centerline.intersection(polygon)
    
    # Sample points along the line
    if isinstance(centerline, LineString):
        distances = np.linspace(0, centerline.length, num_points)
        points = [centerline.interpolate(d) for d in distances]
        return LineString(points)
    elif isinstance(centerline, (list, tuple)):
        # Multiple segments - merge them
        merged = linemerge(centerline)
        if isinstance(merged, LineString):
            distances = np.linspace(0, merged.length, num_points)
            points = [merged.interpolate(d) for d in distances]
            return LineString(points)
    
    return centerline

# Get the main glacier polygon (largest one)
glacier_poly = glacier_gdf.geometry.iloc[0]
if len(glacier_gdf) > 1:
    # Use the largest polygon
    areas = glacier_gdf.geometry.area
    idx = areas.idxmax()
    glacier_poly = glacier_gdf.geometry.iloc[idx]

centerline = extract_centerline_from_polygon(glacier_poly, num_points=200)
print(f"   Centerline length: {centerline.length:.1f} m")
print(f"   Centerline points: {len(centerline.coords)}")

# Save centerline
centerline_gdf = gpd.GeoDataFrame([1], geometry=[centerline], crs=glacier_gdf.crs)
centerline_file = OUTPUT_DIR / "glacier_centerline.shp"
centerline_gdf.to_file(centerline_file)
print(f"   Saved centerline: {centerline_file}")

# ==========================================
# EXTRACT ELEVATION PROFILE
# ==========================================
print("\n4. Extracting elevation profile...")

def sample_raster_along_line(raster_data, transform, line, crs):
    """Sample raster values along a line"""
    # Convert line to raster CRS if needed
    line_gdf = gpd.GeoDataFrame([1], geometry=[line], crs=crs)
    if line_gdf.crs != dem_src.crs:
        line_gdf = line_gdf.to_crs(dem_src.crs)
        line = line_gdf.geometry.iloc[0]
    
    # Sample points along line
    distances = []
    values = []
    
    for i, coord in enumerate(line.coords):
        x, y = coord
        # Convert to pixel coordinates
        row, col = rasterio.transform.rowcol(transform, x, y)
        
        # Check bounds
        if 0 <= row < raster_data.shape[0] and 0 <= col < raster_data.shape[1]:
            value = raster_data[row, col]
            if not np.isnan(value) and value != raster_data.nodata:
                # Calculate distance along line
                if i == 0:
                    dist = 0
                else:
                    prev_x, prev_y = line.coords[i-1]
                    dist = distances[-1] + np.sqrt((x - prev_x)**2 + (y - prev_y)**2)
                distances.append(dist)
                values.append(value)
    
    return np.array(distances), np.array(values)

elev_distances, elevations = sample_raster_along_line(
    dem_data, dem_transform, centerline, dem_crs
)

print(f"   Sampled {len(elevations)} elevation points")
print(f"   Elevation range: {np.nanmin(elevations):.1f} - {np.nanmax(elevations):.1f} m")
print(f"   Profile length: {elev_distances[-1]:.1f} m")

# ==========================================
# EXTRACT VELOCITY PROFILES
# ==========================================
print("\n5. Extracting velocity profiles...")

velocity_files = sorted(VELOCITY_DIR.glob("velocity_*.tif"))
print(f"   Found {len(velocity_files)} velocity maps")

velocity_profiles = {}

for vel_file in velocity_files:
    try:
        with rasterio.open(vel_file) as vel_src:
            vel_data = vel_src.read(1)
            vel_transform = vel_src.transform
            vel_crs = vel_src.crs
            
            # Sample along centerline
            vel_distances, velocities = sample_raster_along_line(
                vel_data, vel_transform, centerline, vel_crs
            )
            
            # Extract date from filename
            date_str = vel_file.stem.replace("velocity_", "").replace("_", "-")
            velocity_profiles[date_str] = {
                'distances': vel_distances,
                'velocities': velocities
            }
            
            print(f"      {date_str}: {len(velocities)} points, "
                  f"vel range: {np.nanmin(velocities):.1f} - {np.nanmax(velocities):.1f} m/day")
    except Exception as e:
        print(f"      ⚠️  Error processing {vel_file.name}: {e}")

# ==========================================
# CREATE ELEVATION PROFILE PLOT
# ==========================================
print("\n6. Creating elevation profile plot...")

fig, ax = plt.subplots(figsize=(12, 6))

# Plot elevation profile (purple fill, like QGIS)
ax.fill_between(elev_distances, elevations, np.nanmin(elevations), 
                color='purple', alpha=0.6, label='Elevation')
ax.plot(elev_distances, elevations, 'k-', linewidth=1.5)

ax.set_xlabel(f'Distance ({elev_distances[-1]:.0f} m)', fontsize=12)
ax.set_ylabel('Elevation (m)', fontsize=12)
ax.set_title('Elevation Profile - Didal Glacier Centerline', fontsize=14, fontweight='bold')
ax.grid(True, alpha=0.3)
ax.legend()

# Add statistics text box
elev_min = np.nanmin(elevations)
elev_max = np.nanmax(elevations)
elev_avg = np.nanmean(elevations)
elev_gain = elev_max - elev_min
total_gain = np.sum(np.diff(elevations)[np.diff(elevations) > 0])
total_loss = np.sum(np.diff(elevations)[np.diff(elevations) < 0])

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

# ==========================================
# CREATE VELOCITY PROFILE PLOT
# ==========================================
if velocity_profiles:
    print("\n7. Creating velocity profile plot...")
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plot all velocity profiles
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

# ==========================================
# SAVE DATA
# ==========================================
print("\n8. Saving cross-section data...")

# Elevation profile
elev_df = pd.DataFrame({
    'distance_m': elev_distances,
    'elevation_m': elevations
})
elev_csv = OUTPUT_DIR / "elevation_profile.csv"
elev_df.to_csv(elev_csv, index=False)
print(f"   Saved: {elev_csv}")

# Velocity profiles
for date_str, data in velocity_profiles.items():
    vel_df = pd.DataFrame({
        'distance_m': data['distances'],
        'velocity_m_per_day': data['velocities']
    })
    vel_csv = OUTPUT_DIR / f"velocity_profile_{date_str.replace('-', '')}.csv"
    vel_df.to_csv(vel_csv, index=False)
    print(f"   Saved: {vel_csv}")

# Summary statistics
stats = {
    'elevation': {
        'min_m': float(elev_min),
        'max_m': float(elev_max),
        'avg_m': float(elev_avg),
        'total_gain_m': float(total_gain),
        'total_loss_m': float(total_loss),
        'profile_length_m': float(elev_distances[-1])
    },
    'centerline': {
        'length_m': float(centerline.length),
        'num_points': len(centerline.coords)
    },
    'velocity_profiles': {
        date: {
            'num_points': len(data['distances']),
            'vel_min': float(np.nanmin(data['velocities'])),
            'vel_max': float(np.nanmax(data['velocities'])),
            'vel_avg': float(np.nanmean(data['velocities']))
        }
        for date, data in velocity_profiles.items()
    }
}

stats_file = OUTPUT_DIR / "cross_section_statistics.json"
with open(stats_file, 'w') as f:
    json.dump(stats, f, indent=2)
print(f"   Saved: {stats_file}")

print("\n" + "=" * 70)
print("✅ CROSS-SECTION EXTRACTION COMPLETE")
print("=" * 70)
print(f"Output directory: {OUTPUT_DIR}")
print(f"  • Elevation profile: elevation_profile.png, elevation_profile.csv")
print(f"  • Velocity profiles: velocity_profiles.png, velocity_profile_*.csv")
print(f"  • Centerline: glacier_centerline.shp")
print(f"  • Statistics: cross_section_statistics.json")
print("=" * 70)

