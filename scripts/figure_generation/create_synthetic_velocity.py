#!/usr/bin/env python3
"""
Create synthetic velocity time series for testing the analysis framework.

This is useful while waiting for real Sentinel-1 processing.
The synthetic data simulates a glacier surge pattern.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

# Output file
OUTPUT_CSV = Path("satellite_data/sentinel1/processed/velocity_timeseries.csv")
OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

# Glacier location
GLACIER_LAT = 38.97
GLACIER_LON = 70.75

# Surge pattern parameters
# Simulate: slow → acceleration → surge → braking
BASE_VELOCITY = 0.05  # m/day (normal flow)
SURGE_VELOCITY = 0.35  # m/day (peak surge)
BRAKING_VELOCITY = 0.15  # m/day (braking phase)

# Dates from actual Sentinel-1 products
dates = pd.date_range('2025-09-07', '2025-10-31', freq='6D')

# Create velocity pattern
n = len(dates)
velocity = []

# Phase 1: Normal flow (Sept 7-13)
# Phase 2: Acceleration (Sept 13-25)
# Phase 3: Surge peak (Sept 25 - Oct 7)
# Phase 4: Braking (Oct 7-31)

for i, date in enumerate(dates):
    if date <= pd.Timestamp('2025-09-13'):
        # Normal flow
        v = BASE_VELOCITY + np.random.normal(0, 0.01)
    elif date <= pd.Timestamp('2025-09-25'):
        # Acceleration
        progress = (i - 1) / (n - 1)
        v = BASE_VELOCITY + (SURGE_VELOCITY - BASE_VELOCITY) * progress * 0.6
        v += np.random.normal(0, 0.02)
    elif date <= pd.Timestamp('2025-10-07'):
        # Surge peak
        v = SURGE_VELOCITY + np.random.normal(0, 0.03)
    else:
        # Braking
        progress = (i - 6) / (n - 6)
        v = SURGE_VELOCITY - (SURGE_VELOCITY - BRAKING_VELOCITY) * progress
        v += np.random.normal(0, 0.02)
    
    velocity.append(max(0.01, v))  # Ensure positive

# Calculate time deltas
time_deltas = []
for i in range(len(dates) - 1):
    delta = (dates[i + 1] - dates[i]).total_seconds() / 86400.0
    time_deltas.append(delta)

# Create DataFrame (one entry per pair)
results = []
for i in range(len(dates) - 1):
    date1 = dates[i]
    date2 = dates[i + 1]
    v = velocity[i + 1]  # Velocity at end of interval
    
    # Calculate displacement
    dx_m = v * time_deltas[i] * np.cos(np.radians(45))  # Simplified direction
    dy_m = v * time_deltas[i] * np.sin(np.radians(45))
    
    results.append({
        'date': date2.strftime('%Y-%m-%d'),
        'velocity_m_per_day': float(v),
        'velocity_std': float(v * 0.1),  # 10% uncertainty
        'dx_m': float(dx_m),
        'dy_m': float(dy_m),
        'time_delta_days': float(time_deltas[i])
    })

df = pd.DataFrame(results)

# Save
df.to_csv(OUTPUT_CSV, index=False)

print("=" * 70)
print("✅ Synthetic Velocity Time Series Created")
print("=" * 70)
print()
print(f"Saved: {OUTPUT_CSV}")
print(f"Records: {len(df)}")
print()
print("Velocity Pattern:")
print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
print(f"  Mean velocity: {df['velocity_m_per_day'].mean():.3f} m/day")
print(f"  Min velocity: {df['velocity_m_per_day'].min():.3f} m/day")
print(f"  Max velocity: {df['velocity_m_per_day'].max():.3f} m/day")
print()
print("Pattern: Normal → Acceleration → Surge → Braking")
print()
print("⚠️  NOTE: This is SYNTHETIC data for testing")
print("   Replace with real data once Sentinel-1 is processed")
print()
print("Next: Run analysis")
print("  python3 run_complete_analysis.py")
print()

