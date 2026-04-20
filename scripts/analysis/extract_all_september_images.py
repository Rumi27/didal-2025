#!/usr/bin/env python3
"""
Extract all September images from nested ZIP files.
"""

import os
import zipfile
import glob

# Directory with the main ZIP
MAIN_ZIP_DIR = "planet_images/new_september/didal_glacier_september_2025"
EXTRACT_DIR = "planet_images/new_september/extracted"

def extract_nested_zips():
    """Extract all nested ZIP files."""
    print("=" * 70)
    print("Extract All September Images from Nested ZIPs")
    print("=" * 70)
    print()
    
    # Find main ZIP file (could be in different locations)
    possible_locations = [
        os.path.join(MAIN_ZIP_DIR, "didal_glacier_september_2025.zip"),
        "planet_images/new_september/didal_glacier_september_2025.zip",
        os.path.join(MAIN_ZIP_DIR, "files", "didal_glacier_september_2025.zip")
    ]
    
    main_zip = None
    for loc in possible_locations:
        if os.path.exists(loc):
            main_zip = loc
            break
    
    if not main_zip:
        # Search for any ZIP in the directory
        zip_files = glob.glob(os.path.join(MAIN_ZIP_DIR, "**", "*.zip"), recursive=True)
        if zip_files:
            main_zip = zip_files[0]
            print(f"Found ZIP: {main_zip}")
        else:
            print(f"✗ Main ZIP not found. Searched:")
            for loc in possible_locations:
                print(f"  - {loc}")
            return
    
    print(f"Main ZIP: {main_zip}")
    print(f"Extract to: {EXTRACT_DIR}")
    print()
    
    os.makedirs(EXTRACT_DIR, exist_ok=True)
    
    # Extract main ZIP
    print("Extracting main ZIP...")
    with zipfile.ZipFile(main_zip, 'r') as main_zip_ref:
        # List contents
        file_list = main_zip_ref.namelist()
        zip_files = [f for f in file_list if f.endswith('.zip')]
        
        print(f"Found {len(zip_files)} nested ZIP files")
        print()
        
        # Extract all nested ZIPs
        for i, nested_zip_path in enumerate(zip_files, 1):
            print(f"Extracting {i}/{len(zip_files)}: {nested_zip_path}")
            
            # Extract nested ZIP to temp location
            temp_zip_path = os.path.join(EXTRACT_DIR, os.path.basename(nested_zip_path))
            with main_zip_ref.open(nested_zip_path) as source:
                with open(temp_zip_path, 'wb') as target:
                    target.write(source.read())
            
            # Extract nested ZIP contents
            nested_extract_dir = os.path.join(EXTRACT_DIR, os.path.basename(nested_zip_path).replace('.zip', ''))
            os.makedirs(nested_extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(temp_zip_path, 'r') as nested_zip_ref:
                nested_zip_ref.extractall(nested_extract_dir)
            
            # Remove temp ZIP
            os.remove(temp_zip_path)
            
            print(f"  ✓ Extracted to: {nested_extract_dir}")
    
    print()
    print("=" * 70)
    print("Extraction Complete")
    print("=" * 70)
    print()
    
    # List extracted images
    tif_files = glob.glob(os.path.join(EXTRACT_DIR, "**", "*_3B_AnalyticMS_SR.tif"), recursive=True)
    print(f"Found {len(tif_files)} TIFF images:")
    for tif_file in sorted(tif_files):
        print(f"  - {os.path.basename(tif_file)}")

if __name__ == "__main__":
    extract_nested_zips()

