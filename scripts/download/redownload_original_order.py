#!/usr/bin/env python3
"""
Re-download the original September order ZIP to get all 9 images.
Only 1 image was extracted before, so we need to get the remaining 8.
"""

import os
import json
import requests
import zipfile
import shutil

# Original order ID
ORDER_ID = "fee2882b-798b-4b20-9239-ec9fbc072acd"
API_KEY = "PLAK97848b681d244728a5a7a02e73eb23d5"

OUTPUT_DIR = "planet_images/new_september/original_order_redownload"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def check_order_status():
    """Check order status and get download links."""
    url = f"https://api.planet.com/compute/ops/orders/v2/{ORDER_ID}"
    auth = (API_KEY, "")
    
    try:
        response = requests.get(url, auth=auth, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error checking order: {e}")
        return None

def download_and_extract():
    """Download and extract the order ZIP."""
    print("=" * 70)
    print("Re-download Original September Order")
    print("=" * 70)
    print()
    print(f"Order ID: {ORDER_ID}")
    print()
    
    order_data = check_order_status()
    if not order_data:
        print("✗ Could not check order status")
        return False
    
    state = order_data.get("state", "").lower()
    print(f"Order state: {state}")
    print()
    
    if state != "success":
        print(f"⚠️  Order is not complete (state: {state})")
        print("   Please wait for order to finish processing")
        return False
    
    # Get download links
    _links = order_data.get("_links", {})
    results = _links.get("results", [])
    
    if not results:
        print("✗ No download links found")
        return False
    
    print(f"Found {len(results)} download link(s)")
    print()
    
    # Find the main ZIP file (not manifest.json)
    zip_result = None
    for result in results:
        if isinstance(result, dict):
            name = result.get("name", "")
            if name.endswith(".zip"):
                zip_result = result
                break
        elif isinstance(result, str) and result.endswith(".zip"):
            zip_result = {"location": result, "name": os.path.basename(result)}
    
    if not zip_result:
        print("✗ No ZIP file found in results")
        return False
    
    # Download ZIP
    zip_url = zip_result.get("location", "")
    zip_name = zip_result.get("name", "order.zip")
    
    if not zip_url:
        print("✗ No download URL found")
        return False
    
    print(f"Downloading: {zip_name}")
    print(f"URL: {zip_url[:80]}...")
    print()
    
    try:
        response = requests.get(zip_url, stream=True, timeout=300)
        response.raise_for_status()
        
        zip_path = os.path.join(OUTPUT_DIR, zip_name)
        
        # Create parent directory if it doesn't exist
        os.makedirs(os.path.dirname(zip_path), exist_ok=True)
        
        print("Downloading...")
        total_size = 0
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    total_size += len(chunk)
                    if total_size % (50 * 1024 * 1024) == 0:  # Every 50 MB
                        print(f"  Downloaded: {total_size / (1024*1024):.1f} MB")
        
        file_size_mb = total_size / (1024 * 1024)
        print(f"✓ Downloaded: {zip_path} ({file_size_mb:.1f} MB)")
        print()
        
        # Extract ZIP
        extract_dir = os.path.join(OUTPUT_DIR, zip_name.replace('.zip', ''))
        if os.path.exists(extract_dir):
            print(f"Removing existing directory: {extract_dir}")
            shutil.rmtree(extract_dir)
        
        os.makedirs(extract_dir, exist_ok=True)
        
        print(f"Extracting to: {extract_dir}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        print(f"✓ Extracted to: {extract_dir}")
        print()
        
        # List extracted images
        import glob
        tif_files = glob.glob(os.path.join(extract_dir, "**", "*_3B_AnalyticMS_SR.tif"), recursive=True)
        print(f"Found {len(tif_files)} TIFF images:")
        for tif_file in sorted(tif_files):
            print(f"  - {os.path.basename(tif_file)}")
        
        print()
        print("=" * 70)
        print("Next Steps")
        print("=" * 70)
        print()
        print("1. Review extracted images")
        print("2. Move/copy images to planet_images/sep_2025/ or planet_images/newa_planet/")
        print("3. Run visualization scripts to process all images")
        
        return True
        
    except Exception as e:
        print(f"✗ Error downloading/extracting: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = download_and_extract()
    exit(0 if success else 1)

