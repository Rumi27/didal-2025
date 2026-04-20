#!/usr/bin/env python3
"""
Automated SNAP processing for same-track Sentinel-1 pairs with 32px windows.

This script automates the processing of 8 same-track pairs using SNAP's
command-line tool (gpt) with REDUCED WINDOW SIZE (32px vs 128px) to test
whether same-track failure is due to valley-wall locking vs decorrelation.

Key Differences from Original:
    - Window size: 32px × 32px (320 m) vs 128px × 128px (1,280 m)
    - Footprint: Comparable to glacier width (~330 m) vs 3.9× wider
    - Expected: Reduced valley-wall locking, but potentially lower SNR

Requirements:
    - SNAP installed with gpt command-line tool
    - Sentinel-1 SAFE files in satellite_data/sentinel1/
    - Glacier outline shapefile for centerline extraction

Usage:
    python automated_same_track_32px.py
"""

import subprocess
import os
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime
import json
import xml.etree.ElementTree as ET

# Configuration
SENTINEL1_DIR = Path("satellite_data/sentinel1")
OUTPUT_DIR = Path("processed_data/velocity_validation/same_track_32px")
GRAPHS_DIR = Path("snap_graphs_32px")
VALIDATION_DIR = Path("processed_data/velocity_validation")

# SNAP paths
GPT_BIN = Path("/home/chunlab/esa-snap/bin/gpt")

# Same-track pairs (from identify_same_track_pairs.py)
SAME_TRACK_PAIRS = [
    # Track 78
    {'track': 78, 'master': '2025-09-07', 'slave': '2025-09-19', 'baseline': 12,
     'master_file': 'S1A_IW_GRDH_1SDV_20250907T012223_20250907T012248_060875_0794A5_8F34.SAFE.zip',
     'slave_file': 'S1A_IW_GRDH_1SDV_20250919T012223_20250919T012248_061050_079BAB_5D90.SAFE.zip'},
    {'track': 78, 'master': '2025-09-19', 'slave': '2025-10-01', 'baseline': 12,
     'master_file': 'S1A_IW_GRDH_1SDV_20250919T012223_20250919T012248_061050_079BAB_5D90.SAFE.zip',
     'slave_file': 'S1A_IW_GRDH_1SDV_20251001T012223_20251001T012248_061225_07A2BD_C76D.SAFE.zip'},
    {'track': 78, 'master': '2025-10-01', 'slave': '2025-10-13', 'baseline': 12,
     'master_file': 'S1A_IW_GRDH_1SDV_20251001T012223_20251001T012248_061225_07A2BD_C76D.SAFE.zip',
     'slave_file': 'S1A_IW_GRDH_1SDV_20251013T012224_20251013T012249_061400_07A9C6_4096.SAFE.zip'},
    {'track': 78, 'master': '2025-10-13', 'slave': '2025-10-25', 'baseline': 11,
     'master_file': 'S1A_IW_GRDH_1SDV_20251013T012224_20251013T012249_061400_07A9C6_4096.SAFE.zip',
     'slave_file': 'S1A_IW_GRDH_1SDV_20251025T012223_20251025T012248_061575_07B0CC_8450.SAFE.zip'},
    # Track 173
    {'track': 173, 'master': '2025-09-13', 'slave': '2025-09-25', 'baseline': 12,
     'master_file': 'S1A_IW_GRDH_1SDV_20250913T131433_20250913T131458_060970_07986E_CBBA.SAFE.zip',
     'slave_file': 'S1A_IW_GRDH_1SDV_20250925T131433_20250925T131458_061145_079F75_FCC5.SAFE.zip'},
    {'track': 173, 'master': '2025-09-25', 'slave': '2025-10-07', 'baseline': 12,
     'master_file': 'S1A_IW_GRDH_1SDV_20250925T131433_20250925T131458_061145_079F75_FCC5.SAFE.zip',
     'slave_file': 'S1A_IW_GRDH_1SDV_20251007T131434_20251007T131459_061320_07A682_9F71.SAFE.zip'},
    {'track': 173, 'master': '2025-10-07', 'slave': '2025-10-19', 'baseline': 12,
     'master_file': 'S1A_IW_GRDH_1SDV_20251007T131434_20251007T131459_061320_07A682_9F71.SAFE.zip',
     'slave_file': 'S1A_IW_GRDH_1SDV_20251019T131434_20251019T131459_061495_07AD88_A4B7.SAFE.zip'},
    {'track': 173, 'master': '2025-10-19', 'slave': '2025-10-31', 'baseline': 12,
     'master_file': 'S1A_IW_GRDH_1SDV_20251019T131434_20251019T131459_061495_07AD88_A4B7.SAFE.zip',
     'slave_file': 'S1A_IW_GRDH_1SDV_20251031T131433_20251031T131458_061670_07B496_0461.SAFE.zip'},
]

