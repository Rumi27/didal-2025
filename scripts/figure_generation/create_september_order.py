#!/usr/bin/env python3
"""
Create a Planet Order to download September images.
Uses the Planet Orders API to request download of the images.
"""

import os
import json
import requests
import time

# Planet API configuration
PLANET_API_KEY = "PLAK97848b681d244728a5a7a02e73eb23d5"

# Output directory
OUTPUT_DIR = "planet_images/new_september"

# Load search results
results_file = os.path.join(OUTPUT_DIR, "september_search_results.json")

def create_order():
    """Create a Planet order for September images."""
    print("=" * 70)
    print("Create Planet Order for September Images")
    print("=" * 70)
    print()
    
    # Load image IDs from search results
    if not os.path.exists(results_file):
        print(f"✗ Search results file not found: {results_file}")
        print("  Run download_september_direct.py first to search for images.")
        return
    
    with open(results_file, 'r') as f:
        items = json.load(f)
    
    # Extract item IDs
    item_ids = [item.get("id") for item in items if item.get("id")]
    
    print(f"Found {len(item_ids)} images to order:")
    for item_id in item_ids:
        print(f"  - {item_id}")
    print()
    
    # Create order payload
    order_payload = {
        "name": "Didal_Glacier_September_2025",
        "products": [
            {
                "item_ids": item_ids,
                "item_type": "PSScene",
                "product_bundle": "analytic_sr_udm2"  # Surface reflectance with UDM2
            }
        ],
        "delivery": {
            "archive_type": "zip",
            "archive_filename": "didal_glacier_september_2025.zip"
        }
    }
    
    # API endpoint
    url = "https://api.planet.com/compute/ops/orders/v2"
    
    # Headers
    headers = {
        "Content-Type": "application/json"
    }
    
    # Authentication
    auth = (PLANET_API_KEY, "")
    
    print("Creating order...")
    print()
    
    try:
        # Create order
        response = requests.post(url, json=order_payload, headers=headers, auth=auth)
        response.raise_for_status()
        
        order_data = response.json()
        order_id = order_data.get("id")
        
        print(f"✓ Order created successfully!")
        print(f"  Order ID: {order_id}")
        print()
        print("Order details:")
        print(f"  Name: {order_data.get('name', 'N/A')}")
        print(f"  State: {order_data.get('state', 'N/A')}")
        print(f"  Created: {order_data.get('created_on', 'N/A')}")
        print()
        
        # Save order info
        order_file = os.path.join(OUTPUT_DIR, "order_info.json")
        with open(order_file, 'w') as f:
            json.dump(order_data, f, indent=2)
        
        print(f"✓ Saved order info to: {order_file}")
        print()
        print("=" * 70)
        print("Order Status")
        print("=" * 70)
        print()
        print("The order is being processed. You can:")
        print(f"1. Check order status: https://www.planet.com/account/#/orders/{order_id}")
        print("2. Or use the API to check status:")
        print(f"   curl -u {PLANET_API_KEY}: https://api.planet.com/compute/ops/orders/v2/{order_id}")
        print()
        print("Once the order is complete, you'll receive a download link.")
        print("The images will be delivered as a ZIP file.")
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Error creating order: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Response: {e.response.text}")
            try:
                error_data = e.response.json()
                print(f"  Error details: {json.dumps(error_data, indent=2)}")
            except:
                pass

def check_order_status(order_id):
    """Check the status of an existing order."""
    url = f"https://api.planet.com/compute/ops/orders/v2/{order_id}"
    auth = (PLANET_API_KEY, "")
    
    try:
        response = requests.get(url, auth=auth)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error checking order: {e}")
        return None

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Check order status
        order_id = sys.argv[1]
        print(f"Checking order status: {order_id}")
        order_data = check_order_status(order_id)
        if order_data:
            print(json.dumps(order_data, indent=2))
    else:
        # Create new order
        create_order()

