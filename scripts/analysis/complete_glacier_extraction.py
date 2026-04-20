#!/usr/bin/env python3
"""
Complete script to extract Didal Glacier outline and verify it.
This can be run in QGIS Python Console or as a standalone script.
"""

from qgis.core import *
from qgis.utils import iface
import os

print("=" * 70)
print("COMPLETE GLACIER EXTRACTION AND VERIFICATION")
print("=" * 70)

# Configuration
FEATURE_ID = 19404
OUTPUT_DIR = "/home/chunlab/Desktop/writing_paper/tajikistan/Didal_Glacier/satellite_data/dem/processed"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "didal_glacier_rgi_outline.shp")

# Create output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Get the RGI layer
layer = None
for lyr in QgsProject.instance().mapLayers().values():
    if 'RGI' in lyr.name() or 'Central Asia' in lyr.name():
        layer = lyr
        break

if layer is None:
    print("❌ Error: RGI Central Asia layer not found")
    print("   Please load the RGI layer first")
else:
    print(f"✅ Found layer: {layer.name()}")
    
    # Get the feature
    feature = layer.getFeature(FEATURE_ID)
    
    if not feature.isValid():
        print(f"❌ Error: Feature {FEATURE_ID} not found")
    else:
        # Get glacier information
        rgi_id = feature.attribute('rgi_id')
        glims_id = feature.attribute('glims_id')
        cenlon = feature.attribute('cenlon')
        cenlat = feature.attribute('cenlat')
        area_km2 = feature.attribute('area_km2')
        
        print(f"\n✅ Glacier Information:")
        print(f"   RGI ID: {rgi_id}")
        print(f"   GLIMS ID: {glims_id}")
        print(f"   Center: {cenlat:.4f}°N, {cenlon:.4f}°E")
        print(f"   Area: {area_km2:.4f} km²")
        print(f"   Feature ID: {FEATURE_ID}")
        
        # Select the feature
        layer.select(FEATURE_ID)
        print(f"\n✅ Feature selected")
        
        # Check if file already exists
        if os.path.exists(OUTPUT_FILE):
            print(f"\n⚠️  File already exists: {OUTPUT_FILE}")
            response = input("   Overwrite? (y/n): ").strip().lower()
            if response != 'y':
                print("   Skipping export")
                OUTPUT_FILE = OUTPUT_FILE.replace('.shp', '_new.shp')
        
        # Export selected features
        print(f"\nExporting to: {OUTPUT_FILE}")
        result = QgsVectorFileWriter.writeAsVectorFormat(
            layer,
            OUTPUT_FILE,
            "UTF-8",
            layer.crs(),
            "ESRI Shapefile",
            onlySelected=True,
            driverName="ESRI Shapefile"
        )
        
        if result[0] == QgsVectorFileWriter.NoError:
            print(f"\n✅ SUCCESS! Glacier outline exported")
            print(f"   File: {OUTPUT_FILE}")
            
            # Verify the file exists
            if os.path.exists(OUTPUT_FILE):
                file_size = os.path.getsize(OUTPUT_FILE) / 1024  # KB
                print(f"   Size: {file_size:.2f} KB")
                
                # Try to load it
                try:
                    exported_layer = iface.addVectorLayer(OUTPUT_FILE, "Didal Glacier Outline", "ogr")
                    if exported_layer:
                        print(f"   ✅ Layer loaded successfully")
                        
                        # Style it
                        symbol = QgsSymbol.defaultSymbol(exported_layer.geometryType())
                        symbol.setColor(QColor("red"))
                        symbol_layer = symbol.symbolLayer(0)
                        if hasattr(symbol_layer, 'setStrokeWidth'):
                            symbol_layer.setStrokeWidth(1.5)
                        elif hasattr(symbol_layer, 'setWidth'):
                            symbol_layer.setWidth(1.5)
                        
                        renderer = QgsSingleSymbolRenderer(symbol)
                        exported_layer.setRenderer(renderer)
                        exported_layer.triggerRepaint()
                        
                        print(f"   ✅ Layer styled with red outline")
                        
                        # Zoom to extent
                        iface.mapCanvas().setExtent(exported_layer.extent())
                        iface.mapCanvas().refresh()
                        print(f"   ✅ Map zoomed to glacier")
                        
                        print(f"\n✅ You can now use this outline in Figure 1!")
                        print(f"   Path: {OUTPUT_FILE}")
                except Exception as e:
                    print(f"   ⚠️  Could not load layer: {e}")
            else:
                print(f"   ⚠️  File not found after export")
        else:
            print(f"\n❌ Error exporting: {result[1]}")
            print(f"\nAlternative: Manual export")
            print(f"   1. Ensure Feature {FEATURE_ID} is selected")
            print(f"   2. Right-click layer → Export → Save Selected Features As...")
            print(f"   3. Save to: {OUTPUT_FILE}")

print("\n" + "=" * 70)
print("Extraction complete!")
print("=" * 70)

