#!/usr/bin/env python3
"""
Calculate PELT change-points with confidence metrics (CROPS, BIC/MBIC) and deceleration rates.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
import warnings
warnings.filterwarnings('ignore')

try:
    from ruptures import Pelt, Binseg, Window
    from ruptures.costs import CostRbf, CostL1, CostL2
    from ruptures.metrics import hausdorff, randindex
    RUPTURES_AVAILABLE = True
except ImportError:
    print("⚠️  ruptures not available. Install with: pip install ruptures")
    RUPTURES_AVAILABLE = False

VELOCITY_TS_FILE = Path("satellite_data/sentinel1/processed/velocity_timeseries_python.csv")
OUTPUT_DIR = Path("processed_data/change_point_analysis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("PELT CHANGE-POINT DETECTION WITH CONFIDENCE METRICS")
print("=" * 80)

# Load velocity time series
df = pd.read_csv(VELOCITY_TS_FILE)
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date')

print(f"\nLoaded {len(df)} velocity measurements")
print(f"Date range: {df['date'].min()} to {df['date'].max()}")
print(f"Velocity range: {df['velocity_m_per_day'].min():.1f} to {df['velocity_m_per_day'].max():.1f} m/day")

# Check for irregular sampling
time_deltas = df['date'].diff().dt.days
print(f"\nTemporal sampling:")
print(f"  Mean interval: {time_deltas.mean():.1f} days")
print(f"  Interval range: {time_deltas.min():.0f} to {time_deltas.max():.0f} days")
print(f"  All intervals equal: {(time_deltas.nunique() == 1)}")

if not RUPTURES_AVAILABLE:
    print("\n⚠️  ruptures library not available. Using simplified analysis.")
    # Simple change-point detection using velocity differences
    df['velocity_diff'] = df['velocity_m_per_day'].diff()
    df['acceleration'] = df['velocity_diff'] / df['time_delta_days']
    
    # Find peak velocity
    peak_idx = df['velocity_m_per_day'].idxmax()
    peak_date = df.loc[peak_idx, 'date']
    peak_velocity = df.loc[peak_idx, 'velocity_m_per_day']
    
    print(f"\nPeak velocity: {peak_velocity:.1f} m/day on {peak_date.strftime('%Y-%m-%d')}")
    
    # Calculate deceleration after peak
    post_peak = df[df['date'] > peak_date]
    if len(post_peak) > 1:
        post_peak_sorted = post_peak.sort_values('date')
        deceleration_rates = []
        for i in range(1, len(post_peak_sorted)):
            dt = (post_peak_sorted.iloc[i]['date'] - post_peak_sorted.iloc[i-1]['date']).days
            dv = post_peak_sorted.iloc[i]['velocity_m_per_day'] - post_peak_sorted.iloc[i-1]['velocity_m_per_day']
            if dt > 0:
                deceleration_rates.append(dv / dt)
        
        if deceleration_rates:
            mean_deceleration = np.mean(deceleration_rates)
            std_deceleration = np.std(deceleration_rates)
            print(f"\nDeceleration rates:")
            print(f"  Mean: {mean_deceleration:.2f} m/day²")
            print(f"  Std: {std_deceleration:.2f} m/day²")
            print(f"  Range: {min(deceleration_rates):.2f} to {max(deceleration_rates):.2f} m/day²")
    
    exit(0)

# Prepare data for PELT
velocities = df['velocity_m_per_day'].values
dates = df['date'].values
n = len(velocities)

print(f"\nData preparation:")
print(f"  Number of points: {n}")
print(f"  Velocity array shape: {velocities.shape}")

# Convert to numpy array for PELT
velocities_2d = velocities.reshape(-1, 1)  # PELT expects 2D array

# Test multiple penalty values for sensitivity
penalty_values = [1, 2, 3, 4, 5, 10, 20, 50, 100]
print(f"\nTesting penalty values: {penalty_values}")

results = []
changepoint_times = {}

for penalty in penalty_values:
    print(f"\n  Testing penalty = {penalty}...")
    
    try:
        # PELT algorithm with RBF cost (suitable for piecewise constant)
        algo = Pelt(model="rbf", min_size=2, jump=1).fit(velocities_2d)
        changepoints = algo.predict(pen=penalty)
        
        # Remove last point (always included by PELT)
        if len(changepoints) > 0 and changepoints[-1] == n:
            changepoints = changepoints[:-1]
        
        n_changepoints = len(changepoints)
        
        # Convert indices to dates
        cp_dates = [dates[idx] for idx in changepoints] if len(changepoints) > 0 else []
        
        print(f"    Detected {n_changepoints} change-points")
        if cp_dates:
            for cp_date in cp_dates:
                print(f"      {cp_date.strftime('%Y-%m-%d')}")
        
        # Calculate BIC
        # BIC = n * log(σ²) + k * log(n)
        # where k = number of segments = n_changepoints + 1
        residuals = []
        if n_changepoints == 0:
            # Single segment
            mean_vel = np.mean(velocities)
            residuals = velocities - mean_vel
        else:
            # Multiple segments
            seg_starts = [0] + changepoints
            seg_ends = changepoints + [n]
            for start, end in zip(seg_starts, seg_ends):
                seg_vel = velocities[start:end]
                seg_mean = np.mean(seg_vel)
                residuals.extend(seg_vel - seg_mean)
        
        sigma_sq = np.var(residuals) if len(residuals) > 1 else 1e-10
        k = n_changepoints + 1  # Number of segments
        bic = n * np.log(sigma_sq) + k * np.log(n)
        
        # MBIC (Modified BIC) = BIC + 2 * k * log(n)
        mbic = bic + 2 * k * np.log(n)
        
        results.append({
            'penalty': penalty,
            'n_changepoints': n_changepoints,
            'changepoints': changepoints,
            'changepoint_dates': [d.strftime('%Y-%m-%d') for d in cp_dates],
            'bic': bic,
            'mbic': mbic,
            'sigma_sq': sigma_sq,
            'n_segments': k
        })
        
        if penalty == 10:  # Default penalty for reporting
            changepoint_times['default'] = {
                'penalty': penalty,
                'changepoints': cp_dates,
                'n_changepoints': n_changepoints
            }
    
    except Exception as e:
        print(f"    ⚠️  Error: {e}")
        import traceback
        traceback.print_exc()

# Select optimal penalty (minimum BIC or MBIC)
if results:
    df_results = pd.DataFrame(results)
    
    # Optimal penalty by BIC
    optimal_bic_idx = df_results['bic'].idxmin()
    optimal_bic = df_results.loc[optimal_bic_idx]
    
    # Optimal penalty by MBIC
    optimal_mbic_idx = df_results['mbic'].idxmin()
    optimal_mbic = df_results.loc[optimal_mbic_idx]
    
    print(f"\n" + "=" * 80)
    print("OPTIMAL PENALTY SELECTION")
    print("=" * 80)
    print(f"\nOptimal by BIC:")
    print(f"  Penalty: {optimal_bic['penalty']}")
    print(f"  BIC: {optimal_bic['bic']:.2f}")
    print(f"  Change-points: {optimal_bic['n_changepoints']}")
    if optimal_bic['changepoint_dates']:
        for cp_date in optimal_bic['changepoint_dates']:
            print(f"    {cp_date}")
    
    print(f"\nOptimal by MBIC:")
    print(f"  Penalty: {optimal_mbic['penalty']}")
    print(f"  MBIC: {optimal_mbic['mbic']:.2f}")
    print(f"  Change-points: {optimal_mbic['n_changepoints']}")
    if optimal_mbic['changepoint_dates']:
        for cp_date in optimal_mbic['changepoint_dates']:
            print(f"    {cp_date}")
    
    # Use MBIC-optimal for reporting (more conservative)
    optimal = optimal_mbic
    optimal_cp_dates = [datetime.strptime(d, '%Y-%m-%d') for d in optimal['changepoint_dates']]
    
    # Calculate CROPS (Change-points Retrieved Over Penalty Space) - range of penalties giving same number of change-points
    n_cp_optimal = optimal['n_changepoints']
    crops_penalties = df_results[df_results['n_changepoints'] == n_cp_optimal]['penalty'].values
    crops_range = (min(crops_penalties), max(crops_penalties)) if len(crops_penalties) > 0 else (None, None)
    
    print(f"\nCROPS (penalty range for {n_cp_optimal} change-points): {crops_range[0]} to {crops_range[1]}")
    
    # Calculate deceleration rates
    print(f"\n" + "=" * 80)
    print("DECELERATION RATE ANALYSIS")
    print("=" * 80)
    
    # Find peak velocity
    peak_idx = df['velocity_m_per_day'].idxmax()
    peak_date = df.loc[peak_idx, 'date']
    peak_velocity = df.loc[peak_idx, 'velocity_m_per_day']
    
    print(f"\nPeak velocity: {peak_velocity:.1f} m/day on {peak_date.strftime('%Y-%m-%d')}")
    
    # Calculate deceleration rates between segments
    deceleration_results = []
    
    if len(optimal_cp_dates) > 0:
        # Add peak date if not in change-points
        all_dates = sorted([peak_date] + optimal_cp_dates)
        
        # Calculate deceleration for each segment after peak
        for i in range(len(all_dates)):
            if all_dates[i] >= peak_date:
                if i < len(all_dates) - 1:
                    seg_start = all_dates[i]
                    seg_end = all_dates[i + 1]
                    
                    seg_data = df[(df['date'] >= seg_start) & (df['date'] < seg_end)]
                    if len(seg_data) >= 2:
                        seg_data = seg_data.sort_values('date')
                        v_start = seg_data.iloc[0]['velocity_m_per_day']
                        v_end = seg_data.iloc[-1]['velocity_m_per_day']
                        dt = (seg_end - seg_start).days
                        
                        if dt > 0:
                            decel_rate = (v_end - v_start) / dt
                            
                            # Uncertainty: use velocity uncertainty (LOD or σ_alg)
                            # Typical uncertainty: ~0.13 m/day (from σ_alg)
                            vel_uncertainty = 0.13  # m/day
                            decel_uncertainty = np.sqrt(2) * vel_uncertainty / dt  # Uncertainty in deceleration rate
                            
                            deceleration_results.append({
                                'segment_start': seg_start.strftime('%Y-%m-%d'),
                                'segment_end': seg_end.strftime('%Y-%m-%d'),
                                'duration_days': dt,
                                'v_start': v_start,
                                'v_end': v_end,
                                'deceleration_rate': decel_rate,
                                'deceleration_rate_uncertainty': decel_uncertainty
                            })
    else:
        # No change-points detected, calculate overall deceleration after peak
        post_peak = df[df['date'] > peak_date]
        if len(post_peak) >= 2:
            post_peak = post_peak.sort_values('date')
            v_start = post_peak.iloc[0]['velocity_m_per_day']
            v_end = post_peak.iloc[-1]['velocity_m_per_day']
            dt = (post_peak.iloc[-1]['date'] - post_peak.iloc[0]['date']).days
            
            if dt > 0:
                decel_rate = (v_end - v_start) / dt
                vel_uncertainty = 0.13  # m/day
                decel_uncertainty = np.sqrt(2) * vel_uncertainty / dt
                
                deceleration_results.append({
                    'segment_start': post_peak.iloc[0]['date'].strftime('%Y-%m-%d'),
                    'segment_end': post_peak.iloc[-1]['date'].strftime('%Y-%m-%d'),
                    'duration_days': dt,
                    'v_start': v_start,
                    'v_end': v_end,
                    'deceleration_rate': decel_rate,
                    'deceleration_rate_uncertainty': decel_uncertainty
                })
    
    # Print deceleration results
    if deceleration_results:
        print(f"\n{'Segment':<20} {'Duration':<12} {'V_start':<10} {'V_end':<10} {'Decel Rate':<15} {'Uncertainty':<15}")
        print("-" * 90)
        for res in deceleration_results:
            print(f"{res['segment_start']}-{res['segment_end']:<10} {res['duration_days']:<12.0f} "
                  f"{res['v_start']:<10.1f} {res['v_end']:<10.1f} "
                  f"{res['deceleration_rate']:<15.2f} ±{res['deceleration_rate_uncertainty']:<14.3f} m/day²")
        
        mean_decel = np.mean([r['deceleration_rate'] for r in deceleration_results])
        print(f"\nMean deceleration rate: {mean_decel:.2f} m/day²")
    else:
        print("\n⚠️  Could not calculate deceleration rates")
    
    # Save results
    summary = {
        'optimal_penalty': {
            'by_bic': {
                'penalty': float(optimal_bic['penalty']),
                'bic': float(optimal_bic['bic']),
                'n_changepoints': int(optimal_bic['n_changepoints']),
                'changepoint_dates': optimal_bic['changepoint_dates']
            },
            'by_mbic': {
                'penalty': float(optimal_mbic['penalty']),
                'mbic': float(optimal_mbic['mbic']),
                'n_changepoints': int(optimal_mbic['n_changepoints']),
                'changepoint_dates': optimal_mbic['changepoint_dates']
            }
        },
        'crops': {
            'n_changepoints': int(n_cp_optimal),
            'penalty_range': [float(crops_range[0]), float(crops_range[1])] if crops_range[0] is not None else None
        },
        'peak_velocity': {
            'date': peak_date.strftime('%Y-%m-%d'),
            'velocity': float(peak_velocity)
        },
        'deceleration_rates': deceleration_results,
        'penalty_sensitivity': df_results[['penalty', 'n_changepoints', 'bic', 'mbic']].to_dict('records'),
        'irregular_sampling': {
            'all_intervals_equal': bool((time_deltas.nunique() == 1)),
            'mean_interval_days': float(time_deltas.mean()),
            'interval_range_days': [float(time_deltas.min()), float(time_deltas.max())]
        }
    }
    
    # Save
    summary_file = OUTPUT_DIR / "pelt_changepoint_results.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"\n✅ Results saved: {summary_file}")
    
    # Save CSV
    df_results.to_csv(OUTPUT_DIR / "penalty_sensitivity.csv", index=False)
    if deceleration_results:
        pd.DataFrame(deceleration_results).to_csv(OUTPUT_DIR / "deceleration_rates.csv", index=False)
    
    print(f"\n✅ Penalty sensitivity saved: {OUTPUT_DIR / 'penalty_sensitivity.csv'}")
    print(f"✅ Deceleration rates saved: {OUTPUT_DIR / 'deceleration_rates.csv'}")

else:
    print("\n⚠️  No results available")

print("\n" + "=" * 80)
print("✅ ANALYSIS COMPLETE")
print("=" * 80)

