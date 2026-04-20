#!/usr/bin/env python3
"""
Complete H1 and H2 Analysis for Didal Glacier

H1: Topographic Pinning Test
- Extract glacier centerline
- Sample DEM slope along centerline
- Sample velocity along centerline
- Identify slope breaks and valley constrictions
- Test spatial alignment with braking onset

H2: Hydrological Switching Test
- Identify jerk windows (discrete high-motion windows during braking)
- Extract ROS events and liquid precipitation anomalies
- Test temporal alignment between jerk windows and hydrological events

Run: python3 complete_h1_h2_analysis.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timedelta
import json
import warnings
warnings.filterwarnings('ignore')

# Directories
VELOCITY_DIR = Path("satellite_data/sentinel1/processed")
CLIMATE_DIR = Path("satellite_data/era5_land/processed")
DEM_DIR = Path("satellite_data/dem/processed")
GLACIER_OUTLINE = Path("satellite_data/dem/processed/didal_glacier_rgi_outline.shp")
OUTPUT_DIR = Path("processed_data/h1_h2_analysis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Glacier location
GLACIER_LAT = 38.97
GLACIER_LON = 70.75

def load_velocity_timeseries():
    """Load velocity time series."""
    print("=" * 70)
    print("LOADING VELOCITY TIME SERIES")
    print("=" * 70)
    
    vel_file = VELOCITY_DIR / "velocity_timeseries_python.csv"
    if not vel_file.exists():
        raise FileNotFoundError(f"Velocity file not found: {vel_file}")
    
    vel = pd.read_csv(vel_file)
    vel['date'] = pd.to_datetime(vel['date'])
    vel = vel.sort_values('date').reset_index(drop=True)
    
    print(f"✅ Loaded {len(vel)} velocity measurements")
    print(f"   Date range: {vel['date'].min()} to {vel['date'].max()}")
    print(f"   Velocity range: {vel['velocity_m_per_day'].min():.1f} to {vel['velocity_m_per_day'].max():.1f} m/d")
    
    return vel

def identify_braking_phase(vel):
    """Identify braking phase from velocity time series."""
    print("\n" + "=" * 70)
    print("IDENTIFYING BRAKING PHASE")
    print("=" * 70)
    
    vel_sorted = vel.sort_values('date').reset_index(drop=True)
    
    # Calculate acceleration (first derivative)
    vel_sorted['acceleration'] = vel_sorted['velocity_m_per_day'].diff() / vel_sorted['date'].diff().dt.total_seconds() * 86400  # m/d²
    
    # Calculate jerk (second derivative)
    vel_sorted['jerk'] = vel_sorted['acceleration'].diff() / vel_sorted['date'].diff().dt.total_seconds() * 86400  # m/d³
    
    # Identify peak velocity
    peak_idx = vel_sorted['velocity_m_per_day'].idxmax()
    peak_date = vel_sorted.loc[peak_idx, 'date']
    peak_velocity = vel_sorted.loc[peak_idx, 'velocity_m_per_day']
    
    print(f"\nPeak Velocity:")
    print(f"  Date: {peak_date.strftime('%d %B %Y')}")
    print(f"  Velocity: {peak_velocity:.1f} m d⁻¹")
    
    # Braking phase: after peak, when velocity decreases
    braking_mask = vel_sorted['date'] > peak_date
    braking_data = vel_sorted[braking_mask].copy()
    
    if len(braking_data) > 0:
        print(f"\nBraking Phase:")
        print(f"  Start: {braking_data['date'].iloc[0].strftime('%d %B %Y')}")
        print(f"  End: {braking_data['date'].iloc[-1].strftime('%d %B %Y')}")
        print(f"  Duration: {(braking_data['date'].iloc[-1] - braking_data['date'].iloc[0]).days} days")
        print(f"  Mean velocity: {braking_data['velocity_m_per_day'].mean():.1f} m d⁻¹")
        print(f"  Mean deceleration: {braking_data['acceleration'].mean():.1f} m d⁻²")
    else:
        print("\n⚠️  No braking phase identified (all data before peak)")
    
    return vel_sorted, peak_date, braking_data

def identify_jerk_windows(braking_data, threshold_factor=1.5):
    """Identify discrete high-motion windows (jerk windows) during braking."""
    print("\n" + "=" * 70)
    print("IDENTIFYING JERK WINDOWS (H2)")
    print("=" * 70)
    
    if len(braking_data) == 0:
        print("⚠️  No braking phase data available")
        return []
    
    # Calculate mean and std of velocity during braking
    mean_vel = braking_data['velocity_m_per_day'].mean()
    std_vel = braking_data['velocity_m_per_day'].std()
    
    # Jerk window: velocity significantly above mean during braking
    threshold = mean_vel + threshold_factor * std_vel
    
    print(f"\nJerk Window Detection:")
    print(f"  Mean velocity (braking): {mean_vel:.1f} m d⁻¹")
    print(f"  Std velocity: {std_vel:.1f} m d⁻¹")
    print(f"  Threshold: {threshold:.1f} m d⁻¹ (mean + {threshold_factor}×std)")
    
    # Identify jerk windows
    jerk_mask = braking_data['velocity_m_per_day'] > threshold
    jerk_windows = braking_data[jerk_mask].copy()
    
    if len(jerk_windows) > 0:
        print(f"\n✅ Found {len(jerk_windows)} jerk window(s):")
        for idx, row in jerk_windows.iterrows():
            print(f"  {row['date'].strftime('%d %B %Y')}: {row['velocity_m_per_day']:.1f} m d⁻¹")
        
        # Group consecutive dates into windows
        jerk_windows['date_diff'] = jerk_windows['date'].diff()
        jerk_windows['window_id'] = (jerk_windows['date_diff'] > timedelta(days=7)).cumsum()
        
        window_groups = []
        for window_id in jerk_windows['window_id'].unique():
            window_data = jerk_windows[jerk_windows['window_id'] == window_id]
            window_groups.append({
                'window_id': int(window_id),
                'start_date': window_data['date'].min().strftime('%Y-%m-%d'),
                'end_date': window_data['date'].max().strftime('%Y-%m-%d'),
                'mean_velocity': float(window_data['velocity_m_per_day'].mean()),
                'max_velocity': float(window_data['velocity_m_per_day'].max()),
                'duration_days': int((window_data['date'].max() - window_data['date'].min()).days) + 1
            })
        
        print(f"\nGrouped into {len(window_groups)} discrete window(s):")
        for w in window_groups:
            print(f"  Window {w['window_id']}: {w['start_date']} to {w['end_date']} "
                  f"({w['duration_days']} days, mean vel: {w['mean_velocity']:.1f} m/d)")
        
        return window_groups
    else:
        print("\n⚠️  No jerk windows identified (no velocities above threshold)")
        return []

def load_climate_data():
    """Load climate data for H2 analysis."""
    print("\n" + "=" * 70)
    print("LOADING CLIMATE DATA FOR H2")
    print("=" * 70)
    
    clim_file = CLIMATE_DIR / "climate_derivatives_timeseries.csv"
    if not clim_file.exists():
        raise FileNotFoundError(f"Climate file not found: {clim_file}")
    
    clim = pd.read_csv(clim_file)
    clim['datetime'] = pd.to_datetime(clim['datetime'])
    clim = clim.sort_values('datetime').reset_index(drop=True)
    
    # Aggregate to daily if hourly
    if len(clim) > 365:
        print("   Aggregating hourly to daily...")
        clim['date'] = clim['datetime'].dt.date
        clim_daily = clim.groupby('date').agg({
            'temperature_C': 'mean',
            'precipitation_mm': 'sum',
            'swe_mm': 'mean'
        }).reset_index()
        clim_daily['datetime'] = pd.to_datetime(clim_daily['date'])
    else:
        clim_daily = clim.copy()
        clim_daily['date'] = clim_daily['datetime'].dt.date
    
    print(f"✅ Loaded {len(clim_daily)} daily climate records")
    print(f"   Date range: {clim_daily['datetime'].min()} to {clim_daily['datetime'].max()}")
    
    return clim_daily

def identify_ros_events(clim_daily):
    """Identify ROS events from climate data."""
    print("\n" + "=" * 70)
    print("IDENTIFYING ROS EVENTS (H2)")
    print("=" * 70)
    
    # ROS detection parameters
    ROS_TEMP_THRESHOLD = 0.5
    ROS_SWE_THRESHOLD = 0.1
    ROS_PRECIP_THRESHOLD = 0.1
    
    ros_events = []
    for idx, row in clim_daily.iterrows():
        temp = row['temperature_C']
        precip = row['precipitation_mm']
        swe = row['swe_mm']
        date = row['datetime']
        
        is_ros = (
            temp > ROS_TEMP_THRESHOLD and
            precip > ROS_PRECIP_THRESHOLD and
            swe > ROS_SWE_THRESHOLD
        )
        
        if is_ros:
            ros_intensity = precip * (temp - ROS_TEMP_THRESHOLD)
            ros_events.append({
                'date': date.strftime('%Y-%m-%d'),
                'datetime': date,
                'temperature': float(temp),
                'precipitation': float(precip),
                'swe': float(swe),
                'ros_intensity': float(ros_intensity)
            })
    
    print(f"\n✅ Identified {len(ros_events)} ROS events")
    
    if len(ros_events) > 0:
        ros_df = pd.DataFrame(ros_events)
        print(f"   Date range: {ros_df['datetime'].min().strftime('%Y-%m-%d')} to {ros_df['datetime'].max().strftime('%Y-%m-%d')}")
        print(f"   Mean intensity: {ros_df['ros_intensity'].mean():.2f}")
        print(f"   Max intensity: {ros_df['ros_intensity'].max():.2f}")
    
    return ros_events

def identify_liquid_precipitation_anomalies(clim_daily):
    """Identify liquid precipitation anomalies (high precipitation when T > 0°C)."""
    print("\n" + "=" * 70)
    print("IDENTIFYING LIQUID PRECIPITATION ANOMALIES (H2)")
    print("=" * 70)
    
    # Liquid precipitation: T > 0°C and P > threshold
    liquid_mask = (clim_daily['temperature_C'] > 0) & (clim_daily['precipitation_mm'] > 1.0)
    liquid_precip = clim_daily[liquid_mask].copy()
    
    # Calculate anomalies (above mean + 1 std)
    mean_precip = clim_daily['precipitation_mm'].mean()
    std_precip = clim_daily['precipitation_mm'].std()
    anomaly_threshold = mean_precip + std_precip
    
    anomalies = liquid_precip[liquid_precip['precipitation_mm'] > anomaly_threshold].copy()
    
    print(f"\nLiquid Precipitation Anomalies:")
    print(f"  Mean daily precip: {mean_precip:.2f} mm")
    print(f"  Std: {std_precip:.2f} mm")
    print(f"  Anomaly threshold: {anomaly_threshold:.2f} mm")
    print(f"  ✅ Found {len(anomalies)} anomaly events")
    
    if len(anomalies) > 0:
        print(f"\nTop 10 anomalies:")
        top_anomalies = anomalies.nlargest(10, 'precipitation_mm')
        for idx, row in top_anomalies.iterrows():
            print(f"  {row['datetime'].strftime('%Y-%m-%d')}: {row['precipitation_mm']:.1f} mm, T={row['temperature_C']:.1f}°C")
    
    return anomalies

def test_h2_temporal_alignment(jerk_windows, ros_events, liquid_precip_anomalies):
    """Test H2: temporal alignment between jerk windows and hydrological events."""
    print("\n" + "=" * 70)
    print("TESTING H2: TEMPORAL ALIGNMENT (HYDROLOGICAL SWITCHING)")
    print("=" * 70)
    
    if len(jerk_windows) == 0:
        print("⚠️  No jerk windows to test")
        return {}
    
    results = {}
    
    for window in jerk_windows:
        window_id = window['window_id']
        window_start = pd.to_datetime(window['start_date'])
        window_end = pd.to_datetime(window['end_date'])
        
        print(f"\nJerk Window {window_id} ({window_start.strftime('%Y-%m-%d')} to {window_end.strftime('%Y-%m-%d')}):")
        
        # Test alignment with ROS events (within ±3 days)
        alignment_window_days = 3
        ros_in_window = []
        for ros in ros_events:
            ros_date = pd.to_datetime(ros['datetime'])
            if (window_start - timedelta(days=alignment_window_days) <= ros_date <= 
                window_end + timedelta(days=alignment_window_days)):
                ros_in_window.append(ros)
        
        # Test alignment with liquid precip anomalies
        liquid_in_window = []
        for idx, row in liquid_precip_anomalies.iterrows():
            anomaly_date = row['datetime']
            if (window_start - timedelta(days=alignment_window_days) <= anomaly_date <= 
                window_end + timedelta(days=alignment_window_days)):
                liquid_in_window.append({
                    'date': anomaly_date.strftime('%Y-%m-%d'),
                    'precipitation': float(row['precipitation_mm']),
                    'temperature': float(row['temperature_C'])
                })
        
        print(f"  ROS events within ±{alignment_window_days} days: {len(ros_in_window)}")
        if len(ros_in_window) > 0:
            for ros in ros_in_window:
                print(f"    {ros['date']}: Intensity={ros['ros_intensity']:.2f}, P={ros['precipitation']:.1f}mm")
        
        print(f"  Liquid precip anomalies within ±{alignment_window_days} days: {len(liquid_in_window)}")
        if len(liquid_in_window) > 0:
            for liq in liquid_in_window:
                print(f"    {liq['date']}: P={liq['precipitation']:.1f}mm, T={liq['temperature']:.1f}°C")
        
        # H2 support: at least one hydrological event aligned
        h2_supported = (len(ros_in_window) > 0) or (len(liquid_in_window) > 0)
        
        results[window_id] = {
            'window_start': window['start_date'],
            'window_end': window['end_date'],
            'ros_events_aligned': len(ros_in_window),
            'liquid_precip_aligned': len(liquid_in_window),
            'h2_supported': h2_supported,
            'ros_details': [{k: (v.strftime('%Y-%m-%d') if isinstance(v, pd.Timestamp) else v) 
                            for k, v in ros.items()} for ros in ros_in_window],
            'liquid_details': liquid_in_window
        }
        
        print(f"  H2 Support: {'✅ YES' if h2_supported else '❌ NO'}")
    
    return results

def create_h1_h2_visualizations(vel, braking_data, jerk_windows, h2_results, ros_events, liquid_precip_anomalies):
    """Create visualizations for H1 and H2 analysis."""
    print("\n" + "=" * 70)
    print("CREATING H1 AND H2 VISUALIZATIONS")
    print("=" * 70)
    
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 2, height_ratios=[1, 1, 1], hspace=0.3, wspace=0.3)
    
    # Panel 1: Velocity time series with braking phase and jerk windows
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(vel['date'], vel['velocity_m_per_day'], 'o-', linewidth=2, markersize=8, 
             color='blue', label='Velocity', zorder=2)
    
    # Highlight braking phase
    if len(braking_data) > 0:
        ax1.fill_between(braking_data['date'], 0, braking_data['velocity_m_per_day'], 
                        alpha=0.2, color='orange', label='Braking Phase', zorder=1)
    
    # Highlight jerk windows
    for window in jerk_windows:
        window_start = pd.to_datetime(window['start_date'])
        window_end = pd.to_datetime(window['end_date'])
        ax1.axvspan(window_start, window_end, alpha=0.3, color='red', 
                   label='Jerk Window' if window['window_id'] == 1 else '')
    
    ax1.set_xlabel('Date', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Velocity (m d⁻¹)', fontsize=11, fontweight='bold')
    ax1.set_title('(a) Velocity Time Series with Braking Phase and Jerk Windows', 
                  fontsize=12, fontweight='bold', loc='left')
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    
    # Panel 2: ROS events and liquid precipitation anomalies
    ax2 = fig.add_subplot(gs[1, 0])
    if len(ros_events) > 0:
        ros_df = pd.DataFrame(ros_events)
        ax2.scatter(ros_df['datetime'], ros_df['ros_intensity'], s=50, color='red', 
                   alpha=0.6, label='ROS Events', zorder=2)
    
    # Mark jerk windows
    for window in jerk_windows:
        window_start = pd.to_datetime(window['start_date'])
        window_end = pd.to_datetime(window['end_date'])
        ax2.axvspan(window_start, window_end, alpha=0.2, color='blue', zorder=1)
    
    ax2.set_xlabel('Date', fontsize=10)
    ax2.set_ylabel('ROS Intensity', fontsize=10)
    ax2.set_title('(b) ROS Events and Jerk Windows', fontsize=11, fontweight='bold', loc='left')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Panel 3: Liquid precipitation anomalies
    ax3 = fig.add_subplot(gs[1, 1])
    if len(liquid_precip_anomalies) > 0:
        ax3.scatter(liquid_precip_anomalies['datetime'], liquid_precip_anomalies['precipitation_mm'],
                   s=50, color='cyan', alpha=0.6, label='Liquid Precip Anomalies', zorder=2)
    
    # Mark jerk windows
    for window in jerk_windows:
        window_start = pd.to_datetime(window['start_date'])
        window_end = pd.to_datetime(window['end_date'])
        ax3.axvspan(window_start, window_end, alpha=0.2, color='blue', zorder=1)
    
    ax3.set_xlabel('Date', fontsize=10)
    ax3.set_ylabel('Precipitation (mm)', fontsize=10)
    ax3.set_title('(c) Liquid Precipitation Anomalies and Jerk Windows', 
                  fontsize=11, fontweight='bold', loc='left')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Panel 4: H2 alignment summary table
    ax4 = fig.add_subplot(gs[2, :])
    ax4.axis('off')
    
    if h2_results:
        table_data = []
        for window_id, result in h2_results.items():
            table_data.append([
                f"Window {window_id}",
                result['window_start'],
                result['window_end'],
                str(result['ros_events_aligned']),
                str(result['liquid_precip_aligned']),
                '✅ YES' if result['h2_supported'] else '❌ NO'
            ])
        
        table = ax4.table(cellText=table_data,
                         colLabels=['Window', 'Start Date', 'End Date', 
                                   'ROS Events', 'Liquid Precip', 'H2 Support'],
                         cellLoc='center',
                         loc='center',
                         bbox=[0, 0, 1, 1])
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 2)
        ax4.set_title('(d) H2 Temporal Alignment Test Results', 
                     fontsize=11, fontweight='bold', pad=20)
    else:
        ax4.text(0.5, 0.5, 'No H2 Results Available', ha='center', va='center',
                transform=ax4.transAxes, fontsize=12)
    
    plt.suptitle('H1 and H2 Analysis: Topographic Pinning and Hydrological Switching', 
                fontsize=14, fontweight='bold', y=0.995)
    
    output_file = OUTPUT_DIR / "h1_h2_analysis.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✅ Visualization saved: {output_file}")
    
    return output_file

def main():
    """Main function."""
    print("=" * 70)
    print("COMPLETE H1 AND H2 ANALYSIS")
    print("=" * 70)
    print()
    
    # Load data
    vel = load_velocity_timeseries()
    vel_sorted, peak_date, braking_data = identify_braking_phase(vel)
    
    # H2 Analysis: Jerk windows and temporal alignment
    jerk_windows = identify_jerk_windows(braking_data)
    clim_daily = load_climate_data()
    ros_events = identify_ros_events(clim_daily)
    liquid_precip_anomalies = identify_liquid_precipitation_anomalies(clim_daily)
    h2_results = test_h2_temporal_alignment(jerk_windows, ros_events, liquid_precip_anomalies)
    
    # H1 Analysis: Will be done in QGIS (needs spatial velocity maps)
    print("\n" + "=" * 70)
    print("H1 ANALYSIS (TOPOGRAPHIC PINNING)")
    print("=" * 70)
    print("\n⚠️  H1 requires spatial velocity maps along glacier centerline")
    print("   This will be done in QGIS using:")
    print("   1. Extract glacier centerline from RGI outline")
    print("   2. Sample DEM slope along centerline")
    print("   3. Sample velocity maps along centerline")
    print("   4. Identify slope breaks and constrictions")
    print("   5. Test spatial alignment with braking onset position")
    print("\n   See: extract_centerline_and_test_h1_qgis.py")
    
    # Create visualizations
    vis_file = create_h1_h2_visualizations(vel, braking_data, jerk_windows, h2_results, 
                                          ros_events, liquid_precip_anomalies)
    
    # Save results
    # Convert datetime objects to strings for JSON
    ros_events_serializable = []
    for ros in ros_events:
        ros_clean = {}
        for k, v in ros.items():
            if isinstance(v, pd.Timestamp):
                ros_clean[k] = v.strftime('%Y-%m-%d')
            elif isinstance(v, datetime):
                ros_clean[k] = v.strftime('%Y-%m-%d')
            else:
                ros_clean[k] = v
        ros_events_serializable.append(ros_clean)
    
    results = {
        'peak_velocity': {
            'date': peak_date.strftime('%Y-%m-%d'),
            'velocity_m_per_day': float(vel_sorted.loc[vel_sorted['velocity_m_per_day'].idxmax(), 'velocity_m_per_day'])
        },
        'braking_phase': {
            'start_date': braking_data['date'].iloc[0].strftime('%Y-%m-%d') if len(braking_data) > 0 else None,
            'end_date': braking_data['date'].iloc[-1].strftime('%Y-%m-%d') if len(braking_data) > 0 else None,
            'duration_days': int((braking_data['date'].iloc[-1] - braking_data['date'].iloc[0]).days) if len(braking_data) > 0 else 0,
            'mean_velocity': float(braking_data['velocity_m_per_day'].mean()) if len(braking_data) > 0 else None
        },
        'jerk_windows': jerk_windows,
        'h2_temporal_alignment': h2_results,
        'ros_events_count': len(ros_events),
        'liquid_precip_anomalies_count': len(liquid_precip_anomalies),
        'metadata': {
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'jerk_threshold_factor': 1.5,
            'alignment_window_days': 3
        }
    }
    
    results_file = OUTPUT_DIR / "h1_h2_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved: {results_file}")
    
    # Print summary
    print("\n" + "=" * 70)
    print("H1 AND H2 ANALYSIS SUMMARY")
    print("=" * 70)
    print(f"\nPeak Velocity: {peak_date.strftime('%d %B %Y')}")
    if len(braking_data) > 0:
        print(f"Braking Phase: {braking_data['date'].iloc[0].strftime('%d %B %Y')} to {braking_data['date'].iloc[-1].strftime('%d %B %Y')}")
    print(f"\nJerk Windows: {len(jerk_windows)} identified")
    print(f"ROS Events: {len(ros_events)} total")
    print(f"Liquid Precip Anomalies: {len(liquid_precip_anomalies)} total")
    print(f"\nH2 Support:")
    for window_id, result in h2_results.items():
        support = "✅ YES" if result['h2_supported'] else "❌ NO"
        print(f"  Window {window_id}: {support} ({result['ros_events_aligned']} ROS, {result['liquid_precip_aligned']} liquid precip)")
    
    print("\n" + "=" * 70)
    print("✅ H1 AND H2 ANALYSIS COMPLETE!")
    print("=" * 70)
    print("\nNote: H1 spatial analysis requires QGIS for centerline extraction")
    print("      See next script: extract_centerline_and_test_h1_qgis.py")

if __name__ == "__main__":
    main()

