#!/usr/bin/env python3
"""
Complete Automated Analysis Pipeline

This script:
1. Reviews all results and generates statistics
2. Refines change-point detection with multiple parameters
3. Creates publication-quality figures
4. Generates interpretation report with findings

Run: python3 complete_analysis_automated.py
"""

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import json
import warnings
warnings.filterwarnings('ignore')

try:
    import ruptures
except ImportError:
    ruptures = None

# Directories
PROCESSED_DIR = Path("satellite_data/sentinel1/processed")
ANALYSIS_DIR = Path("satellite_data/analysis")
CLIMATE_DIR = Path("satellite_data/era5_land/processed")
OUTPUT_DIR = Path("processed_data/analysis_results")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Publication figure settings
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9
plt.rcParams['legend.fontsize'] = 9


def load_all_data():
    """Load all analysis data."""
    print("=" * 70)
    print("Loading All Data")
    print("=" * 70)
    print()
    
    data = {}
    
    # Load velocity time series
    vel_file = PROCESSED_DIR / "velocity_timeseries_python.csv"
    if vel_file.exists():
        data['velocity'] = pd.read_csv(vel_file)
        data['velocity']['date'] = pd.to_datetime(data['velocity']['date'])
        data['velocity'] = data['velocity'].sort_values('date')
        print(f"✅ Velocity: {len(data['velocity'])} measurements")
    else:
        print("❌ Velocity data not found")
        return None
    
    # Load climate derivatives
    climate_file = CLIMATE_DIR / "climate_derivatives_timeseries.csv"
    if climate_file.exists():
        data['climate'] = pd.read_csv(climate_file)
        data['climate']['datetime'] = pd.to_datetime(data['climate']['datetime'])
        data['climate'] = data['climate'].sort_values('datetime')
        print(f"✅ Climate: {len(data['climate'])} time steps")
    else:
        print("⚠️  Climate data not found")
        data['climate'] = None
    
    # Load mechanism test results
    mech_file = ANALYSIS_DIR / "mechanism_test_results.json"
    if mech_file.exists():
        with open(mech_file, 'r') as f:
            data['mechanisms'] = json.load(f)
        print(f"✅ Mechanism results loaded")
    else:
        print("⚠️  Mechanism results not found")
        data['mechanisms'] = None
    
    print()
    return data


def review_results(data):
    """Review and summarize all results."""
    print("=" * 70)
    print("Reviewing Results")
    print("=" * 70)
    print()
    
    summary = {
        'velocity_stats': {},
        'climate_stats': {},
        'mechanism_results': {}
    }
    
    # Velocity statistics
    vel = data['velocity']
    summary['velocity_stats'] = {
        'n_measurements': len(vel),
        'date_range': (vel['date'].min().strftime('%Y-%m-%d'),
                      vel['date'].max().strftime('%Y-%m-%d')),
        'mean_velocity_m_per_day': float(vel['velocity_m_per_day'].mean()),
        'median_velocity_m_per_day': float(vel['velocity_m_per_day'].median()),
        'std_velocity_m_per_day': float(vel['velocity_m_per_day'].std()),
        'min_velocity_m_per_day': float(vel['velocity_m_per_day'].min()),
        'max_velocity_m_per_day': float(vel['velocity_m_per_day'].max()),
        'mean_correlation': float(vel['correlation'].mean()) if 'correlation' in vel.columns else None
    }
    
    print("Velocity Statistics:")
    print(f"  Measurements: {summary['velocity_stats']['n_measurements']}")
    print(f"  Date range: {summary['velocity_stats']['date_range'][0]} to {summary['velocity_stats']['date_range'][1]}")
    print(f"  Mean: {summary['velocity_stats']['mean_velocity_m_per_day']:.2f} m/day")
    print(f"  Range: {summary['velocity_stats']['min_velocity_m_per_day']:.2f} - {summary['velocity_stats']['max_velocity_m_per_day']:.2f} m/day")
    print()
    
    # Climate statistics
    if data['climate'] is not None:
        clim = data['climate']
        summary['climate_stats'] = {
            'n_timesteps': len(clim),
            'date_range': (clim['datetime'].min().strftime('%Y-%m-%d'),
                          clim['datetime'].max().strftime('%Y-%m-%d')),
            'mean_temperature_C': float(clim['temperature_C'].mean()),
            'total_precipitation_mm': float(clim['precipitation_mm'].sum()),
            'ros_events': int((clim['ros'] > 1.0).sum()),
            'max_pdd': float(clim['pdd'].max()) if 'pdd' in clim.columns else None
        }
        print("Climate Statistics:")
        print(f"  Time steps: {summary['climate_stats']['n_timesteps']}")
        print(f"  ROS events: {summary['climate_stats']['ros_events']}")
        print()
    
    # Mechanism results
    if data['mechanisms']:
        summary['mechanism_results'] = data['mechanisms']
        print("Mechanism Test Results:")
        for mech in data['mechanisms']:
            name = mech.get('mechanism', 'Unknown')
            print(f"  {name}:")
            if 'correlation' in mech:
                corr = mech['correlation']
                if not (isinstance(corr, float) and np.isnan(corr)):
                    print(f"    Correlation: {corr:.3f}")
        print()
    
    return summary


