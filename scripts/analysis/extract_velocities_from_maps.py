#!/usr/bin/env python3
"""
Extract centerline velocities from velocity maps.

This script extracts velocity values along the glacier centerline from
velocity GeoTIFF files. It can work with existing velocity maps or
re-processed maps from SNAP.

Usage:
    python extract_velocities_from_maps.py
"""

import os
import glob
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask
import geopandas as gpd
from pathlib import Path
from shapely.geometry import LineString, Point
import json

# Configuration
VELOCITY_MAPS_DIR = "Didal_Glacier_GIS_Data/Velocity_Maps/"
GLACIER_OUTLINE = "Didal_Glacier_GIS_Data/Glacier_Outline/didal_glacier_rgi_outline.shp"
OUTPUT_DIR = "processed_data/velocity_timeseries/"
METADATA_JSON = "satellite_data/sentinel1/processed/sentinel1_detailed_metadata.json"

def load_glacier_outline(shapefile_path):
    """Load glacier outline shapefile."""
    if not os.path.exists(shapefile_path):
        raise FileNotFoundError(f"Glacier outline not found: {shapefile_path}")
    return gpd.read_file(shapefile_path)

def extract_centerline(glacier_outline):
    """Extract centerline from glacier outline polygon."""
    # Get the first (and likely only) polygon
    geom = glacier_outline.geometry.iloc[0]
    
    # Get boundary coordinates
    coords = list(geom.exterior.coords)
    
    # Create a simple centerline: from first to last point
    # In practice, you might want a more sophisticated centerline extraction
    centerline = LineString([coords[0], coords[-1]])
    
    return centerline

def sample_points_along_line(line, spacing_m=10):
    """Sample points along a line at regular spacing."""
    # Convert spacing from meters to degrees (approximate)
    # 1 degree ≈ 111,000 m at equator
    spacing_deg = spacing_m / 111000.0
    
    # Sample points
    points = []
    distance = 0
    while distance < line.length:
        point = line.interpolate(distance)
        points.append(point)
        distance += spacing_deg
    
    # Add endpoint
    points.append(Point(line.coords[-1]))
    
    return points

def extract_velocity_at_points(velocity_map_path, points, glacier_outline):
    """Extract velocity values at specific points from velocity map."""
    with rasterio.open(velocity_map_path) as src:
        # Ensure CRS match
        if glacier_outline.crs != src.crs:
            glacier_outline = glacier_outline.to_crs(src.crs)
        
        # Extract values
        values = []
        valid_points = []
        
        for point in points:
            # Convert point to raster CRS if needed
            if point.crs != src.crs:
                point_gdf = gpd.GeoDataFrame([1], geometry=[point], crs=point.crs)
                point_gdf = point_gdf.to_crs(src.crs)
                point = point_gdf.geometry.iloc[0]
            
            # Sample value
            row, col = src.index(point.x, point.y)
            
            # Check if within bounds
            if 0 <= row < src.height and 0 <= col < src.width:
                value = src.read(1)[row, col]
                if not np.isnan(value) and value != src.nodata:
                    values.append(value)
                    valid_points.append(point)
        
        return values, valid_points

