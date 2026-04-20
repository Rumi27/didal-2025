#!/usr/bin/env python3
"""
Download SRTM DEM from OpenTopography
Alternative source for SRTM data
"""

import os
import urllib.request
import urllib.parse

# Tajikistan extent
TAJIKISTAN_BOUNDS = {
    'west': 67.0,
    'south': 36.0,
    'east': 75.0,
    'north': 41.0
}

# OpenTopography API endpoint
OPENTOPO_API = "https://cloud.sdsc.edu/v1/AUTH_opentopography/Raster/"

def download_opentopography_dem():
    """Download SRTM from OpenTopography."""
    print("=" * 70)
    print("DOWNLOAD SRTM FROM OPENTOPOGRAPHY")
    print("=" * 70)
    print()
    print("OpenTopography provides direct access to SRTM data")
    print()
    print("Manual download (recommended):")
    print("1. Go to: https://opentopography.org/")
    print("2. Click: 'Data' → 'Raster Data'")
    print("3. Select: 'SRTM'")
    print("4. Draw area or enter coordinates:")
    print(f"   West: {TAJIKISTAN_BOUNDS['west']}°")
    print(f"   East: {TAJIKISTAN_BOUNDS['east']}°")
    print(f"   South: {TAJIKISTAN_BOUNDS['south']}°")
    print(f"   North: {TAJIKISTAN_BOUNDS['north']}°")
    print("5. Download")
    print()
    print("=" * 70)
    print()
    print("OR try fixing EarthExplorer search criteria first!")
    print("See: FIX_EARTH_EXPLORER_SEARCH.md")

if __name__ == "__main__":
    download_opentopography_dem()

