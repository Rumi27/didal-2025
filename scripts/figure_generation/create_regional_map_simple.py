#!/usr/bin/env python3
"""
Create regional context map - SIMPLE VERSION that definitely works
Using simple rectangles and polygons that will render correctly.
"""

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, FancyBboxPatch
import numpy as np
import os

# --- Configuration ---
GLACIER_LAT, GLACIER_LON = 38.97, 70.75
OUTPUT_FILE = 'processed_data/analysis_results/figure_regional_map.png'

# Central Asia region extent
CENTRAL_ASIA_EXTENT = {
    'lon_min': 60,
    'lon_max': 80,
    'lat_min': 35,
    'lat_max': 45
}

def create_regional_map_figure():
    """Create regional context map with Tajikistan highlighted."""
    
    # Use non-interactive backend to ensure proper rendering
    plt.ioff()  # Turn off interactive mode
    
    fig = plt.figure(figsize=(14, 10), facecolor='white')
    
    # Main map (larger) - use explicit positioning
    ax_main = fig.add_axes([0.1, 0.15, 0.7, 0.75])
    
    # Set background color first
    ax_main.set_facecolor('#f5f5f0')  # Light beige for land
    
    # Draw a background rectangle for the entire region
    bg_rect = Rectangle(
        (CENTRAL_ASIA_EXTENT['lon_min'], CENTRAL_ASIA_EXTENT['lat_min']),
        CENTRAL_ASIA_EXTENT['lon_max'] - CENTRAL_ASIA_EXTENT['lon_min'],
        CENTRAL_ASIA_EXTENT['lat_max'] - CENTRAL_ASIA_EXTENT['lat_min'],
        facecolor='#f5f5f0',
        edgecolor='#cccccc',
        linewidth=1,
        zorder=0
    )
    ax_main.add_patch(bg_rect)
    
    # Tajikistan - use a simple polygon (simplified rectangular approximation)
    # Tajikistan roughly: 67.4-75.1°E, 36.7-41.0°N
    tajik_coords = np.array([
        [67.4, 36.7],  # SW
        [75.1, 36.7],  # SE
        [75.1, 41.0],  # NE
        [67.4, 41.0],  # NW
        [67.4, 36.7]   # Close
    ])
    
    tajikistan_poly = Polygon(
        tajik_coords,
        closed=True,
        facecolor='red',
        edgecolor='darkred',
        linewidth=3,
        alpha=0.8,
        zorder=2
    )
    ax_main.add_patch(tajikistan_poly)
    
    # Add Tajikistan label
    ax_main.text(71.25, 38.85, 'Tajikistan', 
                fontsize=18, fontweight='bold',
                color='white', ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='darkred', 
                         alpha=0.9, edgecolor='white', linewidth=2),
                zorder=3)
    
    # Add red point for Didal Glacier
    ax_main.plot(GLACIER_LON, GLACIER_LAT, 'o', 
                markersize=14,
                markeredgecolor='white',
                markeredgewidth=3,
                markerfacecolor='darkred',
                zorder=5)
    ax_main.plot(GLACIER_LON, GLACIER_LAT, '+',
                color='white',
                markersize=16,
                markeredgewidth=3,
                zorder=5)
    
    # Add simple country boundary approximations (as rectangles)
    countries = {
        'Uzbekistan': {'x': 56, 'y': 37, 'width': 12, 'height': 6, 'color': '#e0e0e0'},
        'Kyrgyzstan': {'x': 69, 'y': 39, 'width': 8, 'height': 5, 'color': '#e8e8e8'},
        'Afghanistan': {'x': 60.5, 'y': 29.4, 'width': 15, 'height': 9, 'color': '#e5e5e5'},
        'China': {'x': 73.5, 'y': 36.7, 'width': 30, 'height': 15, 'color': '#eeeeee'},
    }
    
    for country_name, params in countries.items():
        # Only show if within our extent
        if (params['x'] < CENTRAL_ASIA_EXTENT['lon_max'] and 
            params['x'] + params['width'] > CENTRAL_ASIA_EXTENT['lon_min'] and
            params['y'] < CENTRAL_ASIA_EXTENT['lat_max'] and
            params['y'] + params['height'] > CENTRAL_ASIA_EXTENT['lat_min']):
            
            country_rect = Rectangle(
                (params['x'], params['y']),
                params['width'],
                params['height'],
                facecolor='none',
                edgecolor='#999999',
                linewidth=1,
                linestyle='--',
                alpha=0.6,
                zorder=1
            )
            ax_main.add_patch(country_rect)
    
    # Set extent
    ax_main.set_xlim(CENTRAL_ASIA_EXTENT['lon_min'], CENTRAL_ASIA_EXTENT['lon_max'])
    ax_main.set_ylim(CENTRAL_ASIA_EXTENT['lat_min'], CENTRAL_ASIA_EXTENT['lat_max'])
    ax_main.set_aspect('equal', adjustable='box')
    
    # Labels and grid
    ax_main.set_xlabel('Longitude (°E)', fontsize=13, fontweight='bold', labelpad=10)
    ax_main.set_ylabel('Latitude (°N)', fontsize=13, fontweight='bold', labelpad=10)
    ax_main.grid(True, alpha=0.4, linestyle='--', linewidth=0.7, color='gray', zorder=0)
    ax_main.tick_params(labelsize=11)
    
    # Title
    ax_main.set_title('Central Asia - Study Area', 
                     fontsize=18, fontweight='bold', pad=20)
    
    # --- INSET MAP: World Map (Bottom-left) ---
    ax_inset = fig.add_axes([0.15, 0.15, 0.25, 0.2])
    ax_inset.set_facecolor('#f0f0f0')
    
    # World map - simple rectangle
    world_rect = Rectangle((-180, -90), 360, 180,
                          facecolor='#f5f5f0',
                          edgecolor='black',
                          linewidth=2,
                          zorder=0)
    ax_inset.add_patch(world_rect)
    
    # Highlight Central Asia region
    box_width = CENTRAL_ASIA_EXTENT['lon_max'] - CENTRAL_ASIA_EXTENT['lon_min']
    box_height = CENTRAL_ASIA_EXTENT['lat_max'] - CENTRAL_ASIA_EXTENT['lat_min']
    box_x = CENTRAL_ASIA_EXTENT['lon_min']
    box_y = CENTRAL_ASIA_EXTENT['lat_min']
    
    region_box = Rectangle((box_x, box_y), box_width, box_height,
                          facecolor='red',
                          edgecolor='darkred',
                          linewidth=3,
                          alpha=0.6,
                          zorder=2)
    ax_inset.add_patch(region_box)
    
    ax_inset.set_xlim(-180, 180)
    ax_inset.set_ylim(-90, 90)
    ax_inset.set_aspect('equal', adjustable='box')
    ax_inset.set_title('Global Context', fontsize=11, fontweight='bold', pad=8)
    ax_inset.set_xticks([])
    ax_inset.set_yticks([])
    
    # Add orange border
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
    print(f"   - Tajikistan highlighted in RED (simple rectangular approximation)")
    print(f"   - Didal Glacier location marked at ({GLACIER_LAT}°N, {GLACIER_LON}°E)")
    print(f"   - World map inset with region box")
    print(f"   - Orange border around figure")

if __name__ == "__main__":
    create_regional_map_figure()

