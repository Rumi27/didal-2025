#!/usr/bin/env python3
"""
Create Planet order for missing critical date images.
"""

import os
import json
import requests

# Planet API configuration
PLANET_API_KEY = "PLAK97848b681d244728a5a7a02e73eb23d5"

# Images to order (best quality, covering glacier)
IMAGES_TO_ORDER = {
    "before_initial": {
        "name": "Before Initial Movement - September 17",
        "item_id": "20250917_064330_29_24b7",  # We have this but it doesn't cover well
        "alternative": "20250918_063024_87_24da",  # 98% cloud - not good
        "note": "September 17 image exists but glacier is just outside bounds"
    },
    "second_movement": {
        "name": "Second Movement - October 25",
        "item_id": "20251025_062610_58_251d",  # Alternative with 27% cloud
        "note": "We have 20251025_062608_36_251d which should work, but ordering alternative"
    }
}

# Load search results to get all options
results_file = "planet_images/missing_dates_search_results.json"

def create_order_for_images(item_ids, order_name):
    """Create a Planet order for specific image IDs."""
    print(f"Creating order: {order_name}")
    print(f"Images: {len(item_ids)}")
    for item_id in item_ids:
        print(f"  - {item_id}")
    print()
    
    order_payload = {
        "name": order_name,
        "products": [
            {
                "item_ids": item_ids,
                "item_type": "PSScene",
                "product_bundle": "analytic_sr_udm2"
            }
        ],
        "delivery": {
            "archive_type": "zip",
            "archive_filename": f"{order_name.lower().replace(' ', '_')}.zip"
        }
    }
    
    url = "https://api.planet.com/compute/ops/orders/v2"
    headers = {"Content-Type": "application/json"}
    auth = (PLANET_API_KEY, "")
    
    try:
        response = requests.post(url, json=order_payload, headers=headers, auth=auth)
        response.raise_for_status()
        
        order_data = response.json()
        order_id = order_data.get("id")
        
        print(f"✓ Order created!")
        print(f"  Order ID: {order_id}")
        print(f"  State: {order_data.get('state', 'N/A')}")
        print()
        
        return order_id
        
    except Exception as e:
        print(f"✗ Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                print(f"  Details: {json.dumps(error_data, indent=2)}")
            except:
                print(f"  Response: {e.response.text}")
        return None

def main():
    """Main function."""
    print("=" * 70)
    print("Create Order for Missing Critical Date Images")
    print("=" * 70)
    print()
    
    # Check what we need
    print("Current status:")
    print("  ✓ October 25: We have 20251025_062608_36_251d (should work)")
    print("  ✗ September 17: We have 20250917_064330_29_24b7 (glacier outside bounds)")
    print()
    
    # Load search results
    if os.path.exists(results_file):
        with open(results_file, 'r') as f:
            search_results = json.load(f)
        
        print("Available alternatives from search:")
        print()
        
        # September options
        sept_results = search_results.get("before_initial", [])
        if sept_results:
            print("September options:")
            for img in sept_results:
                print(f"  - {img['id']}: {img['cloud_cover']}% cloud")
            print()
        
        # October options
        oct_results = search_results.get("second_movement", [])
        if oct_results:
            print("October 25 alternatives:")
            for img in oct_results:
                print(f"  - {img['id']}: {img['cloud_cover']}% cloud")
            print()
    
    print("=" * 70)
    print("Recommendation")
    print("=" * 70)
    print()
    print("1. October 25: Your existing image (20251025_062608_36_251d) should work.")
    print("   It covers the glacier location. Process it if not already done.")
    print()
    print("2. September 17: The image we have doesn't cover the glacier properly.")
    print("   Options:")
    print("   a) Use September 12 image (20250912_063417_10_252b) - we have this")
    print("   b) Search for September 9-14 images (we tried but order only had 1)")
    print("   c) Use the September 17 full scene with note about coverage")
    print()
    
    # Ask if user wants to order October 25 alternative
    print("Would you like to:")
    print("1. Order the October 25 alternative (20251025_062610_58_251d)?")
    print("2. Search for more September images?")
    print("3. Process existing October 25 image?")
    print()
    print("For now, let's process the October 25 image we have and check if it works.")

if __name__ == "__main__":
    main()

