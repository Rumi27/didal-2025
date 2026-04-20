#!/usr/bin/env python3
"""
Apply PELT (Pruned Exact Linear Time) algorithm for change-point detection
on velocity time series.

Identifies regime shifts:
- Pre-surge (baseline)
- Surge initiation
- Active surge
- Braking transition
- Post-surge

Requirements:
    pip install ruptures numpy pandas matplotlib

Output:
    - Change-point locations
    - Regime labels
    - Visualization
"""

import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List
import matplotlib.pyplot as plt

try:
    import ruptures
except ImportError:
    print("⚠️  ruptures not installed. Install with: pip install ruptures")
    ruptures = None

# Input/Output directories
INPUT_DIR = Path("satellite_data/sentinel1/processed")
OUTPUT_DIR = Path("satellite_data/sentinel1/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_velocity_timeseries(csv_file: Path) -> pd.DataFrame:
    """Load velocity time series from CSV."""
    print("=" * 70)
    print("Loading Velocity Time Series")
    print("=" * 70)
    print()
    
    df = pd.read_csv(csv_file)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    print(f"Loaded {len(df)} time steps")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"Velocity range: {df['velocity_m_per_day'].min():.4f} - {df['velocity_m_per_day'].max():.4f} m/day")
    print()
    
    return df


def apply_pelt_changepoint_detection(velocity: np.ndarray, max_changepoints: int = 5) -> List[int]:
    """
    Apply PELT algorithm for change-point detection.
    
    Args:
        velocity: Velocity time series array
        max_changepoints: Maximum number of change-points to detect
    
    Returns:
        List of change-point indices
    """
    if ruptures is None:
        print("❌ ruptures library not available")
        return []
    
    print("=" * 70)
    print("Applying PELT Change-Point Detection")
    print("=" * 70)
    print()
    
    # Prepare data (2D array for ruptures)
    data = velocity.reshape(-1, 1)
    
    # Use PELT algorithm with L2 cost function
    algo = ruptures.Pelt(model="rbf").fit(data)
    
    # Detect change-points (penalty parameter)
    # Higher penalty = fewer change-points
    # Use BIC penalty (try different API versions)
    try:
        # New API (ruptures >= 1.1.0)
        from ruptures.costs import CostRBF
        penalty = len(data) * np.log(len(data))  # BIC penalty
        changepoints = algo.predict(pen=penalty)
    except:
        try:
            # Alternative: use fixed penalty
            penalty = 10.0  # Adjust based on data scale
            changepoints = algo.predict(pen=penalty)
        except:
            # Fallback: detect with max segments
            changepoints = algo.predict(n_bkps=max_changepoints)
    
    # Remove last point (end of series)
    changepoints = changepoints[:-1] if len(changepoints) > 0 else []
    
    print(f"Detected {len(changepoints)} change-point(s)")
    for i, cp in enumerate(changepoints):
        print(f"  Change-point {i+1}: index {cp}")
    print()
    
    return changepoints


