#!/usr/bin/env python3
"""
Analyze glacier tail movement from three key dates: 09/12, 09/17, and 10/25
Provides interactive measurement and automatic calculation
"""

import os
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, FancyArrowPatch
import matplotlib.patches as mpatches

# Configuration
VIS_DIR = "planet_images/visualizations"
RESOLUTION_M_PER_PIXEL = 5.88
MEASUREMENT_FILE = os.path.join(VIS_DIR, "glacier_tail_movement_measurements.json")

def calculate_distance(point1, point2):
    """Calculate Euclidean distance between two points"""
    return np.sqrt((point2[0] - point1[0])**2 + (point2[1] - point1[1])**2)

def pixels_to_meters(pixels):
    """Convert pixels to meters"""
    return pixels * RESOLUTION_M_PER_PIXEL

def analyze_movement_from_measurements():
    """
    Analyze glacier movement from measurement data
    """
    print("\n" + "="*70)
    print("GLACIER TAIL MOVEMENT ANALYSIS")
    print("="*70)
    
    # Check if measurement file exists
    if not os.path.exists(MEASUREMENT_FILE):
        print(f"\n⚠️ Measurement file not found: {MEASUREMENT_FILE}")
        print("\nTo create measurements, you need to:")
        print("1. Identify a fixed reference point (stable feature)")
        print("2. Mark the glacier tail/front edge for each date")
        print("3. Record coordinates")
        print("\nYou can use:")
        print("  - Interactive measurement tool: interactive_measure_sequential.py")
        print("  - Image viewer with coordinate display (GIMP, ImageJ)")
        print("  - Manual coordinate entry")
        return None
    
    # Load measurements
    with open(MEASUREMENT_FILE, 'r') as f:
        data = json.load(f)
    
    dates = ['2025-09-12', '2025-09-17', '2025-10-25']
    
    # Extract measurements
    measurements = {}
    for date in dates:
        if date in data.get('measurements', {}):
            m = data['measurements'][date]
            if m.get('reference_point') and m.get('glacier_front'):
                ref = (m['reference_point']['x'], m['reference_point']['y'])
                front = (m['glacier_front']['x'], m['glacier_front']['y'])
                dist_px = calculate_distance(ref, front)
                dist_m = pixels_to_meters(dist_px)
                
                measurements[date] = {
                    'reference': ref,
                    'glacier_front': front,
                    'distance_pixels': dist_px,
                    'distance_meters': dist_m
                }
    
    if len(measurements) < 3:
        print(f"\n⚠️ Incomplete measurements. Found {len(measurements)}/3 dates.")
        print("Please complete measurements for all three dates.")
        return None
    
    # Calculate movements
    sep12 = measurements['2025-09-12']
    sep17 = measurements['2025-09-17']
    oct25 = measurements['2025-10-25']
    
    # First movement (Sep 12 → Sep 17)
    movement1_px = sep17['distance_pixels'] - sep12['distance_pixels']
    movement1_m = pixels_to_meters(movement1_px)
    
    # Second movement (Sep 17 → Oct 25)
    movement2_px = oct25['distance_pixels'] - sep17['distance_pixels']
    movement2_m = pixels_to_meters(movement2_px)
    
    # Total movement (Sep 12 → Oct 25)
    total_px = oct25['distance_pixels'] - sep12['distance_pixels']
    total_m = pixels_to_meters(total_px)
    
    # Time intervals
    days1 = 5  # Sep 12 to Sep 17
    days2 = 38  # Sep 17 to Oct 25
    days_total = 43  # Sep 12 to Oct 25
    
    # Average velocities
    velocity1 = movement1_m / days1  # m/day
    velocity2 = movement2_m / days2  # m/day
    velocity_avg = total_m / days_total  # m/day
    
    # Print results
    print("\n" + "="*70)
    print("MEASUREMENT RESULTS")
    print("="*70)
    
    print(f"\n📏 Distances from Reference Point:")
    print(f"   Sep 12: {sep12['distance_meters']:.1f} m ({sep12['distance_pixels']:.1f} px)")
    print(f"   Sep 17: {sep17['distance_meters']:.1f} m ({sep17['distance_pixels']:.1f} px)")
    print(f"   Oct 25: {oct25['distance_meters']:.1f} m ({oct25['distance_pixels']:.1f} px)")
    
    print(f"\n📊 Movement Analysis:")
    print(f"\n   First Movement (Sep 12 → Sep 17, {days1} days):")
    print(f"      Distance: {movement1_m:+.1f} m ({movement1_px:+.1f} px)")
    print(f"      Average velocity: {velocity1:.2f} m/day = {velocity1*365:.1f} m/year")
    
    print(f"\n   Second Movement (Sep 17 → Oct 25, {days2} days):")
    print(f"      Distance: {movement2_m:+.1f} m ({movement2_px:+.1f} px)")
    print(f"      Average velocity: {velocity2:.2f} m/day = {velocity2*365:.1f} m/year")
    
    print(f"\n   Total Movement (Sep 12 → Oct 25, {days_total} days):")
    print(f"      Distance: {total_m:+.1f} m ({total_px:+.1f} px)")
    print(f"      Average velocity: {velocity_avg:.2f} m/day = {velocity_avg*365:.1f} m/year")
    
    # Create visualization
    create_movement_visualization(measurements, {
        'movement1_m': movement1_m,
        'movement2_m': movement2_m,
        'total_m': total_m,
        'velocity1': velocity1,
        'velocity2': velocity2,
        'velocity_avg': velocity_avg
    })
    
    # Save results
    results = {
        'resolution_m_per_pixel': RESOLUTION_M_PER_PIXEL,
        'measurements': measurements,
        'movements': {
            'first': {
                'period': '2025-09-12 to 2025-09-17',
                'days': days1,
                'distance_pixels': float(movement1_px),
                'distance_meters': float(movement1_m),
                'velocity_m_per_day': float(velocity1),
                'velocity_m_per_year': float(velocity1 * 365)
            },
            'second': {
                'period': '2025-09-17 to 2025-10-25',
                'days': days2,
                'distance_pixels': float(movement2_px),
                'distance_meters': float(movement2_m),
                'velocity_m_per_day': float(velocity2),
                'velocity_m_per_year': float(velocity2 * 365)
            },
            'total': {
                'period': '2025-09-12 to 2025-10-25',
                'days': days_total,
                'distance_pixels': float(total_px),
                'distance_meters': float(total_m),
                'velocity_m_per_day': float(velocity_avg),
                'velocity_m_per_year': float(velocity_avg * 365)
            }
        }
    }
    
    results_file = os.path.join(VIS_DIR, 'glacier_tail_movement_results.json')
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")
    
    return results

