#!/usr/bin/env python3
"""
Download SRTM 30m DEM for Tajikistan
Uses elevation package or manual download instructions
"""

import os
import sys

# Tajikistan extent
TAJIKISTAN_BOUNDS = {
    'west': 67.0,   # Longitude
    'south': 36.0,  # Latitude
    'east': 75.0,
    'north': 41.0
}

def download_srtm_elevation():
    """Download SRTM using elevation package."""
    try:
        import elevation
        print("=" * 70)
        print("DOWNLOADING SRTM 30m DEM FOR TAJIKISTAN")
        print("=" * 70)
        print()
        print(f"Area: {TAJIKISTAN_BOUNDS['west']}°E to {TAJIKISTAN_BOUNDS['east']}°E")
        print(f"      {TAJIKISTAN_BOUNDS['south']}°N to {TAJIKISTAN_BOUNDS['north']}°N")
        print()
        
        output_file = "satellite_data/dem/srtm_tajikistan.tif"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        print("Downloading SRTM data...")
        print("(This may take several minutes depending on connection speed)")
        print()
        
        elevation.clip(
            bounds=(
                TAJIKISTAN_BOUNDS['west'],
                TAJIKISTAN_BOUNDS['south'],
                TAJIKISTAN_BOUNDS['east'],
                TAJIKISTAN_BOUNDS['north']
            ),
            output=output_file
        )
        
        print()
        print(f"✅ SRTM DEM downloaded: {output_file}")
        print()
        print("Next steps:")
        print("1. Load into QGIS")
        print("2. Create hillshade")
        print("3. Style with elevation colors")
        print("4. Create 3D visualization")
        
        return True
        
    except ImportError:
        print("=" * 70)
        print("ELEVATION PACKAGE NOT INSTALLED")
        print("=" * 70)
        print()
        print("Install with: pip install elevation")
        print()
        print("OR download manually from USGS EarthExplorer:")
        print("1. Go to: https://earthexplorer.usgs.gov/")
        print("2. Register (free)")
        print("3. Search: SRTM 1 Arc-Second Global")
        print("4. Area: Tajikistan (67-75°E, 36-41°N)")
        print("5. Download tiles")
        print()
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        print()
        print("Try manual download from USGS EarthExplorer instead")
        return False

if __name__ == "__main__":
    download_srtm_elevation()

