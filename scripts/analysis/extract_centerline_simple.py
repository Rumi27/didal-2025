#!/usr/bin/env python3
"""
Simple centerline extraction using only geometry (no rasterio dependency).

For small glaciers, creates a centerline from head to toe.
"""

import geopandas as gpd
import numpy as np
from shapely.geometry import LineString, Point
from pathlib import Path
import json

# Directories
GLACIER_OUTLINE = Path("satellite_data/dem/processed/didal_glacier_rgi_outline.shp")
OUTPUT_DIR = Path("satellite_data/dem/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def extract_centerline():
    """Extract simple centerline from glacier outline."""
    print("=" * 70)
    print("EXTRACTING GLACIER CENTERLINE (SIMPLE METHOD)")
    print("=" * 70)
    
    if not GLACIER_OUTLINE.exists():
        raise FileNotFoundError(f"Glacier outline not found: {GLACIER_OUTLINE}")
    
    # Load outline
    gdf = gpd.read_file(GLACIER_OUTLINE)
    print(f"✅ Loaded glacier outline")
    print(f"   CRS: {gdf.crs}")
    print(f"   Bounds: {gdf.total_bounds}")
    
    # Get geometry
    glacier_geom = gdf.iloc[0].geometry
    
    # Get boundary coordinates
    if hasattr(glacier_geom, 'exterior'):
        boundary_coords = list(glacier_geom.exterior.coords)
    elif hasattr(glacier_geom, 'geoms'):
        boundary_coords = list(glacier_geom.geoms[0].exterior.coords)
    else:
        boundary_coords = list(glacier_geom.coords)
    
    boundary_array = np.array(boundary_coords)
    
    # Find head (northernmost) and toe (southernmost)
    head_idx = np.argmax(boundary_array[:, 1])  # Max latitude
    toe_idx = np.argmin(boundary_array[:, 1])   # Min latitude
    
    head_point = Point(boundary_array[head_idx])
    toe_point = Point(boundary_array[toe_idx])
    
    # Create centerline
    centerline = LineString([head_point, toe_point])
    
    # Calculate approximate length (in km)
    # At 39°N, 1 degree latitude ≈ 111 km, 1 degree longitude ≈ 85 km
    lat_rad = np.radians(head_point.y)
    lon_scale = 111.32 * np.cos(lat_rad)
    lat_scale = 111.32
    
    dx = (toe_point.x - head_point.x) * lon_scale
    dy = (toe_point.y - head_point.y) * lat_scale
    length_km = np.sqrt(dx**2 + dy**2)
    
    print(f"\n✅ Centerline created:")
    print(f"   Head: ({head_point.x:.6f}°E, {head_point.y:.6f}°N)")
    print(f"   Toe: ({toe_point.x:.6f}°E, {toe_point.y:.6f}°N)")
    print(f"   Length: {length_km:.3f} km")
    
    # Save centerline
    centerline_gdf = gpd.GeoDataFrame(
        [{'geometry': centerline, 'type': 'centerline', 'length_km': length_km}],
        crs=gdf.crs
    )
    
    output_file = OUTPUT_DIR / "didal_glacier_centerline.shp"
    centerline_gdf.to_file(output_file)
    print(f"\n✅ Centerline saved: {output_file}")
    
    # Save metadata
    metadata = {
        'head': {'lon': float(head_point.x), 'lat': float(head_point.y)},
        'toe': {'lon': float(toe_point.x), 'lat': float(toe_point.y)},
        'length_km': float(length_km),
        'crs': str(gdf.crs)
    }
    
    metadata_file = OUTPUT_DIR / "centerline_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✅ Metadata saved: {metadata_file}")
    
    return centerline, head_point, toe_point, length_km

if __name__ == "__main__":
    extract_centerline()

