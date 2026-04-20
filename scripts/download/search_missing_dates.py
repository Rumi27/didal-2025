#!/usr/bin/env python3
"""
Search for Planet images for missing critical dates:
- Before initial movement (September 17 or earlier)
- Second movement (October 25)
"""

import os
import json
import requests
from datetime import datetime, timedelta

# Planet API configuration
PLANET_API_KEY = "PLAK97848b681d244728a5a7a02e73eb23d5"

# Glacier location
GLACIER_LAT = 39.0005
GLACIER_LON = 70.7385

# Critical dates
CRITICAL_DATES = {
    "before_initial": {
        "name": "Before Initial Movement",
        "date": "2025-09-17",
        "date_range": ("2025-09-15", "2025-09-19")  # ±2 days
    },
    "second_movement": {
        "name": "Second Movement",
        "date": "2025-10-25",
        "date_range": ("2025-10-23", "2025-10-27")  # ±2 days
    }
}

# Search query template
def create_search_query(start_date, end_date):
    """Create search query for date range."""
    return {
        "geometry": {
            "type": "Point",
            "coordinates": [GLACIER_LON, GLACIER_LAT]
        },
        "filter": {
            "type": "AndFilter",
            "config": [
                {
                    "type": "DateRangeFilter",
                    "field_name": "acquired",
                    "config": {
                        "gte": f"{start_date}T00:00:00.000Z",
                        "lte": f"{end_date}T23:59:59.999Z"
                    }
                },
                {
                    "type": "StringInFilter",
                    "field_name": "item_type",
                    "config": ["PSScene"]
                },
                {
                    "type": "StringInFilter",
                    "field_name": "instrument",
                    "config": ["PS2", "PS2.SD", "PSB.SD"]
                },
                {
                    "type": "StringInFilter",
                    "field_name": "publishing_stage",
                    "config": ["standard", "finalized"]
                },
                {
                    "type": "PermissionFilter",
                    "config": ["assets:download", "webtiles:stream"]
                }
            ]
        },
        "item_types": ["PSScene"]
    }

def search_for_date(date_info):
    """Search for images for a specific date."""
    print("=" * 70)
    print(f"Searching for: {date_info['name']}")
    print(f"Target date: {date_info['date']}")
    print(f"Search range: {date_info['date_range'][0]} to {date_info['date_range'][1]}")
    print()
    
    url = "https://api.planet.com/data/v1/quick-search"
    headers = {"Content-Type": "application/json"}
    auth = (PLANET_API_KEY, "")
    
    query = create_search_query(date_info['date_range'][0], date_info['date_range'][1])
    
    try:
        response = requests.post(url, json=query, headers=headers, auth=auth)
        response.raise_for_status()
        
        data = response.json()
        items = data.get("features", [])
        
        print(f"Found {len(items)} images")
        print()
        
        if items:
            # Check which ones cover the glacier location
            good_images = []
            
            for item in items:
                item_id = item.get("id", "")
                props = item.get("properties", {})
                acquired = props.get("acquired", "N/A")
                cloud_cover = props.get("cloud_percent", "N/A")
                
                # Check geometry to see if it covers glacier
                geometry = item.get("geometry", {})
                if geometry.get("type") == "Polygon":
                    coords = geometry.get("coordinates", [])
                    if coords and len(coords) > 0:
                        # Get bounding box
                        lons = [c[0] for ring in coords for c in ring]
                        lats = [c[1] for ring in coords for c in ring]
                        
                        min_lon, max_lon = min(lons), max(lons)
                        min_lat, max_lat = min(lats), max(lats)
                        
                        # Check if glacier is in bounds
                        in_bounds = (min_lon <= GLACIER_LON <= max_lon and 
                                    min_lat <= GLACIER_LAT <= max_lat)
                        
                        if in_bounds:
                            good_images.append({
                                "id": item_id,
                                "acquired": acquired,
                                "cloud_cover": cloud_cover,
                                "bounds": {
                                    "lon": (min_lon, max_lon),
                                    "lat": (min_lat, max_lat)
                                }
                            })
                            print(f"  ✓ {item_id}")
                            print(f"    Acquired: {acquired}")
                            print(f"    Cloud cover: {cloud_cover}%")
                            print(f"    Bounds: {min_lon:.4f}°E to {max_lon:.4f}°E")
                            print(f"             {min_lat:.4f}°N to {max_lat:.4f}°N")
                            print()
            
            return good_images
        else:
            print("No images found in this date range")
            return []
            
    except Exception as e:
        print(f"Error: {e}")
        return []

def main():
    """Main function."""
    print("=" * 70)
    print("Search for Missing Critical Date Images")
    print("=" * 70)
    print()
    print(f"Glacier location: {GLACIER_LAT:.6f}°N, {GLACIER_LON:.6f}°E")
    print()
    
    all_results = {}
    
    for key, date_info in CRITICAL_DATES.items():
        results = search_for_date(date_info)
        all_results[key] = results
        print()
    
    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print()
    
    for key, date_info in CRITICAL_DATES.items():
        results = all_results[key]
        print(f"{date_info['name']} ({date_info['date']}):")
        if results:
            print(f"  ✓ Found {len(results)} images covering glacier")
            for img in results:
                print(f"    - {img['id']} (cloud: {img['cloud_cover']}%)")
        else:
            print(f"  ✗ No images found covering glacier location")
        print()
    
    # Save results
    results_file = "planet_images/missing_dates_search_results.json"
    os.makedirs("planet_images", exist_ok=True)
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"✓ Saved results to: {results_file}")
    print()
    print("Next steps:")
    print("1. Review the search results")
    print("2. Create orders for the best images (lowest cloud cover)")
    print("3. Download and process the images")

if __name__ == "__main__":
    main()

