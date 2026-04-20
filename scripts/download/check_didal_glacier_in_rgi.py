#!/usr/bin/env python3
"""
Check RGI files for Didal Glacier and extract outline if found.
"""

import os
from pathlib import Path
import sys

# Didal Glacier location
GLACIER_LAT = 38.97
GLACIER_LON = 70.75

# RGI file locations
RGI_FILES = [
    os.path.expanduser("~/Desktop/writing_paper/tajikistan/PIN_glaciers/data/data_work/v7/RGI2000-v7.0-G-13_central_asia.shp"),
    os.path.expanduser("~/Desktop/writing_paper/tajikistan/SINDy_glaciers/data/data_work/v7/RGI2000-v7.0-G-13_central_asia.shp"),
    os.path.expanduser("~/Desktop/writing_paper/tajikistan/revised TC paper/central_asia/data/v6/13_rgi60_CentralAsia.shp"),
]

def check_rgi_file(rgi_path):
    """Check if RGI file exists and contains Didal Glacier."""
    print("=" * 70)
    print(f"Checking: {os.path.basename(rgi_path)}")
    print("=" * 70)
    
    if not os.path.exists(rgi_path):
        print(f"❌ File not found: {rgi_path}")
        return None
    
    print(f"✅ File exists: {rgi_path}")
    
    try:
        # Try using geopandas
        try:
            import geopandas as gpd
            from shapely.geometry import Point
            
            print("\nLoading RGI shapefile...")
            gdf = gpd.read_file(rgi_path)
            
            print(f"✅ Loaded successfully!")
            print(f"   Total glaciers: {len(gdf)}")
            print(f"   CRS: {gdf.crs}")
            
            # Get bounds
            bounds = gdf.total_bounds
            print(f"   Bounds: {bounds[0]:.4f}°E to {bounds[2]:.4f}°E")
            print(f"            {bounds[1]:.4f}°N to {bounds[3]:.4f}°N")
            
            # Check if glacier location is within bounds
            in_bounds = (bounds[0] <= GLACIER_LON <= bounds[2] and 
                        bounds[1] <= GLACIER_LAT <= bounds[3])
            
            if not in_bounds:
                print(f"\n⚠️  Glacier location ({GLACIER_LON}°E, {GLACIER_LAT}°N) is OUTSIDE bounds")
                return None
            
            print(f"\n✅ Glacier location is WITHIN bounds!")
            
            # Create point for Didal Glacier
            glacier_point = Point(GLACIER_LON, GLACIER_LAT)
            
            # Set CRS if needed
            if gdf.crs is None:
                gdf.set_crs("EPSG:4326", inplace=True)
            
            # Ensure glacier point has same CRS
            if gdf.crs != "EPSG:4326":
                from pyproj import Transformer
                transformer = Transformer.from_crs("EPSG:4326", gdf.crs, always_xy=True)
                x, y = transformer.transform(GLACIER_LON, GLACIER_LAT)
                glacier_point = Point(x, y)
            
            # Find glaciers containing the point
            print("\nSearching for glaciers containing Didal Glacier location...")
            containing = gdf[gdf.geometry.contains(glacier_point)]
            
            if len(containing) > 0:
                print(f"✅ Found {len(containing)} glacier(s) containing the location!")
                for idx, row in containing.iterrows():
                    name = row.get('Name', row.get('GLIMS_NAME', row.get('RGIId', 'Unknown')))
                    print(f"   - {name}")
                    print(f"     RGI ID: {row.get('RGIId', 'N/A')}")
                    print(f"     Area: {row.get('Area', 'N/A')} km²")
                
                # Return the first match
                return containing.iloc[0]
            else:
                print("⚠️  No glacier polygon contains the exact location")
                
                # Find nearest glacier
                print("\nFinding nearest glacier...")
                gdf['distance'] = gdf.geometry.distance(glacier_point)
                nearest = gdf.loc[gdf['distance'].idxmin()]
                
                # Convert distance to km (approximate)
                if gdf.crs == "EPSG:4326":
                    dist_km = nearest['distance'] * 111  # Rough conversion
                else:
                    dist_km = nearest['distance'] / 1000  # Assume meters
                
                name = nearest.get('Name', nearest.get('GLIMS_NAME', nearest.get('RGIId', 'Unknown')))
                print(f"   Nearest glacier: {name}")
                print(f"   Distance: {dist_km:.2f} km")
                print(f"   RGI ID: {nearest.get('RGIId', 'N/A')}")
                
                if dist_km < 5:  # Within 5 km
                    print(f"   ✅ Very close! This might be Didal Glacier or a nearby glacier")
                    return nearest
                else:
                    print(f"   ⚠️  Too far away - might not be Didal Glacier")
                    return None
            
        except ImportError as e:
            print(f"❌ Error importing geopandas: {e}")
            print("   Trying alternative method...")
            return None
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            import traceback
            traceback.print_exc()
            return None
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

def extract_glacier_outline(glacier_row, output_path):
    """Extract glacier outline to a new shapefile."""
    try:
        import geopandas as gpd
        
        # Create GeoDataFrame with single glacier
        gdf_out = gpd.GeoDataFrame([glacier_row], crs=glacier_row.geometry.crs if hasattr(glacier_row.geometry, 'crs') else None)
        
        # Save to shapefile
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        gdf_out.to_file(output_path)
        
        print(f"\n✅ Glacier outline saved to: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Error saving outline: {e}")
        return False

def main():
    print("=" * 70)
    print("CHECKING RGI FILES FOR DIDAL GLACIER")
    print("=" * 70)
    print(f"\nGlacier location: {GLACIER_LAT}°N, {GLACIER_LON}°E")
    print()
    
    found_glacier = None
    found_file = None
    
    # Check each RGI file
    for rgi_file in RGI_FILES:
        result = check_rgi_file(rgi_file)
        if result is not None:
            found_glacier = result
            found_file = rgi_file
            print("\n" + "=" * 70)
            print("✅ DIDAL GLACIER FOUND!")
            print("=" * 70)
            break
        print()
    
    if found_glacier is None:
        print("\n" + "=" * 70)
        print("⚠️  DIDAL GLACIER NOT FOUND IN RGI FILES")
        print("=" * 70)
        print("\nPossible reasons:")
        print("  1. Glacier might be named differently")
        print("  2. Glacier might be too small to be in RGI")
        print("  3. Location might be slightly different")
        print("\nNext steps:")
        print("  - Check GLIMS database")
        print("  - Manually digitize from satellite imagery")
        print("  - Use QGIS to search by location")
        return
    
    # Extract outline
    output_path = "satellite_data/dem/processed/didal_glacier_rgi_outline.shp"
    print(f"\nExtracting glacier outline...")
    if extract_glacier_outline(found_glacier, output_path):
        print(f"\n✅ SUCCESS! Glacier outline extracted")
        print(f"   File: {output_path}")
        print(f"\nYou can now use this outline in:")
        print("  - Figure 1 (Study Area map)")
        print("  - QGIS for visualization")
        print("  - Further analysis")
    else:
        print(f"\n⚠️  Could not save outline, but glacier was found in: {found_file}")

if __name__ == "__main__":
    main()

