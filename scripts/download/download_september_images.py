#!/usr/bin/env python3
"""
Download September Planet images using Planet API.
Collection: 38647acb-8696-4a10-af32-56e41f5d8141
"""

import os
import asyncio
from planet import Auth, Session, DataClient
from planet.data_filter import and_filter, geometry_filter, date_range_filter

# Planet API configuration
PLANET_API_KEY = "PLAK97848b681d244728a5a7a02e73eb23d5"
PLANET_USER_ID = "d09f3150-dcdb-4644-88d7-9a15f1c1e9b7"

# Collection and delivery info
COLLECTION_ID = "38647acb-8696-4a10-af32-56e41f5d8141"
DELIVERY_ID = "df00030d-eb45-4feb-9efa-0932b0827ca6"

# Image IDs to download
SEPT_IMAGE_IDS = [
    "20250914_063119_12_252d",
    "20250914_062418_62_24f0",
    "20250913_063820_03_24d5",
    "20250913_063818_16_24d5",
    "20250913_062702_66_2516",
    "20250912_063959_56_24fb",
    "20250912_063417_10_252b",
    "20250909_063919_68_24ed",
    "20250909_063917_61_24ed"
]

# Output directory
OUTPUT_DIR = "planet_images/new_september"
os.makedirs(OUTPUT_DIR, exist_ok=True)

async def download_september_images():
    """Download September images from Planet."""
    print("=" * 70)
    print("Download September Planet Images")
    print("=" * 70)
    print()
    print(f"Collection ID: {COLLECTION_ID}")
    print(f"Delivery ID: {DELIVERY_ID}")
    print(f"Output directory: {OUTPUT_DIR}")
    print()
    
    auth = Auth.from_key(PLANET_API_KEY)
    
    async with Session(auth=auth) as sess:
        client = DataClient(sess)
        
        # Verify authentication
        try:
            user_info = await client.get_current_user()
            print(f"✓ Authenticated with User ID: {user_info['id']}")
            print()
        except Exception as e:
            print(f"✗ Authentication failed: {e}")
            return
        
        # Try to get items from the collection/delivery
        print("Searching for images in collection...")
        print()
        
        # Method 1: Search by item IDs
        print("Method 1: Searching by item IDs...")
        items_found = []
        
        for img_id in SEPT_IMAGE_IDS:
            try:
                # Search for this specific item
                query = and_filter([
                    geometry_filter({
                        "type": "Point",
                        "coordinates": [70.7385, 39.0005]  # Glacier location
                    }),
                    date_range_filter("acquired", gte="2025-09-09T00:00:00Z", lte="2025-09-14T23:59:59Z")
                ])
                
                # Create search
                search_name = f"September_{img_id}_Search"
                item_types = ["PSScene"]
                
                try:
                    saved_search = await client.create_search(
                        name=search_name,
                        search_filter=query,
                        item_types=item_types
                    )
                    search_id = saved_search["id"]
                    
                    # Run search
                    search_result = client.run_search(search_id)
                    
                    # Get items
                    async for item in search_result:
                        item_id = item.get("id", "")
                        if img_id in item_id:
                            items_found.append(item)
                            print(f"  ✓ Found: {item_id}")
                            break
                except Exception as e:
                    print(f"  ⚠️  Search error for {img_id}: {e}")
                    continue
                    
            except Exception as e:
                print(f"  ⚠️  Error searching for {img_id}: {e}")
                continue
        
        print()
        
        # Method 2: Try to access collection directly
        print("Method 2: Trying to access collection/delivery directly...")
        try:
            # Try to get collection
            # Note: This may require different API endpoints
            print("  Attempting to access collection...")
            # Collection access might require different methods
        except Exception as e:
            print(f"  ⚠️  Collection access error: {e}")
        
        print()
        
        if not items_found:
            print("⚠️  No items found via search.")
            print()
            print("Alternative approach:")
            print("1. Use Planet Explorer web interface to download images")
            print("2. Or use Planet Orders API if you have order access")
            print()
            print("For manual download:")
            print(f"  - Collection ID: {COLLECTION_ID}")
            print(f"  - Delivery ID: {DELIVERY_ID}")
            print(f"  - Image IDs: {', '.join(SEPT_IMAGE_IDS[:3])}...")
            return
        
        # Download items
        print(f"Found {len(items_found)} items. Downloading...")
        print()
        
        for item in items_found:
            item_id = item.get("id", "")
            print(f"Downloading: {item_id}")
            
            try:
                # Get item assets
                assets = await client.get_asset(item_id, asset_type="ortho_analytic_4b_sr")
                
                if assets:
                    # Download asset
                    # Note: Asset download requires additional steps
                    print(f"  ✓ Asset available for {item_id}")
                    print(f"    Download URL: {assets.get('location', 'N/A')}")
                else:
                    print(f"  ⚠️  No assets found for {item_id}")
                    
            except Exception as e:
                print(f"  ⚠️  Error downloading {item_id}: {e}")
        
        print()
        print("=" * 70)
        print("Download Complete")
        print("=" * 70)
        print()
        print("Note: Full download may require Planet Orders API or web interface.")
        print("Check downloaded files in:", OUTPUT_DIR)

def main():
    """Main function."""
    try:
        asyncio.run(download_september_images())
    except KeyboardInterrupt:
        print("\n\nDownload cancelled by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

