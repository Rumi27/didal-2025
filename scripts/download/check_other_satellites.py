#!/usr/bin/env python3
"""
Check availability of satellite imagery from multiple sources:
- Corona (historical, USGS)
- Landsat (USGS)
- Sentinel-2 (Copernicus)

For Didal Glacier location: 39.0005°N, 70.7385°E
Time period: September - November 2025
"""

import json
from datetime import datetime, timedelta

# Study area
GLACIER_LAT = 39.0005
GLACIER_LON = 70.7385
GLACIER_NAME = "Didal Glacier"

# Time period
START_DATE = "2025-09-01"
END_DATE = "2025-11-30"

# Area of interest (buffer around glacier)
BUFFER_DEG = 0.1  # ~11 km

print("=" * 70)
print("Satellite Imagery Availability Check - Didal Glacier")
print("=" * 70)
print()
print(f"Location: {GLACIER_LAT:.6f}°N, {GLACIER_LON:.6f}°E")
print(f"Time period: {START_DATE} to {END_DATE}")
print(f"Area: {GLACIER_LAT - BUFFER_DEG:.4f}°N to {GLACIER_LAT + BUFFER_DEG:.4f}°N")
print(f"       {GLACIER_LON - BUFFER_DEG:.4f}°E to {GLACIER_LON + BUFFER_DEG:.4f}°E")
print()

# Create GeoJSON for area of interest
aoi_geojson = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "name": "Didal Glacier Study Area",
                "glacier": GLACIER_NAME,
                "buffer_km": BUFFER_DEG * 111
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [GLACIER_LON - BUFFER_DEG, GLACIER_LAT - BUFFER_DEG],
                    [GLACIER_LON + BUFFER_DEG, GLACIER_LAT - BUFFER_DEG],
                    [GLACIER_LON + BUFFER_DEG, GLACIER_LAT + BUFFER_DEG],
                    [GLACIER_LON - BUFFER_DEG, GLACIER_LAT + BUFFER_DEG],
                    [GLACIER_LON - BUFFER_DEG, GLACIER_LAT - BUFFER_DEG]
                ]]
            }
        }
    ]
}

# Save AOI GeoJSON
aoi_file = "satellite_data/aoi_didal_glacier.geojson"
import os
os.makedirs("satellite_data", exist_ok=True)
with open(aoi_file, 'w') as f:
    json.dump(aoi_geojson, f, indent=2)

print(f"✓ Saved AOI GeoJSON: {aoi_file}")
print()

# 1. CORONA (Historical - 1960s-1970s only)
print("=" * 70)
print("1. CORONA (Declassified Historical Imagery)")
print("=" * 70)
print()
print("⚠️  NOTE: Corona imagery is from 1960s-1970s only (not 2025)")
print("   Useful for: Long-term glacier change comparison")
print()
print("Access: USGS EarthExplorer")
print("URL: https://earthexplorer.usgs.gov/")
print()
print("Steps:")
print("  1. Register for free account: https://earthexplorer.usgs.gov/")
print("  2. Login and go to 'Search Criteria'")
print("  3. Draw polygon or enter coordinates:")
print(f"     Latitude: {GLACIER_LAT:.4f}°N")
print(f"     Longitude: {GLACIER_LON:.4f}°E")
print("  4. Go to 'Data Sets' tab")
print("  5. Select: Declassified Data > CORONA")
print("  6. Click 'Results' to see available scenes")
print("  7. Download selected scenes")
print()

# 2. LANDSAT
print("=" * 70)
print("2. LANDSAT (USGS)")
print("=" * 70)
print()
print("Access: USGS EarthExplorer")
print("URL: https://earthexplorer.usgs.gov/")
print()
print("Datasets:")
print("  - Landsat Collection 2 Level-2 (Surface Reflectance)")
print("  - Landsat 8 OLI/TIRS")
print("  - Landsat 9 OLI-2/TIRS-2")
print()
print("Revisit: ~16 days")
print("Resolution: 30 m (15 m panchromatic)")
print()
print("Steps:")
print("  1. Login to EarthExplorer")
print("  2. Search Criteria:")
print(f"     Area: {GLACIER_LAT:.4f}°N, {GLACIER_LON:.4f}°E")
print(f"     Date: {START_DATE} to {END_DATE}")
print("  3. Data Sets: Landsat > Landsat Collection 2 Level-2")
print("  4. Click 'Results'")
print("  5. Filter by cloud cover (< 30% recommended)")
print("  6. Download selected scenes")
print()
print("Alternative: USGS AppEEARS (for bulk downloads)")
print("URL: https://appeears.earthdatacloud.nasa.gov/")
print()

