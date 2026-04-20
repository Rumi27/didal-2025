#!/usr/bin/env python3
"""
Check the actual geographic location of downloaded Planet images.
"""

import json
import glob
import os
import rasterio

# Expected location
EXPECTED_LAT = 38.97  # or 39.0005
EXPECTED_LON = 70.75  # or 70.7385

print("=" * 60)
print("Checking Planet Image Locations")
print("=" * 60)
print(f"\nExpected location: {EXPECTED_LAT}°N, {EXPECTED_LON}°E")
print("(Didal Glacier: 38.97°N, 70.75°E or 39.0005°N, 70.7385°E)")
print()

# Check metadata files
metadata_files = glob.glob("planet_images/newa_planet/*_metadata.json")

for metadata_file in sorted(metadata_files):
    print(f"\n{os.path.basename(metadata_file)}")
    print("-" * 60)
    
    with open(metadata_file, 'r') as f:
        data = json.load(f)
    
    if 'geometry' in data and 'coordinates' in data['geometry']:
        coords = data['geometry']['coordinates'][0][0]  # First polygon, first point
        print(f"  Coordinates (first point): {coords[1]:.6f}°N, {coords[0]:.6f}°E")
        
        # Calculate center of bounding box
        lons = [c[0] for c in data['geometry']['coordinates'][0]]
        lats = [c[1] for c in data['geometry']['coordinates'][0]]
        center_lon = sum(lons) / len(lons)
        center_lat = sum(lats) / len(lats)
        print(f"  Center: {center_lat:.6f}°N, {center_lon:.6f}°E")
        
        # Check if it's near expected location
        lat_diff = abs(center_lat - EXPECTED_LAT)
        lon_diff = abs(center_lon - EXPECTED_LON)
        distance_km = ((lat_diff * 111)**2 + (lon_diff * 111 * abs(center_lat / 90))**2)**0.5
        print(f"  Distance from expected: {distance_km:.2f} km")
        
        if distance_km > 10:
            print(f"  ⚠️  WARNING: Image is {distance_km:.1f} km away from expected location!")
    
    if 'properties' in data:
        props = data['properties']
        print(f"  Acquired: {props.get('acquired', 'N/A')}")
        print(f"  Cloud cover: {props.get('cloud_percent', 'N/A')}%")
        print(f"  Resolution: {props.get('gsd', 'N/A')} m")
    
    # Also check the actual TIFF file bounds
    tif_file = metadata_file.replace('_metadata.json', '_3B_AnalyticMS_SR.tif')
    if os.path.exists(tif_file):
        try:
            with rasterio.open(tif_file) as src:
                bounds = src.bounds
                center_lat_tif = (bounds.top + bounds.bottom) / 2
                center_lon_tif = (bounds.left + bounds.right) / 2
                print(f"  TIFF bounds center: {center_lat_tif:.6f}°N, {center_lon_tif:.6f}°E")
                print(f"  TIFF bounds: {bounds.left:.6f}°E to {bounds.right:.6f}°E, "
                      f"{bounds.bottom:.6f}°N to {bounds.top:.6f}°N")
        except Exception as e:
            print(f"  Could not read TIFF: {e}")

print("\n" + "=" * 60)
print("Summary")
print("=" * 60)
print("\nIf images are far from expected location, they may be:")
print("1. From a different area (wrong download)")
print("2. From the correct area but covering a different extent")
print("3. The coordinates in the screenshot may be slightly different")

