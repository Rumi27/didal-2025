# Fixed script to extract Didal Glacier outline
# Copy and paste this ENTIRE block into QGIS Python Console

from qgis.core import *
from qgis.utils import iface
import os

print("=" * 70)
print("EXTRACTING DIDAL GLACIER OUTLINE")
print("=" * 70)

# Get the RGI layer
layer = None
for lyr in QgsProject.instance().mapLayers().values():
    if 'RGI' in lyr.name() or 'Central Asia' in lyr.name():
        layer = lyr
        break

if layer is None:
    print("❌ Error: RGI Central Asia layer not found")
else:
    print(f"✅ Found layer: {layer.name()}")
    
    # Feature ID from previous search
    feature_id = 19404
    feature = layer.getFeature(feature_id)
    
    if not feature.isValid():
        print(f"❌ Error: Feature {feature_id} not found")
    else:
        # Get glacier information
        rgi_id = feature.attribute('rgi_id')
        glims_id = feature.attribute('glims_id')
        cenlon = feature.attribute('cenlon')
        cenlat = feature.attribute('cenlat')
        
        print(f"\n✅ Glacier Information:")
        print(f"   RGI ID: {rgi_id}")
        print(f"   GLIMS ID: {glims_id}")
        print(f"   Center: {cenlat:.4f}°N, {cenlon:.4f}°E")
        print(f"   Feature ID: {feature_id}")
        
        # Create output directory
        output_dir = "/home/chunlab/Desktop/writing_paper/tajikistan/Didal_Glacier/satellite_data/dem/processed"
        os.makedirs(output_dir, exist_ok=True)
        
        # Export to shapefile
        output_path = os.path.join(output_dir, "didal_glacier_rgi_outline.shp")
        
        # Select the feature
        layer.select(feature_id)
        print(f"\n✅ Feature selected")
        
        # Export selected features
        result = QgsVectorFileWriter.writeAsVectorFormat(
            layer,
            output_path,
            "UTF-8",
            layer.crs(),
            "ESRI Shapefile",
            onlySelected=True
        )
        
        if result[0] == QgsVectorFileWriter.NoError:
            print(f"\n✅ Glacier outline exported to:")
            print(f"   {output_path}")
            
            # Load the exported layer
            exported_layer = iface.addVectorLayer(output_path, "Didal Glacier Outline", "ogr")
            if exported_layer:
                # Style it with red outline
                symbol = QgsSymbol.defaultSymbol(exported_layer.geometryType())
                symbol.setColor(QColor("red"))
                symbol_layer = symbol.symbolLayer(0)
                if hasattr(symbol_layer, 'setStrokeWidth'):
                    symbol_layer.setStrokeWidth(1.0)
                elif hasattr(symbol_layer, 'setWidth'):
                    symbol_layer.setWidth(1.0)
                
                renderer = QgsSingleSymbolRenderer(symbol)
                exported_layer.setRenderer(renderer)
                exported_layer.triggerRepaint()
                
                print(f"   ✅ Layer loaded and styled")
                print(f"\n✅ You can now use this outline in Figure 1!")
        else:
            print(f"\n❌ Error exporting: {result[1]}")
            print(f"   Try manual export:")
            print(f"   1. Right-click layer → Export → Save Selected Features As...")
            print(f"   2. Save to: {output_path}")

print("\n" + "=" * 70)