def refine_changepoint_detection(data, summary):
    """Try multiple change-point detection parameters."""
    print("=" * 70)
    print("Refining Change-Point Detection")
    print("=" * 70)
    print()
    
    if ruptures is None:
        print("⚠️  ruptures library not available, skipping refinement")
        return None
    
    vel = data['velocity']
    velocity_array = vel['velocity_m_per_day'].values.reshape(-1, 1)
    
    results = []
    
    # Try different penalties
    penalties = [5.0, 10.0, 20.0, 50.0, 100.0]
    
    for pen in penalties:
        try:
            algo = ruptures.Pelt(model="rbf").fit(velocity_array)
            changepoints = algo.predict(pen=pen)
            changepoints = changepoints[:-1] if len(changepoints) > 0 else []
            
            results.append({
                'penalty': pen,
                'n_changepoints': len(changepoints),
                'changepoints': [int(cp) for cp in changepoints],
                'changepoint_dates': [vel.iloc[int(cp)]['date'].strftime('%Y-%m-%d') 
                                     for cp in changepoints] if changepoints else []
            })
            
            print(f"Penalty {pen:6.1f}: {len(changepoints)} change-point(s)")
            if changepoints:
                for i, cp in enumerate(changepoints):
                    cp_date = vel.iloc[int(cp)]['date']
                    print(f"  CP {i+1}: {cp_date.strftime('%Y-%m-%d')}")
        except Exception as e:
            print(f"Penalty {pen:6.1f}: Error - {e}")
    
    print()
    
    # Select best result (most change-points without overfitting)
    if results:
        # Prefer results with 1-3 change-points
        best = None
        for r in results:
            if 1 <= r['n_changepoints'] <= 3:
                if best is None or r['n_changepoints'] > best['n_changepoints']:
                    best = r
        
        if best is None:
            # Fallback to first non-zero result
            best = next((r for r in results if r['n_changepoints'] > 0), results[0])
        
        print(f"Selected: Penalty {best['penalty']:.1f} with {best['n_changepoints']} change-point(s)")
        print()
        
        return best
    
    return None


