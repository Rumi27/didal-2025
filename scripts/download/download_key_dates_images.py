#!/usr/bin/env python3
"""
Download Planet images for key event dates using Orders API.
Uses the same AOI as the existing image in from_website folder.
"""

import os
import json
import asyncio
from pathlib import Path
from planet import Auth, Session, OrdersClient
from planet.order_request import build_request, product

# Planet.com API configuration
PLANET_API_KEY = "PLAK97848b681d244728a5a7a02e73eb23d5"
os.environ['PL_API_KEY'] = PLANET_API_KEY

# Key images for each event (selected best ones)
KEY_IMAGES = {
    "Before_Initial_Movement": ["20250917_064328_46_24b7"],  # Sept 17, 0% cloud
    "Second_Movement": ["20251025_062608_36_251d"],  # Oct 25, exact date
    "Continued_Movement": [
        "20251101_063201_24_2533",  # Nov 1
        "20251102_063132_61_24da",  # Nov 2
        "20251103_063453_39_2541",  # Nov 3 (earthquake day)
    ],
}

# Or download all available images
ALL_IMAGES = [
    "20250917_064328_46_24b7",
    "20250917_064330_29_24b7",
    "20250917_064332_12_24b7",
    "20250921_063355_23_24ee",
    "20250921_063357_35_24ee",
    "20251024_063032_47_250d",
    "20251025_062608_36_251d",
    "20251030_063101_40_250a",
    "20251030_063103_59_250a",
    "20251030_063309_54_2507",
    "20251030_063311_64_2507",
    "20251031_062712_77_251a",
    "20251101_063201_24_2533",
    "20251102_063132_61_24da",
    "20251103_063453_39_2541",
]

OUTPUT_DIR = "planet_images/from_website"


async def download_images(image_ids, order_name="Didal_Glacier_Key_Dates"):
    """
    Download images using Planet Orders API.
    """
    auth = Auth.from_key(PLANET_API_KEY)
    session = Session(auth=auth)
    orders_client = OrdersClient(session)
    
    print("=" * 60)
    print("Downloading Planet Images via Orders API")
    print("=" * 60)
    print(f"Images to download: {len(image_ids)}")
    print(f"Image IDs: {', '.join(image_ids[:5])}..." if len(image_ids) > 5 else f"Image IDs: {', '.join(image_ids)}")
    print()
    
    # Create order
    products_list = [
        product(item_ids=image_ids, item_type="PSScene", product_bundle="analytic_sr_udm2")
    ]
    
    order_request = build_request(
        name=order_name,
        products=products_list
    )
    
    try:
        print("Creating order...")
        order = await orders_client.create_order(order_request)
        order_id = order["id"]
        print(f"✓ Order created: {order_id}")
        print(f"  Status: {order.get('state', 'unknown')}")
        print()
        
        print("Waiting for order to complete...")
        print("  (This typically takes 10-30 minutes)")
        print("  Status updates will be shown below:")
        print()
        
        def status_callback(state):
            print(f"  → {state}")
        
        order = await orders_client.wait(order_id, callback=status_callback)
        
        print()
        print(f"✓ Order completed: {order.get('state')}")
        print()
        
        # Download order
        print(f"Downloading images to {OUTPUT_DIR}/...")
        await orders_client.download_order(order_id, directory=OUTPUT_DIR)
        
        print()
        print("=" * 60)
        print("✓ Download complete!")
        print(f"Images saved to: {OUTPUT_DIR}/")
        print()
        print("Note: Images will be in subdirectories similar to:")
        print("  glacier_psscene_analytic_sr_udm2/PSScene/")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """
    Main function - allows selection of images to download.
    """
    print("Available images for key dates:")
    print("-" * 60)
    print("1. Essential dates only (5 images):")
    print("   - Sept 17 (before initial movement)")
    print("   - Oct 25 (second movement)")
    print("   - Nov 1, 2, 3 (continued movement + earthquake)")
    print()
    print("2. All available images (15 images)")
    print()
    
    # For now, download essential dates
    essential_ids = []
    for date_group in KEY_IMAGES.values():
        essential_ids.extend(date_group)
    
    print(f"Downloading essential dates: {len(essential_ids)} images")
    print(f"Image IDs: {', '.join(essential_ids)}")
    print()
    
    asyncio.run(download_images(essential_ids, "Didal_Glacier_Essential_Dates"))


if __name__ == "__main__":
    main()

