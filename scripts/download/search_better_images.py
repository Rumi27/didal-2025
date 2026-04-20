#!/usr/bin/env python3
"""
Search for better Planet images for key dates:
- Before initial movement (before Sept 19, 2025)
- Second movement (October 25, 2025)
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

# Key dates
INITIAL_MOVEMENT = "2025-09-19"
SECOND_MOVEMENT = "2025-10-25"

# Search query for better images
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
                    "type": "AndFilter",
                    "config": [
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
                            "type": "RangeFilter",
                            "field_name": "cloud_percent",
                            "config": {
                                "lte": 30  # Low cloud cover
                            }
                        }
                    ]
                },
                {
                    "type": "PermissionFilter",
                    "config": ["assets:download", "webtiles:stream"]
                }
            ]
        },
        "item_types": ["PSScene"]
    }

def search_images(start_date, end_date, description):
    """Search for images in date range."""
    print(f"\n{'=' * 70}")
    print(f"Search: {description}")
    print(f"Date range: {start_date} to {end_date}")
    print(f"{'=' * 70}")
    print()
    
    url = "https://api.planet.com/data/v1/quick-search"
    headers = {"Content-Type": "application/json"}
    auth = (PLANET_API_KEY, "")
    
    query = create_search_query(start_date, end_date)
    
    try:
        response = requests.post(url, json=query, headers=headers, auth=auth)
        response.raise_for_status()
        
        data = response.json()
        items = data.get("features", [])
        
        print(f"Found {len(items)} images")
        print()
        
        # Filter and display best images
        good_images = []
        for item in items:
            props = item.get("properties", {})
            cloud_percent = props.get("cloud_percent", 100)
            acquired = props.get("acquired", "")
            item_id = item.get("id", "")
            
            # Check if glacier is in bounds (approximate)
            geometry = item.get("geometry", {})
            if geometry.get("type") == "Polygon":
                coords = geometry.get("coordinates", [[[]]])[0]
                if coords:
                    lons = [c[0] for c in coords]
                    lats = [c[1] for c in coords]
                    center_lon = sum(lons) / len(lons)
                    center_lat = sum(lats) / len(lats)
                    
                    # Check if glacier is near center (within ~0.1 degrees)
                    distance = ((center_lat - GLACIER_LAT)**2 + (center_lon - GLACIER_LON)**2)**0.5
                    
                    if cloud_percent <= 30 and distance < 0.1:
                        good_images.append({
                            "id": item_id,
                            "acquired": acquired,
                            "cloud_percent": cloud_percent,
                            "distance": distance,
                            "center": (center_lat, center_lon)
                        })
        
        # Sort by cloud cover and distance
        good_images.sort(key=lambda x: (x["cloud_percent"], x["distance"]))
        
        print(f"Good images (cloud < 30%, glacier in/near bounds): {len(good_images)}")
        print()
        
        for img in good_images[:10]:  # Show top 10
            date_str = img["acquired"][:10] if img["acquired"] else "unknown"
            print(f"  {date_str}: {img['id']}")
            print(f"    Cloud: {img['cloud_percent']:.1f}%")
            print(f"    Distance from glacier: {img['distance']*111:.1f} km")
            print()
        
        return good_images
        
    except Exception as e:
        print(f"Error: {e}")
        return []

def main():
    """Main function."""
    print("=" * 70)
    print("Search for Better Images - Key Dates")
    print("=" * 70)
    print()
    print("Glacier location: 39.0005°N, 70.7385°E")
    print()
    print("Key dates:")
    print(f"  Initial movement: {INITIAL_MOVEMENT}")
    print(f"  Second movement: {SECOND_MOVEMENT}")
    print()
    
    # Search 1: Before initial movement (early September)
    before_images = search_images(
        "2025-09-01",
        "2025-09-18",  # Day before initial movement
        "Before Initial Movement"
    )
    
    # Search 2: Second movement (October 25)
    oct25_images = search_images(
        "2025-10-24",
        "2025-10-26",
        "Second Movement (October 25)"
    )
    
    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print()
    print(f"Before initial movement: {len(before_images)} good images found")
    print(f"Second movement (Oct 25): {len(oct25_images)} good images found")
    print()
    
    if before_images:
        print("Best 'before' image:")
        best_before = before_images[0]
        print(f"  {best_before['id']} ({best_before['acquired'][:10]})")
        print(f"  Cloud: {best_before['cloud_percent']:.1f}%")
        print()
    
    if oct25_images:
        print("Best October 25 image:")
        best_oct25 = oct25_images[0]
        print(f"  {best_oct25['id']} ({best_oct25['acquired'][:10]})")
        print(f"  Cloud: {best_oct25['cloud_percent']:.1f}%")
        print()
    
    print("Next step: Create orders for the best images using create_september_order.py")

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    main()

