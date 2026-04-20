#!/usr/bin/env python3
"""
Statistical mechanism tests for H1 (topographic pinning) vs. H2 (hydrological switching).

Tests include:
1. Event-coincidence rate vs. null (permutation test)
2. Cross-correlation with lags (velocity vs. ROS/precipitation)
3. Logistic regression models (probability of jerk window given ROS event)
4. Effect sizes and p-values
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
import warnings
warnings.filterwarnings('ignore')

from scipy import stats
from scipy.stats import pearsonr, spearmanr, chi2_contingency
from scipy.signal import correlate
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, roc_curve

VELOCITY_FILE = Path("satellite_data/sentinel1/processed/velocity_timeseries_python.csv")
CLIMATE_FILE = Path("satellite_data/era5_land/processed/climate_derivatives_timeseries.csv")
OUTPUT_DIR = Path("processed_data/mechanism_statistics")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("STATISTICAL MECHANISM TESTS: H1 vs. H2")
print("=" * 80)

# Load data
print("\n1. Loading data...")
velocity_df = pd.read_csv(VELOCITY_FILE)
velocity_df['date'] = pd.to_datetime(velocity_df['date'])
velocity_df = velocity_df.sort_values('date')

climate_df = pd.read_csv(CLIMATE_FILE)
climate_df['datetime'] = pd.to_datetime(climate_df['datetime'])
climate_df = climate_df.sort_values('datetime')

print(f"   Velocity measurements: {len(velocity_df)}")
print(f"   Climate data points: {len(climate_df)}")

# Define braking phase: 19 September to 31 October 2025
braking_start = pd.to_datetime('2025-09-19')
braking_end = pd.to_datetime('2025-10-31')
braking_velocities = velocity_df[
    (velocity_df['date'] >= braking_start) & 
    (velocity_df['date'] <= braking_end)
].copy()

print(f"\n   Braking phase: {braking_start.strftime('%Y-%m-%d')} to {braking_end.strftime('%Y-%m-%d')}")
print(f"   Velocity measurements in braking phase: {len(braking_velocities)}")

# Identify jerk windows (high-motion windows during braking phase)
# Jerk window = velocity > mean + 1.5*std during braking phase
mean_vel_braking = braking_velocities['velocity_m_per_day'].mean()
std_vel_braking = braking_velocities['velocity_m_per_day'].std()
jerk_threshold = mean_vel_braking + 1.5 * std_vel_braking

jerk_windows = braking_velocities[
    braking_velocities['velocity_m_per_day'] >= jerk_threshold
].copy()

print(f"\n2. Jerk window identification:")
print(f"   Mean velocity (braking phase): {mean_vel_braking:.1f} m/day")
print(f"   Std velocity (braking phase): {std_vel_braking:.1f} m/day")
print(f"   Jerk threshold (mean + 1.5*std): {jerk_threshold:.1f} m/day")
print(f"   Jerk windows identified: {len(jerk_windows)}")
if len(jerk_windows) > 0:
    for idx, row in jerk_windows.iterrows():
        print(f"      {row['date'].strftime('%Y-%m-%d')}: {row['velocity_m_per_day']:.1f} m/day")

# Extract ROS events during braking phase
climate_braking = climate_df[
    (climate_df['datetime'] >= braking_start) &
    (climate_df['datetime'] <= braking_end)
].copy()

# ROS events: ROS > 0
ros_events = climate_braking[climate_braking.get('ros', climate_braking.get('ros_intensity', 0)) > 0].copy()

print(f"\n3. ROS events during braking phase:")
print(f"   Total ROS events: {len(ros_events)}")
if len(ros_events) > 0:
    print(f"   ROS intensity range: {ros_events.get('ros', ros_events.get('ros_intensity', 0)).min():.1f} to {ros_events.get('ros', ros_events.get('ros_intensity', 0)).max():.1f}")

# ============================================================================
# TEST 1: EVENT-COINCIDENCE RATE vs. NULL (PERMUTATION TEST)
# ============================================================================

print("\n" + "=" * 80)
print("TEST 1: EVENT-COINCIDENCE RATE vs. NULL")
print("=" * 80)

def event_coincidence_rate(events1, events2, window_days=3):
    """
    Calculate event-coincidence rate: fraction of events1 that have an event2 within ±window_days.
    
    Parameters:
    -----------
    events1 : list of datetime
        Primary events (e.g., jerk windows)
    events2 : list of datetime
        Secondary events (e.g., ROS events)
    window_days : float
        Coincidence window in days (default: ±3 days)
    
    Returns:
    --------
    coincidence_rate : float
        Fraction of events1 with coincident events2
    coincident_pairs : list of tuples
        (event1, event2, lag_days) for coincident pairs
    """
    if len(events1) == 0 or len(events2) == 0:
        return 0.0, []
    
    coincident_count = 0
    coincident_pairs = []
    
    for event1 in events1:
        found = False
        for event2 in events2:
            lag_days = (event2 - event1).days
            if abs(lag_days) <= window_days:
                coincident_count += 1
                coincident_pairs.append((event1, event2, lag_days))
                found = True
                break  # Count each jerk window only once
        
        if not found:
            coincident_pairs.append((event1, None, None))
    
    coincidence_rate = coincident_count / len(events1) if len(events1) > 0 else 0.0
    return coincidence_rate, coincident_pairs

# Calculate observed coincidence rate
jerk_dates = jerk_windows['date'].tolist() if len(jerk_windows) > 0 else []
ros_dates = ros_events['datetime'].tolist() if len(ros_events) > 0 else []

if len(jerk_dates) > 0 and len(ros_dates) > 0:
    observed_rate, coincident_pairs = event_coincidence_rate(jerk_dates, ros_dates, window_days=3)
    
    print(f"\n   Observed coincidence rate: {observed_rate:.3f}")
    print(f"   Jerk windows with ROS events (within ±3 days): {sum(1 for p in coincident_pairs if p[1] is not None)} / {len(jerk_dates)}")
    
    if len(coincident_pairs) > 0:
        for j_date, r_date, lag in coincident_pairs:
            if r_date is not None:
                print(f"      {j_date.strftime('%Y-%m-%d')} <-> {r_date.strftime('%Y-%m-%d')} (lag: {lag} days)")
    
    # Permutation test: randomize ROS event dates
    n_permutations = 10000
    null_rates = []
    
    print(f"\n   Running permutation test (n={n_permutations})...")
    # Available days in braking phase
    available_days = pd.date_range(braking_start, braking_end, freq='D')
    n_available = len(available_days)
    n_ros = len(ros_dates)
    
    for i in range(n_permutations):
        # Shuffle ROS event dates within braking phase
        if n_ros <= n_available:
            shuffled_ros_dates = pd.to_datetime(np.random.choice(
                available_days,
                size=n_ros,
                replace=False
            )).tolist()
        else:
            # If more ROS events than days, sample with replacement
            shuffled_ros_dates = pd.to_datetime(np.random.choice(
                available_days,
                size=n_ros,
                replace=True
            )).tolist()
        
        null_rate, _ = event_coincidence_rate(jerk_dates, shuffled_ros_dates, window_days=3)
        null_rates.append(null_rate)
    
    # Calculate p-value
    p_value = np.mean(np.array(null_rates) >= observed_rate)
    effect_size = observed_rate - np.mean(null_rates)  # Difference from null
    
    print(f"\n   Null mean coincidence rate: {np.mean(null_rates):.3f}")
    print(f"   Null std coincidence rate: {np.std(null_rates):.3f}")
    print(f"   Effect size (observed - null mean): {effect_size:.3f}")
    print(f"   p-value: {p_value:.4f}")
    
    # Two-tailed test
    p_value_2tailed = 2 * min(p_value, 1 - p_value)
    print(f"   p-value (two-tailed): {p_value_2tailed:.4f}")
    
    event_coincidence_results = {
        'observed_rate': float(observed_rate),
        'null_mean': float(np.mean(null_rates)),
        'null_std': float(np.std(null_rates)),
        'effect_size': float(effect_size),
        'p_value': float(p_value),
        'p_value_2tailed': float(p_value_2tailed),
        'n_jerk_windows': len(jerk_dates),
        'n_ros_events': len(ros_dates),
        'coincident_count': sum(1 for p in coincident_pairs if p[1] is not None),
        'window_days': 3
    }
else:
    print("\n   ⚠️  Insufficient data for event-coincidence test")
    event_coincidence_results = None

# ============================================================================
# TEST 2: CROSS-CORRELATION WITH LAGS
# ============================================================================

print("\n" + "=" * 80)
print("TEST 2: CROSS-CORRELATION WITH LAGS")
print("=" * 80)

# Merge velocity and climate data
merged_df = velocity_df.merge(
    climate_df,
    left_on='date',
    right_on='datetime',
    how='left'
)

# Fill missing values with forward fill
ros_col = 'ros' if 'ros' in merged_df.columns else 'ros_intensity'
if ros_col in merged_df.columns:
    merged_df[ros_col] = merged_df[ros_col].fillna(0)
    
    # Calculate cross-correlation at different lags
    velocity_vals = merged_df['velocity_m_per_day'].values
    ros_vals = merged_df[ros_col].values
    
    # Remove NaN
    valid_mask = ~(np.isnan(velocity_vals) | np.isnan(ros_vals))
    velocity_vals = velocity_vals[valid_mask]
    ros_vals = ros_vals[valid_mask]
    
    if len(velocity_vals) > 3:
        max_lag = min(3, len(velocity_vals) // 2)  # Up to ±3 lags
        
        cross_corr_results = []
        
        for lag in range(-max_lag, max_lag + 1):
            if lag < 0:
                v_lag = velocity_vals[-lag:]
                ros_lag = ros_vals[:lag]
            elif lag > 0:
                v_lag = velocity_vals[:-lag]
                ros_lag = ros_vals[lag:]
            else:
                v_lag = velocity_vals
                ros_lag = ros_vals
            
            if len(v_lag) > 2:
                r, p = pearsonr(v_lag, ros_lag)
                cross_corr_results.append({
                    'lag': lag,
                    'correlation': float(r),
                    'p_value': float(p),
                    'n': len(v_lag)
                })
        
        if cross_corr_results:
            # Find optimal lag
            optimal_idx = np.argmax([abs(r['correlation']) for r in cross_corr_results])
            optimal = cross_corr_results[optimal_idx]
            
            print(f"\n   Optimal lag: {optimal['lag']} days")
            print(f"   Correlation at optimal lag: {optimal['correlation']:.3f}")
            print(f"   p-value at optimal lag: {optimal['p_value']:.4f}")
            
            print(f"\n   Cross-correlations at all lags:")
            for r in cross_corr_results:
                sig = "***" if r['p_value'] < 0.001 else "**" if r['p_value'] < 0.01 else "*" if r['p_value'] < 0.05 else ""
                print(f"      Lag {r['lag']:+2d}: r = {r['correlation']:6.3f}, p = {r['p_value']:.4f} {sig}")
        else:
            cross_corr_results = None
    else:
        cross_corr_results = None
else:
    print("\n   ⚠️  ROS column not found in climate data")
    cross_corr_results = None

# ============================================================================
# TEST 3: LOGISTIC REGRESSION MODELS
# ============================================================================

print("\n" + "=" * 80)
print("TEST 3: LOGISTIC REGRESSION MODELS")
print("=" * 80)

# Create binary outcome: jerk window (1) or not (0)
braking_velocities['is_jerk'] = (braking_velocities['velocity_m_per_day'] >= jerk_threshold).astype(int)

# Merge with climate data
braking_merged = braking_velocities.merge(
    climate_braking,
    left_on='date',
    right_on='datetime',
    how='left'
)

if ros_col in braking_merged.columns:
    # Feature: ROS event (binary)
    braking_merged['ros_binary'] = (braking_merged[ros_col] > 0).astype(int)
    
    # Feature: ROS intensity (continuous)
    braking_merged[ros_col] = braking_merged[ros_col].fillna(0)
    
    # Feature: Precipitation
    precip_col = 'precipitation_mm' if 'precipitation_mm' in braking_merged.columns else 'precip'
    if precip_col in braking_merged.columns:
        braking_merged[precip_col] = braking_merged[precip_col].fillna(0)
    
    # Logistic regression: probability of jerk window given ROS event
    # Model 1: ROS binary
    X_ros_bin = braking_merged[['ros_binary']].values
    y = braking_merged['is_jerk'].values
    
    if len(np.unique(y)) > 1 and len(np.unique(X_ros_bin)) > 1:
        try:
            lr_ros = LogisticRegression(max_iter=1000)
            lr_ros.fit(X_ros_bin, y)
            
            # Predictions and metrics
            y_pred_proba = lr_ros.predict_proba(X_ros_bin)[:, 1]
            auc_ros = roc_auc_score(y, y_pred_proba) if len(np.unique(y)) > 1 else np.nan
            
            # Effect size: odds ratio
            coef_ros = lr_ros.coef_[0][0]
            odds_ratio_ros = np.exp(coef_ros)
            
            # Wald test for p-value
            from scipy.stats import norm
            se_coef = np.sqrt(1 / np.sum(X_ros_bin))  # Approximate SE
            z_score = coef_ros / se_coef
            p_value_ros = 2 * (1 - norm.cdf(abs(z_score)))
            
            print(f"\n   Model 1: ROS binary predictor")
            print(f"      Coefficient (log-odds): {coef_ros:.3f}")
            print(f"      Odds ratio: {odds_ratio_ros:.3f}")
            print(f"      AUC: {auc_ros:.3f}")
            print(f"      p-value: {p_value_ros:.4f}")
            
            logistic_results = {
                'ros_binary': {
                    'coefficient': float(coef_ros),
                    'odds_ratio': float(odds_ratio_ros),
                    'auc': float(auc_ros) if not np.isnan(auc_ros) else None,
                    'p_value': float(p_value_ros)
                }
            }
            
            # Model 2: ROS intensity (continuous)
            if ros_col in braking_merged.columns:
                X_ros_int = braking_merged[[ros_col]].values
                if np.std(X_ros_int) > 0:
                    lr_ros_int = LogisticRegression(max_iter=1000)
                    lr_ros_int.fit(X_ros_int, y)
                    
                    coef_ros_int = lr_ros_int.coef_[0][0]
                    y_pred_proba_int = lr_ros_int.predict_proba(X_ros_int)[:, 1]
                    auc_ros_int = roc_auc_score(y, y_pred_proba_int) if len(np.unique(y)) > 1 else np.nan
                    
                    se_coef_int = np.sqrt(1 / np.sum(X_ros_int**2))
                    z_score_int = coef_ros_int / se_coef_int
                    p_value_ros_int = 2 * (1 - norm.cdf(abs(z_score_int)))
                    
                    print(f"\n   Model 2: ROS intensity (continuous)")
                    print(f"      Coefficient (log-odds per unit ROS): {coef_ros_int:.3f}")
                    print(f"      AUC: {auc_ros_int:.3f}")
                    print(f"      p-value: {p_value_ros_int:.4f}")
                    
                    logistic_results['ros_intensity'] = {
                        'coefficient': float(coef_ros_int),
                        'auc': float(auc_ros_int) if not np.isnan(auc_ros_int) else None,
                        'p_value': float(p_value_ros_int)
                    }
        except Exception as e:
            print(f"\n   ⚠️  Error in logistic regression: {e}")
            logistic_results = None
    else:
        print("\n   ⚠️  Insufficient variation for logistic regression")
        logistic_results = None
else:
    print("\n   ⚠️  ROS column not found")
    logistic_results = None

# ============================================================================
# SUMMARY AND COMPARISON
# ============================================================================

print("\n" + "=" * 80)
print("SUMMARY: H1 (TOPOGRAPHIC PINNING) vs. H2 (HYDROLOGICAL SWITCHING)")
print("=" * 80)

summary = {
    'H2_hydrological_switching': {
        'event_coincidence': event_coincidence_results,
        'cross_correlation': cross_corr_results,
        'logistic_regression': logistic_results
    },
    'H1_topographic_pinning': {
        'note': 'Spatial analysis required (not yet implemented)'
    }
}

print("\n   H2 (Hydrological Switching):")
if event_coincidence_results:
    print(f"      Event-coincidence rate: {event_coincidence_results['observed_rate']:.3f} "
          f"(p = {event_coincidence_results['p_value_2tailed']:.4f})")
    print(f"      Effect size: {event_coincidence_results['effect_size']:.3f}")

if cross_corr_results and optimal:
    print(f"      Optimal cross-correlation: r = {optimal['correlation']:.3f} at lag {optimal['lag']} "
          f"(p = {optimal['p_value']:.4f})")

if logistic_results:
    if 'ros_binary' in logistic_results:
        print(f"      Logistic regression (ROS binary): OR = {logistic_results['ros_binary']['odds_ratio']:.3f} "
              f"(p = {logistic_results['ros_binary']['p_value']:.4f})")

print("\n   H1 (Topographic Pinning):")
print("      Spatial analysis pending (requires DEM and along-flowline profiles)")

# Save results
summary_file = OUTPUT_DIR / "mechanism_statistical_tests.json"
with open(summary_file, 'w') as f:
    # Convert datetime to string for JSON
    def convert_to_json(obj):
        if isinstance(obj, dict):
            return {k: convert_to_json(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [convert_to_json(item) for item in obj]
        elif isinstance(obj, (datetime, pd.Timestamp)):
            return obj.strftime('%Y-%m-%d')
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj
    
    json.dump(convert_to_json(summary), f, indent=2)

print(f"\n✅ Results saved: {summary_file}")
print("\n" + "=" * 80)
print("✅ STATISTICAL ANALYSIS COMPLETE")
print("=" * 80)