# Create directories
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
GRAPHS_DIR.mkdir(exist_ok=True)
VALIDATION_DIR.mkdir(parents=True, exist_ok=True)


def check_gpt_available():
    """Check if gpt command-line tool is available."""
    if not GPT_BIN.exists():
        print(f"❌ SNAP gpt not found at: {GPT_BIN}")
        print("   Please check SNAP installation")
        return False
    
    # Note: gpt may have buffer overflow issues, but it still works for processing
    # We'll check if the file exists and is executable
    if os.access(GPT_BIN, os.X_OK):
        print(f"✅ SNAP gpt found: {GPT_BIN}")
        print(f"   Note: gpt may show buffer overflow warnings but should still work")
        return True
    else:
        print(f"❌ SNAP gpt not executable: {GPT_BIN}")
        return False


def create_offset_tracking_graph(pair_info):
    """Create SNAP XML graph for offset tracking with 32px windows and 400-pixel search range."""
    graph_id = f"offset_tracking_32px_track{pair_info['track']}_{pair_info['master'].replace('-', '')}_{pair_info['slave'].replace('-', '')}"
    
    # Create XML graph
    graph = ET.Element('graph', id=graph_id)
    ET.SubElement(graph, 'version').text = '1.0'
    
    # Read Master
    read_master = ET.SubElement(graph, 'node', id='Read-Master')
    ET.SubElement(read_master, 'operator').text = 'Read'
    master_params = ET.SubElement(read_master, 'parameters')
    ET.SubElement(master_params, 'file').text = '${masterFile}'
    ET.SubElement(master_params, 'formatName').text = 'SENTINEL-1'
    
    # Read Slave
    read_slave = ET.SubElement(graph, 'node', id='Read-Slave')
    ET.SubElement(read_slave, 'operator').text = 'Read'
    slave_params = ET.SubElement(read_slave, 'parameters')
    ET.SubElement(slave_params, 'file').text = '${slaveFile}'
    ET.SubElement(slave_params, 'formatName').text = 'SENTINEL-1'
    
    # Apply Orbit File - Master
    orbit_master = ET.SubElement(graph, 'node', id='Apply-Orbit-File-Master')
    ET.SubElement(orbit_master, 'operator').text = 'Apply-Orbit-File'
    ET.SubElement(orbit_master, 'sources').append(ET.Element('sourceProduct', refid='Read-Master'))
    orbit_master_params = ET.SubElement(orbit_master, 'parameters')
    ET.SubElement(orbit_master_params, 'orbitType').text = 'Sentinel Precise (Auto Download)'
    
    # Apply Orbit File - Slave
    orbit_slave = ET.SubElement(graph, 'node', id='Apply-Orbit-File-Slave')
    ET.SubElement(orbit_slave, 'operator').text = 'Apply-Orbit-File'
    ET.SubElement(orbit_slave, 'sources').append(ET.Element('sourceProduct', refid='Read-Slave'))
    orbit_slave_params = ET.SubElement(orbit_slave, 'parameters')
    ET.SubElement(orbit_slave_params, 'orbitType').text = 'Sentinel Precise (Auto Download)'
    
    # Calibration - Master
    cal_master = ET.SubElement(graph, 'node', id='Calibration-Master')
    ET.SubElement(cal_master, 'operator').text = 'Calibration'
    ET.SubElement(cal_master, 'sources').append(ET.Element('sourceProduct', refid='Apply-Orbit-File-Master'))
    cal_master_params = ET.SubElement(cal_master, 'parameters')
    ET.SubElement(cal_master_params, 'selectedPolarisations').text = 'VV'
    ET.SubElement(cal_master_params, 'outputImageInComplex').text = 'false'
    
    # Calibration - Slave
    cal_slave = ET.SubElement(graph, 'node', id='Calibration-Slave')
    ET.SubElement(cal_slave, 'operator').text = 'Calibration'
    ET.SubElement(cal_slave, 'sources').append(ET.Element('sourceProduct', refid='Apply-Orbit-File-Slave'))
    cal_slave_params = ET.SubElement(cal_slave, 'parameters')
    ET.SubElement(cal_slave_params, 'selectedPolarisations').text = 'VV'
    ET.SubElement(cal_slave_params, 'outputImageInComplex').text = 'false'
    
    # Terrain Correction - Master
    tc_master = ET.SubElement(graph, 'node', id='Terrain-Correction-Master')
    ET.SubElement(tc_master, 'operator').text = 'Terrain-Correction'
    ET.SubElement(tc_master, 'sources').append(ET.Element('sourceProduct', refid='Calibration-Master'))
    tc_master_params = ET.SubElement(tc_master, 'parameters')
    ET.SubElement(tc_master_params, 'demName').text = 'SRTM 1Sec HGT'
    ET.SubElement(tc_master_params, 'pixelSpacingInMeter').text = '10.0'
    ET.SubElement(tc_master_params, 'mapProjection').text = 'WGS84(DD)'
    
    # Terrain Correction - Slave
    tc_slave = ET.SubElement(graph, 'node', id='Terrain-Correction-Slave')
    ET.SubElement(tc_slave, 'operator').text = 'Terrain-Correction'
    ET.SubElement(tc_slave, 'sources').append(ET.Element('sourceProduct', refid='Calibration-Slave'))
    tc_slave_params = ET.SubElement(tc_slave, 'parameters')
    ET.SubElement(tc_slave_params, 'demName').text = 'SRTM 1Sec HGT'
    ET.SubElement(tc_slave_params, 'pixelSpacingInMeter').text = '10.0'
    ET.SubElement(tc_slave_params, 'mapProjection').text = 'WGS84(DD)'
    
    # DEM-Assisted Coregistration
    coreg = ET.SubElement(graph, 'node', id='DEM-Assisted-Coregistration')
    ET.SubElement(coreg, 'operator').text = 'DEM-Assisted-Coregistration'
    coreg_sources = ET.SubElement(coreg, 'sources')
    ET.SubElement(coreg_sources, 'sourceProduct', refid='Terrain-Correction-Master')
    ET.SubElement(coreg_sources, 'sourceProduct', refid='Terrain-Correction-Slave')
    coreg_params = ET.SubElement(coreg, 'parameters')
    ET.SubElement(coreg_params, 'demName').text = 'SRTM 1Sec HGT'
    
    # Create Stack
    stack = ET.SubElement(graph, 'node', id='Create-Stack')
    ET.SubElement(stack, 'operator').text = 'CreateStack'
    stack_sources = ET.SubElement(stack, 'sources')
    ET.SubElement(stack_sources, 'sourceProduct', refid='DEM-Assisted-Coregistration')
    stack_params = ET.SubElement(stack, 'parameters')
    ET.SubElement(stack_params, 'extent').text = 'Master'
    
    # Offset Tracking (CRITICAL: 32px window size to reduce valley-wall locking)
    offset = ET.SubElement(graph, 'node', id='Offset-Tracking')
    ET.SubElement(offset, 'operator').text = 'Cross-Correlation-Matcher'
    ET.SubElement(offset, 'sources').append(ET.Element('sourceProduct', refid='Create-Stack'))
    offset_params = ET.SubElement(offset, 'parameters')
    ET.SubElement(offset_params, 'windowSizeX').text = '32'  # CHANGED: 32px vs 128px
    ET.SubElement(offset_params, 'windowSizeY').text = '32'  # CHANGED: 32px vs 128px
    ET.SubElement(offset_params, 'searchWindowSizeX').text = '400'  # CRITICAL: 400 pixels
    ET.SubElement(offset_params, 'searchWindowSizeY').text = '400'  # CRITICAL: 400 pixels
    ET.SubElement(offset_params, 'gridSpacingX').text = '40'
    ET.SubElement(offset_params, 'gridSpacingY').text = '40'
    ET.SubElement(offset_params, 'correlationThreshold').text = '0.3'
    
    # Write
    write = ET.SubElement(graph, 'node', id='Write')
    ET.SubElement(write, 'operator').text = 'Write'
    ET.SubElement(write, 'sources').append(ET.Element('sourceProduct', refid='Offset-Tracking'))
    write_params = ET.SubElement(write, 'parameters')
    ET.SubElement(write_params, 'file').text = '${outputFile}'
    ET.SubElement(write_params, 'formatName').text = 'BEAM-DIMAP'
    
    # Save graph
    graph_file = GRAPHS_DIR / f"{graph_id}.xml"
    tree = ET.ElementTree(graph)
    ET.indent(tree, space="  ")
    tree.write(graph_file, encoding='utf-8', xml_declaration=True)
    
    return graph_file


