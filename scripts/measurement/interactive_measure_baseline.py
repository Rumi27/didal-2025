#!/usr/bin/env python3
"""
Interactive tool to mark points on baseline image
Click to mark reference point and glacier front
"""

import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from pathlib import Path
import json
import numpy as np

def interactive_measurement():
    """Interactive measurement tool for baseline image"""
    output_dir = Path('planet_images/visualizations')
    baseline_path = output_dir / 'glacier_cropped_2025-09-12.png'
    
    if not baseline_path.exists():
        print(f"Error: Baseline image not found at {baseline_path}")
        return
    
    # Load image
    from PIL import Image
    img = Image.open(baseline_path)
    img_array = np.array(img)
    
    # Storage for clicked points
    points = {
        'reference_point': None,
        'glacier_front': None
    }
    
    # Create figure
    fig, ax = plt.subplots(figsize=(16, 12))
    ax.imshow(img_array)
    ax.set_title('BASELINE IMAGE (Sep 12, 2025)\n'
                 'LEFT CLICK: Mark Reference Point (fixed feature)\n'
                 'RIGHT CLICK: Mark Glacier Front Edge\n'
                 'Press ENTER when done',
                 fontsize=14, fontweight='bold', pad=20)
    ax.axis('off')
    
    # Markers for visualization
    ref_marker = None
    glacier_marker = None
    
    def on_click(event):
        nonlocal ref_marker, glacier_marker
        
        if event.inaxes != ax:
            return
        
        if event.button == 1:  # Left click - reference point
            if ref_marker:
                ref_marker.remove()
            
            points['reference_point'] = (event.xdata, event.ydata)
            ref_marker = Circle((event.xdata, event.ydata), 
                               radius=20, color='red', 
                               fill=False, linewidth=3, label='Reference Point')
            ax.add_patch(ref_marker)
            
            # Add text label
            ax.text(event.xdata, event.ydata - 30, 'REF', 
                   color='red', fontsize=12, fontweight='bold',
                   ha='center', va='top',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            print(f"✓ Reference point marked at: ({event.xdata:.1f}, {event.ydata:.1f})")
            plt.draw()
            
        elif event.button == 3:  # Right click - glacier front
            if glacier_marker:
                glacier_marker.remove()
            
            points['glacier_front'] = (event.xdata, event.ydata)
            glacier_marker = Circle((event.xdata, event.ydata), 
                                   radius=20, color='blue', 
                                   fill=False, linewidth=3, label='Glacier Front')
            ax.add_patch(glacier_marker)
            
            # Add text label
            ax.text(event.xdata, event.ydata - 30, 'GLACIER', 
                   color='blue', fontsize=12, fontweight='bold',
                   ha='center', va='top',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            print(f"✓ Glacier front marked at: ({event.xdata:.1f}, {event.ydata:.1f})")
            plt.draw()
    
    def on_key(event):
        if event.key == 'enter':
            if points['reference_point'] and points['glacier_front']:
                # Calculate distance
                import math
                dx = points['glacier_front'][0] - points['reference_point'][0]
                dy = points['glacier_front'][1] - points['reference_point'][1]
                distance_px = math.sqrt(dx**2 + dy**2)
                resolution = 5.88  # m/pixel
                distance_m = distance_px * resolution
                
                print("\n" + "=" * 60)
                print("BASELINE MEASUREMENT (Sep 12, 2025)")
                print("=" * 60)
                print(f"Reference Point: ({points['reference_point'][0]:.1f}, {points['reference_point'][1]:.1f})")
                print(f"Glacier Front: ({points['glacier_front'][0]:.1f}, {points['glacier_front'][1]:.1f})")
                print(f"Distance: {distance_px:.1f} pixels = {distance_m:.1f} meters")
                print("=" * 60)
                
                # Save coordinates
                results = {
                    'date': '2025-09-12',
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
                
                output_file = output_dir / 'baseline_measurement.json'
                with open(output_file, 'w') as f:
                    json.dump(results, f, indent=2)
                
                print(f"\n✓ Coordinates saved to: {output_file}")
                print("\nNext steps:")
                print("1. Run: python3 interactive_measure_sep17.py")
                print("2. Run: python3 interactive_measure_oct25.py")
                print("3. Run: python3 calculate_all_movements.py")
                
                plt.close()
            else:
                print("\n⚠ Please mark both points before pressing ENTER")
                print("   - Left click: Reference point")
                print("   - Right click: Glacier front")
    
    # Connect events
    fig.canvas.mpl_connect('button_press_event', on_click)
    fig.canvas.mpl_connect('key_press_event', on_key)
    
    plt.tight_layout()
    print("\n" + "=" * 60)
    print("INTERACTIVE MEASUREMENT TOOL")
    print("=" * 60)
    print("\nInstructions:")
    print("  • LEFT CLICK: Mark reference point (fixed feature)")
    print("  • RIGHT CLICK: Mark glacier front edge")
    print("  • Press ENTER: Save measurements and close")
    print("\nClick on the image to mark points...")
    print("=" * 60 + "\n")
    
    plt.show()

if __name__ == '__main__':
    interactive_measurement()

