#!/usr/bin/env python3
"""
QGIS Python code to search for Didal Glacier in the loaded RGI layer.
This code can be executed via QGIS MCP execute_code tool.
"""

# Didal Glacier location
GLACIER_LAT = 38.97
GLACIER_LON = 70.75

# Code to execute in QGIS
qgis_code = f"""
from qgis.core import *
from qgis.utils import iface

print("=" * 70)
print("SEARCHING FOR DIDAL GLACIER IN RGI LAYER")
print("=" * 70)

# Get the RGI layer (should already be loaded)
layer = None
for lyr in QgsProject.instance().mapLayers().values():
    if 'RGI' in lyr.name() or 'Central Asia' in lyr.name():
        layer = lyr
        break

if layer is None:
    print("❌ Error: RGI Central Asia layer not found")
    print("   Please load the layer first")
else:
    print(f"✅ Found layer: {{layer.name()}}")
    print(f"   Features: {{layer.featureCount()}}")
    print(f"   CRS: {{layer.crs().authid()}}")
    
    # Get field names
    field_names = [field.name() for field in layer.fields()]
    print(f"   Available fields: {{', '.join(field_names[:15])}}")
    
    # Search for Didal by name
    print("\\nSearching for 'Didal' in glacier names...")
    name_fields = [f for f in field_names if 'name' in f.lower() or 'Name' in f or 'GLIMS' in f]
    
    if name_fields:
        print(f"   Checking fields: {{name_fields}}")
        didal_found = False
        
        for feature in layer.getFeatures():
            for name_field in name_fields:
                name = feature.attribute(name_field)
                if name and 'Didal' in str(name):
                    print(f"\\n✅ FOUND: {{name}}")
                    print(f"   Field: {{name_field}}")
                    print(f"   Feature ID: {{feature.id()}}")
                    print(f"   RGI ID: {{feature.attribute('rgi_id') if 'rgi_id' in field_names else 'N/A'}}")
                    didal_found = True
                    
                    # Select and zoom
                    layer.select(feature.id())
                    iface.mapCanvas().setExtent(feature.geometry().boundingBox())
                    iface.mapCanvas().refresh()
                    print(f"   ✅ Feature selected and zoomed to")
                    break
            if didal_found:
                break
        
        if not didal_found:
            print("   ⚠️  No glacier with 'Didal' in name found")
            print("\\nFinding nearest glacier to location...")
            
            from qgis.core import QgsPointXY, QgsGeometry
            point = QgsPointXY({GLACIER_LON}, {GLACIER_LAT})
            point_geom = QgsGeometry.fromPointXY(point)
            
            min_dist = float('inf')
            nearest_feature = None
            
            for feature in layer.getFeatures():
                geom = feature.geometry()
                dist = point_geom.distance(geom)
                if dist < min_dist:
                    min_dist = dist
                    nearest_feature = feature
            
            if nearest_feature:
                # Convert distance to km (rough estimate)
                dist_km = min_dist * 111  # Approximate for degrees
                name = nearest_feature.attribute('Name') if 'Name' in field_names else 'Unknown'
                rgi_id = nearest_feature.attribute('rgi_id') if 'rgi_id' in field_names else 'N/A'
                
                print(f"\\n   Nearest glacier: {{name}}")
                print(f"   RGI ID: {{rgi_id}}")
                print(f"   Distance: {{dist_km:.2f}} km")
                print(f"   Feature ID: {{nearest_feature.id()}}")
                
                if dist_km < 5:
                    print(f"   ✅ Very close! This might be Didal Glacier")
                    layer.select(nearest_feature.id())
                    iface.mapCanvas().setExtent(nearest_feature.geometry().boundingBox())
                    iface.mapCanvas().refresh()
                    print(f"   ✅ Feature selected and zoomed to")
                else:
                    print(f"   ⚠️  Distance is {{dist_km:.2f}} km - might not be Didal Glacier")
    else:
        print("   ⚠️  No name fields found in layer")

print("\\n" + "=" * 70)
print("Search complete!")
print("=" * 70)
"""

# Save the code to a file for easy execution
with open('qgis_search_didal_code.txt', 'w') as f:
    f.write(qgis_code)

print("✅ QGIS code saved to: qgis_search_didal_code.txt")
print("\nYou can:")
print("  1. Copy the code from qgis_search_didal_code.txt")
print("  2. Paste it into QGIS Python Console")
print("  3. OR use QGIS MCP execute_code tool if available")

