#!/usr/bin/env python3
"""
Extract stable ground statistics using QGIS Processing (no rasterio dependency).

This script should be run from QGIS Python Console or via QGIS MCP.

Usage in QGIS:
1. Open QGIS
2. Plugins → Python Console
3. Run this script
"""

# This is a QGIS Python script - run from QGIS Python Console
# Or use QGIS Processing Toolbox manually

print("="*70)
print("STABLE GROUND STATISTICS EXTRACTION (QGIS METHOD)")
print("="*70)
print("""
This script extracts velocity values from stable ground polygons
using QGIS Processing algorithms, avoiding rasterio dependency issues.

RUN THIS IN QGIS PYTHON CONSOLE:
=================================

1. Open QGIS
2. Plugins → Python Console
3. Copy and paste the code below
4. Or use QGIS Processing Toolbox manually (see instructions)

ALTERNATIVE: USE QGIS PROCESSING TOOLBOX (EASIER)
==================================================

For each velocity map:

1. Processing → Toolbox
2. Search: "Zonal Statistics"
3. Raster Analysis → Zonal Statistics
4. Parameters:
   - Input raster: [Select velocity map]
   - Input polygon: stable_ground_mask
   - Statistics: Mean, StdDev
   - Output: [Save to CSV or temporary layer]
5. Click "Run"
6. Repeat for all 6 velocity maps

This will give you:
- Mean velocity in stable areas (μ_stable = bias)
- StdDev velocity in stable areas (σ_stable = uncertainty)

Then manually combine results into:
  processed_data/stable_ground_statistics.csv

With columns:
  pair_id, date1, date2, mu_stable, sigma_stable, n_pixels, lod
""")

# QGIS Python code (for QGIS Console)
QGIS_CODE = """
from qgis.core import QgsProject, QgsVectorLayer, QgsRasterLayer
from qgis.analysis import QgsZonalStatistics
import os
import glob

# Paths
mask_path = "/home/chunlab/Desktop/writing_paper/tajikistan/Didal_Glacier/stable_ground_mask.shp"
velocity_dir = "/home/chunlab/Desktop/writing_paper/tajikistan/Didal_Glacier/Didal_Glacier_GIS_Data/Velocity_Maps/"

# Load mask
mask_layer = QgsVectorLayer(mask_path, "Stable Ground Mask", "ogr")
if not mask_layer.isValid():
    print("Failed to load mask")
else:
    print(f"Mask loaded: {mask_layer.featureCount()} features")
    
    # Process each velocity map
    velocity_files = sorted(glob.glob(os.path.join(velocity_dir, "*.tif")))
    
    for vel_file in velocity_files:
        print(f"\\nProcessing: {os.path.basename(vel_file)}")
        
        # Load raster
        vel_layer = QgsRasterLayer(vel_file, "velocity")
        if vel_layer.isValid():
            # Run zonal statistics
            zonal = QgsZonalStatistics(mask_layer, vel_layer, "vel_", 1, QgsZonalStatistics.Mean | QgsZonalStatistics.StdDev)
            zonal.calculateStatistics(None)
            
            # Extract results
            for feature in mask_layer.getFeatures():
                mean = feature.attribute("vel_mean")
                stddev = feature.attribute("vel_stddev")
                print(f"  Mean: {mean:.3f} m/day, StdDev: {stddev:.3f} m/day")
        else:
            print(f"  Failed to load: {vel_layer.error().message()}")
"""

print("\n" + "="*70)
print("QGIS PYTHON CODE (Copy to QGIS Console):")
print("="*70)
print(QGIS_CODE)
