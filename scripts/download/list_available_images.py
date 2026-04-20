#!/usr/bin/env python3
"""
List available Planet images for key dates without downloading.
Shows what images are available for download.
"""

import os
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from planet import Auth, Session, DataClient
from planet.data_filter import and_filter, geometry_filter, date_range_filter, range_filter

# Planet.com API configuration
PLANET_API_KEY = "PLAK97848b681d244728a5a7a02e73eb23d5"
os.environ['PL_API_KEY'] = PLANET_API_KEY

# Key event dates
KEY_DATES = {
    "Initial Movement": "2025-09-19",
    "Second Movement": "2025-10-25",
    "Continued Movement": "2025-11-01",
    "Earthquake Day": "2025-11-03",
}

# Load AOI
GEOJSON_FILE = "planet_images/from_website/feature (3).geojson"


def load_aoi():
    with open(GEOJSON_FILE, 'r') as f:
        geojson = json.load(f)
    return geojson.get("geometry", {})


async def search_for_date(auth, aoi, event_name, target_date, days_buffer=3):
    client = DataClient(Session(auth=auth))
    
    target_dt = datetime.fromisoformat(target_date)
    start_date = target_dt - timedelta(days=days_buffer)
    end_date = target_dt + timedelta(days=days_buffer)
    
    query = and_filter([
        geometry_filter(aoi),
        date_range_filter("acquired", gte=start_date, lte=end_date),
        range_filter("cloud_cover", lte=0.20)
    ])
    
    search_name = f"Didal_{event_name.replace(' ', '_')}"
    saved_search = await client.create_search(name=search_name, search_filter=query, item_types=["PSScene"])
    search_id = saved_search["id"]
    
    search_result = client.run_search(search_id)
    
    items = []
    async for item in search_result:
        items.append(item)
        if len(items) >= 20:
            break
    
    return items


async def main():
    auth = Auth.from_key(PLANET_API_KEY)
    aoi = load_aoi()
    
    print("=" * 60)
    print("Available Planet Images for Key Event Dates")
    print("=" * 60)
    print(f"AOI: Loaded from {GEOJSON_FILE}")
    print()
    
    all_images = {}
    
    for event_name, target_date in KEY_DATES.items():
        print(f"{event_name} ({target_date}):")
        print("-" * 60)
        
        items = await search_for_date(auth, aoi, event_name, target_date)
        
        if items:
            print(f"  Found {len(items)} images:")
            for item in items:
                item_id = item.get("id")
                props = item.get("properties", {})
                acquired = props.get("acquired", props.get("datetime", "unknown"))
                cloud = props.get("cloud_cover", props.get("eo:cloud_cover", "unknown"))
                
                date_str = acquired[:10] if isinstance(acquired, str) else str(acquired)[:10]
                
                print(f"    • {item_id}")
                print(f"      Date: {date_str}, Cloud: {cloud}%")
                
                if event_name not in all_images:
                    all_images[event_name] = []
                all_images[event_name].append({
                    "id": item_id,
                    "date": date_str,
                    "cloud_cover": cloud
                })
        else:
            print(f"  No images found")
        print()
    
    # Save summary
    summary_file = "planet_images/from_website/available_images_summary.json"
    with open(summary_file, 'w') as f:
        json.dump({
            "key_dates": KEY_DATES,
            "available_images": all_images,
            "total_images": sum(len(imgs) for imgs in all_images.values())
        }, f, indent=2)
    
    print("=" * 60)
    print("Summary saved to: available_images_summary.json")
    print(f"Total images available: {sum(len(imgs) for imgs in all_images.values())}")
    print()
    print("To download these images:")
    print("  1. Use Planet Explorer website with the image IDs")
    print("  2. Or use the download_additional_planet_images.py script")
    print("  3. Or create orders via Planet Orders API")


if __name__ == "__main__":
    asyncio.run(main())

