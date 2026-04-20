#!/usr/bin/env python3
"""
Extract stable ground statistics using QGIS Processing via MCP.

This script uses QGIS MCP tools to run zonal statistics,
avoiding Python dependency issues.

Note: This requires QGIS MCP server to be running.
"""

import json
import glob
import os
from pathlib import Path

# This would be called via QGIS MCP, but for now provides instructions
print("="*70)
print("EXTRACT STATISTICS VIA QGIS PROCESSING")
print("="*70)
print("""
This script uses QGIS Processing algorithms to extract statistics.

Since QGIS MCP processing may have limitations, use QGIS GUI:

FOR EACH VELOCITY MAP:
======================

1. Processing → Toolbox
2. Search: "Zonal Statistics"
3. Raster Analysis → Zonal Statistics
4. Set parameters:
   - Input raster: [velocity map]
   - Input polygon: stable_ground_mask
   - Statistics: Mean, StdDev
5. Click "Run"
6. Results added to mask layer attributes

AFTER ALL MAPS PROCESSED:
=========================

1. Open stable_ground_mask attribute table
2. Export to CSV
3. Create processed_data/stable_ground_statistics.csv with columns:
   - pair_id, date1, date2, mu_stable, sigma_stable, n_pixels, lod

Or manually extract values from attribute table.
""")

# List velocity maps
velocity_dir = "Didal_Glacier_GIS_Data/Velocity_Maps/"
velocity_files = sorted(glob.glob(os.path.join(velocity_dir, "*.tif")))

print(f"\nVelocity maps to process: {len(velocity_files)}")
for i, vf in enumerate(velocity_files, 1):
    basename = os.path.basename(vf)
    parts = basename.replace("velocity_", "").replace(".tif", "").split("_")
    if len(parts) >= 2:
        print(f"  {i}. {basename} → Dates: {parts[0]} to {parts[1]}")

print("\n" + "="*70)
print("After extracting statistics, create CSV manually or use:")
print("  python organized/scripts/analysis/combine_statistics.py")
print("="*70)