def identify_regimes(df: pd.DataFrame, changepoints: List[int]) -> pd.DataFrame:
    """Identify regimes based on change-points."""
    print("=" * 70)
    print("Identifying Regimes")
    print("=" * 70)
    print()
    
    # Add regime labels
    df['regime'] = 'unknown'
    df['regime_id'] = 0
    
    if len(changepoints) == 0:
        print("⚠️  No change-points detected, using single regime")
        df['regime'] = 'single_regime'
        return df
    
    # Define regimes based on number of change-points
    regimes = []
    changepoints_with_ends = [0] + sorted(changepoints) + [len(df)]
    
    for i in range(len(changepoints_with_ends) - 1):
        start_idx = changepoints_with_ends[i]
        end_idx = changepoints_with_ends[i + 1]
        
        # Compute mean velocity for this segment
        segment_vel = df.iloc[start_idx:end_idx]['velocity_m_per_day'].mean()
        
        # Classify regime based on velocity (adjusted for m/day scale)
        # Our velocities are in m/day (100-400 range), not m/year
        if segment_vel < 50:
            regime_name = 'pre_surge' if i == 0 else 'post_surge'
        elif segment_vel < 150:
            regime_name = 'surge_initiation'
        elif segment_vel < 300:
            regime_name = 'active_surge'
        else:
            regime_name = 'peak_surge'
        
        regimes.append({
            'start_idx': start_idx,
            'end_idx': end_idx,
            'regime': regime_name,
            'mean_velocity': segment_vel
        })
        
        # Label data points
        df.loc[start_idx:end_idx-1, 'regime'] = regime_name
        df.loc[start_idx:end_idx-1, 'regime_id'] = i
    
    print("Regimes identified:")
    for reg in regimes:
        start_date = df.iloc[reg['start_idx']]['date']
        end_date = df.iloc[reg['end_idx']-1]['date']
        print(f"  {reg['regime']}: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"    Mean velocity: {reg['mean_velocity']:.4f} m/day")
    print()
    
    return df


def save_results(df: pd.DataFrame, changepoints: List[int], output_dir: Path):
    """Save change-point detection results."""
    print("Saving results...")
    print()
    
    # Save labeled time series
    csv_file = output_dir / "velocity_timeseries_with_regimes.csv"
    df.to_csv(csv_file, index=False)
    print(f"✅ Time series with regimes saved: {csv_file}")
    
    # Save change-point summary
    summary_file = output_dir / "changepoint_summary.txt"
    with open(summary_file, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("Change-Point Detection Summary\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Total change-points detected: {len(changepoints)}\n\n")
        
        for i, cp in enumerate(changepoints):
            cp_date = df.iloc[cp]['date']
            f.write(f"Change-point {i+1}:\n")
            f.write(f"  Index: {cp}\n")
            f.write(f"  Date: {cp_date}\n")
            f.write(f"  Velocity: {df.iloc[cp]['velocity_m_per_day']:.4f} m/day\n\n")
        
        # Regime summary
        f.write("Regimes:\n")
        for regime in df['regime'].unique():
            regime_data = df[df['regime'] == regime]
            f.write(f"  {regime}:\n")
            f.write(f"    Duration: {len(regime_data)} time steps\n")
            f.write(f"    Mean velocity: {regime_data['velocity_m_per_day'].mean():.4f} m/day\n")
            f.write(f"    Date range: {regime_data['date'].min()} to {regime_data['date'].max()}\n\n")
    
    print(f"✅ Summary saved: {summary_file}")
    print()
    
    return csv_file, summary_file


def create_visualizations(df: pd.DataFrame, changepoints: List[int], output_dir: Path):
    """Create visualization plots."""
    print("Creating visualizations...")
    print()
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    
    # Velocity time series with change-points
    ax = axes[0]
    
    # Plot velocity (handle missing velocity_std column)
    if 'velocity_std' in df.columns:
        ax.errorbar(df['date'], df['velocity_m_per_day'],
                    yerr=df['velocity_std'], fmt='o-', capsize=3, alpha=0.7, label='Velocity')
    else:
        ax.plot(df['date'], df['velocity_m_per_day'], 'o-', alpha=0.7, label='Velocity')
    
    # Mark change-points
    for cp in changepoints:
        cp_date = df.iloc[cp]['date']
        ax.axvline(x=cp_date, color='red', linestyle='--', alpha=0.7, linewidth=2)
        ax.text(cp_date, ax.get_ylim()[1] * 0.9, f'CP {changepoints.index(cp)+1}',
                rotation=90, ha='right', va='top', fontsize=9)
    
    # Color by regime
    for regime in df['regime'].unique():
        regime_data = df[df['regime'] == regime]
        ax.scatter(regime_data['date'], regime_data['velocity_m_per_day'],
                  alpha=0.3, s=50, label=regime.replace('_', ' ').title())
    
    ax.set_ylabel('Velocity (m/day)')
    ax.set_title('Velocity Time Series with Change-Points')
    ax.legend(loc='best', fontsize=8)
    ax.grid(True, alpha=0.3)
    
    # Regime timeline
    ax = axes[1]
    
    # Create regime timeline
    regime_colors = {
        'pre_surge': 'blue',
        'surge_initiation': 'yellow',
        'active_surge': 'orange',
        'peak_surge': 'red',
        'post_surge': 'green',
        'unknown': 'gray'
    }
    
    for regime in df['regime'].unique():
        regime_data = df[df['regime'] == regime]
        color = regime_colors.get(regime, 'gray')
        ax.barh(0, len(regime_data), left=regime_data.index.min(),
                height=0.5, color=color, alpha=0.7, label=regime.replace('_', ' ').title())
    
    # Mark change-points
    for cp in changepoints:
        ax.axvline(x=cp, color='red', linestyle='--', alpha=0.7, linewidth=2)
    
    ax.set_xlabel('Time Step Index')
    ax.set_ylabel('Regime')
    ax.set_title('Regime Timeline')
    ax.set_yticks([0])
    ax.set_yticklabels([''])
    ax.legend(loc='best', fontsize=8)
    ax.grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout()
    
    plot_file = output_dir / "changepoint_detection_plot.png"
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"✅ Plot saved: {plot_file}")
    plt.close()
    
    return plot_file


def main():
    """Main processing function."""
    print("=" * 70)
    print("Change-Point Detection (PELT Algorithm)")
    print("=" * 70)
    print()
    
    # Load velocity time series (try Python-calculated first, then fallback)
    csv_file = INPUT_DIR / "velocity_timeseries_python.csv"
    if not csv_file.exists():
        csv_file = INPUT_DIR / "velocity_timeseries.csv"
        if not csv_file.exists():
            print(f"❌ Velocity time series not found")
            print(f"   Expected: {INPUT_DIR / 'velocity_timeseries_python.csv'}")
            print(f"   Or: {INPUT_DIR / 'velocity_timeseries.csv'}")
            print("   Please run calculate_velocity_python.py first")
            return False
    
    df = load_velocity_timeseries(csv_file)
    
    # Apply PELT
    changepoints = apply_pelt_changepoint_detection(df['velocity_m_per_day'].values)
    
    # Identify regimes
    df = identify_regimes(df, changepoints)
    
    # Save results
    csv_file, summary_file = save_results(df, changepoints, OUTPUT_DIR)
    
    # Create visualizations
    plot_file = create_visualizations(df, changepoints, OUTPUT_DIR)
    
    print("=" * 70)
    print("✅ Processing Complete!")
    print("=" * 70)
    print()
    print("Output files:")
    print(f"  - {csv_file}")
    print(f"  - {summary_file}")
    print(f"  - {plot_file}")
    print()
    print("📋 Next steps:")
    print("  1. Review change-points and regime classifications")
    print("  2. Align with climate derivatives for mechanism testing")
    print("  3. Test mechanisms H1, H2, H3")
    print()
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

