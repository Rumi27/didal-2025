#!/usr/bin/env python3
"""
Refined H3 Analysis: Cumulative PDD/SWE Buildup and ROS Event Refinement

This script performs enhanced H3 mechanism testing:
1. Cumulative PDD with multiple time windows (30, 60, 90, 120 days)
2. Enhanced SWE analysis (cumulative changes, depletion rates, timing)
3. ROS event refinement (better detection, intensity quantification)
4. Statistical comparison with baseline periods

Run: python3 refine_h3_analysis.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
from datetime import datetime, timedelta
import json
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Directories
CLIMATE_DIR = Path("satellite_data/era5_land/processed")
VELOCITY_DIR = Path("satellite_data/sentinel1/processed")
OUTPUT_DIR = Path("processed_data/h3_refined_analysis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Configuration
GLACIER_LAT = 38.97
GLACIER_LON = 70.75

# Time windows for cumulative PDD (days)
TIME_WINDOWS = [30, 60, 90, 120, 180]

# ROS detection parameters
ROS_TEMP_THRESHOLD = 0.5  # °C (precipitation is liquid if T > threshold)
ROS_SWE_THRESHOLD = 0.1   # mm (snow present if SWE > threshold)
ROS_PRECIP_THRESHOLD = 0.1  # mm (minimum precipitation for ROS event)

def load_data():
    """Load velocity and climate data."""
    print("=" * 70)
    print("LOADING DATA")
    print("=" * 70)
    
    # Velocity
    vel_file = VELOCITY_DIR / "velocity_timeseries_python.csv"
    if not vel_file.exists():
        raise FileNotFoundError(f"Velocity file not found: {vel_file}")
    
    vel = pd.read_csv(vel_file)
    vel['date'] = pd.to_datetime(vel['date'])
    vel = vel.sort_values('date').reset_index(drop=True)
    
    print(f"✅ Velocity: {len(vel)} measurements")
    print(f"   Date range: {vel['date'].min()} to {vel['date'].max()}")
    
    # Climate
    climate_file = CLIMATE_DIR / "climate_derivatives_timeseries.csv"
    if not climate_file.exists():
        raise FileNotFoundError(f"Climate file not found: {climate_file}")
    
    clim = pd.read_csv(climate_file)
    clim['datetime'] = pd.to_datetime(clim['datetime'])
    clim = clim.sort_values('datetime').reset_index(drop=True)
    
    print(f"✅ Climate: {len(clim)} time steps")
    print(f"   Date range: {clim['datetime'].min()} to {clim['datetime'].max()}")
    
    return vel, clim

def identify_acceleration_onset(vel):
    """Identify acceleration onset from velocity time series."""
    print("\n" + "=" * 70)
    print("IDENTIFYING ACCELERATION ONSET")
    print("=" * 70)
    
    # Find first significant velocity increase
    # Use change-point detection results if available, otherwise use threshold
    vel_sorted = vel.sort_values('date').reset_index(drop=True)
    
    # Calculate velocity change
    vel_sorted['velocity_change'] = vel_sorted['velocity_m_per_day'].diff()
    vel_sorted['velocity_change_pct'] = vel_sorted['velocity_m_per_day'].pct_change() * 100
    
    # Acceleration onset: first date with velocity > 300 m/d (high velocity threshold)
    # Or first significant increase (>50% increase)
    high_vel_threshold = 300  # m/d
    pct_increase_threshold = 50  # %
    
    # Find first date exceeding threshold
    high_vel_mask = vel_sorted['velocity_m_per_day'] > high_vel_threshold
    if high_vel_mask.any():
        first_high_vel = vel_sorted[high_vel_mask].iloc[0]
        acceleration_onset = first_high_vel['date']
        acceleration_velocity = first_high_vel['velocity_m_per_day']
    else:
        # Fallback: find first significant increase
        large_increase_mask = vel_sorted['velocity_change_pct'] > pct_increase_threshold
        if large_increase_mask.any():
            first_increase = vel_sorted[large_increase_mask].iloc[0]
            acceleration_onset = first_increase['date']
            acceleration_velocity = first_increase['velocity_m_per_day']
        else:
            # Use first velocity measurement as fallback
            acceleration_onset = vel_sorted['date'].iloc[0]
            acceleration_velocity = vel_sorted['velocity_m_per_day'].iloc[0]
    
    print(f"\nAcceleration Onset:")
    print(f"  Date: {acceleration_onset.strftime('%d %B %Y')}")
    print(f"  Velocity: {acceleration_velocity:.1f} m d⁻¹")
    
    return acceleration_onset, acceleration_velocity

def calculate_cumulative_pdd_multiple_windows(clim, acceleration_onset, windows):
    """
    Calculate cumulative PDD for multiple time windows leading up to acceleration.
    
    Parameters:
    - clim: Climate dataframe with PDD column
    - acceleration_onset: Date of acceleration onset
    - windows: List of time windows in days
    
    Returns:
    - Dictionary with cumulative PDD for each window
    """
    print("\n" + "=" * 70)
    print("CALCULATING CUMULATIVE PDD FOR MULTIPLE TIME WINDOWS")
    print("=" * 70)
    
    results = {}
    
    # Check available columns
    print(f"   Available columns: {clim.columns.tolist()}")
    
    # Always recalculate PDD from temperature to ensure correct units
    # Check for temperature column
    temp_col = None
    for col in ['temperature_C', 'temperature_2m', 't2m', 'temp']:
        if col in clim.columns:
            temp_col = col
            break
    
    if temp_col:
        # Recalculate hourly PDD (max(T, 0)) to ensure correct units
        # PDD should be in °C·hours for hourly data, then summed to °C·days for daily
        clim['pdd_hourly'] = np.maximum(clim[temp_col], 0)
        print(f"   ✅ Recalculated PDD from {temp_col}")
        pdd_col = 'pdd_hourly'
    else:
        # Fallback to existing PDD column if temperature not available
        if 'pdd' in clim.columns:
            pdd_col = 'pdd'
            print("   ⚠️  Using existing PDD column (could not verify units)")
        elif 'PDD' in clim.columns:
            pdd_col = 'PDD'
            print("   ⚠️  Using existing PDD column (could not verify units)")
        else:
            raise ValueError(f"Cannot calculate PDD: no temperature or PDD column found. Available: {clim.columns.tolist()}")
    
    # Convert to daily if hourly
    clim_daily = clim.copy()
    clim_daily['date'] = clim_daily['datetime'].dt.date
    
    # Aggregate to daily (sum PDD if hourly, or take mean if already daily)
    if len(clim_daily) > 365:  # Likely hourly data
        print(f"   Aggregating hourly data to daily (original: {len(clim_daily)} hours)")
        # For hourly data: sum PDD (hourly PDD in °C·hours, daily PDD in °C·days)
        # Note: If hourly PDD is already in °C·hours, summing 24 hours gives daily PDD
        # But we need to divide by 24 to convert from °C·hours to °C·days
        # Actually, standard practice: daily PDD = sum of hourly max(T,0) = sum in °C·hours
        # Then divide by 24 to get °C·days, OR keep as °C·hours and note the unit
        # For consistency with literature, we'll keep as °C·days (sum/24)
        agg_dict = {pdd_col: 'sum'}  # Sum hourly PDD (will be in °C·hours)
        
        # Add other columns if they exist
        if 'swe_mm' in clim_daily.columns:
            agg_dict['swe_mm'] = 'mean'
        if 'precipitation_mm' in clim_daily.columns:
            agg_dict['precipitation_mm'] = 'sum'
        if temp_col and temp_col in clim_daily.columns:
            agg_dict[temp_col] = 'mean'  # Mean temperature for daily
        
        clim_daily = clim_daily.groupby('date').agg(agg_dict).reset_index()
        clim_daily['datetime'] = pd.to_datetime(clim_daily['date'])
        
        # Convert PDD from °C·hours to °C·days (divide by 24)
        # Standard: daily PDD = sum of hourly max(T,0) / 24
        if pdd_col in clim_daily.columns:
            clim_daily['pdd_daily'] = clim_daily[pdd_col] / 24.0  # Convert to °C·days
            pdd_col = 'pdd_daily'  # Use converted column
            print(f"   ✅ Aggregated to {len(clim_daily)} daily values (PDD converted to °C·days)")
        else:
            print(f"   ✅ Aggregated to {len(clim_daily)} daily values")
    else:
        # Already daily, just ensure datetime is set
        clim_daily['datetime'] = pd.to_datetime(clim_daily['date'])
        print(f"   ✅ Data already daily ({len(clim_daily)} days)")
    
    # Calculate cumulative PDD from start of year
    clim_daily = clim_daily.sort_values('datetime')
    # Ensure we're using the right PDD column
    if 'pdd_daily' in clim_daily.columns:
        pdd_col = 'pdd_daily'
    clim_daily['pdd_cumulative'] = clim_daily[pdd_col].cumsum()
    
    # For each time window
    for window_days in windows:
        window_start = acceleration_onset - timedelta(days=window_days)
        
        # Find data in window
        window_mask = (clim_daily['datetime'] >= window_start) & (clim_daily['datetime'] < acceleration_onset)
        window_data = clim_daily[window_mask]
        
        if len(window_data) > 0:
            # Cumulative PDD in window
            pdd_cumulative = window_data[pdd_col].sum()
            
            # Mean daily PDD in window
            pdd_mean_daily = window_data[pdd_col].mean()
            
            # Maximum daily PDD in window
            pdd_max_daily = window_data[pdd_col].max()
            
            results[f'{window_days}days'] = {
                'window_start': window_start.strftime('%Y-%m-%d'),
                'window_end': acceleration_onset.strftime('%Y-%m-%d'),
                'window_days': window_days,
                'pdd_cumulative': float(pdd_cumulative),
                'pdd_mean_daily': float(pdd_mean_daily),
                'pdd_max_daily': float(pdd_max_daily),
                'data_points': len(window_data)
            }
            
            print(f"\n{window_days}-day window ({window_start.strftime('%Y-%m-%d')} to {acceleration_onset.strftime('%Y-%m-%d')}):")
            print(f"  Cumulative PDD: {pdd_cumulative:.1f} °C·days")
            print(f"  Mean daily PDD: {pdd_mean_daily:.2f} °C·days/day")
            print(f"  Max daily PDD: {pdd_max_daily:.2f} °C·days/day")
        else:
            print(f"\n⚠️  No data found for {window_days}-day window")
            results[f'{window_days}days'] = {
                'window_start': window_start.strftime('%Y-%m-%d'),
                'window_end': acceleration_onset.strftime('%Y-%m-%d'),
                'window_days': window_days,
                'pdd_cumulative': None,
                'pdd_mean_daily': None,
                'pdd_max_daily': None,
                'data_points': 0
            }
    
    return results, clim_daily

def calculate_baseline_pdd(clim_daily, baseline_start, baseline_end):
    """Calculate baseline PDD statistics for comparison."""
    baseline_mask = (clim_daily['datetime'] >= baseline_start) & (clim_daily['datetime'] <= baseline_end)
    baseline_data = clim_daily[baseline_mask]
    
    if len(baseline_data) == 0:
        return None
    
    # Find PDD column (could be pdd_daily, pdd, or PDD)
    pdd_col = None
    for col in ['pdd_daily', 'pdd', 'PDD']:
        if col in baseline_data.columns:
            pdd_col = col
            break
    
    if pdd_col is None:
        print("⚠️  Warning: No PDD column found for baseline calculation")
        return None
    
    # Calculate statistics for different window sizes
    baseline_stats = {}
    for window_days in TIME_WINDOWS:
        # Calculate rolling cumulative PDD
        baseline_data_sorted = baseline_data.sort_values('datetime')
        baseline_data_sorted['pdd_cumulative_rolling'] = baseline_data_sorted[pdd_col].rolling(
            window=window_days, min_periods=1
        ).sum()
        
        baseline_stats[f'{window_days}days'] = {
            'mean_cumulative_pdd': float(baseline_data_sorted['pdd_cumulative_rolling'].mean()),
            'std_cumulative_pdd': float(baseline_data_sorted['pdd_cumulative_rolling'].std()),
            'median_cumulative_pdd': float(baseline_data_sorted['pdd_cumulative_rolling'].median()),
            'percentile_75': float(baseline_data_sorted['pdd_cumulative_rolling'].quantile(0.75)),
            'percentile_90': float(baseline_data_sorted['pdd_cumulative_rolling'].quantile(0.90))
        }
    
    return baseline_stats

def enhanced_swe_analysis(clim_daily, acceleration_onset):
    """Enhanced SWE analysis: cumulative changes, depletion rates, timing."""
    print("\n" + "=" * 70)
    print("ENHANCED SWE ANALYSIS")
    print("=" * 70)
    
    results = {}
    
    # Ensure SWE column exists
    swe_col = 'swe_mm' if 'swe_mm' in clim_daily.columns else 'SWE'
    if swe_col not in clim_daily.columns:
        print("⚠️  Warning: SWE column not found")
        return results
    
    # Sort by date
    clim_daily = clim_daily.sort_values('datetime')
    
    # 1. SWE maximum and timing
    swe_max_idx = clim_daily[swe_col].idxmax()
    swe_max_value = clim_daily.loc[swe_max_idx, swe_col]
    swe_max_date = clim_daily.loc[swe_max_idx, 'datetime']
    
    results['swe_max'] = {
        'value': float(swe_max_value),
        'date': swe_max_date.strftime('%Y-%m-%d'),
        'days_before_acceleration': (acceleration_onset - swe_max_date).days
    }
    
    print(f"\nSWE Maximum:")
    print(f"  Value: {swe_max_value:.1f} mm")
    print(f"  Date: {swe_max_date.strftime('%d %B %Y')}")
    print(f"  Days before acceleration: {(acceleration_onset - swe_max_date).days}")
    
    # 2. SWE at acceleration onset
    accel_data = clim_daily[clim_daily['datetime'] <= acceleration_onset].iloc[-1]
    swe_at_acceleration = accel_data[swe_col]
    
    results['swe_at_acceleration'] = {
        'value': float(swe_at_acceleration),
        'date': acceleration_onset.strftime('%Y-%m-%d'),
        'depletion_from_max': float(swe_max_value - swe_at_acceleration)
    }
    
    print(f"\nSWE at Acceleration Onset:")
    print(f"  Value: {swe_at_acceleration:.1f} mm")
    print(f"  Depletion from max: {swe_max_value - swe_at_acceleration:.1f} mm")
    
    # 3. SWE depletion rate (from max to acceleration)
    if swe_max_date < acceleration_onset:
        days_depletion = (acceleration_onset - swe_max_date).days
        if days_depletion > 0:
            depletion_rate = (swe_max_value - swe_at_acceleration) / days_depletion
            results['swe_depletion_rate'] = {
                'rate_mm_per_day': float(depletion_rate),
                'period_days': days_depletion,
                'period_start': swe_max_date.strftime('%Y-%m-%d'),
                'period_end': acceleration_onset.strftime('%Y-%m-%d')
            }
            print(f"\nSWE Depletion Rate:")
            print(f"  Rate: {depletion_rate:.2f} mm/day")
            print(f"  Period: {days_depletion} days")
    
    # 4. Cumulative SWE change in time windows before acceleration
    for window_days in [30, 60, 90]:
        window_start = acceleration_onset - timedelta(days=window_days)
        window_mask = (clim_daily['datetime'] >= window_start) & (clim_daily['datetime'] < acceleration_onset)
        window_data = clim_daily[window_mask]
        
        if len(window_data) > 0:
            swe_start = window_data.iloc[0][swe_col]
            swe_end = window_data.iloc[-1][swe_col]
            swe_change = swe_end - swe_start
            
            results[f'swe_change_{window_days}days'] = {
                'window_start': window_start.strftime('%Y-%m-%d'),
                'window_end': acceleration_onset.strftime('%Y-%m-%d'),
                'swe_start': float(swe_start),
                'swe_end': float(swe_end),
                'swe_change': float(swe_change),
                'swe_change_rate': float(swe_change / window_days) if window_days > 0 else 0
            }
    
    return results

def refine_ros_detection(clim_daily):
    """Refined ROS event detection with intensity quantification."""
    print("\n" + "=" * 70)
    print("REFINED ROS EVENT DETECTION")
    print("=" * 70)
    
    # Find temperature column
    temp_col = None
    for col in ['temperature_C', 'temperature_2m', 't2m', 'temp']:
        if col in clim_daily.columns:
            temp_col = col
            break
    
    # Find precipitation column
    precip_col = None
    for col in ['precipitation_mm', 'precipitation', 'precip']:
        if col in clim_daily.columns:
            precip_col = col
            break
    
    # Find SWE column
    swe_col = None
    for col in ['swe_mm', 'SWE', 'swe']:
        if col in clim_daily.columns:
            swe_col = col
            break
    
    if temp_col is None or precip_col is None or swe_col is None:
        print("⚠️  Warning: Missing required columns for ROS detection")
        print(f"   Available columns: {clim_daily.columns.tolist()}")
        print(f"   Temperature column: {temp_col}")
        print(f"   Precipitation column: {precip_col}")
        print(f"   SWE column: {swe_col}")
        return []
    
    print(f"   Using columns: temp={temp_col}, precip={precip_col}, swe={swe_col}")
    
    # Detect ROS events
    ros_events = []
    
    for idx, row in clim_daily.iterrows():
        temp = row[temp_col]
        precip = row[precip_col]
        swe = row[swe_col]
        date = row['datetime']
        
        # ROS conditions:
        # 1. Temperature > threshold (liquid precipitation)
        # 2. Precipitation > threshold (significant precipitation)
        # 3. SWE > threshold (snow present)
        is_ros = (
            temp > ROS_TEMP_THRESHOLD and
            precip > ROS_PRECIP_THRESHOLD and
            swe > ROS_SWE_THRESHOLD
        )
        
        if is_ros:
            # Calculate ROS intensity
            ros_intensity = precip * (temp - ROS_TEMP_THRESHOLD)  # Weighted by temperature excess
            
            ros_events.append({
                'date': date.strftime('%Y-%m-%d'),
                'datetime': date,
                'temperature': float(temp),
                'precipitation': float(precip),
                'swe': float(swe),
                'ros_intensity': float(ros_intensity),
                'index': idx
            })
    
    print(f"\nROS Events Detected: {len(ros_events)}")
    
    if len(ros_events) > 0:
        ros_df = pd.DataFrame(ros_events)
        print(f"\nROS Event Statistics:")
        print(f"  Mean intensity: {ros_df['ros_intensity'].mean():.2f}")
        print(f"  Max intensity: {ros_df['ros_intensity'].max():.2f}")
        print(f"  Total precipitation: {ros_df['precipitation'].sum():.2f} mm")
        print(f"\nTop 5 ROS Events:")
        top_ros = ros_df.nlargest(5, 'ros_intensity')
        for _, event in top_ros.iterrows():
            print(f"    {event['date']}: Intensity={event['ros_intensity']:.2f}, "
                  f"P={event['precipitation']:.2f}mm, T={event['temperature']:.1f}°C, SWE={event['swe']:.1f}mm")
    
    return ros_events

def test_pdd_buildup_hypothesis(pdd_results, baseline_stats):
    """Test if PDD buildup exceeds baseline thresholds."""
    print("\n" + "=" * 70)
    print("TESTING PDD BUILDUP HYPOTHESIS (H3)")
    print("=" * 70)
    
    hypothesis_results = {}
    
    for window_key, pdd_data in pdd_results.items():
        if pdd_data['pdd_cumulative'] is None:
            continue
        
        window_days = pdd_data['window_days']
        baseline_key = f'{window_days}days'
        
        if baseline_key in baseline_stats:
            baseline_mean = baseline_stats[baseline_key]['mean_cumulative_pdd']
            baseline_std = baseline_stats[baseline_key]['std_cumulative_pdd']
            baseline_75th = baseline_stats[baseline_key]['percentile_75']
            baseline_90th = baseline_stats[baseline_key]['percentile_90']
            
            pdd_cumulative = pdd_data['pdd_cumulative']
            
            # Test thresholds
            exceeds_mean = pdd_cumulative > baseline_mean
            exceeds_75th = pdd_cumulative > baseline_75th
            exceeds_90th = pdd_cumulative > baseline_90th
            exceeds_mean_plus_std = pdd_cumulative > (baseline_mean + baseline_std)
            
            # Calculate z-score
            if baseline_std > 0:
                z_score = (pdd_cumulative - baseline_mean) / baseline_std
            else:
                z_score = 0
            
            hypothesis_results[window_key] = {
                'pdd_cumulative': pdd_cumulative,
                'baseline_mean': baseline_mean,
                'baseline_std': baseline_std,
                'z_score': float(z_score),
                'exceeds_mean': exceeds_mean,
                'exceeds_75th_percentile': exceeds_75th,
                'exceeds_90th_percentile': exceeds_90th,
                'exceeds_mean_plus_std': exceeds_mean_plus_std,
                'percentile_rank': float(stats.percentileofscore(
                    [baseline_mean - baseline_std, baseline_mean, baseline_mean + baseline_std],
                    pdd_cumulative
                ))
            }
            
            print(f"\n{window_days}-day window:")
            print(f"  Cumulative PDD: {pdd_cumulative:.1f} °C·days")
            print(f"  Baseline mean: {baseline_mean:.1f} °C·days")
            print(f"  Z-score: {z_score:.2f}")
            print(f"  Exceeds mean: {'✅ YES' if exceeds_mean else '❌ NO'}")
            print(f"  Exceeds 75th percentile: {'✅ YES' if exceeds_75th else '❌ NO'}")
            print(f"  Exceeds 90th percentile: {'✅ YES' if exceeds_90th else '❌ NO'}")
    
    return hypothesis_results

def create_visualizations(vel, clim_daily, pdd_results, swe_results, ros_events, acceleration_onset):
    """Create comprehensive visualization of H3 analysis."""
    print("\n" + "=" * 70)
    print("CREATING VISUALIZATIONS")
    print("=" * 70)
    
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(4, 2, height_ratios=[1, 1, 1, 1], hspace=0.3, wspace=0.3)
    
    # Panel 1: Velocity time series with acceleration onset
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(vel['date'], vel['velocity_m_per_day'], 'o-', linewidth=2, markersize=8, color='blue', label='Velocity')
    ax1.axvline(acceleration_onset, color='red', linestyle='--', linewidth=2, label='Acceleration Onset')
    ax1.set_xlabel('Date', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Velocity (m d⁻¹)', fontsize=11, fontweight='bold')
    ax1.set_title('(a) Velocity Time Series with Acceleration Onset', fontsize=12, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # Panel 2: Cumulative PDD with multiple windows
    ax2 = fig.add_subplot(gs[1, 0])
    if 'pdd' in clim_daily.columns or 'PDD' in clim_daily.columns:
        pdd_col = 'pdd' if 'pdd' in clim_daily.columns else 'PDD'
        clim_daily_sorted = clim_daily.sort_values('datetime')
        clim_daily_sorted['pdd_cumulative'] = clim_daily_sorted[pdd_col].cumsum()
        
        ax2.plot(clim_daily_sorted['datetime'], clim_daily_sorted['pdd_cumulative'], 
                linewidth=2, color='orange', label='Cumulative PDD')
        ax2.axvline(acceleration_onset, color='red', linestyle='--', linewidth=2, label='Acceleration Onset')
        
        # Mark time windows
        for window_days in [30, 60, 90, 120]:
            window_start = acceleration_onset - timedelta(days=window_days)
            ax2.axvspan(window_start, acceleration_onset, alpha=0.1, color='blue', 
                       label=f'{window_days}-day window' if window_days == 30 else '')
        
        ax2.set_xlabel('Date', fontsize=10)
        ax2.set_ylabel('Cumulative PDD (°C·days)', fontsize=10)
        ax2.set_title('(b) Cumulative PDD with Time Windows', fontsize=11, fontweight='bold')
        ax2.legend(fontsize=8)
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # Panel 3: SWE time series
    ax3 = fig.add_subplot(gs[1, 1])
    if 'swe_mm' in clim_daily.columns or 'SWE' in clim_daily.columns:
        swe_col = 'swe_mm' if 'swe_mm' in clim_daily.columns else 'SWE'
        clim_daily_sorted = clim_daily.sort_values('datetime')
        
        ax3.plot(clim_daily_sorted['datetime'], clim_daily_sorted[swe_col], 
                linewidth=2, color='cyan', label='SWE')
        ax3.axvline(acceleration_onset, color='red', linestyle='--', linewidth=2, label='Acceleration Onset')
        
        if 'swe_max' in swe_results:
            swe_max_date = pd.to_datetime(swe_results['swe_max']['date'])
            swe_max_value = swe_results['swe_max']['value']
            ax3.plot(swe_max_date, swe_max_value, 'ro', markersize=10, label='SWE Max')
        
        ax3.set_xlabel('Date', fontsize=10)
        ax3.set_ylabel('SWE (mm)', fontsize=10)
        ax3.set_title('(c) SWE Time Series', fontsize=11, fontweight='bold')
        ax3.legend(fontsize=8)
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # Panel 4: PDD buildup by window size
    ax4 = fig.add_subplot(gs[2, 0])
    window_sizes = []
    pdd_values = []
    for window_key, pdd_data in pdd_results.items():
        if pdd_data['pdd_cumulative'] is not None:
            window_sizes.append(pdd_data['window_days'])
            pdd_values.append(pdd_data['pdd_cumulative'])
    
    if window_sizes:
        ax4.bar(window_sizes, pdd_values, color='orange', alpha=0.7, edgecolor='black')
        ax4.set_xlabel('Time Window (days)', fontsize=10)
        ax4.set_ylabel('Cumulative PDD (°C·days)', fontsize=10)
        ax4.set_title('(d) Cumulative PDD by Time Window', fontsize=11, fontweight='bold')
        ax4.grid(True, alpha=0.3, axis='y')
    
    # Panel 5: ROS events
    ax5 = fig.add_subplot(gs[2, 1])
    if len(ros_events) > 0:
        ros_df = pd.DataFrame(ros_events)
        ax5.scatter(ros_df['datetime'], ros_df['ros_intensity'], 
                   s=50, color='red', alpha=0.6, label='ROS Events')
        ax5.axvline(acceleration_onset, color='red', linestyle='--', linewidth=2, label='Acceleration Onset')
        ax5.set_xlabel('Date', fontsize=10)
        ax5.set_ylabel('ROS Intensity', fontsize=10)
        ax5.set_title('(e) ROS Events', fontsize=11, fontweight='bold')
        ax5.legend(fontsize=8)
        ax5.grid(True, alpha=0.3)
        ax5.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax5.xaxis.get_majorticklabels(), rotation=45, ha='right')
    else:
        ax5.text(0.5, 0.5, 'No ROS Events Detected', ha='center', va='center', 
                transform=ax5.transAxes, fontsize=12)
        ax5.set_title('(e) ROS Events', fontsize=11, fontweight='bold')
    
    # Panel 6: Summary statistics table
    ax6 = fig.add_subplot(gs[3, :])
    ax6.axis('off')
    
    # Create summary table
    table_data = []
    for window_key, pdd_data in pdd_results.items():
        if pdd_data['pdd_cumulative'] is not None:
            table_data.append([
                f"{pdd_data['window_days']} days",
                f"{pdd_data['window_start']}",
                f"{pdd_data['window_end']}",
                f"{pdd_data['pdd_cumulative']:.1f}",
                f"{pdd_data['pdd_mean_daily']:.2f}",
                f"{pdd_data['pdd_max_daily']:.2f}"
            ])
    
    if table_data:
        table = ax6.table(cellText=table_data,
                         colLabels=['Window', 'Start Date', 'End Date', 
                                   'Cumulative PDD (°C·days)', 'Mean Daily PDD', 'Max Daily PDD'],
                         cellLoc='center',
                         loc='center',
                         bbox=[0, 0, 1, 1])
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 2)
        ax6.set_title('(f) PDD Buildup Summary by Time Window', fontsize=11, fontweight='bold', pad=20)
    
    plt.suptitle('H3 Analysis: Cumulative PDD/SWE Buildup and ROS Events', 
                fontsize=14, fontweight='bold', y=0.995)
    
    output_file = OUTPUT_DIR / "h3_refined_analysis.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✅ Visualization saved: {output_file}")
    
    return output_file

def main():
    """Main function."""
    print("=" * 70)
    print("REFINED H3 ANALYSIS: CUMULATIVE PDD/SWE BUILDUP")
    print("=" * 70)
    print()
    
    # Load data
    vel, clim = load_data()
    
    # Identify acceleration onset
    acceleration_onset, acceleration_velocity = identify_acceleration_onset(vel)
    
    # Calculate cumulative PDD for multiple windows
    pdd_results, clim_daily = calculate_cumulative_pdd_multiple_windows(
        clim, acceleration_onset, TIME_WINDOWS
    )
    
    # Enhanced SWE analysis
    swe_results = enhanced_swe_analysis(clim_daily, acceleration_onset)
    
    # Refined ROS detection
    ros_events = refine_ros_detection(clim_daily)
    
    # Calculate baseline statistics (use early year as baseline)
    baseline_start = clim_daily['datetime'].min()
    baseline_end = acceleration_onset - timedelta(days=max(TIME_WINDOWS) + 30)  # End 30 days before shortest window
    if baseline_end > baseline_start:
        baseline_stats = calculate_baseline_pdd(clim_daily, baseline_start, baseline_end)
    else:
        baseline_stats = None
        print("\n⚠️  Warning: Insufficient data for baseline calculation")
    
    # Test H3 hypothesis
    if baseline_stats:
        hypothesis_results = test_pdd_buildup_hypothesis(pdd_results, baseline_stats)
    else:
        hypothesis_results = {}
        print("\n⚠️  Warning: Cannot test hypothesis without baseline statistics")
    
    # Create visualizations
    vis_file = create_visualizations(vel, clim_daily, pdd_results, swe_results, ros_events, acceleration_onset)
    
    # Save results (convert all datetime objects to strings)
    results = {
        'acceleration_onset': {
            'date': acceleration_onset.strftime('%Y-%m-%d'),
            'velocity_m_per_day': float(acceleration_velocity)
        },
        'pdd_buildup': pdd_results,
        'swe_analysis': swe_results,
        'ros_events': {
            'total_events': len(ros_events),
            'events': [
                {k: (v.strftime('%Y-%m-%d') if isinstance(v, pd.Timestamp) else v) 
                 for k, v in event.items() if k != 'datetime'}
                for event in ros_events[:20]  # Save first 20 events
            ]
        },
        'hypothesis_testing': hypothesis_results,
        'baseline_stats': baseline_stats,
        'metadata': {
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'time_windows_days': TIME_WINDOWS,
            'ros_parameters': {
                'temp_threshold_c': ROS_TEMP_THRESHOLD,
                'swe_threshold_mm': ROS_SWE_THRESHOLD,
                'precip_threshold_mm': ROS_PRECIP_THRESHOLD
            }
        }
    }
    
    results_file = OUTPUT_DIR / "h3_refined_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved: {results_file}")
    
    # Print summary
    print("\n" + "=" * 70)
    print("H3 ANALYSIS SUMMARY")
    print("=" * 70)
    print(f"\nAcceleration Onset: {acceleration_onset.strftime('%d %B %Y')}")
    print(f"Velocity at Onset: {acceleration_velocity:.1f} m d⁻¹")
    print(f"\nPDD Buildup (leading up to acceleration):")
    for window_key, pdd_data in pdd_results.items():
        if pdd_data['pdd_cumulative'] is not None:
            print(f"  {pdd_data['window_days']}-day window: {pdd_data['pdd_cumulative']:.1f} °C·days")
    print(f"\nSWE Analysis:")
    if 'swe_max' in swe_results:
        print(f"  SWE Max: {swe_results['swe_max']['value']:.1f} mm on {swe_results['swe_max']['date']}")
    if 'swe_at_acceleration' in swe_results:
        print(f"  SWE at Acceleration: {swe_results['swe_at_acceleration']['value']:.1f} mm")
    print(f"\nROS Events: {len(ros_events)} total")
    
    print("\n" + "=" * 70)
    print("✅ H3 REFINED ANALYSIS COMPLETE!")
    print("=" * 70)

if __name__ == "__main__":
    main()

