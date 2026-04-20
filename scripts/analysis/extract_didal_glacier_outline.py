# Extract Didal Glacier outline from RGI
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
    
    # Feature ID from previous search (nearest to 38.97°N, 70.75°E)
    feature_id = 19404
    
    # Get the feature
    feature = layer.getFeature(feature_id)
    
    if not feature.isValid():
        print(f"❌ Error: Feature {feature_id} not found")
    else:
        # Get field names
        field_names = [field.name() for field in layer.fields()]
        
        # Get glacier information
        rgi_id = feature.attribute('rgi_id') if 'rgi_id' in field_names else 'N/A'
        glac_name = feature.attribute('glac_name') if 'glac_name' in field_names else 'Unknown'
        glims_id = feature.attribute('glims_id') if 'glims_id' in field_names else 'N/A'
        cenlon = feature.attribute('cenlon') if 'cenlon' in field_names else 'N/A'
        cenlat = feature.attribute('cenlat') if 'cenlat' in field_names else 'N/A'
        
        print(f"\n✅ Glacier Information:")
        print(f"   RGI ID: {rgi_id}")
        print(f"   GLIMS ID: {glims_id}")
        print(f"   Name: {glac_name}")
        print(f"   Center: {cenlat}°N, {cenlon}°E")
        print(f"   Feature ID: {feature_id}")
        
        # Create output directory
        output_dir = "/home/chunlab/Desktop/writing_paper/tajikistan/Didal_Glacier/satellite_data/dem/processed"
        os.makedirs(output_dir, exist_ok=True)
        
        # Export to shapefile
        output_path = os.path.join(output_dir, "didal_glacier_rgi_outline.shp")
        
        # Create a new layer with just this feature
        fields = layer.fields()
        writer = QgsVectorFileWriter.writeAsVectorFormat(
            layer,
            output_path,
            "UTF-8",
            layer.crs(),
            "ESRI Shapefile",
            onlySelected=False,
            filterFids=[feature_id]
        )
        
        if writer[0] == QgsVectorFileWriter.NoError:
            print(f"\n✅ Glacier outline exported to:")
            print(f"   {output_path}")
            print(f"\n✅ You can now use this outline in Figure 1!")
        else:
            print(f"\n❌ Error exporting: {writer[1]}")
            
            # Alternative method: select and export
            print("\nTrying alternative method...")
            layer.select(feature_id)
            
            # Export selected features
            QgsVectorFileWriter.writeAsVectorFormat(
                layer,
                output_path,
                "UTF-8",
                layer.crs(),
                "ESRI Shapefile",
                onlySelected=True
            )
            
            if os.path.exists(output_path):
                print(f"✅ Glacier outline exported (alternative method)")
                print(f"   {output_path}")
            else:
                print(f"❌ Export failed. Try manual export:")
                print(f"   1. Right-click layer → Export → Save Selected Features As...")
                print(f"   2. Save to: {output_path}")

print("\n" + "=" * 70)

