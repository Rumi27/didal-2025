#!/usr/bin/env python3
"""
Script to download Planet.com satellite images using the official Planet SDK.

Requirements:
    pip install planet requests

Usage:
    export PL_API_KEY='your_api_key'
    python download_planet_correct.py
"""

import os
import json
import asyncio
from datetime import datetime
from planet import Auth, Session, DataClient
from planet.data_filter import and_filter, geometry_filter, date_range_filter, range_filter

# Planet.com API configuration
PLANET_API_KEY = "PLAK97848b681d244728a5a7a02e73eb23d5"
PLANET_USER_ID = "d09f3150-dcdb-4644-88d7-9a15f1c1e9b7"

# Study area: Didal Glacier
GLACIER_CENTER_LAT = 39.0005
GLACIER_CENTER_LON = 70.7385
BUFFER = 0.05  # ~5.5 km buffer

# Date range for the event
START_DATE = "2025-09-01"
END_DATE = "2025-11-30"

# Output directory
OUTPUT_DIR = "planet_images"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Set API key and user ID as environment variables
os.environ['PL_API_KEY'] = PLANET_API_KEY
os.environ['PL_USER_ID'] = PLANET_USER_ID


async def search_planet_images():
    """
    Search for Planet images using the Planet Python SDK.
    """
    try:
        # Authenticate with API key and user ID
        auth = Auth.from_key(PLANET_API_KEY)
        session = Session(auth=auth)
        client = DataClient(session)
        
        print(f"Authenticated with User ID: {PLANET_USER_ID}")
        
        # Define AOI geometry
        aoi = {
            "type": "Polygon",
            "coordinates": [[
                [GLACIER_CENTER_LON - BUFFER, GLACIER_CENTER_LAT - BUFFER],
                [GLACIER_CENTER_LON + BUFFER, GLACIER_CENTER_LAT - BUFFER],
                [GLACIER_CENTER_LON + BUFFER, GLACIER_CENTER_LAT + BUFFER],
                [GLACIER_CENTER_LON - BUFFER, GLACIER_CENTER_LAT + BUFFER],
                [GLACIER_CENTER_LON - BUFFER, GLACIER_CENTER_LAT - BUFFER]
            ]]
        }
        
        # Build search filters
        # Convert date strings to datetime objects
        start_dt = datetime.fromisoformat(f"{START_DATE}T00:00:00")
        end_dt = datetime.fromisoformat(f"{END_DATE}T23:59:59")
        
        query = and_filter([
            geometry_filter(aoi),
            date_range_filter("acquired", gte=start_dt, lte=end_dt),
            range_filter("cloud_cover", lte=0.10)
        ])
        
        print("=" * 60)
        print("Planet.com Image Downloader for Didal Glacier")
        print("=" * 60)
        print()
        print(f"Searching for PlanetScope images...")
        print(f"Date range: {START_DATE} to {END_DATE}")
        print(f"AOI center: {GLACIER_CENTER_LAT}°N, {GLACIER_CENTER_LON}°E")
        print()
        
        # Create a saved search first, then run it
        print("Creating saved search...")
        search_name = "Didal_Glacier_Search"
        item_types = ["PSScene"]
        saved_search = await client.create_search(name=search_name, search_filter=query, item_types=item_types)
        search_id = saved_search["id"]
        print(f"Search ID: {search_id}")
        
        # Execute search using run_search with the search ID (returns async generator)
        search_result = client.run_search(search_id)
        
        # Get items from async generator
        items = []
        count = 0
        async for item in search_result:
            items.append(item)
            count += 1
            if count >= 100:  # Limit to 100 items
                break
        
        print(f"Found {len(items)} images")
        print("-" * 60)
        
        if not items:
            print("No images found matching criteria.")
            print("\nPossible reasons:")
            print("  - Date range is in the future (2025)")
            print("  - No images available for this location/date")
            print("  - Cloud cover too restrictive")
            print("  - API key may not have access to requested item types")
            return []
        
        # Display found images
        print("\nFound images:")
        print("-" * 60)
        for i, item in enumerate(items[:10], 1):  # Show first 10
            props = item.get("properties", {})
            acquired = props.get("acquired", "Unknown")
            cloud_cover = props.get("cloud_cover", "Unknown")
            item_id = item.get("id", "Unknown")
            print(f"{i}. ID: {item_id}")
            print(f"   Acquired: {acquired}")
            if isinstance(cloud_cover, (int, float)):
                print(f"   Cloud cover: {cloud_cover:.2%}")
            else:
                print(f"   Cloud cover: {cloud_cover}")
            print()
        
        # Save metadata
        metadata_file = os.path.join(OUTPUT_DIR, "metadata.json")
        with open(metadata_file, "w") as f:
            # Convert items to serializable format
            items_dict = []
            for item in items:
                item_dict = dict(item)
                # Convert any non-serializable objects
                if 'properties' in item_dict:
                    props = item_dict['properties']
                    if isinstance(props, dict):
                        item_dict['properties'] = {k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v 
                                                  for k, v in props.items()}
                items_dict.append(item_dict)
            json.dump(items_dict, f, indent=2, default=str)
        print(f"Metadata saved to {metadata_file}")
        
        return items
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return []


async def main():
    """
    Main function.
    """
    # Search for images
    items = await search_planet_images()
    
    if not items:
        print("\nNote: If you're searching for future dates (2025), images may not be available yet.")
        print("Try adjusting the date range to past dates to test the API connection.")
        return
    
    print(f"\nTotal images found: {len(items)}")
    print("\nTo download images, you'll need to use Planet's Orders API.")
    print("See: https://docs.planet.com/develop/apis/orders/")
    print("\nFor now, image metadata has been saved to planet_images/metadata.json")


if __name__ == "__main__":
    asyncio.run(main())

