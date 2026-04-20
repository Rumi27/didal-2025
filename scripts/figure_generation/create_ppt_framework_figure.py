#!/usr/bin/env python3
"""
Create PPT Framework conceptual diagram for Methods section.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, ConnectionPatch
import numpy as np

# Set up figure
fig, ax = plt.subplots(1, 1, figsize=(10, 7))
ax.set_xlim(0, 10)
ax.set_ylim(0, 8)
ax.axis('off')

# Define colors
color_predisposing = '#4A90E2'  # Blue
color_preparatory = '#F5A623'    # Orange
color_triggering = '#E94B3C'     # Red
color_hypotheses = '#7ED321'     # Green
bg_color = '#F8F8F8'

# Background
ax.add_patch(mpatches.Rectangle((0, 0), 10, 8, facecolor=bg_color, edgecolor='none', zorder=0))

# Title
ax.text(5, 7.5, 'Predisposing--Preparatory--Triggering (PPT) Framework', 
        ha='center', va='center', fontsize=16, fontweight='bold', zorder=10)

# Predisposing factors box (left)
pred_box = FancyBboxPatch((0.5, 4.5), 2.5, 2, 
                          boxstyle="round,pad=0.1", 
                          facecolor=color_predisposing, 
                          edgecolor='black', linewidth=1.5, alpha=0.8)
ax.add_patch(pred_box)
ax.text(1.75, 6.2, 'PREDISPOSING', ha='center', va='center', 
        fontsize=12, fontweight='bold', color='white')
ax.text(1.75, 5.8, 'Factors', ha='center', va='center', 
        fontsize=10, fontweight='bold', color='white')
ax.text(1.75, 5.3, 'Temporal scale:', ha='center', va='center', 
        fontsize=9, color='white', style='italic')
ax.text(1.75, 5.0, 'Decades', ha='center', va='center', 
        fontsize=9, color='white', fontweight='bold')
ax.text(1.75, 4.6, '• Topography\n• Bed geometry\n• Valley constrictions', 
        ha='center', va='top', fontsize=8, color='white')

# Preparatory factors box (center)
prep_box = FancyBboxPatch((3.75, 4.5), 2.5, 2, 
                          boxstyle="round,pad=0.1", 
                          facecolor=color_preparatory, 
                          edgecolor='black', linewidth=1.5, alpha=0.8)
ax.add_patch(prep_box)
ax.text(5, 6.2, 'PREPARATORY', ha='center', va='center', 
        fontsize=12, fontweight='bold', color='white')
ax.text(5, 5.8, 'Factors', ha='center', va='center', 
        fontsize=10, fontweight='bold', color='white')
ax.text(5, 5.3, 'Temporal scale:', ha='center', va='center', 
        fontsize=9, color='white', style='italic')
ax.text(5, 5.0, 'Seasons to Years', ha='center', va='center', 
        fontsize=9, color='white', fontweight='bold')
ax.text(5, 4.6, '• Cumulative PDD\n• SWE patterns\n• Melt rate', 
        ha='center', va='top', fontsize=8, color='white')

# Triggering factors box (right)
trig_box = FancyBboxPatch((7, 4.5), 2.5, 2, 
                          boxstyle="round,pad=0.1", 
                          facecolor=color_triggering, 
                          edgecolor='black', linewidth=1.5, alpha=0.8)
ax.add_patch(trig_box)
ax.text(8.25, 6.2, 'TRIGGERING', ha='center', va='center', 
        fontsize=12, fontweight='bold', color='white')
ax.text(8.25, 5.8, 'Factors', ha='center', va='center', 
        fontsize=10, fontweight='bold', color='white')
ax.text(8.25, 5.3, 'Temporal scale:', ha='center', va='center', 
        fontsize=9, color='white', style='italic')
ax.text(8.25, 5.0, 'Days to Weeks', ha='center', va='center', 
        fontsize=9, color='white', fontweight='bold')
ax.text(8.25, 4.6, '• ROS events\n• Liquid precip\n• Anomalies', 
        ha='center', va='top', fontsize=8, color='white')

# Hypotheses boxes (bottom)
h1_box = FancyBboxPatch((1, 1.5), 2, 1.5, 
                        boxstyle="round,pad=0.1", 
                        facecolor=color_hypotheses, 
                        edgecolor='black', linewidth=1.5, alpha=0.7)
ax.add_patch(h1_box)
ax.text(2, 2.5, 'H1', ha='center', va='center', 
        fontsize=11, fontweight='bold', color='white')
ax.text(2, 2.1, 'Topographic', ha='center', va='center', 
        fontsize=9, color='white')
ax.text(2, 1.8, 'Pinning', ha='center', va='center', 
        fontsize=9, color='white', fontweight='bold')

h2_box = FancyBboxPatch((4, 1.5), 2, 1.5, 
                        boxstyle="round,pad=0.1", 
                        facecolor=color_hypotheses, 
                        edgecolor='black', linewidth=1.5, alpha=0.7)
ax.add_patch(h2_box)
ax.text(5, 2.5, 'H2', ha='center', va='center', 
        fontsize=11, fontweight='bold', color='white')
ax.text(5, 2.1, 'Hydrological', ha='center', va='center', 
        fontsize=9, color='white')
ax.text(5, 1.8, 'Switching', ha='center', va='center', 
        fontsize=9, color='white', fontweight='bold')

h3_box = FancyBboxPatch((7, 1.5), 2, 1.5, 
                        boxstyle="round,pad=0.1", 
                        facecolor=color_hypotheses, 
                        edgecolor='black', linewidth=1.5, alpha=0.7)
ax.add_patch(h3_box)
ax.text(8, 2.5, 'H3', ha='center', va='center', 
        fontsize=11, fontweight='bold', color='white')
ax.text(8, 2.1, 'Melt-driven', ha='center', va='center', 
        fontsize=9, color='white')
ax.text(8, 2.0, 'Preconditioning', ha='center', va='center', 
        fontsize=9, color='white', fontweight='bold')

# Arrows from factors to hypotheses
# Predisposing -> H1
arrow1 = FancyArrowPatch((1.75, 4.5), (2, 3), 
                         arrowstyle='->', lw=2, 
                         color='black', zorder=5)
ax.add_patch(arrow1)

# Preparatory -> H3
arrow2 = FancyArrowPatch((5, 4.5), (8, 3), 
                         arrowstyle='->', lw=2, 
                         color='black', zorder=5)
ax.add_patch(arrow2)

# Triggering -> H2
arrow3 = FancyArrowPatch((8.25, 4.5), (5, 3), 
                         arrowstyle='->', lw=2, 
                         color='black', zorder=5)
ax.add_patch(arrow3)

# Also show that preparatory contributes to H3 (already shown)
# And triggering can also relate to H3
arrow4 = FancyArrowPatch((8.25, 4.5), (7.5, 3), 
                         arrowstyle='->', lw=1.5, 
                         color='gray', linestyle='--', zorder=4, alpha=0.6)
ax.add_patch(arrow4)

# Add connecting line between factors (temporal progression)
ax.plot([1.75, 5, 8.25], [5.5, 5.5, 5.5], 
        'k--', lw=1, alpha=0.3, zorder=1)
ax.text(5, 5.7, 'Temporal progression', ha='center', va='bottom', 
        fontsize=8, style='italic', color='gray')

plt.tight_layout()
plt.savefig('figures/ppt_framework.png', dpi=300, bbox_inches='tight', facecolor='white')
print("Created figures/ppt_framework.png")
plt.close()
