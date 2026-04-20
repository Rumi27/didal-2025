#!/usr/bin/env python3
"""
Extract Didal Glacier outline from GLIMS Tajikistan polygons.
This script should be run in QGIS Python Console if geopandas doesn't work.
"""

# Didal Glacier coordinates
GLACIER_LON = 70.75
GLACIER_LAT = 38.97
SEARCH_RADIUS_DEG = 0.1  # ~11 km

print("=" * 70)
print("EXTRACTING DIDAL GLACIER FROM GLIMS TAJIKISTAN POLYGONS")
print("=" * 70)

# Method 1: Try with QGIS Python Console
qgis_code = """
from qgis.core import *
from qgis.utils import iface
import os

print("Loading GLIMS Tajikistan polygons...")

# Path to GLIMS polygons
glims_path = "/home/chunlab/Desktop/writing_paper/tajikistan/Didal_Glacier/glims_download_02735/Tajikistan_glaciers_glims_polygons.shp"

# Load the layer
layer = QgsVectorLayer(glims_path, "GLIMS Tajikistan Glaciers", "ogr")

if not layer.isValid():
    print(f"❌ Error: Could not load GLIMS layer")
    print(f"   File: {glims_path}")
    print(f"   Error: {layer.error().message()}")
else:
    print(f"✅ Loaded GLIMS layer: {layer.featureCount()} glaciers")
    
    # Get field names
    field_names = [field.name() for field in layer.fields()]
    print(f"\\nAvailable fields: {field_names[:20]}...")  # Show first 20
    
    # Search for Didal Glacier
    glacier_lon = 70.75
    glacier_lat = 38.97
    
    # Create a point for Didal Glacier location
    from qgis.core import QgsPointXY, QgsGeometry
    glacier_point = QgsPointXY(glacier_lon, glacier_lat)
    glacier_geom = QgsGeometry.fromPointXY(glacier_point)
    
    # Buffer for search (0.1 degrees ≈ 11 km)
    buffer_geom = glacier_geom.buffer(0.1, 5)  # 5 segments
    
    # Find glaciers within buffer
    matching_features = []
    for feature in layer.getFeatures():
        if feature.geometry().intersects(buffer_geom):
            matching_features.append(feature)
    
    print(f"\\nFound {len(matching_features)} glacier(s) near Didal location:")
    
    for i, feature in enumerate(matching_features):
        # Get centroid
        centroid = feature.geometry().centroid().asPoint()
        dist = ((centroid.x() - glacier_lon)**2 + (centroid.y() - glacier_lat)**2)**0.5
        
        # Get attributes
        attrs = feature.attributes()
        print(f"\\n  Glacier {i+1}:")
        print(f"    Distance: {dist*111:.2f} km")
        print(f"    Center: {centroid.y():.4f}°N, {centroid.x():.4f}°E")
        
        # Print relevant fields
        name_fields = [f for f in field_names if 'name' in f.lower() or 'glac' in f.lower() or 'id' in f.lower()]
        for field_name in name_fields[:5]:  # Show first 5 name-related fields
            idx = layer.fields().indexFromName(field_name)
            if idx >= 0:
                value = feature.attribute(field_name)
                if value:
                    print(f"    {field_name}: {value}")
    
    # If we found matches, export the closest one
    if matching_features:
        # Sort by distance
        matching_features.sort(key=lambda f: 
            ((f.geometry().centroid().asPoint().x() - glacier_lon)**2 + 
             (f.geometry().centroid().asPoint().y() - glacier_lat)**2)**0.5)
        
        closest = matching_features[0]
        centroid = closest.geometry().centroid().asPoint()
        dist = ((centroid.x() - glacier_lon)**2 + (centroid.y() - glacier_lat)**2)**0.5
        
        print(f"\\n✅ Closest glacier: {dist*111:.2f} km away")
        
        # Export to shapefile
        output_dir = "/home/chunlab/Desktop/writing_paper/tajikistan/Didal_Glacier/satellite_data/dem/processed"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "didal_glacier_glims_outline.shp")
        
        # Create new layer with just this feature
        writer = QgsVectorFileWriter.writeAsVectorFormat(
            layer,
            output_path,
            "UTF-8",
            layer.crs(),
            "ESRI Shapefile",
            onlySelected=False,
            filterFids=[closest.id()]
        )
        
        if writer[0] == QgsVectorFileWriter.NoError:
            print(f"✅ Exported to: {output_path}")
            print(f"\\n✅ You can now use this GLIMS outline instead of RGI!")
        else:
            print(f"❌ Export error: {writer[1]}")
    else:
        print("\\n❌ No glaciers found near Didal location")
        print("   Try increasing search radius or check coordinates")

print("\\n" + "=" * 70)
"""

print("\n" + "=" * 70)
print("INSTRUCTIONS:")
print("=" * 70)
print("\n1. Open QGIS")
print("2. Go to: Plugins → Python Console → Open Editor")
print("3. Copy and paste the following code:")
print("\n" + "-" * 70)
print(qgis_code)
print("-" * 70)
print("\n4. Click 'Run Script' (or press Ctrl+E)")
print("5. Check the output for Didal Glacier")
print("\n" + "=" * 70)

# Also save the code to a file for easy access
with open("extract_didal_from_glims_qgis_code.py", "w") as f:
    f.write(qgis_code)

print("\n✅ Code saved to: extract_didal_from_glims_qgis_code.py")
print("   You can copy this file content into QGIS Python Console")