def extract_centerline_velocity(velocity_map_path, glacier_outline, output_csv):
    """Extract velocity along glacier centerline from velocity map."""
    print(f"\nProcessing: {os.path.basename(velocity_map_path)}")
    
    # Extract centerline
    centerline = extract_centerline(glacier_outline)
    
    # Sample points along centerline
    points = sample_points_along_line(centerline, spacing_m=10)
    print(f"  Sampled {len(points)} points along centerline")
    
    # Extract velocities
    velocities, valid_points = extract_velocity_at_points(
        velocity_map_path, points, glacier_outline
    )
    
    if len(velocities) == 0:
        print(f"  Warning: No valid velocities extracted")
        return None
    
    # Calculate statistics
    mean_velocity = np.mean(velocities)
    std_velocity = np.std(velocities, ddof=1)
    median_velocity = np.median(velocities)
    max_velocity = np.max(velocities)
    min_velocity = np.min(velocities)
    
    print(f"  Mean velocity: {mean_velocity:.2f} m/day")
    print(f"  Std dev: {std_velocity:.2f} m/day")
    print(f"  Range: {min_velocity:.2f} - {max_velocity:.2f} m/day")
    print(f"  Valid points: {len(velocities)}/{len(points)}")
    
    # Extract date from filename
    basename = os.path.basename(velocity_map_path)
    # Expected format: velocity_YYYYMMDD_YYYYMMDD.tif
    parts = basename.replace("velocity_", "").replace(".tif", "").split("_")
    
    if len(parts) >= 2:
        date1 = parts[0]
        date2 = parts[1]
        # Calculate midpoint date
        from datetime import datetime, timedelta
        d1 = datetime.strptime(date1, "%Y%m%d")
        d2 = datetime.strptime(date2, "%Y%m%d")
        midpoint = d1 + (d2 - d1) / 2
        midpoint_date = midpoint.strftime("%Y-%m-%d")
        time_delta = (d2 - d1).days
    else:
        date1 = "unknown"
        date2 = "unknown"
        midpoint_date = "unknown"
        time_delta = None
    
    # Create result
    result = {
        'date1': date1,
        'date2': date2,
        'midpoint_date': midpoint_date,
        'time_delta_days': time_delta,
        'velocity_mean': mean_velocity,
        'velocity_std': std_velocity,
        'velocity_median': median_velocity,
        'velocity_max': max_velocity,
        'velocity_min': min_velocity,
        'n_points': len(velocities),
        'velocity_file': basename
    }
    
    # Save to CSV
    df = pd.DataFrame([result])
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df.to_csv(output_csv, index=False)
    print(f"  Saved to: {output_csv}")
    
    return result

def identify_track_from_dates(date1, date2, metadata):
    """Identify track (orbit) from dates using metadata."""
    acquisitions = metadata.get('acquisitions', [])
    
    for acq in acquisitions:
        if acq['acquisition_date'] == date1:
            return acq['relative_orbit']
        if acq['acquisition_date'] == date2:
            return acq['relative_orbit']
    
    return None

def main():
    """Main execution."""
    print("=" * 80)
    print("EXTRACTING CENTERLINE VELOCITIES FROM VELOCITY MAPS")
    print("=" * 80)
    
    # Load glacier outline
    print(f"\nLoading glacier outline: {GLACIER_OUTLINE}")
    glacier_outline = load_glacier_outline(GLACIER_OUTLINE)
    print(f"  CRS: {glacier_outline.crs}")
    print(f"  Area: {glacier_outline.geometry.area.sum():.6f} degrees²")
    
    # Load metadata (for track identification)
    metadata = None
    if os.path.exists(METADATA_JSON):
        with open(METADATA_JSON, 'r') as f:
            metadata = json.load(f)
        print(f"\nLoaded metadata: {len(metadata['acquisitions'])} acquisitions")
    
    # Find all velocity maps
    velocity_files = sorted(glob.glob(os.path.join(VELOCITY_MAPS_DIR, "*.tif")))
    
    if not velocity_files:
        print(f"\n⚠️  No velocity maps found in {VELOCITY_MAPS_DIR}")
        print("   This script works with existing velocity maps.")
        print("   For re-processed maps, place them in the same directory.")
        return
    
    print(f"\nFound {len(velocity_files)} velocity maps")
    
    # Process each map
    results = []
    for vel_file in velocity_files:
        # Create output filename
        basename = os.path.basename(vel_file).replace(".tif", "")
        output_csv = os.path.join(OUTPUT_DIR, f"{basename}_centerline.csv")
        
        # Extract velocities
        result = extract_centerline_velocity(vel_file, glacier_outline, output_csv)
        if result:
            results.append(result)
    
    # Combine results
    if results:
        df_all = pd.DataFrame(results)
        output_combined = os.path.join(OUTPUT_DIR, "all_centerline_velocities.csv")
        df_all.to_csv(output_combined, index=False)
        
        print(f"\n{'='*80}")
        print("SUMMARY")
        print("=" * 80)
        print(f"Total maps processed: {len(results)}")
        print(f"Combined results saved to: {output_combined}")
        print(f"\nVelocity statistics:")
        print(f"  Mean: {df_all['velocity_mean'].mean():.2f} m/day")
        print(f"  Std dev: {df_all['velocity_mean'].std():.2f} m/day")
        print(f"  Range: {df_all['velocity_mean'].min():.2f} - {df_all['velocity_mean'].max():.2f} m/day")
    
    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
