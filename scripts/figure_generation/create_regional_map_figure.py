#!/usr/bin/env python3
"""
Create regional context map showing Tajikistan highlighted in red
with surrounding countries and a world map inset.
Similar to reference figure style.
"""

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch
import numpy as np
import os

# --- Configuration ---
GLACIER_LAT, GLACIER_LON = 38.97, 70.75
OUTPUT_FILE = 'processed_data/analysis_results/figure_regional_map.png'

# Central Asia region extent (approximate)
CENTRAL_ASIA_EXTENT = {
    'lon_min': 60,   # West
    'lon_max': 80,   # East
    'lat_min': 35,   # South
    'lat_max': 45    # North
}

# Tajikistan approximate boundaries (simplified polygon)
TAJIKISTAN_POLYGON = {
    'lon': [67.4, 70.3, 75.1, 74.2, 73.5, 71.5, 70.5, 68.5, 67.4, 67.4],
    'lat': [36.7, 36.7, 38.5, 39.5, 40.0, 40.5, 40.0, 39.5, 38.5, 36.7]
}

# Neighboring countries (simplified boundaries)
COUNTRIES = {
    'Uzbekistan': {'lon': [56.0, 73.0, 73.0, 66.0, 66.0, 56.0, 56.0], 
                   'lat': [37.0, 37.0, 45.5, 45.5, 41.0, 41.0, 37.0]},
    'Kyrgyzstan': {'lon': [69.0, 80.0, 80.0, 73.0, 69.0, 69.0],
                   'lat': [39.0, 39.0, 43.3, 43.3, 41.0, 39.0]},
    'Kazakhstan': {'lon': [46.0, 87.0, 87.0, 46.0, 46.0],
                   'lat': [40.5, 40.5, 55.5, 55.5, 40.5]},
    'Afghanistan': {'lon': [60.5, 74.9, 74.9, 71.5, 71.5, 60.5, 60.5],
                    'lat': [29.4, 29.4, 38.5, 38.5, 36.7, 36.7, 29.4]},
    'China': {'lon': [73.5, 75.1, 75.1, 104.0, 104.0, 73.5, 73.5],
              'lat': [36.7, 36.7, 40.0, 40.0, 50.0, 50.0, 36.7]},
    'Turkmenistan': {'lon': [52.5, 66.7, 66.7, 56.0, 56.0, 52.5, 52.5],
                     'lat': [35.1, 35.1, 42.8, 42.8, 41.0, 41.0, 35.1]}
}

