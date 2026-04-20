#!/usr/bin/env python3
"""
Script to download Planet.com satellite images for Didal Glacier study area.

Requirements:
    pip install planet requests

Usage:
    python download_planet_images.py

Before running:
    1. Set your Planet API key in the PLANET_API_KEY variable below
    2. Adjust date range, AOI, and other parameters as needed
"""

import os
import requests
from datetime import datetime, timedelta
import json

# Planet.com API configuration
PLANET_API_KEY = "PLAK97848b681d244728a5a7a02e73eb23d5"  # Replace with your actual API key
PLANET_API_URL = "https://api.planet.com/data/v1"

# Study area: Didal Glacier
# Coordinates: 39.0005°N, 70.7385°E
GLACIER_CENTER_LAT = 39.0005
GLACIER_CENTER_LON = 70.7385

# Area of Interest (AOI) - adjust buffer as needed (in degrees)
BUFFER = 0.05  # ~5.5 km buffer around center point

# Date range for the event
# Event timeline: Sept 19, Oct 25, Nov 1-3, 2025
START_DATE = "2025-09-01"
END_DATE = "2025-11-30"

# Create AOI geometry (GeoJSON format)
AOI_GEOMETRY = {
    "type": "Polygon",
    "coordinates": [[
        [GLACIER_CENTER_LON - BUFFER, GLACIER_CENTER_LAT - BUFFER],
        [GLACIER_CENTER_LON + BUFFER, GLACIER_CENTER_LAT - BUFFER],
        [GLACIER_CENTER_LON + BUFFER, GLACIER_CENTER_LAT + BUFFER],
        [GLACIER_CENTER_LON - BUFFER, GLACIER_CENTER_LAT + BUFFER],
        [GLACIER_CENTER_LON - BUFFER, GLACIER_CENTER_LAT - BUFFER]
    ]]
}

