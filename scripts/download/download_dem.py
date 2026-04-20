#!/usr/bin/env python3
"""
Download DEM (Digital Elevation Model) for Didal Glacier study.

Options:
1. SRTM 1 Arc-Second (30 m) - Recommended
2. ASTER GDEM v3 (30 m)

Study Area: 38.97°N, 70.75°E

Usage:
    python3 download_dem.py --source srtm
    python3 download_dem.py --source aster
"""

import os
import sys
import argparse
import math
from pathlib import Path
import urllib.request
import zipfile

# Study area coordinates
GLACIER_LAT = 38.97
GLACIER_LON = 70.75

# Output directory
OUTPUT_DIR = "satellite_data/dem"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_srtm_tile_name(lat, lon):
    """
    Get SRTM tile name from coordinates.
    SRTM tiles are named like: N38E070.hgt
    """
    # Round down to get tile boundaries
    lat_tile = int(math.floor(lat))
    lon_tile = int(math.floor(lon))
    
    # Format: N/S + latitude, E/W + longitude
    lat_str = f"N{lat_tile:02d}" if lat >= 0 else f"S{abs(lat_tile):02d}"
    lon_str = f"E{lon_tile:03d}" if lon >= 0 else f"W{abs(lon_tile):03d}"
    
    return f"{lat_str}{lon_str}"

def download_srtm_direct(tile_name):
    """
    Download SRTM tile directly from USGS servers.
    Note: This uses public SRTM data servers.
    """
    print(f"📥 Downloading SRTM tile: {tile_name}")
    
    # SRTM 1 Arc-Second (30m) download URLs
    # Try multiple sources
    urls = [
        f"https://e4ftl01.cr.usgs.gov/MEASURES/SRTMGL1.003/2000.02.11/{tile_name}.SRTMGL1.hgt.zip",
        f"https://dds.cr.usgs.gov/srtm/version2_1/SRTM1/Eurasia/{tile_name}.hgt.zip",
    ]
    
    output_file = os.path.join(OUTPUT_DIR, f"{tile_name}.hgt.zip")
    
    for url in urls:
        try:
            print(f"   Trying: {url}")
            urllib.request.urlretrieve(url, output_file)
            
            # Check if file is valid (not HTML error page)
            if os.path.getsize(output_file) > 1000:  # Real file should be >1KB
                print(f"   ✅ Downloaded: {output_file}")
                return output_file
            else:
                os.remove(output_file)
        except Exception as e:
            print(f"   ⚠️  Failed: {e}")
            if os.path.exists(output_file):
                os.remove(output_file)
            continue
    
    return None

def download_srtm_via_eodag():
    """
    Download SRTM using eodag library (if available).
    Requires: pip install eodag
    """
    try:
        from eodag import EODataAccessGateway
        
        print("📥 Downloading SRTM via eodag...")
        
        dag = EODataAccessGateway()
        
        # Configure for USGS
        dag.set_preferred_provider("usgs")
        
        # Search for SRTM
        search_criteria = {
            "productType": "SRTMGL1",
            "geom": {
                "type": "Point",
                "coordinates": [GLACIER_LON, GLACIER_LAT]
            },
            "bbox": [
                GLACIER_LON - 0.5, GLACIER_LAT - 0.5,
                GLACIER_LON + 0.5, GLACIER_LAT + 0.5
            ]
        }
        
        products = dag.search(**search_criteria)
        
        if products:
            print(f"   Found {len(products)} products")
            product = products[0]
            output_file = dag.download(product, outputs_prefix=OUTPUT_DIR)
            print(f"   ✅ Downloaded: {output_file}")
            return output_file
        else:
            print("   ⚠️  No products found")
            return None
            
    except ImportError:
        print("⚠️  eodag library not installed")
        print("   Install with: pip install eodag")
        return None
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def download_aster_gdem():
    """
    Download ASTER GDEM.
    Note: ASTER GDEM requires authentication via USGS EarthExplorer API.
    """
    print("⚠️  ASTER GDEM download requires USGS EarthExplorer account")
    print("   Recommendation: Use SRTM instead (easier, no account needed)")
    print()
    print("   For ASTER GDEM, use manual download from:")
    print("   https://earthexplorer.usgs.gov/")
    return None

def extract_dem_zip(zip_file):
    """Extract DEM from zip file."""
    if not zip_file or not os.path.exists(zip_file):
        return None
    
    print(f"📦 Extracting: {zip_file}")
    
    try:
        with zipfile.ZipFile(zip_file, 'r') as z:
            # Extract all files
            z.extractall(OUTPUT_DIR)
            
            # Find .hgt or .tif files
            extracted_files = []
            for f in z.namelist():
                if f.endswith('.hgt') or f.endswith('.tif') or f.endswith('.tiff'):
                    extracted_path = os.path.join(OUTPUT_DIR, f)
                    if os.path.exists(extracted_path):
                        extracted_files.append(extracted_path)
            
            print(f"   ✅ Extracted {len(extracted_files)} file(s)")
            return extracted_files[0] if extracted_files else None
            
    except Exception as e:
        print(f"   ❌ Extraction error: {e}")
        return None

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Download DEM for Didal Glacier study'
    )
    parser.add_argument(
        '--source',
        type=str,
        choices=['srtm', 'aster'],
        default='srtm',
        help='DEM source: srtm (recommended) or aster'
    )
    parser.add_argument(
        '--method',
        type=str,
        choices=['direct', 'eodag'],
        default='direct',
        help='Download method: direct (HTTP) or eodag (library)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Downloading DEM for Didal Glacier")
    print("=" * 60)
    print()
    print(f"Location: {GLACIER_LAT}°N, {GLACIER_LON}°E")
    print(f"Source: {args.source.upper()}")
    print(f"Method: {args.method}")
    print()
    
    if args.source == 'srtm':
        # Get SRTM tile name
        tile_name = get_srtm_tile_name(GLACIER_LAT, GLACIER_LON)
        print(f"SRTM tile covering glacier: {tile_name}")
        print()
        
        if args.method == 'direct':
            zip_file = download_srtm_direct(tile_name)
        else:
            zip_file = download_srtm_via_eodag()
        
        if zip_file:
            # Extract
            dem_file = extract_dem_zip(zip_file)
            
            if dem_file:
                print()
                print("=" * 60)
                print("✅ Download Complete!")
                print("=" * 60)
                print()
                print(f"DEM file: {dem_file}")
                print()
                print("📋 Next steps:")
                print("   1. Check DEM coverage (should cover glacier area)")
                print("   2. Reproject if needed (to match Sentinel-1)")
                print("   3. Compute derived products:")
                print("      - Slope map")
                print("      - Aspect map")
                print("      - Hillshade")
                print("      - Along-flowline profiles")
                print()
                return True
        
    elif args.source == 'aster':
        download_aster_gdem()
    
    print()
    print("=" * 60)
    print("❌ Download Failed")
    print("=" * 60)
    print()
    print("Alternative: Manual download from USGS EarthExplorer")
    print("   1. Go to: https://earthexplorer.usgs.gov/")
    print("   2. Draw area around 38.97°N, 70.75°E")
    print("   3. Select: SRTM 1 Arc-Second Global")
    print("   4. Download")
    print()
    
    return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

