#!/usr/bin/env python3
"""
Script to download Planet.com satellite images using the official Planet SDK.

Requirements:
    pip install planet requests

Usage:
    python download_planet_sdk.py
"""

import os
from planet import api
from planet.api import filters
import json
from datetime import datetime

# Planet.com API configuration
PLANET_API_KEY = "PLAK97848b681d244728a5a7a02e73eb23d5"

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

# Set API key as environment variable (required by Planet SDK)
os.environ['PL_API_KEY'] = PLANET_API_KEY


def search_planet_images_sdk():
    """
    Search for Planet images using the Planet Python SDK.
    """
    try:
        # Initialize client
        client = api.ClientV1()
        
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
        query = filters.and_filter([
            filters.geom_filter(aoi),
            filters.date_range("acquired", gte=f"{START_DATE}T00:00:00Z", lte=f"{END_DATE}T23:59:59Z"),
            filters.range_filter("cloud_cover", lte=0.10)
        ])
        
        # Build search request
        request = filters.build_search_request(
            query,
            item_types=["PSScene"]
        )
        
        print("=" * 60)
        print("Planet.com Image Downloader for Didal Glacier (SDK)")
        print("=" * 60)
        print()
        print(f"Searching for PlanetScope images...")
        print(f"Date range: {START_DATE} to {END_DATE}")
        print(f"AOI center: {GLACIER_CENTER_LAT}°N, {GLACIER_CENTER_LON}°E")
        print()
        
        # Execute search
        result = client.quick_search(request)
        
        # Get items
        items = list(result.items_iter(limit=100))
        
        print(f"Found {len(items)} images")
        print("-" * 60)
        
        if not items:
            print("No images found matching criteria.")
            print("\nPossible reasons:")
            print("  - Date range is in the future (2025)")
            print("  - No images available for this location/date")
            print("  - Cloud cover too restrictive")
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
            print(f"   Cloud cover: {cloud_cover:.2%}" if isinstance(cloud_cover, (int, float)) else f"   Cloud cover: {cloud_cover}")
            print()
        
        # Save metadata
        metadata_file = os.path.join(OUTPUT_DIR, "metadata.json")
        with open(metadata_file, "w") as f:
            json.dump([dict(item) for item in items], f, indent=2, default=str)
        print(f"Metadata saved to {metadata_file}")
        
        return items
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return []


def download_image_asset_sdk(item_id, asset_type="visual"):
    """
    Download a specific asset using the Planet SDK.
    """
    try:
        client = api.ClientV1()
        
        # Get assets
        assets = client.get_assets(item_id).get()
        
        if asset_type not in assets:
            print(f"Asset type '{asset_type}' not available for {item_id}")
            print(f"Available assets: {list(assets.keys())}")
            return None
        
        asset = assets[asset_type]
        
        # Activate asset if needed
        if asset.get("status") != "active":
            print(f"Activating asset {asset_type} for {item_id}...")
            client.activate_asset(asset)
            
            # Wait for activation
            import time
            max_wait = 60  # seconds
            wait_time = 0
            while asset.get("status") != "active" and wait_time < max_wait:
                time.sleep(2)
                wait_time += 2
                assets = client.get_assets(item_id).get()
                asset = assets.get(asset_type, {})
            
            if asset.get("status") != "active":
                print(f"Asset activation timeout for {item_id}")
                return None
        
        # Download asset
        print(f"Downloading {item_id} ({asset_type})...")
        download_url = asset.get("location")
        
        if download_url:
            import requests
            response = requests.get(download_url, stream=True)
            
            if response.status_code == 200:
                filename = f"{item_id}_{asset_type}.tif"
                filepath = os.path.join(OUTPUT_DIR, filename)
                
                with open(filepath, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                print(f"Downloaded: {filepath}")
                return filepath
        
        return None
        
    except Exception as e:
        print(f"Error downloading {item_id}: {e}")
        return None


def main():
    """
    Main function.
    """
    # Search for images
    items = search_planet_images_sdk()
    
    if not items:
        return
    
    # Ask user which images to download
    print(f"\nTotal images found: {len(items)}")
    download_all = input("Download all images? (y/n): ").lower().strip()
    
    if download_all == "y":
        images_to_download = items
    else:
        indices = input("Enter image numbers to download (comma-separated, e.g., 1,2,3): ")
        try:
            indices = [int(i.strip()) - 1 for i in indices.split(",")]
            images_to_download = [items[i] for i in indices if 0 <= i < len(items)]
        except:
            print("Invalid input. Downloading first image only.")
            images_to_download = items[:1]
    
    # Download selected images
    print(f"\nDownloading {len(images_to_download)} images...")
    print("-" * 60)
    
    downloaded_files = []
    for item in images_to_download:
        item_id = item.get("id")
        if item_id:
            filepath = download_image_asset_sdk(item_id, asset_type="visual")
            if filepath:
                downloaded_files.append(filepath)
    
    print(f"\nDownloaded {len(downloaded_files)} images to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()