# Output directory
OUTPUT_DIR = "planet_images"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def search_planet_images(geometry, start_date, end_date, item_type="PSScene"):
    """
    Search for Planet images using the Data API.
    
    Parameters:
    -----------
    geometry : dict
        GeoJSON geometry of the area of interest
    start_date : str
        Start date in YYYY-MM-DD format
    end_date : str
        End date in YYYY-MM-DD format
    item_type : str
        Planet item type (e.g., "PSScene", "REOrthoTile", "SkySatScene")
    
    Returns:
    --------
    list
        List of image IDs matching the search criteria
    """
    # Use the correct Planet API endpoint
    search_url = f"https://api.planet.com/data/v1/searches/quick"
    
    search_request = {
        "item_types": [item_type],
        "filter": {
            "type": "And",
            "config": [
                {
                    "type": "GeometryFilter",
                    "field_name": "geometry",
                    "config": geometry
                },
                {
                    "type": "DateRangeFilter",
                    "field_name": "acquired",
                    "config": {
                        "gte": f"{start_date}T00:00:00Z",
                        "lte": f"{end_date}T23:59:59Z"
                    }
                },
                {
                    "type": "RangeFilter",
                    "field_name": "cloud_cover",
                    "config": {
                        "lte": 0.10  # Maximum 10% cloud cover
                    }
                }
            ]
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # Planet API uses API key in Authorization header
    auth_headers = {
        "Authorization": f"api-key {PLANET_API_KEY}",
        "Content-Type": "application/json"
    }
    
    print(f"Searching for {item_type} images...")
    print(f"Date range: {start_date} to {end_date}")
    print(f"AOI center: {GLACIER_CENTER_LAT}°N, {GLACIER_CENTER_LON}°E")
    print(f"API endpoint: {search_url}")
    
    response = requests.post(
        search_url,
        headers=auth_headers,
        json=search_request
    )
    
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 200:
        search_results = response.json()
        items = search_results.get("features", [])
        print(f"Found {len(items)} images")
        return items
    else:
        print(f"Error: {response.status_code}")
        print(f"Response: {response.text[:500]}")  # First 500 chars
        return []


def get_image_metadata(item_id):
    """
    Get detailed metadata for a specific image.
    """
    url = f"{PLANET_API_URL}/item-types/PSScene/items/{item_id}"
    auth_headers = {
        "Authorization": f"api-key {PLANET_API_KEY}"
    }
    
    response = requests.get(url, headers=auth_headers)
    if response.status_code == 200:
        return response.json()
    return None


def download_image_asset(item_id, asset_type="visual", output_dir=OUTPUT_DIR):
    """
    Download a specific asset from a Planet image.
    
    Parameters:
    -----------
    item_id : str
        Planet image ID
    asset_type : str
        Asset type (e.g., "visual", "analytic", "analytic_sr")
    output_dir : str
        Directory to save downloaded images
    """
    # Get asset activation URL
    asset_url = f"{PLANET_API_URL}/item-types/PSScene/items/{item_id}/assets"
    auth_headers = {
        "Authorization": f"api-key {PLANET_API_KEY}"
    }
    
    response = requests.get(asset_url, headers=auth_headers)
    if response.status_code != 200:
        print(f"Error getting assets for {item_id}: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        return None
    
    assets = response.json()
    
    if asset_type not in assets:
        print(f"Asset type '{asset_type}' not available for {item_id}")
        print(f"Available assets: {list(assets.keys())}")
        return None
    
    asset = assets[asset_type]
    
    # Activate asset if needed
    if asset.get("status") != "active":
        if "_links" in asset and "activate" in asset["_links"]:
            activation_url = asset["_links"]["activate"]
            activation_response = requests.get(activation_url, headers=auth_headers)
            if activation_response.status_code == 202:
                print(f"Activating asset for {item_id}...")
                # Wait for activation (simplified - in production, poll status)
                import time
                time.sleep(5)
        else:
            print(f"Asset {asset_type} for {item_id} is not active and cannot be activated")
            return None
    
    # Get download URL
    if "_links" in asset and "_self" in asset["_links"]:
        download_url = asset["_links"]["_self"]
        download_response = requests.get(download_url, headers=auth_headers)
        
        if download_response.status_code == 200:
            download_data = download_response.json()
            download_link = download_data.get("location")
            
            if download_link:
                # Download the file
                print(f"Downloading {item_id}...")
                file_response = requests.get(download_link, stream=True)
                
                if file_response.status_code == 200:
                    filename = f"{item_id}_{asset_type}.tif"
                    filepath = os.path.join(output_dir, filename)
                    
                    with open(filepath, "wb") as f:
                        for chunk in file_response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    print(f"Downloaded: {filepath}")
                    return filepath
                else:
                    print(f"Error downloading file: {file_response.status_code}")
            else:
                print(f"No download location in response: {download_data}")
        else:
            print(f"Error getting download URL: {download_response.status_code}")
            print(f"Response: {download_response.text[:200]}")
    else:
        print(f"No download links available for asset {asset_type}")
    
    return None


def main():
    """
    Main function to search and download Planet images.
    """
    if PLANET_API_KEY == "YOUR_API_KEY_HERE":
        print("ERROR: Please set your Planet API key in the script!")
        print("Get your API key from: https://www.planet.com/account/")
        return
    
    print("=" * 60)
    print("Planet.com Image Downloader for Didal Glacier")
    print("=" * 60)
    print()
    
    # Search for images
    items = search_planet_images(
        AOI_GEOMETRY,
        START_DATE,
        END_DATE,
        item_type="PSScene"  # PlanetScope scenes
    )
    
    if not items:
        print("No images found matching criteria.")
        print("Try:")
        print("  - Adjusting date range")
        print("  - Increasing cloud cover threshold")
        print("  - Checking AOI coordinates")
        return
    
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
        print(f"   Cloud cover: {cloud_cover}")
        print()
    
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
            filepath = download_image_asset(item_id, asset_type="visual")
            if filepath:
                downloaded_files.append(filepath)
    
    print(f"\nDownloaded {len(downloaded_files)} images to {OUTPUT_DIR}/")
    
    # Save metadata
    metadata_file = os.path.join(OUTPUT_DIR, "metadata.json")
    with open(metadata_file, "w") as f:
        json.dump(items, f, indent=2)
    print(f"Metadata saved to {metadata_file}")


if __name__ == "__main__":
    main()

