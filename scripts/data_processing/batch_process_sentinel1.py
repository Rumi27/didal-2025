#!/usr/bin/env python3
"""
Batch processing script for Sentinel-1 products using SNAP.

This script provides multiple automation options:
1. Generate SNAP XML graphs for each product
2. Create batch processing instructions
3. Attempt command-line processing (if gpt works)
4. Generate SNAP GUI batch processing workflow
"""

import os
import sys
from pathlib import Path
import subprocess
from datetime import datetime

# Directories
SENTINEL1_DIR = Path("satellite_data/sentinel1")
PROCESSED_DIR = Path("satellite_data/sentinel1/processed")
GRAPHS_DIR = Path("snap_graphs")
GRAPHS_DIR.mkdir(exist_ok=True)

# SNAP paths
SNAP_BIN = Path.home() / "esa-snap" / "bin" / "snap"
GPT_BIN = Path.home() / "esa-snap" / "bin" / "gpt"

def get_unprocessed_products():
    """Get list of products that haven't been processed yet."""
    print("=" * 70)
    print("Finding Unprocessed Products")
    print("=" * 70)
    print()
    
    # Get all input products
    input_files = sorted(SENTINEL1_DIR.glob("*.SAFE.zip"))
    
    # Get already processed products
    processed_files = set()
    for dim_file in PROCESSED_DIR.glob("*_TC_BEAM.dim"):
        # Extract date from filename
        # Format: S1A_IW_GRDH_1SDV_20250907T012223_..._TC_BEAM.dim
        parts = dim_file.stem.split("_")
        for part in parts:
            if "T" in part and len(part) == 15:  # Date format: 20250907T012223
                date_str = part.split("T")[0]
                processed_files.add(date_str)
    
    unprocessed = []
    for input_file in input_files:
        # Extract date from filename
        date_str = None
        for part in input_file.stem.split("_"):
            if "T" in part and len(part) == 15:
                date_str = part.split("T")[0]
                break
        
        if date_str and date_str not in processed_files:
            unprocessed.append(input_file)
    
    print(f"Total products: {len(input_files)}")
    print(f"Already processed: {len(processed_files)}")
    print(f"Remaining to process: {len(unprocessed)}")
    print()
    
    if unprocessed:
        print("Unprocessed products:")
        for f in unprocessed:
            print(f"  - {f.name}")
    else:
        print("✅ All products have been processed!")
    
    print()
    return unprocessed


def create_snap_graph():
    """Create SNAP XML graph for terrain correction."""
    graph_content = """<?xml version="1.0" encoding="UTF-8"?>
<graph id="TerrainCorrection">
  <version>1.0</version>
  <node id="Read">
    <operator>Read</operator>
    <parameters>
      <file>${inputFile}</file>
      <formatName>SENTINEL-1</formatName>
    </parameters>
  </node>
  <node id="Apply-Orbit-File">
    <operator>Apply-Orbit-File</operator>
    <sources>
      <sourceProduct refid="Read"/>
    </sources>
    <parameters>
      <orbitType>Sentinel Precise (Auto Download)</orbitType>
      <polyDegree>3</polyDegree>
      <continueOnFail>false</continueOnFail>
    </parameters>
  </node>
  <node id="Calibration">
    <operator>Calibration</operator>
    <sources>
      <sourceProduct refid="Apply-Orbit-File"/>
    </sources>
    <parameters>
      <selectedPolarisations>VV,VH</selectedPolarisations>
      <outputImageInComplex>false</outputImageInComplex>
      <outputImageScaleInDb>false</outputImageScaleInDb>
      <createGamma0Band>true</createGamma0Band>
      <createBeta0Band>false</createBeta0Band>
    </parameters>
  </node>
  <node id="Terrain-Correction">
    <operator>Terrain-Correction</operator>
    <sources>
      <sourceProduct refid="Calibration"/>
    </sources>
    <parameters>
      <demName>SRTM 1Sec HGT</demName>
      <demResamplingMethod>Bilinear</demResamplingMethod>
      <resampling>Bilinear</resampling>
      <mapProjection>WGS84(DD)</mapProjection>
      <pixelSpacingInMeter>10.0</pixelSpacingInMeter>
      <saveProjectedLocalIncidenceAngle>true</saveProjectedLocalIncidenceAngle>
      <saveSelectedSourceBand>true</saveSelectedSourceBand>
      <outputComplex>false</outputComplex>
      <applyRadiometricNormalization>false</applyRadiometricNormalization>
      <saveSigmaNought>true</saveSigmaNought>
      <saveGammaNought>true</saveGammaNought>
      <saveBetaNought>false</saveBetaNought>
      <incidenceAngleForSigma0>Use projected local incidence angle from DEM</incidenceAngleForSigma0>
      <auxFile>Latest Auxiliary File</auxFile>
    </parameters>
  </node>
  <node id="Write">
    <operator>Write</operator>
    <sources>
      <sourceProduct refid="Terrain-Correction"/>
    </sources>
    <parameters>
      <file>${outputFile}</file>
      <formatName>BEAM-DIMAP</formatName>
    </parameters>
  </node>
</graph>
"""
    
    graph_file = GRAPHS_DIR / "terrain_correction.xml"
    with open(graph_file, 'w') as f:
        f.write(graph_content)
    
    print(f"✅ Created SNAP graph: {graph_file}")
    return graph_file


