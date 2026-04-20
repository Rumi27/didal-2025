#!/usr/bin/env python3
"""
Prepare files and instructions for manual SNAP GUI processing.

Since the gpt command-line tool has buffer overflow issues, this script
prepares everything needed for manual processing in SNAP GUI.

Usage:
    python prepare_manual_snap_processing.py
"""

import json
from pathlib import Path
import pandas as pd

# Configuration
SENTINEL1_DIR = Path("satellite_data/sentinel1")
OUTPUT_DIR = Path("processed_data/velocity_validation/same_track")
SAME_TRACK_CSV = Path("processed_data/same_track_pairs_for_reprocessing.csv")

# Same-track pairs
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

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def check_files_exist():
    """Check if all required Sentinel-1 files exist."""
    print("=" * 80)
    print("CHECKING REQUIRED FILES")
    print("=" * 80)
    print()
    
    missing_files = []
    existing_files = []
    
    for pair in SAME_TRACK_PAIRS:
        master_file = SENTINEL1_DIR / pair['master_file']
        slave_file = SENTINEL1_DIR / pair['slave_file']
        
        if master_file.exists():
            existing_files.append(('master', pair['master_file']))
        else:
            missing_files.append(('master', pair['master_file']))
        
        if slave_file.exists():
            existing_files.append(('slave', pair['slave_file']))
        else:
            missing_files.append(('slave', pair['slave_file']))
    
    print(f"✅ Found: {len(existing_files)}/{len(existing_files) + len(missing_files)} files")
    
    if missing_files:
        print(f"\n❌ Missing files ({len(missing_files)}):")
        for file_type, filename in missing_files:
            print(f"   {file_type}: {filename}")
        return False
    else:
        print("\n✅ All required Sentinel-1 files are present!")
        return True


def create_processing_guide():
    """Create a detailed processing guide for manual SNAP GUI processing."""
    guide = f"""# Manual SNAP GUI Processing Guide for Same-Track Validation

## Overview

This guide walks you through processing 8 same-track Sentinel-1 pairs manually in SNAP GUI.
Each pair takes approximately 15-30 minutes to process.

**Total time estimate:** 2-4 hours for all 8 pairs

---

## Prerequisites

- ✅ SNAP installed and accessible
- ✅ All Sentinel-1 SAFE files downloaded
- ✅ Glacier outline shapefile available (for centerline extraction)

---

## Processing Workflow (For Each Pair)

### Step 1: Open SNAP GUI

```bash
/home/chunlab/esa-snap/bin/snap
```

### Step 2: Load Master and Slave Images

1. **File** → **Open Product**
2. Navigate to: `satellite_data/sentinel1/`
3. Select master image (earlier date)
4. Repeat for slave image (later date)
5. Both should appear in Product Explorer

### Step 3: Apply Orbit File (Both Images)

For each image:
1. Select product in Product Explorer
2. **Radar** → **Apply Orbit File**
3. Orbit Type: **Sentinel Precise (Auto Download)**
4. Click **Run**
5. Wait for completion

### Step 4: Radiometric Calibration (Both Images)

For each image:
1. Select product
2. **Radar** → **Radiometric** → **Calibrate**
3. Source Band: **Intensity_VV**
4. Output: **Sigma0**
5. Click **Run**

### Step 5: Terrain Correction (Both Images)

For each image:
1. Select calibrated product
2. **Radar** → **Geometric** → **Terrain Correction** → **Range-Doppler Terrain Correction**
3. Parameters:
   - **DEM:** SRTM 1Sec HGT
   - **Pixel Spacing:** 10 m (both X and Y)
   - **Map Projection:** WGS84 (EPSG:4326)
4. Click **Run**

### Step 6: DEM-Assisted Coregistration

1. Select **both** terrain-corrected products (Ctrl+Click)
2. **Radar** → **Coregistration** → **DEM-Assisted Coregistration**
3. DEM: **SRTM 1Sec HGT**
4. Click **Run**

### Step 7: Create Stack

1. Select both coregistered products
2. **Radar** → **Coregistration** → **Create Stack**
3. Click **Run**

### Step 8: Offset Tracking (CRITICAL STEP)

1. Select stack product
2. **Radar** → **Offset Tracking** → **Cross-Correlation Matcher**
3. **CRITICAL PARAMETERS:**
   - **Search Range X: 400** (or 500 for safety)
   - **Search Range Y: 400** (or 500 for safety)
   - **Window Size X: 128**
   - **Window Size Y: 128**
   - **Grid Spacing X: 40**
   - **Grid Spacing Y: 40**
   - **Correlation Threshold: 0.3**
4. Click **Run**
5. Processing takes 10-20 minutes

### Step 9: Calculate Velocity

The offset tracking produces displacement maps. To calculate velocity:

1. Open the offset tracking result
2. You'll see bands: **X_offset**, **Y_offset**, **correlation**
3. Calculate velocity: Velocity = sqrt(X_offset² + Y_offset²) / time_interval_days
4. Or use: **Radar** → **Offset Tracking** → **Velocity Calculator** (if available)

### Step 10: Extract Centerline Velocity

1. Load glacier outline shapefile (if available)
2. Extract velocity values along centerline
3. Export to CSV

**OR** manually extract:
- Open velocity map
- Use **Raster** → **Extract Values** → **Along Line**
- Draw line along glacier centerline
- Export values to CSV

### Step 11: Save CSV File

Save CSV with format: `track{{orbit}}_{{YYYYMMDD}}_{{YYYYMMDD}}_vel.csv`

**Required columns:**
- `date` (or `midpoint_date`) - Measurement date
- `velocity_m_per_day` (or `velocity`) - Velocity in m/day

**Save location:** `processed_data/velocity_validation/same_track/`

---

## Pairs to Process

"""
    
    for i, pair in enumerate(SAME_TRACK_PAIRS, 1):
        master_file = SENTINEL1_DIR / pair['master_file']
        slave_file = SENTINEL1_DIR / pair['slave_file']
        
        guide += f"""
### Pair {i}: Track {pair['track']}, {pair['master']} → {pair['slave']}

**Master:** `{pair['master_file']}`
- Location: `{master_file.absolute()}`
- ✅ File exists: {master_file.exists()}

**Slave:** `{pair['slave_file']}`
- Location: `{slave_file.absolute()}`
- ✅ File exists: {slave_file.exists()}

**Baseline:** {pair['baseline']} days

**Output CSV:** `track{pair['track']}_{pair['master'].replace('-', '')}_{pair['slave'].replace('-', '')}_vel.csv`

**Expected midpoint date:** {(pd.to_datetime(pair['master']) + pd.Timedelta(days=pair['baseline']/2)).strftime('%Y-%m-%d')}

---

"""
    
    guide += """
## Validation Checklist (After Each Pair)

Before moving to the next pair, verify:

- [ ] Correlation ≥ 0.1 in peak velocity area
- [ ] Velocity NOT at search boundary (±400 pixels)
- [ ] Velocity map covers glacier area
- [ ] Centerline velocity extracted
- [ ] CSV file saved with correct filename
- [ ] CSV contains required columns (`date`, `velocity_m_per_day`)

---

## After All Pairs Processed

1. **Verify all files exist:**
   ```bash
   ls processed_data/velocity_validation/same_track/*.csv
   ```
   Should show 8 files.

2. **Run validation script:**
   ```bash
   python organized/scripts/validation/process_same_track_validation.py
   ```

3. **Check results:**
   - Review: `processed_data/velocity_validation/same_track_cross_track_comparison.csv`
   - Review: `processed_data/velocity_validation/same_track_validation_summary.json`
   - Check if bias exceeds 10% threshold

---

## Troubleshooting

### Low Correlation (< 0.1)
- Increase search range to 500 pixels
- Check if images are properly coregistered
- Verify DEM quality

### Velocity at Boundary
- Increase search range to 500-600 pixels
- True velocity may exceed 800 m/day

### Processing Errors
- Ensure sufficient disk space (each pair ~500 MB)
- Check SNAP version compatibility
- Verify SAFE files are not corrupted

### CSV Format Issues
- Ensure column names match: `date` and `velocity_m_per_day`
- Check that dates are in YYYY-MM-DD format
- Verify velocities are in m/day (not m/year)

---

## Notes

- **Do NOT mix tracks** - Process Track 78 and Track 173 separately
- **Save frequently** - SNAP processing can be time-consuming
- **Validate each pair** - Don't proceed until current pair is validated
- **Document issues** - Note any pairs that fail validation

---

**Status:** Ready to begin processing. Start with Pair 1 (Track 78, 2025-09-07 → 2025-09-19).

**See also:** `SNAP_PROCESSING_CHECKLIST.md` for a quick checklist version.
"""
    
    guide_file = Path("MANUAL_SNAP_PROCESSING_GUIDE.md")
    with open(guide_file, 'w') as f:
        f.write(guide)
    
    print(f"✅ Created processing guide: {guide_file}")
    return guide_file


