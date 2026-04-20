"""
QGIS Python Console Script to Create 3D DEM View of Tajikistan

Run this in QGIS Python Console (Plugins → Python Console)
"""

from qgis.core import QgsProject, QgsRasterLayer
from qgis.gui import Qgs3DMapCanvas, Qgs3DMapSettings
from qgis.utils import iface
import os

def create_3d_tajikistan_dem():
    """Create 3D visualization of Tajikistan DEM."""
    
    project = QgsProject.instance()
    
    # Get Tajikistan DEM layer
    tajik_dem = project.mapLayersByName("Tajikistan DEM")[0]
    
    if not tajik_dem:
        print("ERROR: Tajikistan DEM layer not found")
        return False
    
    print("Creating 3D Map View...")
    
    # Create 3D map view
    # Note: QGIS 3D requires iface.createNew3DMapCanvas() or manual creation
    try:
        # Try to create 3D view
        view_3d = iface.createNew3DMapCanvas()
        
        if view_3d:
            # Configure 3D settings
            settings = view_3d.engine().settings()
            
            # Set elevation source
            settings.setElevationSource(Qgs3DMapSettings.RasterLayer, tajik_dem.id())
            
            # Set vertical exaggeration (2-3x for mountainous terrain)
            settings.setVerticalScale(2.5)
            
            # Set terrain resolution
            settings.setTerrainResolution(10)  # meters per pixel
            
            # Set camera position (center of Tajikistan approximately)
            # Tajikistan center: ~71°E, 39°N
            from qgis.core import QgsPointXY
            camera_pos = QgsPointXY(71.0, 39.0)
            settings.setCameraPosition(camera_pos, 50000, 60, 315)  # altitude, pitch, yaw
            
            # Apply settings
            view_3d.engine().setSettings(settings)
            
            # Show 3D view
            view_3d.show()
            view_3d.setWindowTitle("Tajikistan 3D DEM")
            
            print("✅ 3D view created!")
            print("   Adjust camera angle and export manually")
            return True
        else:
            print("ERROR: Could not create 3D map view")
            print("   Try: View → 3D Map Views → New 3D Map View manually")
            return False
            
    except Exception as e:
        print(f"ERROR creating 3D view: {e}")
        print("   Try: View → 3D Map Views → New 3D Map View manually")
        return False

if __name__ == "__main__":
    create_3d_tajikistan_dem()