def process_pair(pair_info, graph_file):
    """Process a single same-track pair using gpt."""
    print(f"\n{'='*80}")
    print(f"Processing Pair: Track {pair_info['track']}, {pair_info['master']} → {pair_info['slave']}")
    print(f"{'='*80}")
    
    # Find input files
    master_file = SENTINEL1_DIR / pair_info['master_file']
    slave_file = SENTINEL1_DIR / pair_info['slave_file']
    
    if not master_file.exists():
        print(f"❌ Master file not found: {master_file}")
        return False
    
    if not slave_file.exists():
        print(f"❌ Slave file not found: {slave_file}")
        return False
    
    # Output file
    output_name = f"track{pair_info['track']}_{pair_info['master'].replace('-', '')}_{pair_info['slave'].replace('-', '')}"
    output_file = OUTPUT_DIR / f"{output_name}.dim"
    
    print(f"Master: {master_file.name}")
    print(f"Slave: {slave_file.name}")
    print(f"Output: {output_file.name}")
    print(f"Graph: {graph_file.name}")
    
    # Run gpt
    cmd = [
        str(GPT_BIN),
        str(graph_file),
        f"-PmasterFile={master_file.absolute()}",
        f"-PslaveFile={slave_file.absolute()}",
        f"-PoutputFile={output_file.absolute()}",
        "-q", "2"  # Quiet mode
    ]
    
    print(f"\nRunning: {' '.join(cmd)}")
    print("This may take 15-30 minutes per pair...")
    
    try:
        env = os.environ.copy()
        env['_JAVA_OPTIONS'] = '-Xmx8G -Djava.awt.headless=true'
        
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        if result.returncode == 0:
            print(f"✅ Processing complete: {output_file.name}")
            return True
        else:
            print(f"❌ Processing failed:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ Processing timed out (>1 hour)")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def extract_velocity_from_result(pair_info, output_file):
    """Extract velocity from SNAP output and save as CSV."""
    # This is a simplified version - in practice, you'd need to:
    # 1. Read the DIM file or exported GeoTIFF
    # 2. Extract displacement maps (dx, dy)
    # 3. Calculate velocity along centerline
    # 4. Save as CSV
    
    # For now, create a placeholder CSV structure
    midpoint_date = datetime.strptime(pair_info['master'], '%Y-%m-%d') + \
                   pd.Timedelta(days=pair_info['baseline']/2)
    
    csv_file = OUTPUT_DIR / f"track{pair_info['track']}_{pair_info['master'].replace('-', '')}_{pair_info['slave'].replace('-', '')}_vel.csv"
    
    # Placeholder - actual extraction would read from DIM/GeoTIFF
    df = pd.DataFrame({
        'date': [midpoint_date.strftime('%Y-%m-%d')],
        'velocity_m_per_day': [0.0],  # To be filled from actual processing
        'velocity_std': [0.0],
        'dx_m': [0.0],
        'dy_m': [0.0],
        'time_delta_days': [pair_info['baseline']]
    })
    
    df.to_csv(csv_file, index=False)
    print(f"   ⚠️  Placeholder CSV created: {csv_file.name}")
    print(f"   Note: Actual velocity extraction requires reading DIM/GeoTIFF files")
    
    return csv_file