def create_quick_reference():
    """Create a quick reference card for processing."""
    ref = """# Quick Reference: SNAP Processing Steps

## For Each Pair:

1. **Open SNAP** → Load master & slave SAFE files
2. **Apply Orbit File** → Both (Sentinel Precise)
3. **Calibrate** → Both (Sigma0, VV)
4. **Terrain Correction** → Both (SRTM, 10m, WGS84)
5. **DEM-Assisted Coregistration** → Both together
6. **Create Stack** → Both together
7. **Offset Tracking** → Search Range: **400 pixels** ⚠️
8. **Extract Centerline** → Velocity along glacier
9. **Save CSV** → `track{orbit}_YYYYMMDD_YYYYMMDD_vel.csv`

## Critical Parameter:
**Search Range = 400 pixels** (or 500 for safety)

## Output Location:
`processed_data/velocity_validation/same_track/`

## After All 8 Pairs:
```bash
python organized/scripts/validation/process_same_track_validation.py
```
"""
    
    ref_file = Path("SNAP_QUICK_REFERENCE.md")
    with open(ref_file, 'w') as f:
        f.write(ref)
    
    print(f"✅ Created quick reference: {ref_file}")
    return ref_file


def main():
    """Main function."""
    print("=" * 80)
    print("PREPARING MANUAL SNAP PROCESSING")
    print("=" * 80)
    print()
    
    # Check files
    files_ok = check_files_exist()
    
    print()
    
    # Create guides
    print("=" * 80)
    print("CREATING PROCESSING GUIDES")
    print("=" * 80)
    print()
    
    guide_file = create_processing_guide()
    ref_file = create_quick_reference()
    
    print()
    print("=" * 80)
    print("✅ PREPARATION COMPLETE")
    print("=" * 80)
    print()
    
    if files_ok:
        print("✅ All required files are present!")
        print()
        print("Next steps:")
        print("  1. Open SNAP GUI: /home/chunlab/esa-snap/bin/snap")
        print("  2. Follow the guide: MANUAL_SNAP_PROCESSING_GUIDE.md")
        print("  3. Process all 8 pairs (2-4 hours)")
        print("  4. Run validation script when complete")
    else:
        print("⚠️  Some files are missing - check the list above")
        print("   Download missing files before processing")
    
    print()
    print(f"📖 Full guide: {guide_file}")
    print(f"📋 Quick reference: {ref_file}")
    print()


if __name__ == "__main__":
    main()
