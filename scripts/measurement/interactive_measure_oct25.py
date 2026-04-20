#!/usr/bin/env python3
"""
Interactive tool to mark points on Oct 25 image
"""

import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from pathlib import Path
import json
import numpy as np

def interactive_measurement():
    """Interactive measurement tool for Oct 25 image"""
    output_dir = Path('planet_images/visualizations')
    image_path = output_dir / 'glacier_cropped_2025-10-25.png'
    
    if not image_path.exists():
        print(f"Error: Image not found at {image_path}")
        return
    
    from PIL import Image
    img = Image.open(image_path)
    img_array = np.array(img)
    
    # Load baseline reference point
    baseline_file = output_dir / 'baseline_measurement.json'
    baseline_ref = None
    if baseline_file.exists():
        with open(baseline_file, 'r') as f:
            baseline_data = json.load(f)
            baseline_ref = (baseline_data['reference_point']['x'], 
                          baseline_data['reference_point']['y'])
    
    points = {
        'reference_point': baseline_ref,
        'glacier_front': None
    }
    
    fig, ax = plt.subplots(figsize=(16, 12))
    ax.imshow(img_array)
    ax.set_title('OCT 25, 2025 (Second Movement)\n'
                 'LEFT CLICK: Mark Reference Point (same as baseline)\n'
                 'RIGHT CLICK: Mark Glacier Front Edge\n'
                 'Press ENTER when done',
                 fontsize=14, fontweight='bold', pad=20)
    ax.axis('off')
    
    ref_marker = None
    glacier_marker = None
    
    if baseline_ref:
        ref_marker = Circle(baseline_ref, radius=20, color='green', 
                           fill=False, linewidth=2, linestyle='--', 
                           label='Baseline Reference')
        ax.add_patch(ref_marker)
        ax.text(baseline_ref[0], baseline_ref[1] - 30, 'BASELINE REF', 
               color='green', fontsize=10, fontweight='bold',
               ha='center', va='top',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        points['reference_point'] = baseline_ref
        print(f"✓ Using baseline reference point: ({baseline_ref[0]:.1f}, {baseline_ref[1]:.1f})")
    
    def on_click(event):
        nonlocal ref_marker, glacier_marker
        
        if event.inaxes != ax:
            return
        
        if event.button == 1:  # Left click
            if ref_marker and ref_marker.get_linestyle() != '--':
                ref_marker.remove()
            
            points['reference_point'] = (event.xdata, event.ydata)
            if ref_marker:
                ref_marker.remove()
            ref_marker = Circle((event.xdata, event.ydata), 
                               radius=20, color='red', 
                               fill=False, linewidth=3)
            ax.add_patch(ref_marker)
            
            ax.text(event.xdata, event.ydata - 30, 'REF', 
                   color='red', fontsize=12, fontweight='bold',
                   ha='center', va='top',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            print(f"✓ Reference point marked at: ({event.xdata:.1f}, {event.ydata:.1f})")
            plt.draw()
            
        elif event.button == 3:  # Right click
            if glacier_marker:
                glacier_marker.remove()
            
            points['glacier_front'] = (event.xdata, event.ydata)
            glacier_marker = Circle((event.xdata, event.ydata), 
                                   radius=20, color='blue', 
                                   fill=False, linewidth=3)
            ax.add_patch(glacier_marker)
            
            ax.text(event.xdata, event.ydata - 30, 'GLACIER', 
                   color='blue', fontsize=12, fontweight='bold',
                   ha='center', va='top',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            print(f"✓ Glacier front marked at: ({event.xdata:.1f}, {event.ydata:.1f})")
            plt.draw()
    
    def on_key(event):
        if event.key == 'enter':
            if points['reference_point'] and points['glacier_front']:
                import math
                dx = points['glacier_front'][0] - points['reference_point'][0]
                dy = points['glacier_front'][1] - points['reference_point'][1]
                distance_px = math.sqrt(dx**2 + dy**2)
                resolution = 5.88
                distance_m = distance_px * resolution
                
                print("\n" + "=" * 60)
                print("OCT 25 MEASUREMENT")
                print("=" * 60)
                print(f"Reference Point: ({points['reference_point'][0]:.1f}, {points['reference_point'][1]:.1f})")
                print(f"Glacier Front: ({points['glacier_front'][0]:.1f}, {points['glacier_front'][1]:.1f})")
                print(f"Distance: {distance_px:.1f} pixels = {distance_m:.1f} meters")
                print("=" * 60)
                
                results = {
                    'date': '2025-10-25',
                    'reference_point': {
                        'x': float(points['reference_point'][0]),
                        'y': float(points['reference_point'][1])
                    },
                    'glacier_front': {
                        'x': float(points['glacier_front'][0]),
                        'y': float(points['glacier_front'][1])
                    },
                    'distance_pixels': float(distance_px),
                    'distance_meters': float(distance_m),
                    'resolution_m_per_pixel': resolution
                }
                
                output_file = output_dir / 'oct25_measurement.json'
                with open(output_file, 'w') as f:
                    json.dump(results, f, indent=2)
                
                print(f"\n✓ Coordinates saved to: {output_file}")
                print("\nNext: Run python3 calculate_all_movements.py")
                
                plt.close()
            else:
                print("\n⚠ Please mark both points before pressing ENTER")
    
    fig.canvas.mpl_connect('button_press_event', on_click)
    fig.canvas.mpl_connect('key_press_event', on_key)
    
    plt.tight_layout()
    print("\n" + "=" * 60)
    print("OCT 25 MEASUREMENT")
    print("=" * 60)
    print("\nClick on the image to mark points...")
    print("=" * 60 + "\n")
    
    plt.show()

if __name__ == '__main__':
    interactive_measurement()