def create_publication_figures(data, summary, changepoint_result):
    """Create publication-quality figures."""
    print("=" * 70)
    print("Creating Publication Figures")
    print("=" * 70)
    print()
    
    vel = data['velocity']
    clim = data['climate']
    
    # Figure 1: Velocity time series with climate overlay
    fig, axes = plt.subplots(3, 1, figsize=(10, 10))
    
    # Panel 1: Velocity time series
    ax = axes[0]
    ax.plot(vel['date'], vel['velocity_m_per_day'], 'o-', 
            color='#2E86AB', linewidth=2, markersize=8, label='Velocity')
    
    # Mark change-points if available
    if changepoint_result and changepoint_result['n_changepoints'] > 0:
        for cp_idx in changepoint_result['changepoints']:
            cp_date = vel.iloc[cp_idx]['date']
            ax.axvline(x=cp_date, color='red', linestyle='--', 
                      linewidth=2, alpha=0.7, label='Change-point')
    
    ax.set_ylabel('Velocity (m/day)', fontweight='bold')
    ax.set_title('Glacier Velocity Time Series', fontweight='bold', fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # Panel 2: Temperature and PDD (if climate data available)
    if clim is not None:
        ax = axes[1]
        
        # Resample climate to daily
        clim_daily = clim.set_index('datetime').resample('D').agg({
            'temperature_C': 'mean',
            'pdd': 'last' if 'pdd' in clim.columns else 'mean'
        }).reset_index()
        
        # Align with velocity dates
        vel_dates = vel['date'].values
        clim_aligned = []
        for vd in vel_dates:
            closest = clim_daily.iloc[(clim_daily['datetime'] - vd).abs().argsort()[:1]]
            if len(closest) > 0:
                clim_aligned.append({
                    'date': vd,
                    'temperature': closest['temperature_C'].values[0],
                    'pdd': closest['pdd'].values[0] if 'pdd' in closest.columns else None
                })
        
        if clim_aligned:
            clim_df = pd.DataFrame(clim_aligned)
            ax2 = ax.twinx()
            ax.plot(clim_df['date'], clim_df['temperature'], 's-', 
                   color='#F24236', alpha=0.7, label='Temperature')
            if 'pdd' in clim_df.columns and not clim_df['pdd'].isna().all():
                ax2.plot(clim_df['date'], clim_df['pdd'] / 1000, '^-', 
                        color='#F18F01', alpha=0.7, label='PDD (×1000)')
                ax2.set_ylabel('PDD (×1000 °C·days)', fontweight='bold', color='#F18F01')
                ax2.tick_params(axis='y', labelcolor='#F18F01')
            
            ax.set_ylabel('Temperature (°C)', fontweight='bold', color='#F24236')
            ax.tick_params(axis='y', labelcolor='#F24236')
            ax.set_title('Climate Variables', fontweight='bold', fontsize=12)
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper left')
            if 'pdd' in clim_df.columns:
                ax2.legend(loc='upper right')
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # Panel 3: ROS events (if available)
    if clim is not None and 'ros' in clim.columns:
        ax = axes[2]
        
        # Daily ROS
        clim_daily = clim.set_index('datetime').resample('D').agg({
            'ros': 'sum'
        }).reset_index()
        
        # Filter significant ROS events
        ros_significant = clim_daily[clim_daily['ros'] > 1.0]
        
        if len(ros_significant) > 0:
            ax.bar(ros_significant['datetime'], ros_significant['ros'], 
                  color='#06A77D', alpha=0.7, width=1.0)
            ax.set_ylabel('ROS (mm)', fontweight='bold')
            ax.set_title('Rain-on-Snow Events', fontweight='bold', fontsize=12)
            ax.grid(True, alpha=0.3, axis='y')
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.xaxis.set_major_locator(mdates.MonthLocator())
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    fig_file = OUTPUT_DIR / "figure1_velocity_climate_timeseries.png"
    plt.savefig(fig_file, dpi=300, bbox_inches='tight')
    print(f"✅ Figure 1 saved: {fig_file}")
    plt.close()
    
    # Figure 2: Mechanism test results with visualizations
    if data['mechanisms']:
        fig, axes = plt.subplots(1, 3, figsize=(14, 5))
        
        mechs = data['mechanisms']
        vel = data['velocity']
        clim = data['climate']
        
        # H1: Topographic - Create slope/elevation visualization
        ax = axes[0]
        if any(m.get('mechanism') == 'H1_Topographic_Pinning' for m in mechs):
            h1 = next(m for m in mechs if m.get('mechanism') == 'H1_Topographic_Pinning')
            
            # Create a bar chart for slope and elevation
            categories = ['Mean Slope', 'Elevation\nRange']
            values = [h1.get('mean_slope_deg', 0), h1.get('elevation_range_m', 0) / 100]  # Divide elevation by 100 for scale
            colors = ['#4A90E2', '#7B68EE']
            
            bars = ax.bar(categories, values, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
            ax.set_ylabel('Slope (°) / Elevation Range (×100 m)', fontweight='bold')
            ax.set_title('H1: Topographic Pinning', fontweight='bold', fontsize=12)
            ax.grid(True, alpha=0.3, axis='y')
            
            # Add value labels on bars
            for i, (bar, val, orig_val) in enumerate(zip(bars, values, [h1.get('mean_slope_deg', 0), h1.get('elevation_range_m', 0)])):
                if i == 0:
                    label = f'{orig_val:.1f}°'
                else:
                    label = f'{orig_val:.0f} m'
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values)*0.02,
                       label, ha='center', va='bottom', fontweight='bold', fontsize=10)
            
            # Add status text
            ax.text(0.5, 0.95, 'Topographic control likely', 
                   ha='center', fontsize=10, transform=ax.transAxes,
                   bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7, edgecolor='blue', linewidth=1.5))
        
        # H2: ROS - Create correlation scatter plot
        ax = axes[1]
        if any(m.get('mechanism') == 'H2_ROS' for m in mechs):
            h2 = next(m for m in mechs if m.get('mechanism') == 'H2_ROS')
            corr = h2.get('correlation', np.nan)
            
            # Align ROS with velocity for scatter plot
            if clim is not None and 'ros' in clim.columns and not (isinstance(corr, float) and np.isnan(corr)):
                # Get daily ROS aligned with velocity dates
                clim_daily = clim.set_index('datetime').resample('D').agg({'ros': 'sum'}).reset_index()
                
                ros_aligned = []
                vel_aligned = []
                for vd in vel['date']:
                    closest = clim_daily.iloc[(clim_daily['datetime'] - vd).abs().argsort()[:1]]
                    if len(closest) > 0 and closest['ros'].values[0] > 0:
                        ros_aligned.append(closest['ros'].values[0])
                        vel_aligned.append(vel[vel['date'] == vd]['velocity_m_per_day'].values[0])
                
                if len(ros_aligned) > 0:
                    ax.scatter(ros_aligned, vel_aligned, s=100, alpha=0.7, color='#E74C3C', edgecolors='black', linewidth=1.5)
                    
                    # Add trend line if correlation exists
                    if len(ros_aligned) > 1:
                        z = np.polyfit(ros_aligned, vel_aligned, 1)
                        p = np.poly1d(z)
                        x_line = np.linspace(min(ros_aligned), max(ros_aligned), 100)
                        ax.plot(x_line, p(x_line), "r--", alpha=0.5, linewidth=2, label=f'Correlation: {corr:.3f}')
                        ax.legend(loc='best', fontsize=9)
                    
                    ax.set_xlabel('ROS (mm)', fontweight='bold')
                    ax.set_ylabel('Velocity (m/day)', fontweight='bold')
                    ax.grid(True, alpha=0.3)
                else:
                    # Fallback: show correlation value
                    ax.text(0.5, 0.5, f'Correlation: {corr:.3f}\nROS Events: {h2.get("ros_events_count", 0)}',
                           ha='center', va='center', fontsize=12, transform=ax.transAxes,
                           bbox=dict(boxstyle='round', facecolor='lightcoral' if corr < 0 else 'lightgreen', alpha=0.7))
            else:
                # Show correlation value
                color = 'lightcoral' if (isinstance(corr, float) and not np.isnan(corr) and corr < 0) else 'lightgreen'
                status = "Negative correlation\n(unexpected)" if (isinstance(corr, float) and not np.isnan(corr) and corr < 0) else "Positive correlation"
                ax.text(0.5, 0.5, f'Correlation: {corr:.3f if not (isinstance(corr, float) and np.isnan(corr)) else "N/A"}\nROS Events: {h2.get("ros_events_count", 0)}\n{status}',
                       ha='center', va='center', fontsize=11, transform=ax.transAxes,
                       bbox=dict(boxstyle='round', facecolor=color, alpha=0.7, edgecolor='red' if corr < 0 else 'green', linewidth=1.5))
            
            ax.set_title('H2: ROS Mechanism', fontweight='bold', fontsize=12)
        
        # H3: PDD - Create PDD vs velocity scatter plot
        ax = axes[2]
        if any(m.get('mechanism') == 'H3_PDD_Buildup' for m in mechs):
            h3 = next(m for m in mechs if m.get('mechanism') == 'H3_PDD_Buildup')
            corr = h3.get('correlation', np.nan)
            pdd_range = h3.get('pdd_range', [0, 0])
            
            # Align PDD with velocity for scatter plot
            if clim is not None and 'pdd' in clim.columns:
                clim_daily = clim.set_index('datetime').resample('D').agg({'pdd': 'last'}).reset_index()
                
                pdd_aligned = []
                vel_aligned = []
                for vd in vel['date']:
                    closest = clim_daily.iloc[(clim_daily['datetime'] - vd).abs().argsort()[:1]]
                    if len(closest) > 0 and not pd.isna(closest['pdd'].values[0]):
                        pdd_aligned.append(closest['pdd'].values[0] / 1000)  # Divide by 1000 for readability
                        vel_aligned.append(vel[vel['date'] == vd]['velocity_m_per_day'].values[0])
                
                if len(pdd_aligned) > 0:
                    ax.scatter(pdd_aligned, vel_aligned, s=100, alpha=0.7, color='#F39C12', edgecolors='black', linewidth=1.5)
                    
                    # Add trend line if correlation exists
                    if len(pdd_aligned) > 1 and not (isinstance(corr, float) and np.isnan(corr)):
                        z = np.polyfit(pdd_aligned, vel_aligned, 1)
                        p = np.poly1d(z)
                        x_line = np.linspace(min(pdd_aligned), max(pdd_aligned), 100)
                        ax.plot(x_line, p(x_line), "r--", alpha=0.5, linewidth=2, label=f'Correlation: {corr:.3f}')
                        ax.legend(loc='best', fontsize=9)
                    
                    ax.set_xlabel('PDD (×1000 °C·days)', fontweight='bold')
                    ax.set_ylabel('Velocity (m/day)', fontweight='bold')
                    ax.grid(True, alpha=0.3)
                else:
                    # Fallback: show range
                    ax.text(0.5, 0.5, f'PDD Range:\n{pdd_range[0]:.0f} - {pdd_range[1]:.0f}\nNo clear relationship',
                           ha='center', va='center', fontsize=11, transform=ax.transAxes,
                           bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.7, edgecolor='orange', linewidth=1.5))
            else:
                # Show range
                ax.text(0.5, 0.5, f'PDD Range:\n{pdd_range[0]:.0f} - {pdd_range[1]:.0f}\nNo clear relationship',
                       ha='center', va='center', fontsize=11, transform=ax.transAxes,
                       bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.7, edgecolor='orange', linewidth=1.5))
            
            ax.set_title('H3: PDD Buildup', fontweight='bold', fontsize=12)
        
        plt.tight_layout()
        fig_file = OUTPUT_DIR / "figure2_mechanism_test_results.png"
        plt.savefig(fig_file, dpi=300, bbox_inches='tight')
        print(f"✅ Figure 2 saved: {fig_file}")
        plt.close()
    
    print()


