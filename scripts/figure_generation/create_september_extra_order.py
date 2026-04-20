#!/usr/bin/env python3
"""
Create a new Planet order for the 9 missing September images.
Run this locally with network access.

Usage:
    export PL_API_KEY="PLAK97848b681d244728a5a7a02e73eb23d5"
    python3 create_september_extra_order.py
"""

import os
import json
import requests
import sys

# Get API key from environment or use default (user should set env var)
API_KEY = os.environ.get("PL_API_KEY", "PLAK97848b681d244728a5a7a02e73eb23d5")

# The 9 missing September images (not in original order)
MISSING_IMAGE_IDS = [
    "20250917_064330_29_24b7",  # Sept 17 - 2% cloud (important!)
    "20250917_064328_46_24b7",  # Sept 17 - 0% cloud (important!)
    "20250927_063229_94_253f",  # Sept 27 - 0% cloud
    "20250922_063432_07_24e5",  # Sept 22 - 0% cloud
    "20250922_063119_39_2531",  # Sept 22 - 0% cloud
    "20250922_062909_81_2507",  # Sept 22 - 0% cloud
    "20250921_063357_35_24ee",  # Sept 21 - 0% cloud
    "20250921_063355_23_24ee",  # Sept 21 - 0% cloud
    "20250908_062528_54_251a",  # Sept 8 - 0% cloud
]

def create_order():
    """Create new Planet order for missing September images."""
    print("=" * 70)
    print("Create New Planet Order - Missing September Images")
    print("=" * 70)
    print()
    
    if not os.environ.get("PL_API_KEY"):
        print("⚠️  Warning: PL_API_KEY not set in environment")
        print("   Using default API key (not recommended for production)")
        print()
    
    print(f"Ordering {len(MISSING_IMAGE_IDS)} images:")
    for img_id in MISSING_IMAGE_IDS:
        date = img_id[:8]  # YYYYMMDD
        print(f"  - {img_id} ({date[:4]}-{date[4:6]}-{date[6:8]})")
    print()
    
    order_payload = {
        "name": "Didal_Glacier_September_Extra",
        "products": [
            {
                "item_ids": MISSING_IMAGE_IDS,
                "item_type": "PSScene",
                "product_bundle": "analytic_sr_udm2"  # Surface reflectance + UDM2
            }
        ],
        "delivery": {
            "archive_type": "zip",
            "archive_filename": "didal_glacier_september_extra.zip"
        }
    }
    
    url = "https://api.planet.com/compute/ops/orders/v2"
    headers = {"Content-Type": "application/json"}
    auth = (API_KEY, "")
    
    try:
        print("Creating order...")
        response = requests.post(url, json=order_payload, headers=headers, auth=auth, timeout=60)
        response.raise_for_status()
        
        order_data = response.json()
        order_id = order_data.get("id")
        
        print(f"✓ Order created successfully!")
        print()
        print(f"Order ID: {order_id}")
        print(f"Name: {order_data.get('name', 'N/A')}")
        print(f"State: {order_data.get('state', 'N/A')}")
        print()
        
        # Save order info
        output_dir = "planet_images/new_september"
        os.makedirs(output_dir, exist_ok=True)
        
        order_info_file = os.path.join(output_dir, "extra_order_info.json")
        with open(order_info_file, 'w') as f:
            json.dump(order_data, f, indent=2)
        
        print(f"✓ Saved order info to: {order_info_file}")
        print()
        print("Next steps:")
        print("1. Wait for order to complete (check status with check_and_download_order.py)")
        print("2. Download the ZIP when ready")
        print("3. Extract to planet_images/sep_2025/ or planet_images/new_september/")
        print("4. Run visualization scripts to process new images")
        
        return order_id
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Error creating order: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                print(f"  Details: {json.dumps(error_data, indent=2)}")
            except:
                print(f"  Response: {e.response.text}")
        return None

if __name__ == "__main__":
    order_id = create_order()
    if order_id:
        print()
        print(f"To check order status, run:")
        print(f"  python3 check_and_download_order.py --order-id {order_id}")
        sys.exit(0)
    else:
        sys.exit(1)