def create_batch_processing_script(unprocessed_products):
    """Create batch processing script for command-line (if gpt works)."""
    script_file = GRAPHS_DIR / "batch_process.sh"
    
    with open(script_file, 'w') as f:
        f.write("#!/bin/bash\n")
        f.write("# Batch processing script for Sentinel-1 products\n")
        f.write("# Usage: bash batch_process.sh\n\n")
        f.write(f"# SNAP paths\n")
        f.write(f"GPT='{GPT_BIN}'\n")
        f.write(f"GRAPH='{GRAPHS_DIR / 'terrain_correction.xml'}'\n")
        f.write(f"INPUT_DIR='{SENTINEL1_DIR}'\n")
        f.write(f"OUTPUT_DIR='{PROCESSED_DIR}'\n\n")
        f.write("echo 'Starting batch processing...'\n")
        f.write("echo ''\n\n")
        
        for i, product in enumerate(unprocessed_products, 1):
            # Generate output filename
            output_name = product.stem.replace(".SAFE", "_TC_BEAM")
            output_file = PROCESSED_DIR / f"{output_name}.dim"
            
            f.write(f"echo '[{i}/{len(unprocessed_products)}] Processing: {product.name}'\n")
            f.write(f"$GPT $GRAPH \\\n")
            f.write(f"    -PinputFile='{product.absolute()}' \\\n")
            f.write(f"    -PoutputFile='{output_file.absolute()}' \\\n")
            f.write(f"    -q 2\n")
            f.write(f"if [ $? -eq 0 ]; then\n")
            f.write(f"    echo '  ✅ Success'\n")
            f.write(f"else\n")
            f.write(f"    echo '  ❌ Failed'\n")
            f.write(f"fi\n")
            f.write(f"echo ''\n\n")
        
        f.write("echo 'Batch processing complete!'\n")
    
    # Make executable
    os.chmod(script_file, 0o755)
    
    print(f"✅ Created batch script: {script_file}")
    return script_file


