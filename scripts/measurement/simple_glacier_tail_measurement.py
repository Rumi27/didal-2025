#!/usr/bin/env python3
"""
Simple glacier tail measurement - shows images and asks for coordinates
No complex event handling - just display and manual entry
"""

import os
import json
import math
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

# Configuration
VIS_DIR = "planet_images/visualizations"
RESOLUTION_M_PER_PIXEL = 5.88
RESULTS_FILE = os.path.join(VIS_DIR, "glacier_tail_click_measurements.json")

IMAGE_PATHS = {
    '2025-09-12': {
        'enhanced': os.path.join(VIS_DIR, 'glacier_enhanced_2025-09-12.png'),
        'cropped': os.path.join(VIS_DIR, 'glacier_cropped_2025-09-12.png'),
        'label': 'Baseline (5 days before initial movement)'
    },
    '2025-09-17': {
        'enhanced': os.path.join(VIS_DIR, 'glacier_enhanced_2025-09-17.png'),
        'cropped': os.path.join(VIS_DIR, 'glacier_cropped_2025-09-17.png'),
        'label': 'Initial movement detected'
    },
    '2025-10-25': {
        'enhanced': os.path.join(VIS_DIR, 'glacier_enhanced_2025-10-25.png'),
        'cropped': os.path.join(VIS_DIR, 'glacier_cropped_2025-10-25.png'),
        'label': 'Second movement'
    }
}

def get_image_path(date):
    """Get the best available image path for a date"""
    info = IMAGE_PATHS[date]
    if os.path.exists(info['enhanced']):
        return info['enhanced'], info['label']
    elif os.path.exists(info['cropped']):
        return info['cropped'], info['label']
    else:
        return None, None

def calculate_distance(point1, point2):
    """Calculate Euclidean distance between two points in pixels"""
    return math.sqrt((point2[0] - point1[0])**2 + (point2[1] - point1[1])**2)

def pixels_to_meters(pixels):
    """Convert pixels to meters"""
    return pixels * RESOLUTION_M_PER_PIXEL

def show_image_and_get_coords(date, image_path, label, previous_position=None):
    """
    Show image and get coordinates from user
    """
    print("\n" + "="*70)
    print(f"IMAGE: {date} - {label}")
    print("="*70)
    
    # Load image
    img = Image.open(image_path)
    img_array = np.array(img)
    width, height = img.size
    
    # Show image
    fig, ax = plt.subplots(figsize=(16, 12))
    ax.imshow(img_array)
    ax.set_title(f'{date}\n{label}\n\nLook at the image and note the glacier tail position',
                fontsize=14, fontweight='bold', pad=20)
    ax.axis('off')
    
    # Show previous position if available
    if previous_position:
        from matplotlib.patches import Circle, FancyArrowPatch
        prev_circle = Circle(previous_position, radius=30, color='green', 
                           fill=False, linewidth=3, linestyle='--', alpha=0.7)
        ax.add_patch(prev_circle)
        ax.text(previous_position[0], previous_position[1] - 40, 'PREVIOUS\nPOSITION', 
               color='green', fontsize=10, fontweight='bold',
               ha='center', va='top',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
    
    # Add info
    info_text = ax.text(0.02, 0.98, 
                       f'Image size: {width} x {height} pixels\n'
                       f'Resolution: 5.88 m/pixel\n\n'
                       'Close this window and enter coordinates',
                       transform=ax.transAxes, fontsize=11,
                       verticalalignment='top',
                       bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.9))
    
    print(f"\n📸 Showing image: {os.path.basename(image_path)}")
    print(f"   Image size: {width} x {height} pixels")
    print(f"   Resolution: {RESOLUTION_M_PER_PIXEL} m/pixel")
    print("\n   → Look at the image and identify the glacier tail position")
    print("   → Close the window when ready")
    print("   → Then enter the pixel coordinates (x, y)")
    
    # Show image in non-blocking mode first
    plt.show(block=False)
    plt.pause(0.5)  # Give window time to appear
    
    # Wait for user to close window
    input("\nPress Enter after you've closed the image window: ")
    
    # Explicitly close the figure
    plt.close(fig)
    
    # Get coordinates from user
    print("\n" + "-"*70)
    print("Enter the pixel coordinates of the glacier tail position")
    print(f"Image size: {width} x {height} pixels")
    print("Format: x,y  (e.g., 650.5,280.3)")
    print("(Origin (0,0) is at top-left corner)")
    print("-"*70)
    
    while True:
        try:
            coords_input = input("\nGlacier tail coordinates (x,y): ").strip()
            
            if not coords_input:
                print("⚠ Please enter coordinates")
                continue
            
            # Parse coordinates
            parts = coords_input.replace('(', '').replace(')', '').split(',')
            x = float(parts[0].strip())
            y = float(parts[1].strip())
            
            # Validate range
            if 0 <= x <= width and 0 <= y <= height:
                position = (x, y)
                
                # Calculate distance from previous if available
                if previous_position:
                    dist_px = calculate_distance(previous_position, position)
                    dist_m = pixels_to_meters(dist_px)
                    print(f"✓ Coordinates accepted: ({x:.1f}, {y:.1f})")
                    print(f"  Movement from previous: {dist_m:.1f} m ({dist_px:.1f} px)")
                else:
                    print(f"✓ Coordinates accepted: ({x:.1f}, {y:.1f})")
                    print(f"  This is the baseline position")
                
                return position
            else:
                print(f"⚠ Coordinates out of range!")
                print(f"   X must be between 0 and {width}")
                print(f"   Y must be between 0 and {height}")
                
        except ValueError:
            print("⚠ Invalid format. Use: x,y (e.g., 650.5,280.3)")
        except KeyboardInterrupt:
            print("\n\n⚠ Measurement cancelled")
            return None
        except Exception as e:
            print(f"⚠ Error: {e}")

