#!/usr/bin/env python3
"""
Script to filter Planet images that actually cover the Didal Glacier location.
Checks if the glacier coordinates are within each image's footprint.
"""

import json
from shapely.geometry import Point, Polygon

# Glacier location
GLACIER_LAT = 39.0005
GLACIER_LON = 70.7385
glacier_point = Point(GLACIER_LON, GLACIER_LAT)

# Load metadata
metadata_file = "planet_images/metadata.json"

def point_in_polygon(point, polygon_coords):
    """
    Check if a point is within a polygon.
    """
    try:
        # Convert coordinates to Shapely polygon
        coords = polygon_coords[0]  # Get outer ring
        polygon = Polygon(coords)
        return polygon.contains(point)
    except:
        return False

def filter_images_by_location():
    """
    Filter images that actually contain the glacier location.
    """
    with open(metadata_file, 'r') as f:
        items = json.load(f)
    
    print("=" * 60)
    print("Filtering Images by Glacier Location")
    print("=" * 60)
    print(f"Glacier location: {GLACIER_LAT}°N, {GLACIER_LON}°E")
    print(f"Total images in metadata: {len(items)}")
    print()
    
    covering_images = []
    
    for item in items:
        item_id = item.get("id", "unknown")
        geometry = item.get("geometry", {})
        coords = geometry.get("coordinates", [])
        acquired = item.get("properties", {}).get("acquired", "unknown")
        cloud_cover = item.get("properties", {}).get("cloud_cover", "unknown")
        
        # Check if glacier point is within image footprint
        if coords and point_in_polygon(glacier_point, coords):
            covering_images.append({
                "id": item_id,
                "acquired": acquired,
                "cloud_cover": cloud_cover,
                "geometry": geometry
            })
    
    print(f"Images covering glacier location: {len(covering_images)}")
    print("-" * 60)
    
    # Sort by date
    covering_images.sort(key=lambda x: x["acquired"])
    
    print("\nImages covering Didal Glacier:")
    for i, img in enumerate(covering_images, 1):
        print(f"{i}. {img['id']}")
        print(f"   Date: {img['acquired']}")
        print(f"   Cloud cover: {img['cloud_cover']}%")
        print()
    
    # Save filtered list
    filtered_file = "planet_images/glacier_covering_images.json"
    with open(filtered_file, 'w') as f:
        json.dump(covering_images, f, indent=2)
    
    print(f"Filtered list saved to: {filtered_file}")
    
    return covering_images

if __name__ == "__main__":
    try:
        filter_images_by_location()
    except ImportError:
        print("Error: shapely library not installed.")
        print("Install it with: pip install shapely")
        print("\nAlternatively, checking images manually...")
        
        # Fallback: check if coordinates are roughly in range
        with open(metadata_file, 'r') as f:
            items = json.load(f)
        
        print(f"\nChecking {len(items)} images for approximate location match...")
        print(f"Glacier: {GLACIER_LAT}°N, {GLACIER_LON}°E")
        print()
        
        for item in items[:10]:  # Check first 10
            geometry = item.get("geometry", {})
            coords = geometry.get("coordinates", [])
            if coords:
                # Get bounding box
                lons = [c[0] for ring in coords for c in ring]
                lats = [c[1] for ring in coords for c in ring]
                min_lon, max_lon = min(lons), max(lons)
                min_lat, max_lat = min(lats), max(lats)
                
                # Check if glacier is roughly in bounding box
                in_box = (min_lon <= GLACIER_LON <= max_lon and 
                         min_lat <= GLACIER_LAT <= max_lat)
                
                if in_box:
                    print(f"✓ {item.get('id')} - covers glacier area")
                    print(f"  Bbox: {min_lat:.4f}-{max_lat:.4f}°N, {min_lon:.4f}-{max_lon:.4f}°E")

