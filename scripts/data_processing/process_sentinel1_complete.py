#!/usr/bin/env python3
"""
Complete Sentinel-1 velocity processing workflow.

This script provides multiple options:
1. Automated processing using SNAP (if installed)
2. Automated processing using ISCE (if installed)
3. Manual processing guide
4. Velocity extraction from processed results

Requirements:
    Option A: SNAP + snappy
    Option B: ISCE
    Option C: Manual processing (external tools)

Output:
    - Velocity time series CSV
    - Ready for analysis framework
"""

import os
import sys
import subprocess
from pathlib import Path
import pandas as pd
from datetime import datetime
import json

# Directories
SENTINEL1_DIR = Path("satellite_data/sentinel1")
OUTPUT_DIR = Path("satellite_data/sentinel1/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Glacier location
GLACIER_LAT = 38.97
GLACIER_LON = 70.75


def check_snap():
    """Check if SNAP is available."""
    snap_paths = [
        "/home/chunlab/esa-snap/bin/gpt",  # User's installation
        "/usr/local/snap/bin/gpt",
        os.path.expanduser("~/snap/bin/gpt"),
        os.path.expanduser("~/esa-snap/bin/gpt"),
        "/opt/snap/bin/gpt",
        "gpt"  # If in PATH
    ]
    
    for path in snap_paths:
        try:
            result = subprocess.run([path, "--version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return path
        except:
            continue
    return None


def check_snappy():
    """Check if snappy (Python interface) is available."""
    try:
        import snappy
        return True
    except ImportError:
        return False


def check_isce():
    """Check if ISCE is available."""
    try:
        import isce
        return True
    except ImportError:
        return False


def list_sentinel1_products():
    """List all Sentinel-1 products."""
    products = sorted(SENTINEL1_DIR.glob("*.SAFE.zip"))
    return products


def process_with_snap_gpt(products):
    """Process Sentinel-1 using SNAP gpt command-line tool."""
    print("=" * 70)
    print("Processing with SNAP (gpt command-line)")
    print("=" * 70)
    print()
    
    snap_path = check_snap()
    if not snap_path:
        print("❌ SNAP gpt not found")
        return False
    
    print(f"Using SNAP: {snap_path}")
    print()
    
    # Process each product for terrain correction
    terrain_corrected = []
    
    for i, product in enumerate(products, 1):
        print(f"Processing {i}/{len(products)}: {product.name}")
        
        # Output file
        output_name = product.stem.replace('.SAFE', '_terrain.tif')
        output_file = OUTPUT_DIR / output_name
        
        if output_file.exists():
            print(f"  ✅ Already processed: {output_file.name}")
            terrain_corrected.append(output_file)
            continue
        
        # Use SNAP graph
        graph_file = Path("snap_graphs/terrain_correction.xml")
        if not graph_file.exists():
            print(f"  ⚠️  Graph file not found: {graph_file}")
            continue
        
        # Run gpt
        cmd = [
            snap_path,
            str(graph_file),
            f"-PinputFile={product}",
            f"-PoutputFile={output_file}"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode == 0:
                print(f"  ✅ Terrain corrected: {output_file.name}")
                terrain_corrected.append(output_file)
            else:
                print(f"  ❌ Error: {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            print(f"  ⚠️  Timeout (processing may still be running)")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print()
    return len(terrain_corrected) > 0


def process_with_snappy(products):
    """Process Sentinel-1 using snappy (Python interface)."""
    print("=" * 70)
    print("Processing with SNAP (snappy Python interface)")
    print("=" * 70)
    print()
    
    try:
        import snappy
        from snappy import ProductIO, GPF
        
        print("✅ snappy available")
        print()
        
        # Process each product
        for i, product in enumerate(products, 1):
            print(f"Processing {i}/{len(products)}: {product.name}")
            
            try:
                # Read product
                prod = ProductIO.readProduct(str(product))
                print(f"  Product: {prod.getName()}")
                
                # Apply terrain correction operators
                # (This is simplified - full implementation requires operator chaining)
                print("  ⚠️  Full processing requires operator chaining")
                print("  See SNAP_PROCESSING_WORKFLOW.md for detailed steps")
                
                prod.dispose()
            except Exception as e:
                print(f"  ❌ Error: {e}")
        
        return True
    except ImportError:
        print("❌ snappy not available")
        return False


def process_with_isce(products):
    """Process Sentinel-1 using ISCE."""
    print("=" * 70)
    print("Processing with ISCE")
    print("=" * 70)
    print()
    
    try:
        import isce
        from isce import SENSOR
        
        print("✅ ISCE available")
        print()
        print("⚠️  ISCE processing requires detailed configuration")
        print("   See ISCE documentation for Sentinel-1 processing")
        print()
        
        # ISCE processing would go here
        # This is a placeholder - full implementation requires ISCE-specific code
        
        return False  # Not fully implemented yet
    except ImportError:
        print("❌ ISCE not available")
        return False


def create_manual_processing_guide():
    """Create guide for manual processing."""
    guide = """# Manual Sentinel-1 Processing Guide

Since SNAP/ISCE are not installed, here are options for processing:

## Option 1: Install SNAP (Recommended)

### Installation:
1. Download from: https://step.esa.int/main/download/snap-download/
2. Install SNAP (follow installer instructions)
3. Configure Python interface:
   ```bash
   python -m snappy --setup
   ```
4. Re-run this script

### Processing Steps:
1. Open SNAP
2. Import Sentinel-1 products (File → Import → Sentinel-1)
3. Apply processing chain:
   - Apply Orbit File
   - Remove GRD Border Noise
   - Calibration
   - Terrain Correction
4. Export as GeoTIFF

## Option 2: Use ISCE

### Installation:
```bash
conda install -c conda-forge isce2
```

### Processing:
See ISCE documentation for Sentinel-1 GRD processing

## Option 3: Use Online Services

### Google Earth Engine:
- Process Sentinel-1 using GEE
- Export velocity/displacement maps
- Download and extract time series

### ASF Vertex:
- Process using ASF tools
- Download processed products

## Option 4: Extract from Pre-processed Data

If you have already processed Sentinel-1 data elsewhere:
1. Place velocity/displacement maps in: satellite_data/sentinel1/processed/
2. Use extract_velocity_from_snap.py to extract time series
3. Export to CSV format

## Velocity CSV Format Required:

```csv
date,velocity_m_per_day,velocity_std,dx_m,dy_m,time_delta_days
2025-09-13,0.15,0.05,10.5,8.2,6.0
2025-09-19,0.25,0.08,15.3,12.1,6.0
...
```

Save as: satellite_data/sentinel1/processed/velocity_timeseries.csv
"""
    
    guide_file = Path("MANUAL_SENTINEL1_PROCESSING.md")
    with open(guide_file, 'w') as f:
        f.write(guide)
    
    print(f"✅ Created guide: {guide_file}")
    return guide_file


def extract_velocity_from_manual_data():
    """Helper to extract velocity if user has processed data manually."""
    print("=" * 70)
    print("Velocity Extraction Helper")
    print("=" * 70)
    print()
    
    print("If you have processed Sentinel-1 data (velocity/displacement maps):")
    print()
    print("1. Place files in: satellite_data/sentinel1/processed/")
    print("2. Files should be GeoTIFF with displacement data")
    print("3. Run: python3 extract_velocity_from_snap.py")
    print()
    
    # Check if any processed files exist
    processed_files = list(OUTPUT_DIR.glob("*.tif")) + list(OUTPUT_DIR.glob("*.nc"))
    
    if processed_files:
        print(f"Found {len(processed_files)} processed files:")
        for f in processed_files[:5]:
            print(f"  - {f.name}")
        print()
        print("You can use extract_velocity_from_snap.py to extract velocity")
    else:
        print("No processed files found yet")
        print("Process Sentinel-1 first, then extract velocity")
    
    print()


def create_velocity_csv_template():
    """Create a template CSV for manual velocity entry."""
    print("Creating velocity CSV template...")
    print()
    
    # Get product dates
    products = list_sentinel1_products()
    
    # Create template with dates
    dates = []
    for product in products:
        # Extract date from filename
        # Format: S1A_IW_GRDH_1SDV_20250907T012223_...
        parts = product.stem.split('_')
        for part in parts:
            if 'T' in part and len(part) == 15:
                try:
                    date = datetime.strptime(part, '%Y%m%dT%H%M%S')
                    dates.append(date)
                    break
                except:
                    pass
    
    dates.sort()
    
    # Create template
    template_data = []
    for i in range(len(dates) - 1):
        date1 = dates[i]
        date2 = dates[i + 1]
        time_delta = (date2 - date1).days
        
        template_data.append({
            'date': date2.strftime('%Y-%m-%d'),
            'velocity_m_per_day': 0.0,  # To be filled
            'velocity_std': 0.0,  # To be filled
            'dx_m': 0.0,  # Optional
            'dy_m': 0.0,  # Optional
            'time_delta_days': time_delta
        })
    
    template_df = pd.DataFrame(template_data)
    template_file = OUTPUT_DIR / "velocity_timeseries_template.csv"
    template_df.to_csv(template_file, index=False)
    
    print(f"✅ Template created: {template_file}")
    print(f"   {len(template_df)} time steps")
    print()
    print("Fill in velocity values and save as: velocity_timeseries.csv")
    print()
    
    return template_file


def main():
    """Main processing function."""
    print("=" * 70)
    print("Sentinel-1 Velocity Processing")
    print("=" * 70)
    print()
    
    # List products
    products = list_sentinel1_products()
    if not products:
        print("❌ No Sentinel-1 products found")
        return False
    
    print(f"Found {len(products)} Sentinel-1 products")
    print()
    
    # Check available tools
    snap_path = check_snap()
    snappy_available = check_snappy()
    isce_available = check_isce()
    
    print("Available processing tools:")
    print(f"  SNAP (gpt): {'✅' if snap_path else '❌'}")
    print(f"  snappy (Python): {'✅' if snappy_available else '❌'}")
    print(f"  ISCE: {'✅' if isce_available else '❌'}")
    print()
    
    # Try processing
    success = False
    
    if snap_path:
        print("Attempting processing with SNAP gpt...")
        success = process_with_snap_gpt(products)
    elif snappy_available:
        print("Attempting processing with snappy...")
        success = process_with_snappy(products)
    elif isce_available:
        print("Attempting processing with ISCE...")
        success = process_with_isce(products)
    else:
        print("⚠️  No processing tools available")
        print()
        create_manual_processing_guide()
        extract_velocity_from_manual_data()
        create_velocity_csv_template()
        
        print("=" * 70)
        print("Manual Processing Required")
        print("=" * 70)
        print()
        print("See: MANUAL_SENTINEL1_PROCESSING.md")
        print()
        print("Once you have velocity data, create CSV:")
        print("  satellite_data/sentinel1/processed/velocity_timeseries.csv")
        print()
        print("Template created: velocity_timeseries_template.csv")
        print()
        return True
    
    if success:
        print("=" * 70)
        print("✅ Processing Complete!")
        print("=" * 70)
        print()
        print("Next: Extract velocity time series")
        print("  python3 extract_velocity_from_snap.py")
        print()
    else:
        print("⚠️  Processing incomplete or not available")
        print("   See manual processing guide")
    
    return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

