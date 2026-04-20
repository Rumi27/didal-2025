#!/usr/bin/env python3
"""
Check Planet order status and download images when ready.
"""

import os
import json
import requests
import time
import zipfile
from urllib.parse import urlparse

# Planet API configuration
PLANET_API_KEY = "PLAK97848b681d244728a5a7a02e73eb23d5"

# Order ID (from create_september_order.py)
ORDER_ID = "fee2882b-798b-4b20-9239-ec9fbc072acd"

# Output directory
OUTPUT_DIR = "planet_images/new_september"

def check_order_status(order_id):
    """Check the status of an order."""
    url = f"https://api.planet.com/compute/ops/orders/v2/{order_id}"
    auth = (PLANET_API_KEY, "")
    
    try:
        response = requests.get(url, auth=auth)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error checking order: {e}")
        return None

def download_order(order_id, output_dir):
    """Download completed order."""
    order_data = check_order_status(order_id)
    
    if not order_data:
        return False
    
    state = order_data.get("state", "").lower()
    
    print(f"Order state: {state}")
    print()
    
    if state == "success":
        # Get download links
        _links = order_data.get("_links", {})
        results = _links.get("results", [])
        
        if results:
            print(f"Order complete! Found {len(results)} download links")
            print()
            
            # Download each result
            for i, result in enumerate(results, 1):
                # Handle both dict and string formats
                if isinstance(result, dict):
                    result_url = result.get("location", "")
                    result_name = result.get("name", f"result_{i}")
                else:
                    result_url = result
                    result_name = f"result_{i}"
                
                if not result_url:
                    print(f"  ⚠️  No download URL for result {i}")
                    continue
                
                print(f"Downloading {i}/{len(results)}: {result_name}")
                print(f"  URL: {result_url[:80]}...")
                
                try:
                    # Download file (no auth needed for signed URLs)
                    response = requests.get(result_url, stream=True, timeout=300)
                    response.raise_for_status()
                    
                    # Determine filename from name or URL
                    if result_name and result_name != f"result_{i}":
                        # Extract filename from name (e.g., "order_id/filename.zip")
                        filename = result_name.split('/')[-1]
                    else:
                        parsed_url = urlparse(result_url)
                        filename = os.path.basename(parsed_url.path.split('?')[0])
                    
                    if not filename or filename == "/":
                        filename = f"order_result_{i}.zip"
                    
                    filepath = os.path.join(output_dir, filename)
                    
                    # Save file
                    print(f"  Saving to: {filepath}")
                    total_size = 0
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                total_size += len(chunk)
                                if total_size % (10 * 1024 * 1024) == 0:  # Every 10 MB
                                    print(f"    Downloaded: {total_size / (1024*1024):.1f} MB")
                    
                    file_size_mb = total_size / (1024 * 1024)
                    print(f"  ✓ Saved: {filepath} ({file_size_mb:.1f} MB)")
                    
                    # Extract if it's a zip
                    if filename.endswith('.zip'):
                        extract_dir = os.path.join(output_dir, filename.replace('.zip', ''))
                        os.makedirs(extract_dir, exist_ok=True)
                        
                        print(f"  Extracting to: {extract_dir}")
                        with zipfile.ZipFile(filepath, 'r') as zip_ref:
                            zip_ref.extractall(extract_dir)
                        
                        print(f"  ✓ Extracted to: {extract_dir}")
                    
                except Exception as e:
                    print(f"  ✗ Error downloading: {e}")
                    import traceback
                    traceback.print_exc()
            
            return True
        else:
            print("No download links found in order results")
            return False
    
    elif state == "failed":
        print("Order failed!")
        error = order_data.get("error", {})
        print(f"Error: {error}")
        return False
    
    else:
        print(f"Order is still {state}. Please wait and check again later.")
        return False

def main():
    """Main function."""
    import sys
    
    # Support command-line argument for order ID
    order_id = ORDER_ID
    if len(sys.argv) > 1:
        if sys.argv[1] == "--order-id" and len(sys.argv) > 2:
            order_id = sys.argv[2]
        elif sys.argv[1].startswith("--"):
            print("Usage: python3 check_and_download_order.py [--order-id ORDER_ID]")
            sys.exit(1)
        else:
            order_id = sys.argv[1]
    
    print("=" * 70)
    print("Check and Download Planet Order")
    print("=" * 70)
    print()
    print(f"Order ID: {order_id}")
    print()
    
    # Check status
    order_data = check_order_status(order_id)
    
    if order_data:
        print("Order details:")
        print(f"  Name: {order_data.get('name', 'N/A')}")
        print(f"  State: {order_data.get('state', 'N/A')}")
        print(f"  Created: {order_data.get('created_on', 'N/A')}")
        print(f"  Last modified: {order_data.get('last_modified', 'N/A')}")
        print()
        
        # Save order info
        order_file = os.path.join(OUTPUT_DIR, "order_info.json")
        with open(order_file, 'w') as f:
            json.dump(order_data, f, indent=2)
        
        # Try to download if ready
        if order_data.get("state", "").lower() == "success":
            print("Order is complete! Downloading...")
            print()
            success = download_order(order_id, OUTPUT_DIR)
            if not success:
                sys.exit(1)
        else:
            print(f"Order is {order_data.get('state', 'unknown')}. Check again later.")
            print()
            print("To check status again, run:")
            print(f"  python3 check_and_download_order.py --order-id {order_id}")
    else:
        print("Could not retrieve order status")
        sys.exit(1)

if __name__ == "__main__":
    main()

