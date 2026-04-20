# Simple QGIS Python code to search for Didal Glacier
# Copy and paste this into QGIS Python Console

from qgis.core import *
from qgis.utils import iface

print("=" * 70)
print("SEARCHING FOR DIDAL GLACIER")
print("=" * 70)

# Get the RGI layer (already loaded)
layer = None
for lyr in QgsProject.instance().mapLayers().values():
    if 'RGI' in lyr.name() or 'Central Asia' in lyr.name():
        layer = lyr
        break

if layer is None:
    print("❌ Error: RGI Central Asia layer not found")
else:
    print(f"✅ Found layer: {layer.name()}")
    
    # Didal Glacier location
    GLACIER_LAT = 38.97
    GLACIER_LON = 70.75
    
    # Get field names
    field_names = [field.name() for field in layer.fields()]
    print(f"   Fields: {', '.join(field_names[:10])}...")
    
    # Find nearest glacier
    print(f"\nFinding nearest glacier to {GLACIER_LAT}°N, {GLACIER_LON}°E...")
    from qgis.core import QgsPointXY, QgsGeometry
    
    point = QgsPointXY(GLACIER_LON, GLACIER_LAT)
    point_geom = QgsGeometry.fromPointXY(point)
    
    min_dist = float('inf')
    nearest_feature = None
    
    # Check first 1000 features (faster)
    count = 0
    for feature in layer.getFeatures():
        geom = feature.geometry()
        dist = point_geom.distance(geom)
        if dist < min_dist:
            min_dist = dist
            nearest_feature = feature
        count += 1
        if count >= 1000:  # Limit to first 1000 for speed
            break
    
    if nearest_feature:
        dist_km = min_dist * 111  # Approximate conversion
        name = nearest_feature.attribute('Name') if 'Name' in field_names else 'Unknown'
        rgi_id = nearest_feature.attribute('rgi_id') if 'rgi_id' in field_names else 'N/A'
        
        print(f"\n✅ Nearest glacier (from first 1000):")
        print(f"   Name: {name}")
        print(f"   RGI ID: {rgi_id}")
        print(f"   Distance: {dist_km:.2f} km")
        print(f"   Feature ID: {nearest_feature.id()}")
        
        if dist_km < 5:
            print(f"   ✅ Very close! Selecting and zooming...")
            layer.select(nearest_feature.id())
            iface.mapCanvas().setExtent(nearest_feature.geometry().boundingBox())
            iface.mapCanvas().refresh()
            print(f"   ✅ Done!")
        else:
            print(f"   ⚠️  Distance is {dist_km:.2f} km")
            print(f"   Try searching all features for better results")

print("\n" + "=" * 70)

