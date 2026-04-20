#!/usr/bin/env python3
"""
Advanced Phase Boundary Detection and Mechanism Testing

This script performs:
1. Phase boundary detection (acceleration onset, peak, braking onset)
2. H1: Map braking-onset position to centerline; compare to DEM slope break/valley constriction
3. H2: Compute acceleration and jerk; define jerk windows; test temporal alignment with ROS
4. H3: Compute cumulative PDD/SWE leading up to acceleration; test if buildup precedes acceleration

Run: python3 advanced_phase_mechanism_analysis.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
from datetime import datetime, timedelta
import json
from scipy import signal
from scipy.stats import pearsonr
import warnings
warnings.filterwarnings('ignore')

# Directories
PROCESSED_DIR = Path("satellite_data/sentinel1/processed")
CLIMATE_DIR = Path("satellite_data/era5_land/processed")
DEM_DIR = Path("satellite_data/dem/processed")
ANALYSIS_DIR = Path("satellite_data/analysis")
OUTPUT_DIR = Path("processed_data/advanced_analysis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_data():
    """Load velocity and climate data."""
    print("Loading data...")
    
    # Velocity
    vel_file = PROCESSED_DIR / "velocity_timeseries_python.csv"
    if not vel_file.exists():
        raise FileNotFoundError(f"Velocity file not found: {vel_file}")
    
    vel = pd.read_csv(vel_file)
    vel['date'] = pd.to_datetime(vel['date'])
    vel = vel.sort_values('date').reset_index(drop=True)
    
    # Climate
    climate_file = CLIMATE_DIR / "climate_derivatives_timeseries.csv"
    if not climate_file.exists():
        raise FileNotFoundError(f"Climate file not found: {climate_file}")
    
    clim = pd.read_csv(climate_file)
    clim['datetime'] = pd.to_datetime(clim['datetime'])
    clim = clim.sort_values('datetime').reset_index(drop=True)
    
    print(f"✅ Velocity: {len(vel)} measurements")
    print(f"✅ Climate: {len(clim)} time steps")
    
    return vel, clim

def detect_phase_boundaries(vel):
    """
    Detect phase boundaries using multiple methods:
    1. Peak detection (simple max)
    2. Acceleration/deceleration analysis
    3. Manual breakpoints based on velocity changes
    """
    print("\n" + "="*70)
    print("1. PHASE BOUNDARY DETECTION")
    print("="*70)
    
    results = {}
    
    # Method 1: Peak velocity
    peak_idx = vel['velocity_m_per_day'].idxmax()
    peak_date = vel.loc[peak_idx, 'date']
    peak_vel = vel.loc[peak_idx, 'velocity_m_per_day']
    
    results['peak'] = {
        'date': peak_date.strftime('%Y-%m-%d'),
        'velocity': float(peak_vel),
        'index': int(peak_idx)
    }
    
    print(f"\nPeak Velocity:")
    print(f"  Date: {peak_date.strftime('%d %B %Y')}")
    print(f"  Velocity: {peak_vel:.1f} m d⁻¹")
    
    # Method 2: Acceleration analysis
    # Compute acceleration (derivative of velocity)
    vel_sorted = vel.sort_values('date').reset_index(drop=True)
    time_days = (vel_sorted['date'] - vel_sorted['date'].iloc[0]).dt.total_seconds() / 86400
    velocities = vel_sorted['velocity_m_per_day'].values
    
    # Compute acceleration (m d⁻²)
    if len(velocities) > 1:
        dt = np.diff(time_days.values)
        acceleration = np.diff(velocities) / dt
        acceleration_dates = vel_sorted['date'].iloc[1:].values
        
        # Find acceleration peaks (positive) and deceleration peaks (negative)
        accel_peaks, _ = signal.find_peaks(acceleration, height=0)
        decel_peaks, _ = signal.find_peaks(-acceleration, height=0)
        
        # Convert dates to strings
        accel_peaks_dates = [pd.to_datetime(acceleration_dates[i]).strftime('%Y-%m-%d') for i in accel_peaks]
        decel_peaks_dates = [pd.to_datetime(acceleration_dates[i]).strftime('%Y-%m-%d') for i in decel_peaks]
        
        results['acceleration'] = {
            'mean': float(np.mean(acceleration)),
            'std': float(np.std(acceleration)),
            'max': float(np.max(acceleration)),
            'min': float(np.min(acceleration)),
            'accel_peaks': accel_peaks_dates,
            'decel_peaks': decel_peaks_dates
        }
        
        print(f"\nAcceleration Analysis:")
        print(f"  Mean: {np.mean(acceleration):.2f} m d⁻²")
        print(f"  Max: {np.max(acceleration):.2f} m d⁻²")
        print(f"  Min: {np.min(acceleration):.2f} m d⁻²")
        if len(accel_peaks) > 0:
            print(f"  Acceleration peaks: {len(accel_peaks)}")
        if len(decel_peaks) > 0:
            print(f"  Deceleration peaks: {len(decel_peaks)}")
    
    # Method 3: Manual breakpoints based on velocity changes
    # Define phases based on velocity thresholds
    mean_vel = velocities.mean()
    std_vel = velocities.std()
    
    # High velocity: > mean + 0.5*std
    # Low velocity: < mean - 0.5*std
    high_threshold = mean_vel + 0.5 * std_vel
    low_threshold = mean_vel - 0.5 * std_vel
    
    high_vel_mask = velocities > high_threshold
    low_vel_mask = velocities < low_threshold
    
    # Find transitions
    transitions = []
    for i in range(1, len(high_vel_mask)):
        if high_vel_mask[i] != high_vel_mask[i-1]:
            transitions.append({
                'date': pd.to_datetime(vel_sorted.loc[i, 'date']).strftime('%Y-%m-%d'),
                'type': 'high_to_low' if not high_vel_mask[i] else 'low_to_high',
                'velocity': float(vel_sorted.loc[i, 'velocity_m_per_day'])
            })
    
    results['transitions'] = transitions
    results['thresholds'] = {
        'high': float(high_threshold),
        'low': float(low_threshold),
        'mean': float(mean_vel),
        'std': float(std_vel)
    }
    
    print(f"\nVelocity Transitions:")
    print(f"  High threshold: {high_threshold:.1f} m d⁻¹")
    print(f"  Low threshold: {low_threshold:.1f} m d⁻¹")
    print(f"  Transitions: {len(transitions)}")
    
    # Identify potential phases
    # Acceleration onset: first significant increase
    # Braking onset: first significant decrease after peak
    
    if len(transitions) > 0:
        # Find first low-to-high (potential acceleration onset)
        accel_onsets = [t for t in transitions if t['type'] == 'low_to_high']
        if accel_onsets:
            results['acceleration_onset'] = accel_onsets[0]
            print(f"\n  Acceleration onset: {accel_onsets[0]['date']}")
        
        # Find first high-to-low after peak (potential braking onset)
        peak_date_obj = pd.to_datetime(results['peak']['date'])
        braking_onsets = [t for t in transitions 
                          if t['type'] == 'high_to_low' 
                          and pd.to_datetime(t['date']) > peak_date_obj]
        if braking_onsets:
            results['braking_onset'] = braking_onsets[0]
            print(f"  Braking onset: {braking_onsets[0]['date']}")
    
    return results, acceleration, acceleration_dates if len(velocities) > 1 else None, None

def h1_topographic_analysis(vel, dem_dir):
    """
    H1: Map braking-onset position to centerline; compare to DEM slope break/valley constriction.
    
    Note: This requires spatial velocity data along the centerline.
    For now, we'll analyze the single-point location and note limitations.
    """
    print("\n" + "="*70)
    print("2. H1: TOPOGRAPHIC PINNING ANALYSIS")
    print("="*70)
    
    results = {
        'status': 'limited',
        'note': 'Single-point velocity measurements; spatial analysis needed for full H1 test'
    }
    
    # Check for slope data
    slope_file = dem_dir / "slope.tif"
    if slope_file.exists():
        try:
            import rasterio
            with rasterio.open(slope_file) as src:
                # Get glacier location (38.97°N, 70.75°E)
                lon, lat = 70.75, 38.97
                row, col = src.index(lon, lat)
                
                # Read slope at this location
                window = rasterio.windows.Window(col-1, row-1, 3, 3)
                slope_data = src.read(1, window=window)
                mean_slope = np.nanmean(slope_data)
                
                results['slope_at_location'] = {
                    'mean_deg': float(mean_slope),
                    'lon': lon,
                    'lat': lat
                }
                
                print(f"\nSlope at glacier location ({lat}°N, {lon}°E):")
                print(f"  Mean slope: {mean_slope:.1f}°")
        except Exception as e:
            print(f"⚠️  Could not read slope data: {e}")
            results['slope_error'] = str(e)
    else:
        print("⚠️  Slope file not found")
    
    # Identify braking onset from phase analysis
    # (Will be filled in after phase detection)
    results['braking_onset_date'] = None
    results['braking_onset_velocity'] = None
    
    print("\n⚠️  Full H1 test requires:")
    print("  - Spatial velocity fields along centerline")
    print("  - Centerline extraction from DEM")
    print("  - Slope profile along centerline")
    print("  - Valley width profile")
    print("  - Comparison of braking-onset position with topographic features")
    
    return results

def h2_acceleration_jerk_analysis(vel, clim):
    """
    H2: Compute acceleration and jerk; define jerk windows; 
    test temporal alignment with ROS/liquid precipitation anomalies.
    """
    print("\n" + "="*70)
    print("3. H2: ACCELERATION AND JERK ANALYSIS")
    print("="*70)
    
    results = {}
    
    # Sort velocity by date
    vel_sorted = vel.sort_values('date').reset_index(drop=True)
    time_days = (vel_sorted['date'] - vel_sorted['date'].iloc[0]).dt.total_seconds() / 86400
    velocities = vel_sorted['velocity_m_per_day'].values
    
    # Compute acceleration (m d⁻²)
    if len(velocities) < 2:
        print("⚠️  Insufficient data for acceleration analysis")
        return results
    
    dt = np.diff(time_days.values)
    acceleration = np.diff(velocities) / dt
    acceleration_dates = vel_sorted['date'].iloc[1:].values
    
    # Compute jerk (derivative of acceleration, m d⁻³)
    if len(acceleration) > 1:
        dt_jerk = np.diff(time_days.iloc[1:].values)
        jerk = np.diff(acceleration) / dt_jerk
        jerk_dates = vel_sorted['date'].iloc[2:].values
        
        results['jerk'] = {
            'mean': float(np.nanmean(jerk)),
            'std': float(np.nanstd(jerk)),
            'max': float(np.nanmax(jerk)),
            'min': float(np.nanmin(jerk)),
            'dates': [pd.to_datetime(d).strftime('%Y-%m-%d') for d in jerk_dates],
            'values': [float(v) for v in jerk]
        }
        
        print(f"\nJerk Statistics:")
        print(f"  Mean: {np.nanmean(jerk):.2f} m d⁻³")
        print(f"  Std: {np.nanstd(jerk):.2f} m d⁻³")
        print(f"  Max: {np.nanmax(jerk):.2f} m d⁻³")
        print(f"  Min: {np.nanmin(jerk):.2f} m d⁻³")
        
        # Define jerk windows (periods of high |jerk|)
        jerk_abs = np.abs(jerk)
        jerk_threshold = np.nanmean(jerk_abs) + np.nanstd(jerk_abs)
        
        jerk_windows = []
        in_window = False
        window_start = None
        
        for i, (date, j_val) in enumerate(zip(jerk_dates, jerk_abs)):
            date_pd = pd.to_datetime(date)
            if j_val > jerk_threshold:
                if not in_window:
                    window_start = date_pd
                    in_window = True
            else:
                if in_window:
                    jerk_windows.append({
                        'start': window_start.strftime('%Y-%m-%d'),
                        'end': pd.to_datetime(jerk_dates[i-1]).strftime('%Y-%m-%d'),
                        'max_jerk': float(np.max(jerk_abs[i-(i-1):i+1]))
                    })
                    in_window = False
        
        if in_window:
            jerk_windows.append({
                'start': window_start.strftime('%Y-%m-%d'),
                'end': pd.to_datetime(jerk_dates[-1]).strftime('%Y-%m-%d'),
                'max_jerk': float(jerk_abs[-1])
            })
        
        results['jerk_windows'] = jerk_windows
        results['jerk_threshold'] = float(jerk_threshold)
        
        print(f"\nJerk Windows (|jerk| > {jerk_threshold:.2f} m d⁻³):")
        for i, window in enumerate(jerk_windows, 1):
            print(f"  Window {i}: {window['start']} to {window['end']} (max |jerk|: {window['max_jerk']:.2f})")
        
        # Align jerk windows with ROS events
        # Get ROS data for velocity measurement dates
        clim_daily = clim.groupby(clim['datetime'].dt.date).agg({
            'ros': 'sum',
            'precipitation_mm': 'sum',
            'temperature_C': 'mean'
        }).reset_index()
        clim_daily['date'] = pd.to_datetime(clim_daily['datetime'])
        
        # For each jerk window, find ROS events
        jerk_ros_alignment = []
        for window in jerk_windows:
            window_start = pd.to_datetime(window['start'])
            window_end = pd.to_datetime(window['end'])
            
            # Get ROS events in this window
            window_clim = clim_daily[
                (clim_daily['date'] >= window_start) & 
                (clim_daily['date'] <= window_end)
            ]
            
            ros_sum = window_clim['ros'].sum()
            ros_events = (window_clim['ros'] > 1.0).sum()  # Events > 1mm
            
            jerk_ros_alignment.append({
                'window': window,
                'ros_sum': float(ros_sum),
                'ros_events': int(ros_events),
                'precipitation_sum': float(window_clim['precipitation_mm'].sum())
            })
        
        results['jerk_ros_alignment'] = jerk_ros_alignment
        
        print(f"\nJerk Window - ROS Alignment:")
        for i, align in enumerate(jerk_ros_alignment, 1):
            print(f"  Window {i}:")
            print(f"    ROS sum: {align['ros_sum']:.2f} mm")
            print(f"    ROS events (>1mm): {align['ros_events']}")
            print(f"    Total precipitation: {align['precipitation_sum']:.2f} mm")
        
        # Statistical test: correlation between |jerk| and ROS
        # Interpolate ROS to jerk dates
        jerk_dates_pd = [pd.to_datetime(d) for d in jerk_dates]
        ros_interp = np.interp(
            [(d - jerk_dates_pd[0]).total_seconds() / 86400 for d in jerk_dates_pd],
            [(d - clim_daily['date'].iloc[0]).total_seconds() / 86400 for d in clim_daily['date']],
            clim_daily['ros'].values
        )
        
        if len(jerk) == len(ros_interp):
            corr, p_value = pearsonr(np.abs(jerk), ros_interp)
            results['jerk_ros_correlation'] = {
                'correlation': float(corr),
                'p_value': float(p_value)
            }
            
            print(f"\nJerk-ROS Correlation:")
            print(f"  Correlation: {corr:.3f}")
            print(f"  p-value: {p_value:.4f}")
    
    results['acceleration'] = {
        'mean': float(np.nanmean(acceleration)),
        'std': float(np.nanstd(acceleration)),
        'max': float(np.nanmax(acceleration)),
        'min': float(np.nanmin(acceleration)),
        'dates': [pd.to_datetime(d).strftime('%Y-%m-%d') for d in acceleration_dates],
        'values': [float(v) for v in acceleration]
    }
    
    return results

def h3_pdd_swe_buildup(vel, clim):
    """
    H3: Compute cumulative PDD/SWE leading up to acceleration; 
    test if buildup precedes acceleration and ROS aligns with regime shifts.
    """
    print("\n" + "="*70)
    print("4. H3: PDD/SWE BUILDUP ANALYSIS")
    print("="*70)
    
    results = {}
    
    # Get first velocity measurement date (earliest observation)
    first_vel_date = vel['date'].min()
    
    # Get climate data before first velocity measurement
    clim_before = clim[clim['datetime'] < first_vel_date].copy()
    
    if len(clim_before) == 0:
        print("⚠️  No climate data before first velocity measurement")
        return results
    
    # Compute cumulative PDD from start of year
    year_start = pd.Timestamp(f"{first_vel_date.year}-01-01")
    clim_year = clim[clim['datetime'] >= year_start].copy()
    
    # PDD column is hourly PDD (max(T, 0)), so sum by day
    clim_daily = clim_year.groupby(clim_year['datetime'].dt.date).agg({
        'pdd': 'sum',  # Sum hourly PDD to get daily PDD
        'swe_mm': 'last'  # Take last value of day for SWE
    }).reset_index()
    clim_daily.columns = ['date', 'pdd_daily', 'swe_mm']
    clim_daily['date'] = pd.to_datetime(clim_daily['date'])
    clim_daily['pdd_cumulative'] = clim_daily['pdd_daily'].cumsum()
    
    # Use daily aggregated data
    clim_year_daily = clim_daily
    
    # SWE evolution
    swe_max = clim_year_daily['swe_mm'].max()
    swe_max_date = clim_year_daily.loc[clim_year_daily['swe_mm'].idxmax(), 'date']
    
    # PDD/SWE at first velocity measurement
    first_vel_clim = clim_year_daily[clim_year_daily['date'] <= first_vel_date]
    if len(first_vel_clim) > 0:
        pdd_at_first_vel = first_vel_clim['pdd_cumulative'].iloc[-1]
        swe_at_first_vel = first_vel_clim['swe_mm'].iloc[-1]
        
        results['at_first_velocity'] = {
            'date': first_vel_date.strftime('%Y-%m-%d'),
            'pdd_cumulative': float(pdd_at_first_vel),
            'swe_mm': float(swe_at_first_vel)
        }
        
        print(f"\nAt First Velocity Measurement ({first_vel_date.strftime('%d %B %Y')}):")
        print(f"  Cumulative PDD: {pdd_at_first_vel:.0f} °C·days")
        print(f"  SWE: {swe_at_first_vel:.1f} mm")
    
    # PDD/SWE buildup before first velocity
    days_before = 30  # Look back 30 days
    lookback_date = first_vel_date - pd.Timedelta(days=days_before)
    clim_lookback = clim_year_daily[
        (clim_year_daily['date'] >= lookback_date) & 
        (clim_year_daily['date'] <= first_vel_date)
    ]
    
    if len(clim_lookback) > 0:
        pdd_buildup = clim_lookback['pdd_daily'].sum()
        swe_change = clim_lookback['swe_mm'].iloc[-1] - clim_lookback['swe_mm'].iloc[0]
        
        results['buildup_30days'] = {
            'pdd_buildup': float(pdd_buildup),
            'swe_change': float(swe_change),
            'period': f"{lookback_date.strftime('%Y-%m-%d')} to {first_vel_date.strftime('%Y-%m-%d')}"
        }
        
        print(f"\nPDD/SWE Buildup (30 days before first velocity):")
        print(f"  PDD buildup: {pdd_buildup:.0f} °C·days")
        print(f"  SWE change: {swe_change:.1f} mm")
    
    # Test if PDD/SWE buildup precedes acceleration
    # Since we don't have pre-surge baseline, we'll check if buildup occurred
    # before the observation period
    
    results['swe_max'] = {
        'value': float(swe_max),
        'date': swe_max_date.strftime('%Y-%m-%d')
    }
    
    print(f"\nSWE Maximum:")
    print(f"  Value: {swe_max:.1f} mm")
    print(f"  Date: {swe_max_date.strftime('%d %B %Y')}")
    
    # Check if SWE max occurred before first velocity
    if swe_max_date < first_vel_date:
        results['swe_max_before_observation'] = True
        print(f"  ✅ SWE max occurred before first velocity measurement")
    else:
        results['swe_max_before_observation'] = False
        print(f"  ⚠️  SWE max occurred after first velocity measurement")
    
    # ROS alignment with regime shifts
    # Get ROS events around velocity measurements
    vel_dates = vel['date'].values
    ros_events_near_vel = []
    
    for vel_date in vel_dates:
        window_start = vel_date - pd.Timedelta(days=3)
        window_end = vel_date + pd.Timedelta(days=3)
        
        window_clim = clim[
            (clim['datetime'] >= window_start) & 
            (clim['datetime'] <= window_end)
        ]
        
        ros_sum = window_clim['ros'].sum()
        ros_events_near_vel.append({
            'velocity_date': pd.to_datetime(vel_date).strftime('%Y-%m-%d'),
            'ros_sum': float(ros_sum),
            'ros_events': int((window_clim['ros'] > 1.0).sum())
        })
    
    results['ros_near_velocity'] = ros_events_near_vel
    
    print(f"\nROS Events Near Velocity Measurements (±3 days):")
    for event in ros_events_near_vel[:5]:  # Show first 5
        print(f"  {event['velocity_date']}: ROS sum = {event['ros_sum']:.2f} mm, events = {event['ros_events']}")
    
    return results

def create_visualizations(vel, clim, phase_results, h2_results, h3_results):
    """Create visualization figures."""
    print("\n" + "="*70)
    print("Creating Visualizations")
    print("="*70)
    
    fig, axes = plt.subplots(4, 1, figsize=(12, 14))
    
    # 1. Velocity time series with phase boundaries
    ax1 = axes[0]
    ax1.plot(vel['date'], vel['velocity_m_per_day'], 'o-', linewidth=2, markersize=8, label='Velocity')
    
    # Mark peak
    if 'peak' in phase_results:
        peak_date = pd.to_datetime(phase_results['peak']['date'])
        peak_vel = phase_results['peak']['velocity']
        ax1.plot(peak_date, peak_vel, 'r*', markersize=15, label='Peak Velocity')
    
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Velocity (m d⁻¹)')
    ax1.set_title('Velocity Time Series with Phase Boundaries')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
    
    # 2. Acceleration and jerk
    ax2 = axes[1]
    if 'acceleration' in h2_results and h2_results['acceleration']['dates']:
        accel_dates = pd.to_datetime(h2_results['acceleration']['dates'])
        accel_vals = h2_results['acceleration']['values']
        ax2.plot(accel_dates, accel_vals, 'o-', linewidth=2, markersize=6, label='Acceleration', color='orange')
        ax2.axhline(0, color='k', linestyle='--', alpha=0.3)
        ax2.set_ylabel('Acceleration (m d⁻²)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
    
    # 3. Jerk with ROS overlay
    ax3 = axes[2]
    if 'jerk' in h2_results and h2_results['jerk']['dates']:
        jerk_dates = pd.to_datetime(h2_results['jerk']['dates'])
        jerk_vals = h2_results['jerk']['values']
        ax3.plot(jerk_dates, jerk_vals, 'o-', linewidth=2, markersize=6, label='Jerk', color='green')
        ax3.axhline(0, color='k', linestyle='--', alpha=0.3)
        
        # Add ROS events
        clim_daily = clim.groupby(clim['datetime'].dt.date).agg({'ros': 'sum'}).reset_index()
        clim_daily['date'] = pd.to_datetime(clim_daily['datetime'])
        ax3_twin = ax3.twinx()
        ax3_twin.bar(clim_daily['date'], clim_daily['ros'], alpha=0.3, color='blue', label='ROS (mm)')
        ax3_twin.set_ylabel('ROS (mm)', color='blue')
        ax3_twin.tick_params(axis='y', labelcolor='blue')
        
        ax3.set_ylabel('Jerk (m d⁻³)', color='green')
        ax3.tick_params(axis='y', labelcolor='green')
        ax3.legend(loc='upper left')
        ax3_twin.legend(loc='upper right')
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
    
    # 4. Cumulative PDD and SWE
    ax4 = axes[3]
    first_vel_date = vel['date'].min()
    year_start = pd.Timestamp(f"{first_vel_date.year}-01-01")
    clim_year_subset = clim[clim['datetime'] >= year_start].copy()
    
    # Aggregate to daily
    clim_daily_viz = clim_year_subset.groupby(clim_year_subset['datetime'].dt.date).agg({
        'pdd': 'sum',
        'swe_mm': 'last'
    }).reset_index()
    clim_daily_viz.columns = ['date', 'pdd_daily', 'swe_mm']
    clim_daily_viz['date'] = pd.to_datetime(clim_daily_viz['date'])
    clim_daily_viz['pdd_cumulative'] = clim_daily_viz['pdd_daily'].cumsum()
    
    ax4.plot(clim_daily_viz['date'], clim_daily_viz['pdd_cumulative'], linewidth=2, label='Cumulative PDD', color='red')
    ax4_twin = ax4.twinx()
    ax4_twin.plot(clim_daily_viz['date'], clim_daily_viz['swe_mm'], linewidth=2, label='SWE', color='blue')
    
    # Mark first velocity date
    ax4.axvline(first_vel_date, color='k', linestyle='--', alpha=0.5, label='First Velocity Measurement')
    
    ax4.set_xlabel('Date')
    ax4.set_ylabel('Cumulative PDD (°C·days)', color='red')
    ax4.tick_params(axis='y', labelcolor='red')
    ax4_twin.set_ylabel('SWE (mm)', color='blue')
    ax4_twin.tick_params(axis='y', labelcolor='blue')
    ax4.legend(loc='upper left')
    ax4_twin.legend(loc='upper right')
    ax4.grid(True, alpha=0.3)
    ax4.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
    
    plt.tight_layout()
    output_file = OUTPUT_DIR / "advanced_phase_mechanism_analysis.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Figure saved: {output_file}")
    plt.close()

def main():
    """Main execution function."""
    print("="*70)
    print("Advanced Phase Boundary Detection and Mechanism Testing")
    print("="*70)
    
    # Load data
    vel, clim = load_data()
    
    # 1. Phase boundary detection
    phase_results, acceleration, accel_dates, _ = detect_phase_boundaries(vel)
    
    # 2. H1: Topographic analysis
    h1_results = h1_topographic_analysis(vel, DEM_DIR)
    h1_results['braking_onset_date'] = phase_results.get('braking_onset', {}).get('date')
    h1_results['braking_onset_velocity'] = phase_results.get('braking_onset', {}).get('velocity')
    
    # 3. H2: Acceleration and jerk analysis
    h2_results = h2_acceleration_jerk_analysis(vel, clim)
    
    # 4. H3: PDD/SWE buildup analysis
    h3_results = h3_pdd_swe_buildup(vel, clim)
    
    # Create visualizations
    create_visualizations(vel, clim, phase_results, h2_results, h3_results)
    
    # Save results
    all_results = {
        'phase_boundaries': phase_results,
        'h1_topographic': h1_results,
        'h2_acceleration_jerk': h2_results,
        'h3_pdd_swe_buildup': h3_results,
        'metadata': {
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'velocity_count': len(vel),
            'climate_count': len(clim)
        }
    }
    
    results_file = OUTPUT_DIR / "advanced_phase_mechanism_results.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\n✅ Results saved: {results_file}")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"\n1. Phase Boundaries:")
    print(f"   Peak: {phase_results['peak']['date']} ({phase_results['peak']['velocity']:.1f} m d⁻¹)")
    if 'acceleration_onset' in phase_results:
        print(f"   Acceleration onset: {phase_results['acceleration_onset']['date']}")
    if 'braking_onset' in phase_results:
        print(f"   Braking onset: {phase_results['braking_onset']['date']}")
    
    print(f"\n2. H1 (Topographic Pinning):")
    print(f"   Status: {h1_results['status']}")
    if 'slope_at_location' in h1_results:
        print(f"   Slope at location: {h1_results['slope_at_location']['mean_deg']:.1f}°")
    
    print(f"\n3. H2 (Acceleration/Jerk):")
    if 'jerk_windows' in h2_results:
        print(f"   Jerk windows: {len(h2_results['jerk_windows'])}")
    if 'jerk_ros_correlation' in h2_results:
        corr = h2_results['jerk_ros_correlation']['correlation']
        print(f"   Jerk-ROS correlation: {corr:.3f}")
    
    print(f"\n4. H3 (PDD/SWE Buildup):")
    if 'at_first_velocity' in h3_results:
        print(f"   PDD at first velocity: {h3_results['at_first_velocity']['pdd_cumulative']:.0f} °C·days")
    if 'swe_max' in h3_results:
        print(f"   SWE max: {h3_results['swe_max']['value']:.1f} mm on {h3_results['swe_max']['date']}")
    
    print("\n✅ Analysis complete!")

if __name__ == '__main__':
    main()

