#!/usr/bin/env python3
"""
Sequential interactive tool to measure glacier front on all three dates
Opens images one by one: Sep 12 → Sep 17 → Oct 25
"""

import matplotlib.pyplot as plt
plt.ion()  # Turn on interactive mode
from matplotlib.patches import Circle
from pathlib import Path
import json
import numpy as np
import math

class ImageMeasurer:
    """Class to handle image measurement"""
    def __init__(self):
        self.glacier_front = None
        self.measurement_done = False
        self.fig = None
        self.ax = None
    
    def measure_image(self, date_label, image_path, reference_point=None):
        """Measure glacier front on a single image"""
        from PIL import Image
        
        if not image_path.exists():
            print(f"Error: Image not found at {image_path}")
            return None
        
        img = np.array(Image.open(image_path))
        
        # Reset state
        self.glacier_front = None
        self.measurement_done = False
        
        # Create figure
        self.fig, self.ax = plt.subplots(figsize=(16, 12))
        self.ax.imshow(img)
        self.ax.set_title(f'{date_label}\nRIGHT-CLICK to mark glacier front position\nPress ENTER when done',
                         fontsize=16, fontweight='bold', pad=20)
        self.ax.axis('off')
        
        # Show reference point if provided
        if reference_point:
            ref_circle = Circle(reference_point, radius=20, color='green', 
                               fill=False, linewidth=2, linestyle='--')
            self.ax.add_patch(ref_circle)
            self.ax.text(reference_point[0], reference_point[1] - 30, 'REF', 
                       color='green', fontsize=12, fontweight='bold',
                       ha='center', va='top',
                       bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
        
        glacier_marker = None
        
        def on_click(event):
            nonlocal glacier_marker
            
            if event.inaxes != self.ax:
                return
            
            if event.button == 3:  # Right click
                if glacier_marker:
                    glacier_marker.remove()
                
                self.glacier_front = (event.xdata, event.ydata)
                glacier_marker = Circle((event.xdata, event.ydata), 
                                       radius=25, color='blue', 
                                       fill=False, linewidth=4, label='Glacier Front')
                self.ax.add_patch(glacier_marker)
                
                self.ax.text(event.xdata, event.ydata - 35, 'GLACIER', 
                           color='blue', fontsize=14, fontweight='bold',
                           ha='center', va='top',
                           bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
                
                # Calculate distance if reference point available
                if reference_point:
                    dx = event.xdata - reference_point[0]
                    dy = event.ydata - reference_point[1]
                    dist_px = math.sqrt(dx**2 + dy**2)
                    dist_m = dist_px * 5.88
                    
                    self.ax.text(0.02, 0.98, f'Distance from ref:\n{dist_m:.1f} m\n({dist_px:.1f} px)', 
                               transform=self.ax.transAxes, fontsize=12, fontweight='bold',
                               verticalalignment='top',
                               bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.9))
                    
                    print(f"  Distance from ref: {dist_px:.1f} px = {dist_m:.1f} m")
                
                print(f"✓ Glacier front marked at: ({event.xdata:.1f}, {event.ydata:.1f})")
                self.fig.canvas.draw()
        
        def on_key(event):
            if event.key == 'enter':
                if self.glacier_front:
                    print(f"\n✓ Measurement complete for {date_label}")
                    self.measurement_done = True
                    plt.close(self.fig)
                else:
                    print("\n⚠ Please mark glacier front before pressing ENTER")
                    print("   RIGHT-CLICK on the glacier front position first")
        
        def on_close(event):
            # When window closes, mark as done
            self.measurement_done = True
        
        # Connect events
        self.fig.canvas.mpl_connect('button_press_event', on_click)
        self.fig.canvas.mpl_connect('key_press_event', on_key)
        self.fig.canvas.mpl_connect('close_event', on_close)
        
        plt.tight_layout()
        
        print("\n" + "=" * 60)
        print(f"MEASURING: {date_label}")
        print("=" * 60)
        print("RIGHT-CLICK on the glacier front position")
        print("Press ENTER when done")
        print("=" * 60)
        print("\n>>> Image window should now be open. Mark the point and press ENTER.")
        
        # Show and block until closed
        plt.show(block=True)
        
        # Small delay to ensure events are processed
        import time
        time.sleep(0.2)
        
        # Return the marked point
        if self.glacier_front:
            return self.glacier_front
        else:
            print(f"\n⚠ No point was marked for {date_label}")
            print("   Please run again and make sure to RIGHT-CLICK on the glacier front")
            return None

def interactive_measure_sequential():
    """Sequential measurement of all three dates"""
    output_dir = Path('planet_images/visualizations')
    
    # Baseline reference point (from earlier)
    baseline_ref = (656.3, 276.7)
    
    # Image paths
    images = {
        'sep12': {
            'path': output_dir / 'glacier_cropped_2025-09-12.png',
            'label': 'SEP 12, 2025 (Baseline)',
            'date': '2025-09-12'
        },
        'sep17': {
            'path': output_dir / 'glacier_cropped_2025-09-17.png',
            'label': 'SEP 17, 2025 (First Movement)',
            'date': '2025-09-17',
            'reference': baseline_ref
        },
        'oct25': {
            'path': output_dir / 'glacier_cropped_2025-10-25.png',
            'label': 'OCT 25, 2025 (Second Movement)',
            'date': '2025-10-25',
            'reference': baseline_ref
        }
    }
    
    print("=" * 60)
    print("SEQUENTIAL GLACIER MOVEMENT MEASUREMENT")
    print("=" * 60)
    print(f"\nReference Point: ({baseline_ref[0]:.1f}, {baseline_ref[1]:.1f})")
    print("\nYou will measure each image one by one:")
    print("1. Sep 12 (Baseline)")
    print("2. Sep 17 (First Movement)")
    print("3. Oct 25 (Second Movement)")
    print("\n" + "=" * 60)
    
    # Create measurer
    measurer = ImageMeasurer()
    
    # Measure each image sequentially
    measurements = {}
    
    # 1. Baseline (Sep 12)
    print("\n>>> STEP 1: BASELINE (Sep 12, 2025)")
    glacier_sep12 = measurer.measure_image(
        images['sep12']['label'],
        images['sep12']['path'],
        reference_point=baseline_ref
    )
    
    if not glacier_sep12:
        print("Error: Could not measure Sep 12")
        return
    
    measurements['sep12'] = {
        'reference_point': baseline_ref,
        'glacier_front': glacier_sep12
    }
    
    # Calculate baseline distance
    dx = glacier_sep12[0] - baseline_ref[0]
    dy = glacier_sep12[1] - baseline_ref[1]
    dist_sep12_px = math.sqrt(dx**2 + dy**2)
    dist_sep12_m = dist_sep12_px * 5.88
    
    print(f"\n✓ Baseline measurement complete")
    print(f"  Distance: {dist_sep12_px:.1f} px = {dist_sep12_m:.1f} m")
    
    # 2. Sep 17
    print("\n>>> STEP 2: FIRST MOVEMENT (Sep 17, 2025)")
    glacier_sep17 = measurer.measure_image(
        images['sep17']['label'],
        images['sep17']['path'],
        reference_point=baseline_ref
    )
    
    if not glacier_sep17:
        print("Error: Could not measure Sep 17")
        return
    
    measurements['sep17'] = {
        'reference_point': baseline_ref,
        'glacier_front': glacier_sep17
    }
    
    # Calculate Sep 17 distance
    dx = glacier_sep17[0] - baseline_ref[0]
    dy = glacier_sep17[1] - baseline_ref[1]
    dist_sep17_px = math.sqrt(dx**2 + dy**2)
    dist_sep17_m = dist_sep17_px * 5.88
    
    print(f"\n✓ Sep 17 measurement complete")
    print(f"  Distance: {dist_sep17_px:.1f} px = {dist_sep17_m:.1f} m")
    
    # 3. Oct 25
    print("\n>>> STEP 3: SECOND MOVEMENT (Oct 25, 2025)")
    glacier_oct25 = measurer.measure_image(
        images['oct25']['label'],
        images['oct25']['path'],
        reference_point=baseline_ref
    )
    
    if not glacier_oct25:
        print("Error: Could not measure Oct 25")
        return
    
    measurements['oct25'] = {
        'reference_point': baseline_ref,
        'glacier_front': glacier_oct25
    }
    
    # Calculate Oct 25 distance
    dx = glacier_oct25[0] - baseline_ref[0]
    dy = glacier_oct25[1] - baseline_ref[1]
    dist_oct25_px = math.sqrt(dx**2 + dy**2)
    dist_oct25_m = dist_oct25_px * 5.88
    
    print(f"\n✓ Oct 25 measurement complete")
    print(f"  Distance: {dist_oct25_px:.1f} px = {dist_oct25_m:.1f} m")
    
    # Calculate movements
    resolution = 5.88
    
    movement1_px = dist_sep17_px - dist_sep12_px
    movement1_m = dist_sep17_m - dist_sep12_m
    
    movement2_px = dist_oct25_px - dist_sep17_px
    movement2_m = dist_oct25_m - dist_sep17_m
    
    total_px = dist_oct25_px - dist_sep12_px
    total_m = dist_oct25_m - dist_sep12_m
    
    # Print results
    print("\n" + "=" * 60)
    print("GLACIER MOVEMENT CALCULATIONS")
    print("=" * 60)
    
    print(f"\nBASELINE (Sep 12, 2025):")
    print(f"  Glacier Front: ({glacier_sep12[0]:.1f}, {glacier_sep12[1]:.1f})")
    print(f"  Distance from ref: {dist_sep12_px:.1f} px = {dist_sep12_m:.1f} m")
    
    print(f"\nSEP 17, 2025 (First Movement):")
    print(f"  Glacier Front: ({glacier_sep17[0]:.1f}, {glacier_sep17[1]:.1f})")
    print(f"  Distance from ref: {dist_sep17_px:.1f} px = {dist_sep17_m:.1f} m")
    
    print(f"\nOCT 25, 2025 (Second Movement):")
    print(f"  Glacier Front: ({glacier_oct25[0]:.1f}, {glacier_oct25[1]:.1f})")
    print(f"  Distance from ref: {dist_oct25_px:.1f} px = {dist_oct25_m:.1f} m")
    
    print(f"\n" + "-" * 60)
    print(f"FIRST MOVEMENT (Sep 12 → Sep 17):")
    print(f"  Position change: ({glacier_sep17[0] - glacier_sep12[0]:+.1f}, {glacier_sep17[1] - glacier_sep12[1]:+.1f}) pixels")
    print(f"  Distance change: {movement1_px:+.1f} pixels")
    print(f"  Movement: {abs(movement1_m):.1f} meters")
    if movement1_px > 0:
        print(f"  Direction: Glacier ADVANCED (moved forward)")
    else:
        print(f"  Direction: Glacier RETREATED (moved backward)")
    
    print(f"\nSECOND MOVEMENT (Sep 17 → Oct 25):")
    print(f"  Position change: ({glacier_oct25[0] - glacier_sep17[0]:+.1f}, {glacier_oct25[1] - glacier_sep17[1]:+.1f}) pixels")
    print(f"  Distance change: {movement2_px:+.1f} pixels")
    print(f"  Movement: {abs(movement2_m):.1f} meters")
    if movement2_px > 0:
        print(f"  Direction: Glacier ADVANCED (moved forward)")
    else:
        print(f"  Direction: Glacier RETREATED (moved backward)")
    
    print(f"\nTOTAL MOVEMENT (Sep 12 → Oct 25):")
    print(f"  Position change: ({glacier_oct25[0] - glacier_sep12[0]:+.1f}, {glacier_oct25[1] - glacier_sep12[1]:+.1f}) pixels")
    print(f"  Distance change: {total_px:+.1f} pixels")
    print(f"  Total movement: {abs(total_m):.1f} meters")
    if total_px > 0:
        print(f"  Direction: Glacier ADVANCED (moved forward)")
    else:
        print(f"  Direction: Glacier RETREATED (moved backward)")
    
    print("\n" + "=" * 60)
    
    # Save all measurements
    sep12_data = {
        'date': '2025-09-12',
        'reference_point': {'x': float(baseline_ref[0]), 'y': float(baseline_ref[1])},
        'glacier_front': {'x': float(glacier_sep12[0]), 'y': float(glacier_sep12[1])},
        'distance_pixels': float(dist_sep12_px),
        'distance_meters': float(dist_sep12_m),
        'resolution_m_per_pixel': resolution
    }
    
    sep17_data = {
        'date': '2025-09-17',
        'reference_point': {'x': float(baseline_ref[0]), 'y': float(baseline_ref[1])},
        'glacier_front': {'x': float(glacier_sep17[0]), 'y': float(glacier_sep17[1])},
        'distance_pixels': float(dist_sep17_px),
        'distance_meters': float(dist_sep17_m),
        'resolution_m_per_pixel': resolution
    }
    
    oct25_data = {
        'date': '2025-10-25',
        'reference_point': {'x': float(baseline_ref[0]), 'y': float(baseline_ref[1])},
        'glacier_front': {'x': float(glacier_oct25[0]), 'y': float(glacier_oct25[1])},
        'distance_pixels': float(dist_oct25_px),
        'distance_meters': float(dist_oct25_m),
        'resolution_m_per_pixel': resolution
    }
    
    with open(output_dir / 'baseline_measurement.json', 'w') as f:
        json.dump(sep12_data, f, indent=2)
    
    with open(output_dir / 'sep17_measurement.json', 'w') as f:
        json.dump(sep17_data, f, indent=2)
    
    with open(output_dir / 'oct25_measurement.json', 'w') as f:
        json.dump(oct25_data, f, indent=2)
    
    # Save final results
    final_results = {
        'resolution_m_per_pixel': resolution,
        'reference_point': {'x': float(baseline_ref[0]), 'y': float(baseline_ref[1])},
        'glacier_positions': {
            '2025-09-12': {'x': float(glacier_sep12[0]), 'y': float(glacier_sep12[1])},
            '2025-09-17': {'x': float(glacier_sep17[0]), 'y': float(glacier_sep17[1])},
            '2025-10-25': {'x': float(glacier_oct25[0]), 'y': float(glacier_oct25[1])}
        },
        'distances': {
            '2025-09-12': {'pixels': dist_sep12_px, 'meters': dist_sep12_m},
            '2025-09-17': {'pixels': dist_sep17_px, 'meters': dist_sep17_m},
            '2025-10-25': {'pixels': dist_oct25_px, 'meters': dist_oct25_m}
        },
        'movements': {
            'first_movement': {
                'pixels': movement1_px,
                'meters': movement1_m,
                'position_change_pixels': {
                    'x': float(glacier_sep17[0] - glacier_sep12[0]),
                    'y': float(glacier_sep17[1] - glacier_sep12[1])
                },
                'direction': 'advanced' if movement1_px > 0 else 'retreated'
            },
            'second_movement': {
                'pixels': movement2_px,
                'meters': movement2_m,
                'position_change_pixels': {
                    'x': float(glacier_oct25[0] - glacier_sep17[0]),
                    'y': float(glacier_oct25[1] - glacier_sep17[1])
                },
                'direction': 'advanced' if movement2_px > 0 else 'retreated'
            },
            'total_movement': {
                'pixels': total_px,
                'meters': total_m,
                'position_change_pixels': {
                    'x': float(glacier_oct25[0] - glacier_sep12[0]),
                    'y': float(glacier_oct25[1] - glacier_sep12[1])
                },
                'direction': 'advanced' if total_px > 0 else 'retreated'
            }
        }
    }
    
    results_file = output_dir / 'final_movement_results.json'
    with open(results_file, 'w') as f:
        json.dump(final_results, f, indent=2)
    
    print(f"\n✓ All measurements saved!")
    print(f"✓ Final results saved to: {results_file}")
    
    return final_results

if __name__ == '__main__':
    interactive_measure_sequential()

