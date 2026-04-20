#!/usr/bin/env python3
"""
Download additional Planet images for key event dates using the same AOI
as the images in from_website folder.

This script will:
1. Read the AOI from the existing GeoJSON files
2. Search for images on key event dates
3. Create orders to download full-resolution images
"""

import os
import json
import asyncio
from pathlib import Path
from planet import Auth, Session, DataClient, OrdersClient
from planet.data_filter import and_filter, geometry_filter, date_range_filter, range_filter
from planet.order_request import build_request, product

# Planet.com API configuration
PLANET_API_KEY = "PLAK97848b681d244728a5a7a02e73eb23d5"
PLANET_USER_ID = "d09f3150-dcdb-4644-88d7-9a15f1c1e9b7"

os.environ['PL_API_KEY'] = PLANET_API_KEY

# Key event dates
KEY_DATES = {
    "initial_movement": "2025-09-19",
    "second_movement": "2025-10-25",
    "continued_movement_1": "2025-11-01",
    "continued_movement_2": "2025-11-02",
    "earthquake_day": "2025-11-03",
}

# Output directory
OUTPUT_DIR = "planet_images/from_website"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load existing AOI from GeoJSON
GEOJSON_FILE = "planet_images/from_website/feature (3).geojson"


def load_aoi_from_geojson():
    """
    Load AOI geometry from existing GeoJSON file.
    """
    with open(GEOJSON_FILE, 'r') as f:
        geojson = json.load(f)
    
    return geojson.get("geometry", {})


async def search_images_for_date(auth, aoi, target_date, days_buffer=2):
    """
    Search for images on or near a target date.
    """
    client = DataClient(Session(auth=auth))
    
    # Date range: target date ± buffer days
    from datetime import datetime, timedelta
    target_dt = datetime.fromisoformat(target_date)
    start_date = target_dt - timedelta(days=days_buffer)
    end_date = target_dt + timedelta(days=days_buffer)
    
    # Build search filters
    query = and_filter([
        geometry_filter(aoi),
        date_range_filter("acquired", gte=start_date, lte=end_date),
        range_filter("cloud_cover", lte=0.20)  # Max 20% cloud cover
    ])
    
    # Create search
    search_name = f"Didal_Glacier_{target_date}"
    saved_search = await client.create_search(name=search_name, search_filter=query, item_types=["PSScene"])
    search_id = saved_search["id"]
    
    # Run search
    search_result = client.run_search(search_id)
    
    # Collect items
    items = []
    async for item in search_result:
        items.append(item)
        if len(items) >= 10:  # Limit to 10 per date
            break
    
    return items


async def download_images_for_dates():
    """
    Download images for key event dates.
    """
    # Authenticate
    auth = Auth.from_key(PLANET_API_KEY)
    session = Session(auth=auth)
    orders_client = OrdersClient(session)
    
    # Load AOI
    aoi = load_aoi_from_geojson()
    print("=" * 60)
    print("Downloading Additional Planet Images for Key Dates")
    print("=" * 60)
    print(f"AOI loaded from: {GEOJSON_FILE}")
    print()
    
    all_image_ids = []
    
    # Search for each key date
    for event_name, target_date in KEY_DATES.items():
        print(f"Searching for {event_name} ({target_date})...")
        
        items = await search_images_for_date(auth, aoi, target_date)
        
        if items:
            print(f"  Found {len(items)} images")
            for item in items:
                item_id = item.get("id")
                acquired = item.get("properties", {}).get("acquired", "unknown")
                cloud = item.get("properties", {}).get("cloud_cover", "unknown")
                print(f"    - {item_id} ({acquired[:10]}, cloud: {cloud}%)")
                all_image_ids.append(item_id)
        else:
            print(f"  No images found for {target_date}")
        print()
    
    if not all_image_ids:
        print("No images found for any key dates.")
        return
    
    # Remove duplicates
    all_image_ids = list(set(all_image_ids))
    
    print(f"Total unique images to download: {len(all_image_ids)}")
    print(f"Image IDs: {', '.join(all_image_ids[:5])}..." if len(all_image_ids) > 5 else f"Image IDs: {', '.join(all_image_ids)}")
    print()
    
    # Save list of image IDs
    ids_file = os.path.join(OUTPUT_DIR, "image_ids_to_download.json")
    with open(ids_file, 'w') as f:
        json.dump({
            "image_ids": all_image_ids,
            "dates": KEY_DATES,
            "total": len(all_image_ids)
        }, f, indent=2)
    print(f"Image IDs saved to: {ids_file}")
    print()
    
    # Ask for confirmation (skip if running non-interactively)
    try:
        confirm = input("Create order to download these images? (y/n): ").lower().strip()
    except EOFError:
        print("Running non-interactively. To download, run with --download flag or edit script.")
        print("Image IDs have been saved. You can create the order manually via Planet website.")
        return
    
    if confirm != "y":
        print("Cancelled. Image IDs saved for later use.")
        return
    
    # Create order
    print("Creating order...")
    products_list = [
        product(item_ids=all_image_ids, item_type="PSScene", product_bundle="analytic_sr_udm2")
    ]
    
    order_request = build_request(
        name="Didal_Glacier_Key_Dates",
        products=products_list
    )
    
    try:
        order = await orders_client.create_order(order_request)
        order_id = order["id"]
        print(f"Order created: {order_id}")
        print(f"Order status: {order.get('state', 'unknown')}")
        print()
        
        print("Waiting for order to complete (this may take 10-30 minutes)...")
        order = await orders_client.wait(order_id, callback=lambda state: print(f"  Status: {state}"))
        
        print(f"Order completed: {order.get('state')}")
        print()
        
        # Download order
        print(f"Downloading images to {OUTPUT_DIR}/...")
        await orders_client.download_order(order_id, directory=OUTPUT_DIR)
        
        print()
        print("=" * 60)
        print("Download complete!")
        print(f"Images saved to: {OUTPUT_DIR}/")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(download_images_for_dates())

