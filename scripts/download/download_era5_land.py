#!/usr/bin/env python3
"""
Download ERA5-Land climate data for Didal Glacier study.

Study Area: 38.97°N, 70.75°E
Date Range: January 1 - December 31, 2025
Variables: 2m temperature, total precipitation, snow water equivalent

Requirements:
1. Copernicus CDS account (free): https://cds.climate.copernicus.eu/
2. CDS API key: Get from https://cds.climate.copernicus.eu/api-how-to
3. Install: pip install cdsapi

Usage:
    python3 download_era5_land.py --api-key YOUR_API_KEY
    OR
    python3 download_era5_land.py  # Will prompt for API key
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Study area coordinates
GLACIER_LAT = 38.97
GLACIER_LON = 70.75

# Date range (full year for climate derivatives)
START_DATE = "2025-01-01"
END_DATE = "2025-12-31"

# Output directory
OUTPUT_DIR = "satellite_data/era5_land"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def check_cdsapi():
    """Check if cdsapi is installed."""
    try:
        import cdsapi
        return True, cdsapi
    except ImportError:
        print("=" * 60)
        print("⚠️  cdsapi library not installed")
        print("=" * 60)
        print()
        print("Install with:")
        print("  pip install cdsapi")
        print()
        print("Or:")
        print("  pip3 install cdsapi")
        print()
        return False, None

def get_api_key(api_key_arg=None):
    """Get CDS API key from argument or environment variable."""
    if api_key_arg:
        return api_key_arg
    
    # Check environment variable
    api_key = os.environ.get('CDS_API_KEY')
    if api_key:
        return api_key
    
    # Check for .cdsapirc file
    cdsapirc = Path.home() / '.cdsapirc'
    if cdsapirc.exists():
        print(f"✅ Found CDS API credentials in: {cdsapirc}")
        print("   Using credentials from .cdsapirc file")
        return None  # cdsapi will use .cdsapirc automatically
    
    # Prompt user
    print("=" * 60)
    print("CDS API Key Required")
    print("=" * 60)
    print()
    print("To download ERA5-Land data, you need:")
    print("  1. Copernicus CDS account (free)")
    print("     Register at: https://cds.climate.copernicus.eu/")
    print()
    print("  2. API key from:")
    print("     https://cds.climate.copernicus.eu/api-how-to")
    print()
    print("  3. Set up credentials:")
    print("     Option A: Create ~/.cdsapirc file with:")
    print("        url: https://cds.climate.copernicus.eu/api/v2")
    print("        key: YOUR_UID:YOUR_API_KEY")
    print()
    print("     Option B: Set environment variable:")
    print("        export CDS_API_KEY='YOUR_UID:YOUR_API_KEY'")
    print()
    print("     Option C: Pass as argument:")
    print("        python3 download_era5_land.py --api-key YOUR_UID:YOUR_API_KEY")
    print()
    
    api_key = input("Enter API key (UID:KEY) or press Enter to use .cdsapirc: ").strip()
    if api_key:
        return api_key
    
    return None

def download_era5_land(api_key=None):
    """Download ERA5-Land data for Didal Glacier."""
    
    # Check if cdsapi is available
    available, cdsapi_module = check_cdsapi()
    if not available:
        return False
    
    # Initialize client
    if api_key:
        # Parse UID and KEY
        if ':' in api_key:
            uid, key = api_key.split(':', 1)
            client = cdsapi_module.Client(url="https://cds.climate.copernicus.eu/api/v2", key=f"{uid}:{key}")
        else:
            print("❌ Error: API key must be in format 'UID:KEY'")
            return False
    else:
        # Use .cdsapirc or environment variable
        client = cdsapi_module.Client()
    
    print("=" * 60)
    print("Downloading ERA5-Land Climate Data")
    print("=" * 60)
    print()
    print(f"Study Area: {GLACIER_LAT}°N, {GLACIER_LON}°E")
    print(f"Date Range: {START_DATE} to {END_DATE}")
    print(f"Variables: 2m temperature, total precipitation, snow water equivalent")
    print()
    
    # ERA5-Land grid resolution is 0.1° (~9 km)
    # Find grid cell containing glacier
    # Round to nearest 0.1°
    grid_lat = round(GLACIER_LAT * 10) / 10
    grid_lon = round(GLACIER_LON * 10) / 10
    
    print(f"Grid cell: {grid_lat}°N, {grid_lon}°E (0.1° resolution)")
    print()
    
    # Define area (small region around glacier)
    # ERA5-Land uses North, West, South, East format
    area = [
        grid_lat + 0.05,  # North
        grid_lon - 0.05,  # West
        grid_lat - 0.05,  # South
        grid_lon + 0.05,  # East
    ]
    
    print(f"Download area: {area[2]}°N to {area[0]}°N, {area[1]}°E to {area[3]}°E")
    print()
    
    # Download by month to avoid cost limits
    # CDS has limits on request size, so we download month by month
    months = [
        ('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
        ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'),
        ('09', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')
    ]
    
    downloaded_files = []
    
    print("📥 Starting downloads (month by month to avoid size limits)...")
    print()
    
    for month_num, month_name in months:
        print(f"📅 Downloading {month_name} 2025...")
        
        # Days for this month
        if month_num in ['01', '03', '05', '07', '08', '10', '12']:
            days = [f'{i:02d}' for i in range(1, 32)]
        elif month_num == '02':
            days = [f'{i:02d}' for i in range(1, 29)]  # 2025 is not a leap year
        else:
            days = [f'{i:02d}' for i in range(1, 31)]
        
        # Request parameters for this month
        request_params = {
            'product_type': 'reanalysis',
            'variable': [
                '2m_temperature',           # 2m air temperature
                'total_precipitation',      # Total precipitation
                'snow_depth_water_equivalent',  # Snow water equivalent
            ],
            'year': '2025',
            'month': month_num,
            'day': days,
            'time': [
                '00:00', '01:00', '02:00', '03:00', '04:00', '05:00',
                '06:00', '07:00', '08:00', '09:00', '10:00', '11:00',
                '12:00', '13:00', '14:00', '15:00', '16:00', '17:00',
                '18:00', '19:00', '20:00', '21:00', '22:00', '23:00'
            ],
            'area': area,  # North, West, South, East
            'format': 'netcdf',
        }
        
        # Output filename for this month
        output_file = os.path.join(OUTPUT_DIR, f"ERA5-Land_Didal_Glacier_2025_{month_num}.nc")
        
        try:
            # Submit request
            client.retrieve(
                'reanalysis-era5-land',
                request_params,
                output_file
            )
            
            # Check file size
            if os.path.exists(output_file):
                size_mb = os.path.getsize(output_file) / (1024 * 1024)
                print(f"   ✅ Downloaded: {size_mb:.1f} MB")
                downloaded_files.append(output_file)
            else:
                print(f"   ⚠️  File not found after download")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            print(f"   ⚠️  Skipping {month_name}, will retry later")
            continue
        
        print()
    
    # Summary
    print("=" * 60)
    if downloaded_files:
        print(f"✅ Download Complete! ({len(downloaded_files)}/12 months)")
        print("=" * 60)
        print()
        print("Downloaded files:")
        total_size = 0
        for f in downloaded_files:
            size_mb = os.path.getsize(f) / (1024 * 1024)
            total_size += size_mb
            print(f"   - {os.path.basename(f)} ({size_mb:.1f} MB)")
        print()
        print(f"Total size: {total_size:.1f} MB")
        print()
        print("📋 Next steps:")
        print("   1. Merge monthly files into one annual file (optional)")
        print("   2. Extract grid cell at 38.97°N, 70.75°E")
        print("   3. Compute climate derivatives:")
        print("      - PDD (Positive Degree Days)")
        print("      - SWE metrics (SWE_max, SWE_max date, days to SWE_0)")
        print("      - MLT (Melt-rate proxy)")
        print("      - ROS (Rain-on-Snow potential)")
        print()
        return True
    else:
        print("❌ No files downloaded")
        print("=" * 60)
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Download ERA5-Land climate data for Didal Glacier study'
    )
    parser.add_argument(
        '--api-key',
        type=str,
        help='CDS API key in format UID:KEY'
    )
    
    args = parser.parse_args()
    
    # Get API key
    api_key = get_api_key(args.api_key)
    
    # Download data
    success = download_era5_land(api_key)
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()

