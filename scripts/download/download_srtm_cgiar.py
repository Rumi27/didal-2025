#!/usr/bin/env python3
"""
Download SRTM tiles from CGIAR-CSI (no registration required)
This is the easiest method for downloading SRTM data
"""

import os
import urllib.request
from pathlib import Path

# Tajikistan extent
TAJIKISTAN_BOUNDS = {
    'west': 67.0,
    'south': 36.0,
    'east': 75.0,
    'north': 41.0
}

# CGIAR-CSI SRTM base URL
CGIAR_BASE_URL = "http://srtm.csi.cgiar.org/wp-content/uploads/files/srtm_5x5/TIFF/"

def generate_tile_list():
    """Generate list of SRTM tiles needed for Tajikistan."""
    tiles = []
    
    # Generate tile names (N36-N41, E067-E075)
    for lat in range(36, 42):  # N36 to N41
        for lon in range(67, 76):  # E067 to E075
            tile_name = f"srtm_{lat:02d}_{lon:03d}.tif"
            tiles.append({
                'name': tile_name,
                'url': f"{CGIAR_BASE_URL}{tile_name}",
                'lat': lat,
                'lon': lon
            })
    
    return tiles

def download_tile(tile_info, output_dir):
    """Download a single SRTM tile."""
    output_path = os.path.join(output_dir, tile_info['name'])
    
    # Skip if already exists
    if os.path.exists(output_path):
        print(f"  ✓ Already exists: {tile_info['name']}")
        return True
    
    try:
        print(f"  Downloading: {tile_info['name']}...", end=' ', flush=True)
        urllib.request.urlretrieve(tile_info['url'], output_path)
        file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
        print(f"✓ ({file_size:.1f} MB)")
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"✗ (tile not available)")
        else:
            print(f"✗ (HTTP {e.code})")
        return False
    except Exception as e:
        print(f"✗ (Error: {e})")
        return False

def main():
    print("=" * 70)
    print("DOWNLOAD SRTM TILES FROM CGIAR-CSI")
    print("=" * 70)
    print()
    print("Tajikistan extent:")
    print(f"  {TAJIKISTAN_BOUNDS['west']}°E to {TAJIKISTAN_BOUNDS['east']}°E")
    print(f"  {TAJIKISTAN_BOUNDS['south']}°N to {TAJIKISTAN_BOUNDS['north']}°N")
    print()
    
    # Create output directory
    output_dir = "satellite_data/dem/srtm_raw"
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}")
    print()
    
    # Generate tile list
    tiles = generate_tile_list()
    print(f"Total tiles to check: {len(tiles)}")
    print()
    print("Downloading tiles...")
    print("-" * 70)
    
    downloaded = 0
    failed = 0
    
    for tile in tiles:
        if download_tile(tile, output_dir):
            downloaded += 1
        else:
            failed += 1
    
    print("-" * 70)
    print()
    print(f"✅ Downloaded: {downloaded} tiles")
    if failed > 0:
        print(f"⚠️  Failed/Not available: {failed} tiles")
    print()
    print("Next steps:")
    print("1. Check downloaded tiles in:", output_dir)
    print("2. I'll help merge and process them in QGIS")
    print()
    print("=" * 70)

if __name__ == "__main__":
    main()

