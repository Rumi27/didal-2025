#!/usr/bin/env python3
"""
Master script to download imagery from multiple satellite sources.
Coordinates downloads from Sentinel-2, Landsat, and Planet.
"""

import os
import json
from datetime import datetime

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

# Output directories
OUTPUT_DIRS = {
    "sentinel2": "satellite_data/sentinel2",
    "landsat": "satellite_data/landsat",
    "planet": "satellite_data/planet",
    "corona": "satellite_data/corona"
}

for dir_path in OUTPUT_DIRS.values():
    os.makedirs(dir_path, exist_ok=True)

def create_aoi_geojson():
    """
    Create AOI GeoJSON file for all downloads.
    """
    aoi = {
        "type": "Feature",
        "properties": {
            "name": "Didal Glacier AOI",
            "description": "Area of Interest for Didal Glacier failure event"
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [GLACIER_CENTER_LON - 0.05, GLACIER_CENTER_LAT - 0.05],
                [GLACIER_CENTER_LON + 0.05, GLACIER_CENTER_LAT - 0.05],
                [GLACIER_CENTER_LON + 0.05, GLACIER_CENTER_LAT + 0.05],
                [GLACIER_CENTER_LON - 0.05, GLACIER_CENTER_LAT + 0.05],
                [GLACIER_CENTER_LON - 0.05, GLACIER_CENTER_LAT - 0.05]
            ]]
        }
    }
    
    aoi_file = "satellite_data/aoi.geojson"
    with open(aoi_file, 'w') as f:
        json.dump(aoi, f, indent=2)
    
    return aoi_file

def print_download_guide():
    """
    Print comprehensive guide for downloading satellite imagery.
    """
    print("=" * 60)
    print("Satellite Imagery Download Guide - Didal Glacier")
    print("=" * 60)
    print()
    print(f"Study Area: {GLACIER_CENTER_LAT}°N, {GLACIER_CENTER_LON}°E")
    print(f"Time Period: September - November 2025")
    print()
    
    # Create AOI file
    aoi_file = create_aoi_geojson()
    print(f"AOI GeoJSON created: {aoi_file}")
    print()
    
    print("=" * 60)
    print("1. SENTINEL-2 (Copernicus)")
    print("=" * 60)
    print("  Resolution: 10-20 m")
    print("  Revisit: 5 days")
    print("  Best for: Multi-temporal analysis, change detection")
    print()
    print("  Setup:")
    print("    1. Register (free): https://scihub.copernicus.eu/dhus/#/self-registration")
    print("    2. Install: pip install sentinelsat")
    print("    3. Run: python download_sentinel2.py --username USER --password PASS")
    print()
    print("  Manual download: https://scihub.copernicus.eu/")
    print()
    
    print("=" * 60)
    print("2. LANDSAT (USGS)")
    print("=" * 60)
    print("  Resolution: 30 m (15 m panchromatic)")
    print("  Revisit: 16 days")
    print("  Best for: Long-term monitoring, historical comparison")
    print()
    print("  Setup:")
    print("    1. Register (free): https://earthexplorer.usgs.gov/")
    print("    2. Install: pip install landsatxplore")
    print("    3. Run: python download_landsat.py --username USER --password PASS")
    print()
    print("  Manual download: https://earthexplorer.usgs.gov/")
    print()
    
    print("=" * 60)
    print("3. PLANET (Already have some)")
    print("=" * 60)
    print("  Resolution: 3 m")
    print("  Revisit: Daily")
    print("  Best for: High-resolution time series, event documentation")
    print()
    print("  Status: Already downloaded October 28, 2025 image")
    print("  Additional images available via:")
    print("    - Planet Explorer: https://www.planet.com/explorer/")
    print("    - Python script: download_key_dates_images.py")
    print()
    
    print("=" * 60)
    print("4. CORONA (Historical - Not for 2025 events)")
    print("=" * 60)
    print("  Resolution: 1.8-2.7 m")
    print("  Period: 1960s-1970s")
    print("  Best for: Historical baseline, long-term change")
    print()
    print("  Note: Corona imagery is from 1960s-1970s, not relevant for 2025 events")
    print("  But useful for historical comparison if needed")
    print()
    print("  Download: https://earthexplorer.usgs.gov/")
    print("    Search: Declassified Data > CORONA")
    print()
    
    print("=" * 60)
    print("Recommended Workflow")
    print("=" * 60)
    print()
    print("1. Sentinel-2: Primary data source for multi-temporal analysis")
    print("   - Download for all key dates")
    print("   - Use for change detection, velocity mapping")
    print()
    print("2. Landsat: Complementary data, longer historical context")
    print("   - Download for key dates")
    print("   - Use for comparison with historical events")
    print()
    print("3. Planet: High-resolution documentation")
    print("   - Already have Oct 28, 2025")
    print("   - Download additional key dates if available")
    print()
    print("4. Integration: Combine all sources for comprehensive analysis")
    print()
    
    # Save summary
    summary = {
        "study_area": {
            "center": [GLACIER_CENTER_LAT, GLACIER_CENTER_LON],
            "aoi_file": aoi_file
        },
        "key_dates": KEY_DATES,
        "satellite_sources": {
            "sentinel2": {
                "resolution": "10-20 m",
                "revisit": "5 days",
                "registration": "https://scihub.copernicus.eu/dhus/#/self-registration"
            },
            "landsat": {
                "resolution": "30 m",
                "revisit": "16 days",
                "registration": "https://earthexplorer.usgs.gov/"
            },
            "planet": {
                "resolution": "3 m",
                "revisit": "Daily",
                "status": "Already have Oct 28, 2025"
            }
        }
    }
    
    summary_file = "satellite_data/download_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"Summary saved to: {summary_file}")


if __name__ == "__main__":
    print_download_guide()

