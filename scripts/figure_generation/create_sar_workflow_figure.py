#!/usr/bin/env python3
"""
Create SAR processing workflow diagram for Methods section.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# Set up figure
fig, ax = plt.subplots(1, 1, figsize=(12, 8))
ax.set_xlim(0, 12)
ax.set_ylim(0, 9)
ax.axis('off')

# Define colors
color_input = '#E8F4F8'      # Light blue
color_process = '#FFF4E6'    # Light orange
color_output = '#E8F5E9'    # Light green
color_arrow = '#333333'     # Dark gray
bg_color = '#FFFFFF'

# Background
ax.add_patch(mpatches.Rectangle((0, 0), 12, 9, facecolor=bg_color, edgecolor='none', zorder=0))

# Title
ax.text(6, 8.3, 'Sentinel-1 SAR Processing Workflow', 
        ha='center', va='center', fontsize=16, fontweight='bold', zorder=10)

# Step 1: Input Data
input_box = FancyBboxPatch((0.5, 6), 2.5, 1.2, 
                           boxstyle="round,pad=0.15", 
                           facecolor=color_input, 
                           edgecolor='black', linewidth=1.5)
ax.add_patch(input_box)
ax.text(1.75, 6.8, 'Input Data', ha='center', va='center', 
        fontsize=11, fontweight='bold')
ax.text(1.75, 6.4, 'S1A IW-GRDH\nOrbits 78, 173\n9 pairs, 6-day', 
        ha='center', va='center', fontsize=9)

# Arrow 1
arrow1 = FancyArrowPatch((3, 6.6), (4, 6.6), 
                         arrowstyle='->', lw=2.5, 
                         color=color_arrow, zorder=5)
ax.add_patch(arrow1)

# Step 2: Preprocessing
prep_box = FancyBboxPatch((4, 5.5), 2.5, 2.2, 
                          boxstyle="round,pad=0.15", 
                          facecolor=color_process, 
                          edgecolor='black', linewidth=1.5)
ax.add_patch(prep_box)
ax.text(5.25, 7.2, 'Preprocessing', ha='center', va='center', 
        fontsize=11, fontweight='bold')
ax.text(5.25, 6.8, '1. Orbit correction', ha='center', va='center', 
        fontsize=9)
ax.text(5.25, 6.5, '2. Radiometric', ha='center', va='center', 
        fontsize=9)
ax.text(5.25, 6.3, '   calibration', ha='center', va='center', 
        fontsize=9)
ax.text(5.25, 6.0, '3. Terrain correction', ha='center', va='center', 
        fontsize=9)
ax.text(5.25, 5.7, '   (10 m × 10 m grid)', ha='center', va='center', 
        fontsize=8, style='italic')

# Arrow 2
arrow2 = FancyArrowPatch((6.5, 6.6), (7.5, 6.6), 
                         arrowstyle='->', lw=2.5, 
                         color=color_arrow, zorder=5)
ax.add_patch(arrow2)

# Step 3: Coregistration
coreg_box = FancyBboxPatch((7.5, 5.5), 2.5, 2.2, 
                           boxstyle="round,pad=0.15", 
                           facecolor=color_process, 
                           edgecolor='black', linewidth=1.5)
ax.add_patch(coreg_box)
ax.text(8.75, 7.2, 'Coregistration', ha='center', va='center', 
        fontsize=11, fontweight='bold')
ax.text(8.75, 6.8, 'DEM-assisted', ha='center', va='center', 
        fontsize=9)
ax.text(8.75, 6.5, 'alignment', ha='center', va='center', 
        fontsize=9)
ax.text(8.75, 6.0, 'Cross-track pairs', ha='center', va='center', 
        fontsize=9)
ax.text(8.75, 5.7, 'Mean corr: 0.483', ha='center', va='center', 
        fontsize=8, style='italic')

# Arrow 3 (down)
arrow3 = FancyArrowPatch((8.75, 5.5), (8.75, 4.5), 
                         arrowstyle='->', lw=2.5, 
                         color=color_arrow, zorder=5)
ax.add_patch(arrow3)

# Step 4: Offset Tracking
offset_box = FancyBboxPatch((6, 3), 5.5, 1.2, 
                            boxstyle="round,pad=0.15", 
                            facecolor=color_process, 
                            edgecolor='black', linewidth=1.5)
ax.add_patch(offset_box)
ax.text(8.75, 3.8, 'Offset Tracking', ha='center', va='center', 
        fontsize=11, fontweight='bold')
ax.text(8.75, 3.4, 'NCC template matching | Ensemble: 32, 64, 128 px | Search: 200 px | Corr threshold: 0.3', 
        ha='center', va='center', fontsize=8)

# Arrow 4 (down)
arrow4 = FancyArrowPatch((8.75, 3), (8.75, 2.2), 
                         arrowstyle='->', lw=2.5, 
                         color=color_arrow, zorder=5)
ax.add_patch(arrow4)

# Step 5: Velocity Conversion
velocity_box = FancyBboxPatch((6, 1), 5.5, 1, 
                               boxstyle="round,pad=0.15", 
                               facecolor=color_output, 
                               edgecolor='black', linewidth=1.5)
ax.add_patch(velocity_box)
ax.text(8.75, 1.7, 'Velocity Conversion', ha='center', va='center', 
        fontsize=11, fontweight='bold')
ax.text(8.75, 1.3, '$V = (\\Delta d_{\\text{pixels}} \\times 10 \\text{ m/pixel}) / \\Delta t$', 
        ha='center', va='center', fontsize=10)

# Add side note for parameters table
note_box = FancyBboxPatch((0.5, 1), 4.5, 3, 
                           boxstyle="round,pad=0.1", 
                           facecolor='#F5F5F5', 
                           edgecolor='gray', linewidth=1, linestyle='--')
ax.add_patch(note_box)
ax.text(2.75, 3.5, 'Key Parameters', ha='center', va='center', 
        fontsize=10, fontweight='bold')
ax.text(2.75, 3.0, 'See Table X', ha='center', va='center', 
        fontsize=9, style='italic')
ax.text(0.7, 2.5, '• Window sizes: 32, 64, 128 px', ha='left', va='center', 
        fontsize=8)
ax.text(0.7, 2.2, '• Search range: 200 px (2,000 m)', ha='left', va='center', 
        fontsize=8)
ax.text(0.7, 1.9, '• Max velocity: 333 m day⁻¹', ha='left', va='center', 
        fontsize=8)
ax.text(0.7, 1.6, '• Resolution: 1.67 m day⁻¹', ha='left', va='center', 
        fontsize=8)
ax.text(0.7, 1.3, '• Temporal baseline: 6 days', ha='left', va='center', 
        fontsize=8)

plt.tight_layout()
plt.savefig('figures/sar_workflow.png', dpi=300, bbox_inches='tight', facecolor='white')
print("Created figures/sar_workflow.png")
plt.close()
