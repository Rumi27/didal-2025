#!/usr/bin/env python3
"""
Discover and assess cloud-free optical imagery for feature tracking validation.

This script queries Sentinel-2 and Landsat archives to identify cloud-free
image pairs suitable for optical feature tracking.

Requirements:
    pip install sentinelsat landsatxplore rasterio geopandas
    # Or use Google Earth Engine API
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import json
import warnings
warnings.filterwarnings('ignore')

# Configuration
GLACIER_LON = 70.72
GLACIER_LAT = 38.97
STUDY_START = '2025-09-01'
STUDY_END = '2025-11-30'
OUTPUT_DIR = Path("processed_data/velocity_validation/optical")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Temporal baseline for feature tracking (days)
MIN_BASELINE = 6
MAX_BASELINE = 12

def check_sentinel2_availability():
    """Check Sentinel-2 scene availability via Copernicus Data Space."""
    print("=" * 80)
    print("SENTINEL-2 SCENE DISCOVERY")
    print("=" * 80)
    
    print("\n1. Checking Sentinel-2 availability...")
    print("   Note: Requires Copernicus Data Space API access")
    print("   Alternative: Use Google Earth Engine (see use_google_earth_engine.py)")
    
    # Try to use sentinelsat or Copernicus API
    try:
        from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
        from datetime import datetime
        
        # Initialize API (requires credentials)
        # api = SentinelAPI('username', 'password', 'https://apihub.copernicus.eu/apihub')
        
        print("   ⚠️  Sentinel-2 API access requires credentials")
        print("   See: https://dataspace.copernicus.eu/")
        print("   Or use Google Earth Engine for easier access")
        
        return None
        
    except ImportError:
        print("   ⚠️  sentinelsat not installed")
        print("   Install with: pip install sentinelsat")
        return None
    except Exception as e:
        print(f"   ⚠️  Error accessing Sentinel-2: {e}")
        return None

def check_landsat_availability():
    """Check Landsat scene availability via USGS EarthExplorer."""
    print("\n2. Checking Landsat availability...")
    print("   Note: Requires USGS EarthExplorer API access")
    
    try:
        from landsatxplore.api import API
        
        # Initialize API (requires credentials)
        # api = API('username', 'password')
        
        print("   ⚠️  Landsat API access requires credentials")
        print("   See: https://earthexplorer.usgs.gov/")
        print("   Or use Google Earth Engine for easier access")
        
        return None
        
    except ImportError:
        print("   ⚠️  landsatxplore not installed")
        print("   Install with: pip install landsatxplore")
        return None
    except Exception as e:
        print(f"   ⚠️  Error accessing Landsat: {e}")
        return None

def check_google_earth_engine():
    """Check availability via Google Earth Engine (recommended)."""
    print("\n3. Checking Google Earth Engine availability...")
    
    try:
        import ee
        
        # Initialize (requires authentication)
        try:
            ee.Initialize()
            print("   ✓ Google Earth Engine initialized")
            
            # Define area of interest
            aoi = ee.Geometry.Point([GLACIER_LON, GLACIER_LAT]).buffer(5000)  # 5km buffer
            
            # Query Sentinel-2
            s2_collection = ee.ImageCollection('COPERNICUS/S2_SR') \
                .filterBounds(aoi) \
                .filterDate(STUDY_START, STUDY_END) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
            
            s2_count = s2_collection.size().getInfo()
            print(f"   Sentinel-2 scenes (cloud <30%): {s2_count}")
            
            # Get scene dates
            s2_dates = s2_collection.aggregate_array('system:time_start').getInfo()
            s2_dates = [datetime.fromtimestamp(d/1000) for d in s2_dates]
            s2_dates.sort()
            
            # Query Landsat
            landsat_collection = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2') \
                .filterBounds(aoi) \
                .filterDate(STUDY_START, STUDY_END) \
                .filter(ee.Filter.lt('CLOUD_COVER', 30))
            
            landsat_count = landsat_collection.size().getInfo()
            print(f"   Landsat 8 scenes (cloud <30%): {landsat_count}")
            
            # Get scene dates
            landsat_dates = landsat_collection.aggregate_array('system:time_start').getInfo()
            landsat_dates = [datetime.fromtimestamp(d/1000) for d in landsat_dates]
            landsat_dates.sort()
            
            # Find suitable pairs
            pairs = find_suitable_pairs(s2_dates, landsat_dates)
            
            return {
                'sentinel2_count': s2_count,
                'sentinel2_dates': [d.strftime('%Y-%m-%d') for d in s2_dates],
                'landsat_count': landsat_count,
                'landsat_dates': [d.strftime('%Y-%m-%d') for d in landsat_dates],
                'suitable_pairs': pairs
            }
            
        except Exception as e:
            print(f"   ⚠️  Google Earth Engine not authenticated")
            print(f"   Run: earthengine authenticate")
            print(f"   Error: {e}")
            return None
            
    except ImportError:
        print("   ⚠️  earthengine-api not installed")
        print("   Install with: pip install earthengine-api")
        print("   Then authenticate: earthengine authenticate")
        return None

def find_suitable_pairs(s2_dates, landsat_dates):
    """Find suitable image pairs for feature tracking."""
    print("\n4. Finding suitable pairs for feature tracking...")
    
    all_dates = []
    for d in s2_dates:
        all_dates.append({'date': d, 'source': 'Sentinel-2'})
    for d in landsat_dates:
        all_dates.append({'date': d, 'source': 'Landsat'})
    
    all_dates.sort(key=lambda x: x['date'])
    
    pairs = []
    for i in range(len(all_dates)):
        for j in range(i+1, len(all_dates)):
            date1 = all_dates[i]['date']
            date2 = all_dates[j]['date']
            baseline = (date2 - date1).days
            
            if MIN_BASELINE <= baseline <= MAX_BASELINE:
                pairs.append({
                    'master_date': date1.strftime('%Y-%m-%d'),
                    'slave_date': date2.strftime('%Y-%m-%d'),
                    'baseline_days': baseline,
                    'master_source': all_dates[i]['source'],
                    'slave_source': all_dates[j]['source'],
                    'midpoint_date': (date1 + timedelta(days=baseline/2)).strftime('%Y-%m-%d')
                })
    
    print(f"   Found {len(pairs)} suitable pairs (baseline: {MIN_BASELINE}-{MAX_BASELINE} days)")
    
    # Save pairs
    if pairs:
        pairs_df = pd.DataFrame(pairs)
        pairs_file = OUTPUT_DIR / "suitable_optical_pairs.csv"
        pairs_df.to_csv(pairs_file, index=False)
        print(f"   ✅ Pairs saved: {pairs_file}")
        
        # Print summary
        print("\n   Pair summary:")
        for i, pair in enumerate(pairs[:10], 1):  # Show first 10
            print(f"      {i}. {pair['master_date']} → {pair['slave_date']} "
                  f"({pair['baseline_days']} days, {pair['master_source']} → {pair['slave_source']})")
        if len(pairs) > 10:
            print(f"      ... and {len(pairs) - 10} more pairs")
    
    return pairs

def main():
    """Main execution."""
    print("=" * 80)
    print("OPTICAL IMAGERY DISCOVERY FOR FEATURE TRACKING")
    print("=" * 80)
    print(f"\nStudy area: {GLACIER_LAT}°N, {GLACIER_LON}°E")
    print(f"Date range: {STUDY_START} to {STUDY_END}")
    print(f"Baseline range: {MIN_BASELINE}-{MAX_BASELINE} days")
    
    # Try Google Earth Engine first (easiest)
    results = check_google_earth_engine()
    
    if results is None:
        # Try other methods
        check_sentinel2_availability()
        check_landsat_availability()
        
        print("\n" + "=" * 80)
        print("RECOMMENDATION")
        print("=" * 80)
        print("\nFor easiest access, use Google Earth Engine:")
        print("  1. Install: pip install earthengine-api")
        print("  2. Authenticate: earthengine authenticate")
        print("  3. Run this script again")
        print("\nOr manually download from:")
        print("  - Sentinel-2: https://dataspace.copernicus.eu/")
        print("  - Landsat: https://earthexplorer.usgs.gov/")
    else:
        # Save results
        summary_file = OUTPUT_DIR / "optical_scene_discovery_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n   ✅ Summary saved: {summary_file}")
        
        print("\n" + "=" * 80)
        print("NEXT STEPS")
        print("=" * 80)
        print("\n1. Review suitable pairs in: processed_data/velocity_validation/optical/suitable_optical_pairs.csv")
        print("2. Download or access scenes via Google Earth Engine")
        print("3. Run optical_feature_tracking.py to process pairs")
    
    print("\n" + "=" * 80)
    print("✅ DISCOVERY COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
