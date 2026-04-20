#!/usr/bin/env python3
"""
Interactive tool to click on glacier tail position - V2 (More Reliable)
Uses a simpler approach with better event handling
"""

import os
import json
import math
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('TkAgg')  # Force TkAgg backend for better interactivity
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch

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

def click_glacier_tail_simple(date, image_path, label, previous_position=None):
    """
    Simpler version with manual coordinate entry as fallback
    """
    print("\n" + "="*70)
    print(f"IMAGE: {date} - {label}")
    print("="*70)
    
    # Load image
    img = Image.open(image_path)
    img_array = np.array(img)
    width, height = img.size
    
    # Storage
    glacier_tail_position = None
    click_received = False
    
    # Create figure with better settings
    fig = plt.figure(figsize=(16, 12))
    ax = fig.add_subplot(111)
    ax.imshow(img_array)
    ax.set_title(f'{date}\n{label}\n\nCLICK on glacier tail, then type coordinates in terminal',
                fontsize=14, fontweight='bold', pad=20)
    ax.axis('off')
    
    # Show previous position
    if previous_position:
        prev_circle = Circle(previous_position, radius=30, color='green', 
                           fill=False, linewidth=3, linestyle='--', alpha=0.7)
        ax.add_patch(prev_circle)
        ax.text(previous_position[0], previous_position[1] - 40, 'PREVIOUS', 
               color='green', fontsize=10, fontweight='bold',
               ha='center', va='top',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
    
    # Instructions
    info_text = ax.text(0.02, 0.98, 
                       f'Image size: {width} x {height} pixels\n'
                       f'Resolution: 5.88 m/pixel\n\n'
                       'Option 1: Click on image\n'
                       'Option 2: Enter coordinates manually',
                       transform=ax.transAxes, fontsize=10,
                       verticalalignment='top',
                       bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.9))
    
    # Click handler
    def on_click(event):
        nonlocal glacier_tail_position, click_received
        
        if event.inaxes == ax and (event.button == 1 or event.button == 3):
            glacier_tail_position = (event.xdata, event.ydata)
            click_received = True
            
            # Draw marker
            circle = Circle((event.xdata, event.ydata), radius=30, color='red', 
                          fill=False, linewidth=4)
            ax.add_patch(circle)
            ax.text(event.xdata, event.ydata - 45, 'TAIL', 
                   color='red', fontsize=11, fontweight='bold',
                   ha='center', va='top',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
            
            if previous_position:
                arrow = FancyArrowPatch(previous_position, glacier_tail_position,
                                      arrowstyle='->', mutation_scale=30,
                                      color='yellow', linewidth=3, alpha=0.8)
                ax.add_patch(arrow)
                dist_px = calculate_distance(previous_position, glacier_tail_position)
                dist_m = pixels_to_meters(dist_px)
                info_text.set_text(
                    f'Clicked at: ({event.xdata:.1f}, {event.ydata:.1f})\n'
                    f'Movement: {dist_m:.1f} m\n'
                    f'Close window and press Enter in terminal'
                )
            else:
                info_text.set_text(
                    f'Clicked at: ({event.xdata:.1f}, {event.ydata:.1f})\n'
                    f'Baseline position\n'
                    f'Close window and press Enter in terminal'
                )
            
            fig.canvas.draw()
            print(f"\n✓ Click registered at: ({event.xdata:.1f}, {event.ydata:.1f})")
            print("  Close the window and press Enter in terminal to continue")
    
    # Connect event
    fig.canvas.mpl_connect('button_press_event', on_click)
    
    # Show image (non-blocking first, then blocking)
    print(f"\n📸 Image opened: {os.path.basename(image_path)}")
    print("   → Click on the glacier tail position in the image")
    print("   → OR enter coordinates manually in terminal")
    print("   → Close the window when done")
    
    plt.show(block=False)
    plt.pause(0.1)  # Give window time to appear
    
    # Wait for user input
    print("\n" + "-"*70)
    print("After clicking on the image (or if clicking doesn't work):")
    print("1. Look at the image and note the glacier tail position")
    print("2. Close the matplotlib window")
    print("3. Enter coordinates manually if needed")
    print("-"*70)
    
    # Try to get click, with fallback to manual entry
    user_input = input("\nPress Enter after clicking (or 'm' to enter coordinates manually): ").strip().lower()
    
    if user_input == 'm' or not click_received:
        # Manual coordinate entry
        print(f"\nEnter pixel coordinates for glacier tail position")
        print(f"Image size: {width} x {height} pixels")
        print("Format: x,y  (e.g., 650.5,280.3)")
        
        while True:
            try:
                coords_input = input("Coordinates (x,y): ").strip()
                x, y = map(float, coords_input.split(','))
                
                if 0 <= x <= width and 0 <= y <= height:
                    glacier_tail_position = (x, y)
                    print(f"✓ Coordinates accepted: ({x:.1f}, {y:.1f})")
                    break
                else:
                    print(f"⚠ Coordinates out of range. Image is {width} x {height}")
            except ValueError:
                print("⚠ Invalid format. Use: x,y (e.g., 650.5,280.3)")
            except Exception as e:
                print(f"⚠ Error: {e}")
    
    plt.close(fig)
    
    return glacier_tail_position

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
    print("INTERACTIVE GLACIER TAIL MOVEMENT MEASUREMENT - V2")
    print("="*70)
    print("\nThis version works even if clicking doesn't work!")
    print("You can click on images OR enter coordinates manually.")
    print(f"\nResolution: {RESOLUTION_M_PER_PIXEL} meters per pixel")
    
    os.makedirs(VIS_DIR, exist_ok=True)
    
    positions = {}
    
    # Step 1: Baseline
    date1 = '2025-09-12'
    path1, label1 = get_image_path(date1)
    if not path1:
        print(f"\n❌ Error: Image not found for {date1}")
        return
    
    pos1 = click_glacier_tail_simple(date1, path1, label1, previous_position=None)
    if pos1:
        positions[date1] = pos1
    
    # Step 2: First movement
    date2 = '2025-09-17'
    path2, label2 = get_image_path(date2)
    if path2:
        pos2 = click_glacier_tail_simple(date2, path2, label2, previous_position=pos1 if pos1 else None)
        if pos2:
            positions[date2] = pos2
    
    # Step 3: Second movement
    date3 = '2025-10-25'
    path3, label3 = get_image_path(date3)
    if path3:
        pos3 = click_glacier_tail_simple(date3, path3, label3, previous_position=pos2 if pos2 else pos1 if pos1 else None)
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

