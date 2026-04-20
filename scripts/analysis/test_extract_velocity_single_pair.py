#!/usr/bin/env python3
import rasterio
import numpy as np
from pathlib import Path
from datetime import datetime

GLACIER_LAT = 38.97
GLACIER_LON = 70.75

VEL_IMG = Path('satellite_data/sentinel1/processed') / \
    'S1A_IW_GRDH_1SDV_20250907T012223_20250907T012248_060875_0794A5_8F34_Orb_Cal_TC_Stack_vel.data' / \
    'Velocity_slv1_13Sep2025.img'

DATE1 = datetime(2025, 9, 7)
DATE2 = datetime(2025, 9, 13)

print('='*70)
print('Testing velocity extraction for Sept 7 → Sept 13 pair')
print('='*70)
print()

if not VEL_IMG.exists():
    print('❌ Velocity image not found:', VEL_IMG)
    raise SystemExit(1)

with rasterio.open(VEL_IMG) as src:
    print('CRS:', src.crs)
    print('Transform:', src.transform)
    print('Size:', src.width, 'x', src.height)
    
    # Convert glacier lat/lon to pixel indices
    row, col = src.index(GLACIER_LON, GLACIER_LAT)
    print('Glacier pixel (row, col):', row, col)
    
    if row < 0 or row >= src.height or col < 0 or col >= src.width:
        print('⚠️ Glacier location outside image bounds')
        raise SystemExit(1)
    
    # Read a small window (5x5) around glacier
    window = ((max(0, row-2), min(src.height, row+3)),
              (max(0, col-2), min(src.width, col+3)))
    data = src.read(1, window=window).astype(float)
    
    # Velocity is already in m/day from SNAP (Offset Tracking with velocity output)
    v_mean = float(np.nanmean(data))
    v_std = float(np.nanstd(data))
    
    print('\nVelocity window (5x5) stats at glacier:')
    print('  mean  = %.3f m/day' % v_mean)
    print('  std   = %.3f m/day' % v_std)
    print('\nRaw values:')
    print(data)

print('\n✅ Test extraction complete')