def calculate_movements(positions):
    """Calculate movement distances from initial position"""
    if '2025-09-12' not in positions:
        print("⚠ Error: Baseline position (2025-09-12) is required")
        return None
    
    baseline = positions['2025-09-12']
    results = {
        'baseline': {
            'date': '2025-09-12',
            'position': baseline,
            'movement_pixels': 0.0,
            'movement_meters': 0.0
        }
    }
    
    for date in ['2025-09-17', '2025-10-25']:
        if date in positions:
            pos = positions[date]
            dist_px = calculate_distance(baseline, pos)
            dist_m = pixels_to_meters(dist_px)
            
            results[date] = {
                'date': date,
                'position': pos,
                'movement_pixels': dist_px,
                'movement_meters': dist_m
            }
    
    if '2025-09-17' in positions and '2025-10-25' in positions:
        sep17 = positions['2025-09-17']
        oct25 = positions['2025-10-25']
        incremental_px = calculate_distance(sep17, oct25)
        incremental_m = pixels_to_meters(incremental_px)
        
        results['incremental'] = {
            'period': '2025-09-17 to 2025-10-25',
            'movement_pixels': incremental_px,
            'movement_meters': incremental_m
        }
    
    return results

def main():
    """Main function"""
    print("\n" + "="*70)
    print("SIMPLE GLACIER TAIL MOVEMENT MEASUREMENT")
    print("="*70)
    print("\nThis version shows images and asks for coordinates manually.")
    print("No clicking needed - just look and type coordinates!")
    print(f"\nResolution: {RESOLUTION_M_PER_PIXEL} meters per pixel")
    
    os.makedirs(VIS_DIR, exist_ok=True)
    
    positions = {}
    
    # Step 1: Baseline
    date1 = '2025-09-12'
    path1, label1 = get_image_path(date1)
    if not path1:
        print(f"\n❌ Error: Image not found for {date1}")
        return
    
    pos1 = show_image_and_get_coords(date1, path1, label1, previous_position=None)
    if pos1:
        positions[date1] = pos1
    else:
        print("\n❌ Measurement cancelled")
        return
    
    # Step 2: First movement
    date2 = '2025-09-17'
    path2, label2 = get_image_path(date2)
    if path2:
        pos2 = show_image_and_get_coords(date2, path2, label2, previous_position=pos1)
        if pos2:
            positions[date2] = pos2
    
    # Step 3: Second movement
    date3 = '2025-10-25'
    path3, label3 = get_image_path(date3)
    if path3:
        pos3 = show_image_and_get_coords(date3, path3, label3, previous_position=pos2 if pos2 else pos1)
        if pos3:
            positions[date3] = pos3
    
    # Calculate movements
    print("\n" + "="*70)
    print("CALCULATING MOVEMENTS")
    print("="*70)
    
    results = calculate_movements(positions)
    
    if not results:
        print("\n❌ Could not calculate movements")
        return
    
    # Print results
    print("\n📊 MOVEMENT RESULTS:")
    print("-" * 70)
    
    baseline = results['baseline']
    print(f"\nBaseline (2025-09-12):")
    print(f"  Position: ({baseline['position'][0]:.1f}, {baseline['position'][1]:.1f}) pixels")
    print(f"  Movement: 0.0 m (reference position)")
    
    if '2025-09-17' in results:
        m = results['2025-09-17']
        print(f"\nFirst Movement (2025-09-17):")
        print(f"  Position: ({m['position'][0]:.1f}, {m['position'][1]:.1f}) pixels")
        print(f"  Movement from baseline: {m['movement_meters']:.1f} m ({m['movement_pixels']:.1f} px)")
        print(f"  Time period: 5 days")
        print(f"  Average velocity: {m['movement_meters']/5:.2f} m/day")
    
    if '2025-10-25' in results:
        m = results['2025-10-25']
        print(f"\nSecond Movement (2025-10-25):")
        print(f"  Position: ({m['position'][0]:.1f}, {m['position'][1]:.1f}) pixels")
        print(f"  Movement from baseline: {m['movement_meters']:.1f} m ({m['movement_pixels']:.1f} px)")
        print(f"  Time period: 43 days")
        print(f"  Average velocity: {m['movement_meters']/43:.2f} m/day")
    
    if 'incremental' in results:
        m = results['incremental']
        print(f"\nIncremental Movement (Sep 17 → Oct 25):")
        print(f"  Movement: {m['movement_meters']:.1f} m ({m['movement_pixels']:.1f} px)")
        print(f"  Time period: 38 days")
        print(f"  Average velocity: {m['movement_meters']/38:.2f} m/day")
    
    # Save results
    output_data = {
        'resolution_m_per_pixel': RESOLUTION_M_PER_PIXEL,
        'positions': {k: {'x': float(v[0]), 'y': float(v[1])} for k, v in positions.items()},
        'results': {
            k: {kk: float(vv) if isinstance(vv, (int, float)) else vv 
                for kk, vv in v.items()} 
            for k, v in results.items()
        }
    }
    
    with open(RESULTS_FILE, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n💾 Results saved to: {RESULTS_FILE}")
    print("\n✅ Measurement complete!")

if __name__ == "__main__":
    main()

