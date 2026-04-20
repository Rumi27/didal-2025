#!/usr/bin/env python3
"""
Interactive script to download satellite imagery.
Prompts for credentials and downloads available imagery.
"""

import os
import sys
import getpass

# Check for required libraries
try:
    import sentinelsat
    SENTINEL2_AVAILABLE = True
except ImportError:
    SENTINEL2_AVAILABLE = False
    print("⚠️  sentinelsat not installed. Install with: pip install sentinelsat")

try:
    import landsatxplore
    LANDSAT_AVAILABLE = True
except ImportError:
    LANDSAT_AVAILABLE = False
    print("⚠️  landsatxplore not installed. Install with: pip install landsatxplore")

print("=" * 60)
print("Satellite Image Downloader - Didal Glacier")
print("=" * 60)
print()

# Glacier location
GLACIER_CENTER_LAT = 38.97
GLACIER_CENTER_LON = 70.75

# Key dates
KEY_DATES = {
    "before_initial": ("2025-09-01", "2025-09-18"),
    "initial_movement": ("2025-09-19", "2025-09-25"),
    "second_movement": ("2025-10-20", "2025-10-30"),
    "continued_movement": ("2025-10-31", "2025-11-10"),
}

print(f"Study Area: {GLACIER_CENTER_LAT}°N, {GLACIER_CENTER_LON}°E")
print(f"Time Period: September - November 2025")
print()

# Ask which satellite to download
print("Which satellite imagery would you like to download?")
print("  1. Sentinel-2 (Copernicus) - Recommended")
print("  2. Landsat (USGS)")
print("  3. Both")
print("  4. Skip (show instructions only)")
print()

choice = input("Enter choice (1-4): ").strip()

if choice == "4":
    print()
    print("=" * 60)
    print("Download Instructions")
    print("=" * 60)
    print()
    print("SENTINEL-2:")
    print("  1. Register (free): https://scihub.copernicus.eu/dhus/#/self-registration")
    print("  2. Run: python3 download_sentinel2.py --username USER --password PASS")
    print()
    print("LANDSAT:")
    print("  1. Register (free): https://earthexplorer.usgs.gov/")
    print("  2. Run: python3 download_landsat.py --username USER --password PASS")
    print()
    sys.exit(0)

# Get credentials
sentinel2_username = None
sentinel2_password = None
landsat_username = None
landsat_password = None

if choice in ["1", "3"] and SENTINEL2_AVAILABLE:
    print()
    print("SENTINEL-2 Credentials:")
    print("  (Register free at: https://scihub.copernicus.eu/dhus/#/self-registration)")
    sentinel2_username = input("  Username: ").strip()
    sentinel2_password = getpass.getpass("  Password: ")

if choice in ["2", "3"] and LANDSAT_AVAILABLE:
    print()
    print("LANDSAT Credentials:")
    print("  (Register free at: https://earthexplorer.usgs.gov/)")
    landsat_username = input("  Username: ").strip()
    landsat_password = getpass.getpass("  Password: ")

# Download Sentinel-2
if choice in ["1", "3"] and SENTINEL2_AVAILABLE and sentinel2_username:
    print()
    print("=" * 60)
    print("Downloading Sentinel-2 Imagery")
    print("=" * 60)
    print()
    
    try:
        from sentinelsat import SentinelAPI, geojson_to_wkt
        import json
        
        # Create AOI
        aoi = {
            "type": "Polygon",
            "coordinates": [[
                [GLACIER_CENTER_LON - 0.05, GLACIER_CENTER_LAT - 0.05],
                [GLACIER_CENTER_LON + 0.05, GLACIER_CENTER_LAT - 0.05],
                [GLACIER_CENTER_LON + 0.05, GLACIER_CENTER_LAT + 0.05],
                [GLACIER_CENTER_LON - 0.05, GLACIER_CENTER_LAT + 0.05],
                [GLACIER_CENTER_LON - 0.05, GLACIER_CENTER_LAT - 0.05]
            ]]
        }
        
        footprint = geojson_to_wkt(aoi)
        
        # Connect to API
        api = SentinelAPI(sentinel2_username, sentinel2_password, 
                         'https://apihub.copernicus.eu/apihub')
        
        output_dir = "satellite_data/sentinel2"
        os.makedirs(output_dir, exist_ok=True)
        
        all_products = {}
        
        # Search for each time period
        for period_name, (start_date, end_date) in KEY_DATES.items():
            print(f"Searching {period_name} ({start_date} to {end_date})...")
            
            products = api.query(
                area=footprint,
                date=(start_date, end_date),
                platformname='Sentinel-2',
                processinglevel='Level-2A',
                cloudcoverpercentage=(0, 30)
            )
            
            print(f"  Found {len(products)} products")
            
            if products:
                all_products[period_name] = products
                
                # Download first product from each period
                for product_id, product_info in list(products.items())[:1]:
                    print(f"  Downloading {product_id}...")
                    try:
                        api.download(product_id, directory_path=output_dir)
                        print(f"    ✓ Downloaded")
                    except Exception as e:
                        print(f"    ✗ Error: {e}")
            
            print()
        
        print(f"Sentinel-2 download complete! Files in: {output_dir}/")
        
    except Exception as e:
        print(f"Error downloading Sentinel-2: {e}")
        print("Please check your credentials and try again.")

# Download Landsat
if choice in ["2", "3"] and LANDSAT_AVAILABLE and landsat_username:
    print()
    print("=" * 60)
    print("Downloading Landsat Imagery")
    print("=" * 60)
    print()
    
    try:
        from landsatxplore.api import API
        from landsatxplore.earthexplorer import EarthExplorer
        
        # Initialize API
        api = API(landsat_username, landsat_password)
        
        # Define bounding box
        bbox = (
            GLACIER_CENTER_LON - 0.05,
            GLACIER_CENTER_LAT - 0.05,
            GLACIER_CENTER_LON + 0.05,
            GLACIER_CENTER_LAT + 0.05
        )
        
        output_dir = "satellite_data/landsat"
        os.makedirs(output_dir, exist_ok=True)
        
        all_scenes = {}
        
        # Search for each time period
        for period_name, (start_date, end_date) in KEY_DATES.items():
            print(f"Searching {period_name} ({start_date} to {end_date})...")
            
            scenes = api.search(
                dataset='landsat_ot_c2_l2',
                bbox=bbox,
                start_date=start_date,
                end_date=end_date,
                max_cloud_cover=30
            )
            
            print(f"  Found {len(scenes)} scenes")
            
            if scenes:
                all_scenes[period_name] = scenes
                
                # Download first scene from each period
                scene = scenes[0]
                print(f"  Downloading {scene['displayId']}...")
                
                ee = EarthExplorer(landsat_username, landsat_password)
                try:
                    ee.download(scene['entityId'], output_dir=output_dir)
                    print(f"    ✓ Downloaded")
                except Exception as e:
                    print(f"    ✗ Error: {e}")
                finally:
                    ee.logout()
            
            print()
        
        api.logout()
        print(f"Landsat download complete! Files in: {output_dir}/")
        
    except Exception as e:
        print(f"Error downloading Landsat: {e}")
        print("Please check your credentials and try again.")

print()
print("=" * 60)
print("Download Process Complete!")
print("=" * 60)

