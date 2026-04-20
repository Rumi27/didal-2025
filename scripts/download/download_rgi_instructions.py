#!/usr/bin/env python3
"""
Download and search RGI (Randolph Glacier Inventory) for Didal Glacier.
Provides instructions and automated download if possible.
"""

import os
import sys

GLACIER_COORDS = (38.97, 70.75)  # Latitude, Longitude
RGI_REGION = 13  # Central Asia

def check_rgi_files():
    """Check if RGI files are already downloaded."""
    rgi_dir = 'satellite_data/rgi'
    if os.path.exists(rgi_dir):
        files = os.listdir(rgi_dir)
        shp_files = [f for f in files if f.endswith('.shp')]
        if shp_files:
            print(f"✅ Found RGI shapefiles: {shp_files}")
            return os.path.join(rgi_dir, shp_files[0])
    return None

def download_rgi_instructions():
    """Provide instructions for downloading RGI."""
    print("=" * 70)
    print("RGI (RANDOLPH GLACIER INVENTORY) DOWNLOAD INSTRUCTIONS")
    print("=" * 70)
    print(f"\nGlacier Location: {GLACIER_COORDS[0]}°N, {GLACIER_COORDS[1]}°E")
    print(f"Region: Central Asia (RGI Region {RGI_REGION})")
    print("\nDownload Options:")
    print("\n1. DIRECT DOWNLOAD (Recommended)")
    print("   URL: https://www.glims.org/RGI/rgi60_dl.html")
    print("   File: rgi60_13_central_asia.zip")
    print("   Size: ~50-100 MB")
    print("\n   Steps:")
    print("   1. Visit the URL above")
    print("   2. Download 'Region 13: Central Asia'")
    print("   3. Extract zip file")
    print("   4. Place shapefile in: satellite_data/rgi/")
    print("\n2. ALTERNATIVE: Use Google Earth Engine (if available)")
    print("   RGI is available as an asset in GEE")
    print("   Asset ID: users/nsidc/rgi60")
    print("\n3. PYTHON AUTOMATED (if URL is stable)")
    print("   Note: RGI download URLs may change, manual download recommended")
    
def search_rgi_python(rgi_file):
    """Search RGI shapefile for Didal Glacier."""
    try:
        import geopandas as gpd
        import shapely.geometry as geom
        
        print(f"\nLoading RGI file: {rgi_file}")
        rgi = gpd.read_file(rgi_file)
        print(f"✅ Loaded {len(rgi)} glaciers from RGI")
        
        # Create point for glacier location
        glacier_point = geom.Point(GLACIER_COORDS[1], GLACIER_COORDS[0])  # lon, lat
        
        # Find nearby glaciers (within 0.1 degrees ~11 km)
        buffer = glacier_point.buffer(0.1)
        nearby = rgi[rgi.geometry.intersects(buffer)]
        
        # Search by name (case insensitive)
        if 'NAME' in rgi.columns:
            name_match = rgi[rgi['NAME'].str.contains('Didal', case=False, na=False)]
        elif 'name' in rgi.columns:
            name_match = rgi[rgi['name'].str.contains('Didal', case=False, na=False)]
        else:
            name_match = gpd.GeoDataFrame()
        
        print(f"\n📊 Search Results:")
        print(f"   Glaciers within 0.1° (~11 km): {len(nearby)}")
        print(f"   Glaciers with 'Didal' in name: {len(name_match)}")
        
        if len(nearby) > 0:
            print(f"\n✅ Found {len(nearby)} nearby glacier(s)!")
            print("\nNearby glaciers:")
            for idx, row in nearby.iterrows():
                name = row.get('NAME', row.get('name', 'Unknown'))
                area = row.get('Area', row.get('area', 'N/A'))
                print(f"   - {name} (Area: {area} km²)")
            
            # Find closest glacier
            distances = nearby.geometry.distance(glacier_point)
            closest_idx = distances.idxmin()
            closest = nearby.loc[closest_idx]
            closest_name = closest.get('NAME', closest.get('name', 'Unknown'))
            closest_dist = distances.loc[closest_idx] * 111  # Convert degrees to km
            
            print(f"\n🎯 Closest glacier: {closest_name}")
            print(f"   Distance: {closest_dist:.2f} km")
            
            # Export closest glacier outline
            output_dir = 'satellite_data/dem/processed'
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, 'didal_glacier_rgi_outline.shp')
            
            closest_gdf = gpd.GeoDataFrame([closest], crs=rgi.crs)
            closest_gdf.to_file(output_file)
            print(f"✅ Exported glacier outline to: {output_file}")
            
            return output_file
        
        elif len(name_match) > 0:
            print(f"\n✅ Found {len(name_match)} glacier(s) with 'Didal' in name!")
            # Export first match
            output_dir = 'satellite_data/dem/processed'
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, 'didal_glacier_rgi_outline.shp')
            name_match.head(1).to_file(output_file)
            print(f"✅ Exported glacier outline to: {output_file}")
            return output_file
        
        else:
            print("\n❌ Didal Glacier not found in RGI")
            print("   Recommendation: Digitize manually from PlanetScope imagery")
            return None
            
    except ImportError:
        print("\n⚠️  geopandas not installed")
        print("   Install: pip install geopandas")
        return None
    except Exception as e:
        print(f"\n❌ Error searching RGI: {e}")
        return None

def main():
    """Main function."""
    print("\n" + "=" * 70)
    print("RGI GLACIER OUTLINE SEARCH FOR DIDAL GLACIER")
    print("=" * 70)
    
    # Check if RGI files exist
    rgi_file = check_rgi_files()
    
    if rgi_file:
        print(f"\n✅ RGI file found: {rgi_file}")
        result = search_rgi_python(rgi_file)
        if result:
            print(f"\n✅ SUCCESS! Glacier outline saved to: {result}")
            print("   You can now add this to Figure 1!")
    else:
        print("\n⚠️  RGI files not found in satellite_data/rgi/")
        download_rgi_instructions()
        print("\n" + "=" * 70)
        print("NEXT STEPS:")
        print("=" * 70)
        print("1. Download RGI Central Asia shapefile")
        print("2. Extract and place in: satellite_data/rgi/")
        print("3. Run this script again to search for Didal Glacier")
        print("=" * 70)

if __name__ == "__main__":
    main()

