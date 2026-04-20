#!/usr/bin/env python3
"""
Calculate glacier movement from cropped images
Uses image analysis to detect glacier front and measure movement
"""

import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Arrow, Rectangle
from pathlib import Path
import json

def load_and_analyze_images():
    """Load cropped images and analyze for movement"""
    output_dir = Path('planet_images/visualizations')
    
    # Load the three cropped images
    images = {
        '2025-09-12': Image.open(output_dir / 'glacier_cropped_2025-09-12.png'),
        '2025-09-17': Image.open(output_dir / 'glacier_cropped_2025-09-17.png'),
        '2025-10-25': Image.open(output_dir / 'glacier_cropped_2025-10-25.png')
    }
    
    resolution = 5.88  # m/pixel
    
    print("=" * 60)
    print("GLACIER MOVEMENT MEASUREMENT")
    print("=" * 60)
    print(f"\nResolution: {resolution} meters per pixel")
    print("\nTo measure movement, you need to:")
    print("1. Identify a fixed reference point (stable feature)")
    print("2. Mark the glacier front edge for each date")
    print("3. Measure pixel distances")
    print("4. Calculate: pixels × 5.88 = meters")
    
    # Display images for manual measurement
    fig, axes = plt.subplots(1, 3, figsize=(30, 10))
    fig.suptitle('Glacier Movement Measurement - Click to Mark Points\n'
                 'Left click: Reference point | Right click: Glacier front',
                 fontsize=16, fontweight='bold')
    
    coordinates = {
        '2025-09-12': {'ref': None, 'glacier': None},
        '2025-09-17': {'ref': None, 'glacier': None},
        '2025-10-25': {'ref': None, 'glacier': None}
    }
    
    def on_click(event, date):
        if event.inaxes is None:
            return
        if event.button == 1:  # Left click - reference point
            coordinates[date]['ref'] = (event.xdata, event.ydata)
            print(f"{date}: Reference point marked at ({event.xdata:.1f}, {event.ydata:.1f})")
        elif event.button == 3:  # Right click - glacier front
            coordinates[date]['glacier'] = (event.xdata, event.ydata)
            print(f"{date}: Glacier front marked at ({event.xdata:.1f}, {event.ydata:.1f})")
    
    for idx, (date, img) in enumerate(images.items()):
        ax = axes[idx]
        ax.imshow(img)
        ax.axis('off')
        ax.set_title(f"{date}\nClick to mark points", fontsize=14, fontweight='bold')
        
        # Connect click event
        fig.canvas.mpl_connect('button_press_event', 
                               lambda e, d=date: on_click(e, d))
    
    plt.tight_layout()
    
    # Save interactive version
    output_path = output_dir / 'glacier_movement_interactive.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n✓ Created interactive measurement image: {output_path}")
    print("\nNOTE: For accurate measurements, use an image viewer with pixel coordinates")
    print("      (e.g., GIMP, ImageJ, or online image viewers)")
    
    # Create a script to calculate if coordinates are provided
    calculation_script = """
# GLACIER MOVEMENT CALCULATION SCRIPT
# Fill in the coordinates below and run this script

import math

resolution = 5.88  # m/pixel

# Coordinates (fill these in after measuring in image viewer)
# Format: (x, y) in pixels

# September 12, 2025
ref_sep12 = (None, None)  # Reference point coordinates
glacier_sep12 = (None, None)  # Glacier front coordinates

# September 17, 2025  
ref_sep17 = (None, None)  # Same reference point
glacier_sep17 = (None, None)  # Glacier front coordinates

# October 25, 2025
ref_oct25 = (None, None)  # Same reference point
glacier_oct25 = (None, None)  # Glacier front coordinates

def calculate_distance(point1, point2):
    return math.sqrt((point2[0] - point1[0])**2 + (point2[1] - point1[1])**2)

# Calculate distances
if all(p is not None for p in [ref_sep12, glacier_sep12]):
    dist_sep12 = calculate_distance(ref_sep12, glacier_sep12)
    dist_sep12_m = dist_sep12 * resolution
    print(f"Sep 12: {dist_sep12:.1f} pixels = {dist_sep12_m:.1f} meters")

if all(p is not None for p in [ref_sep17, glacier_sep17]):
    dist_sep17 = calculate_distance(ref_sep17, glacier_sep17)
    dist_sep17_m = dist_sep17 * resolution
    print(f"Sep 17: {dist_sep17:.1f} pixels = {dist_sep17_m:.1f} meters")

if all(p is not None for p in [ref_oct25, glacier_oct25]):
    dist_oct25 = calculate_distance(ref_oct25, glacier_oct25)
    dist_oct25_m = dist_oct25 * resolution
    print(f"Oct 25: {dist_oct25:.1f} pixels = {dist_oct25_m:.1f} meters")

# Calculate movements
if all(d is not None for d in [dist_sep12, dist_sep17, dist_oct25]):
    movement1_px = dist_sep17 - dist_sep12
    movement1_m = movement1_px * resolution
    print(f"\\nFirst Movement (Sep 12 → Sep 17):")
    print(f"  {movement1_px:.1f} pixels = {movement1_m:.1f} meters")
    
    movement2_px = dist_oct25 - dist_sep17
    movement2_m = movement2_px * resolution
    print(f"\\nSecond Movement (Sep 17 → Oct 25):")
    print(f"  {movement2_px:.1f} pixels = {movement2_m:.1f} meters")
    
    total_px = dist_oct25 - dist_sep12
    total_m = total_px * resolution
    print(f"\\nTotal Movement (Sep 12 → Oct 25):")
    print(f"  {total_px:.1f} pixels = {total_m:.1f} meters")
"""
    
    script_path = output_dir / 'calculate_movement.py'
    with open(script_path, 'w') as f:
        f.write(calculation_script)
    
    print(f"✓ Created calculation script: {script_path}")
    print("\n" + "=" * 60)
    print("INSTRUCTIONS FOR MEASUREMENT:")
    print("=" * 60)
    print("\n1. Open the cropped images in an image viewer:")
    print("   - glacier_cropped_2025-09-12.png")
    print("   - glacier_cropped_2025-09-17.png")
    print("   - glacier_cropped_2025-10-25.png")
    print("\n2. Identify a FIXED reference point (appears in all 3 images)")
    print("   - Example: Rock outcrop, mountain peak, permanent feature")
    print("\n3. Mark the GLACIER FRONT EDGE for each date")
    print("   - Use the same edge definition for all dates")
    print("\n4. Record pixel coordinates (x, y) for:")
    print("   - Reference point (same for all dates)")
    print("   - Glacier front (different for each date)")
    print("\n5. Edit calculate_movement.py with your coordinates")
    print("6. Run: python3 calculate_movement.py")
    print("\n" + "=" * 60)
    
    return coordinates

if __name__ == '__main__':
    load_and_analyze_images()

