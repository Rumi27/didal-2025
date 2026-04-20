#!/usr/bin/env python3
"""
Quick check for Sentinel-2 data availability over Didal Glacier.

This script provides guidance on checking Sentinel-2 cloud-free scenes
for optical offset tracking validation.

Area of Interest: Didal Glacier
- Latitude: 38.99°N
- Longitude: 70.72°E
- Date Range: September 7 – October 31, 2025
- Required: Cloud cover <20% over glacier area

Data Sources to Check:
1. Copernicus Data Space (recommended): https://dataspace.copernicus.eu/
2. Google Earth Engine (programmatic access)
3. USGS EarthExplorer (alternative)

Usage:
    python check_sentinel2_availability.py
"""

import sys
from datetime import datetime

# Didal Glacier location
LATITUDE = 38.99
LONGITUDE = 70.72
GLACIER_NAME = "Didal Glacier"

# Study period
START_DATE = "2025-09-07"
END_DATE = "2025-10-31"

# Cloud cover threshold
MAX_CLOUD_COVER = 20  # percent


def print_search_instructions():
    """Print instructions for manual Sentinel-2 data search."""
    
    print("=" * 80)
    print("SENTINEL-2 DATA AVAILABILITY CHECK")
    print("=" * 80)
    print()
    print(f"Glacier: {GLACIER_NAME}")
    print(f"Location: {LATITUDE}°N, {LONGITUDE}°E")
    print(f"Date Range: {START_DATE} to {END_DATE}")
    print(f"Cloud Cover Threshold: <{MAX_CLOUD_COVER}%")
    print()
    
    print("=" * 80)
    print("METHOD 1: Copernicus Data Space (RECOMMENDED)")
    print("=" * 80)
    print()
    print("1. Visit: https://dataspace.copernicus.eu/")
    print()
    print("2. Click 'Browser' or 'Search'")
    print()
    print("3. Set Search Parameters:")
    print(f"   - Mission: Sentinel-2")
    print(f"   - Product Type: S2MSI1C (Level-1C, Top of Atmosphere)")
    print(f"   - Time Range: {START_DATE} to {END_DATE}")
    print(f"   - Area: Draw polygon or enter coordinates:")
    print(f"     * Center: {LATITUDE}°N, {LONGITUDE}°E")
    print(f"     * Radius: ~5 km (to cover glacier and surrounding area)")
    print(f"   - Cloud Cover: 0–{MAX_CLOUD_COVER}%")
    print()
    print("4. Review Results:")
    print("   - Look for scenes with low cloud cover over glacier area")
    print("   - Need ≥2 cloud-free scenes for temporal pairs")
    print("   - Ideal: 2–3 scene pairs spanning surge period")
    print()
    print("5. Check Preview Images:")
    print("   - Click on each scene")
    print("   - Verify glacier is visible (not obscured by clouds)")
    print("   - Note: Glacier may have snow cover (white), but should not have clouds")
    print()
    print("6. Record Usable Scenes:")
    print("   - Note dates of cloud-free acquisitions")
    print("   - Download or bookmark for later processing")
    print()
    
    print("=" * 80)
    print("METHOD 2: Google Earth Engine (PROGRAMMATIC)")
    print("=" * 80)
    print()
    print("If you have GEE access, run this query in Code Editor:")
    print()
    print("```javascript")
    print("// Define area of interest")
    print(f"var point = ee.Geometry.Point([{LONGITUDE}, {LATITUDE}]);")
    print("var aoi = point.buffer(5000); // 5 km radius")
    print()
    print("// Load Sentinel-2 collection")
    print("var s2 = ee.ImageCollection('COPERNICUS/S2')")
    print(f"  .filterBounds(aoi)")
    print(f"  .filterDate('{START_DATE}', '{END_DATE}')")
    print(f"  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', {MAX_CLOUD_COVER}));")
    print()
    print("// Print results")
    print("print('Number of scenes:', s2.size());")
    print("print('Scene dates:', s2.aggregate_array('system:index'));")
    print()
    print("// Visualize")
    print("Map.centerObject(aoi, 12);")
    print("Map.addLayer(s2.median(), {bands: ['B4', 'B3', 'B2'], min: 0, max: 3000}, 'S2 Median');")
    print("```")
    print()
    
    print("=" * 80)
    print("WHAT TO LOOK FOR")
    print("=" * 80)
    print()
    print("✅ GOOD SIGNS:")
    print("   - ≥2 cloud-free scenes during surge period")
    print("   - Temporal separation: 6–12 days ideal")
    print("   - Glacier clearly visible in preview (white snow is OK, clouds are NOT)")
    print("   - Consistent illumination (avoid dawn/dusk scenes)")
    print()
    print("❌ BAD SIGNS:")
    print("   - Persistent cloud cover over glacier area")
    print("   - Only 1 cloud-free scene (need ≥2 for pairs)")
    print("   - Large temporal gaps (>3 weeks between usable scenes)")
    print("   - Glacier obscured by clouds in preview images")
    print()
    
    print("=" * 80)
    print("NEXT STEPS AFTER CHECKING")
    print("=" * 80)
    print()
    print("IF ≥2 CLOUD-FREE SCENES AVAILABLE:")
    print("   1. Download scenes (L1C or L2A)")
    print("   2. Process with optical offset tracking:")
    print("      - COSI-Corr (ENVI/IDL)")
    print("      - GeFolki (Python, open-source)")
    print("      - ImGRAFT (MATLAB/Python)")
    print("      - Simple OpenCV feature tracking")
    print("   3. Compare optical velocities with SAR Vindex")
    print("   4. Update manuscript with optical validation results")
    print()
    print("IF INSUFFICIENT CLOUD-FREE SCENES:")
    print("   1. Document specific findings:")
    print("      - Number of scenes checked")
    print("      - Mean cloud cover during study period")
    print("      - Why optical validation not feasible")
    print("   2. Add to Methods section:")
    print('      "Sentinel-2 optical offset tracking was not feasible due to')
    print('       persistent cloud cover during the surge period (mean X%)"')
    print("   3. Focus on other validation methods:")
    print("      - Manual SNAP 32px (2 pairs)")
    print("      - ITS_LIVE comparison")
    print("      - PlanetScope terminus displacement (already have)")
    print()
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("This check should take 15–30 minutes.")
    print()
    print("If Sentinel-2 data IS available:")
    print("   → This becomes PRIMARY validation approach (high impact)")
    print("   → Worth investing 4–6 hours in optical processing")
    print("   → Provides independent cross-check of SAR results")
    print()
    print("If Sentinel-2 data NOT available:")
    print("   → Document why explicitly in manuscript")
    print("   → Focus on other validation methods")
    print("   → Still demonstrates thoroughness (checked all options)")
    print()
    print("=" * 80)
    print()
    print("Ready to check? Visit: https://dataspace.copernicus.eu/")
    print()


if __name__ == "__main__":
    print_search_instructions()
    
    print("\nNote: This is a guidance script. Actual data search must be done manually")
    print("      at Copernicus Data Space or using Google Earth Engine.")
    print()