def create_movement_visualization(measurements, movements):
    """
    Create visualization of glacier tail movement
    """
    print("\n📊 Creating movement visualization...")
    
    # Load images
    images = {}
    for date in ['2025-09-12', '2025-09-17', '2025-10-25']:
        img_path = os.path.join(VIS_DIR, f'glacier_cropped_{date}.png')
        if os.path.exists(img_path):
            images[date] = Image.open(img_path)
        else:
            print(f"⚠️ Image not found: {img_path}")
            return
    
    # Create figure
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle('Glacier Tail Movement Analysis', fontsize=16, fontweight='bold')
    
    dates = ['2025-09-12', '2025-09-17', '2025-10-25']
    colors = ['blue', 'orange', 'red']
    
    for idx, date in enumerate(dates):
        ax = axes[idx]
        img = images[date]
        m = measurements[date]
        
        # Display image
        ax.imshow(img)
        ax.axis('off')
        
        # Draw reference point
        ref = m['reference']
        ax.plot(ref[0], ref[1], 'ko', markersize=10, label='Reference Point')
        ax.plot(ref[0], ref[1], 'wo', markersize=8)
        
        # Draw glacier front
        front = m['glacier_front']
        ax.plot(front[0], front[1], 'o', color=colors[idx], markersize=12, 
                label='Glacier Front', markeredgecolor='white', markeredgewidth=2)
        
        # Draw line from reference to front
        ax.plot([ref[0], front[0]], [ref[1], front[1]], 
                color=colors[idx], linewidth=2, linestyle='--', alpha=0.7)
        
        # Add distance label
        dist_text = f"{m['distance_meters']:.0f} m\n({m['distance_pixels']:.0f} px)"
        ax.text(0.5, 0.95, date, transform=ax.transAxes,
                fontsize=12, fontweight='bold', ha='center',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
        ax.text(0.5, 0.05, dist_text, transform=ax.transAxes,
                fontsize=10, ha='center',
                bbox=dict(boxstyle='round', facecolor=colors[idx], alpha=0.7))
    
    # Add summary text
    summary_text = (
        f"Movement Summary:\n"
        f"Sep 12→17: {movements['movement1_m']:+.0f} m ({movements['velocity1']:.2f} m/day)\n"
        f"Sep 17→Oct 25: {movements['movement2_m']:+.0f} m ({movements['velocity2']:.2f} m/day)\n"
        f"Total: {movements['total_m']:+.0f} m ({movements['velocity_avg']:.2f} m/day)"
    )
    
    fig.text(0.5, 0.02, summary_text, ha='center', fontsize=10,
             bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
    
    plt.tight_layout(rect=[0, 0.05, 1, 0.96])
    
    # Save
    output_path = os.path.join(VIS_DIR, 'glacier_tail_movement_analysis.png')
    fig.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"✅ Visualization saved to: {output_path}")
    
    plt.close()

def create_measurement_template():
    """
    Create a template for manual measurement entry
    """
    template = {
        "resolution_m_per_pixel": RESOLUTION_M_PER_PIXEL,
        "instructions": {
            "step1": "Identify a fixed reference point (stable feature visible in all 3 images)",
            "step2": "Mark the glacier tail/front edge for each date",
            "step3": "Record pixel coordinates (x, y) - origin is top-left",
            "step4": "Run this script to calculate movements"
        },
        "measurements": {
            "2025-09-12": {
                "reference_point": {"x": None, "y": None, "note": "Fixed stable feature"},
                "glacier_front": {"x": None, "y": None, "note": "Glacier tail/front edge"}
            },
            "2025-09-17": {
                "reference_point": {"x": None, "y": None, "note": "Same fixed point"},
                "glacier_front": {"x": None, "y": None, "note": "Glacier tail/front edge"}
            },
            "2025-10-25": {
                "reference_point": {"x": None, "y": None, "note": "Same fixed point"},
                "glacier_front": {"x": None, "y": None, "note": "Glacier tail/front edge"}
            }
        }
    }
    
    with open(MEASUREMENT_FILE, 'w') as f:
        json.dump(template, f, indent=2)
    
    print(f"✅ Measurement template created: {MEASUREMENT_FILE}")
    print("\nTo use:")
    print("1. Open the cropped images in an image viewer (GIMP, ImageJ, etc.)")
    print("2. Identify a fixed reference point (e.g., rock outcrop, mountain peak)")
    print("3. Mark the glacier tail/front edge for each date")
    print("4. Record coordinates in the JSON file")
    print("5. Run this script again to calculate movements")

def main():
    """Main function"""
    print("\n" + "="*70)
    print("GLACIER TAIL MOVEMENT ANALYSIS")
    print("="*70)
    
    os.makedirs(VIS_DIR, exist_ok=True)
    
    # Check if measurement file exists
    if not os.path.exists(MEASUREMENT_FILE):
        print("\n⚠️ No measurement file found. Creating template...")
        create_measurement_template()
        print("\nPlease fill in the measurements and run this script again.")
        return
    
    # Analyze movements
    results = analyze_movement_from_measurements()
    
    if results:
        print("\n" + "="*70)
        print("ANALYSIS COMPLETE")
        print("="*70)
        print("\n✅ Movement analysis completed successfully!")
        print("   - Results saved to JSON file")
        print("   - Visualization created")
        print("\n📋 For your paper:")
        print("   - Use these values in Results section")
        print("   - Include visualization in figures if needed")
        print("   - Report velocities in m/day and m/year")

if __name__ == "__main__":
    main()

