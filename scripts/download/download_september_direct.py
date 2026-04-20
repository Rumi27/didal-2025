#!/usr/bin/env python3
"""
Download September Planet images using direct HTTP requests to quick-search API.
Uses the exact curl command format provided.
"""

import os
import json
import requests
from datetime import datetime

# Planet API configuration
PLANET_API_KEY = "PLAK97848b681d244728a5a7a02e73eb23d5"

# Output directory
OUTPUT_DIR = "planet_images/new_september"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Search query (exact format from curl command)
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

def search_images():
    """Search for September images using quick-search API."""
    print("=" * 70)
    print("Search September Planet Images via Quick-Search API")
    print("=" * 70)
    print()
    
    # API endpoint
    url = "https://api.planet.com/data/v1/quick-search"
    
    # Headers
    headers = {
        "Content-Type": "application/json"
    }
    
    # Authentication
    auth = (PLANET_API_KEY, "")
    
    print("Sending search request...")
    print()
    
    try:
        # Make POST request
        response = requests.post(url, json=SEARCH_QUERY, headers=headers, auth=auth)
        response.raise_for_status()
        
        # Parse response
        data = response.json()
        
        items = data.get("features", [])
        print(f"✓ Found {len(items)} items")
        print()
        
        # Filter for September images we want
        sept_items = []
        for item in items:
            item_id = item.get("id", "")
            for target_id in SEPT_IMAGE_IDS:
                if target_id in item_id:
                    sept_items.append(item)
                    props = item.get("properties", {})
                    acquired = props.get("acquired", "N/A")
                    print(f"  ✓ Found: {item_id}")
                    print(f"    Acquired: {acquired}")
                    break
        
        print()
        print(f"Matched {len(sept_items)} September images")
        print()
        
        if not sept_items:
            print("⚠️  No matching September images found.")
            print("Showing first few items found:")
            for item in items[:5]:
                item_id = item.get("id", "N/A")
                props = item.get("properties", {})
                acquired = props.get("acquired", "N/A")
                print(f"  - {item_id} ({acquired})")
            return
        
        # Save results
        results_file = os.path.join(OUTPUT_DIR, "september_search_results.json")
        with open(results_file, 'w') as f:
            json.dump(sept_items, f, indent=2)
        
        print(f"✓ Saved search results to: {results_file}")
        print()
        print("=" * 70)
        print("Search Complete")
        print("=" * 70)
        print()
        print("Next steps:")
        print("1. Use Planet Explorer web interface to download these images")
        print("2. Or use Planet Orders API for bulk download")
        print()
        print("Image IDs found:")
        for item in sept_items:
            print(f"  - {item.get('id', 'N/A')}")
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Response: {e.response.text}")

if __name__ == "__main__":
    search_images()

