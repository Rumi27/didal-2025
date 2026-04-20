#!/usr/bin/env python3
"""
Check RGI files for Didal Glacier using ogr (GDAL) command-line tools.
This avoids the geopandas library issue.
"""

import os
import subprocess
from pathlib import Path

# Didal Glacier location
GLACIER_LAT = 38.97
GLACIER_LON = 70.75

# RGI file locations
RGI_FILES = [
    os.path.expanduser("~/Desktop/writing_paper/tajikistan/PIN_glaciers/data/data_work/v7/RGI2000-v7.0-G-13_central_asia.shp"),
    os.path.expanduser("~/Desktop/writing_paper/tajikistan/SINDy_glaciers/data/data_work/v7/RGI2000-v7.0-G-13_central_asia.shp"),
    os.path.expanduser("~/Desktop/writing_paper/tajikistan/revised TC paper/central_asia/data/v6/13_rgi60_CentralAsia.shp"),
]

def check_rgi_with_ogr(rgi_path):
    """Check RGI file using ogrinfo."""
    rgi_path = os.path.expanduser(rgi_path)
    
    if not os.path.exists(rgi_path):
        print(f"❌ File not found: {rgi_path}")
        return None
    
    print(f"\n{'='*70}")
    print(f"Checking: {os.path.basename(rgi_path)}")
    print(f"{'='*70}")
    print(f"✅ File exists: {rgi_path}")
    
    try:
        # Get file info
        result = subprocess.run(
            ['ogrinfo', '-al', '-so', rgi_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"❌ Error reading file: {result.stderr}")
            return None
        
        print("\nFile information:")
        print(result.stdout[:500])  # First 500 chars
        
        # Get feature count
        count_result = subprocess.run(
            ['ogrinfo', '-al', rgi_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Count features
        feature_count = count_result.stdout.count('Feature')
        print(f"\n✅ Total glaciers in file: {feature_count}")
        
        # Try to search for Didal by name
        if 'Didal' in count_result.stdout or 'didal' in count_result.stdout.lower():
            print("\n✅ Found 'Didal' in file!")
            # Extract lines with Didal
            for line in count_result.stdout.split('\n'):
                if 'didal' in line.lower():
                    print(f"   {line[:200]}")
        
        return rgi_path
        
    except FileNotFoundError:
        print("❌ ogrinfo not found. Install GDAL: sudo apt-get install gdal-bin")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def create_qgis_script(rgi_path):
    """Create a QGIS Python script to check for Didal Glacier."""
    script = f"""
# QGIS Python script to find Didal Glacier in RGI
from qgis.core import *
from qgis.utils import iface

# Didal Glacier location
glacier_lat = 38.97
glacier_lon = 70.75

# Load RGI layer
rgi_path = r"{rgi_path}"
layer = iface.addVectorLayer(rgi_path, "RGI Central Asia", "ogr")

if layer is None:
    print("Error: Could not load layer")
else:
    print(f"Loaded: {{layer.name()}}")
    print(f"Features: {{layer.featureCount()}}")
    
    # Search for Didal
    for feature in layer.getFeatures():
        name = feature.attribute('Name') if 'Name' in feature.fields().names() else None
        if name and 'Didal' in str(name):
            print(f"Found: {{name}}")
            print(f"Geometry: {{feature.geometry()}}")
    
    # Find nearest to location
    from qgis.core import QgsPointXY
    point = QgsPointXY(glacier_lon, glacier_lat)
    # ... more code to find nearest
"""
    
    script_path = "check_rgi_in_qgis.py"
    with open(script_path, 'w') as f:
        f.write(script)
    
    print(f"\n✅ Created QGIS script: {script_path}")
    print("   You can run this in QGIS Python console")

def main():
    print("=" * 70)
    print("CHECKING RGI FILES FOR DIDAL GLACIER")
    print("=" * 70)
    print(f"\nGlacier location: {GLACIER_LAT}°N, {GLACIER_LON}°E")
    print("\nUsing ogrinfo (GDAL) to check files...")
    
    found_files = []
    
    for rgi_file in RGI_FILES:
        result = check_rgi_with_ogr(rgi_file)
        if result:
            found_files.append(result)
    
    if found_files:
        print(f"\n{'='*70}")
        print(f"✅ FOUND {len(found_files)} RGI FILE(S)")
        print(f"{'='*70}")
        print("\nNext steps:")
        print("  1. Load the RGI file in QGIS")
        print("  2. Search for Didal Glacier by location (38.97°N, 70.75°E)")
        print("  3. Or search by name if available")
        print("\nRecommended file to use:")
        print(f"  {found_files[0]}")
        
        # Create QGIS script
        create_qgis_script(found_files[0])
    else:
        print("\n⚠️  Could not check RGI files (ogrinfo not available)")

if __name__ == "__main__":
    main()

