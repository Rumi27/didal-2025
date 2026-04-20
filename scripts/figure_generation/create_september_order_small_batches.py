#!/usr/bin/env python3
"""
Create September orders in smaller batches to work within quota limits.
Prioritizes the most important dates first (September 17).
"""

import os
import json
import requests
import sys
import time

API_KEY = os.environ.get("PL_API_KEY", "PLAK97848b681d244728a5a7a02e73eb23d5")

# Prioritize September 17 (most important for timeline)
PRIORITY_ITEMS = [
    "20250917_064330_29_24b7",  # Sept 17 - 2% cloud
    "20250917_064328_46_24b7",  # Sept 17 - 0% cloud
]

# Other items
OTHER_ITEMS = [
    "20250927_063229_94_253f",  # Sept 27
    "20250922_063432_07_24e5",  # Sept 22
    "20250922_063119_39_2531",  # Sept 22
    "20250922_062909_81_2507",  # Sept 22
    "20250921_063357_35_24ee",  # Sept 21
    "20250921_063355_23_24ee",  # Sept 21
    "20250908_062528_54_251a",  # Sept 8
]

def create_order(item_ids, order_name_suffix):
    """Create an order for a batch of items."""
    order_payload = {
        "name": f"Didal_Glacier_September_{order_name_suffix}",
        "products": [
            {
                "item_ids": item_ids,
                "item_type": "PSScene",
                "product_bundle": "analytic_sr_udm2"
            }
        ],
        "delivery": {
            "archive_type": "zip",
            "archive_filename": f"didal_glacier_september_{order_name_suffix.lower()}.zip"
        }
    }
    
    url = "https://api.planet.com/compute/ops/orders/v2"
    headers = {"Content-Type": "application/json"}
    auth = (API_KEY, "")
    
    try:
        response = requests.post(url, json=order_payload, headers=headers, auth=auth, timeout=60)
        response.raise_for_status()
        
        order_data = response.json()
        order_id = order_data.get("id")
        state = order_data.get("state", "unknown")
        
        return order_id, state, order_data
        
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                return None, "error", error_data
            except:
                return None, "error", {"message": str(e)}
        return None, "error", {"message": str(e)}

def main():
    """Main function."""
    print("=" * 70)
    print("Create September Orders in Small Batches")
    print("=" * 70)
    print()
    print("Note: Your account has hit quota limits.")
    print("Creating smaller orders to work within quota.")
    print()
    
    orders_created = []
    
    # Order 1: Priority - September 17 (most important)
    print("Creating Order 1: September 17 (Priority)...")
    order_id, state, order_data = create_order(PRIORITY_ITEMS, "Priority_Sept17")
    
    if order_id:
        orders_created.append({
            "order_id": order_id,
            "name": f"Didal_Glacier_September_Priority_Sept17",
            "items": PRIORITY_ITEMS,
            "state": state
        })
        print(f"  ✓ Order created: {order_id}")
        print(f"    State: {state}")
        if state == "failed":
            print(f"    Error: {order_data.get('last_message', 'Unknown')}")
    else:
        print(f"  ✗ Order failed: {order_data}")
    
    print()
    
    # Order 2: Other dates (if quota allows)
    if len(OTHER_ITEMS) > 0:
        print("Creating Order 2: Other September dates...")
        # Split into smaller batches of 3-4 items
        batch_size = 3
        for i in range(0, len(OTHER_ITEMS), batch_size):
            batch = OTHER_ITEMS[i:i+batch_size]
            batch_num = i // batch_size + 2
            
            print(f"  Batch {batch_num}: {len(batch)} items")
            order_id, state, order_data = create_order(batch, f"Batch{batch_num}")
            
            if order_id:
                orders_created.append({
                    "order_id": order_id,
                    "name": f"Didal_Glacier_September_Batch{batch_num}",
                    "items": batch,
                    "state": state
                })
                print(f"    ✓ Order created: {order_id} (State: {state})")
                if state == "failed":
                    print(f"      Error: {order_data.get('last_message', 'Unknown')}")
                    if "quota" in order_data.get('last_message', '').lower():
                        print(f"      ⚠️  Quota exceeded. Wait and try remaining batches later.")
                        break
            else:
                print(f"    ✗ Order failed: {order_data}")
            
            # Small delay between orders
            if i + batch_size < len(OTHER_ITEMS):
                time.sleep(1)
    
    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print()
    
    if orders_created:
        print(f"Created {len(orders_created)} order(s):")
        for order in orders_created:
            print(f"  - {order['order_id']}: {order['name']} ({order['state']})")
            print(f"    Items: {len(order['items'])}")
        
        # Save order info
        output_file = "planet_images/new_september/batch_orders_info.json"
        os.makedirs("planet_images/new_september", exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(orders_created, f, indent=2)
        
        print()
        print(f"✓ Saved order info to: {output_file}")
        print()
        print("To check order status:")
        for order in orders_created:
            print(f"  python3 check_and_download_order.py --order-id {order['order_id']}")
    else:
        print("No orders were created successfully.")
        print("Your account quota may be exhausted.")
        print("Options:")
        print("  1. Wait for quota to reset (usually monthly)")
        print("  2. Upgrade your Planet plan")
        print("  3. Contact Planet support about quota limits")

if __name__ == "__main__":
    main()


