#!/usr/bin/env python3
"""
H1 Analysis: Extract Glacier Centerline and Test Topographic Pinning

This script is designed to be run in QGIS Python Console or via QGIS MCP.

It:
1. Loads glacier outline (RGI)
2. Extracts centerline
3. Samples DEM slope along centerline
4. Samples velocity maps along centerline
5. Identifies slope breaks and valley constrictions
6. Tests spatial alignment with braking onset position

Usage in QGIS:
1. Open QGIS
2. Load: didal_glacier_rgi_outline.shp
3. Load: DEM (dem.tif or hillshade.tif)
4. Load: Velocity maps (velocity_*.tif)
5. Open Python Console
6. Paste and run this script
"""

from qgis.core import QgsProject, QgsVectorLayer, QgsRasterLayer, QgsProcessing
from qgis.core import QgsCoordinateReferenceSystem, QgsPointXY, QgsGeometry
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
from qgis.utils import iface
import processing
import os
from pathlib import Path

# Paths (adjust as needed)
GLACIER_OUTLINE_PATH = "satellite_data/dem/processed/didal_glacier_rgi_outline.shp"
DEM_PATH = "satellite_data/dem/processed/dem.tif"
VELOCITY_MAPS_DIR = "satellite_data/sentinel1/processed/velocity_maps"
OUTPUT_DIR = "processed_data/h1_h2_analysis"

def load_layers():
    """Load required layers."""
    print("=" * 70)
    print("LOADING LAYERS FOR H1 ANALYSIS")
    print("=" * 70)
    
    project = QgsProject.instance()
    
    # Load glacier outline
    glacier_layer = QgsVectorLayer(GLACIER_OUTLINE_PATH, "Didal Glacier Outline", "ogr")
    if not glacier_layer.isValid():
        print(f"❌ Error: Could not load glacier outline from {GLACIER_OUTLINE_PATH}")
        return None, None, None
    
    project.addMapLayer(glacier_layer)
    print(f"✅ Loaded glacier outline: {glacier_layer.name()}")
    
    # Load DEM
    dem_layer = QgsRasterLayer(DEM_PATH, "DEM", "gdal")
    if not dem_layer.isValid():
        print(f"❌ Error: Could not load DEM from {DEM_PATH}")
        return glacier_layer, None, None
    
    project.addMapLayer(dem_layer)
    print(f"✅ Loaded DEM: {dem_layer.name()}")
    
    # Load velocity maps
    velocity_layers = []
    velocity_dir = Path(VELOCITY_MAPS_DIR)
    if velocity_dir.exists():
        for vel_file in sorted(velocity_dir.glob("velocity_*.tif")):
            vel_layer = QgsRasterLayer(str(vel_file), f"Velocity {vel_file.stem}", "gdal")
            if vel_layer.isValid():
                project.addMapLayer(vel_layer)
                velocity_layers.append(vel_layer)
                print(f"✅ Loaded velocity map: {vel_layer.name()}")
            else:
                print(f"⚠️  Warning: Could not load {vel_file}")
    else:
        print(f"⚠️  Warning: Velocity maps directory not found: {VELOCITY_MAPS_DIR}")
    
    return glacier_layer, dem_layer, velocity_layers

def extract_centerline(glacier_layer):
    """Extract glacier centerline using QGIS processing."""
    print("\n" + "=" * 70)
    print("EXTRACTING GLACIER CENTERLINE")
    print("=" * 70)
    
    # Method 1: Use v.to.rast.flow (GRASS) to create flow accumulation
    # Then extract centerline from flow accumulation
    
    # Method 2: Use v.centerline (simpler, but may need plugin)
    
    # Method 3: Manual centerline digitization (if automated fails)
    
    # For now, we'll use a simplified approach:
    # Extract longest axis or use v.to.rast.flow
    
    try:
        # Try v.to.rast.flow (GRASS)
        output_centerline = str(Path(OUTPUT_DIR) / "glacier_centerline.shp")
        
        # This is a placeholder - actual implementation depends on QGIS version
        # and available processing algorithms
        print("⚠️  Centerline extraction requires manual processing or specific QGIS algorithms")
        print("   Options:")
        print("   1. Use 'v.to.rast.flow' (GRASS) to create flow accumulation")
        print("   2. Use 'v.centerline' plugin if available")
        print("   3. Manually digitize centerline along glacier axis")
        print(f"   Output should be saved to: {output_centerline}")
        
        return None
        
    except Exception as e:
        print(f"❌ Error extracting centerline: {e}")
        return None

def calculate_slope_along_centerline(dem_layer, centerline_layer):
    """Calculate slope along centerline."""
    print("\n" + "=" * 70)
    print("CALCULATING SLOPE ALONG CENTERLINE")
    print("=" * 70)
    
    if centerline_layer is None:
        print("⚠️  No centerline available")
        return None
    
    # Create slope raster from DEM
    slope_output = str(Path(OUTPUT_DIR) / "slope.tif")
    
    try:
        # Use gdal:slope processing
        slope_params = {
            'INPUT': dem_layer,
            'BAND': 1,
            'SCALE': 1.0,
            'AS_PERCENT': False,
            'COMPUTE_EDGES': False,
            'ZEVENBERGEN': False,
            'OPTIONS': '',
            'OUTPUT': slope_output
        }
        
        result = processing.run('gdal:slope', slope_params)
        slope_layer = QgsRasterLayer(result['OUTPUT'], "Slope", "gdal")
        
        if slope_layer.isValid():
            QgsProject.instance().addMapLayer(slope_layer)
            print(f"✅ Created slope raster: {slope_output}")
            
            # Sample slope along centerline
            # Use processing.run('qgis:rastersampling') or similar
            print("   Sampling slope along centerline...")
            # This would extract slope values at each point along centerline
            
            return slope_layer
        else:
            print("❌ Error: Could not create slope raster")
            return None
            
    except Exception as e:
        print(f"❌ Error calculating slope: {e}")
        return None

