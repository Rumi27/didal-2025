#!/usr/bin/env python3
"""
Search for September images using the exact API query provided.
Uses the Planet quick-search API with the exact geometry and filters.
"""

import os
import json
import requests

# Planet API configuration
PLANET_API_KEY = "PLAK97848b681d244728a5a7a02e73eb23d5"

# Exact search query from curl command
SEARCH_QUERY = {
    "geometry": {
        "type": "Polygon",
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
                        [70.74417495, 39.04524936], [70.7385, 39.04546602]]]
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
                        "gte": "2025-09-07T00:00:00.000Z",
                        "lte": "2025-09-30T23:59:59.999Z"
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
                                "type": "RangeFilter",
                                "config": {"gte": 0, "lte": 0.36},
                                "field_name": "cloud_cover"
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

OUTPUT_DIR = "planet_images/new_september"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def search_september_images():
    """Search for September images using the exact API query."""
    print("=" * 70)
    print("Search September Images - Exact API Query")
    print("=" * 70)
    print()
    print("Search parameters:")
    print("  Date range: 2025-09-07 to 2025-09-30")
    print("  Cloud cover: ≤ 36%")
    print("  Item type: PSScene")
    print("  Asset: basic_analytic_4b")
    print()
    
    url = "https://api.planet.com/data/v1/quick-search"
    headers = {"Content-Type": "application/json"}
    auth = (PLANET_API_KEY, "")
    
    try:
        print("Sending search request...")
        response = requests.post(url, json=SEARCH_QUERY, headers=headers, auth=auth, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        items = data.get("features", [])
        
        print(f"✓ Found {len(items)} images")
        print()
        
        if not items:
            print("No images found matching the criteria")
            return []
        
        # Filter for images that cover the glacier location
        glacier_lat = 39.0005
        glacier_lon = 70.7385
        
        good_images = []
        print("Images covering glacier location (39.0005°N, 70.7385°E):")
        print()
        
        for item in items:
            item_id = item.get("id", "")
            props = item.get("properties", {})
            acquired = props.get("acquired", "N/A")
            cloud_cover = props.get("cloud_percent", "N/A")
            
            # Check geometry
            geometry = item.get("geometry", {})
            if geometry.get("type") == "Polygon":
                coords = geometry.get("coordinates", [])
                if coords and len(coords) > 0:
                    # Get bounding box
                    lons = [c[0] for ring in coords for c in ring]
                    lats = [c[1] for ring in coords for c in ring]
                    
                    min_lon, max_lon = min(lons), max(lons)
                    min_lat, max_lat = min(lats), max(lats)
                    
                    # Check if glacier is in bounds
                    in_bounds = (min_lon <= glacier_lon <= max_lon and 
                                min_lat <= glacier_lat <= max_lat)
                    
                    if in_bounds:
                        good_images.append({
                            "id": item_id,
                            "acquired": acquired,
                            "cloud_cover": cloud_cover,
                            "bounds": {
                                "lon": (min_lon, max_lon),
                                "lat": (min_lat, max_lat)
                            },
                            "full_item": item
                        })
                        print(f"  ✓ {item_id}")
                        print(f"    Acquired: {acquired}")
                        print(f"    Cloud cover: {cloud_cover}%")
                        print(f"    Bounds: {min_lon:.4f}°E to {max_lon:.4f}°E")
                        print(f"             {min_lat:.4f}°N to {max_lat:.4f}°N")
                        print()
        
        # Save results
        results_file = os.path.join(OUTPUT_DIR, "september_search_results.json")
        with open(results_file, 'w') as f:
            json.dump({
                "total_found": len(items),
                "covering_glacier": len(good_images),
                "images": good_images
            }, f, indent=2, default=str)
        
        print(f"✓ Saved results to: {results_file}")
        print()
        print(f"Summary: {len(good_images)} images cover the glacier location")
        
        return good_images
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Response: {e.response.text}")
        return []

def check_existing_order():
    """Check status of existing September order."""
    print("=" * 70)
    print("Check Existing September Order")
    print("=" * 70)
    print()
    
    order_id = "fee2882b-798b-4b20-9239-ec9fbc072acd"
    url = f"https://api.planet.com/compute/ops/orders/v2/{order_id}"
    auth = (PLANET_API_KEY, "")
    
    try:
        response = requests.get(url, auth=auth, timeout=30)
        response.raise_for_status()
        
        order_data = response.json()
        
        print(f"Order ID: {order_id}")
        print(f"Name: {order_data.get('name', 'N/A')}")
        print(f"State: {order_data.get('state', 'N/A')}")
        print(f"Created: {order_data.get('created_on', 'N/A')}")
        print(f"Last modified: {order_data.get('last_modified', 'N/A')}")
        print()
        
        # Check products
        products = order_data.get('products', [])
        if products:
            print("Products ordered:")
            for i, product in enumerate(products, 1):
                item_ids = product.get('item_ids', [])
                print(f"  Product {i}: {len(item_ids)} items")
                print(f"    Item type: {product.get('item_type', 'N/A')}")
                print(f"    Bundle: {product.get('product_bundle', 'N/A')}")
                for item_id in item_ids[:5]:
                    print(f"      - {item_id}")
                if len(item_ids) > 5:
                    print(f"      ... and {len(item_ids) - 5} more")
        print()
        
        # Check delivery
        if order_data.get('state') == 'success':
            _links = order_data.get('_links', {})
            results = _links.get('results', [])
            print(f"Delivery: {len(results)} download link(s) available")
        
        return order_data
        
    except Exception as e:
        print(f"✗ Error checking order: {e}")
        return None

def main():
    """Main function."""
    # Check existing order first
    order_data = check_existing_order()
    print()
    
    # Search for September images
    good_images = search_september_images()
    
    print()
    print("=" * 70)
    print("Next Steps")
    print("=" * 70)
    print()
    
    if good_images:
        print(f"Found {len(good_images)} images covering the glacier.")
        print("You can:")
        print("1. Create a new order for these images")
        print("2. Compare with existing order to see what's missing")
    else:
        print("No images found covering the glacier location.")
        print("You may need to:")
        print("1. Adjust the search criteria (date range, cloud cover)")
        print("2. Check if images are available for this area")
    
    print()
    print("Note: The search uses 'basic_analytic_4b' asset filter.")
    print("For orders, you may want 'analytic_sr_udm2' bundle instead.")

if __name__ == "__main__":
    main()

