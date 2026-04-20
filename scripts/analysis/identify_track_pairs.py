#!/usr/bin/env python3
"""
Identify Track 78 and Track 173 same-track pairs for cross-track artifact analysis.

This script identifies which same-track pairs need to be processed to test
whether the "stuttering" velocity pattern is a geometric artifact or real physics.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# Load metadata
metadata_file = Path("satellite_data/sentinel1/processed/sentinel1_detailed_metadata.json")
with open(metadata_file, 'r') as f:
    metadata = json.load(f)

# Create orbit and date mapping
acquisitions = {}
for item in metadata['acquisitions']:
    date = item['acquisition_date']
    orbit = item['relative_orbit']
    datetime_str = item['datetime']
    acquisitions[date] = {
        'orbit': orbit,
        'datetime': datetime_str,
        'filename': item['filename']
    }

# Separate by track
track78_dates = sorted([d for d, info in acquisitions.items() if info['orbit'] == 78])
track173_dates = sorted([d for d, info in acquisitions.items() if info['orbit'] == 173])

print("=" * 80)
print("TASK 1: CROSS-TRACK ARTIFACT ANALYSIS - PAIR IDENTIFICATION")
print("=" * 80)

print("\n=== CURRENT CROSS-TRACK PAIRS (9 pairs, 6-day intervals) ===")
print("All pairs mix Orbit 78 and Orbit 173 - potential geometric artifacts\n")

# Current cross-track pairs (from velocity_timeseries_python.csv)
cross_track_pairs = [
    ("2025-09-07", "2025-09-13"),  # 78 → 173
    ("2025-09-13", "2025-09-19"),  # 173 → 78
    ("2025-09-19", "2025-09-25"),  # 78 → 173
    ("2025-09-25", "2025-10-01"),  # 173 → 78
    ("2025-10-01", "2025-10-07"),  # 78 → 173
    ("2025-10-07", "2025-10-13"),  # 173 → 78
    ("2025-10-13", "2025-10-19"),  # 78 → 173
    ("2025-10-19", "2025-10-25"),  # 173 → 78
    ("2025-10-25", "2025-10-31"),  # 78 → 173
]

for i, (date1, date2) in enumerate(cross_track_pairs, 1):
    orbit1 = acquisitions[date1]['orbit']
    orbit2 = acquisitions[date2]['orbit']
    days = (datetime.strptime(date2, "%Y-%m-%d") - datetime.strptime(date1, "%Y-%m-%d")).days
    print(f"Pair {i}: {date1} (Orbit {orbit1}) → {date2} (Orbit {orbit2}) | {days} days | CROSS-TRACK")

print("\n" + "=" * 80)
print("=== REQUIRED SAME-TRACK PAIRS ===")
print("=" * 80)

print("\n--- Track 78 Same-Track Pairs (12-day intervals) ---")
track78_pairs = []
for i in range(len(track78_dates) - 1):
    date1 = track78_dates[i]
    date2 = track78_dates[i + 1]
    days = (datetime.strptime(date2, "%Y-%m-%d") - datetime.strptime(date1, "%Y-%m-%d")).days
    midpoint = datetime.strptime(date1, "%Y-%m-%d") + timedelta(days=days/2)
    midpoint_str = midpoint.strftime("%Y-%m-%d")
    
    track78_pairs.append({
        'date1': date1,
        'date2': date2,
        'days': days,
        'midpoint': midpoint_str
    })
    
    print(f"Pair {i+1}: {date1} → {date2} | {days} days | Midpoint: {midpoint_str} | Orbit 78 → 78")

print("\n--- Track 173 Same-Track Pairs (12-day intervals) ---")
track173_pairs = []
for i in range(len(track173_dates) - 1):
    date1 = track173_dates[i]
    date2 = track173_dates[i + 1]
    days = (datetime.strptime(date2, "%Y-%m-%d") - datetime.strptime(date1, "%Y-%m-%d")).days
    midpoint = datetime.strptime(date1, "%Y-%m-%d") + timedelta(days=days/2)
    midpoint_str = midpoint.strftime("%Y-%m-%d")
    
    track173_pairs.append({
        'date1': date1,
        'date2': date2,
        'days': days,
        'midpoint': midpoint_str
    })
    
    print(f"Pair {i+1}: {date1} → {date2} | {days} days | Midpoint: {midpoint_str} | Orbit 173 → 173")

print("\n" + "=" * 80)
print("=== EXPECTED TIME SERIES AFTER PROCESSING ===")
print("=" * 80)

print("\nTrack 78 Time Series (4 measurements, 12-day intervals):")
for i, pair in enumerate(track78_pairs, 1):
    print(f"  {i}. {pair['midpoint']}: Velocity from {pair['date1']} → {pair['date2']} pair")

print("\nTrack 173 Time Series (4 measurements, 12-day intervals):")
for i, pair in enumerate(track173_pairs, 1):
    print(f"  {i}. {pair['midpoint']}: Velocity from {pair['date1']} → {pair['date2']} pair")

print("\n" + "=" * 80)
print("=== PROCESSING REQUIREMENTS ===")
print("=" * 80)
print("""
1. Re-process 8 same-track pairs in SNAP:
   - 4 Track 78 pairs (12-day intervals)
   - 4 Track 173 pairs (12-day intervals)

2. Critical parameter changes:
   - Search range: Increase from 200 to ≥400 pixels
   - Window size: Keep 128 pixels (same as current)
   - Extract: Glacier centerline velocities

3. Output files:
   - track78_velocity_timeseries.csv
   - track173_velocity_timeseries.csv
   - track_comparison_plot.png

4. Analysis:
   - Compare velocity patterns between tracks
   - Test for synchronization
   - Determine if "stuttering" is artifact or real
""")

print("=" * 80)
print("STATUS: Planning complete. Ready for re-processing.")
print("=" * 80)
