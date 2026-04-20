#!/usr/bin/env python3
"""
Align change-points with climate events for final analysis.

This script:
1. Loads velocity time series with change-points
2. Loads climate derivatives
3. Aligns change-points with climate events (ROS, PDD, temperature)
4. Creates comprehensive visualization
5. Generates paper-ready statistics

Requirements:
    pip install pandas numpy matplotlib scipy
"""

import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import json

# Input directories
CLIMATE_DIR = Path("satellite_data/era5_land/processed")
VELOCITY_DIR = Path("satellite_data/sentinel1/processed")
OUTPUT_DIR = Path("satellite_data/analysis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_data():
    """Load all required data."""
    print("=" * 70)
    print("Loading Data")
    print("=" * 70)
    print()
    
    # Load climate derivatives
    climate_file = CLIMATE_DIR / "climate_derivatives_timeseries.csv"
    if not climate_file.exists():
        print(f"❌ Climate derivatives not found: {climate_file}")
        return None, None, None
    
    climate_df = pd.read_csv(climate_file)
    climate_df['datetime'] = pd.to_datetime(climate_df['datetime'])
    climate_df = climate_df.sort_values('datetime')
    print(f"✅ Climate data: {len(climate_df)} time steps")
    print(f"   Date range: {climate_df['datetime'].min()} to {climate_df['datetime'].max()}")
    
    # Load velocity with change-points
    velocity_file = VELOCITY_DIR / "velocity_timeseries_with_regimes.csv"
    if not velocity_file.exists():
        # Try without regimes
        velocity_file = VELOCITY_DIR / "velocity_timeseries.csv"
        if not velocity_file.exists():
            print(f"⚠️  Velocity time series not found")
            return climate_df, None, None
    
    velocity_df = pd.read_csv(velocity_file)
    velocity_df['date'] = pd.to_datetime(velocity_df['date'])
    velocity_df = velocity_df.sort_values('date')
    print(f"✅ Velocity data: {len(velocity_df)} measurements")
    print(f"   Date range: {velocity_df['date'].min()} to {velocity_df['date'].max()}")
    
    # Load change-point summary
    changepoint_file = VELOCITY_DIR / "changepoint_summary.txt"
    changepoints = None
    if changepoint_file.exists():
        # Parse change-points from summary
        with open(changepoint_file, 'r') as f:
            content = f.read()
            # Extract change-point dates (simplified parsing)
            import re
            dates = re.findall(r'Date: (\d{4}-\d{2}-\d{2})', content)
            changepoints = [pd.to_datetime(d) for d in dates]
            print(f"✅ Change-points: {len(changepoints)} detected")
            for i, cp in enumerate(changepoints):
                print(f"   CP {i+1}: {cp.strftime('%Y-%m-%d')}")
    
    print()
    return climate_df, velocity_df, changepoints


def align_changepoints_with_climate(climate_df, velocity_df, changepoints):
    """Align change-points with climate events."""
    print("=" * 70)
    print("Aligning Change-Points with Climate Events")
    print("=" * 70)
    print()
    
    if changepoints is None or len(changepoints) == 0:
        print("⚠️  No change-points available")
        return None
    
    results = []
    
    for i, cp_date in enumerate(changepoints):
        print(f"Change-point {i+1}: {cp_date.strftime('%Y-%m-%d')}")
        
        # Find climate data around change-point (±7 days)
        window_start = cp_date - timedelta(days=7)
        window_end = cp_date + timedelta(days=7)
        
        climate_window = climate_df[
            (climate_df['datetime'] >= window_start) &
            (climate_df['datetime'] <= window_end)
        ].copy()
        
        if len(climate_window) == 0:
            print(f"  ⚠️  No climate data in window")
            continue
        
        # Extract climate metrics
        result = {
            'changepoint_id': i + 1,
            'changepoint_date': cp_date,
            'window_start': window_start,
            'window_end': window_end
        }
        
        # Temperature
        if 'temperature_C' in climate_window.columns:
            result['mean_temp'] = climate_window['temperature_C'].mean()
            result['max_temp'] = climate_window['temperature_C'].max()
            result['temp_trend'] = 'increasing' if climate_window['temperature_C'].iloc[-1] > climate_window['temperature_C'].iloc[0] else 'decreasing'
        
        # PDD
        if 'pdd' in climate_window.columns:
            result['pdd_at_cp'] = climate_window[climate_window['datetime'] <= cp_date]['pdd'].iloc[-1] if len(climate_window[climate_window['datetime'] <= cp_date]) > 0 else np.nan
            result['pdd_change'] = climate_window['pdd'].iloc[-1] - climate_window['pdd'].iloc[0] if len(climate_window) > 1 else 0
        
        # ROS events
        if 'ros' in climate_window.columns:
            ros_events = climate_window[climate_window['ros'] > 0.1]
            result['ros_events_count'] = len(ros_events)
            result['ros_total'] = ros_events['ros'].sum() if len(ros_events) > 0 else 0
            result['ros_before_cp'] = len(climate_window[(climate_window['datetime'] < cp_date) & (climate_window['ros'] > 0.1)])
            result['ros_after_cp'] = len(climate_window[(climate_window['datetime'] > cp_date) & (climate_window['ros'] > 0.1)])
        
        # Precipitation
        if 'precipitation_mm' in climate_window.columns:
            result['precip_total'] = climate_window['precipitation_mm'].sum()
            result['precip_before_cp'] = climate_window[climate_window['datetime'] < cp_date]['precipitation_mm'].sum()
            result['precip_after_cp'] = climate_window[climate_window['datetime'] > cp_date]['precipitation_mm'].sum()
        
        # SWE
        if 'swe_mm' in climate_window.columns:
            result['swe_at_cp'] = climate_window[climate_window['datetime'] <= cp_date]['swe_mm'].iloc[-1] if len(climate_window[climate_window['datetime'] <= cp_date]) > 0 else np.nan
            result['swe_trend'] = 'decreasing' if climate_window['swe_mm'].iloc[-1] < climate_window['swe_mm'].iloc[0] else 'increasing'
        
        results.append(result)
        
        # Print summary
        print(f"  Temperature: {result.get('mean_temp', 'N/A'):.2f}°C")
        print(f"  PDD at CP: {result.get('pdd_at_cp', 'N/A'):.1f} °C·days")
        print(f"  ROS events: {result.get('ros_events_count', 0)}")
        print(f"  Precipitation: {result.get('precip_total', 0):.1f} mm")
        print()
    
    return results


def create_comprehensive_visualization(climate_df, velocity_df, changepoints, alignment_results):
    """Create comprehensive visualization."""
    print("Creating comprehensive visualization...")
    print()
    
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(5, 1, hspace=0.3, height_ratios=[1.5, 1, 1, 1, 0.8])
    
    # Velocity with change-points
    ax1 = fig.add_subplot(gs[0])
    if velocity_df is not None:
        ax1.errorbar(velocity_df['date'], velocity_df['velocity_m_per_day'],
                     yerr=velocity_df.get('velocity_std', 0), fmt='o-', capsize=3,
                     color='blue', alpha=0.7, label='Velocity', linewidth=2, markersize=6)
        
        # Mark change-points
        if changepoints:
            for i, cp in enumerate(changepoints):
                ax1.axvline(x=cp, color='red', linestyle='--', linewidth=2, alpha=0.7)
                ax1.text(cp, ax1.get_ylim()[1] * 0.95, f'CP{i+1}',
                        rotation=90, ha='right', va='top', fontsize=10, fontweight='bold')
        
        # Color by regime if available
        if 'regime' in velocity_df.columns:
            for regime in velocity_df['regime'].unique():
                regime_data = velocity_df[velocity_df['regime'] == regime]
                ax1.scatter(regime_data['date'], regime_data['velocity_m_per_day'],
                           alpha=0.3, s=100, label=regime.replace('_', ' ').title())
    
    ax1.set_ylabel('Velocity (m/day)', fontsize=12, fontweight='bold')
    ax1.set_title('Glacier Velocity Time Series with Change-Points', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper left', fontsize=9)
    ax1.grid(True, alpha=0.3)
    
    # Temperature and PDD
    ax2 = fig.add_subplot(gs[1])
    ax2_twin = ax2.twinx()
    
    if 'temperature_C' in climate_df.columns:
        ax2.plot(climate_df['datetime'], climate_df['temperature_C'],
                'b-', alpha=0.6, linewidth=1.5, label='Temperature')
        ax2.axhline(y=0, color='gray', linestyle=':', alpha=0.5)
        ax2.set_ylabel('Temperature (°C)', color='blue', fontsize=11)
    
    if 'pdd' in climate_df.columns:
        ax2_twin.plot(climate_df['datetime'], climate_df['pdd'],
                     'r-', linewidth=2, label='Cumulative PDD', alpha=0.8)
        ax2_twin.set_ylabel('Cumulative PDD (°C·days)', color='red', fontsize=11)
    
    # Mark change-points
    if changepoints:
        for cp in changepoints:
            ax2.axvline(x=cp, color='red', linestyle='--', linewidth=1.5, alpha=0.5)
    
    ax2.set_title('Climate: Temperature and PDD', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper left', fontsize=8)
    ax2_twin.legend(loc='upper right', fontsize=8)
    
    # ROS events
    ax3 = fig.add_subplot(gs[2])
    if 'ros' in climate_df.columns:
        ros_events = climate_df[climate_df['ros'] > 0.1]
        if len(ros_events) > 0:
            ax3.bar(ros_events['datetime'], ros_events['ros'],
                   width=timedelta(hours=6), alpha=0.7, color='orange', label='ROS')
    
    # Mark change-points
    if changepoints:
        for cp in changepoints:
            ax3.axvline(x=cp, color='red', linestyle='--', linewidth=1.5, alpha=0.5)
    
    ax3.set_ylabel('ROS (mm)', fontsize=11)
    ax3.set_title('Rain-on-Snow (ROS) Events', fontsize=12, fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='y')
    ax3.legend(fontsize=8)
    
    # Precipitation
    ax4 = fig.add_subplot(gs[3])
    if 'precipitation_mm' in climate_df.columns:
        # Daily sum
        climate_daily = climate_df.set_index('datetime').resample('D')['precipitation_mm'].sum()
        ax4.bar(climate_daily.index, climate_daily.values,
               width=timedelta(days=0.8), alpha=0.6, color='cyan', label='Precipitation')
    
    # Mark change-points
    if changepoints:
        for cp in changepoints:
            ax4.axvline(x=cp, color='red', linestyle='--', linewidth=1.5, alpha=0.5)
    
    ax4.set_ylabel('Precipitation (mm)', fontsize=11)
    ax4.set_xlabel('Date', fontsize=12, fontweight='bold')
    ax4.set_title('Daily Precipitation', fontsize=12, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='y')
    ax4.legend(fontsize=8)
    
    # Alignment summary
    ax5 = fig.add_subplot(gs[4])
    ax5.axis('off')
    
    if alignment_results:
        summary_text = "Change-Point - Climate Event Alignment:\n\n"
        for result in alignment_results:
            cp_id = result['changepoint_id']
            cp_date = result['changepoint_date'].strftime('%Y-%m-%d')
            summary_text += f"CP{cp_id} ({cp_date}):\n"
            summary_text += f"  Temp: {result.get('mean_temp', 'N/A'):.1f}°C, "
            summary_text += f"PDD: {result.get('pdd_at_cp', 'N/A'):.0f} °C·days, "
            summary_text += f"ROS: {result.get('ros_events_count', 0)} events\n"
    else:
        summary_text = "No alignment results available"
    
    ax5.text(0.05, 0.5, summary_text, fontsize=10, family='monospace',
            verticalalignment='center', transform=ax5.transAxes)
    
    plt.suptitle('Integrated Analysis: Velocity, Climate, and Change-Points', 
                fontsize=16, fontweight='bold', y=0.995)
    
    plot_file = OUTPUT_DIR / "comprehensive_analysis_plot.png"
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"✅ Plot saved: {plot_file}")
    plt.close()
    
    return plot_file


def save_alignment_results(alignment_results, output_dir):
    """Save alignment results."""
    print("Saving alignment results...")
    print()
    
    # Convert to DataFrame
    if alignment_results:
        df = pd.DataFrame(alignment_results)
        
        # Convert datetime to string for JSON
        df['changepoint_date'] = df['changepoint_date'].dt.strftime('%Y-%m-%d')
        df['window_start'] = df['window_start'].dt.strftime('%Y-%m-%d')
        df['window_end'] = df['window_end'].dt.strftime('%Y-%m-%d')
        
        # Save CSV
        csv_file = output_dir / "changepoint_climate_alignment.csv"
        df.to_csv(csv_file, index=False)
        print(f"✅ CSV saved: {csv_file}")
        
        # Save JSON
        json_file = output_dir / "changepoint_climate_alignment.json"
        df_dict = df.to_dict(orient='records')
        with open(json_file, 'w') as f:
            json.dump(df_dict, f, indent=2, default=str)
        print(f"✅ JSON saved: {json_file}")
        
        return csv_file, json_file
    
    return None, None


def main():
    """Main processing function."""
    print("=" * 70)
    print("Aligning Change-Points with Climate Events")
    print("=" * 70)
    print()
    
    # Load data
    climate_df, velocity_df, changepoints = load_data()
    
    if climate_df is None:
        return False
    
    # Align change-points with climate
    alignment_results = align_changepoints_with_climate(climate_df, velocity_df, changepoints)
    
    # Create visualization
    plot_file = create_comprehensive_visualization(climate_df, velocity_df, changepoints, alignment_results)
    
    # Save results
    if alignment_results:
        csv_file, json_file = save_alignment_results(alignment_results, OUTPUT_DIR)
    
    print("=" * 70)
    print("✅ Analysis Complete!")
    print("=" * 70)
    print()
    print("Output files:")
    if alignment_results:
        print(f"  - {csv_file}")
        print(f"  - {json_file}")
    print(f"  - {plot_file}")
    print()
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

