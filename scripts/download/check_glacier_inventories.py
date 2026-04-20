#!/usr/bin/env python3
"""
Check GLIMS/RGI databases for Didal Glacier outline.
This script provides instructions and checks if glacier is in global inventories.
"""

import requests
import json

GLACIER_NAME = "Didal"
GLACIER_COORDS = (38.97, 70.75)  # Latitude, Longitude

def check_rgi_online():
    """
    Instructions for checking Randolph Glacier Inventory (RGI).
    RGI is available from: https://www.glims.org/RGI/
    """
    print("=" * 60)
    print("RANDOLPH GLACIER INVENTORY (RGI) CHECK")
    print("=" * 60)
    print("\nRGI Website: https://www.glims.org/RGI/")
    print("Download: https://www.glims.org/RGI/rgi60_dl.html")
    print("\nSteps:")
    print("1. Download RGI 6.0 shapefiles (Regional or Global)")
    print("2. Region of interest: Central Asia (Region 13)")
    print("3. Load in QGIS/Python and search for glacier near:")
    print(f"   Latitude: {GLACIER_COORDS[0]}°N")
    print(f"   Longitude: {GLACIER_COORDS[1]}°E")
    print("\nPython code to search:")
    print("""
import geopandas as gpd
import shapely.geometry as geom

# Load RGI shapefile
rgi = gpd.read_file('rgi60_13_central_asia.shp')

# Create point for glacier location
glacier_point = geom.Point(GLACIER_COORDS[1], GLACIER_COORDS[0])  # lon, lat

# Find nearby glaciers (within 0.1 degrees ~11 km)
buffer = glacier_point.buffer(0.1)
nearby = rgi[rgi.geometry.intersects(buffer)]

# Search by name
name_match = rgi[rgi['NAME'].str.contains('Didal', case=False, na=False)]

print(f"Found {len(nearby)} glaciers within 0.1 degrees")
print(f"Found {len(name_match)} glaciers with 'Didal' in name")
""")

def check_glims():
    """
    Instructions for checking GLIMS database.
    """
    print("\n" + "=" * 60)
    print("GLIMS DATABASE CHECK")
    print("=" * 60)
    print("\nGLIMS Website: https://www.glims.org/")
    print("Interactive Map: https://www.glims.org/maps/glims")
    print("\nSteps:")
    print("1. Go to GLIMS interactive map")
    print("2. Navigate to coordinates:")
    print(f"   {GLACIER_COORDS[0]}°N, {GLACIER_COORDS[1]}°E")
    print("3. Search for glaciers in Pamir Mountains, Tajikistan")
    print("4. Look for 'Didal' or nearby glaciers")
    print("\nAPI access (if available):")
    print("Some GLIMS data available via web services")

def manual_digitization_instructions():
    """
    Instructions for manual digitization from PlanetScope imagery.
    """
    print("\n" + "=" * 60)
    print("MANUAL DIGITIZATION FROM PLANETSCOPE")
    print("=" * 60)
    print("\nIf glacier is not in RGI/GLIMS, digitize from PlanetScope imagery:")
    print("\nAvailable PlanetScope scenes:")
    print("  - 20250917_064328_46_24b7_3B_AnalyticMS_SR.tif (Sep 17, 2025)")
    print("  - 20251025_062608_36_251d_3B_AnalyticMS_SR.tif (Oct 25, 2025)")
    print("  - 20251101_063201_24_2533_3B_AnalyticMS_SR.tif (Nov 1, 2025)")
    print("\nTools:")
    print("1. QGIS: Use 'Create Feature' tool to digitize polygon")
    print("2. Python: Use rasterio + matplotlib for interactive digitization")
    print("3. Google Earth: Digitize and export as KML")
    print("\nSteps in QGIS:")
    print("1. Load PlanetScope image")
    print("2. Create new shapefile layer (Polygon, WGS84)")
    print("3. Digitize glacier outline following ice/debris boundary")
    print("4. Save as GeoJSON or Shapefile")
    print("\nPython approach:")
    print("  Use 'rasterio' to load image, 'matplotlib' for visualization,")
    print("  and 'shapely' for polygon creation")

def create_summary():
    """Create summary document."""
    summary = f"""
# Glacier Outline Data Sources for Didal Glacier

**Glacier Location**: {GLACIER_COORDS[0]}°N, {GLACIER_COORDS[1]}°E
**Region**: Pamir Mountains, Tajikistan

## Recommended Approach (Priority Order):

### 1. Check RGI 6.0 (Randolph Glacier Inventory) ⭐ RECOMMENDED
- **Why**: Global standard, scientifically authoritative
- **Region**: Central Asia (Region 13)
- **Format**: Shapefile
- **Download**: https://www.glims.org/RGI/rgi60_dl.html
- **Search radius**: ~0.1 degrees (11 km) from coordinates

### 2. Check GLIMS Database
- **Why**: Comprehensive glacier inventory
- **Website**: https://www.glims.org/maps/glims
- **Search**: Interactive map or API

### 3. Manual Digitization from PlanetScope
- **When**: If not in RGI/GLIMS
- **Data**: 3 m resolution PlanetScope imagery (available)
- **Tool**: QGIS or Python
- **Accuracy**: High (3 m resolution)

## Next Steps:
1. Download RGI Central Asia shapefile
2. Search for glaciers near coordinates
3. If found, extract outline and use in Figure 1
4. If not found, digitize from PlanetScope imagery
"""
    return summary

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("GLACIER OUTLINE DATA SOURCES CHECK")
    print("=" * 60)
    print(f"\nGlacier: {GLACIER_NAME} Glacier")
    print(f"Location: {GLACIER_COORDS[0]}°N, {GLACIER_COORDS[1]}°E")
    print(f"Region: Pamir Mountains, Tajikistan")
    
    check_rgi_online()
    check_glims()
    manual_digitization_instructions()
    
    # Save summary
    summary = create_summary()
    with open('GLACIER_OUTLINE_CHECK.md', 'w') as f:
        f.write(summary)
    
    print("\n" + "=" * 60)
    print("✅ Summary saved to: GLACIER_OUTLINE_CHECK.md")
    print("=" * 60)

