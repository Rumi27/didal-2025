#!/usr/bin/env python3
"""
Process Sentinel-1 data using SNAP (ESA Sentinel Application Platform).

This script provides:
1. Instructions for SNAP installation
2. Batch processing workflow
3. Velocity extraction from offset tracking results
4. Export to CSV format for analysis framework

Requirements:
    - SNAP installed (https://step.esa.int/main/download/snap-download/)
    - snappy configured (python -m snappy --setup)
    OR
    - ISCE installed (conda install -c conda-forge isce2)
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

# Glacier location for velocity extraction
GLACIER_LAT = 38.97
GLACIER_LON = 70.75


def check_snap_installation():
    """Check if SNAP is installed and accessible."""
    print("=" * 70)
    print("Checking SNAP Installation")
    print("=" * 70)
    print()
    
    # Check for gpt command
    snap_paths = [
        "/usr/local/snap/bin/gpt",
        os.path.expanduser("~/snap/bin/gpt"),
        "/opt/snap/bin/gpt",
        "gpt"  # In PATH
    ]
    
    for path in snap_paths:
        try:
            result = subprocess.run([path, "--version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"✅ SNAP found at: {path}")
                print(f"   Version: {result.stdout.strip()}")
                return path
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    
    print("❌ SNAP not found")
    print()
    print("Installation required:")
    print("  1. Download from: https://step.esa.int/main/download/snap-download/")
    print("  2. Install SNAP")
    print("  3. Configure snappy: python -m snappy --setup")
    print()
    return None


def list_sentinel1_products():
    """List available Sentinel-1 products."""
    print("=" * 70)
    print("Finding Sentinel-1 Products")
    print("=" * 70)
    print()
    
    products = sorted(SENTINEL1_DIR.glob("*.SAFE.zip"))
    
    if not products:
        print(f"❌ No Sentinel-1 products found in {SENTINEL1_DIR}")
        return []
    
    print(f"Found {len(products)} Sentinel-1 products:")
    for i, p in enumerate(products, 1):
        print(f"  {i}. {p.name}")
    print()
    
    return products


def create_processing_workflow():
    """Create processing workflow guide."""
    workflow = """# SNAP Processing Workflow for Sentinel-1 Velocity

## Step 1: Terrain Correction (for each product)

For each Sentinel-1 product, apply terrain correction:

```bash
gpt snap_graphs/terrain_correction.xml \\
    -PinputFile=satellite_data/sentinel1/PRODUCT_NAME.SAFE.zip \\
    -PoutputFile=satellite_data/sentinel1/processed/PRODUCT_NAME_terrain.tif
```

Or use SNAP GUI:
1. Open SNAP
2. File → Import → Sentinel-1
3. Apply operators: Apply Orbit File → Remove GRD Border Noise → Calibration → Terrain Correction
4. Export as GeoTIFF

## Step 2: Offset Tracking (for each pair)

For consecutive products, perform offset tracking:

```bash
gpt snap_graphs/offset_tracking.xml \\
    -PmasterFile=satellite_data/sentinel1/processed/MASTER_terrain.tif \\
    -PslaveFile=satellite_data/sentinel1/processed/SLAVE_terrain.tif \\
    -PoutputFile=satellite_data/sentinel1/processed/offset_MASTER_SLAVE.tif
```

Or use SNAP GUI:
1. Open both terrain-corrected products
2. Radar → Offset Tracking
3. Set parameters:
   - Window size: 64 pixels
   - Search window: 128 pixels
   - Skip factor: 2
4. Export displacement maps

## Step 3: Extract Velocity Time Series

After processing all pairs, extract velocity at glacier location.

The offset tracking produces:
- East-West displacement (dx)
- North-South displacement (dy)

Velocity = sqrt(dx² + dy²) / time_delta

## Step 4: Export to CSV

Create CSV file: satellite_data/sentinel1/processed/velocity_timeseries.csv

Format:
```csv
date,velocity_m_per_day,velocity_std,dx_m,dy_m,time_delta_days
2025-09-13,0.15,0.05,10.5,8.2,6.0
2025-09-19,0.25,0.08,15.3,12.1,6.0
...
```

