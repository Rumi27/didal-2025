#!/usr/bin/env python3
"""
Create publication-quality visualization figure showing glacier tail movement
"""

import os
import json
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle
import matplotlib.patches as mpatches

# Configuration
VIS_DIR = "planet_images/visualizations"
RESULTS_FILE = os.path.join(VIS_DIR, "glacier_tail_click_measurements.json")
RESOLUTION_M_PER_PIXEL = 5.88

def create_movement_figure():
    """Create publication-quality figure showing glacier tail movement"""
    
    # Load results
    with open(RESULTS_FILE, 'r') as f:
        data = json.load(f)
    
    positions = data['positions']
    results = data['results']
    
    # Load images
    images = {}
    dates = ['2025-09-12', '2025-09-17', '2025-10-25']
    colors = ['blue', 'orange', 'red']
    labels = [
        'Baseline\n(5 days before\ninitial movement)',
        'Initial movement\ndetected',
        'Second movement'
    ]
    
    for date in dates:
        # Try enhanced first, then cropped
        enhanced = os.path.join(VIS_DIR, f'glacier_enhanced_{date}.png')
        cropped = os.path.join(VIS_DIR, f'glacier_cropped_{date}.png')
        
        if os.path.exists(enhanced):
            images[date] = np.array(Image.open(enhanced))
        elif os.path.exists(cropped):
            images[date] = np.array(Image.open(cropped))
    
    if not images:
        print("❌ No images found")
        return
    
    # Create figure
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle('Glacier Tail Movement - Three Key Dates', 
                 fontsize=16, fontweight='bold', y=0.98)
    
    for idx, date in enumerate(dates):
        if date not in images:
            continue
        
        ax = axes[idx]
        img = images[date]
        pos = positions[date]
        color = colors[idx]
        
        # Display image
        ax.imshow(img)
        ax.axis('off')
        
        # Mark position
        circle = Circle((pos['x'], pos['y']), radius=40, color=color, 
                       fill=False, linewidth=4, label='Glacier Tail')
        ax.add_patch(circle)
        
        # Add label
        ax.text(pos['x'], pos['y'] - 50, 'TAIL', 
               color=color, fontsize=12, fontweight='bold',
               ha='center', va='top',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
        
        # Show movement from baseline if not baseline
        if date != '2025-09-12' and date in results:
            movement = results[date]
            movement_text = f"Movement:\n{movement['movement_meters']:.0f} m\n({movement['movement_pixels']:.0f} px)"
            ax.text(0.98, 0.02, movement_text, transform=ax.transAxes,
                   fontsize=11, fontweight='bold', color=color,
                   ha='right', va='bottom',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
        
        # Add date label
        ax.text(0.02, 0.98, date, transform=ax.transAxes,
                fontsize=12, fontweight='bold', color='white',
                bbox=dict(boxstyle='round', facecolor='black', alpha=0.7),
                verticalalignment='top')
        
        # Add description
        ax.text(0.5, 0.05, labels[idx], transform=ax.transAxes,
                fontsize=10, ha='center', va='bottom',
                bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
    
    # Add summary text
    sep17 = results.get('2025-09-17', {})
    oct25 = results.get('2025-10-25', {})
    incremental = results.get('incremental', {})
    
    summary_lines = [
        "Movement Summary:",
        f"Sep 12→17: {sep17.get('movement_meters', 0):.0f} m (60 m/day)",
        f"Sep 17→Oct 25: {incremental.get('movement_meters', 0):.0f} m (57 m/day)",
        f"Total: {oct25.get('movement_meters', 0):.0f} m (58 m/day avg)"
    ]
    
    fig.text(0.5, 0.01, '\n'.join(summary_lines), ha='center', fontsize=11,
             bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))
    
    plt.tight_layout(rect=[0, 0.05, 1, 0.96])
    
    # Save
    output_path = os.path.join(VIS_DIR, 'glacier_tail_movement_figure.png')
    fig.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white', format='png')
    print(f"✅ Figure saved to: {output_path}")
    
    # Also save high-res version
    output_path_hr = os.path.join(VIS_DIR, 'glacier_tail_movement_figure_600dpi.png')
    fig.savefig(output_path_hr, dpi=600, bbox_inches='tight', facecolor='white', format='png')
    print(f"✅ High-res figure (600 DPI) saved to: {output_path_hr}")
    
    plt.close()
    
    return output_path

if __name__ == "__main__":
    create_movement_figure()

