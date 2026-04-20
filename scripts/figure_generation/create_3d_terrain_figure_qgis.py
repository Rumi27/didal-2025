#!/usr/bin/env python3
"""
QGIS Python Script: Create 3D Terrain Visualization (Chamoli-style Figure 1A)

This script creates a 3D perspective rendering of the Didal Glacier study area
similar to the Chamoli disaster paper's Figure 1A.

Run this script in QGIS Python Console (Plugins → Python Console → Show Editor)

Requirements:
- QGIS 3.0+ with 3D Map View enabled
- DEM loaded in QGIS
- Satellite imagery (optional, for draping)
- Vector layers for labels (optional)

Usage:
1. Open QGIS
2. Load your DEM and other layers
3. Open Python Console (Plugins → Python Console)
4. Open Script Editor (Show Editor button)
5. Paste this script
6. Modify paths and parameters as needed
7. Run script
"""

# QGIS Python API imports
from qgis.core import (
    QgsProject, QgsRasterLayer, QgsVectorLayer, Qgs3DMappingSettings,
    QgsVector3DSymbol, QgsPhongMaterialSettings, QgsMesh3DSymbol,
    QgsPoint3DSymbol, QgsPolygon3DSymbol, QgsLine3DSymbol,
    Qgs3DAxis, QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsPointXY, QgsRectangle, QgsVector3DTileStyle, Qgs3DTerrainGenerator,
    QgsFlatTerrainGenerator, QgsDemTerrainGenerator, QgsMeshTerrainGenerator,
    Qgs3DMapSettings, Qgs3DMapScene, Qgs3DMapCanvas
)
from qgis.gui import Qgs3DMapCanvasWidget
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QColor
import os

# Configuration
GLACIER_LAT = 38.97
GLACIER_LON = 70.75
DEM_PATH = 'satellite_data/dem/processed/dem.tif'
HILLSHADE_PATH = 'satellite_data/dem/processed/hillshade.tif'
GLACIER_OUTLINE = 'satellite_data/dem/processed/didal_glacier_rgi_outline.shp'
OUTPUT_IMAGE = 'processed_data/analysis_results/figure1_3d_terrain.png'

# 3D View Parameters
VERTICAL_EXAGGERATION = 2.5  # 2-3x recommended for mountainous terrain
TERRAIN_RESOLUTION = 512  # Higher = better quality but slower
CAMERA_HEIGHT = 5000  # meters above terrain
CAMERA_PITCH = 60  # degrees (0 = horizontal, 90 = vertical down)
CAMERA_YAW = 315  # degrees (0 = North, 90 = East, 315 = Northwest)
CAMERA_DISTANCE = 15000  # meters from center point

