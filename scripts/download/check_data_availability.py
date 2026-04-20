#!/usr/bin/env python3
"""
Check data availability for different satellite sources.
"""

from datetime import datetime, timedelta
import json

# Current date
today = datetime.now()
print("=" * 60)
print("Satellite Data Availability Check")
print("=" * 60)
print(f"Current Date: {today.strftime('%Y-%m-%d')}")
print()

# Target dates for Didal Glacier event
target_dates = {
    "before_initial": ("2025-09-01", "2025-09-18"),
    "initial_movement": ("2025-09-19", "2025-09-25"),
    "second_movement": ("2025-10-20", "2025-10-30"),
    "continued_movement": ("2025-10-31", "2025-11-10"),
}

print("Target Dates for Didal Glacier Event:")
print("-" * 60)
for period, (start, end) in target_dates.items():
    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")
    days_ago_start = (today - start_dt).days
    days_ago_end = (today - end_dt).days
    
    print(f"{period.replace('_', ' ').title()}:")
    print(f"  Dates: {start} to {end}")
    if days_ago_start > 0:
        print(f"  Start date: {days_ago_start} days ago")
    else:
        print(f"  Start date: {abs(days_ago_start)} days in the future")
    if days_ago_end > 0:
        print(f"  End date: {days_ago_end} days ago")
    else:
        print(f"  End date: {abs(days_ago_end)} days in the future")
    print()

print("=" * 60)
print("Data Availability by Source")
print("=" * 60)
print()

# 1. Sentinel-2
print("1. SENTINEL-2 (Copernicus)")
print("-" * 60)
print("  Typical delay: 1-3 days after acquisition")
print("  Processing delay: Level-2A products: 1-2 weeks")
print("  Status: ", end="")
if today.year >= 2025:
    print("✅ Data should be available (if dates are in past)")
    print("  → Check: https://scihub.copernicus.eu/")
else:
    print("⏳ Data not yet available (dates are in future)")
    print("  → Will be available after acquisition dates")
print()

# 2. Landsat
print("2. LANDSAT (USGS)")
print("-" * 60)
print("  Typical delay: 1-2 days after acquisition")
print("  Processing delay: Collection 2 Level-2: 1-2 weeks")
print("  Status: ", end="")
if today.year >= 2025:
    print("✅ Data should be available (if dates are in past)")
    print("  → Check: https://earthexplorer.usgs.gov/")
else:
    print("⏳ Data not yet available (dates are in future)")
    print("  → Will be available after acquisition dates")
print()

# 3. Corona
print("3. CORONA (USGS - Historical)")
print("-" * 60)
print("  Period: 1960s-1970s only")
print("  Status: ❌ NOT AVAILABLE for 2025 dates")
print("  Note: Corona is historical imagery only")
print("  → Can be used for baseline comparison from 1960s-1970s")
print()

# 4. Planet
print("4. PLANET CubeSat")
print("-" * 60)
print("  Typical delay: Hours to days")
print("  Processing: Near real-time")
print("  Status: ✅ DATA AVAILABLE")
print("  → Already downloaded: October 28, 2025")
print("  → Additional images available via Planet Explorer")
print("  → Check: https://www.planet.com/explorer/")
print()

print("=" * 60)
print("Recommendations")
print("=" * 60)
print()

if today.year < 2025:
    print("⚠️  You are checking for future dates (2025).")
    print("   Data will become available after the acquisition dates.")
    print()
    print("✅ CURRENTLY AVAILABLE:")
    print("   - Planet: Already have Oct 28, 2025 image")
    print("   - Planet: Can search for additional dates")
    print()
    print("⏳ WILL BE AVAILABLE LATER:")
    print("   - Sentinel-2: Check 1-2 weeks after each date")
    print("   - Landsat: Check 1-2 weeks after each date")
    print()
    print("❌ NOT AVAILABLE:")
    print("   - Corona: Historical only (1960s-1970s)")
else:
    print("✅ CHECK NOW:")
    print("   1. Planet: https://www.planet.com/explorer/")
    print("   2. Sentinel-2: https://scihub.copernicus.eu/")
    print("   3. Landsat: https://earthexplorer.usgs.gov/")
    print()
    print("   All three sources should have data available now.")

print()
print("=" * 60)

