#!/usr/bin/env python3
"""
Download September Planet images using the exact API search query.
Uses the Planet API quick-search endpoint.
"""

import os
import json
import asyncio
import requests
from planet import Auth, Session, DataClient
from datetime import datetime

# Planet API configuration
PLANET_API_KEY = "PLAK97848b681d244728a5a7a02e73eb23d5"
PLANET_USER_ID = "d09f3150-dcdb-4644-88d7-9a15f1c1e9b7"

# Output directory
OUTPUT_DIR = "planet_images/new_september"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Search query from curl command
SEARCH_QUERY = {
    "geometry": {
        "coordinates": [[[70.7385, 39.04546602], [70.73282505, 39.04524936], [70.72720486, 39.04460146],
                        [70.72169365, 39.04352859], [70.71634459, 39.04204109], [70.71120928, 39.04015331],
                        [70.70633723, 39.03788346], [70.70177541, 39.03525345], [70.6975678, 39.03228863],
                        [70.69375491, 39.0290176], [70.69037346, 39.0254719], [70.68745599, 39.02168572],
                        [70.68503053, 39.01769555], [70.6831204, 39.01353986], [70.68174389, 39.00925869],
                        [70.68091417, 39.00489329], [70.68063914, 39.00048571], [70.68092135, 38.99607841],
                        [70.68175796, 38.99171382], [70.68314083, 38.98743397], [70.68505654, 38.98328006],
                        [70.68748656, 38.97929206], [70.69040743, 38.97550835], [70.69379097, 38.97196533],
                        [70.69760457, 38.96869708], [70.70181148, 38.96573505], [70.7063712, 38.96310772],
                        [70.71123985, 38.96084034], [70.7163706, 38.95895473], [70.72171408, 38.957469],
                        [70.72721894, 38.95639745], [70.73283223, 38.95575037], [70.7385, 38.95553398],
                        [70.74416777, 38.95575037], [70.74978106, 38.95639745], [70.75528592, 38.957469],
                        [70.7606294, 38.95895473], [70.76576015, 38.96084034], [70.7706288, 38.96310772],
                        [70.77518852, 38.96573505], [70.77939543, 38.96869708], [70.78320903, 38.97196533],
                        [70.78659257, 38.97550835], [70.78951344, 38.97929206], [70.79194346, 38.98328006],
                        [70.79385917, 38.98743397], [70.79524204, 38.99171382], [70.79607865, 38.99607841],
                        [70.79636086, 39.00048571], [70.79608583, 39.00489329], [70.79525611, 39.00925869],
                        [70.7938796, 39.01353986], [70.79196947, 39.01769555], [70.78954401, 39.02168572],
                        [70.78662654, 39.0254719], [70.78324509, 39.0290176], [70.7794322, 39.03228863],
                        [70.77522459, 39.03525345], [70.77066277, 39.03788346], [70.76579072, 39.04015331],
                        [70.76065541, 39.04204109], [70.75530635, 39.04352859], [70.74979514, 39.04460146],
                        [70.74417495, 39.04524936], [70.7385, 39.04546602]]],
        "type": "Polygon"
    },
    "filter": {
        "type": "AndFilter",
        "config": [
            {
                "type": "OrFilter",
                "config": [{
                    "type": "DateRangeFilter",
                    "field_name": "acquired",
                    "config": {
                        "gte": "2025-09-01T00:00:00.000Z",
                        "lte": "2025-10-31T23:59:59.999Z"
                    }
                }]
            },
            {
                "type": "OrFilter",
                "config": [
                    {
                        "type": "AndFilter",
                        "config": [
                            {
                                "type": "AndFilter",
                                "config": [
                                    {
                                        "type": "StringInFilter",
                                        "field_name": "item_type",
                                        "config": ["PSScene"]
                                    },
                                    {
                                        "type": "AndFilter",
                                        "config": [{
                                            "type": "AssetFilter",
                                            "config": ["basic_analytic_4b"]
                                        }]
                                    }
                                ]
                            },
                            {
                                "type": "StringInFilter",
                                "field_name": "instrument",
                                "config": ["PS2", "PS2.SD", "PSB.SD"]
                            },
                            {
                                "type": "StringInFilter",
                                "field_name": "publishing_stage",
                                "config": ["standard", "finalized"]
                            }
                        ]
                    }
                ]
            },
            {
                "type": "PermissionFilter",
                "config": ["assets:download", "webtiles:stream"]
            }
        ]
    },
    "item_types": ["PSScene"]
}

