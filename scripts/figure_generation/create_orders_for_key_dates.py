#!/usr/bin/env python3
"""
Create Planet orders for better images at key dates:
- Before initial movement (September 4, 2025 - best quality)
- Second movement (October 25, 2025 - alternative image)
"""

import os
import json
import requests

# Planet API configuration
PLANET_API_KEY = "PLAK97848b681d244728a5a7a02e73eb23d5"

# Best images found
BEFORE_IMAGE = "20250904_063523_93_24fd"  # Sept 4 - 0% cloud, closest to glacier
OCT25_IMAGE = "20251025_062610_58_251d"   # Oct 25 - alternative image

def create_order(item_ids, order_name, description):
    """Create a Planet order."""
    print(f"\n{'=' * 70}")
    print(f"Creating Order: {order_name}")
    print(f"Description: {description}")
    print(f"{'=' * 70}")
    print()
    
    order_payload = {
        "name": order_name,
        "products": [
            {
                "item_ids": item_ids,
                "item_type": "PSScene",
                "product_bundle": "analytic_sr_udm2"  # Surface reflectance with UDM2
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
    
    print(f"Ordering {len(item_ids)} image(s):")
    for item_id in item_ids:
        print(f"  - {item_id}")
    print()
    
    try:
        response = requests.post(url, json=order_payload, headers=headers, auth=auth)
        response.raise_for_status()
        
        order_data = response.json()
        order_id = order_data.get("id")
        
        print(f"✓ Order created successfully!")
        print(f"  Order ID: {order_id}")
        print(f"  State: {order_data.get('state', 'N/A')}")
        print()
        
        # Save order info
        order_file = f"planet_images/orders/{order_name.lower().replace(' ', '_')}_order.json"
        os.makedirs("planet_images/orders", exist_ok=True)
        with open(order_file, 'w') as f:
            json.dump(order_data, f, indent=2)
        
        print(f"✓ Saved order info to: {order_file}")
        print()
        print(f"Check status: https://www.planet.com/account/#/orders/{order_id}")
        print()
        
        return order_id
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Error creating order: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Response: {e.response.text}")
        return None

def main():
    """Main function."""
    print("=" * 70)
    print("Create Orders for Key Dates - Better Images")
    print("=" * 70)
    print()
    print("Key dates:")
    print("  Initial movement: 2025-09-19")
    print("  Second movement: 2025-10-25")
    print()
    print("Images to order:")
    print(f"  1. Before movement: {BEFORE_IMAGE} (Sept 4, 0% cloud)")
    print(f"  2. Second movement: {OCT25_IMAGE} (Oct 25, 27% cloud)")
    print()
    
    # Create order for "before" image
    before_order_id = create_order(
        [BEFORE_IMAGE],
        "Didal_Glacier_Before_Movement_Sept4",
        "Before initial movement - September 4, 2025 (best quality)"
    )
    
    # Create order for October 25 alternative
    oct25_order_id = create_order(
        [OCT25_IMAGE],
        "Didal_Glacier_Second_Movement_Oct25_Alt",
        "Second movement - October 25, 2025 (alternative image)"
    )
    
    print("\n" + "=" * 70)
    print("Orders Created")
    print("=" * 70)
    print()
    if before_order_id:
        print(f"✓ Before movement order: {before_order_id}")
    if oct25_order_id:
        print(f"✓ October 25 order: {oct25_order_id}")
    print()
    print("Next steps:")
    print("1. Wait for orders to complete (usually a few minutes)")
    print("2. Check status: python3 check_and_download_order.py <order_id>")
    print("3. Or check online: https://www.planet.com/account/#/orders/")
    print()

if __name__ == "__main__":
    main()