# 3. SENTINEL-2
print("=" * 70)
print("3. SENTINEL-2 (Copernicus)")
print("=" * 70)
print()
print("Access: Copernicus Data Space Ecosystem")
print("URL: https://dataspace.copernicus.eu/")
print()
print("⚠️  NOTE: Old SciHub is deprecated (use new Copernicus Data Space)")
print()
print("Product: Sentinel-2 Level-2A (Surface Reflectance)")
print("Revisit: ~5 days")
print("Resolution: 10-20 m")
print()
print("Steps:")
print("  1. Register for free account: https://dataspace.copernicus.eu/")
print("  2. Login")
print("  3. Use search interface:")
print(f"     Area: {GLACIER_LAT:.4f}°N, {GLACIER_LON:.4f}°E")
print(f"     Date: {START_DATE} to {END_DATE}")
print("     Product: Sentinel-2 Level-2A")
print("     Cloud cover: < 30%")
print("  4. Download selected products")
print()
print("Alternative: Google Earth Engine (for analysis without download)")
print("URL: https://earthengine.google.com/")
print()

# Create download instructions file
instructions = f"""
# Satellite Imagery Download Instructions - Didal Glacier

## Study Area
- Location: {GLACIER_LAT:.6f}°N, {GLACIER_LON:.6f}°E
- Glacier: {GLACIER_NAME}
- Time Period: {START_DATE} to {END_DATE}
- AOI GeoJSON: {aoi_file}

## 1. CORONA (Historical - 1960s-1970s)

**Note:** Corona imagery is from 1960s-1970s only, not 2025.
Useful for long-term glacier change comparison.

**Access:** USGS EarthExplorer
- URL: https://earthexplorer.usgs.gov/
- Free registration required

**Steps:**
1. Register/login to EarthExplorer
2. Search Criteria:
   - Draw polygon or enter: {GLACIER_LAT:.4f}°N, {GLACIER_LON:.4f}°E
   - Date: 1960-01-01 to 1972-12-31 (Corona period)
3. Data Sets: Declassified Data > CORONA
4. Click 'Results'
5. Download selected scenes

---

## 2. LANDSAT (USGS)

**Access:** USGS EarthExplorer
- URL: https://earthexplorer.usgs.gov/
- Free registration required

**Products:**
- Landsat Collection 2 Level-2 (Surface Reflectance)
- Landsat 8 OLI/TIRS
- Landsat 9 OLI-2/TIRS-2

**Specifications:**
- Resolution: 30 m (15 m panchromatic)
- Revisit: ~16 days
- Coverage: Global

**Steps:**
1. Login to EarthExplorer
2. Search Criteria:
   - Area: {GLACIER_LAT:.4f}°N, {GLACIER_LON:.4f}°E
   - Date: {START_DATE} to {END_DATE}
3. Data Sets: Landsat > Landsat Collection 2 Level-2
4. Click 'Results'
5. Filter by cloud cover (< 30% recommended)
6. Download selected scenes

**Alternative:** USGS AppEEARS (for bulk downloads)
- URL: https://appeears.earthdatacloud.nasa.gov/
- Allows batch processing and subsetting

---

## 3. SENTINEL-2 (Copernicus)

**Access:** Copernicus Data Space Ecosystem
- URL: https://dataspace.copernicus.eu/
- Free registration required

**⚠️ Important:** Old SciHub (scihub.copernicus.eu) is deprecated.
Use the new Copernicus Data Space Ecosystem.

**Product:** Sentinel-2 Level-2A (Surface Reflectance)

**Specifications:**
- Resolution: 10-20 m
- Revisit: ~5 days
- Coverage: Global

**Steps:**
1. Register/login to Copernicus Data Space Ecosystem
2. Use search interface:
   - Area: {GLACIER_LAT:.4f}°N, {GLACIER_LON:.4f}°E
   - Date: {START_DATE} to {END_DATE}
   - Product: Sentinel-2 Level-2A
   - Cloud cover: < 30%
3. Download selected products

**Alternative:** Google Earth Engine
- URL: https://earthengine.google.com/
- For analysis without downloading full scenes
- Requires Google account and EEE access

---

## Expected Availability (September-November 2025)

### Landsat:
- Revisit: ~16 days
- Expected scenes: ~6 scenes in 3-month period
- Cloud cover may be high in mountainous regions

### Sentinel-2:
- Revisit: ~5 days
- Expected scenes: ~18 scenes in 3-month period
- Better temporal coverage than Landsat
- Cloud cover may still be an issue

### Corona:
- Historical only (1960s-1970s)
- Not available for 2025 event
- Useful for baseline comparison

---

## Recommended Approach

1. **Primary:** Sentinel-2 (best temporal resolution)
2. **Secondary:** Landsat (complementary, longer archive)
3. **Historical:** Corona (for long-term change analysis)

## Notes

- Mountainous regions often have high cloud cover
- SAR data (Sentinel-1) may be necessary for continuous monitoring
- Planet imagery already provides high-resolution coverage for key dates
"""

