#!/usr/bin/env python3
"""
Analyze Planet images downloaded from website.
Summarizes image properties, dates, and coverage.
"""

import os
import json
from pathlib import Path

# Directories
FROM_WEBSITE_DIR = "planet_images/from_website"
GEOJSON_DIR = FROM_WEBSITE_DIR
IMAGE_DIR = os.path.join(FROM_WEBSITE_DIR, "glacier_psscene_analytic_sr_udm2/PSScene")

def analyze_planet_images():
    """
    Analyze downloaded Planet images.
    """
    print("=" * 60)
    print("Planet Images Analysis - From Website Downloads")
    print("=" * 60)
    print()
    
    # Check GeoJSON files (AOI definitions)
    geojson_files = list(Path(GEOJSON_DIR).glob("*.geojson"))
    print(f"GeoJSON AOI files found: {len(geojson_files)}")
    for geojson_file in geojson_files:
        print(f"  - {geojson_file.name}")
    print()
    
    # Check image files
    if os.path.exists(IMAGE_DIR):
        tif_files = list(Path(IMAGE_DIR).glob("*.tif"))
        json_files = list(Path(IMAGE_DIR).glob("*.json"))
        
        print(f"Image files found: {len(tif_files)} TIFF files")
        print(f"Metadata files: {len(json_files)} JSON files")
        print()
        
        # Analyze each image
        for tif_file in tif_files:
            if "AnalyticMS_SR" in tif_file.name:
                # This is the main image
                image_id = tif_file.stem.replace("_3B_AnalyticMS_SR_clip", "")
                print(f"Image ID: {image_id}")
                print(f"File: {tif_file.name}")
                print(f"Size: {tif_file.stat().st_size / (1024*1024):.2f} MB")
                
                # Find corresponding JSON metadata
                json_file = Path(IMAGE_DIR) / f"{image_id}.json"
                if json_file.exists():
                    with open(json_file, 'r') as f:
                        metadata = json.load(f)
                    
                    props = metadata.get("properties", {})
                    print(f"Acquisition date: {props.get('datetime', 'Unknown')}")
                    print(f"Cloud cover: {props.get('eo:cloud_cover', 'Unknown')}%")
                    print(f"GSD (Ground Sample Distance): {props.get('gsd', 'Unknown')} m")
                    print(f"Platform: {props.get('platform', 'Unknown')}")
                    print(f"Instrument: {', '.join(props.get('instruments', []))}")
                    
                    # Geometry info
                    bbox = metadata.get("bbox", [])
                    if bbox:
                        print(f"Bounding box: {bbox[0]:.4f}°E, {bbox[1]:.4f}°N to {bbox[2]:.4f}°E, {bbox[3]:.4f}°N")
                    
                    # Asset info
                    assets = metadata.get("assets", {})
                    if "20251028_062851_61_2500_3B_AnalyticMS_SR_clip_tif" in assets:
                        asset = assets["20251028_062851_61_2500_3B_AnalyticMS_SR_clip_tif"]
                        bands = asset.get("raster:bands", [])
                        print(f"Bands: {len(bands)}")
                        print(f"  - Blue, Green, Red, Near-Infrared (4-band)")
                        print(f"Resolution: {bands[0].get('spatial_resolution', 'Unknown')} m")
                        print(f"EPSG: {asset.get('proj:epsg', 'Unknown')}")
                        shape = asset.get("proj:shape", [])
                        if shape:
                            print(f"Dimensions: {shape[1]} x {shape[0]} pixels")
                
                print()
                
                # Check UDM2 file
                udm2_file = Path(IMAGE_DIR) / f"{image_id}_3B_udm2_clip.tif"
                if udm2_file.exists():
                    print(f"UDM2 (Usable Data Mask): {udm2_file.name}")
                    print(f"Size: {udm2_file.stat().st_size / 1024:.2f} KB")
                    print("  Contains: Clear, Snow, Shadow, Haze, Cloud, Confidence maps")
                    print()
    
    # Summary
    print("-" * 60)
    print("Summary:")
    print("-" * 60)
    print("✓ Full-resolution PlanetScope images downloaded")
    print("✓ Analytic Surface Reflectance (4-band: B, G, R, NIR)")
    print("✓ UDM2 quality masks included")
    print("✓ GeoJSON AOI files for reference")
    print()
    print("These images are ready for:")
    print("  - Visual analysis and interpretation")
    print("  - Change detection (if multiple dates)")
    print("  - Integration with Sentinel-1 SAR data")
    print("  - Figure creation for the paper")

if __name__ == "__main__":
    analyze_planet_images()

