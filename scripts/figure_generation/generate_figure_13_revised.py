#!/usr/bin/env python3
"""
Generate Revised Figure 13 (H3 Analysis) - Vector PDF
Simplified 2-panel layout for Q1 journal publication.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import rcParams
from pathlib import Path
from datetime import datetime, timedelta
import warnings
import calendar

# Suppress warnings

# Suppress warnings
warnings.filterwarnings('ignore')

# Set publication-quality matplotlib parameters for vector output
rcParams['font.family'] = 'sans-serif'
rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
rcParams['font.size'] = 14
rcParams['axes.labelsize'] = 16
rcParams['axes.titlesize'] = 16
rcParams['xtick.labelsize'] = 14
rcParams['ytick.labelsize'] = 14
rcParams['legend.fontsize'] = 14
rcParams['figure.titlesize'] = 18
rcParams['axes.linewidth'] = 1.0
rcParams['grid.linewidth'] = 0.5
rcParams['lines.linewidth'] = 1.5
rcParams['lines.markersize'] = 6
rcParams['pdf.fonttype'] = 42  # Ensure text is editable in Illustrator/Inkscape
rcParams['ps.fonttype'] = 42

# Directories
VELOCITY_DIR = Path("satellite_data/sentinel1/processed")
CLIMATE_DIR = Path("satellite_data/era5_land/processed")
OUTPUT_DIR = Path("processed_data/h3_refined_analysis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Publication settings
FIGURE_SIZE = (10, 8)  # Width, Height in inches (fits standard column/page)

def load_data():
    """Load velocity and climate data."""
    print("Loading data...")
    # Load Velocity
    vel_file = VELOCITY_DIR / "velocity_timeseries_python.csv"
    if not vel_file.exists():
        raise FileNotFoundError(f"Velocity file not found: {vel_file}")
    
    vel = pd.read_csv(vel_file)
    vel['date'] = pd.to_datetime(vel['date'])
    vel = vel.sort_values('date').reset_index(drop=True)
    
    # Load Climate
    clim_file = CLIMATE_DIR / "climate_derivatives_timeseries.csv"
    if not clim_file.exists():
        raise FileNotFoundError(f"Climate file not found: {clim_file}")
    
    clim = pd.read_csv(clim_file)
    clim['datetime'] = pd.to_datetime(clim['datetime'])
    clim = clim.sort_values('datetime').reset_index(drop=True)
    
    # Aggregate to daily
    if len(clim) > 365:
        clim['date'] = clim['datetime'].dt.date
        clim_daily = clim.groupby('date').agg({
            'temperature_C': 'mean',
            'precipitation_mm': 'sum',
            'swe_mm': 'mean'
        }).reset_index()
        clim_daily['datetime'] = pd.to_datetime(clim_daily['date'])
        clim_daily['pdd'] = np.maximum(clim_daily['temperature_C'], 0)
    else:
        clim_daily = clim.copy()
        clim_daily['date'] = clim_daily['datetime'].dt.date
        if 'pdd' not in clim_daily.columns:
            clim_daily['pdd'] = np.maximum(clim_daily['temperature_C'], 0)
    
    # --- CRITICAL FIX: Ensure Temperature is in Celsius and Recompute PDD ---
    # Check if temperature is in Kelvin (e.g., mean > 200)
    temp_mean = clim_daily['temperature_C'].mean()
    if temp_mean > 200:
        print(f"Warning: Temperature appears to be in Kelvin (mean={temp_mean:.2f}). Converting to Celsius.")
        clim_daily['temperature_C'] = clim_daily['temperature_C'] - 273.15
    
    # Force re-calculation of PDD to avoid using potentially incorrect pre-existing column
    print("Recalculating PDD from temperature_C...")
    clim_daily['pdd'] = np.maximum(clim_daily['temperature_C'], 0)
    # ------------------------------------------------------------------------
    
    clim_daily = clim_daily.sort_values('datetime')
    print(f"Data loaded. ranges: Vel {vel['date'].min().date()} to {vel['date'].max().date()}, Clim {clim_daily['datetime'].min().date()} to {clim_daily['datetime'].max().date()}")
    return vel, clim_daily

def identify_acceleration_onset(vel):
    """Identify acceleration onset (>300 m/d or first significant increase)."""
    vel_sorted = vel.sort_values('date').reset_index(drop=True)
    high_vel_mask = vel_sorted['velocity_m_per_day'] > 300
    if high_vel_mask.any():
        first_high_vel = vel_sorted[high_vel_mask].iloc[0]
        return first_high_vel['date']
    return vel_sorted['date'].iloc[0]  # Fallback

def calculate_pdd_windows(clim_daily, acceleration_onset, windows=[30, 60, 90, 120]):
    """Calculate cumulative PDD for multiple windows."""
    results = {}
    for window_days in windows:
        window_start = acceleration_onset - timedelta(days=window_days)
        window_mask = (clim_daily['datetime'] >= window_start) & (clim_daily['datetime'] < acceleration_onset)
        pdd_sum = clim_daily[window_mask]['pdd'].sum()
        results[window_days] = pdd_sum
    return results

def identify_ros_events(clim_daily):
    """Identify ROS events."""
    ros_events = []
    for _, row in clim_daily.iterrows():
        # Raised SWE threshold to > 5.0 mm to avoid trace artifacts near onset
        if (row['temperature_C'] > 0.5 and row['precipitation_mm'] > 0.1 and row['swe_mm'] > 5.0):
            ros_intensity = row['precipitation_mm'] * (row['temperature_C'] - 0.5)
            ros_events.append({
                'datetime': row['datetime'],
                'ros_intensity': float(ros_intensity)
            })
    return pd.DataFrame(ros_events)

def create_figure(vel, clim_daily, pdd_results, ros_events, acceleration_onset):
    """Create simplified 2-panel figure."""
    print("Creating figure...")
    
    fig = plt.figure(figsize=FIGURE_SIZE)
    gs = fig.add_gridspec(2, 1, height_ratios=[1, 1], hspace=0.6)
    
    # Colors
    color_pdd = '#E69F00'   # Orange-ish (Colorblind friendly palette: Wong/Okabe-Ito)
    color_swe = '#56B4E9'   # Sky Blue
    color_ros = '#D55E00'   # Vermillion (Red-ish)
    color_onset = '#000000' # Black
    
    # --- Panel A: Cumulative PDD Buildup ---
    ax1 = fig.add_subplot(gs[0])
    
    windows = sorted(pdd_results.keys())
    values = [pdd_results[w] for w in windows]
    labels = [f'{w} days' for w in windows]
    
    bars = ax1.bar(labels, values, color=color_pdd, edgecolor='black', alpha=0.8, width=0.6)
    
    # Add values on top
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + max(values)*0.02,
                f'{height:.0f}', ha='center', va='bottom', fontsize=10)
    
    ax1.set_ylabel('Cumulative PDD (°C·days)')
    ax1.set_xlabel('Time Window Before Acceleration')
    ax1.set_title('(a) Melt Season Preconditioning (PDD Buildup)', loc='left')
    ax1.grid(True, axis='y', alpha=0.3, linestyle='--')
    
    # --- Panel B: SWE Evolution & ROS Events ---
    ax2 = fig.add_subplot(gs[1])
    
    # Plot SWE
    clim_sorted = clim_daily.sort_values('datetime')
    # Filter to relevant period (e.g., Jan 2025 onwards)
    start_date = pd.Timestamp('2025-01-01')
    clim_subset = clim_sorted[clim_sorted['datetime'] >= start_date]
    
    ax2.plot(clim_subset['datetime'], clim_subset['swe_mm'], color=color_swe, linewidth=2, label='SWE (mm)')
    ax2.fill_between(clim_subset['datetime'], clim_subset['swe_mm'], color=color_swe, alpha=0.2)
    
    ax2.set_ylabel('SWE (mm)', color=color_swe)
    ax2.tick_params(axis='y', labelcolor=color_swe)
    
    # Create twin axis for ROS
    ax2_twin = ax2.twinx()
    
    if not ros_events.empty:
        # Filter ROS events to same period
        ros_subset = ros_events[ros_events['datetime'] >= start_date]
        if not ros_subset.empty:
            ax2_twin.scatter(ros_subset['datetime'], ros_subset['ros_intensity'], 
                           color=color_ros, s=50, alpha=0.7, edgecolors='white', linewidth=0.8, 
                           label='ROS proxy index (mm·°C)', zorder=10)
    
    ax2_twin.set_ylabel('ROS proxy index (mm·°C)', color=color_ros)
    ax2_twin.tick_params(axis='y', labelcolor=color_ros)
    
    # Mark Acceleration Onset
    ax2.axvline(acceleration_onset, color=color_onset, linestyle='--', linewidth=1.5, alpha=0.8)
    # Add label for onset
    ax2.text(acceleration_onset + timedelta(days=2), ax2.get_ylim()[1]*0.9, 
             'Surge\nOnset', color=color_onset, ha='left', va='top')

    ax2.set_title('(b) Snow Water Equivalent (SWE) and Rain-on-Snow (ROS) Events', loc='left')
    ax2.set_xlabel('Month (2025)')
    
    # Format X-axis (Robust English Labels)
    months = pd.date_range("2025-01-01", "2025-12-01", freq="MS")
    ax2.set_xticks(months)
    ax2.set_xticklabels([calendar.month_abbr[m.month] for m in months])
    
    # Legend
    # Combine legends from both axes
    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left', frameon=True)
    
    ax2.grid(True, alpha=0.3, linestyle='--')
    
    # --- Save ---
    
    # Save as PDF (Vector)
    pdf_path = OUTPUT_DIR / "figure_13_revised.pdf"
    # plt.tight_layout()
    print(f"Saving PDF to {pdf_path}...")
    plt.savefig(pdf_path, format='pdf', dpi=300)
    print(f"Created PDF: {pdf_path}")
    
    # Save as PNG (Preview)
    png_path = OUTPUT_DIR / "figure_13_revised.png"
    plt.savefig(png_path, format='png', dpi=300)
    print(f"Created PNG Preview: {png_path}")
    
    plt.close()

def main():
    print("Generating Revised Figure 13...")
    vel, clim_daily = load_data()
    onset = identify_acceleration_onset(vel)
    print(f"Acceleration Onset: {onset.date()}")
    
    pdd_results = calculate_pdd_windows(clim_daily, onset)
    ros_events = identify_ros_events(clim_daily)
    
    create_figure(vel, clim_daily, pdd_results, ros_events, onset)
    print("Done.")

if __name__ == "__main__":
    main()