with open("satellite_data/download_instructions.txt", 'w') as f:
    f.write(instructions)

print(f"✓ Saved download instructions: satellite_data/download_instructions.txt")
print()

# Create Python scripts for automated download (if libraries available)
print("=" * 70)
print("Automated Download Scripts")
print("=" * 70)
print()
print("Creating Python scripts for automated downloads...")
print("(Note: These require API access and may need authentication)")
print()

# Sentinel-2 download script
sentinel2_script = '''#!/usr/bin/env python3
"""
Download Sentinel-2 imagery from Copernicus Data Space Ecosystem.
Requires: Copernicus account and API credentials.
"""

import os
from datetime import datetime

# Study area
GLACIER_LAT = 39.0005
GLACIER_LON = 70.7385
START_DATE = "2025-09-01"
END_DATE = "2025-11-30"

# Note: This requires Copernicus Data Space Ecosystem API access
# See: https://documentation.dataspace.copernicus.eu/

print("Sentinel-2 Download Script")
print("=" * 60)
print()
print("This script requires:")
print("1. Copernicus Data Space Ecosystem account")
print("2. API credentials (OAuth2)")
print()
print("Manual download recommended via web interface:")
print("https://dataspace.copernicus.eu/")
print()
print(f"Search parameters:")
print(f"  Location: {GLACIER_LAT:.4f}°N, {GLACIER_LON:.4f}°E")
print(f"  Date: {START_DATE} to {END_DATE}")
print(f"  Product: Sentinel-2 Level-2A")
'''

with open("satellite_data/download_sentinel2_manual.py", 'w') as f:
    f.write(sentinel2_script)

# Landsat download script
landsat_script = '''#!/usr/bin/env python3
"""
Download Landsat imagery from USGS EarthExplorer.
Requires: USGS EarthExplorer account credentials.
"""

import os
from datetime import datetime

# Study area
GLACIER_LAT = 39.0005
GLACIER_LON = 70.7385
START_DATE = "2025-09-01"
END_DATE = "2025-11-30"

print("Landsat Download Script")
print("=" * 60)
print()
print("This script requires:")
print("1. USGS EarthExplorer account")
print("2. landsatxplore library: pip install landsatxplore")
print()
print("Manual download recommended via web interface:")
print("https://earthexplorer.usgs.gov/")
print()
print(f"Search parameters:")
print(f"  Location: {GLACIER_LAT:.4f}°N, {GLACIER_LON:.4f}°E")
print(f"  Date: {START_DATE} to {END_DATE}")
print(f"  Product: Landsat Collection 2 Level-2")
'''

with open("satellite_data/download_landsat_manual.py", 'w') as f:
    f.write(landsat_script)

print("✓ Created download scripts in satellite_data/")
print()
print("=" * 70)
print("Summary")
print("=" * 70)
print()
print("All instructions and scripts saved to: satellite_data/")
print()
print("Next steps:")
print("1. Review download_instructions.txt for detailed steps")
print("2. Register for accounts (if needed):")
print("   - USGS EarthExplorer (for Landsat/Corona)")
print("   - Copernicus Data Space (for Sentinel-2)")
print("3. Use web interfaces to search and download imagery")
print("4. Or use provided Python scripts (require API setup)")
print()

