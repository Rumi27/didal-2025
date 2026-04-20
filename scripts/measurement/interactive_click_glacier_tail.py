#!/usr/bin/env python3
"""
Interactive tool to click on glacier tail position in each image
and calculate movement distances from the initial position (Sep 12)

Usage:
1. Image 1 (2025-09-12) opens - Click on glacier tail position
2. Image 2 (2025-09-17) opens - Click on glacier tail position (moved)
3. Image 3 (2025-10-25) opens - Click on glacier tail position (moved further)
4. Results show movement distances from initial position
"""

import os
import json
import math
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch
import matplotlib.patches as mpatches

# Configuration
VIS_DIR = "planet_images/visualizations"
RESOLUTION_M_PER_PIXEL = 5.88  # meters per pixel
RESULTS_FILE = os.path.join(VIS_DIR, "glacier_tail_click_measurements.json")

# Image paths - using enhanced individual images if available, otherwise cropped
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

def click_glacier_tail(date, image_path, label, previous_position=None):
    """
    Interactive tool to click on glacier tail position
    
    Args:
        date: Date string (e.g., '2025-09-12')
        image_path: Path to image file
        label: Label for the image
        previous_position: Previous glacier tail position (x, y) if available
    
    Returns:
        (x, y) coordinates of clicked position
    """
    print("\n" + "="*70)
    print(f"IMAGE: {date} - {label}")
    print("="*70)
    
    # Load image
    img = Image.open(image_path)
    img_array = np.array(img)
    
    # Storage for click position
    glacier_tail_position = None
    tail_marker = None
    click_complete = False
    
    # Create figure
    fig, ax = plt.subplots(figsize=(16, 12))
    ax.imshow(img_array)
    ax.set_title(f'{date}\n{label}\n\nCLICK on the glacier tail position (the front/end of the glacier)\nPress ENTER when done',
                fontsize=16, fontweight='bold', pad=20)
    ax.axis('off')
    
    # Show previous position if available
    if previous_position:
        prev_circle = Circle(previous_position, radius=30, color='green', 
                           fill=False, linewidth=3, linestyle='--', alpha=0.7)
        ax.add_patch(prev_circle)
        ax.text(previous_position[0], previous_position[1] - 40, 'PREVIOUS\nPOSITION', 
               color='green', fontsize=11, fontweight='bold',
               ha='center', va='top',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
        
        # Draw arrow from previous to current (will update on click)
        arrow = None
    
    # Instructions text
    info_text = ax.text(0.02, 0.98, 
                       'Instructions:\n'
                       '1. LEFT-CLICK or RIGHT-CLICK on glacier tail\n'
                       '2. Press ENTER when done\n'
                       '3. Resolution: 5.88 m/pixel',
                       transform=ax.transAxes, fontsize=11,
                       verticalalignment='top',
                       bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.9))
    
    def on_click(event):
        nonlocal glacier_tail_position, tail_marker, arrow
        
        print(f"  [DEBUG] Click detected: button={event.button}, inaxes={event.inaxes is not None}")
        
        if event.inaxes != ax:
            print("  ⚠ Click inside the image area!")
            return
        
        # Accept both left click (button 1) and right click (button 3)
        if event.button == 1 or event.button == 3:
            print(f"  [DEBUG] Processing click at ({event.xdata:.1f}, {event.ydata:.1f})")
            # Remove previous marker if exists
            if tail_marker:
                tail_marker.remove()
            if arrow:
                arrow.remove()
            
            # Store position
            glacier_tail_position = (event.xdata, event.ydata)
            
            # Create marker
            tail_marker = Circle((event.xdata, event.ydata), 
                               radius=30, color='red', 
                               fill=False, linewidth=4, label='Glacier Tail')
            ax.add_patch(tail_marker)
            
            # Add label
            ax.text(event.xdata, event.ydata - 45, 'GLACIER\nTAIL', 
                   color='red', fontsize=12, fontweight='bold',
                   ha='center', va='top',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
            
            # Calculate distance from previous position if available
            if previous_position:
                dist_px = calculate_distance(previous_position, glacier_tail_position)
                dist_m = pixels_to_meters(dist_px)
                
                # Draw arrow
                arrow = FancyArrowPatch(previous_position, glacier_tail_position,
                                      arrowstyle='->', mutation_scale=30,
                                      color='yellow', linewidth=3, alpha=0.8)
                ax.add_patch(arrow)
                
                # Update info text
                info_text.set_text(
                    f'Glacier Tail Position:\n'
                    f'Coordinates: ({event.xdata:.1f}, {event.ydata:.1f})\n\n'
                    f'Movement from previous:\n'
                    f'{dist_m:.1f} m ({dist_px:.1f} px)\n\n'
                    f'Resolution: 5.88 m/pixel\n\n'
                    f'Press ENTER to continue'
                )
                
                print(f"  ✓ Glacier tail marked at: ({event.xdata:.1f}, {event.ydata:.1f})")
                print(f"  → Movement from previous: {dist_m:.1f} m ({dist_px:.1f} px)")
            else:
                # First image - no previous position
                info_text.set_text(
                    f'Glacier Tail Position (Baseline):\n'
                    f'Coordinates: ({event.xdata:.1f}, {event.ydata:.1f})\n\n'
                    f'This is the reference position.\n'
                    f'Next images will show movement from here.\n\n'
                    f'Resolution: 5.88 m/pixel\n\n'
                    f'Press ENTER to continue'
                )
                print(f"  ✓ Glacier tail marked at: ({event.xdata:.1f}, {event.ydata:.1f})")
                print(f"  → This is the baseline position")
            
            fig.canvas.draw()
            fig.canvas.flush_events()
    
    def on_key(event):
        nonlocal click_complete
        print(f"  [DEBUG] Key pressed: {event.key}")
        if event.key == 'enter' or event.key == 'return':
            if glacier_tail_position:
                print(f"\n✓ Measurement confirmed for {date}")
                click_complete = True
                plt.close(fig)
            else:
                print("\n⚠ Please click on the glacier tail position first!")
                print("   LEFT-CLICK or RIGHT-CLICK on the glacier tail, then press ENTER")
                print("   Make sure the matplotlib window is in focus (click on it)")
        else:
            print(f"  [DEBUG] Pressed key '{event.key}' - need ENTER")
    
    def on_close(event):
        nonlocal click_complete
        if glacier_tail_position:
            click_complete = True
    
    # Connect events
    fig.canvas.mpl_connect('button_press_event', on_click)
    fig.canvas.mpl_connect('key_press_event', on_key)
    fig.canvas.mpl_connect('close_event', on_close)
    
    # Show plot and wait for click
    print(f"\n📸 Image opened: {os.path.basename(image_path)}")
    print("   → LEFT-CLICK or RIGHT-CLICK on the glacier tail position")
    print("   → Make sure the matplotlib window is ACTIVE (click on it first!)")
    print("   → Press ENTER when done (make sure window is focused)")
    print("\n   TIP: Click directly on the image, then press ENTER")
    
    # Use blocking show - this ensures the window is properly interactive
    plt.show(block=True)
    
    if glacier_tail_position:
        return glacier_tail_position
    else:
        print(f"\n⚠ No position recorded for {date}")
        return None

def calculate_movements(positions):
    """
    Calculate movement distances from initial position
    
    Args:
        positions: Dict with dates as keys and (x, y) tuples as values
    
    Returns:
        Dict with movement calculations
    """
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
    
    # Calculate movement for each subsequent date
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
    
    # Calculate incremental movements
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

def create_results_visualization(positions, results):
    """Create visualization showing all positions and movements"""
    print("\n📊 Creating results visualization...")
    
    # Load all images
    images = {}
    for date in ['2025-09-12', '2025-09-17', '2025-10-25']:
        path, label = get_image_path(date)
        if path and os.path.exists(path):
            images[date] = {
                'image': np.array(Image.open(path)),
                'label': label,
                'position': positions.get(date)
            }
    
    if not images:
        print("⚠ No images found for visualization")
        return
    
    # Create figure
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle('Glacier Tail Movement Analysis - Click Measurements', 
                 fontsize=16, fontweight='bold', y=0.98)
    
    dates = ['2025-09-12', '2025-09-17', '2025-10-25']
    colors = ['blue', 'orange', 'red']
    
    for idx, date in enumerate(dates):
        if date not in images:
            continue
        
        ax = axes[idx]
        img_info = images[date]
        
        # Display image
        ax.imshow(img_info['image'])
        ax.axis('off')
        
        # Add date label
        ax.text(0.02, 0.98, date, transform=ax.transAxes,
                fontsize=12, fontweight='bold', color='white',
                bbox=dict(boxstyle='round', facecolor='black', alpha=0.7),
                verticalalignment='top')
        
        # Mark position if available
        if img_info['position']:
            pos = img_info['position']
            circle = Circle(pos, radius=30, color=colors[idx], 
                          fill=False, linewidth=4)
            ax.add_patch(circle)
            
            ax.text(pos[0], pos[1] - 45, 'TAIL', 
                   color=colors[idx], fontsize=11, fontweight='bold',
                   ha='center', va='top',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
            
            # Show movement from baseline if not baseline
            if date != '2025-09-12' and date in results:
                movement = results[date]
                movement_text = f"Movement:\n{movement['movement_meters']:.0f} m\n({movement['movement_pixels']:.0f} px)"
                ax.text(0.98, 0.02, movement_text, transform=ax.transAxes,
                       fontsize=10, fontweight='bold', color=colors[idx],
                       ha='right', va='bottom',
                       bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
        
        # Add label
        ax.text(0.5, 0.05, img_info['label'], transform=ax.transAxes,
                fontsize=10, ha='center', va='bottom',
                bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
    
    # Add summary text
    summary_lines = ["Movement Summary:"]
    if '2025-09-17' in results:
        m = results['2025-09-17']
        summary_lines.append(f"Sep 12→17: {m['movement_meters']:.0f} m")
    if '2025-10-25' in results:
        m = results['2025-10-25']
        summary_lines.append(f"Sep 12→Oct 25: {m['movement_meters']:.0f} m")
    if 'incremental' in results:
        m = results['incremental']
        summary_lines.append(f"Sep 17→Oct 25: {m['movement_meters']:.0f} m")
    
    fig.text(0.5, 0.01, '\n'.join(summary_lines), ha='center', fontsize=11,
             bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))
    
    plt.tight_layout(rect=[0, 0.05, 1, 0.96])
    
    # Save
    output_path = os.path.join(VIS_DIR, 'glacier_tail_click_analysis.png')
    fig.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"✅ Visualization saved to: {output_path}")
    
    plt.close()

def main():
    """Main function - sequential measurement"""
    print("\n" + "="*70)
    print("INTERACTIVE GLACIER TAIL MOVEMENT MEASUREMENT")
    print("="*70)
    print("\nThis tool will open three images sequentially.")
    print("Click on the glacier tail position in each image.")
    print("Movement will be calculated from the initial position (Sep 12).")
    print(f"\nResolution: {RESOLUTION_M_PER_PIXEL} meters per pixel")
    
    os.makedirs(VIS_DIR, exist_ok=True)
    
    # Storage for positions
    positions = {}
    
    # Step 1: Baseline (Sep 12)
    date1 = '2025-09-12'
    path1, label1 = get_image_path(date1)
    if not path1:
        print(f"\n❌ Error: Image not found for {date1}")
        return
    
    pos1 = click_glacier_tail(date1, path1, label1, previous_position=None)
    if not pos1:
        print("\n❌ Measurement cancelled")
        return
    positions[date1] = pos1
    
    # Step 2: First movement (Sep 17)
    date2 = '2025-09-17'
    path2, label2 = get_image_path(date2)
    if not path2:
        print(f"\n❌ Error: Image not found for {date2}")
        return
    
    pos2 = click_glacier_tail(date2, path2, label2, previous_position=pos1)
    if not pos2:
        print("\n⚠ Warning: No position recorded for Sep 17")
    else:
        positions[date2] = pos2
    
    # Step 3: Second movement (Oct 25)
    date3 = '2025-10-25'
    path3, label3 = get_image_path(date3)
    if not path3:
        print(f"\n❌ Error: Image not found for {date3}")
        return
    
    pos3 = click_glacier_tail(date3, path3, label3, previous_position=pos2 if pos2 else pos1)
    if not pos3:
        print("\n⚠ Warning: No position recorded for Oct 25")
    else:
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
    
    # Create visualization
    create_results_visualization(positions, results)
    
    print("\n" + "="*70)
    print("MEASUREMENT COMPLETE!")
    print("="*70)
    print("\n✅ All measurements completed successfully!")
    print("   - Results saved to JSON file")
    print("   - Visualization created")
    print("\n📋 For your paper:")
    print("   - Use these movement values in Results section")
    print("   - Include visualization in figures if needed")
    print("   - Report velocities in m/day and m/year")

if __name__ == "__main__":
    main()