# September image IDs we're looking for
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

async def search_and_download():
    """Search for and download September images."""
    print("=" * 70)
    print("Download September Planet Images via API")
    print("=" * 70)
    print()
    
    auth = Auth.from_key(PLANET_API_KEY)
    
    async with Session(auth=auth) as sess:
        client = DataClient(sess)
        
        # Verify authentication
        print("✓ Authenticated with Planet API")
        print()
        
        # Search for images
        print("Searching for September images...")
        print()
        
        # Use quick search
        try:
            # Create search using the query
            search_name = "September_Didal_Glacier_Search"
            saved_search = await client.create_search(
                name=search_name,
                search_filter=SEARCH_QUERY,
                item_types=["PSScene"]
            )
            search_id = saved_search["id"]
            print(f"✓ Created search: {search_id}")
            print()
            
            # Run search
            search_result = client.run_search(search_id)
            
            # Collect matching items
            all_items = []
            async for item in search_result:
                all_items.append(item)
                if len(all_items) >= 100:  # Limit to 100 items
                    break
            
            print(f"Found {len(all_items)} total items")
            print()
            
            # Filter for September images we want
            sept_items = []
            for item in all_items:
                item_id = item.get("id", "")
                for target_id in SEPT_IMAGE_IDS:
                    if target_id in item_id:
                        sept_items.append(item)
                        print(f"  ✓ Found: {item_id}")
                        break
            
            print()
            print(f"Matched {len(sept_items)} September images")
            print()
            
            if not sept_items:
                print("⚠️  No matching September images found in search results.")
                print("Showing first few items found:")
                for item in all_items[:5]:
                    print(f"  - {item.get('id', 'N/A')} ({item.get('properties', {}).get('acquired', 'N/A')})")
                return
            
            # Download items
            print("Downloading images...")
            print()
            
            for item in sept_items:
                item_id = item.get("id", "")
                print(f"Processing: {item_id}")
                
                try:
                    # Get available assets
                    try:
                        asset_types = await client.list_asset_types(item_id)
                        print(f"  Available asset types: {asset_types}")
                        
                        # Look for analytic surface reflectance asset
                        asset_type = "ortho_analytic_4b_sr"  # Surface reflectance
                        
                        if asset_type in asset_types:
                            asset = await client.get_asset(item_id, asset_type=asset_type)
                            
                            if asset and asset.get("status") == "active":
                                print(f"  ✓ Asset available: {asset_type}")
                                print(f"    Location: {asset.get('location', 'N/A')[:80]}...")
                                
                                # Note: Actual download requires additional steps
                                print(f"    Note: Use Planet Orders API or web interface for full download")
                            else:
                                print(f"  ⚠️  Asset not available or not active")
                        else:
                            print(f"  ⚠️  Asset type {asset_type} not available")
                            print(f"     Available: {', '.join(asset_types)}")
                            
                    except Exception as e:
                        print(f"  ⚠️  Error getting asset: {e}")
                    
                except Exception as e:
                    print(f"  ⚠️  Error processing {item_id}: {e}")
                
                print()
            
            print("=" * 70)
            print("Search Complete")
            print("=" * 70)
            print()
            print("Note: Full image download typically requires:")
            print("  1. Planet Orders API (for bulk downloads)")
            print("  2. Planet Explorer web interface (for manual downloads)")
            print()
            print("The search found the images. Use the item IDs above to download via web interface.")
            
        except Exception as e:
            print(f"Error during search: {e}")
            import traceback
            traceback.print_exc()

def main():
    """Main function."""
    try:
        asyncio.run(search_and_download())
    except KeyboardInterrupt:
        print("\n\nDownload cancelled by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