def create_regional_map_figure():
    """Create regional context map with Tajikistan highlighted."""
    
    fig = plt.figure(figsize=(14, 10))
    
    # Main map (larger)
    ax_main = fig.add_axes([0.1, 0.15, 0.7, 0.75])  # [left, bottom, width, height]
    
    # --- MAIN MAP: Central Asia Region ---
    
    # Draw neighboring countries (light beige/light gray)
    for country_name, coords in COUNTRIES.items():
        ax_main.plot(coords['lon'], coords['lat'], 
                    color='#d4d4d4', linewidth=1, zorder=1)
        ax_main.fill(coords['lon'], coords['lat'], 
                    color='#f5f5f0', alpha=0.7, zorder=0)
    
    # Draw Tajikistan (highlighted in RED)
    ax_main.plot(TAJIKISTAN_POLYGON['lon'], TAJIKISTAN_POLYGON['lat'],
                color='darkred', linewidth=2, zorder=3)
    ax_main.fill(TAJIKISTAN_POLYGON['lon'], TAJIKISTAN_POLYGON['lat'],
                color='red', alpha=0.7, zorder=2, label='Tajikistan')
    
    # Add red point for Didal Glacier
    ax_main.plot(GLACIER_LON, GLACIER_LAT, 'o', 
                color='darkred', markersize=10, 
                markeredgecolor='white', markeredgewidth=2,
                markerfacecolor='red', zorder=5, label='Didal Glacier')
    ax_main.plot(GLACIER_LON, GLACIER_LAT, '+', 
                color='white', markersize=12, 
                markeredgewidth=2, zorder=5)
    
    # Add country labels (optional)
    ax_main.text(68.0, 39.0, 'Tajikistan', fontsize=14, fontweight='bold',
                color='white', ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='red', alpha=0.8),
                zorder=4)
    
    # Set extent
    ax_main.set_xlim(CENTRAL_ASIA_EXTENT['lon_min'], CENTRAL_ASIA_EXTENT['lon_max'])
    ax_main.set_ylim(CENTRAL_ASIA_EXTENT['lat_min'], CENTRAL_ASIA_EXTENT['lat_max'])
    ax_main.set_aspect('equal', adjustable='box')
    
    # Labels and grid
    ax_main.set_xlabel('Longitude (°E)', fontsize=12, fontweight='bold')
    ax_main.set_ylabel('Latitude (°N)', fontsize=12, fontweight='bold')
    ax_main.grid(True, alpha=0.3, linestyle='--', linewidth=0.5, color='gray')
    ax_main.set_facecolor('#e8f4f8')  # Light blue background for water areas
    
    # Add water body labels (optional)
    # Caspian Sea area (approximate)
    ax_main.text(52, 42, 'Caspian\nSea', fontsize=9, 
                ha='center', va='center', color='blue', style='italic')
    
    # Title
    ax_main.set_title('Central Asia - Study Area', 
                     fontsize=16, fontweight='bold', pad=15)
    
    # --- INSET MAP: World Map (Bottom-left) ---
    ax_inset = fig.add_axes([0.15, 0.15, 0.25, 0.2])
    
    # Simple world map outline (approximate)
    world_lon = [-180, 180, 180, -180, -180]
    world_lat = [-90, -90, 90, 90, -90]
    
    # Draw world continents (simplified - just outline)
    ax_inset.plot(world_lon, world_lat, 'k-', linewidth=1.5, zorder=1)
    ax_inset.fill(world_lon, world_lat, color='#f0f0f0', alpha=0.5, zorder=0)
    
    # Highlight Central Asia region with a box
    box_lon = [CENTRAL_ASIA_EXTENT['lon_min'], CENTRAL_ASIA_EXTENT['lon_max'],
               CENTRAL_ASIA_EXTENT['lon_max'], CENTRAL_ASIA_EXTENT['lon_min'],
               CENTRAL_ASIA_EXTENT['lon_min']]
    box_lat = [CENTRAL_ASIA_EXTENT['lat_min'], CENTRAL_ASIA_EXTENT['lat_min'],
               CENTRAL_ASIA_EXTENT['lat_max'], CENTRAL_ASIA_EXTENT['lat_max'],
               CENTRAL_ASIA_EXTENT['lat_min']]
    
    ax_inset.plot(box_lon, box_lat, 'r-', linewidth=2.5, zorder=3, label='Study Area')
    ax_inset.fill(box_lon, box_lat, color='red', alpha=0.3, zorder=2)
    
    # Set world map extent
    ax_inset.set_xlim(-180, 180)
    ax_inset.set_ylim(-90, 90)
    ax_inset.set_aspect('equal', adjustable='box')
    ax_inset.set_title('Global Context', fontsize=10, fontweight='bold')
    ax_inset.set_xticks([])
    ax_inset.set_yticks([])
    ax_inset.set_facecolor('#e8f4f8')
    
    # Add orange border around entire figure
    # Create a fancy box for the border
    border = FancyBboxPatch((0, 0), 1, 1, 
                           transform=fig.transFigure, 
                           boxstyle="round,pad=0.01",
                           edgecolor='orange', 
                           facecolor='none', 
                           linewidth=4, 
                           zorder=100)
    fig.patches.append(border)
    
    # Save figure
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches='tight', 
                facecolor='white', edgecolor='orange', pad_inches=0.1)
    plt.close()
    
    print(f"✅ Regional map figure saved: {OUTPUT_FILE}")
    print(f"   - Tajikistan highlighted in RED")
    print(f"   - Didal Glacier location marked")
    print(f"   - World map inset with region box")
    print(f"   - Orange border around figure")
    return True

if __name__ == "__main__":
    create_regional_map_figure()