def sample_velocity_along_centerline(velocity_layers, centerline_layer):
    """Sample velocity values along centerline for each velocity map."""
    print("\n" + "=" * 70)
    print("SAMPLING VELOCITY ALONG CENTERLINE")
    print("=" * 70)
    
    if centerline_layer is None or len(velocity_layers) == 0:
        print("⚠️  No centerline or velocity maps available")
        return None
    
    # For each velocity map, sample values along centerline
    velocity_profiles = {}
    
    for vel_layer in velocity_layers:
        print(f"   Sampling {vel_layer.name()}...")
        # Use processing.run('qgis:rastersampling') or similar
        # Extract velocity values at each point along centerline
        # Store in dictionary with date as key
        
    return velocity_profiles

def identify_slope_breaks(slope_profile):
    """Identify slope breaks (sudden changes in slope)."""
    print("\n" + "=" * 70)
    print("IDENTIFYING SLOPE BREAKS")
    print("=" * 70)
    
    # Calculate slope gradient (first derivative)
    # Identify points where gradient exceeds threshold
    # These are potential pinning points
    
    print("   Slope breaks identified at:")
    # List identified break points
    
    return []

def identify_valley_constrictions(glacier_layer, centerline_layer):
    """Identify valley constrictions (narrowing of glacier width)."""
    print("\n" + "=" * 70)
    print("IDENTIFYING VALLEY CONSTRICTIONS")
    print("=" * 70)
    
    # Calculate glacier width perpendicular to centerline at regular intervals
    # Identify points where width is significantly narrower
    # These are potential pinning points
    
    print("   Valley constrictions identified at:")
    # List identified constriction points
    
    return []

def test_h1_alignment(braking_onset_position, slope_breaks, constrictions):
    """Test H1: spatial alignment of braking onset with topographic features."""
    print("\n" + "=" * 70)
    print("TESTING H1: TOPOGRAPHIC PINNING")
    print("=" * 70)
    
    # Check if braking onset position aligns with:
    # 1. Slope breaks
    # 2. Valley constrictions
    
    # Define alignment threshold (e.g., within 100m)
    alignment_threshold_m = 100
    
    print(f"\nBraking onset position: [to be determined from velocity maps]")
    print(f"Alignment threshold: {alignment_threshold_m} m")
    
    # Test alignment
    aligned_with_slope_break = False
    aligned_with_constriction = False
    
    # Check slope breaks
    for break_point in slope_breaks:
        distance = calculate_distance(braking_onset_position, break_point)
        if distance < alignment_threshold_m:
            aligned_with_slope_break = True
            print(f"  ✅ Aligned with slope break (distance: {distance:.1f} m)")
    
    # Check constrictions
    for constriction in constrictions:
        distance = calculate_distance(braking_onset_position, constriction)
        if distance < alignment_threshold_m:
            aligned_with_constriction = True
            print(f"  ✅ Aligned with valley constriction (distance: {distance:.1f} m)")
    
    h1_supported = aligned_with_slope_break or aligned_with_constriction
    
    print(f"\nH1 Support: {'✅ YES' if h1_supported else '❌ NO'}")
    
    return {
        'h1_supported': h1_supported,
        'aligned_with_slope_break': aligned_with_slope_break,
        'aligned_with_constriction': aligned_with_constriction
    }

def calculate_distance(point1, point2):
    """Calculate distance between two points."""
    # Placeholder - implement actual distance calculation
    return 0.0

def main():
    """Main function for H1 analysis."""
    print("=" * 70)
    print("H1 ANALYSIS: TOPOGRAPHIC PINNING TEST")
    print("=" * 70)
    print()
    
    # Load layers
    glacier_layer, dem_layer, velocity_layers = load_layers()
    
    if glacier_layer is None:
        print("❌ Cannot proceed without glacier outline")
        return
    
    # Extract centerline
    centerline_layer = extract_centerline(glacier_layer)
    
    # Calculate slope
    slope_layer = None
    if dem_layer is not None and centerline_layer is not None:
        slope_layer = calculate_slope_along_centerline(dem_layer, centerline_layer)
    
    # Sample velocity
    velocity_profiles = None
    if len(velocity_layers) > 0 and centerline_layer is not None:
        velocity_profiles = sample_velocity_along_centerline(velocity_layers, centerline_layer)
    
    # Identify topographic features
    slope_breaks = []
    constrictions = []
    
    if slope_layer is not None:
        # Extract slope profile along centerline
        # slope_profile = extract_profile(slope_layer, centerline_layer)
        # slope_breaks = identify_slope_breaks(slope_profile)
        pass
    
    if centerline_layer is not None:
        # constrictions = identify_valley_constrictions(glacier_layer, centerline_layer)
        pass
    
    # Test H1
    # braking_onset_position = determine_braking_onset_from_velocity(velocity_profiles)
    # h1_results = test_h1_alignment(braking_onset_position, slope_breaks, constrictions)
    
    print("\n" + "=" * 70)
    print("H1 ANALYSIS COMPLETE")
    print("=" * 70)
    print("\nNote: This script provides the framework for H1 analysis.")
    print("      Some steps may require manual processing in QGIS GUI.")
    print("      See QGIS documentation for centerline extraction methods.")

if __name__ == "__main__":
    # This script is designed for QGIS Python Console
    # Run main() after loading layers in QGIS
    main()

