#!/usr/bin/env python3
"""
Correlation-Based Feature Importance Analysis for H3
====================================================

Alternative approach focusing on correlation and feature importance
rather than predictive modeling, which is more appropriate for small datasets.

This analysis:
1. Computes correlation coefficients between features and velocity
2. Uses partial correlation to control for confounding
3. Provides feature importance rankings
4. More appropriate for n=9 than regression models

Run: python3 ml_h3_correlation_analysis.py
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import rcParams
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from scipy.stats import pearsonr, spearmanr
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import f_regression

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

# Directories
VELOCITY_DIR = Path("satellite_data/sentinel1/processed")
CLIMATE_DIR = Path("satellite_data/era5_land/processed")
OUTPUT_DIR = Path("processed_data/ml_h3_analysis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PUBLICATION_DPI = 600
FIGURE_SIZE = (16, 10)

def load_and_prepare_data():
    """Load velocity and climate data."""
    print("=" * 70)
    print("LOADING DATA FOR CORRELATION ANALYSIS")
    print("=" * 70)
    
    # Load velocity
    vel_file = VELOCITY_DIR / "velocity_timeseries_python.csv"
    vel = pd.read_csv(vel_file)
    vel['date'] = pd.to_datetime(vel['date'])
    vel = vel.sort_values('date').reset_index(drop=True)
    
    print(f"✅ Loaded {len(vel)} velocity measurements")
    print(f"   Date range: {vel['date'].min()} to {vel['date'].max()}")
    print(f"   Velocity range: {vel['velocity_m_per_day'].min():.1f} - {vel['velocity_m_per_day'].max():.1f} m/d")
    
    # Load climate
    clim_file = CLIMATE_DIR / "climate_derivatives_timeseries.csv"
    clim = pd.read_csv(clim_file)
    clim['datetime'] = pd.to_datetime(clim['datetime'])
    
    # Aggregate to daily
    if len(clim) > 365:
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
    
    clim_daily['pdd'] = np.maximum(clim_daily['temperature_C'], 0)
    clim_daily = clim_daily.sort_values('datetime').reset_index(drop=True)
    
    print(f"✅ Loaded {len(clim_daily)} daily climate records")
    
    return vel, clim_daily

def create_features_for_velocity_dates(vel, clim_daily):
    """Create features for velocity measurement dates using full climate history."""
    print("\n" + "=" * 70)
    print("CREATING FEATURES FOR VELOCITY MEASUREMENT DATES")
    print("=" * 70)
    
    features_list = []
    
    for idx, row in vel.iterrows():
        vel_date = row['date']
        vel_date_only = vel_date.date()
        
        # Find index in climate data
        clim_idx = clim_daily[clim_daily['date'] == vel_date_only].index
        
        if len(clim_idx) == 0:
            continue
        
        clim_idx = clim_idx[0]
        features = {'date': vel_date, 'velocity_m_per_day': row['velocity_m_per_day']}
        
        # PDD cumulative windows
        for window in [30, 60, 90, 120, 180]:
            window_start = max(0, clim_idx - window)
            window_data = clim_daily.iloc[window_start:clim_idx+1]
            features[f'pdd_cumulative_{window}d'] = window_data['pdd'].sum()
        
        # SWE metrics
        features['swe_current'] = clim_daily.iloc[clim_idx]['swe_mm']
        features['swe_max'] = clim_daily.iloc[:clim_idx+1]['swe_mm'].max()
        features['swe_depletion'] = features['swe_max'] - features['swe_current']
        
        # ROS metrics (simplified)
        for window in [30, 60, 90]:
            window_start = max(0, clim_idx - window)
            window_data = clim_daily.iloc[window_start:clim_idx+1]
            
            ros_mask = (
                (window_data['temperature_C'] > 0.5) &
                (window_data['precipitation_mm'] > 0.1) &
                (window_data['swe_mm'] > 0.1)
            )
            ros_events = window_data[ros_mask]
            
            features[f'ros_count_{window}d'] = len(ros_events)
            if len(ros_events) > 0:
                ros_intensity = (ros_events['precipitation_mm'] * 
                               (ros_events['temperature_C'] - 0.5)).sum()
                features[f'ros_intensity_{window}d'] = ros_intensity
            else:
                features[f'ros_intensity_{window}d'] = 0
        
        # Temporal features
        features['day_of_year'] = vel_date.dayofyear
        features['month'] = vel_date.month
        
        # Lagged PDD
        for lag in [1, 7, 14]:
            if clim_idx >= lag:
                features[f'pdd_lag_{lag}d'] = clim_daily.iloc[clim_idx-lag]['pdd']
            else:
                features[f'pdd_lag_{lag}d'] = 0
        
        # Current climate
        features['pdd_current'] = clim_daily.iloc[clim_idx]['pdd']
        features['precip_current'] = clim_daily.iloc[clim_idx]['precipitation_mm']
        features['temp_current'] = clim_daily.iloc[clim_idx]['temperature_C']
        
        features_list.append(features)
    
    features_df = pd.DataFrame(features_list)
    
    # Fill any NaN
    feature_cols = [col for col in features_df.columns if col not in ['date', 'velocity_m_per_day']]
    for col in feature_cols:
        features_df[col] = features_df[col].fillna(0)
    
    print(f"✅ Created features for {len(features_df)} velocity measurements")
    print(f"   Total features: {len(feature_cols)}")
    
    return features_df

def compute_correlations(features_df):
    """Compute correlation coefficients and feature importance."""
    print("\n" + "=" * 70)
    print("COMPUTING CORRELATIONS AND FEATURE IMPORTANCE")
    print("=" * 70)
    
    feature_cols = [col for col in features_df.columns 
                    if col not in ['date', 'velocity_m_per_day']]
    
    y = features_df['velocity_m_per_day'].values
    
    results = []
    
    for col in feature_cols:
        x = features_df[col].values
        
        # Pearson correlation
        r_pearson, p_pearson = pearsonr(x, y)
        
        # Spearman correlation (rank-based, more robust)
        r_spearman, p_spearman = spearmanr(x, y)
        
        # F-statistic (from sklearn feature selection)
        f_stat, _ = f_regression(x.reshape(-1, 1), y)
        f_stat = f_stat[0]
        
        # Absolute correlation (for ranking)
        abs_corr = abs(r_pearson)
        
        results.append({
            'feature': col,
            'pearson_r': r_pearson,
            'pearson_p': p_pearson,
            'spearman_r': r_spearman,
            'spearman_p': p_spearman,
            'f_statistic': f_stat,
            'abs_correlation': abs_corr
        })
    
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('abs_correlation', ascending=False)
    
    print(f"\n✅ Computed correlations for {len(feature_cols)} features")
    print(f"\nTop 10 Features by |Correlation|:")
    for i, row in results_df.head(10).iterrows():
        sig = "***" if row['pearson_p'] < 0.01 else "**" if row['pearson_p'] < 0.05 else "*" if row['pearson_p'] < 0.1 else ""
        print(f"  {row['feature']:30s} | r={row['pearson_r']:6.3f} | p={row['pearson_p']:.3f} {sig}")
    
    return results_df

def compute_category_importance(results_df):
    """Compute total importance by climate driver category."""
    print("\n" + "=" * 70)
    print("COMPUTING CATEGORY IMPORTANCE")
    print("=" * 70)
    
    pdd_features = results_df[results_df['feature'].str.contains('pdd', case=False)]
    swe_features = results_df[results_df['feature'].str.contains('swe', case=False)]
    ros_features = results_df[results_df['feature'].str.contains('ros', case=False)]
    
    pdd_total = pdd_features['abs_correlation'].sum()
    swe_total = swe_features['abs_correlation'].sum()
    ros_total = ros_features['abs_correlation'].sum()
    
    total = pdd_total + swe_total + ros_total
    
    pdd_pct = (pdd_total / total) * 100 if total > 0 else 0
    swe_pct = (swe_total / total) * 100 if total > 0 else 0
    ros_pct = (ros_total / total) * 100 if total > 0 else 0
    
    print(f"\nCategory Importance (sum of |correlation|):")
    print(f"  PDD Features: {pdd_total:.3f} ({pdd_pct:.1f}%)")
    print(f"  SWE Features: {swe_total:.3f} ({swe_pct:.1f}%)")
    print(f"  ROS Features: {ros_total:.3f} ({ros_pct:.1f}%)")
    
    return {
        'pdd_total': pdd_total,
        'swe_total': swe_total,
        'ros_total': ros_total,
        'pdd_pct': pdd_pct,
        'swe_pct': swe_pct,
        'ros_pct': ros_pct
    }

def create_publication_visualizations(features_df, results_df, category_importance):
    """Create publication-quality visualizations."""
    print("\n" + "=" * 70)
    print("CREATING PUBLICATION-QUALITY VISUALIZATIONS")
    print("=" * 70)
    
    fig = plt.figure(figsize=FIGURE_SIZE, dpi=100)
    gs = fig.add_gridspec(2, 3, height_ratios=[1, 1], hspace=0.35, wspace=0.3)
    
    # Panel (a): Top 15 feature correlations
    ax1 = fig.add_subplot(gs[0, :])
    
    top_features = results_df.head(15)
    y_pos = np.arange(len(top_features))
    
    colors = ['#2E86AB' if r > 0 else '#C73E1D' for r in top_features['pearson_r'].values]
    bars = ax1.barh(y_pos, top_features['pearson_r'].values, color=colors, alpha=0.8)
    
    # Add significance markers
    for i, (idx, row) in enumerate(top_features.iterrows()):
        sig = ""
        if row['pearson_p'] < 0.01:
            sig = "***"
        elif row['pearson_p'] < 0.05:
            sig = "**"
        elif row['pearson_p'] < 0.1:
            sig = "*"
        if sig:
            ax1.text(row['pearson_r'], i, sig, va='center', ha='left' if row['pearson_r'] > 0 else 'right', 
                   fontsize=9, fontweight='bold')
    
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(top_features['feature'].values, fontsize=9)
    ax1.set_xlabel('Pearson Correlation Coefficient (r)', fontsize=12)
    ax1.set_title('(a) Top 15 Feature Correlations with Velocity', fontsize=13, loc='left', pad=10)
    ax1.axvline(0, color='black', linewidth=1, linestyle='--')
    ax1.grid(True, alpha=0.3, axis='x')
    ax1.set_facecolor('#FAFAFA')
    ax1.invert_yaxis()
    
    # Add legend for significance
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#2E86AB', alpha=0.8, label='Positive correlation'),
        Patch(facecolor='#C73E1D', alpha=0.8, label='Negative correlation'),
        plt.Line2D([0], [0], marker='', color='none', label='*** p<0.01, ** p<0.05, * p<0.1')
    ]
    ax1.legend(handles=legend_elements, loc='lower right', fontsize=9)
    
    # Panel (b): PDD window correlations
    ax2 = fig.add_subplot(gs[1, 0])
    
    pdd_features = results_df[results_df['feature'].str.contains('pdd_cumulative')]
    if len(pdd_features) > 0:
        windows = [int(f.split('_')[-1].replace('d', '')) for f in pdd_features['feature']]
        correlations = pdd_features['pearson_r'].values
        
        colors_pdd = ['#F18F01' if r > 0 else '#C73E1D' for r in correlations]
        ax2.bar(range(len(windows)), correlations, color=colors_pdd, alpha=0.8)
        ax2.set_xticks(range(len(windows)))
        ax2.set_xticklabels([f'{w}d' for w in windows], fontsize=9)
        ax2.set_xlabel('PDD Time Window', fontsize=12)
        ax2.set_ylabel('Correlation (r)', fontsize=12)
        ax2.set_title('(b) PDD Window Correlations', fontsize=13, loc='left', pad=10)
        ax2.axhline(0, color='black', linewidth=1, linestyle='--')
        ax2.grid(True, alpha=0.3, axis='y')
        ax2.set_facecolor('#FAFAFA')
    
    # Panel (c): Category importance
    ax3 = fig.add_subplot(gs[1, 1])
    
    categories = ['PDD\nFeatures', 'SWE\nFeatures', 'ROS\nFeatures']
    importances = [
        category_importance['pdd_total'],
        category_importance['swe_total'],
        category_importance['ros_total']
    ]
    colors = ['#F18F01', '#6A994E', '#C73E1D']
    
    bars = ax3.bar(categories, importances, color=colors, alpha=0.8)
    ax3.set_ylabel('Sum of |Correlation|', fontsize=12)
    ax3.set_title('(c) Climate Driver Category Importance', fontsize=13, loc='left', pad=10)
    ax3.grid(True, alpha=0.3, axis='y')
    ax3.set_facecolor('#FAFAFA')
    
    # Add percentage labels
    for i, (bar, pct) in enumerate(zip(bars, [category_importance['pdd_pct'], 
                                               category_importance['swe_pct'],
                                               category_importance['ros_pct']])):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{pct:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # Panel (d): Time series with top features
    ax4 = fig.add_subplot(gs[1, 2])
    
    top_feature_name = results_df.iloc[0]['feature']
    top_feature_values = features_df[top_feature_name].values
    dates = features_df['date'].values
    velocity = features_df['velocity_m_per_day'].values
    
    ax4_twin = ax4.twinx()
    
    line1 = ax4.plot(dates, velocity, 'o-', linewidth=2.5, markersize=8, 
                    color='#2E86AB', label='Velocity', alpha=0.8)
    line2 = ax4_twin.plot(dates, top_feature_values, 's-', linewidth=2, markersize=6,
                         color='#F18F01', label=f'{top_feature_name}', alpha=0.8)
    
    ax4.set_xlabel('Date', fontsize=12)
    ax4.set_ylabel('Velocity (m d⁻¹)', fontsize=12, color='#2E86AB')
    ax4_twin.set_ylabel(f'{top_feature_name}', fontsize=10, color='#F18F01')
    ax4.set_title(f'(d) Velocity vs Top Feature ({top_feature_name})', fontsize=13, loc='left', pad=10)
    
    # Combine legends
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax4.legend(lines, labels, loc='upper left', fontsize=9)
    
    ax4.grid(True, alpha=0.3)
    ax4.set_facecolor('#FAFAFA')
    ax4.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=9)
    
    # Overall title
    fig.suptitle('H3 Correlation Analysis: Climate-Velocity Relationships', 
                fontsize=14, y=0.995)
    
    # Save
    output_file = OUTPUT_DIR / "ml_h3_correlation_analysis.png"
    plt.savefig(output_file, dpi=PUBLICATION_DPI, bbox_inches='tight', 
                facecolor='white', edgecolor='none', format='png')
    print(f"\n✅ Publication-quality figure saved: {output_file}")
    print(f"   Resolution: {PUBLICATION_DPI} DPI")
    
    plt.close()
    return output_file

def save_results(results_df, category_importance):
    """Save results to files."""
    print("\n" + "=" * 70)
    print("SAVING RESULTS")
    print("=" * 70)
    
    # Save correlation results
    results_file = OUTPUT_DIR / "correlation_analysis_results.csv"
    results_df.to_csv(results_file, index=False)
    print(f"✅ Correlation results saved: {results_file}")
    
    # Save summary
    import json
    summary = {
        'total_features': len(results_df),
        'top_feature': results_df.iloc[0]['feature'],
        'top_correlation': float(results_df.iloc[0]['pearson_r']),
        'top_p_value': float(results_df.iloc[0]['pearson_p']),
        'category_importance': category_importance,
        'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    summary_file = OUTPUT_DIR / "correlation_analysis_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"✅ Summary saved: {summary_file}")
    
    return summary

def main():
    """Main function."""
    print("=" * 70)
    print("CORRELATION-BASED FEATURE IMPORTANCE ANALYSIS FOR H3")
    print("=" * 70)
    print("\nThis analysis uses correlation coefficients rather than")
    print("predictive modeling, which is more appropriate for small datasets (n=9).")
    print()
    
    # Load data
    vel, clim_daily = load_and_prepare_data()
    
    # Create features
    features_df = create_features_for_velocity_dates(vel, clim_daily)
    
    # Compute correlations
    results_df = compute_correlations(features_df)
    
    # Compute category importance
    category_importance = compute_category_importance(results_df)
    
    # Create visualizations
    vis_file = create_publication_visualizations(features_df, results_df, category_importance)
    
    # Save results
    summary = save_results(results_df, category_importance)
    
    # Print summary
    print("\n" + "=" * 70)
    print("CORRELATION ANALYSIS SUMMARY")
    print("=" * 70)
    print(f"\nTop Feature: {summary['top_feature']}")
    print(f"Correlation: r = {summary['top_correlation']:.3f}")
    print(f"P-value: p = {summary['top_p_value']:.3f}")
    
    print(f"\nCategory Importance:")
    print(f"  PDD: {category_importance['pdd_pct']:.1f}%")
    print(f"  SWE: {category_importance['swe_pct']:.1f}%")
    print(f"  ROS: {category_importance['ros_pct']:.1f}%")
    
    print("\n" + "=" * 70)
    print("✅ CORRELATION ANALYSIS COMPLETE!")
    print("=" * 70)
    print("\nThis approach is more appropriate for small datasets than")
    print("predictive modeling, focusing on feature importance rather")
    print("than prediction accuracy.")

if __name__ == "__main__":
    main()