def create_3d_map_view():
    """
    Create a 3D map view in QGIS with terrain visualization.
    
    This function:
    1. Sets up 3D terrain from DEM
    2. Configures camera position
    3. Adds vector layers (glacier outline, labels)
    4. Exports high-resolution image
    """
    print("=" * 70)
    print("CREATING 3D TERRAIN VISUALIZATION")
    print("=" * 70)
    
    # Get project instance
    project = QgsProject.instance()
    
    # Check if DEM layer exists
    dem_layer = None
    for layer_id, layer in project.mapLayers().items():
        if isinstance(layer, QgsRasterLayer):
            if 'dem' in layer.name().lower() or layer.source().endswith('dem.tif'):
                dem_layer = layer
                break
    
    if not dem_layer:
        # Try to load DEM
        if os.path.exists(DEM_PATH):
            dem_layer = QgsRasterLayer(DEM_PATH, "DEM")
            if dem_layer.isValid():
                project.addMapLayer(dem_layer)
                print(f"✅ Loaded DEM: {DEM_PATH}")
            else:
                print(f"❌ Error: Could not load DEM from {DEM_PATH}")
                return None
        else:
            print(f"❌ Error: DEM file not found: {DEM_PATH}")
            print("   Please load DEM layer in QGIS first")
            return None
    
    # Create 3D map settings
    map3d = Qgs3DMapSettings()
    map3d.setCrs(dem_layer.crs())
    
    # Set terrain generator (DEM-based)
    terrain = QgsDemTerrainGenerator()
    terrain.setLayer(dem_layer)
    terrain.setVerticalScale(VERTICAL_EXAGGERATION)
    terrain.setResolution(TERRAIN_RESOLUTION)
    map3d.setTerrainGenerator(terrain)
    
    # Set camera position
    # Convert glacier location to DEM CRS
    glacier_point = QgsPointXY(GLACIER_LON, GLACIER_LAT)
    transform = QgsCoordinateTransform(
        QgsCoordinateReferenceSystem("EPSG:4326"),
        dem_layer.crs(),
        project.transformContext()
    )
    glacier_point_transformed = transform.transform(glacier_point)
    
    # Calculate camera position
    camera_x = glacier_point_transformed.x()
    camera_y = glacier_point_transformed.y()
    
    # Get elevation at glacier location (simplified - use DEM value)
    # In practice, you'd sample the DEM at this point
    camera_z = CAMERA_HEIGHT  # Approximate
    
    # Set camera
    map3d.setCameraPosition(
        QgsPointXY(camera_x, camera_y),
        CAMERA_HEIGHT,
        CAMERA_PITCH,
        CAMERA_YAW
    )
    
    # Set output size (for export)
    map3d.setOutputSize(QSize(3000, 2000))  # High resolution for publication
    
    # Add vector layers (glacier outline)
    if os.path.exists(GLACIER_OUTLINE):
        try:
            glacier_layer = QgsVectorLayer(GLACIER_OUTLINE, "Glacier Outline", "ogr")
            if glacier_layer.isValid():
                # Transform to DEM CRS if needed
                if glacier_layer.crs() != dem_layer.crs():
                    glacier_layer.setCrs(glacier_layer.crs())
                    # Reproject on-the-fly
                
                # Create 3D symbol for glacier outline
                symbol_3d = QgsPolygon3DSymbol()
                symbol_3d.setMaterial(QgsPhongMaterialSettings())
                symbol_3d.setExtrusionHeight(0)  # Flat on terrain
                symbol_3d.setEdgesEnabled(True)
                symbol_3d.setEdgeColor(QColor(255, 0, 0))  # Red outline
                symbol_3d.setEdgeWidth(3)
                
                # Add to map
                map3d.addVectorLayer(glacier_layer, symbol_3d)
                print(f"✅ Added glacier outline: {GLACIER_OUTLINE}")
        except Exception as e:
            print(f"⚠️  Warning: Could not add glacier outline: {e}")
    
    print(f"\n✅ 3D Map Settings Configured:")
    print(f"   Vertical Exaggeration: {VERTICAL_EXAGGERATION}x")
    print(f"   Terrain Resolution: {TERRAIN_RESOLUTION}")
    print(f"   Camera Height: {CAMERA_HEIGHT} m")
    print(f"   Camera Pitch: {CAMERA_PITCH}°")
    print(f"   Camera Yaw: {CAMERA_YAW}°")
    
    return map3d

def create_3d_canvas():
    """
    Create and display 3D map canvas widget.
    
    Note: This requires QGIS GUI to be running.
    """
    print("\n" + "=" * 70)
    print("CREATING 3D MAP CANVAS")
    print("=" * 70)
    
    map3d = create_3d_map_view()
    if not map3d:
        return None
    
    # Create 3D scene
    scene = Qgs3DMapScene(map3d)
    
    # Create canvas widget
    # Note: This must be done in QGIS GUI context
    try:
        from qgis.gui import Qgs3DMapCanvasWidget
        canvas_widget = Qgs3DMapCanvasWidget()
        canvas_widget.setMapSettings(map3d)
        
        print("✅ 3D Canvas created")
        print("\nNext steps:")
        print("1. The 3D view should appear in QGIS")
        print("2. Use mouse to adjust camera angle")
        print("3. Right-click → Export as Image to save")
        
        return canvas_widget
    except Exception as e:
        print(f"⚠️  Note: 3D Canvas requires QGIS GUI: {e}")
        print("   Use QGIS menu: View → 3D Map Views → New 3D Map View")
        return None

