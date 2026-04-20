# SNAP Re-processing Instructions for Phase 1

## Overview

This document provides step-by-step instructions for re-processing 8 same-track Sentinel-1 pairs in SNAP with enlarged search range (400+ pixels).

**Critical Parameter:** Search Range = 400 pixels (or 500 for safety margin)  
**Target:** Max Velocity >800 m/d

---

## Pairs to Process

### Track 78 (4 pairs)

1. **2025-09-07 → 2025-09-19** (12 days)
   - Master: `S1A_IW_GRDH_1SDV_20250907T012223_20250907T012248_060875_0794A5_8F34.SAFE`
   - Slave: `S1A_IW_GRDH_1SDV_20250919T012223_20250919T012248_061050_079BAB_5D90.SAFE`

2. **2025-09-19 → 2025-10-01** (12 days)
   - Master: `S1A_IW_GRDH_1SDV_20250919T012223_20250919T012248_061050_079BAB_5D90.SAFE`
   - Slave: `S1A_IW_GRDH_1SDV_20251001T012223_20251001T012248_061225_07A2BD_C76D.SAFE`

3. **2025-10-01 → 2025-10-13** (12 days)
   - Master: `S1A_IW_GRDH_1SDV_20251001T012223_20251001T012248_061225_07A2BD_C76D.SAFE`
   - Slave: `S1A_IW_GRDH_1SDV_20251013T012224_20251013T012249_061400_07A9C6_4096.SAFE`

4. **2025-10-13 → 2025-10-25** (11 days)
   - Master: `S1A_IW_GRDH_1SDV_20251013T012224_20251013T012249_061400_07A9C6_4096.SAFE`
   - Slave: `S1A_IW_GRDH_1SDV_20251025T012223_20251025T012248_061575_07B0CC_8450.SAFE`

### Track 173 (4 pairs)

5. **2025-09-13 → 2025-09-25** (12 days)
   - Master: `S1A_IW_GRDH_1SDV_20250913T131433_20250913T131458_060970_07986E_CBBA.SAFE`
   - Slave: `S1A_IW_GRDH_1SDV_20250925T131433_20250925T131458_061145_079F75_FCC5.SAFE`

6. **2025-09-25 → 2025-10-07** (12 days)
   - Master: `S1A_IW_GRDH_1SDV_20250925T131433_20250925T131458_061145_079F75_FCC5.SAFE`
   - Slave: `S1A_IW_GRDH_1SDV_20251007T131434_20251007T131459_061320_07A682_9F71.SAFE`

7. **2025-10-07 → 2025-10-19** (12 days)
   - Master: `S1A_IW_GRDH_1SDV_20251007T131434_20251007T131459_061320_07A682_9F71.SAFE`
   - Slave: `S1A_IW_GRDH_1SDV_20251019T131434_20251019T131459_061495_07AD88_A4B7.SAFE`

8. **2025-10-19 → 2025-10-31** (11 days)
   - Master: `S1A_IW_GRDH_1SDV_20251019T131434_20251019T131459_061495_07AD88_A4B7.SAFE`
   - Slave: `S1A_IW_GRDH_1SDV_20251031T131433_20251031T131458_061670_07B496_0461.SAFE`

---

## Step-by-Step Processing (For Each Pair)

### 1. Open SNAP

- Launch SNAP application
- File → Open Product → Navigate to SAFE file location

### 2. Load Master and Slave Images

- Load master image (earlier date)
- Load slave image (later date)
- Both should appear in Product Explorer

### 3. Apply Orbit File

- Select master product → Radar → Apply Orbit File
- Select slave product → Radar → Apply Orbit File
- Use "Sentinel Precise Orbit" (auto-downloads if needed)

### 4. Radiometric Calibration

- Select master product → Radar → Radiometric → Calibrate
  - Source Band: Intensity_VV (or Intensity_VH)
  - Output: Sigma0
  - Click "Run"
- Repeat for slave product

### 5. Terrain Correction

- Select master product → Radar → Geometric → Terrain Correction → Range-Doppler Terrain Correction
  - DEM: SRTM 1Sec HGT (or load your SRTM DEM)
  - Pixel Spacing: 10 m (both X and Y)
  - Map Projection: WGS84 (EPSG:4326)
  - Click "Run"
- Repeat for slave product

### 6. DEM-Assisted Coregistration

- Select both master and slave (terrain-corrected) products
- Radar → Coregistration → DEM-Assisted Coregistration
  - DEM: SRTM 1Sec HGT
  - Click "Run"

### 7. Create Stack

- Select both coregistered products
- Radar → Coregistration → Create Stack
  - Click "Run"
  - This creates a stack product with both images

### 8. Offset Tracking (CRITICAL STEP)

- Select stack product
- Radar → Offset Tracking → Cross-Correlation Matcher
- **CRITICAL PARAMETERS:**
  - **Search Range X: 400** (or 500 for safety)
  - **Search Range Y: 400** (or 500 for safety)
  - **Window Size X: 128**
  - **Window Size Y: 128**
  - **Grid Spacing X: 40**
  - **Grid Spacing Y: 40**
  - **Correlation Threshold: 0.3**
  - Click "Run"

### 9. Calculate Velocity

- The offset tracking produces displacement maps (X_offset, Y_offset)
- Calculate velocity: Velocity = sqrt(X_offset² + Y_offset²) / time_interval_days
- Or use: Radar → Offset Tracking → Velocity Calculator (if available)

### 10. Extract Centerline Velocity

- Load glacier outline shapefile
- Extract velocity values along centerline
- Save to CSV: `track{orbit}_YYYYMMDD_YYYYMMDD_vel.csv`

### 11. Validate Results

- Check correlation map: Should have correlation ≥ 0.1 in peak velocity area
- Check if velocity is at search boundary: Should NOT be at ±400 pixels
- If correlation < 0.1 or at boundary: Increase search range to 500 pixels and re-process

---

## Output Files

For each pair, save:
- Velocity map: `track{orbit}_YYYYMMDD_YYYYMMDD_vel.tif`
- Centerline velocity CSV: `track{orbit}_YYYYMMDD_YYYYMMDD_vel.csv`
- Correlation map: `track{orbit}_YYYYMMDD_YYYYMMDD_corr.tif` (optional, for validation)

---

## Validation Checklist

After processing each pair:

- [ ] Correlation ≥ 0.1 in peak velocity area
- [ ] Velocity NOT at search boundary (±400 pixels)
- [ ] Velocity map covers glacier area
- [ ] Centerline velocity extracted and saved

---

## Time Estimate

- Per pair: 15-30 minutes (depending on computer speed)
- Total for 8 pairs: 2-4 hours of active processing time
- With validation and troubleshooting: 1-2 days

---

## Troubleshooting

### Low Correlation (< 0.1)
- Increase search range to 500 pixels
- Check if images are properly coregistered
- Verify DEM quality

### Velocity at Boundary
- Increase search range to 500-600 pixels
- True velocity may exceed 800 m/d

### Processing Errors
- Ensure sufficient disk space (each pair ~500 MB)
- Check SNAP version compatibility
- Verify SAFE files are not corrupted

---

## Notes

- **Do NOT mix tracks** - Process Track 78 and Track 173 completely separately
- **Save frequently** - SNAP processing can be time-consuming
- **Validate each pair** - Don't proceed to next pair until current one is validated
- **Document any issues** - Note any pairs that fail validation

---

**Status:** Instructions ready. Begin processing when ready.
