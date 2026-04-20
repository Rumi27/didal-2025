#!/usr/bin/env python3
"""
Guide for creating stable ground mask in QGIS.

This script cannot create the mask automatically (requires QGIS GUI),
but it provides instructions and can validate an existing mask.

Usage:
    python create_stable_ground_mask_guide.py
"""

import os
from pathlib import Path

def print_qgis_instructions():
    """Print step-by-step instructions for creating stable ground mask in QGIS."""
    
    print("=" * 80)
    print("STABLE GROUND MASK CREATION GUIDE")
    print("=" * 80)
    
    print("""
This mask will be used to extract empirical uncertainty statistics from
stable bedrock/ridge areas outside the glacier.

STEP-BY-STEP INSTRUCTIONS FOR QGIS:
====================================

1. OPEN QGIS
   - Launch QGIS application

2. LOAD BASE LAYERS
   - Add satellite imagery (PlanetScope or Sentinel-2)
     Layer → Add Layer → Add Raster Layer
   - Add glacier outline
     Layer → Add Layer → Add Vector Layer
     File: Didal_Glacier_GIS_Data/Glacier_Outline/didal_glacier_rgi_outline.shp
   - Add DEM (optional, for elevation context)
     File: Didal_Glacier_GIS_Data/DEM/n38_e070_1arc_v3.tif

3. IDENTIFY STABLE AREAS
   Look for:
   - Bedrock outcrops (visible as rock surfaces in imagery)
   - Stable ridges (outside glacier boundaries)
   - Valley floors (away from glacier and landslide zones)
   
   AVOID:
   - Glacier ice
   - Landslide/detachment zones
   - Debris-covered areas with potential motion
   - Areas near glacier margins (may have motion)

4. CREATE POLYGON LAYER
   - Layer → Create Layer → New Shapefile Layer
   - Geometry type: Polygon
   - CRS: WGS84 (EPSG:4326)
   - Add fields:
     * area_m2 (Real, 10, 2)
     * notes (Text, 50)
   - Save as: stable_ground_mask.shp
   - Click "OK"

5. START EDITING
   - Right-click on stable_ground_mask layer → Toggle Editing
   - Click "Add Polygon Feature" button

6. DIGITIZE STABLE AREAS
   - Draw polygons around stable bedrock/ridge areas
   - Click to add vertices, right-click to finish polygon
   - Create multiple polygons for better coverage
   - Ensure polygons are:
     * Outside glacier outline
     * Outside landslide/detachment zone
     * Cover sufficient area (aim for >100 pixels per pair)

7. SAVE EDITS
   - Click "Save Edits" button
   - Stop editing

8. VALIDATE MASK
   - Check polygon areas (should cover sufficient pixels)
   - Verify no overlap with glacier
   - Verify no overlap with landslide zone
   - Visual inspection: areas should be clearly bedrock/stable

9. SAVE FINAL MASK
   - Right-click layer → Export → Save Features As...
   - Format: ESRI Shapefile
   - File name: stable_ground_mask.shp
   - CRS: WGS84 (EPSG:4326)
   - Click "OK"

VALIDATION:
===========

After creating the mask, run this script with --validate flag:
    python create_stable_ground_mask_guide.py --validate stable_ground_mask.shp

This will check:
- Mask exists and is valid
- Polygons are outside glacier outline
- Sufficient coverage for statistics extraction
- CRS matches velocity maps

EXPECTED OUTPUT:
================

File: stable_ground_mask.shp (and associated .shx, .dbf, .prj files)

Location: Root directory or processed_data/ directory

CRS: WGS84 (EPSG:4326)

Minimum coverage: ~100 pixels per velocity map pair

""")

def validate_mask(mask_path, glacier_outline_path):
    """Validate an existing stable ground mask."""
    try:
        import geopandas as gpd
        
        print(f"\nValidating stable ground mask: {mask_path}")
        
        # Load mask
        mask_gdf = gpd.read_file(mask_path)
        print(f"  ✓ Mask loaded: {len(mask_gdf)} polygon(s)")
        print(f"  CRS: {mask_gdf.crs}")
        
        # Load glacier outline
        if os.path.exists(glacier_outline_path):
            glacier_gdf = gpd.read_file(glacier_outline_path)
            print(f"  ✓ Glacier outline loaded")
            
            # Ensure same CRS
            if mask_gdf.crs != glacier_gdf.crs:
                mask_gdf = mask_gdf.to_crs(glacier_gdf.crs)
            
            # Check for overlap
            overlap = mask_gdf.overlaps(glacier_gdf.unary_union).any()
            if overlap:
                print(f"  ⚠️  WARNING: Mask overlaps with glacier outline!")
            else:
                print(f"  ✓ Mask does not overlap with glacier")
        else:
            print(f"  ⚠️  Glacier outline not found, skipping overlap check")
        
        # Check area
        total_area = mask_gdf.geometry.area.sum()
        print(f"  Total area: {total_area:.6f} degrees²")
        
        # Estimate pixel coverage (assuming 10m pixels, ~0.00009 degrees)
        pixel_size_deg = 10 / 111000.0  # Approximate
        estimated_pixels = total_area / (pixel_size_deg ** 2)
        print(f"  Estimated pixel coverage: ~{estimated_pixels:.0f} pixels")
        
        if estimated_pixels < 100:
            print(f"  ⚠️  WARNING: Coverage may be insufficient (<100 pixels)")
        else:
            print(f"  ✓ Coverage appears sufficient")
        
        print(f"\n  ✓ Mask validation complete")
        return True
        
    except Exception as e:
        print(f"  ✗ Error validating mask: {e}")
        return False

def main():
    """Main execution."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--validate":
        if len(sys.argv) < 3:
            print("Usage: python create_stable_ground_mask_guide.py --validate <mask.shp>")
            return
        
        mask_path = sys.argv[2]
        glacier_outline = "Didal_Glacier_GIS_Data/Glacier_Outline/didal_glacier_rgi_outline.shp"
        
        if not os.path.exists(mask_path):
            print(f"Error: Mask file not found: {mask_path}")
            return
        
        validate_mask(mask_path, glacier_outline)
    else:
        print_qgis_instructions()
        
        # Check if mask already exists
        possible_paths = [
            "stable_ground_mask.shp",
            "processed_data/stable_ground_mask.shp",
            "Didal_Glacier_GIS_Data/stable_ground_mask.shp"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                print(f"\n{'='*80}")
                print(f"Found existing mask: {path}")
                print("=" * 80)
                validate_mask(path, "Didal_Glacier_GIS_Data/Glacier_Outline/didal_glacier_rgi_outline.shp")
                break

if __name__ == "__main__":
    main()
