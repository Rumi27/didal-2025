#!/usr/bin/env python3
"""
Download Sentinel-1 SAR data for Didal Glacier study area.
Uses Copernicus Data Space Ecosystem API (new system, since July 2023).

Study Area: 38.97°N, 70.75°E
Date Range: August 1 - December 31, 2025
Product Type: IW SLC or GRD (Interferometric Wide swath)
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

try:
    from sentinelsat import SentinelAPI, geojson_to_wkt
    SENTINELSAT_AVAILABLE = True
except ImportError:
    SENTINELSAT_AVAILABLE = False
    print("⚠️ sentinelsat library not installed")
    print("   Install with: pip install sentinelsat")

# Study area coordinates
GLACIER_CENTER_LAT = 38.97
GLACIER_CENTER_LON = 70.75

# Date range for surge event
START_DATE = "20250801"  # August 1, 2025 (before surge)
END_DATE = "20251231"    # December 31, 2025 (after surge)

# Create AOI (Area of Interest) - bounding box with buffer
BUFFER_DEG = 0.05  # ~5.5 km buffer
AOI_BBOX = {
    "type": "Polygon",
    "coordinates": [[
        [GLACIER_CENTER_LON - BUFFER_DEG, GLACIER_CENTER_LAT - BUFFER_DEG],
        [GLACIER_CENTER_LON + BUFFER_DEG, GLACIER_CENTER_LAT - BUFFER_DEG],
        [GLACIER_CENTER_LON + BUFFER_DEG, GLACIER_CENTER_LAT + BUFFER_DEG],
        [GLACIER_CENTER_LON - BUFFER_DEG, GLACIER_CENTER_LAT + BUFFER_DEG],
        [GLACIER_CENTER_LON - BUFFER_DEG, GLACIER_CENTER_LAT - BUFFER_DEG]
    ]]
}

# Output directory
OUTPUT_DIR = "satellite_data/sentinel1"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def check_existing_sentinel1_data():
    """Check for existing Sentinel-1 data in the project"""
    print("\n" + "="*70)
    print("CHECKING FOR EXISTING SENTINEL-1 DATA")
    print("="*70)
    
    # Search in common locations
    search_paths = [
        "satellite_data/sentinel1",
        "satellite_data",
        ".",
        "sentinel1",
        "S1"
    ]
    
    found_files = []
    found_dirs = []
    
    for search_path in search_paths:
        if os.path.exists(search_path):
            for root, dirs, files in os.walk(search_path):
                for file in files:
                    if any(keyword in file.upper() for keyword in ['S1', 'SENTINEL-1', 'IW', 'GRD', 'SLC']):
                        found_files.append(os.path.join(root, file))
                for dir_name in dirs:
                    if any(keyword in dir_name.upper() for keyword in ['S1', 'SENTINEL-1', 'IW', 'GRD', 'SLC', 'SAFE']):
                        found_dirs.append(os.path.join(root, dir_name))
    
    if found_files or found_dirs:
        print(f"\n✅ Found {len(found_files)} files and {len(found_dirs)} directories:")
        
        if found_files:
            print("\nFiles:")
            for f in found_files[:10]:  # Show first 10
                size = os.path.getsize(f) / (1024*1024)  # MB
                print(f"  - {f} ({size:.1f} MB)")
        
        if found_dirs:
            print("\nDirectories:")
            for d in found_dirs[:10]:  # Show first 10
                print(f"  - {d}")
        
        # Check if they match our requirements
        print("\n⚠️ Checking if existing data matches project requirements...")
        print(f"   Required location: {GLACIER_CENTER_LAT}°N, {GLACIER_CENTER_LON}°E")
        print(f"   Required dates: {START_DATE} to {END_DATE}")
        print("\n   Note: You may need to verify if existing data covers the correct")
        print("         location and date range for this project.")
        
        return True
    else:
        print("\n❌ No Sentinel-1 data found in project directories")
        return False

def download_sentinel1(username=None, password=None, product_type='GRD', orbit_type='IW'):
    """
    Download Sentinel-1 SAR imagery.
    
    Args:
        username: Copernicus Data Space Ecosystem username
        password: Copernicus Data Space Ecosystem password
        product_type: 'GRD' (Ground Range Detected) or 'SLC' (Single Look Complex)
        orbit_type: 'IW' (Interferometric Wide) - recommended for glaciers
    """
    
    if not SENTINELSAT_AVAILABLE:
        print("\n" + "="*70)
        print("SETUP REQUIRED")
        print("="*70)
        print("\nTo download Sentinel-1 data, you need:")
        print("  1. Install sentinelsat library:")
        print("     pip install sentinelsat")
        print("\n  2. Register for free Copernicus Data Space Ecosystem account:")
        print("     https://dataspace.copernicus.eu/")
        print("\n  3. Run this script with credentials:")
        print("     python download_sentinel1_sar.py --username USER --password PASS")
        print("\nAlternatively, download manually from:")
        print("  https://dataspace.copernicus.eu/")
        return
    
    if not username or not password:
        print("\n" + "="*70)
        print("SENTINEL-1 SAR DOWNLOAD SETUP")
        print("="*70)
        print("\nTo download Sentinel-1 SAR data, you need:")
        print("  1. A free Copernicus Data Space Ecosystem account")
        print("     Register at: https://dataspace.copernicus.eu/")
        print("\n  2. Install sentinelsat library:")
        print("     pip install sentinelsat")
        print("\n  3. Run this script with your credentials:")
        print("     python download_sentinel1_sar.py --username YOUR_USERNAME --password YOUR_PASSWORD")
        print("\n  4. Optional parameters:")
        print("     --product-type GRD  (or SLC)")
        print("     --orbit-type IW     (Interferometric Wide)")
        print("\nAlternatively, download manually from:")
        print("  https://dataspace.copernicus.eu/")
        print("\n" + "="*70)
        print("PROJECT REQUIREMENTS")
        print("="*70)
        print(f"\nStudy Area: {GLACIER_CENTER_LAT}°N, {GLACIER_CENTER_LON}°E")
        print(f"Date Range: {START_DATE} to {END_DATE}")
        print(f"Product Type: {product_type} (Ground Range Detected)")
        print(f"Orbit Type: {orbit_type} (Interferometric Wide)")
        print(f"Polarization: VV, VH (dual polarization recommended)")
        print("\nSearch for:")
        print("  - Platform: Sentinel-1")
        print("  - Product Type: S1A_IW_GRDH_1SDV or S1B_IW_GRDH_1SDV")
        print("  - Mode: IW (Interferometric Wide)")
        print("  - Processing Level: Level-1 GRD")
        return
    
    print("\n" + "="*70)
    print("SENTINEL-1 SAR DATA DOWNLOAD")
    print("="*70)
    print(f"\nStudy Area: {GLACIER_CENTER_LAT}°N, {GLACIER_CENTER_LON}°E")
    print(f"Date Range: {START_DATE} to {END_DATE}")
    print(f"Product Type: {product_type}")
    print(f"Orbit Type: {orbit_type}")
    print(f"Output Directory: {OUTPUT_DIR}")
    
    # Connect to API
    # Note: Copernicus Data Space Ecosystem uses OAuth2 authentication
    # The old sentinelsat library may not work with new system
    # Try multiple endpoints and methods
    
    api = None
    api_endpoints = [
        ('https://dataspace.copernicus.eu/apihub', 'New Copernicus Data Space Ecosystem'),
        ('https://apihub.copernicus.eu/apihub', 'Old SciHub (deprecated)'),
    ]
    
    print("\n" + "="*70)
    print("CONNECTING TO COPERNICUS API")
    print("="*70)
    
    for endpoint, description in api_endpoints:
        try:
            print(f"\nTrying: {description}")
            print(f"Endpoint: {endpoint}")
            print("Connecting... (this may take 30-60 seconds)")
            
            # Set timeout for connection
            import socket
            socket.setdefaulttimeout(60)  # 60 second timeout
            
            api = SentinelAPI(username, password, endpoint, timeout=60)
            
            # Test connection with a simple query
            print("Testing connection...")
            test_query = api.query(
                area=geojson_to_wkt(AOI_BBOX), 
                date=(START_DATE, END_DATE), 
                platformname='Sentinel-1', 
                limit=1
            )
            
            print(f"✅ Connected successfully to {description}")
            print(f"   Endpoint: {endpoint}")
            break
            
        except Exception as e:
            error_msg = str(e)
            print(f"⚠️ Connection failed: {error_msg[:200]}")
            
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                print("   → Connection timeout - possible reasons:")
                print("     - Network connectivity issues")
                print("     - API endpoint may be down")
                print("     - Firewall/proxy blocking connection")
                print("     - Try manual download from website instead")
            elif "authentication" in error_msg.lower() or "unauthorized" in error_msg.lower():
                print("   → Authentication error - check credentials")
            elif "404" in error_msg or "not found" in error_msg.lower():
                print("   → Endpoint not found - may be deprecated")
            continue
    
    if not api:
        print("\n" + "="*70)
        print("❌ COULD NOT CONNECT TO API")
        print("="*70)
        print("\n🔍 DIAGNOSIS:")
        print("   Connection timeout to Copernicus API")
        print("   Possible reasons:")
        print("   - Old API endpoint may be deprecated/slow")
        print("   - New system uses OAuth2 (sentinelsat may not support)")
        print("   - Network/firewall blocking connection")
        print("   - API server may be down")
        print("\n✅ RECOMMENDED SOLUTION: Manual Download")
        print("   1. Go to: https://dataspace.copernicus.eu/")
        print("   2. Login with your account")
        print("   3. Search for Sentinel-1:")
        print("      - Area: 38.97°N, 70.75°E")
        print("      - Date: 2025-08-01 to 2025-12-31")
        print("      - Product: IW GRD (Ground Range Detected)")
        print("   4. Select and download products")
        print("   5. Save to: satellite_data/sentinel1/")
        print("\n📋 See SENTINEL1_DOWNLOAD_ALTERNATIVES.md for detailed manual guide")
        print("\n🔄 Alternative: Try again later or use different network")
        return
    
    # Convert AOI to WKT
    footprint = geojson_to_wkt(AOI_BBOX)
    
    # Search for Sentinel-1 products
    print("\n" + "="*70)
    print("SEARCHING FOR SENTINEL-1 PRODUCTS")
    print("="*70)
    
    # Build query
    query_params = {
        'area': footprint,
        'date': (START_DATE, END_DATE),
        'platformname': 'Sentinel-1',
        'producttype': f'IW_{product_type}DH',  # IW mode, GRD or SLC, Dual pol, High res
    }
    
    print(f"\nSearch parameters:")
    print(f"  Area: {GLACIER_CENTER_LAT}°N, {GLACIER_CENTER_LON}°E (±{BUFFER_DEG}°)")
    print(f"  Date: {START_DATE} to {END_DATE}")
    print(f"  Platform: Sentinel-1")
    print(f"  Product Type: IW_{product_type}DH (Interferometric Wide, {product_type}, Dual pol, High res)")
    
    try:
        products = api.query(**query_params)
        print(f"\n✅ Found {len(products)} Sentinel-1 products")
        
        if not products:
            print("\n⚠️ No products found. Possible reasons:")
            print("  1. Data may not be available yet (2025 data may have delay)")
            print("  2. Check if dates are correct (format: YYYYMMDD)")
            print("  3. Try different product type (GRD vs SLC)")
            print("  4. Check Copernicus Data Space Ecosystem manually:")
            print("     https://dataspace.copernicus.eu/")
            return
        
        # Display found products
        print("\n" + "-"*70)
        print("FOUND PRODUCTS:")
        print("-"*70)
        
        products_by_date = {}
        orbit_ids = set()
        
        for product_id, product_info in products.items():
            date = product_info['beginposition'].date()
            orbit_id = product_info.get('relativeorbitnumber', 'Unknown')
            orbit_ids.add(orbit_id)
            
            if date not in products_by_date:
                products_by_date[date] = []
            
            products_by_date[date].append({
                'id': product_id,
                'title': product_info['title'],
                'orbit': orbit_id,
                'mode': product_info.get('sensoroperationalmode', 'Unknown'),
                'polarization': product_info.get('polarisationmode', 'Unknown'),
                'size_mb': product_info['size'] / (1024*1024)
            })
        
        # Sort by date
        sorted_dates = sorted(products_by_date.keys())
        
        print(f"\nProducts found: {len(products)}")
        print(f"Date range: {sorted_dates[0]} to {sorted_dates[-1]}")
        print(f"Unique orbit IDs: {sorted(orbit_ids)}")
        print(f"\nProducts by date:")
        
        for date in sorted_dates[:20]:  # Show first 20 dates
            date_products = products_by_date[date]
            print(f"\n  {date} ({len(date_products)} products):")
            for p in date_products:
                print(f"    - {p['title']}")
                print(f"      Orbit: {p['orbit']}, Mode: {p['mode']}, Pol: {p['polarization']}, Size: {p['size_mb']:.1f} MB")
        
        if len(sorted_dates) > 20:
            print(f"\n  ... and {len(sorted_dates) - 20} more dates")
        
        # Save product list
        products_file = os.path.join(OUTPUT_DIR, "sentinel1_products_available.json")
        products_summary = {
            'search_parameters': {
                'area': f"{GLACIER_CENTER_LAT}°N, {GLACIER_CENTER_LON}°E",
                'date_range': f"{START_DATE} to {END_DATE}",
                'product_type': product_type,
                'orbit_type': orbit_type
            },
            'total_products': len(products),
            'orbit_ids': sorted(list(orbit_ids)),
            'date_range': {
                'start': str(sorted_dates[0]),
                'end': str(sorted_dates[-1])
            },
            'products_by_date': {
                str(date): [
                    {
                        'id': p['id'],
                        'title': p['title'],
                        'orbit': p['orbit'],
                        'mode': p['mode'],
                        'polarization': p['polarization'],
                        'size_mb': p['size_mb']
                    }
                    for p in products
                ]
                for date, products in products_by_date.items()
            }
        }
        
        with open(products_file, 'w') as f:
            json.dump(products_summary, f, indent=2)
        
        print(f"\n💾 Product list saved to: {products_file}")
        
        # Ask user if they want to download
        print("\n" + "="*70)
        print("DOWNLOAD OPTIONS")
        print("="*70)
        print("\nYou can:")
        print("  1. Download all products (may take time and disk space)")
        print("  2. Download specific products by date")
        print("  3. Download manually from Copernicus Data Space Ecosystem")
        print("\nTo download all products, uncomment the download section in the script")
        print("Or download manually from: https://dataspace.copernicus.eu/")
        
        # Uncomment below to enable automatic download
        # print("\nStarting download...")
        # for product_id, product_info in products.items():
        #     print(f"Downloading {product_id}...")
        #     try:
        #         api.download(product_id, directory_path=OUTPUT_DIR)
        #         print(f"  ✅ Downloaded")
        #     except Exception as e:
        #         print(f"  ❌ Error: {e}")
        
    except Exception as e:
        print(f"\n❌ Error searching for products: {e}")
        print("\nTroubleshooting:")
        print("  1. Check your credentials")
        print("  2. Verify internet connection")
        print("  3. Check if Copernicus Data Space Ecosystem is accessible")
        print("  4. Try manual download from: https://dataspace.copernicus.eu/")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Download Sentinel-1 SAR data for Didal Glacier')
    parser.add_argument('--username', help='Copernicus Data Space Ecosystem username')
    parser.add_argument('--password', help='Copernicus Data Space Ecosystem password')
    parser.add_argument('--product-type', choices=['GRD', 'SLC'], default='GRD',
                       help='Product type: GRD (Ground Range Detected) or SLC (Single Look Complex)')
    parser.add_argument('--orbit-type', default='IW',
                       help='Orbit type: IW (Interferometric Wide) recommended')
    parser.add_argument('--check-existing', action='store_true',
                       help='Check for existing Sentinel-1 data in project')
    
    args = parser.parse_args()
    
    # Check for existing data first
    if args.check_existing or not args.username:
        check_existing_sentinel1_data()
    
    # Download if credentials provided
    if args.username and args.password:
        download_sentinel1(args.username, args.password, 
                          args.product_type, args.orbit_type)
    else:
        download_sentinel1()  # Show setup instructions

if __name__ == "__main__":
    main()

