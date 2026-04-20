#!/usr/bin/env python3
"""
Script to download full Planet images using Orders API.

This script will:
1. Create an order for selected images
2. Wait for the order to complete
3. Download the images

Note: This requires Planet API credits/subscription.
"""

import os
import json
import asyncio
from planet import Auth, Session, OrdersClient
from planet.order_request import build_request, product

# Planet.com API configuration
PLANET_API_KEY = "PLAK97848b681d244728a5a7a02e73eb23d5"
PLANET_USER_ID = "d09f3150-dcdb-4644-88d7-9a15f1c1e9b7"

# Set API key
os.environ['PL_API_KEY'] = PLANET_API_KEY

# Output directory
OUTPUT_DIR = "planet_images/full_images"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load metadata
metadata_file = "planet_images/metadata.json"


async def download_full_images(image_ids=None, max_images=5, asset_type="ortho_visual"):
    """
    Download full images using Planet Orders API.
    
    Parameters:
    -----------
    image_ids : list
        List of image IDs to download. If None, uses first max_images from metadata.
    max_images : int
        Maximum number of images to download if image_ids is None
    asset_type : str
        Asset type to download (e.g., "ortho_visual", "ortho_analytic_4b")
    """
    # Authenticate
    auth = Auth.from_key(PLANET_API_KEY)
    session = Session(auth=auth)
    orders_client = OrdersClient(session)
    
    # Load metadata and get image IDs
    with open(metadata_file, 'r') as f:
        items = json.load(f)
    
    if image_ids is None:
        image_ids = [item.get("id") for item in items[:max_images] if item.get("id")]
    
    print("=" * 60)
    print("Planet Full Image Downloader")
    print("=" * 60)
    print(f"Images to download: {len(image_ids)}")
    print(f"Asset type: {asset_type}")
    print(f"Image IDs: {', '.join(image_ids[:3])}..." if len(image_ids) > 3 else f"Image IDs: {', '.join(image_ids)}")
    print()
    
    # Build order request
    products = [
        product(item_ids=image_ids, item_type="PSScene", product_bundle=asset_type)
    ]
    
    order_request = build_request(
        name="Didal_Glacier_Images",
        products=products
    )
    
    print("Creating order...")
    try:
        # Create order
        order = await orders_client.create_order(order_request)
        order_id = order["id"]
        print(f"Order created: {order_id}")
        print(f"Order status: {order.get('state', 'unknown')}")
        print()
        
        # Wait for order to complete
        print("Waiting for order to complete (this may take several minutes)...")
        order = await orders_client.wait(order_id)
        
        print(f"Order completed: {order.get('state')}")
        print()
        
        # Download order
        print(f"Downloading images to {OUTPUT_DIR}/...")
        await orders_client.download_order(order_id, directory=OUTPUT_DIR)
        
        print()
        print("=" * 60)
        print("Download complete!")
        print(f"Images saved to: {OUTPUT_DIR}/")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """
    Main function - allows user to select images.
    """
    # Load metadata
    with open(metadata_file, 'r') as f:
        items = json.load(f)
    
    print("Available images:")
    print("-" * 60)
    for i, item in enumerate(items[:10], 1):
        item_id = item.get("id", "unknown")
        acquired = item.get("properties", {}).get("acquired", "unknown")
        print(f"{i}. {item_id} - {acquired}")
    
    print()
    print(f"Total images available: {len(items)}")
    print()
    
    choice = input("Download first 5 images? (y/n): ").lower().strip()
    
    if choice == "y":
        asyncio.run(download_full_images(max_images=5))
    else:
        indices = input("Enter image numbers to download (comma-separated, e.g., 1,2,3): ")
        try:
            indices = [int(i.strip()) - 1 for i in indices.split(",")]
            selected_ids = [items[i].get("id") for i in indices if 0 <= i < len(items) and items[i].get("id")]
            if selected_ids:
                asyncio.run(download_full_images(image_ids=selected_ids))
            else:
                print("No valid image IDs selected.")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()

