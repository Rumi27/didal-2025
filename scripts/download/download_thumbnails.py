#!/usr/bin/env python3
"""
Script to download thumbnails from Planet images.
Thumbnails are small preview images that can be viewed without ordering.
"""

import os
import json
import requests
from planet import Auth, Session

# Planet.com API configuration
PLANET_API_KEY = "PLAK97848b681d244728a5a7a02e73eb23d5"
PLANET_USER_ID = "d09f3150-dcdb-4644-88d7-9a15f1c1e9b7"

# Set API key
os.environ['PL_API_KEY'] = PLANET_API_KEY

# Output directory
OUTPUT_DIR = "planet_images/thumbnails"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load metadata
metadata_file = "planet_images/metadata.json"

def download_thumbnails(max_images=20):
    """
    Download thumbnails for images in metadata.
    """
    # Authenticate
    auth = Auth.from_key(PLANET_API_KEY)
    session = Session(auth=auth)
    
    # Load metadata
    with open(metadata_file, 'r') as f:
        items = json.load(f)
    
    print(f"Found {len(items)} images in metadata")
    print(f"Downloading thumbnails for first {max_images} images...")
    print("-" * 60)
    
    downloaded = 0
    failed = 0
    
    for i, item in enumerate(items[:max_images], 1):
        item_id = item.get("id", "unknown")
        thumbnail_url = None
        
        # Get thumbnail URL
        if "_links" in item and "thumbnail" in item["_links"]:
            thumbnail_url = item["_links"]["thumbnail"]
        else:
            # Construct thumbnail URL
            thumbnail_url = f"https://tiles.planet.com/data/v1/item-types/PSScene/items/{item_id}/thumb"
        
        # Get acquisition date
        acquired = item.get("properties", {}).get("acquired", "unknown")
        
        print(f"{i}. {item_id}")
        print(f"   Acquired: {acquired}")
        print(f"   Downloading thumbnail...")
        
        try:
            # Download thumbnail (requires authentication)
            headers = {
                "Authorization": f"api-key {PLANET_API_KEY}"
            }
            
            response = requests.get(thumbnail_url, headers=headers, stream=True, timeout=30)
            
            if response.status_code == 200:
                filename = f"{item_id}_thumb.png"
                filepath = os.path.join(OUTPUT_DIR, filename)
                
                with open(filepath, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                print(f"   ✓ Saved: {filepath}")
                downloaded += 1
            else:
                print(f"   ✗ Error: {response.status_code}")
                failed += 1
                
        except Exception as e:
            print(f"   ✗ Error: {e}")
            failed += 1
        
        print()
    
    print("-" * 60)
    print(f"Downloaded: {downloaded} thumbnails")
    print(f"Failed: {failed} thumbnails")
    print(f"Thumbnails saved to: {OUTPUT_DIR}/")

if __name__ == "__main__":
    download_thumbnails(max_images=20)

