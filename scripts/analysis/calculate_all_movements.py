#!/usr/bin/env python3
"""
Calculate all glacier movements from saved measurements
"""

import json
from pathlib import Path

def calculate_movements():
    """Calculate movements from saved measurements"""
    output_dir = Path('planet_images/visualizations')
    
    # Load all measurements
    files = {
        'baseline': output_dir / 'baseline_measurement.json',
        'sep17': output_dir / 'sep17_measurement.json',
        'oct25': output_dir / 'oct25_measurement.json'
    }
    
    measurements = {}
    for key, filepath in files.items():
        if filepath.exists():
            with open(filepath, 'r') as f:
                measurements[key] = json.load(f)
        else:
            print(f"⚠ Missing: {filepath.name}")
            return
    
    # Extract distances
    dist_sep12 = measurements['baseline']['distance_meters']
    dist_sep17 = measurements['sep17']['distance_meters']
    dist_oct25 = measurements['oct25']['distance_meters']
    
    dist_sep12_px = measurements['baseline']['distance_pixels']
    dist_sep17_px = measurements['sep17']['distance_pixels']
    dist_oct25_px = measurements['oct25']['distance_pixels']
    
    # Calculate movements
    movement1_px = dist_sep17_px - dist_sep12_px
    movement1_m = dist_sep17 - dist_sep12
    
    movement2_px = dist_oct25_px - dist_sep17_px
    movement2_m = dist_oct25 - dist_sep17
    
    total_px = dist_oct25_px - dist_sep12_px
    total_m = dist_oct25 - dist_sep12
    
    # Print results
    print("\n" + "=" * 60)
    print("GLACIER MOVEMENT CALCULATIONS")
    print("=" * 60)
    
    print(f"\nBASELINE (Sep 12, 2025):")
    print(f"  Distance: {dist_sep12_px:.1f} pixels = {dist_sep12:.1f} meters")
    
    print(f"\nFIRST MOVEMENT (Sep 12 → Sep 17):")
    print(f"  Distance change: {movement1_px:+.1f} pixels")
    print(f"  Movement: {abs(movement1_m):.1f} meters")
    if movement1_px > 0:
        print(f"  Direction: Glacier ADVANCED (moved forward)")
    else:
        print(f"  Direction: Glacier RETREATED (moved backward)")
    
    print(f"\nSECOND MOVEMENT (Sep 17 → Oct 25):")
    print(f"  Distance change: {movement2_px:+.1f} pixels")
    print(f"  Movement: {abs(movement2_m):.1f} meters")
    if movement2_px > 0:
        print(f"  Direction: Glacier ADVANCED (moved forward)")
    else:
        print(f"  Direction: Glacier RETREATED (moved backward)")
    
    print(f"\nTOTAL MOVEMENT (Sep 12 → Oct 25):")
    print(f"  Distance change: {total_px:+.1f} pixels")
    print(f"  Total movement: {abs(total_m):.1f} meters")
    if total_px > 0:
        print(f"  Direction: Glacier ADVANCED (moved forward)")
    else:
        print(f"  Direction: Glacier RETREATED (moved backward)")
    
    print("\n" + "=" * 60)
    
    # Save results
    results = {
        'resolution_m_per_pixel': 5.88,
        'distances': {
            '2025-09-12': {
                'pixels': dist_sep12_px,
                'meters': dist_sep12
            },
            '2025-09-17': {
                'pixels': dist_sep17_px,
                'meters': dist_sep17
            },
            '2025-10-25': {
                'pixels': dist_oct25_px,
                'meters': dist_oct25
            }
        },
        'movements': {
            'first_movement': {
                'pixels': movement1_px,
                'meters': movement1_m,
                'direction': 'advanced' if movement1_px > 0 else 'retreated'
            },
            'second_movement': {
                'pixels': movement2_px,
                'meters': movement2_m,
                'direction': 'advanced' if movement2_px > 0 else 'retreated'
            },
            'total_movement': {
                'pixels': total_px,
                'meters': total_m,
                'direction': 'advanced' if total_px > 0 else 'retreated'
            }
        }
    }
    
    results_file = output_dir / 'final_movement_results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✓ Results saved to: {results_file}")
    
    return results

if __name__ == '__main__':
    calculate_movements()

