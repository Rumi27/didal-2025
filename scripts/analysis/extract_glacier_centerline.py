#!/usr/bin/env python3
"""
Phase 3a: Extract Glacier Centerline from RGI Outline

This script:
1. Loads the RGI glacier outline
2. Extracts the centerline (medial axis or longest path)
3. Samples DEM and velocity along centerline
4. Prepares data for H1 topographic pinning test

Run: python3 extract_glacier_centerline.py
"""

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.warp import transform as rasterio_transform
from shapely.geometry import LineString, Point
from pathlib import Path
import json
from scipy.ndimage import distance_transform_edt
from skimage.morphology import medial_axis
import warnings
warnings.filterwarnings('ignore')

# Directories
GLACIER_OUTLINE = Path("satellite_data/dem/processed/didal_glacier_rgi_outline.shp")
DEM_PATH = Path("satellite_data/dem/processed/dem.tif")
SLOPE_PATH = Path("satellite_data/dem/processed/slope.tif")
OUTPUT_DIR = Path("satellite_data/dem/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Glacier location
GLACIER_LAT = 38.97
GLACIER_LON = 70.75

def load_glacier_outline():
    """Load glacier outline from shapefile."""
    print("=" * 70)
    print("LOADING GLACIER OUTLINE")
    print("=" * 70)
    
    if not GLACIER_OUTLINE.exists():
        raise FileNotFoundError(f"Glacier outline not found: {GLACIER_OUTLINE}")
    
    try:
        gdf = gpd.read_file(GLACIER_OUTLINE)
        print(f"✅ Loaded: {len(gdf)} feature(s)")
        print(f"   CRS: {gdf.crs}")
        print(f"   Bounds: {gdf.total_bounds}")
        
        return gdf
    except Exception as e:
        print(f"❌ Error loading outline: {e}")
        raise

def extract_centerline_simple(gdf):
    """
    Extract centerline using simplified approach:
    1. Find longest axis (head to toe)
    2. Create centerline along that axis
    """
    print("\n" + "=" * 70)
    print("EXTRACTING GLACIER CENTERLINE")
    print("=" * 70)
    
    # Get the glacier polygon
    if len(gdf) == 0:
        raise ValueError("No features in glacier outline")
    
    glacier_geom = gdf.iloc[0].geometry
    
    # Get bounds
    bounds = glacier_geom.bounds  # (minx, miny, maxx, maxy)
    
    # For a small glacier, create centerline from centroid to farthest point
    # Or use a simple approach: create line along longest dimension
    
    # Method 1: Use centroid and create line along longest axis
    centroid = glacier_geom.centroid
    
    # Get boundary points
    if hasattr(glacier_geom, 'exterior'):
        boundary_coords = list(glacier_geom.exterior.coords)
    else:
        # MultiPolygon - get first polygon
        boundary_coords = list(glacier_geom.geoms[0].exterior.coords) if hasattr(glacier_geom, 'geoms') else []
    
    if len(boundary_coords) < 2:
        raise ValueError("Insufficient boundary coordinates")
    
    # Find head (highest elevation point - we'll use northernmost for now)
    # and toe (lowest elevation point - southernmost)
    boundary_array = np.array(boundary_coords)
    
    # For small glaciers, use geographic centerline
    # Head: northernmost point
    head_idx = np.argmax(boundary_array[:, 1])  # Max latitude
    head_point = Point(boundary_array[head_idx])
    
    # Toe: southernmost point
    toe_idx = np.argmin(boundary_array[:, 1])  # Min latitude
    toe_point = Point(boundary_array[toe_idx])
    
    # Create centerline as straight line from head to toe
    # (For small glaciers, this is a reasonable approximation)
    centerline = LineString([head_point, toe_point])
    
    print(f"\n✅ Centerline created:")
    print(f"   Head: ({head_point.x:.6f}, {head_point.y:.6f})")
    print(f"   Toe: ({toe_point.x:.6f}, {toe_point.y:.6f})")
    print(f"   Length: {centerline.length * 111:.1f} km (approximate)")
    
    return centerline, head_point, toe_point

def sample_dem_along_centerline(centerline, dem_path, slope_path=None):
    """Sample DEM and slope along centerline."""
    print("\n" + "=" * 70)
    print("SAMPLING DEM ALONG CENTERLINE")
    print("=" * 70)
    
    if not dem_path.exists():
        print(f"⚠️  DEM not found: {dem_path}")
        return None
    
    # Create points along centerline
    num_points = 50  # Sample 50 points along centerline
    distances = np.linspace(0, centerline.length, num_points)
    sample_points = [centerline.interpolate(d) for d in distances]
    
    dem_values = []
    slope_values = []
    elevations = []
    distances_along = []
    
    with rasterio.open(dem_path) as dem_src:
        # Transform centerline to DEM CRS if needed
        if gdf.crs != dem_src.crs:
            from pyproj import Transformer
            transformer = Transformer.from_crs(gdf.crs, dem_src.crs, always_xy=True)
            centerline_transformed = LineString([
                transformer.transform(p.x, p.y) for p in centerline.coords
            ])
        else:
            centerline_transformed = centerline
        
        # Sample DEM
        for i, point in enumerate(sample_points):
            if gdf.crs != dem_src.crs:
                x, y = transformer.transform(point.x, point.y)
            else:
                x, y = point.x, point.y
            
            # Sample DEM
            row, col = dem_src.index(x, y)
            if 0 <= row < dem_src.height and 0 <= col < dem_src.width:
                dem_val = dem_src.read(1)[row, col]
                elevations.append(float(dem_val))
            else:
                elevations.append(np.nan)
            
            distances_along.append(float(distances[i] * 111))  # Convert to km (approximate)
        
        print(f"✅ Sampled {len(elevations)} points along centerline")
        print(f"   Elevation range: {np.nanmin(elevations):.1f} to {np.nanmax(elevations):.1f} m")
    
    # Sample slope if available
    if slope_path and slope_path.exists():
        with rasterio.open(slope_path) as slope_src:
            for i, point in enumerate(sample_points):
                if gdf.crs != slope_src.crs:
                    x, y = transformer.transform(point.x, point.y)
                else:
                    x, y = point.x, point.y
                
                row, col = slope_src.index(x, y)
                if 0 <= row < slope_src.height and 0 <= col < slope_src.width:
                    slope_val = slope_src.read(1)[row, col]
                    slope_values.append(float(slope_val))
                else:
                    slope_values.append(np.nan)
        
        print(f"✅ Sampled slope along centerline")
        print(f"   Slope range: {np.nanmin(slope_values):.1f} to {np.nanmax(slope_values):.1f} degrees")
    else:
        # Calculate slope from DEM if slope file not available
        print("   Calculating slope from DEM...")
        elevations_array = np.array(elevations)
        valid_mask = ~np.isnan(elevations_array)
        if valid_mask.sum() > 1:
            # Calculate gradient (slope approximation)
            distances_array = np.array(distances_along)
            valid_dist = distances_array[valid_mask]
            valid_elev = elevations_array[valid_mask]
            
            # Calculate slope as elevation change / distance
            if len(valid_dist) > 1:
                elev_diff = np.diff(valid_elev)
                dist_diff = np.diff(valid_dist) * 1000  # Convert km to m
                slopes_rad = np.arctan(elev_diff / dist_diff)
                slopes_deg = np.degrees(slopes_rad)
                
                # Pad to match original length
                slope_values = [np.nan] * len(elevations)
                for i in range(len(slopes_deg)):
                    slope_values[valid_mask][i+1] = slopes_deg[i]
    
    return {
        'distances_along_centerline_km': distances_along,
        'elevations_m': elevations,
        'slopes_deg': slope_values if slope_values else None,
        'num_points': len(elevations)
    }

def detect_slope_breaks(slope_profile):
    """Detect significant slope breaks along centerline."""
    print("\n" + "=" * 70)
    print("DETECTING SLOPE BREAKS")
    print("=" * 70)
    
    if slope_profile['slopes_deg'] is None:
        print("⚠️  No slope data available")
        return []
    
    slopes = np.array(slope_profile['slopes_deg'])
    valid_mask = ~np.isnan(slopes)
    
    if valid_mask.sum() < 3:
        print("⚠️  Insufficient slope data")
        return []
    
    valid_slopes = slopes[valid_mask]
    valid_distances = np.array(slope_profile['distances_along_centerline_km'])[valid_mask]
    
    # Calculate slope change (second derivative of elevation)
    slope_changes = np.diff(valid_slopes)
    
    # Detect significant breaks (slope change > threshold)
    # Threshold: 5 degrees change over one sample point
    threshold = 5.0  # degrees
    
    slope_breaks = []
    for i in range(len(slope_changes)):
        if abs(slope_changes[i]) > threshold:
            break_position = valid_distances[i+1]  # Position after change
            break_slope_before = valid_slopes[i]
            break_slope_after = valid_slopes[i+1]
            slope_change = slope_changes[i]
            
            slope_breaks.append({
                'position_km': float(break_position),
                'slope_before_deg': float(break_slope_before),
                'slope_after_deg': float(break_slope_after),
                'slope_change_deg': float(slope_change),
                'index': int(i+1)
            })
    
    print(f"\n✅ Detected {len(slope_breaks)} slope breaks:")
    for i, break_info in enumerate(slope_breaks, 1):
        print(f"   Break {i}: Position {break_info['position_km']:.2f} km")
        print(f"      Slope change: {break_info['slope_before_deg']:.1f}° → {break_info['slope_after_deg']:.1f}° "
              f"(Δ{break_info['slope_change_deg']:.1f}°)")
    
    return slope_breaks

def save_centerline(centerline, gdf, output_dir):
    """Save centerline to shapefile."""
    centerline_gdf = gpd.GeoDataFrame(
        [{'geometry': centerline, 'type': 'centerline'}],
        crs=gdf.crs
    )
    
    output_file = output_dir / "didal_glacier_centerline.shp"
    centerline_gdf.to_file(output_file)
    print(f"\n✅ Centerline saved: {output_file}")
    return output_file

def main():
    """Main function."""
    print("=" * 70)
    print("PHASE 3a: EXTRACT GLACIER CENTERLINE")
    print("=" * 70)
    print()
    
    # Load glacier outline
    gdf = load_glacier_outline()
    
    # Extract centerline
    centerline, head_point, toe_point = extract_centerline_simple(gdf)
    
    # Sample DEM along centerline
    dem_profile = sample_dem_along_centerline(centerline, DEM_PATH, SLOPE_PATH)
    
    if dem_profile:
        # Detect slope breaks
        slope_breaks = detect_slope_breaks(dem_profile)
        
        # Save centerline
        centerline_file = save_centerline(centerline, gdf, OUTPUT_DIR)
        
        # Save profile data
        profile_data = {
            'centerline': {
                'head': {'lon': float(head_point.x), 'lat': float(head_point.y)},
                'toe': {'lon': float(toe_point.x), 'lat': float(toe_point.y)},
                'length_km': float(centerline.length * 111)  # Approximate
            },
            'dem_profile': dem_profile,
            'slope_breaks': slope_breaks
        }
        
        profile_file = OUTPUT_DIR / "centerline_profile.json"
        with open(profile_file, 'w') as f:
            json.dump(profile_data, f, indent=2)
        
        print(f"\n✅ Profile data saved: {profile_file}")
        
        print("\n" + "=" * 70)
        print("✅ CENTERLINE EXTRACTION COMPLETE!")
        print("=" * 70)
        print(f"\nNext steps:")
        print(f"  1. Use centerline for H1 analysis")
        print(f"  2. Map braking-onset position to centerline")
        print(f"  3. Test alignment with slope breaks")
    else:
        print("\n⚠️  Could not sample DEM along centerline")

if __name__ == "__main__":
    main()