def create_gui_batch_instructions(unprocessed_products):
    """Create instructions for SNAP GUI batch processing."""
    instructions_file = Path("SNAP_BATCH_PROCESSING_GUIDE.md")
    
    instructions = f"""# SNAP GUI Batch Processing Guide

## Overview
This guide shows how to process all {len(unprocessed_products)} remaining Sentinel-1 products using SNAP's GUI batch processing feature.

## Method 1: SNAP Batch Processing (Recommended) ⭐

### Step 1: Open SNAP and Create Processing Graph

1. **Open SNAP:**
   ```bash
   ~/esa-snap/bin/snap
   ```

2. **Create a new graph:**
   - Go to: `Tools` → `Graph Builder`
   - Or: `File` → `New` → `Graph`

3. **Build the processing chain:**
   - **Read** → Select "Read" operator
     - Set format: `SENTINEL-1`
   - **Apply-Orbit-File** → Connect to Read
     - Orbit Type: `Sentinel Precise (Auto Download)`
   - **Calibration** → Connect to Apply-Orbit-File
     - Selected Polarizations: `VV, VH`
   - **Terrain-Correction** → Connect to Calibration
     - DEM: `SRTM 1Sec HGT`
     - Pixel Spacing: `10.0` meters
     - Map Projection: `WGS84(DD)`
   - **Write** → Connect to Terrain-Correction
     - Format: `BEAM-DIMAP`

4. **Save the graph:**
   - `File` → `Save Graph As...`
   - Save as: `snap_graphs/terrain_correction.xml`

### Step 2: Batch Process All Products

1. **Open Batch Processing:**
   - Go to: `Tools` → `Batch Processing`
   - Or: `File` → `Batch Processing`

2. **Load your graph:**
   - Click "Load Graph"
   - Select: `snap_graphs/terrain_correction.xml`

3. **Add input files:**
   - Click "Add Files" or "Add Directory"
   - Navigate to: `satellite_data/sentinel1/`
   - Select all `.SAFE.zip` files (or the unprocessed ones)

4. **Set output directory:**
   - Output folder: `satellite_data/sentinel1/processed/`
   - Output naming: Use default or customize

5. **Run batch processing:**
   - Click "Run" or "Execute"
   - Processing will run automatically for all files
   - Monitor progress in the console

### Step 3: Verify Results

After processing, check:
```bash
ls -lh satellite_data/sentinel1/processed/*_TC_BEAM.dim
```

You should have {len(unprocessed_products)} new processed products.

---

## Method 2: Process One-by-One (Current Method)

If batch processing doesn't work, continue processing manually:

### Remaining Products to Process:

"""
    
    for i, product in enumerate(unprocessed_products, 1):
        date_str = None
        for part in product.stem.split("_"):
            if "T" in part and len(part) == 15:
                date_str = part.split("T")[0]
                break
        
        instructions += f"""
#### {i}. {product.name}

**Date:** {date_str if date_str else 'Unknown'}

**Steps:**
1. Open SNAP
2. `File` → `Open Product` → Select: `{product.name}`
3. Apply processing chain:
   - Apply Orbit File
   - Calibration
   - Terrain Correction
4. `File` → `Save Product As...`
   - Format: `BEAM-DIMAP`
   - Save as: `satellite_data/sentinel1/processed/{product.stem.replace('.SAFE', '_TC_BEAM')}.dim`

"""
    
    instructions += """
---

## Method 3: Command-Line (If gpt Works)

If the `gpt` command-line tool works on your system:

```bash
cd snap_graphs
bash batch_process.sh
```

**Note:** The `gpt` tool currently has issues on this system (buffer overflow), so GUI batch processing is recommended.

---

## After Processing

Once all products are processed:

1. **Run offset tracking** between consecutive pairs
2. **Extract velocity time series**
3. **Run change-point detection**
4. **Integrate with climate data**

See `run_complete_analysis.py` for the full workflow.

---

## Troubleshooting

### Batch Processing Not Available
- Use Method 2 (one-by-one processing)
- Or try updating SNAP to the latest version

### Processing Fails
- Check that orbit files can be downloaded
- Verify DEM (SRTM) is accessible
- Check disk space (each product needs ~5-6 GB)

### Output Files Missing
- Check SNAP console for errors
- Verify output directory permissions
- Check if processing completed successfully

---

*Generated: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """*
"""
    
    with open(instructions_file, 'w') as f:
        f.write(instructions)
    
    print(f"✅ Created batch processing guide: {instructions_file}")
    return instructions_file


def attempt_gpt_processing(product, graph_file):
    """Attempt to process a single product using gpt (with workarounds)."""
    output_name = product.stem.replace(".SAFE", "_TC_BEAM")
    output_file = PROCESSED_DIR / f"{output_name}.dim"
    
    # Try with environment variables to avoid buffer overflow
    env = os.environ.copy()
    env['_JAVA_OPTIONS'] = '-Xmx8G -Djava.awt.headless=true'
    
    cmd = [
        str(GPT_BIN),
        str(graph_file),
        f"-PinputFile={product.absolute()}",
        f"-PoutputFile={output_file.absolute()}",
        "-q", "2"  # Quiet mode
    ]
    
    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        if result.returncode == 0:
            return True, "Success"
        else:
            return False, result.stderr
    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)


def main():
    """Main function."""
    print("=" * 70)
    print("Sentinel-1 Batch Processing Automation")
    print("=" * 70)
    print()
    
    # Get unprocessed products
    unprocessed = get_unprocessed_products()
    
    if not unprocessed:
        print("✅ All products are already processed!")
        return True
    
    print()
    print("=" * 70)
    print("Creating Automation Resources")
    print("=" * 70)
    print()
    
    # Create SNAP graph
    graph_file = create_snap_graph()
    
    # Create batch script (for command-line, if it works)
    batch_script = create_batch_processing_script(unprocessed)
    
    # Create GUI batch processing guide
    guide_file = create_gui_batch_instructions(unprocessed)
    
    print()
    print("=" * 70)
    print("✅ Automation Resources Created!")
    print("=" * 70)
    print()
    print("Next Steps:")
    print()
    print("OPTION 1: SNAP GUI Batch Processing (Recommended)")
    print("  1. Open SNAP: ~/esa-snap/bin/snap")
    print("  2. Follow the guide: SNAP_BATCH_PROCESSING_GUIDE.md")
    print("  3. Use Tools → Batch Processing to process all files at once")
    print()
    print("OPTION 2: Command-Line (If gpt works)")
    print(f"  bash {batch_script}")
    print("  (Note: gpt currently has issues on this system)")
    print()
    print("OPTION 3: Continue Manual Processing")
    print("  Process remaining products one-by-one in SNAP GUI")
    print("  See guide for list of remaining products")
    print()
    print(f"📖 Full guide: {guide_file}")
    print()
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

