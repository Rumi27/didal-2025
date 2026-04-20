#!/usr/bin/env python3
"""
Check for Glacier Inventory and DEM data on the system.
Searches for RGI, GGI, GLIMS, and ASTER GDEM data.
"""

import os
from pathlib import Path
import glob

# Search locations
SEARCH_LOCATIONS = [
    Path.home(),
    Path.home() / "Desktop",
    Path.home() / "Documents",
    Path.home() / "Downloads",
    Path("/home/chunlab/Desktop/writing_paper"),
]

# Search patterns
PATTERNS = {
    "RGI": ["*rgi*", "*randolph*glacier*", "*RGI*.shp", "*RGI*.zip"],
    "GGI": ["*ggi*", "*gamdam*", "*GGI*.shp", "*GGI*.zip"],
    "GLIMS": ["*glims*", "*GLIMS*.shp", "*GLIMS*.zip"],
    "ASTER_GDEM": ["*aster*", "*gdem*", "*ASTGTM*", "*ASTER*.tif", "*GDEM*.tif"],
}

def search_files(pattern_list, max_depth=5):
    """Search for files matching patterns."""
    found = []
    for location in SEARCH_LOCATIONS:
        if not location.exists():
            continue
        for pattern in pattern_list:
            # Search in location and subdirectories
            matches = list(location.rglob(pattern))
            found.extend(matches[:10])  # Limit per pattern
    return found

def main():
    print("=" * 70)
    print("SEARCHING FOR GLACIER INVENTORY AND DEM DATA")
    print("=" * 70)
    print()
    
    results = {}
    
    for data_type, patterns in PATTERNS.items():
        print(f"Searching for {data_type}...")
        found = search_files(patterns)
        results[data_type] = found
        
        if found:
            print(f"  ✅ Found {len(found)} files/directories:")
            for item in found[:5]:  # Show first 5
                size = ""
                if item.is_file():
                    try:
                        size = f" ({item.stat().st_size / (1024*1024):.1f} MB)"
                    except:
                        pass
                print(f"    - {item}{size}")
            if len(found) > 5:
                print(f"    ... and {len(found) - 5} more")
        else:
            print(f"  ⚠️  No {data_type} data found")
        print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    total_found = sum(len(v) for v in results.values())
    if total_found > 0:
        print(f"✅ Found data files/directories: {total_found}")
        print()
        print("Next steps:")
        print("  1. Check if RGI/GGI data covers Central Asia region")
        print("  2. Check if ASTER GDEM covers the Pamir Mountains area")
        print("  3. Verify data covers coordinates: 38.97°N, 70.75°E")
    else:
        print("⚠️  No glacier inventory or ASTER GDEM data found")
        print()
        print("You may need to download:")
        print("  - RGI: https://www.glims.org/RGI/")
        print("  - ASTER GDEM: https://earthexplorer.usgs.gov/")
    
    return results

if __name__ == "__main__":
    results = main()

