#!/usr/bin/env python3
"""
Download Sentinel-2 optical imagery for Didal Glacier area.
Uses sentinelsat library to access Copernicus Open Access Hub.
"""

import os
from datetime import datetime, timedelta
from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
import json

# Glacier location and AOI
GLACIER_CENTER_LAT = 38.97
GLACIER_CENTER_LON = 70.75

# Create AOI (bounding box around glacier, ~5km buffer)
AOI_BBOX = {
    "type": "Polygon",
    "coordinates": [[
        [GLACIER_CENTER_LON - 0.05, GLACIER_CENTER_LAT - 0.05],
        [GLACIER_CENTER_LON + 0.05, GLACIER_CENTER_LAT - 0.05],
        [GLACIER_CENTER_LON + 0.05, GLACIER_CENTER_LAT + 0.05],
        [GLACIER_CENTER_LON - 0.05, GLACIER_CENTER_LAT + 0.05],
        [GLACIER_CENTER_LON - 0.05, GLACIER_CENTER_LAT - 0.05]
    ]]
}

# Key event dates
KEY_DATES = {
    "before_initial": ("2025-09-01", "2025-09-18"),
    "initial_movement": ("2025-09-19", "2025-09-25"),
    "second_movement": ("2025-10-20", "2025-10-30"),
    "continued_movement": ("2025-10-31", "2025-11-10"),
}

# Output directory
OUTPUT_DIR = "satellite_data/sentinel2"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Save AOI to GeoJSON
aoi_file = os.path.join(OUTPUT_DIR, "aoi.geojson")
with open(aoi_file, 'w') as f:
    json.dump(AOI_BBOX, f, indent=2)

def download_sentinel2(username=None, password=None):
    """
    Download Sentinel-2 imagery.
    
    Note: Requires Copernicus Data Space Ecosystem account (free):
    https://dataspace.copernicus.eu/
    
    The old Copernicus Open Access Hub (SciHub) has been replaced by
    the Copernicus Data Space Ecosystem (since July 2023).
    """
    if not username or not password:
        print("=" * 60)
        print("Sentinel-2 Download Setup")
        print("=" * 60)
        print()
        print("To download Sentinel-2 imagery, you need:")
        print("  1. A free Copernicus Open Access Hub account")
        print("     Register at: https://scihub.copernicus.eu/dhus/#/self-registration")
        print()
        print("  2. Install sentinelsat library:")
        print("     pip install sentinelsat")
        print()
        print("  3. Run this script with your credentials:")
        print("     python download_sentinel2.py --username YOUR_USERNAME --password YOUR_PASSWORD")
        print()
        print("Alternatively, you can download manually from:")
        print("  https://scihub.copernicus.eu/")
        print()
        return
    
    # Connect to API
    # Note: For Copernicus Data Space Ecosystem, use:
    # api = SentinelAPI(username, password, 'https://dataspace.copernicus.eu/apihub')
    # For old SciHub (if still needed):
    api = SentinelAPI(username, password, 'https://apihub.copernicus.eu/apihub')
    
    print("=" * 60)
    print("Searching for Sentinel-2 Imagery")
    print("=" * 60)
    print(f"Area: {GLACIER_CENTER_LAT}°N, {GLACIER_CENTER_LON}°E")
    print()
    
    # Convert AOI to WKT
    footprint = geojson_to_wkt(AOI_BBOX)
    
    all_products = {}
    
    # Search for each time period
    for period_name, (start_date, end_date) in KEY_DATES.items():
        print(f"Searching {period_name} ({start_date} to {end_date})...")
        
        products = api.query(
            area=footprint,
            date=(start_date, end_date),
            platformname='Sentinel-2',
            processinglevel='Level-2A',  # Surface reflectance
            cloudcoverpercentage=(0, 30)  # Max 30% cloud cover
        )
        
        print(f"  Found {len(products)} products")
        
        if products:
            all_products[period_name] = products
            
            # Show first few
            for i, (product_id, product_info) in enumerate(list(products.items())[:3]):
                print(f"    {i+1}. {product_id}")
                print(f"       Date: {product_info['beginposition']}")
                print(f"       Cloud: {product_info['cloudcoverpercentage']:.1f}%")
        
        print()
    
    if not all_products:
        print("No Sentinel-2 products found.")
        return
    
    print(f"Total products found: {sum(len(p) for p in all_products.values())}")
    print()
    
    # Download products
    print("To download products, use:")
    print("  api.download(product_id, directory_path=OUTPUT_DIR)")
    print()
    print("Or download manually from Copernicus Open Access Hub")
    print("  https://scihub.copernicus.eu/")
    
    # Save product list
    products_file = os.path.join(OUTPUT_DIR, "available_products.json")
    products_summary = {}
    for period, products in all_products.items():
        products_summary[period] = {
            product_id: {
                "title": info["title"],
                "date": str(info["beginposition"]),
                "cloud_cover": info["cloudcoverpercentage"]
            }
            for product_id, info in products.items()
        }
    
    with open(products_file, 'w') as f:
        json.dump(products_summary, f, indent=2)
    
    print(f"Product list saved to: {products_file}")


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
    
    download_sentinel2(username, password)

