#!/usr/bin/env python3
"""
Publication-Quality ML H3 Figure for Q1 Journal
================================================

Creates a professional, Q1 journal-quality figure for ML analysis
with improved formatting, clearer panels, better labels, and proper styling.

Run: python3 create_publication_quality_ml_figure.py
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import rcParams
from matplotlib.patches import Patch
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from scipy.stats import pearsonr, spearmanr
from sklearn.feature_selection import f_regression

# Set publication-quality matplotlib parameters (Q1 Journal Style)
rcParams['font.family'] = 'sans-serif'
rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
rcParams['font.size'] = 12  # Increased for readability
rcParams['axes.labelsize'] = 13  # Increased
rcParams['axes.titlesize'] = 14  # Increased
rcParams['xtick.labelsize'] = 11  # Increased
rcParams['ytick.labelsize'] = 11  # Increased
rcParams['legend.fontsize'] = 11  # Increased
rcParams['figure.titlesize'] = 16  # Increased
rcParams['axes.linewidth'] = 1.5
rcParams['grid.linewidth'] = 1.0
rcParams['lines.linewidth'] = 2.5
rcParams['lines.markersize'] = 8
rcParams['xtick.major.width'] = 1.5
rcParams['ytick.major.width'] = 1.5
rcParams['xtick.major.size'] = 5
rcParams['ytick.major.size'] = 5

# Directories
VELOCITY_DIR = Path("satellite_data/sentinel1/processed")
CLIMATE_DIR = Path("satellite_data/era5_land/processed")
OUTPUT_DIR = Path("processed_data/ml_h3_analysis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PUBLICATION_DPI = 600
FIGURE_SIZE = (18, 12)  # Wider for better layout

def load_and_prepare_data():
    """Load velocity and climate data."""
    # Load velocity
    vel_file = VELOCITY_DIR / "velocity_timeseries_python.csv"
    vel = pd.read_csv(vel_file)
    vel['date'] = pd.to_datetime(vel['date'])
    vel = vel.sort_values('date').reset_index(drop=True)
    
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
    
    return vel, clim_daily

def create_features_for_velocity_dates(vel, clim_daily):
    """Create features for velocity measurement dates using full climate history."""
    features_list = []
    
    for idx, row in vel.iterrows():
        vel_date = row['date']
        vel_date_only = vel_date.date()
        
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
        features['swe_change_30d'] = clim_daily.iloc[clim_idx]['swe_mm'] - clim_daily.iloc[max(0, clim_idx-30)]['swe_mm']
        features['swe_change_60d'] = clim_daily.iloc[clim_idx]['swe_mm'] - clim_daily.iloc[max(0, clim_idx-60)]['swe_mm']
        
        # ROS metrics
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
        features['day_of_year_sin'] = np.sin(2 * np.pi * vel_date.dayofyear / 365.25)
        features['day_of_year_cos'] = np.cos(2 * np.pi * vel_date.dayofyear / 365.25)
        
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
    
    return features_df

def compute_correlations(features_df):
    """Compute correlation coefficients and feature importance."""
    feature_cols = [col for col in features_df.columns 
                    if col not in ['date', 'velocity_m_per_day']]
    
    y = features_df['velocity_m_per_day'].values
    
    results = []
    
    for col in feature_cols:
        x = features_df[col].values
        
        r_pearson, p_pearson = pearsonr(x, y)
        r_spearman, p_spearman = spearmanr(x, y)
        f_stat, _ = f_regression(x.reshape(-1, 1), y)
        f_stat = f_stat[0]
        
        results.append({
            'feature': col,
            'pearson_r': r_pearson,
            'pearson_p': p_pearson,
            'spearman_r': r_spearman,
            'spearman_p': p_spearman,
            'f_statistic': f_stat,
            'abs_correlation': abs(r_pearson)
        })
    
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('abs_correlation', ascending=False)
    
    return results_df

def compute_category_importance(results_df):
    """Compute total importance by climate driver category."""
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
    
    return {
        'pdd_total': pdd_total,
        'swe_total': swe_total,
        'ros_total': ros_total,
        'pdd_pct': pdd_pct,
        'swe_pct': swe_pct,
        'ros_pct': ros_pct
    }

def create_publication_quality_figure(features_df, results_df, category_importance):
    """Create publication-quality Q1 journal figure."""
    print("\n" + "=" * 70)
    print("CREATING PUBLICATION-QUALITY Q1 JOURNAL FIGURE")
    print("=" * 70)
    
    fig = plt.figure(figsize=FIGURE_SIZE, dpi=100, facecolor='white')
    gs = fig.add_gridspec(2, 3, height_ratios=[1.2, 1], hspace=0.4, wspace=0.35, 
                         left=0.08, right=0.95, top=0.93, bottom=0.10)
    
    # ========== PANEL (a): Top Features Correlations ==========
    ax1 = fig.add_subplot(gs[0, 0])
    
    top_features = results_df.head(12)
    y_pos = np.arange(len(top_features))
    
    colors = ['#2E86AB' if r > 0 else '#C73E1D' for r in top_features['pearson_r'].values]
    bars = ax1.barh(y_pos, top_features['pearson_r'].values, color=colors, alpha=0.85, 
                   edgecolor='black', linewidth=1.2, height=0.75)
    
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
            x_pos = row['pearson_r']
            ha_pos = 'left' if x_pos > 0 else 'right'
            x_offset = 0.02 if x_pos > 0 else -0.02
            ax1.text(x_pos + x_offset, i, sig, va='center', ha=ha_pos, 
                   fontsize=12, fontweight='bold', color='black')
    
    # Clean up feature names for display
    feature_labels = []
    for f in top_features['feature'].values:
        if 'pdd_cumulative' in f:
            window = f.split('_')[-1].replace('d', '')
            feature_labels.append(f'PDD cumulative ({window}d)')
        elif 'pdd_lag' in f:
            lag = f.split('_')[-1].replace('d', '')
            feature_labels.append(f'PDD lag ({lag})')
        elif 'ros_intensity' in f:
            window = f.split('_')[-1].replace('d', '')
            feature_labels.append(f'ROS intensity ({window}d)')
        elif 'ros_count' in f:
            window = f.split('_')[-1].replace('d', '')
            feature_labels.append(f'ROS count ({window}d)')
        elif 'temp_current' in f:
            feature_labels.append('Temperature (current)')
        elif 'pdd_current' in f:
            feature_labels.append('PDD (current)')
        elif 'swe_' in f:
            feature_labels.append(f.replace('_', ' ').title())
        elif 'month' in f:
            feature_labels.append('Month')
        elif 'day_of_year' in f:
            feature_labels.append('Day of year')
        else:
            feature_labels.append(f.replace('_', ' ').title())
    
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(feature_labels, fontsize=10)
    ax1.set_xlabel('Pearson correlation coefficient (r)', fontsize=13, labelpad=8)
    ax1.set_title('(a) Feature Correlations with Velocity', fontsize=14, loc='left', pad=12)
    ax1.axvline(0, color='black', linewidth=1.5, linestyle='-', zorder=0)
    ax1.grid(True, alpha=0.3, axis='x', linestyle='--', linewidth=1.0, zorder=0)
    ax1.set_facecolor('#FAFAFA')
    ax1.invert_yaxis()
    ax1.set_xlim(-0.8, 0.8)
    
    # Add legend for significance
    legend_elements = [
        Patch(facecolor='#2E86AB', alpha=0.85, edgecolor='black', linewidth=1.2, label='Positive'),
        Patch(facecolor='#C73E1D', alpha=0.85, edgecolor='black', linewidth=1.2, label='Negative'),
        plt.Line2D([0], [0], marker='', color='none', label='*** p<0.01, ** p<0.05, * p<0.1')
    ]
    ax1.legend(handles=legend_elements, loc='lower right', fontsize=10, 
              frameon=True, fancybox=True, shadow=True, framealpha=0.95)
    
    # ========== PANEL (b): PDD Window Importance ==========
    ax2 = fig.add_subplot(gs[0, 1])
    
    pdd_features = results_df[results_df['feature'].str.contains('pdd_cumulative')]
    if len(pdd_features) > 0:
        windows = [int(f.split('_')[-1].replace('d', '')) for f in pdd_features['feature']]
        correlations = pdd_features['pearson_r'].values
        
        # Sort by window length
        sort_idx = np.argsort(windows)
        windows_sorted = [windows[i] for i in sort_idx]
        correlations_sorted = correlations[sort_idx]
        
        colors_pdd = ['#F18F01' if r > 0 else '#C73E1D' for r in correlations_sorted]
        bars = ax2.bar(range(len(windows_sorted)), correlations_sorted, color=colors_pdd, 
                      alpha=0.85, edgecolor='black', linewidth=1.5, width=0.7)
        
        # Add correlation values on bars
        for i, (w, r) in enumerate(zip(windows_sorted, correlations_sorted)):
            height = r
            y_pos = height + 0.02 if height > 0 else height - 0.02
            ax2.text(i, y_pos, f'{r:.2f}', ha='center', 
                   va='bottom' if height > 0 else 'top', fontsize=11, fontweight='bold')
        
        ax2.set_xticks(range(len(windows_sorted)))
        ax2.set_xticklabels([f'{w}d' for w in windows_sorted], fontsize=11)
        ax2.set_xlabel('PDD time window', fontsize=13, labelpad=8)
        ax2.set_ylabel('Correlation coefficient (r)', fontsize=13, labelpad=8)
        ax2.set_title('(b) PDD Cumulative Window Correlations', fontsize=14, loc='left', pad=12)
        ax2.axhline(0, color='black', linewidth=1.5, linestyle='-', zorder=0)
        ax2.grid(True, alpha=0.3, axis='y', linestyle='--', linewidth=1.0, zorder=0)
        ax2.set_facecolor('#FAFAFA')
        ax2.set_ylim(-0.7, 0.1)
    
    # ========== PANEL (c): Category Importance ==========
    ax3 = fig.add_subplot(gs[0, 2])
    
    categories = ['PDD\nFeatures', 'ROS\nFeatures', 'SWE\nFeatures']
    importances = [
        category_importance['pdd_total'],
        category_importance['ros_total'],
        category_importance['swe_total']
    ]
    percentages = [
        category_importance['pdd_pct'],
        category_importance['ros_pct'],
        category_importance['swe_pct']
    ]
    colors = ['#F18F01', '#C73E1D', '#6A994E']
    
    bars = ax3.bar(categories, importances, color=colors, alpha=0.85, 
                  edgecolor='black', linewidth=1.5, width=0.65)
    
    # Add percentage labels on top
    for i, (bar, pct) in enumerate(zip(bars, percentages)):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{pct:.1f}%', ha='center', va='bottom', 
                fontsize=13, fontweight='bold', color='black')
    
    ax3.set_ylabel('Total |Correlation|', fontsize=13, labelpad=8)
    ax3.set_title('(c) Climate Driver Category Importance', fontsize=14, loc='left', pad=12)
    ax3.grid(True, alpha=0.3, axis='y', linestyle='--', linewidth=1.0, zorder=0)
    ax3.set_facecolor('#FAFAFA')
    ax3.set_ylim(0, max(importances) * 1.15)
    
    # ========== PANEL (d): Time Series ==========
    ax4 = fig.add_subplot(gs[1, :])
    
    top_feature_name = results_df.iloc[0]['feature']
    top_feature_values = features_df[top_feature_name].values
    dates = features_df['date'].values
    velocity = features_df['velocity_m_per_day'].values
    
    ax4_twin = ax4.twinx()
    
    # Plot velocity
    line1 = ax4.plot(dates, velocity, 'o-', linewidth=3, markersize=10, 
                    color='#2E86AB', label='Velocity', alpha=0.9, zorder=3,
                    markerfacecolor='white', markeredgewidth=2, markeredgecolor='#2E86AB')
    
    # Plot top feature (normalized for visibility)
    # Normalize feature to match velocity scale for comparison
    feature_normalized = (top_feature_values - top_feature_values.min()) / (top_feature_values.max() - top_feature_values.min() + 1e-10)
    velocity_range = velocity.max() - velocity.min()
    feature_scaled = feature_normalized * velocity_range + velocity.min()
    
    line2 = ax4_twin.plot(dates, top_feature_values, 's-', linewidth=2.5, markersize=9,
                         color='#F18F01', label=f'{top_feature_name.replace("_", " ").title()}', 
                         alpha=0.85, zorder=2, markerfacecolor='white', 
                         markeredgewidth=2, markeredgecolor='#F18F01')
    
    # Clean up feature name for label
    if 'temp_current' in top_feature_name:
        feature_label = 'Temperature (°C)'
    elif 'pdd_current' in top_feature_name:
        feature_label = 'PDD (°C·days)'
    else:
        feature_label = top_feature_name.replace('_', ' ').title()
    
    ax4.set_xlabel('Date', fontsize=13, labelpad=8)
    ax4.set_ylabel('Velocity (m d⁻¹)', fontsize=13, color='#2E86AB', labelpad=8)
    ax4_twin.set_ylabel(f'{feature_label}', fontsize=13, color='#F18F01', labelpad=8)
    ax4.set_title(f'(d) Velocity vs. Top Feature ({feature_label})', fontsize=14, loc='left', pad=12)
    
    # Color y-axis labels
    ax4.tick_params(axis='y', labelcolor='#2E86AB')
    ax4_twin.tick_params(axis='y', labelcolor='#F18F01')
    
    # Combine legends
    lines = line1 + line2
    labels = ['Velocity (m d⁻¹)', feature_label]
    ax4.legend(lines, labels, loc='upper left', fontsize=11, 
              frameon=True, fancybox=True, shadow=True, framealpha=0.95)
    
    ax4.grid(True, alpha=0.3, linestyle='--', linewidth=1.0, zorder=1)
    ax4.set_facecolor('#FAFAFA')
    ax4.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax4.xaxis.set_major_locator(mdates.DayLocator(interval=7))
    plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=10)
    
    # Add correlation text box
    r_val = results_df.iloc[0]['pearson_r']
    p_val = results_df.iloc[0]['pearson_p']
    sig_text = "***" if p_val < 0.01 else "**" if p_val < 0.05 else "*" if p_val < 0.1 else ""
    corr_text = f'r = {r_val:.3f}, p = {p_val:.3f} {sig_text}'
    ax4.text(0.98, 0.98, corr_text, transform=ax4.transAxes, 
            fontsize=11, verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='white', 
                     edgecolor='gray', linewidth=1.5, alpha=0.95))
    
    # Overall title (removed or made subtle)
    # No overall title for cleaner look
    
    # Save
    output_file = OUTPUT_DIR / "ml_h3_analysis_publication_quality.png"
    plt.savefig(output_file, dpi=PUBLICATION_DPI, bbox_inches='tight', 
                facecolor='white', edgecolor='none', format='png')
    print(f"\n✅ Publication-quality figure saved: {output_file}")
    print(f"   Resolution: {PUBLICATION_DPI} DPI")
    print(f"   Size: {FIGURE_SIZE[0]}×{FIGURE_SIZE[1]} inches")
    
    plt.close()
    return output_file

def main():
    """Main function."""
    print("=" * 70)
    print("CREATING PUBLICATION-QUALITY Q1 JOURNAL FIGURE")
    print("=" * 70)
    
    # Load data
    vel, clim_daily = load_and_prepare_data()
    
    # Create features
    features_df = create_features_for_velocity_dates(vel, clim_daily)
    
    # Compute correlations
    results_df = compute_correlations(features_df)
    
    # Compute category importance
    category_importance = compute_category_importance(results_df)
    
    # Create figure
    vis_file = create_publication_quality_figure(features_df, results_df, category_importance)
    
    print("\n" + "=" * 70)
    print("✅ PUBLICATION-QUALITY FIGURE COMPLETE!")
    print("=" * 70)
    print(f"\nFigure saved: {vis_file}")
    print("\nImprovements made:")
    print("  • Larger, more readable fonts")
    print("  • Better panel spacing and layout")
    print("  • Cleaner feature labels")
    print("  • Enhanced significance markers")
    print("  • Professional color scheme")
    print("  • Better legends and annotations")
    print("  • Q1 journal formatting standards")

if __name__ == "__main__":
    main()