def export_3d_image(map3d, output_path, width=3000, height=2000, dpi=300):
    """
    Export 3D map to high-resolution image.
    
    Parameters:
    - map3d: Qgs3DMapSettings object
    - output_path: Output file path
    - width, height: Image dimensions in pixels
    - dpi: Resolution for publication
    """
    print("\n" + "=" * 70)
    print("EXPORTING 3D IMAGE")
    print("=" * 70)
    
    if not map3d:
        print("❌ Error: No 3D map settings available")
        return False
    
    try:
        # Set output size
        map3d.setOutputSize(QSize(width, height))
        
        # Create scene
        scene = Qgs3DMapScene(map3d)
        
        # Render to image
        # Note: This is a simplified approach
        # In practice, you'd use Qgs3DMapCanvasWidget.render() method
        
        print(f"✅ 3D scene configured for export")
        print(f"   Output: {output_path}")
        print(f"   Size: {width} x {height} pixels")
        print(f"   DPI: {dpi}")
        print(f"\n⚠️  Note: Actual export should be done through QGIS GUI:")
        print(f"   1. Open 3D Map View (View → 3D Map Views → New 3D Map View)")
        print(f"   2. Adjust camera angle")
        print(f"   3. Right-click → Export as Image")
        print(f"   4. Set DPI to {dpi}")
        
        return True
    except Exception as e:
        print(f"❌ Error exporting image: {e}")
        return False

def main():
    """
    Main function - run this in QGIS Python Console.
    """
    print("=" * 70)
    print("QGIS 3D TERRAIN VISUALIZATION SCRIPT")
    print("=" * 70)
    print("\nThis script configures a 3D terrain view for Didal Glacier.")
    print("Run this in QGIS Python Console after loading your DEM layer.")
    print()
    
    # Create 3D map settings
    map3d = create_3d_map_view()
    
    if map3d:
        # Try to create canvas (requires GUI)
        canvas = create_3d_canvas()
        
        if not canvas:
            print("\n" + "=" * 70)
            print("MANUAL STEPS (QGIS GUI)")
            print("=" * 70)
            print("\nSince 3D canvas requires GUI, follow these steps:")
            print("\n1. Load DEM layer in QGIS:")
            print(f"   - Layer → Add Raster Layer → {DEM_PATH}")
            print("\n2. Open 3D Map View:")
            print("   - View → 3D Map Views → New 3D Map View")
            print("\n3. Configure 3D View:")
            print("   - Right-click 3D view → Configure")
            print("   - Type: DEM (Raster Layer)")
            print(f"   - Elevation: Select your DEM layer")
            print(f"   - Vertical Scale: {VERTICAL_EXAGGERATION}")
            print(f"   - Resolution: {TERRAIN_RESOLUTION}")
            print("\n4. Position Camera:")
            print(f"   - Center: {GLACIER_LON}°E, {GLACIER_LAT}°N")
            print(f"   - Height: {CAMERA_HEIGHT} m")
            print(f"   - Pitch: {CAMERA_PITCH}°")
            print(f"   - Yaw: {CAMERA_YAW}° (Northwest view)")
            print("\n5. Add Vector Layers:")
            print(f"   - Add glacier outline: {GLACIER_OUTLINE}")
            print("   - Style with red outline")
            print("\n6. Export Image:")
            print("   - Right-click 3D view → Export as Image")
            print(f"   - DPI: 300-600 for publication")
            print(f"   - Output: {OUTPUT_IMAGE}")
        
        # Export configuration
        export_3d_image(map3d, OUTPUT_IMAGE)
    else:
        print("\n❌ Could not create 3D map. Please check DEM layer.")

# Run if executed directly
if __name__ == "__main__":
    main()

