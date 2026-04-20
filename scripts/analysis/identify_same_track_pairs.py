#!/usr/bin/env python3
"""
Identify same-track pairs for Task 1 re-processing.

This script identifies all same-track Sentinel-1 pairs that need to be
re-processed with enlarged search range (Task 2) to eliminate cross-track
artifacts (Task 1).
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

def load_metadata(metadata_path):
    """Load Sentinel-1 acquisition metadata."""
    with open(metadata_path, 'r') as f:
        return json.load(f)

def identify_same_track_pairs(acquisitions):
    """Identify same-track pairs from acquisitions."""
    # Group by orbit
    by_orbit = {}
    for acq in acquisitions:
        orbit = acq['relative_orbit']
        if orbit not in by_orbit:
            by_orbit[orbit] = []
        by_orbit[orbit].append(acq)
    
    # Sort each orbit by date
    for orbit in by_orbit:
        by_orbit[orbit].sort(key=lambda x: x['datetime'])
    
    # Find pairs within each orbit
    same_track_pairs = {}
    for orbit, acqs in by_orbit.items():
        pairs = []
        for i in range(len(acqs) - 1):
            master = acqs[i]
            slave = acqs[i+1]
            
            # Calculate time difference
            master_dt = datetime.fromisoformat(master['datetime'])
            slave_dt = datetime.fromisoformat(slave['datetime'])
            time_diff = slave_dt - master_dt
            
            pairs.append({
                'master': master,
                'slave': slave,
                'temporal_baseline_days': time_diff.days,
                'midpoint_date': (master_dt + timedelta(days=time_diff.days/2)).strftime('%Y-%m-%d')
            })
        
        if pairs:
            same_track_pairs[orbit] = pairs
    
    return same_track_pairs

def main():
    """Main execution."""
    metadata_path = "satellite_data/sentinel1/processed/sentinel1_detailed_metadata.json"
    
    print("=" * 80)
    print("TASK 1 & 2: SAME-TRACK PAIR IDENTIFICATION")
    print("=" * 80)
    
    # Load metadata
    metadata = load_metadata(metadata_path)
    acquisitions = metadata['acquisitions']
    
    # Identify same-track pairs
    same_track_pairs = identify_same_track_pairs(acquisitions)
    
    print("\n=== SAME-TRACK PAIRS FOR RE-PROCESSING ===")
    print(f"\nTotal orbits: {len(same_track_pairs)}")
    
    all_pairs = []
    
    for orbit, pairs in same_track_pairs.items():
        print(f"\n--- Track {orbit} ({len(pairs)} pairs) ---")
        for i, pair in enumerate(pairs, 1):
            master = pair['master']
            slave = pair['slave']
            baseline = pair['temporal_baseline_days']
            midpoint = pair['midpoint_date']
            
            print(f"  Pair {i}: {master['acquisition_date']} → {slave['acquisition_date']}")
            print(f"    Baseline: {baseline} days")
            print(f"    Midpoint: {midpoint}")
            print(f"    Master file: {master['filename']}")
            print(f"    Slave file: {slave['filename']}")
            
            all_pairs.append({
                'track': orbit,
                'pair_num': i,
                'master_date': master['acquisition_date'],
                'slave_date': slave['acquisition_date'],
                'baseline_days': baseline,
                'midpoint_date': midpoint,
                'master_file': master['filename'],
                'slave_file': slave['filename']
            })
    
    # Save to CSV for reference
    import pandas as pd
    df = pd.DataFrame(all_pairs)
    output_path = "processed_data/same_track_pairs_for_reprocessing.csv"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print("=" * 80)
    print(f"Total same-track pairs: {len(all_pairs)}")
    print(f"  Track 78: {len([p for p in all_pairs if p['track'] == 78])} pairs")
    print(f"  Track 173: {len([p for p in all_pairs if p['track'] == 173])} pairs")
    print(f"\nPairs saved to: {output_path}")
    print(f"\n{'='*80}")
    print("RE-PROCESSING REQUIREMENTS")
    print("=" * 80)
    print("""
For each pair, re-process in SNAP with:
1. Search range: 400 pixels (increased from 200)
2. Window size: 128 pixels (unchanged)
3. Grid spacing: 40 pixels (unchanged)
4. Correlation threshold: 0.3 (unchanged)

After processing:
- Extract velocity from glacier centerline
- Save to: processed_data/velocity_timeseries/track{orbit}_YYYYMMDD_YYYYMMDD_vel.csv
""")

if __name__ == "__main__":
    main()
