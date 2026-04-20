#!/usr/bin/env python3
"""
Download thumbnails for images that actually cover the Didal Glacier location.
"""

import os
import json
import requests
from planet import Auth, Session

# Planet.com API configuration
PLANET_API_KEY = "PLAK97848b681d244728a5a7a02e73eb23d5"

# Set API key
os.environ['PL_API_KEY'] = PLANET_API_KEY

# Output directory
OUTPUT_DIR = "planet_images/glacier_thumbnails"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load filtered images
filtered_file = "planet_images/glacier_covering_images.json"

def download_glacier_thumbnails():
    """
    Download thumbnails for images covering the glacier.
    """
    # Load filtered images
    with open(filtered_file, 'r') as f:
        images = json.load(f)
    
    print("=" * 60)
    print("Downloading Thumbnails for Glacier-Covering Images")
    print("=" * 60)
    print(f"Total images covering glacier: {len(images)}")
    print()
    
    # Authenticate
    auth = Auth.from_key(PLANET_API_KEY)
    session = Session(auth=auth)
    
    downloaded = 0
    failed = 0
    
    # Focus on key event dates
    key_dates = [
        "2025-09-19",  # Initial movement
        "2025-10-25",  # Second movement
        "2025-11-01",  # Continued movement period
        "2025-11-02",
        "2025-11-03",  # Earthquake day
    ]
    
    print("Prioritizing images from key event dates:")
    print("  - Sept 19 (initial movement)")
    print("  - Oct 25 (second movement)")
    print("  - Nov 1-3 (continued movement + earthquake)")
    print()
    
    # Sort: key dates first, then others
    def sort_key(img):
        date = img['acquired'][:10]  # Get date part
        if date in key_dates:
            return (0, date)  # Key dates first
        return (1, date)  # Others after
    
    sorted_images = sorted(images, key=sort_key)
    
    for i, img in enumerate(sorted_images, 1):
        item_id = img['id']
        acquired = img['acquired']
        date = acquired[:10]
        
        # Mark key dates
        is_key = date in key_dates
        marker = "⭐" if is_key else "  "
        
        print(f"{marker} {i}. {item_id}")
        print(f"     Date: {date}")
        print(f"     Cloud: {img['cloud_cover']}%")
        
        # Construct thumbnail URL
        thumbnail_url = f"https://tiles.planet.com/data/v1/item-types/PSScene/items/{item_id}/thumb"
        
        try:
            headers = {
                "Authorization": f"api-key {PLANET_API_KEY}"
            }
            
            response = requests.get(thumbnail_url, headers=headers, stream=True, timeout=30)
            
            if response.status_code == 200:
                filename = f"{date}_{item_id}_thumb.png"
                filepath = os.path.join(OUTPUT_DIR, filename)
                
                with open(filepath, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                print(f"     ✓ Saved: {filename}")
                downloaded += 1
            else:
                print(f"     ✗ Error: {response.status_code}")
                failed += 1
                
        except Exception as e:
            print(f"     ✗ Error: {e}")
            failed += 1
        
        print()
    
    print("-" * 60)
    print(f"Downloaded: {downloaded} thumbnails")
    print(f"Failed: {failed} thumbnails")
    print(f"Saved to: {OUTPUT_DIR}/")
    print()
    print("Note: Thumbnails are low-resolution previews (~80-90 KB).")
    print("For analysis, you'll need full-resolution images via Orders API.")

if __name__ == "__main__":
    download_glacier_thumbnails()