def main():
    """Main processing function."""
    print("=" * 80)
    print("AUTOMATED SAME-TRACK PROCESSING")
    print("=" * 80)
    print()
    
    # Check gpt availability
    if not check_gpt_available():
        print("\n❌ Cannot proceed without gpt command-line tool")
        print("   Please use manual GUI method (see SNAP_PROCESSING_CHECKLIST.md)")
        return False
    
    print(f"\nProcessing {len(SAME_TRACK_PAIRS)} same-track pairs")
    print(f"Output directory: {OUTPUT_DIR}")
    print()
    
    # Process each pair
    results = []
    for i, pair in enumerate(SAME_TRACK_PAIRS, 1):
        print(f"\n[{i}/{len(SAME_TRACK_PAIRS)}] ", end="")
        
        # Create graph
        graph_file = create_offset_tracking_graph(pair)
        print(f"✅ Graph created: {graph_file.name}")
        
        # Process pair
        success = process_pair(pair, graph_file)
        
        if success:
            # Extract velocity (placeholder for now)
            csv_file = extract_velocity_from_result(pair, OUTPUT_DIR / f"track{pair['track']}_{pair['master'].replace('-', '')}_{pair['slave'].replace('-', '')}.dim")
            results.append({'pair': i, 'success': True, 'csv': csv_file})
        else:
            results.append({'pair': i, 'success': False})
    
    # Summary
    print("\n" + "=" * 80)
    print("PROCESSING SUMMARY")
    print("=" * 80)
    
    successful = sum(1 for r in results if r.get('success', False))
    print(f"Successfully processed: {successful}/{len(SAME_TRACK_PAIRS)}")
    
    if successful == len(SAME_TRACK_PAIRS):
        print("\n✅ All pairs processed!")
        print("\nNext steps:")
        print("  1. Extract velocities from DIM files (manual step or use extract_velocity_from_snap.py)")
        print("  2. Run validation:")
        print("     python organized/scripts/validation/process_same_track_validation.py")
    else:
        print(f"\n⚠️  {len(SAME_TRACK_PAIRS) - successful} pairs failed")
        print("   Check error messages above")
        print("   You may need to process failed pairs manually")
    
    return successful == len(SAME_TRACK_PAIRS)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
