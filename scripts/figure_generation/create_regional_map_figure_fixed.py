#!/usr/bin/env python3
"""
Create regional context map showing Tajikistan highlighted in red
with surrounding countries. Fixed version with proper rendering.
"""

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, Polygon
import numpy as np
import os

# --- Configuration ---
GLACIER_LAT, GLACIER_LON = 38.97, 70.75
OUTPUT_FILE = 'processed_data/analysis_results/figure_regional_map.png'

# Central Asia region extent
CENTRAL_ASIA_EXTENT = {
    'lon_min': 60,   # West
    'lon_max': 80,   # East
    'lat_min': 35,   # South
    'lat_max': 45    # North
}

# Tajikistan approximate boundaries (simplified but more accurate)
TAJIKISTAN_COORDS = np.array([
    [67.4, 36.7],  # Southwest corner
    [70.3, 36.7],  # South
    [75.1, 38.5],  # East
    [74.2, 39.5],  # Northeast
    [73.5, 40.0],  # North
    [71.5, 40.5],  # Northwest
    [70.5, 40.0],  # North central
    [68.5, 39.5],  # West central
    [67.4, 38.5],  # Southwest
    [67.4, 36.7]   # Close polygon
])

def create_regional_map_figure():
    """Create regional context map with Tajikistan highlighted."""
    
    fig = plt.figure(figsize=(14, 10))
    
    # Main map (larger)
    ax_main = fig.add_axes([0.1, 0.15, 0.7, 0.75])  # [left, bottom, width, height]
    
    # --- MAIN MAP: Central Asia Region ---
    
    # Background (water areas - light blue)
    ax_main.set_facecolor('#e8f4f8')
    
    # Draw a simple background rectangle for land areas (light beige)
    background_rect = Rectangle(
        (CENTRAL_ASIA_EXTENT['lon_min'], CENTRAL_ASIA_EXTENT['lat_min']),
        CENTRAL_ASIA_EXTENT['lon_max'] - CENTRAL_ASIA_EXTENT['lon_min'],
        CENTRAL_ASIA_EXTENT['lat_max'] - CENTRAL_ASIA_EXTENT['lat_min'],
        facecolor='#f5f5f0', edgecolor='none', zorder=0
    )
    ax_main.add_patch(background_rect)
    
    # Draw Tajikistan (highlighted in RED) using Polygon patch
    tajikistan_poly = Polygon(
        TAJIKISTAN_COORDS,
        closed=True,
        facecolor='red',
        edgecolor='darkred',
        linewidth=2.5,
        alpha=0.8,
        zorder=3,
        label='Tajikistan'
    )
    ax_main.add_patch(tajikistan_poly)
    
    # Add red point for Didal Glacier
    ax_main.plot(GLACIER_LON, GLACIER_LAT, 'o', 
                markersize=12, 
                markeredgecolor='white', markeredgewidth=2.5,
                markerfacecolor='darkred', zorder=5, label='Didal Glacier')
    ax_main.plot(GLACIER_LON, GLACIER_LAT, '+', 
                color='white', markersize=14, 
                markeredgewidth=3, zorder=5)
    
    # Add country label
    ax_main.text(70.0, 39.0, 'Tajikistan', fontsize=16, fontweight='bold',
                color='white', ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='darkred', 
                         alpha=0.9, edgecolor='white', linewidth=2),
                zorder=4)
    
    # Add simple country boundaries (light gray lines)
    # These are simplified approximations
    country_boundaries = [
        # Uzbekistan (to the west and north)
        np.array([[56.0, 37.0], [66.0, 37.0], [66.0, 41.0], [56.0, 41.0], [56.0, 37.0]]),
        # Kyrgyzstan (to the east)
        np.array([[69.0, 39.0], [80.0, 39.0], [80.0, 43.3], [73.0, 43.3], [69.0, 41.0], [69.0, 39.0]]),
        # Afghanistan (to the south)
        np.array([[60.5, 29.4], [74.9, 29.4], [74.9, 36.7], [71.5, 36.7], [71.5, 38.5], [60.5, 38.5], [60.5, 29.4]]),
        # China (to the east)
        np.array([[73.5, 36.7], [75.1, 36.7], [75.1, 40.0], [73.5, 40.0], [73.5, 36.7]]),
    ]
    
    for boundary in country_boundaries:
        poly = Polygon(boundary, closed=True, facecolor='none',
                      edgecolor='#cccccc', linewidth=1, linestyle='--',
                      alpha=0.6, zorder=1)
        ax_main.add_patch(poly)
    
    # Set extent
    ax_main.set_xlim(CENTRAL_ASIA_EXTENT['lon_min'], CENTRAL_ASIA_EXTENT['lon_max'])
    ax_main.set_ylim(CENTRAL_ASIA_EXTENT['lat_min'], CENTRAL_ASIA_EXTENT['lat_max'])
    ax_main.set_aspect('equal', adjustable='box')
    
    # Labels and grid
    ax_main.set_xlabel('Longitude (°E)', fontsize=13, fontweight='bold', labelpad=10)
    ax_main.set_ylabel('Latitude (°N)', fontsize=13, fontweight='bold', labelpad=10)
    ax_main.grid(True, alpha=0.4, linestyle='--', linewidth=0.7, color='gray', zorder=1)
    ax_main.tick_params(labelsize=11)
    
    # Title
    ax_main.set_title('Central Asia - Study Area', 
                     fontsize=18, fontweight='bold', pad=20)
    
    # Add scale bar (approximate)
    scale_length_km = 500
    scale_length_deg = scale_length_km / 111.0  # Approximate: 1 deg ≈ 111 km
    scale_x_start = CENTRAL_ASIA_EXTENT['lon_min'] + 1.0
    scale_y = CENTRAL_ASIA_EXTENT['lat_min'] + 0.5
    
    ax_main.plot([scale_x_start, scale_x_start + scale_length_deg], 
                [scale_y, scale_y], 'k-', linewidth=3, zorder=6)
    ax_main.text(scale_x_start + scale_length_deg/2, scale_y + 0.2,
                f'{scale_length_km} km', ha='center', va='bottom',
                fontsize=10, fontweight='bold', zorder=6)
    
    # --- INSET MAP: World Map (Bottom-left) ---
    ax_inset = fig.add_axes([0.15, 0.15, 0.25, 0.2])
    
    # Background
    ax_inset.set_facecolor('#f0f0f0')
    
    # Simple world map outline (just a rectangle for simplicity)
    world_rect = Rectangle((-180, -90), 360, 180,
                          facecolor='#f5f5f0', edgecolor='black',
                          linewidth=1.5, zorder=0)
    ax_inset.add_patch(world_rect)
    
    # Highlight Central Asia region with a red box
    box_width = CENTRAL_ASIA_EXTENT['lon_max'] - CENTRAL_ASIA_EXTENT['lon_min']
    box_height = CENTRAL_ASIA_EXTENT['lat_max'] - CENTRAL_ASIA_EXTENT['lat_min']
    box_x = CENTRAL_ASIA_EXTENT['lon_min']
    box_y = CENTRAL_ASIA_EXTENT['lat_min']
    
    region_box = Rectangle((box_x, box_y), box_width, box_height,
                          facecolor='red', edgecolor='darkred',
                          linewidth=2.5, alpha=0.5, zorder=2)
    ax_inset.add_patch(region_box)
    
    region_outline = Rectangle((box_x, box_y), box_width, box_height,
                              facecolor='none', edgecolor='darkred',
                              linewidth=2.5, zorder=3)
    ax_inset.add_patch(region_outline)
    
    # Set world map extent
    ax_inset.set_xlim(-180, 180)
    ax_inset.set_ylim(-90, 90)
    ax_inset.set_aspect('equal', adjustable='box')
    ax_inset.set_title('Global Context', fontsize=11, fontweight='bold', pad=8)
    ax_inset.set_xticks([])
    ax_inset.set_yticks([])
    
    # Add orange border around entire figure
    border = FancyBboxPatch((0, 0), 1, 1, 
                           transform=fig.transFigure, 
                           boxstyle="round,pad=0.01",
                           edgecolor='orange', 
                           facecolor='none', 
                           linewidth=5, 
                           zorder=100)
    fig.patches.append(border)
    
    # Save figure
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches='tight', 
                facecolor='white', edgecolor='orange', pad_inches=0.1)
    plt.close()
    
    print(f"✅ Regional map figure saved: {OUTPUT_FILE}")
    print(f"   - Tajikistan highlighted in RED")
    print(f"   - Didal Glacier location marked at ({GLACIER_LAT}°N, {GLACIER_LON}°E)")
    print(f"   - World map inset with region box")
    print(f"   - Orange border around figure")
    print(f"   - Scale bar and grid added")

if __name__ == "__main__":
    create_regional_map_figure()

