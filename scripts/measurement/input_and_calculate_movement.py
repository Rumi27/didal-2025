#!/usr/bin/env python3
"""
Simple script to input coordinates and calculate glacier movement
"""

import math
from pathlib import Path

def calculate_distance(point1, point2):
    """Calculate pixel distance between two points"""
    return math.sqrt((point2[0] - point1[0])**2 + (point2[1] - point1[1])**2)

def calculate_movement():
    """Calculate glacier movement from coordinates"""
    
    resolution = 5.88  # meters per pixel
    
    print("=" * 60)
    print("GLACIER MOVEMENT CALCULATOR")
    print("=" * 60)
    print(f"\nResolution: {resolution} meters per pixel")
    print("\nEnter pixel coordinates (x, y) from your image viewer")
    print("(Press Enter to skip if you don't have coordinates yet)\n")
    
    # Get coordinates
    print("SEPTEMBER 12, 2025 (Baseline):")
    ref_sep12_input = input("  Reference point (x, y): ").strip()
    glacier_sep12_input = input("  Glacier front (x, y): ").strip()
    
    print("\nSEPTEMBER 17, 2025 (First Movement):")
    ref_sep17_input = input("  Reference point (x, y): ").strip()
    glacier_sep17_input = input("  Glacier front (x, y): ").strip()
    
    print("\nOCTOBER 25, 2025 (Second Movement):")
    ref_oct25_input = input("  Reference point (x, y): ").strip()
    glacier_oct25_input = input("  Glacier front (x, y): ").strip()
    
    # Parse coordinates
    def parse_coords(s):
        if not s:
            return None
        try:
            parts = s.replace('(', '').replace(')', '').split(',')
            return (float(parts[0].strip()), float(parts[1].strip()))
        except:
            return None
    
    ref_sep12 = parse_coords(ref_sep12_input)
    glacier_sep12 = parse_coords(glacier_sep12_input)
    ref_sep17 = parse_coords(ref_sep17_input)
    glacier_sep17 = parse_coords(glacier_sep17_input)
    ref_oct25 = parse_coords(ref_oct25_input)
    glacier_oct25 = parse_coords(glacier_oct25_input)
    
    # Calculate distances
    distances = {}
    
    if ref_sep12 and glacier_sep12:
        dist_sep12 = calculate_distance(ref_sep12, glacier_sep12)
        dist_sep12_m = dist_sep12 * resolution
        distances['sep12'] = (dist_sep12, dist_sep12_m)
        print(f"\n✓ Sep 12: {dist_sep12:.1f} pixels = {dist_sep12_m:.1f} meters")
    
    if ref_sep17 and glacier_sep17:
        dist_sep17 = calculate_distance(ref_sep17, glacier_sep17)
        dist_sep17_m = dist_sep17 * resolution
        distances['sep17'] = (dist_sep17, dist_sep17_m)
        print(f"✓ Sep 17: {dist_sep17:.1f} pixels = {dist_sep17_m:.1f} meters")
    
    if ref_oct25 and glacier_oct25:
        dist_oct25 = calculate_distance(ref_oct25, glacier_oct25)
        dist_oct25_m = dist_oct25 * resolution
        distances['oct25'] = (dist_oct25, dist_oct25_m)
        print(f"✓ Oct 25: {dist_oct25:.1f} pixels = {dist_oct25_m:.1f} meters")
    
    # Calculate movements
    if 'sep12' in distances and 'sep17' in distances and 'oct25' in distances:
        print("\n" + "=" * 60)
        print("MOVEMENT CALCULATIONS")
        print("=" * 60)
        
        # First movement
        movement1_px = distances['sep17'][0] - distances['sep12'][0]
        movement1_m = movement1_px * resolution
        print(f"\nFIRST MOVEMENT (Sep 12 → Sep 17):")
        print(f"  Distance change: {movement1_px:+.1f} pixels")
        print(f"  Movement: {abs(movement1_m):.1f} meters")
        if movement1_px > 0:
            print(f"  Direction: Glacier advanced (moved forward)")
        else:
            print(f"  Direction: Glacier retreated (moved backward)")
        
        # Second movement
        movement2_px = distances['oct25'][0] - distances['sep17'][0]
        movement2_m = movement2_px * resolution
        print(f"\nSECOND MOVEMENT (Sep 17 → Oct 25):")
        print(f"  Distance change: {movement2_px:+.1f} pixels")
        print(f"  Movement: {abs(movement2_m):.1f} meters")
        if movement2_px > 0:
            print(f"  Direction: Glacier advanced (moved forward)")
        else:
            print(f"  Direction: Glacier retreated (moved backward)")
        
        # Total movement
        total_px = distances['oct25'][0] - distances['sep12'][0]
        total_m = total_px * resolution
        print(f"\nTOTAL MOVEMENT (Sep 12 → Oct 25):")
        print(f"  Distance change: {total_px:+.1f} pixels")
        print(f"  Total movement: {abs(total_m):.1f} meters")
        if total_px > 0:
            print(f"  Direction: Glacier advanced (moved forward)")
        else:
            print(f"  Direction: Glacier retreated (moved backward)")
        
        print("\n" + "=" * 60)
        
        # Save results
        results = {
            'resolution_m_per_pixel': resolution,
            'distances': {
                '2025-09-12': {'pixels': distances['sep12'][0], 'meters': distances['sep12'][1]},
                '2025-09-17': {'pixels': distances['sep17'][0], 'meters': distances['sep17'][1]},
                '2025-10-25': {'pixels': distances['oct25'][0], 'meters': distances['oct25'][1]}
            },
            'movements': {
                'first_movement': {'pixels': movement1_px, 'meters': movement1_m},
                'second_movement': {'pixels': movement2_px, 'meters': movement2_m},
                'total_movement': {'pixels': total_px, 'meters': total_m}
            }
        }
        
        output_dir = Path('planet_images/visualizations')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        import json
        results_path = output_dir / 'movement_results.json'
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✓ Results saved to: {results_path}")
        
    else:
        print("\n⚠ Not enough coordinates provided for calculation.")
        print("Please measure coordinates in an image viewer and run again.")
        print("\nTo measure:")
        print("1. Open glacier_cropped_*.png images")
        print("2. Identify fixed reference point")
        print("3. Mark glacier front for each date")
        print("4. Record pixel coordinates (x, y)")
        print("5. Run this script again with coordinates")

if __name__ == '__main__':
    calculate_movement()