## Alternative: Using ISCE

If using ISCE instead of SNAP:

```python
from isce import SENSOR
from isce import TerrainCorrectedProduct
from isce import OffsetTracking

# Process each product
# ... (see ISCE documentation)

# Extract velocity
# ... (see ISCE documentation)
```
"""
    
    workflow_file = Path("SNAP_PROCESSING_WORKFLOW.md")
    with open(workflow_file, 'w') as f:
        f.write(workflow)
    
    print(f"✅ Created workflow guide: {workflow_file}")
    return workflow_file


def create_velocity_extraction_template():
    """Create template script for extracting velocity from SNAP results."""
    template = """#!/usr/bin/env python3
\"\"\"
Extract velocity time series from SNAP offset tracking results.

This script reads displacement maps from SNAP and extracts velocity
at the glacier location.

Place this script in your project directory and modify as needed.
\"\"\"

import rasterio
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import json

# Glacier location
GLACIER_LAT = 38.97
GLACIER_LON = 70.75

# Input: Displacement maps from SNAP
DISPLACEMENT_DIR = Path("satellite_data/sentinel1/processed/displacements")
OUTPUT_CSV = Path("satellite_data/sentinel1/processed/velocity_timeseries.csv")

def extract_velocity_from_displacement(displacement_file, date1, date2):
    \"\"\"Extract velocity from displacement map.\"\"\"
    with rasterio.open(displacement_file) as src:
        # Get pixel coordinates for glacier location
        row, col = src.index(GLACIER_LON, GLACIER_LAT)
        
        # Read displacement bands (dx, dy)
        dx = src.read(1)  # East-West displacement (pixels)
        dy = src.read(2)  # North-South displacement (pixels)
        
        # Get pixel size
        pixel_size = abs(src.transform[0])  # meters
        
        # Convert to meters
        dx_m = dx[row, col] * pixel_size
        dy_m = dy[row, col] * pixel_size
        
        # Calculate velocity
        time_delta = (date2 - date1).days
        velocity = np.sqrt(dx_m**2 + dy_m**2) / time_delta
        
        # Calculate uncertainty (simplified)
        # In practice, use correlation or other metrics from SNAP
        velocity_std = velocity * 0.1  # 10% uncertainty (adjust based on your data)
        
        return {
            'date': date2,
            'velocity_m_per_day': velocity,
            'velocity_std': velocity_std,
            'dx_m': dx_m,
            'dy_m': dy_m,
            'time_delta_days': time_delta
        }

# Example usage:
# results = []
# for pair in displacement_pairs:
#     result = extract_velocity_from_displacement(...)
#     results.append(result)
# 
# df = pd.DataFrame(results)
# df.to_csv(OUTPUT_CSV, index=False)
"""
    
    template_file = Path("extract_velocity_from_snap.py")
    with open(template_file, 'w') as f:
        f.write(template)
    
    print(f"✅ Created extraction template: {template_file}")
    return template_file


def main():
    """Main function."""
    print("=" * 70)
    print("SNAP/ISCE Processing Setup for Sentinel-1")
    print("=" * 70)
    print()
    
    # Check SNAP
    snap_path = check_snap_installation()
    
    # List products
    products = list_sentinel1_products()
    
    if not products:
        return False
    
    # Create workflow guide
    workflow_file = create_processing_workflow()
    
    # Create extraction template
    template_file = create_velocity_extraction_template()
    
    print()
    print("=" * 70)
    print("✅ Setup Complete!")
    print("=" * 70)
    print()
    
    if snap_path:
        print("SNAP is installed and ready!")
        print()
        print("Next steps:")
        print("  1. Process products using SNAP (see workflow guide)")
        print("  2. Extract velocity using template script")
        print("  3. Run analysis scripts")
    else:
        print("SNAP not found - installation required")
        print()
        print("Options:")
        print("  A. Install SNAP (see instructions above)")
        print("  B. Use ISCE instead (conda install -c conda-forge isce2)")
        print()
        print("See workflow guide for detailed instructions")
    
    print()
    print(f"Workflow guide: {workflow_file}")
    print(f"Extraction template: {template_file}")
    print()
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

