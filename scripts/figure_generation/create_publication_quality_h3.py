#!/usr/bin/env python3
"""
Create Publication-Quality H3 Analysis Figure
Improves styling, resolution, and layout for Q1 journal publication
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import rcParams
from pathlib import Path
from datetime import datetime, timedelta
import json
import warnings
warnings.filterwarnings('ignore')

# Set publication-quality matplotlib parameters
rcParams['font.family'] = 'sans-serif'
rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
rcParams['font.size'] = 11
rcParams['axes.labelsize'] = 12
rcParams['axes.titlesize'] = 13
rcParams['xtick.labelsize'] = 10
rcParams['ytick.labelsize'] = 10
rcParams['legend.fontsize'] = 10
rcParams['figure.titlesize'] = 14
rcParams['axes.linewidth'] = 1.2
rcParams['grid.linewidth'] = 0.8
rcParams['lines.linewidth'] = 2.5
rcParams['lines.markersize'] = 8
rcParams['xtick.major.width'] = 1.2
rcParams['ytick.major.width'] = 1.2

# Directories
VELOCITY_DIR = Path("satellite_data/sentinel1/processed")
CLIMATE_DIR = Path("satellite_data/era5_land/processed")
OUTPUT_DIR = Path("processed_data/h3_refined_analysis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Publication settings
PUBLICATION_DPI = 600
FIGURE_SIZE = (14, 10)  # inches

def load_data():
    """Load velocity and climate data."""
    vel_file = VELOCITY_DIR / "velocity_timeseries_python.csv"
    if not vel_file.exists():
        raise FileNotFoundError(f"Velocity file not found: {vel_file}")
    
    vel = pd.read_csv(vel_file)
    vel['date'] = pd.to_datetime(vel['date'])
    vel = vel.sort_values('date').reset_index(drop=True)
    
    clim_file = CLIMATE_DIR / "climate_derivatives_timeseries.csv"
    if not clim_file.exists():
        raise FileNotFoundError(f"Climate file not found: {clim_file}")
    
    clim = pd.read_csv(clim_file)
    clim['datetime'] = pd.to_datetime(clim['datetime'])
    clim = clim.sort_values('datetime').reset_index(drop=True)
    
    # Aggregate to daily if hourly
    if len(clim) > 365:
        clim['date'] = clim['datetime'].dt.date
        clim_daily = clim.groupby('date').agg({
            'temperature_C': 'mean',
            'precipitation_mm': 'sum',
            'swe_mm': 'mean'
        }).reset_index()
        clim_daily['datetime'] = pd.to_datetime(clim_daily['date'])
        
        # Calculate PDD
        clim_daily['pdd'] = np.maximum(clim_daily['temperature_C'], 0)
    else:
        clim_daily = clim.copy()
        clim_daily['date'] = clim_daily['datetime'].dt.date
        if 'pdd' not in clim_daily.columns:
            clim_daily['pdd'] = np.maximum(clim_daily['temperature_C'], 0)
    
    return vel, clim_daily

def identify_acceleration_onset(vel):
    """Identify acceleration onset."""
    vel_sorted = vel.sort_values('date').reset_index(drop=True)
    high_vel_mask = vel_sorted['velocity_m_per_day'] > 300
    if high_vel_mask.any():
        first_high_vel = vel_sorted[high_vel_mask].iloc[0]
        return first_high_vel['date'], first_high_vel['velocity_m_per_day']
    return vel_sorted['date'].iloc[0], vel_sorted['velocity_m_per_day'].iloc[0]

def calculate_pdd_windows(clim_daily, acceleration_onset, windows=[30, 60, 90, 120, 180]):
    """Calculate cumulative PDD for multiple windows."""
    results = {}
    clim_daily = clim_daily.sort_values('datetime')
    
    for window_days in windows:
        window_start = acceleration_onset - timedelta(days=window_days)
        window_mask = (clim_daily['datetime'] >= window_start) & (clim_daily['datetime'] < acceleration_onset)
        window_data = clim_daily[window_mask]
        
        if len(window_data) > 0:
            pdd_cumulative = window_data['pdd'].sum()
            results[f'{window_days}days'] = {
                'window_start': window_start,
                'window_end': acceleration_onset,
                'window_days': window_days,
                'pdd_cumulative': float(pdd_cumulative)
            }
    
    return results

def identify_swe_max(clim_daily):
    """Identify SWE maximum."""
    swe_max_idx = clim_daily['swe_mm'].idxmax()
    return clim_daily.loc[swe_max_idx, 'datetime'], clim_daily.loc[swe_max_idx, 'swe_mm']

def identify_ros_events(clim_daily):
    """Identify ROS events."""
    ros_events = []
    for idx, row in clim_daily.iterrows():
        if (row['temperature_C'] > 0.5 and row['precipitation_mm'] > 0.1 and row['swe_mm'] > 0.1):
            ros_intensity = row['precipitation_mm'] * (row['temperature_C'] - 0.5)
            ros_events.append({
                'datetime': row['datetime'],
                'ros_intensity': float(ros_intensity),
                'precipitation': float(row['precipitation_mm'])
            })
    return ros_events

def create_publication_quality_figure(vel, clim_daily, pdd_results, acceleration_onset, swe_max_date, swe_max_value, ros_events):
    """Create publication-quality H3 figure."""
    print("\n" + "=" * 70)
    print("CREATING PUBLICATION-QUALITY H3 FIGURE")
    print("=" * 70)
    
    fig = plt.figure(figsize=FIGURE_SIZE, dpi=100)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.2, 1], hspace=0.35, wspace=0.3)
    
    # Professional color scheme
    colors = {
        'velocity': '#2E86AB',      # Blue
        'pdd': '#F18F01',           # Orange
        'swe': '#6A994E',           # Green
        'ros': '#C73E1D',           # Red
        'onset': '#8B0000',         # Dark red
        'grid': '#E0E0E0'           # Light gray
    }
    
    # Panel (a): Cumulative PDD over multiple windows
    ax1 = fig.add_subplot(gs[0, 0])
    
    window_sizes = []
    pdd_values = []
    for window_key, pdd_data in pdd_results.items():
        if pdd_data['pdd_cumulative'] is not None:
            window_sizes.append(pdd_data['window_days'])
            pdd_values.append(pdd_data['pdd_cumulative'])
    
    if window_sizes:
        bars = ax1.bar(window_sizes, pdd_values, color=colors['pdd'], 
                      alpha=0.8, edgecolor='black', linewidth=1.5, width=15)
        # Add value labels on bars
        for i, (size, val) in enumerate(zip(window_sizes, pdd_values)):
            ax1.text(size, val + max(pdd_values)*0.02, f'{val:.0f}',
                    ha='center', va='bottom', fontsize=10)
        
        ax1.set_xlabel('Time Window (days)', fontsize=12)
        ax1.set_ylabel('Cumulative PDD (°C·days)', fontsize=12)
        ax1.set_title('(a) Cumulative Positive Degree Days', 
                      fontsize=13, loc='left', pad=10)
        ax1.grid(True, alpha=0.3, linestyle='--', linewidth=0.8, color=colors['grid'], axis='y')
        ax1.set_facecolor('#FAFAFA')
    
    # Panel (b): SWE evolution
    ax2 = fig.add_subplot(gs[0, 1])
    
    clim_sorted = clim_daily.sort_values('datetime')
    ax2.plot(clim_sorted['datetime'], clim_sorted['swe_mm'], 
             linewidth=2.5, color=colors['swe'], label='SWE', zorder=2)
    
    # Mark SWE maximum
    ax2.plot(swe_max_date, swe_max_value, 'o', markersize=12, 
            color='red', markeredgecolor='darkred', markeredgewidth=2,
            label=f'SWE Max ({swe_max_value:.0f} mm)', zorder=3)
    
    # Mark acceleration onset
    ax2.axvline(acceleration_onset, color=colors['onset'], linestyle='--', 
               linewidth=2.5, label='Surge Onset', zorder=1, alpha=0.8)
    
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel('SWE (mm)', fontsize=12)
    ax2.set_title('(b) Snow Water Equivalent Evolution', 
                  fontsize=13, loc='left', pad=10)
    ax2.legend(loc='upper right', frameon=True, fancybox=True, shadow=True, fontsize=10)
    ax2.grid(True, alpha=0.3, linestyle='--', linewidth=0.8, color=colors['grid'])
    ax2.set_facecolor('#FAFAFA')
    
    # Format x-axis
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=10)
    
    # Panel (c): ROS events
    ax3 = fig.add_subplot(gs[1, :])
    
    if len(ros_events) > 0:
        ros_df = pd.DataFrame(ros_events)
        ax3.scatter(ros_df['datetime'], ros_df['ros_intensity'], 
                   s=100, color=colors['ros'], alpha=0.7, 
                   label='ROS Events', zorder=3, edgecolors='darkred', linewidths=1.5)
        
        # Mark acceleration onset
        ax3.axvline(acceleration_onset, color=colors['onset'], linestyle='--', 
                   linewidth=2.5, label='Surge Onset (13 Sep 2025)', zorder=2, alpha=0.8)
        
        # Highlight ROS clusters
        april_mask = (ros_df['datetime'] >= pd.to_datetime('2025-04-01')) & (ros_df['datetime'] < pd.to_datetime('2025-05-01'))
        may_mask = (ros_df['datetime'] >= pd.to_datetime('2025-05-01')) & (ros_df['datetime'] < pd.to_datetime('2025-06-01'))
        
        if april_mask.any():
            ax3.axvspan(pd.to_datetime('2025-04-01'), pd.to_datetime('2025-05-01'), 
                       alpha=0.1, color='blue', label='April Cluster', zorder=1)
        if may_mask.any():
            ax3.axvspan(pd.to_datetime('2025-05-01'), pd.to_datetime('2025-06-01'), 
                       alpha=0.1, color='purple', label='May Cluster', zorder=1)
    
    ax3.set_xlabel('Date', fontsize=12)
    ax3.set_ylabel('ROS Intensity', fontsize=12)
    ax3.set_title('(c) Rain-on-Snow Events (53 events clustered in April–May 2025)', 
                  fontsize=13, loc='left', pad=10)
    ax3.legend(loc='upper right', frameon=True, fancybox=True, shadow=True, fontsize=10, ncol=2)
    ax3.grid(True, alpha=0.3, linestyle='--', linewidth=0.8, color=colors['grid'])
    ax3.set_facecolor('#FAFAFA')
    
    # Format x-axis
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax3.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=10)
    
    # Overall title
    fig.suptitle('Climate Drivers (H3 Analysis): PDD Buildup, SWE Evolution, and ROS Events', 
                fontsize=14, y=0.98)
    
    # Save at publication quality
    output_file = OUTPUT_DIR / "h3_refined_analysis.png"
    plt.savefig(output_file, dpi=PUBLICATION_DPI, bbox_inches='tight', 
                facecolor='white', edgecolor='none', format='png')
    print(f"\n✅ Publication-quality figure saved: {output_file}")
    print(f"   Resolution: {PUBLICATION_DPI} DPI")
    print(f"   Figure size: {FIGURE_SIZE[0]}×{FIGURE_SIZE[1]} inches")
    
    plt.close()
    return output_file

def main():
    """Main function."""
    print("=" * 70)
    print("CREATING PUBLICATION-QUALITY H3 FIGURE")
    print("=" * 70)
    
    # Load data
    vel, clim_daily = load_data()
    
    # Identify acceleration onset
    acceleration_onset, acceleration_velocity = identify_acceleration_onset(vel)
    print(f"\nAcceleration Onset: {acceleration_onset.strftime('%Y-%m-%d')}")
    
    # Calculate PDD windows
    pdd_results = calculate_pdd_windows(clim_daily, acceleration_onset)
    
    # Identify SWE maximum
    swe_max_date, swe_max_value = identify_swe_max(clim_daily)
    print(f"SWE Maximum: {swe_max_value:.1f} mm on {swe_max_date.strftime('%Y-%m-%d')}")
    
    # Identify ROS events
    ros_events = identify_ros_events(clim_daily)
    print(f"ROS Events: {len(ros_events)} total")
    
    # Create publication-quality figure
    output_file = create_publication_quality_figure(vel, clim_daily, pdd_results, 
                                                     acceleration_onset, swe_max_date, 
                                                     swe_max_value, ros_events)
    
    print("\n" + "=" * 70)
    print("✅ PUBLICATION-QUALITY FIGURE CREATED!")
    print("=" * 70)
    print(f"\nFile: {output_file}")
    print(f"Quality: {PUBLICATION_DPI} DPI (Q1 journal standard)")
    print(f"Ready for: Publication submission")

if __name__ == "__main__":
    main()

