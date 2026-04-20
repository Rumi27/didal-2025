#!/usr/bin/env python3
"""
Combine zonal statistics results into final CSV.

After running QGIS Zonal Statistics for all velocity maps,
this script helps combine the results into stable_ground_statistics.csv.

Usage:
    python combine_statistics.py
"""

import csv
import os
from pathlib import Path

# Configuration
OUTPUT_CSV = "processed_data/stable_ground_statistics.csv"
MASK_CSV = "stable_ground_mask_exported.csv"  # If exported from QGIS

def create_template():
    """Create template CSV for manual entry."""
    template = [
        {
            'pair_id': 1,
            'date1': '2025-09-07',
            'date2': '2025-09-13',
            'mu_stable': '',  # Fill from QGIS zonal statistics (vel_mean)
            'sigma_stable': '',  # Fill from QGIS zonal statistics (vel_stddev)
            'n_pixels': '',  # Estimate from polygon area
            'lod': ''  # Calculate: mu_stable + 2*sigma_stable
        },
        {
            'pair_id': 2,
            'date1': '2025-09-13',
            'date2': '2025-09-19',
            'mu_stable': '',
            'sigma_stable': '',
            'n_pixels': '',
            'lod': ''
        },
        {
            'pair_id': 3,
            'date1': '2025-09-19',
            'date2': '2025-09-25',
            'mu_stable': '',
            'sigma_stable': '',
            'n_pixels': '',
            'lod': ''
        },
        {
            'pair_id': 4,
            'date1': '2025-09-25',
            'date2': '2025-10-01',
            'mu_stable': '',
            'sigma_stable': '',
            'n_pixels': '',
            'lod': ''
        },
        {
            'pair_id': 5,
            'date1': '2025-10-01',
            'date2': '2025-10-07',
            'mu_stable': '',
            'sigma_stable': '',
            'n_pixels': '',
            'lod': ''
        },
        {
            'pair_id': 6,
            'date1': '2025-10-13',
            'date2': '2025-10-19',
            'mu_stable': '',
            'sigma_stable': '',
            'n_pixels': '',
            'lod': ''
        }
    ]
    
    return template

def main():
    """Main execution."""
    print("="*70)
    print("COMBINE STABLE GROUND STATISTICS")
    print("="*70)
    print("""
This script helps create stable_ground_statistics.csv after running
QGIS Zonal Statistics for all velocity maps.

INSTRUCTIONS:
============

1. In QGIS, after running Zonal Statistics for all 6 velocity maps:
   - Right-click stable_ground_mask layer
   - Export → Save Features As... → CSV
   - Save as: stable_ground_mask_exported.csv

2. Or manually enter values from QGIS attribute table:
   - For each velocity map, note the vel_mean and vel_stddev values
   - Enter them in the template below

3. Run this script to create template:
   python combine_statistics.py --create-template

4. Fill in the template with values from QGIS

5. Save as: processed_data/stable_ground_statistics.csv
""")
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--create-template":
        template = create_template()
        
        os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
        
        with open(OUTPUT_CSV, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=template[0].keys())
            writer.writeheader()
            writer.writerows(template)
        
        print(f"\n✓ Template created: {OUTPUT_CSV}")
        print("\nNext steps:")
        print("1. Open the CSV file")
        print("2. Fill in mu_stable and sigma_stable from QGIS zonal statistics")
        print("3. Calculate lod = mu_stable + 2*sigma_stable")
        print("4. Save the file")
    else:
        print("\nTo create template CSV, run:")
        print("  python combine_statistics.py --create-template")

if __name__ == "__main__":
    main()
