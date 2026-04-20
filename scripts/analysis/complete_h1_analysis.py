#!/usr/bin/env python3
"""
Phase 3: Complete H1 Analysis - Topographic Pinning Test

This script tests Hypothesis H1:
"The braking transition onset will align spatially with a valley constriction 
or slope break along the glacier centerline (topographic pinning mechanism)."

Approach:
1. Identify braking-onset timing from velocity time series
2. Extract glacier centerline
3. Calculate DEM slope along centerline (using QGIS or alternative)
4. Detect slope breaks and valley constrictions
5. Test spatial alignment (conceptual, since we don't have exact spatial velocity)

Run: python3 complete_h1_analysis.py
"""

import pandas as pd
import numpy as np
import geopandas as gpd
from pathlib import Path
from datetime import datetime
import json
import matplotlib.pyplot as plt
from shapely.geometry import Point, LineString
import warnings
warnings.filterwarnings('ignore')

# Directories
VELOCITY_DIR = Path("satellite_data/sentinel1/processed")
GLACIER_OUTLINE = Path("satellite_data/dem/processed/didal_glacier_rgi_outline.shp")
CENTERLINE_FILE = Path("satellite_data/dem/processed/didal_glacier_centerline.shp")
DEM_DIR = Path("satellite_data/dem/processed")
OUTPUT_DIR = Path("processed_data/h1_analysis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Glacier location
GLACIER_LAT = 38.97
GLACIER_LON = 70.75

def load_velocity_data():
    """Load velocity time series and identify braking onset."""
    print("=" * 70)
    print("LOADING VELOCITY DATA")
    print("=" * 70)
    
    vel_file = VELOCITY_DIR / "velocity_timeseries_python.csv"
    if not vel_file.exists():
        raise FileNotFoundError(f"Velocity file not found: {vel_file}")
    
    vel = pd.read_csv(vel_file)
    vel['date'] = pd.to_datetime(vel['date'])
    vel = vel.sort_values('date').reset_index(drop=True)
    
    print(f"✅ Loaded {len(vel)} velocity measurements")
    
    # Identify braking onset (from previous analysis)
    # Braking onset: first significant velocity decrease
    # From advanced_phase_mechanism_results.json: 2025-09-19
    
    # Find braking onset in velocity data
    vel_sorted = vel.sort_values('date')
    velocity_changes = vel_sorted['velocity_m_per_day'].diff()
    
    # Braking: significant negative change
    braking_threshold = -50  # m/d decrease
    braking_mask = velocity_changes < braking_threshold
    
    if braking_mask.any():
        braking_idx = vel_sorted[braking_mask].index[0]
        braking_date = vel_sorted.loc[braking_idx, 'date']
        braking_velocity = vel_sorted.loc[braking_idx, 'velocity_m_per_day']
    else:
        # Use date from previous analysis
        braking_date = pd.to_datetime('2025-09-19')
        braking_velocity = vel[vel['date'] == braking_date]['velocity_m_per_day'].values[0] if len(vel[vel['date'] == braking_date]) > 0 else None
    
    print(f"\nBraking Onset:")
    print(f"  Date: {braking_date.strftime('%d %B %Y')}")
    print(f"  Velocity: {braking_velocity:.1f} m d⁻¹" if braking_velocity else "  Velocity: N/A")
    
    return vel, braking_date, braking_velocity

def load_centerline():
    """Load glacier centerline."""
    print("\n" + "=" * 70)
    print("LOADING GLACIER CENTERLINE")
    print("=" * 70)
    
    if not CENTERLINE_FILE.exists():
        print("⚠️  Centerline not found. Creating simple centerline...")
        # Run centerline extraction
        import subprocess
        result = subprocess.run(['python3', 'extract_centerline_simple.py'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Error creating centerline: {result.stderr}")
            return None
    
    try:
        centerline_gdf = gpd.read_file(CENTERLINE_FILE)
        centerline = centerline_gdf.iloc[0].geometry
        
        print(f"✅ Loaded centerline")
        print(f"   Type: {type(centerline)}")
        print(f"   Length: {centerline.length * 111:.3f} km (approximate)")
        
        return centerline, centerline_gdf.crs
    except Exception as e:
        print(f"❌ Error loading centerline: {e}")
        return None, None

def analyze_topography_conceptual(centerline, braking_date):
    """
    Conceptual topographic analysis for H1.
    
    Since we can't easily sample DEM with rasterio, we'll:
    1. Use centerline geometry
    2. Identify potential constriction points (narrowest parts)
    3. Use DEM slope/aspect files if available via alternative method
    4. Create a framework for testing alignment
    """
    print("\n" + "=" * 70)
    print("CONCEPTUAL TOPOGRAPHIC ANALYSIS FOR H1")
    print("=" * 70)
    
    if centerline is None:
        print("⚠️  No centerline available")
        return None
    
    # Get centerline coordinates
    coords = list(centerline.coords)
    coords_array = np.array(coords)
    
    # Calculate distances along centerline
    distances = [0]
    for i in range(1, len(coords)):
        dx = (coords[i][0] - coords[i-1][0]) * 111.32 * np.cos(np.radians(coords[i][1]))
        dy = (coords[i][1] - coords[i-1][1]) * 111.32
        dist = np.sqrt(dx**2 + dy**2)
        distances.append(distances[-1] + dist)
    
    distances_km = np.array(distances)
    
    # For small glaciers, we can't easily detect constrictions from geometry alone
    # But we can note the framework for testing
    
    results = {
        'centerline_length_km': float(distances_km[-1]),
        'num_points': len(coords),
        'braking_date': braking_date.strftime('%Y-%m-%d'),
        'analysis_note': 'Topographic analysis requires DEM sampling. For H1 test, we need: 1) Slope profile along centerline, 2) Valley width profile, 3) Spatial velocity at braking onset. Current limitation: SNAP velocity maps are empty, so we test alignment conceptually.'
    }
    
    print(f"\nCenterline Analysis:")
    print(f"  Length: {distances_km[-1]:.3f} km")
    print(f"  Points: {len(coords)}")
    print(f"\n⚠️  Note: Full H1 test requires:")
    print(f"  1. DEM slope profile along centerline")
    print(f"  2. Spatial velocity map at braking onset")
    print(f"  3. Valley constriction mapping")
    print(f"\n  Current status: Framework created, needs DEM sampling")
    
    return results

def create_h1_visualization(vel, braking_date, centerline, results):
    """Create visualization for H1 analysis."""
    print("\n" + "=" * 70)
    print("CREATING H1 VISUALIZATION")
    print("=" * 70)
    
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))
    
    # Panel 1: Velocity time series with braking onset
    ax1 = axes[0]
    ax1.plot(vel['date'], vel['velocity_m_per_day'], 'o-', linewidth=2, 
            markersize=8, color='blue', label='Velocity')
    ax1.axvline(braking_date, color='red', linestyle='--', linewidth=2, 
               label=f'Braking Onset ({braking_date.strftime("%Y-%m-%d")})')
    ax1.set_xlabel('Date', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Velocity (m d⁻¹)', fontsize=11, fontweight='bold')
    ax1.set_title('(a) Velocity Time Series with Braking Onset', fontsize=12, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Panel 2: Centerline visualization (conceptual)
    ax2 = axes[1]
    if centerline:
        coords = np.array(list(centerline.coords))
        ax2.plot(coords[:, 0], coords[:, 1], 'b-', linewidth=3, label='Glacier Centerline')
        ax2.plot(coords[0, 0], coords[0, 1], 'go', markersize=10, label='Head')
        ax2.plot(coords[-1, 0], coords[-1, 1], 'ro', markersize=10, label='Toe')
        ax2.set_xlabel('Longitude (°E)', fontsize=11, fontweight='bold')
        ax2.set_ylabel('Latitude (°N)', fontsize=11, fontweight='bold')
        ax2.set_title('(b) Glacier Centerline (Conceptual H1 Test Framework)', fontsize=12, fontweight='bold')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.set_aspect('equal', adjustable='box')
    else:
        ax2.text(0.5, 0.5, 'Centerline not available', ha='center', va='center',
                transform=ax2.transAxes, fontsize=12)
    
    plt.suptitle('H1 Analysis: Topographic Pinning Test Framework', 
                fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    output_file = OUTPUT_DIR / "h1_analysis_framework.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✅ Visualization saved: {output_file}")
    
    return output_file

def main():
    """Main function."""
    print("=" * 70)
    print("PHASE 3: COMPLETE H1 ANALYSIS - TOPOGRAPHIC PINNING TEST")
    print("=" * 70)
    print()
    
    # Load velocity data
    vel, braking_date, braking_velocity = load_velocity_data()
    
    # Load centerline
    centerline, crs = load_centerline()
    
    # Analyze topography (conceptual)
    topo_results = analyze_topography_conceptual(centerline, braking_date)
    
    # Create visualization
    vis_file = create_h1_visualization(vel, braking_date, centerline, topo_results)
    
    # Save results
    results = {
        'braking_onset': {
            'date': braking_date.strftime('%Y-%m-%d'),
            'velocity_m_per_day': float(braking_velocity) if braking_velocity else None
        },
        'centerline': {
            'available': centerline is not None,
            'length_km': topo_results['centerline_length_km'] if topo_results else None
        },
        'topographic_analysis': topo_results,
        'h1_test_status': 'framework_created',
        'limitations': [
            'SNAP velocity maps are empty (all zeros)',
            'Need DEM sampling along centerline (rasterio library issue)',
            'Full spatial velocity mapping requires alternative approach'
        ],
        'recommendations': [
            'Use QGIS to sample DEM slope along centerline',
            'Create velocity maps using Python-based offset tracking if needed',
            'Test H1 conceptually: braking occurs, test if it aligns with known topographic features'
        ]
    }
    
    results_file = OUTPUT_DIR / "h1_analysis_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved: {results_file}")
    
    print("\n" + "=" * 70)
    print("H1 ANALYSIS SUMMARY")
    print("=" * 70)
    print(f"\nBraking Onset: {braking_date.strftime('%d %B %Y')}")
    print(f"Velocity: {braking_velocity:.1f} m d⁻¹" if braking_velocity else "Velocity: N/A")
    if centerline:
        print(f"Centerline: Available ({topo_results['centerline_length_km']:.3f} km)")
    else:
        print(f"Centerline: Not available")
    print(f"\n⚠️  H1 Test Status: Framework created")
    print(f"   Full test requires DEM sampling and spatial velocity maps")
    print(f"   See recommendations in results file")
    
    print("\n" + "=" * 70)
    print("✅ H1 ANALYSIS FRAMEWORK COMPLETE!")
    print("=" * 70)

if __name__ == "__main__":
    main()