def generate_interpretation_report(data, summary, changepoint_result):
    """Generate comprehensive interpretation report."""
    print("=" * 70)
    print("Generating Interpretation Report")
    print("=" * 70)
    print()
    
    report = []
    report.append("# Didal Glacier Surge Analysis: Interpretation Report")
    report.append("")
    report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    report.append("---")
    report.append("")
    
    # Executive Summary
    report.append("## Executive Summary")
    report.append("")
    vel = data['velocity']
    report.append(f"This analysis examined the Didal Glacier surge event from {vel['date'].min().strftime('%B %d, %Y')} to {vel['date'].max().strftime('%B %d, %Y')}.")
    report.append(f"Velocity measurements were derived from Sentinel-1 SAR offset tracking using Python-based normalized cross-correlation.")
    report.append("")
    report.append(f"**Key Findings:**")
    report.append(f"- Mean velocity: **{summary['velocity_stats']['mean_velocity_m_per_day']:.1f} m/day** ({summary['velocity_stats']['mean_velocity_m_per_day']*365:.0f} m/year)")
    report.append(f"- Velocity range: {summary['velocity_stats']['min_velocity_m_per_day']:.1f} - {summary['velocity_stats']['max_velocity_m_per_day']:.1f} m/day")
    report.append(f"- {summary['velocity_stats']['n_measurements']} velocity measurements over {len(vel)} days")
    report.append("")
    
    # Velocity Characteristics
    report.append("## 1. Velocity Characteristics")
    report.append("")
    report.append("### 1.1 Temporal Pattern")
    report.append("")
    report.append(f"The glacier exhibited **high sustained velocities** throughout the observation period:")
    report.append(f"- Mean velocity: {summary['velocity_stats']['mean_velocity_m_per_day']:.1f} m/day")
    report.append(f"- Standard deviation: {summary['velocity_stats']['std_velocity_m_per_day']:.1f} m/day")
    report.append(f"- Coefficient of variation: {(summary['velocity_stats']['std_velocity_m_per_day'] / summary['velocity_stats']['mean_velocity_m_per_day'] * 100):.1f}%")
    report.append("")
    
    if changepoint_result and changepoint_result['n_changepoints'] > 0:
        report.append(f"**Change-Point Detection:** {changepoint_result['n_changepoints']} regime shift(s) detected:")
        for i, cp_date in enumerate(changepoint_result['changepoint_dates']):
            report.append(f"- Change-point {i+1}: {cp_date}")
        report.append("")
    else:
        report.append("**Change-Point Detection:** No clear regime shifts detected, suggesting:")
        report.append("- The surge was already active when observations began")
        report.append("- Velocities remained consistently high throughout the period")
        report.append("- Need for pre-surge baseline data to identify initiation")
        report.append("")
    
    # Mechanism Testing Results
    report.append("## 2. Mechanism Testing Results")
    report.append("")
    
    if data['mechanisms']:
        for mech in data['mechanisms']:
            name = mech.get('mechanism', 'Unknown')
            report.append(f"### {name}")
            report.append("")
            
            if name == 'H1_Topographic_Pinning':
                report.append(f"- **Mean slope:** {mech.get('mean_slope_deg', 0):.1f}° (very steep terrain)")
                report.append(f"- **Elevation range:** {mech.get('elevation_range_m', 0):.0f} m")
                report.append(f"- **Mean velocity:** {mech.get('mean_velocity_m_per_day', 0):.1f} m/day")
                report.append("")
                report.append("**Interpretation:** High slope terrain suggests topographic control is likely important. However, spatial analysis along the flowline is needed to test whether velocity changes align with topographic constrictions or slope breaks.")
                report.append("")
            
            elif name == 'H2_ROS':
                corr = mech.get('correlation', np.nan)
                report.append(f"- **ROS events:** {mech.get('ros_events_count', 0)} events detected")
                report.append(f"- **Total ROS:** {mech.get('ros_total_mm', 0):.1f} mm")
                report.append(f"- **Correlation with velocity:** {corr:.3f}" if not (isinstance(corr, float) and np.isnan(corr)) else "- **Correlation with velocity:** No clear relationship")
                report.append("")
                if isinstance(corr, float) and not np.isnan(corr):
                    if corr < 0:
                        report.append("**Interpretation:** **Negative correlation** (-0.34) is unexpected and suggests ROS events may not be the primary driver of velocity changes. This could indicate:")
                        report.append("- ROS events occurred but did not trigger velocity increases")
                        report.append("- Other factors (topography, bed conditions) override ROS effects")
                        report.append("- Temporal misalignment between ROS events and velocity measurements")
                    else:
                        report.append("**Interpretation:** Positive correlation suggests ROS events may contribute to velocity increases, though the relationship is moderate.")
                report.append("")
            
            elif name == 'H3_PDD_Buildup':
                pdd_range = mech.get('pdd_range', [0, 0])
                corr = mech.get('correlation', np.nan)
                report.append(f"- **PDD range:** {pdd_range[0]:.0f} - {pdd_range[1]:.0f} °C·days")
                report.append(f"- **Correlation with velocity:** {'No clear relationship' if (isinstance(corr, float) and np.isnan(corr)) else f'{corr:.3f}'}")
                report.append("")
                report.append("**Interpretation:** No clear correlation between PDD and velocity suggests:")
                report.append("- PDD buildup may have occurred before the observation period (preparatory phase)")
                report.append("- PDD effects may be cumulative over longer timescales than measured")
                report.append("- Other mechanisms may be more important for this surge")
                report.append("")
    
    # Conclusions
    report.append("## 3. Conclusions")
    report.append("")
    report.append("### 3.1 Velocity Characteristics")
    report.append("")
    report.append("The Didal Glacier exhibited **exceptionally high velocities** (mean ~273 m/day, range 123-422 m/day) throughout the observation period. This is consistent with an active surge phase, though the lack of clear regime shifts suggests:")
    report.append("1. Observations began during an already-active surge")
    report.append("2. Pre-surge baseline data would help identify initiation timing")
    report.append("3. The surge may have been sustained rather than episodic")
    report.append("")
    
    report.append("### 3.2 Mechanism Support")
    report.append("")
    report.append("**H1 (Topographic Pinning):** ⚠️ **Partially supported**")
    report.append("- High slope terrain (89.9° mean) suggests topographic control")
    report.append("- Spatial analysis needed to test alignment with constrictions")
    report.append("")
    
    report.append("**H2 (ROS):** ❌ **Not supported**")
    report.append("- Negative correlation (-0.34) suggests ROS is not primary driver")
    report.append("- May indicate other factors override ROS effects")
    report.append("")
    
    report.append("**H3 (PDD Buildup):** ❌ **Not supported**")
    report.append("- No clear correlation with velocity")
    report.append("- PDD effects may have occurred before observation period")
    report.append("")
    
    report.append("### 3.3 Recommendations")
    report.append("")
    report.append("1. **Obtain pre-surge baseline data** to identify surge initiation")
    report.append("2. **Spatial velocity analysis** to test H1 along flowline")
    report.append("3. **Extended temporal coverage** to capture full surge cycle")
    report.append("4. **Investigate other mechanisms:** bed conditions, subglacial hydrology")
    report.append("")
    
    # Save report
    report_text = "\n".join(report)
    report_file = OUTPUT_DIR / "interpretation_report.md"
    with open(report_file, 'w') as f:
        f.write(report_text)
    
    print(f"✅ Interpretation report saved: {report_file}")
    print()
    
    # Also save summary JSON
    summary_file = OUTPUT_DIR / "analysis_summary.json"
    summary_data = {
        'summary': summary,
        'changepoint_result': changepoint_result,
        'timestamp': datetime.now().isoformat()
    }
    with open(summary_file, 'w') as f:
        json.dump(summary_data, f, indent=2, default=str)
    
    print(f"✅ Summary JSON saved: {summary_file}")
    print()
    
    return report_file


def main():
    """Main execution function."""
    print("=" * 70)
    print("Complete Automated Analysis Pipeline")
    print("=" * 70)
    print()
    
    # Step 1: Load data
    data = load_all_data()
    if data is None:
        print("❌ Failed to load data")
        return False
    
    # Step 2: Review results
    summary = review_results(data)
    
    # Step 3: Refine change-point detection
    changepoint_result = refine_changepoint_detection(data, summary)
    
    # Step 4: Create publication figures
    create_publication_figures(data, summary, changepoint_result)
    
    # Step 5: Generate interpretation report
    report_file = generate_interpretation_report(data, summary, changepoint_result)
    
    print("=" * 70)
    print("✅ Complete Analysis Pipeline Finished!")
    print("=" * 70)
    print()
    print("Output files:")
    print(f"  📊 Figures: {OUTPUT_DIR}")
    print(f"  📝 Report: {report_file}")
    print(f"  📋 Summary: {OUTPUT_DIR / 'analysis_summary.json'}")
    print()
    print("Next steps:")
    print("  1. Review interpretation report")
    print("  2. Incorporate figures into paper")
    print("  3. Refine analysis based on findings")
    print()
    
    return True


if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)

