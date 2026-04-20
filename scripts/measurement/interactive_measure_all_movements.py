#!/usr/bin/env python3
"""
Interactive tool to measure glacier front positions on all three dates
Opens Sep 17 and Oct 25 images, uses baseline reference point
"""

import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from pathlib import Path
import json
import numpy as np
import math

def interactive_measure_all():
    """Interactive measurement for all dates"""
    output_dir = Path('planet_images/visualizations')
    
    # Load baseline measurement
    baseline_file = output_dir / 'baseline_measurement.json'
    if not baseline_file.exists():
        print("⚠ Baseline measurement file not found.")
        print("Please provide baseline coordinates:")
        print("(You mentioned you already marked the reference point at ~656, 277)")
        
        # Try to get from user or use the coordinates mentioned
        ref_input = input("\nReference point (x, y) [default: 656.3, 276.7]: ").strip()
        if ref_input:
            ref_parts = ref_input.replace('(', '').replace(')', '').split(',')
            baseline_ref = (float(ref_parts[0].strip()), float(ref_parts[1].strip()))
        else:
            baseline_ref = (656.3, 276.7)  # From the earlier output
        
        glacier_input = input("Glacier front (x, y) [press Enter if unknown]: ").strip()
        if glacier_input:
            glacier_parts = glacier_input.replace('(', '').replace(')', '').split(',')
            baseline_glacier = (float(glacier_parts[0].strip()), float(glacier_parts[1].strip()))
        else:
            # Calculate distance if we have both, otherwise use placeholder
            baseline_glacier = None
        
        if baseline_glacier:
            import math
            dx = baseline_glacier[0] - baseline_ref[0]
            dy = baseline_glacier[1] - baseline_ref[1]
            dist_px = math.sqrt(dx**2 + dy**2)
            dist_m = dist_px * 5.88
            baseline_data = {
                'reference_point': {'x': baseline_ref[0], 'y': baseline_ref[1]},
                'glacier_front': {'x': baseline_glacier[0], 'y': baseline_glacier[1]},
                'distance_pixels': dist_px,
                'distance_meters': dist_m
            }
        else:
            # Use placeholder - will calculate later
            baseline_data = {
                'reference_point': {'x': baseline_ref[0], 'y': baseline_ref[1]},
                'glacier_front': None,
                'distance_pixels': None,
                'distance_meters': None
            }
    else:
        with open(baseline_file, 'r') as f:
            baseline_data = json.load(f)
    
    baseline_ref = (baseline_data['reference_point']['x'], 
                   baseline_data['reference_point']['y'])
    
    if baseline_data['glacier_front']:
        baseline_glacier = (baseline_data['glacier_front']['x'],
                          baseline_data['glacier_front']['y'])
        baseline_dist = baseline_data['distance_meters']
    else:
        baseline_glacier = None
        baseline_dist = None
    
    print("=" * 60)
    print("GLACIER MOVEMENT MEASUREMENT")
    print("=" * 60)
    print(f"\nBaseline Reference Point: ({baseline_ref[0]:.1f}, {baseline_ref[1]:.1f})")
    if baseline_glacier:
        print(f"Baseline Glacier Front: ({baseline_glacier[0]:.1f}, {baseline_glacier[1]:.1f})")
        print(f"Baseline Distance: {baseline_dist:.1f} meters")
    else:
        print("Baseline Glacier Front: (will calculate from measurements)")
    
    # Load images
    img_sep17_path = output_dir / 'glacier_cropped_2025-09-17.png'
    img_oct25_path = output_dir / 'glacier_cropped_2025-10-25.png'
    
    if not img_sep17_path.exists() or not img_oct25_path.exists():
        print("Error: Image files not found!")
        return
    
    from PIL import Image
    img_sep17 = np.array(Image.open(img_sep17_path))
    img_oct25 = np.array(Image.open(img_oct25_path))
    
    # Storage for points
    measurements = {
        'sep17': {
            'reference_point': baseline_ref,
            'glacier_front': None
        },
        'oct25': {
            'reference_point': baseline_ref,
            'glacier_front': None
        }
    }
    
    # Create figure with two subplots
    fig, axes = plt.subplots(1, 2, figsize=(24, 12))
    fig.suptitle('Glacier Front Measurement - Click on Glacier Front Position\n'
                 'LEFT image: Sep 17, 2025 | RIGHT image: Oct 25, 2025\n'
                 'RIGHT-CLICK on each image to mark glacier front\n'
                 'Press ENTER when both are marked',
                 fontsize=16, fontweight='bold', y=0.98)
    
    # Display Sep 17 image
    ax1 = axes[0]
    ax1.imshow(img_sep17)
    ax1.set_title('SEP 17, 2025 (First Movement)\nRight-click to mark glacier front',
                 fontsize=14, fontweight='bold', pad=15)
    ax1.axis('off')
    
    # Show baseline reference point
    ref_circle1 = Circle(baseline_ref, radius=20, color='green', 
                        fill=False, linewidth=2, linestyle='--')
    ax1.add_patch(ref_circle1)
    ax1.text(baseline_ref[0], baseline_ref[1] - 30, 'REF', 
            color='green', fontsize=11, fontweight='bold',
            ha='center', va='top',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
    
    # Display Oct 25 image
    ax2 = axes[1]
    ax2.imshow(img_oct25)
    ax2.set_title('OCT 25, 2025 (Second Movement)\nRight-click to mark glacier front',
                 fontsize=14, fontweight='bold', pad=15)
    ax2.axis('off')
    
    # Show baseline reference point
    ref_circle2 = Circle(baseline_ref, radius=20, color='green', 
                        fill=False, linewidth=2, linestyle='--')
    ax2.add_patch(ref_circle2)
    ax2.text(baseline_ref[0], baseline_ref[1] - 30, 'REF', 
            color='green', fontsize=11, fontweight='bold',
            ha='center', va='top',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
    
    # Markers
    glacier_marker1 = None
    glacier_marker2 = None
    
    def on_click(event):
        nonlocal glacier_marker1, glacier_marker2
        
        if event.inaxes == ax1:  # Sep 17 image
            if event.button == 3:  # Right click
                if glacier_marker1:
                    glacier_marker1.remove()
                
                measurements['sep17']['glacier_front'] = (event.xdata, event.ydata)
                glacier_marker1 = Circle((event.xdata, event.ydata), 
                                       radius=25, color='blue', 
                                       fill=False, linewidth=4, label='Glacier Front')
                ax1.add_patch(glacier_marker1)
                
                ax1.text(event.xdata, event.ydata - 35, 'GLACIER', 
                       color='blue', fontsize=12, fontweight='bold',
                       ha='center', va='top',
                       bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
                
                # Calculate and display distance
                dx = event.xdata - baseline_ref[0]
                dy = event.ydata - baseline_ref[1]
                dist_px = math.sqrt(dx**2 + dy**2)
                dist_m = dist_px * 5.88
                
                ax1.text(0.02, 0.98, f'Distance: {dist_m:.1f} m\n({dist_px:.1f} px)', 
                        transform=ax1.transAxes, fontsize=11, fontweight='bold',
                        verticalalignment='top',
                        bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.8))
                
                print(f"✓ Sep 17: Glacier front marked at ({event.xdata:.1f}, {event.ydata:.1f})")
                print(f"  Distance from ref: {dist_px:.1f} px = {dist_m:.1f} m")
                plt.draw()
        
        elif event.inaxes == ax2:  # Oct 25 image
            if event.button == 3:  # Right click
                if glacier_marker2:
                    glacier_marker2.remove()
                
                measurements['oct25']['glacier_front'] = (event.xdata, event.ydata)
                glacier_marker2 = Circle((event.xdata, event.ydata), 
                                       radius=25, color='red', 
                                       fill=False, linewidth=4, label='Glacier Front')
                ax2.add_patch(glacier_marker2)
                
                ax2.text(event.xdata, event.ydata - 35, 'GLACIER', 
                       color='red', fontsize=12, fontweight='bold',
                       ha='center', va='top',
                       bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
                
                # Calculate and display distance
                dx = event.xdata - baseline_ref[0]
                dy = event.ydata - baseline_ref[1]
                dist_px = math.sqrt(dx**2 + dy**2)
                dist_m = dist_px * 5.88
                
                ax2.text(0.02, 0.98, f'Distance: {dist_m:.1f} m\n({dist_px:.1f} px)', 
                        transform=ax2.transAxes, fontsize=11, fontweight='bold',
                        verticalalignment='top',
                        bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.8))
                
                print(f"✓ Oct 25: Glacier front marked at ({event.xdata:.1f}, {event.ydata:.1f})")
                print(f"  Distance from ref: {dist_px:.1f} px = {dist_m:.1f} m")
                plt.draw()
    
    def on_key(event):
        if event.key == 'enter':
            if measurements['sep17']['glacier_front'] and measurements['oct25']['glacier_front']:
                resolution = 5.88
                
                # Calculate distances
                def calc_dist(ref, front):
                    dx = front[0] - ref[0]
                    dy = front[1] - ref[1]
                    return math.sqrt(dx**2 + dy**2)
                
                # Get baseline distance
                if baseline_data.get('distance_pixels'):
                    dist_sep12 = baseline_data['distance_pixels']
                    dist_sep12_m = baseline_data['distance_meters']
                elif baseline_glacier:
                    # Calculate from coordinates
                    dx = baseline_glacier[0] - baseline_ref[0]
                    dy = baseline_glacier[1] - baseline_ref[1]
                    dist_sep12 = math.sqrt(dx**2 + dy**2)
                    dist_sep12_m = dist_sep12 * resolution
                else:
                    # Use 0 as baseline (relative measurements)
                    dist_sep12 = 0
                    dist_sep12_m = 0
                
                dist_sep17_px = calc_dist(baseline_ref, measurements['sep17']['glacier_front'])
                dist_sep17_m = dist_sep17_px * resolution
                
                dist_oct25_px = calc_dist(baseline_ref, measurements['oct25']['glacier_front'])
                dist_oct25_m = dist_oct25_px * resolution
                
                # Calculate movements
                movement1_px = dist_sep17_px - dist_sep12
                movement1_m = dist_sep17_m - dist_sep12_m
                
                movement2_px = dist_oct25_px - dist_sep17_px
                movement2_m = dist_oct25_m - dist_sep17_m
                
                total_px = dist_oct25_px - dist_sep12
                total_m = dist_oct25_m - dist_sep12_m
                
                # Save measurements
                sep17_data = {
                    'date': '2025-09-17',
                    'reference_point': {'x': float(baseline_ref[0]), 'y': float(baseline_ref[1])},
                    'glacier_front': {'x': float(measurements['sep17']['glacier_front'][0]),
                                     'y': float(measurements['sep17']['glacier_front'][1])},
                    'distance_pixels': float(dist_sep17_px),
                    'distance_meters': float(dist_sep17_m),
                    'resolution_m_per_pixel': resolution
                }
                
                oct25_data = {
                    'date': '2025-10-25',
                    'reference_point': {'x': float(baseline_ref[0]), 'y': float(baseline_ref[1])},
                    'glacier_front': {'x': float(measurements['oct25']['glacier_front'][0]),
                                     'y': float(measurements['oct25']['glacier_front'][1])},
                    'distance_pixels': float(dist_oct25_px),
                    'distance_meters': float(dist_oct25_m),
                    'resolution_m_per_pixel': resolution
                }
                
                with open(output_dir / 'sep17_measurement.json', 'w') as f:
                    json.dump(sep17_data, f, indent=2)
                
                with open(output_dir / 'oct25_measurement.json', 'w') as f:
                    json.dump(oct25_data, f, indent=2)
                
                # Print results
                print("\n" + "=" * 60)
                print("GLACIER MOVEMENT CALCULATIONS")
                print("=" * 60)
                
                print(f"\nBASELINE (Sep 12, 2025):")
                print(f"  Distance: {dist_sep12:.1f} pixels = {dist_sep12_m:.1f} meters")
                
                print(f"\nSEP 17, 2025 (First Movement):")
                print(f"  Distance: {dist_sep17_px:.1f} pixels = {dist_sep17_m:.1f} meters")
                
                print(f"\nOCT 25, 2025 (Second Movement):")
                print(f"  Distance: {dist_oct25_px:.1f} pixels = {dist_oct25_m:.1f} meters")
                
                print(f"\n" + "-" * 60)
                print(f"FIRST MOVEMENT (Sep 12 → Sep 17):")
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
                
                # Save final results
                final_results = {
                    'resolution_m_per_pixel': resolution,
                    'distances': {
                        '2025-09-12': {'pixels': dist_sep12, 'meters': dist_sep12_m},
                        '2025-09-17': {'pixels': dist_sep17_px, 'meters': dist_sep17_m},
                        '2025-10-25': {'pixels': dist_oct25_px, 'meters': dist_oct25_m}
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
                    json.dump(final_results, f, indent=2)
                
                print(f"\n✓ All measurements saved!")
                print(f"✓ Final results saved to: {results_file}")
                
                plt.close()
            else:
                print("\n⚠ Please mark glacier front on BOTH images before pressing ENTER")
                if not measurements['sep17']['glacier_front']:
                    print("   - Missing: Sep 17 glacier front")
                if not measurements['oct25']['glacier_front']:
                    print("   - Missing: Oct 25 glacier front")
    
    # Connect events
    fig.canvas.mpl_connect('button_press_event', on_click)
    fig.canvas.mpl_connect('key_press_event', on_key)
    
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    
    print("\n" + "=" * 60)
    print("INSTRUCTIONS:")
    print("=" * 60)
    print("1. RIGHT-CLICK on LEFT image (Sep 17) to mark glacier front")
    print("2. RIGHT-CLICK on RIGHT image (Oct 25) to mark glacier front")
    print("3. Press ENTER to calculate movements")
    print("=" * 60 + "\n")
    
    plt.show()

if __name__ == '__main__':
    interactive_measure_all()

