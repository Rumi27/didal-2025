#!/usr/bin/env python3
"""
Download Landsat imagery for Didal Glacier area.
Uses landsatxplore library to access USGS EarthExplorer.
"""

import os
from datetime import datetime
import json

# Glacier location
GLACIER_CENTER_LAT = 38.97
GLACIER_CENTER_LON = 70.75

# Key event dates
KEY_DATES = {
    "before_initial": ("2025-09-01", "2025-09-18"),
    "initial_movement": ("2025-09-19", "2025-09-25"),
    "second_movement": ("2025-10-20", "2025-10-30"),
    "continued_movement": ("2025-10-31", "2025-11-10"),
}

# Output directory
OUTPUT_DIR = "satellite_data/landsat"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def download_landsat(username=None, password=None):
    """
    Download Landsat imagery.
    
    Note: Requires USGS EarthExplorer account (free):
    https://earthexplorer.usgs.gov/
    """
    try:
        from landsatxplore.api import API
        from landsatxplore.earthexplorer import EarthExplorer
    except ImportError:
        print("=" * 60)
        print("Landsat Download Setup")
        print("=" * 60)
        print()
        print("To download Landsat imagery, you need:")
        print("  1. Install landsatxplore library:")
        print("     pip install landsatxplore")
        print()
        print("  2. A free USGS EarthExplorer account")
        print("     Register at: https://earthexplorer.usgs.gov/")
        print()
        print("  3. Run this script with your credentials:")
        print("     python download_landsat.py --username YOUR_USERNAME --password YOUR_PASSWORD")
        print()
        print("Alternatively, download manually from:")
        print("  https://earthexplorer.usgs.gov/")
        print()
        return
    
    if not username or not password:
        print("Please provide USGS EarthExplorer credentials.")
        print("Usage: python download_landsat.py --username USER --password PASS")
        return
    
    # Initialize API
    api = API(username, password)
    
    print("=" * 60)
    print("Searching for Landsat Imagery")
    print("=" * 60)
    print(f"Area: {GLACIER_CENTER_LAT}°N, {GLACIER_CENTER_LON}°E")
    print()
    
    # Define bounding box (W, S, E, N)
    bbox = (
        GLACIER_CENTER_LON - 0.05,  # West
        GLACIER_CENTER_LAT - 0.05,  # South
        GLACIER_CENTER_LON + 0.05,  # East
        GLACIER_CENTER_LAT + 0.05   # North
    )
    
    all_scenes = {}
    
    # Search for each time period
    for period_name, (start_date, end_date) in KEY_DATES.items():
        print(f"Searching {period_name} ({start_date} to {end_date})...")
        
        # Search Landsat Collection 2 Level-2 (Surface Reflectance)
        scenes = api.search(
            dataset='landsat_ot_c2_l2',  # Landsat 8/9 Collection 2 Level-2
            bbox=bbox,
            start_date=start_date,
            end_date=end_date,
            max_cloud_cover=30
        )
        
        print(f"  Found {len(scenes)} scenes")
        
        if scenes:
            all_scenes[period_name] = scenes
            
            # Show first few
            for i, scene in enumerate(scenes[:3]):
                print(f"    {i+1}. {scene['displayId']}")
                print(f"       Date: {scene['acquisitionDate']}")
                print(f"       Cloud: {scene['cloudCover']:.1f}%")
        
        print()
    
    if not all_scenes:
        print("No Landsat scenes found.")
        api.logout()
        return
    
    print(f"Total scenes found: {sum(len(s) for s in all_scenes.values())}")
    print()
    
    # Download scenes
    ee = EarthExplorer(username, password)
    
    print("Downloading scenes...")
    downloaded = 0
    
    for period_name, scenes in all_scenes.items():
        print(f"\nDownloading {period_name} scenes...")
        period_dir = os.path.join(OUTPUT_DIR, period_name)
        os.makedirs(period_dir, exist_ok=True)
        
        for scene in scenes[:5]:  # Limit to 5 per period
            scene_id = scene['entityId']
            print(f"  Downloading {scene['displayId']}...")
            
            try:
                ee.download(scene_id, output_dir=period_dir)
                downloaded += 1
                print(f"    ✓ Downloaded")
            except Exception as e:
                print(f"    ✗ Error: {e}")
    
    ee.logout()
    api.logout()
    
    print()
    print(f"Downloaded {downloaded} scenes to {OUTPUT_DIR}/")
    
    # Save scene list
    scenes_file = os.path.join(OUTPUT_DIR, "available_scenes.json")
    scenes_summary = {}
    for period, scenes in all_scenes.items():
        scenes_summary[period] = [
            {
                "displayId": s["displayId"],
                "entityId": s["entityId"],
                "date": s["acquisitionDate"],
                "cloud_cover": s["cloudCover"]
            }
            for s in scenes
        ]
    
    with open(scenes_file, 'w') as f:
        json.dump(scenes_summary, f, indent=2)
    
    print(f"Scene list saved to: {scenes_file}")


if __name__ == "__main__":
    import sys
    
    username = None
    password = None
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv):
            if arg == "--username" and i + 1 < len(sys.argv):
                username = sys.argv[i + 1]
            elif arg == "--password" and i + 1 < len(sys.argv):
                password = sys.argv[i + 1]
    
    download_landsat(username, password)

