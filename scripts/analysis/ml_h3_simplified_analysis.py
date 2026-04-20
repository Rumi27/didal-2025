#!/usr/bin/env python3
"""
SIMPLIFIED Q1-Quality ML Analysis for H3
========================================
Simplified visualization for clearer manuscript presentation.
Focuses on:
1. Observed vs Predicted Time Series (Model Fit)
2. Top Feature Importance (Physical Drivers)
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

# ML Libraries
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge, Lasso, ElasticNet
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

# Publication settings - LARGER FONTS
rcParams['font.family'] = 'sans-serif'
rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
rcParams['font.size'] = 14        # Base font size increased
rcParams['axes.labelsize'] = 16   # Axis labels
rcParams['axes.titlesize'] = 18   # Subplot titles
rcParams['xtick.labelsize'] = 14  # Ticks
rcParams['ytick.labelsize'] = 14
rcParams['legend.fontsize'] = 14
rcParams['figure.titlesize'] = 20

# Directories
VELOCITY_DIR = Path("satellite_data/sentinel1/processed")
CLIMATE_DIR = Path("satellite_data/era5_land/processed")
OUTPUT_DIR = Path("processed_data/ml_h3_analysis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Figure settings
PUBLICATION_DPI = 600
FIGURE_SIZE = (12, 10)  # Simpler 2-panel layout

def load_and_prepare_data():
    """Load velocity and climate data."""
    vel_file = VELOCITY_DIR / "velocity_timeseries_python.csv"
    vel = pd.read_csv(vel_file)
    vel['date'] = pd.to_datetime(vel['date'])
    vel = vel.sort_values('date').reset_index(drop=True)
    vel = vel[['date', 'velocity_m_per_day']].copy()
    
    clim_file = CLIMATE_DIR / "climate_derivatives_timeseries.csv"
    clim = pd.read_csv(clim_file)
    clim['datetime'] = pd.to_datetime(clim['datetime'])
    clim = clim.sort_values('datetime').reset_index(drop=True)
    
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

def create_ml_features_all_climate(clim_daily, vel_df):
    """Create ML features."""
    vel_dates = vel_df['date'].dt.date.values
    clim_daily = clim_daily.sort_values('datetime').reset_index(drop=True)
    
    all_features = []
    
    for i in range(len(clim_daily)):
        date = clim_daily.iloc[i]['datetime']
        features = {'date': date}
        
        # PDD cumulative
        for window in [30, 60, 90, 120, 180]:
            window_start = max(0, i - window)
            window_data = clim_daily.iloc[window_start:i+1]
            features[f'CDD_{window}d'] = window_data['pdd'].sum() # Renamed PDD_cumulative to CDD for brevity
        
        # SWE
        features['SWE_current'] = clim_daily.iloc[i]['swe_mm']
        features['SWE_depletion'] = clim_daily.iloc[:i+1]['swe_mm'].max() - features['SWE_current']
        
        # ROS counts
        for window in [30, 60, 90]:
            window_start = max(0, i - window)
            window_data = clim_daily.iloc[window_start:i+1]
            ros_mask = (
                (window_data['temperature_C'] > 0.5) &
                (window_data['precipitation_mm'] > 0.1) &
                (window_data['swe_mm'] > 0.1)
            )
            features[f'ROS_days_{window}d'] = ros_mask.sum()
        
        # Temporal
        features['day_of_year'] = date.dayofyear
        
        # Current
        features['Temp_current'] = clim_daily.iloc[i]['temperature_C']
        features['Precip_current'] = clim_daily.iloc[i]['precipitation_mm']
        
        all_features.append(features)
    
    features_df = pd.DataFrame(all_features)
    
    # Filter to velocity dates
    vel_dict = {d: v for d, v in zip(vel_dates, vel_df['velocity_m_per_day'])}
    features_df['velocity'] = features_df['date'].dt.date.map(vel_dict)
    features_df = features_df.dropna(subset=['velocity']).reset_index(drop=True)
    features_df = features_df.fillna(0)
    
    return features_df

def train_and_visualize(features_df):
    """Train model and create SIMPLIFIED visualization."""
    
    # Prepare data
    feature_cols = [c for c in features_df.columns if c not in ['date', 'velocity']]
    X = features_df[feature_cols].values
    y = features_df['velocity'].values
    
    # Feature Selection
    selector = SelectKBest(score_func=f_regression, k=min(10, len(feature_cols)))
    X_selected = selector.fit_transform(X, y)
    selected_indices = selector.get_support(indices=True)
    selected_features = [feature_cols[i] for i in selected_indices]
    
    # Train Random Forest (robust, non-linear)
    model = RandomForestRegressor(n_estimators=100, max_depth=5, random_state=42)
    model.fit(X_selected, y)
    y_pred = model.predict(X_selected)
    
    # Metrics
    r2 = r2_score(y, y_pred)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    
    # --- CREATE SIMPLIFIED PLOT ---
    fig = plt.figure(figsize=FIGURE_SIZE, dpi=100)
    gs = fig.add_gridspec(2, 1, height_ratios=[1, 1], hspace=0.3)
    
    # Panel A: Time Series
    ax1 = fig.add_subplot(gs[0])
    dates = features_df['date']
    
    ax1.plot(dates, y, 'o-', color='black', linewidth=2, markersize=8, label='Observed Velocity', alpha=0.8)
    ax1.plot(dates, y_pred, 's--', color='#D55E00', linewidth=2, markersize=8, label='Modeled (RF)', alpha=0.8)
    
    ax1.set_ylabel('Velocity (m d⁻¹)')
    ax1.set_title('(a) Obs. vs Modeled Velocity', loc='left', fontweight='bold')
    ax1.legend(frameon=False)
    ax1.grid(True, alpha=0.3)
    
    # Add stats box
    stats_text = f"R² = {r2:.2f}\nRMSE = {rmse:.1f} m d⁻¹"
    ax1.text(0.02, 0.95, stats_text, transform=ax1.transAxes, verticalalignment='top',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9))
    
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    
    # Panel B: Feature Importance
    ax2 = fig.add_subplot(gs[1])
    
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1]
    top_n = min(8, len(selected_features)) # Max 8 features for clarity
    
    top_indices = indices[:top_n]
    top_feats = [selected_features[i] for i in top_indices]
    top_imps = importances[top_indices]
    
    # Clean label names
    clean_labels = []
    for f in top_feats:
        f = f.replace('_', ' ')
        f = f.replace('cumulative', '')
        f = f.replace('current', '')
        clean_labels.append(f)
        
    y_pos = np.arange(len(clean_labels))
    ax2.barh(y_pos, top_imps, color='#0072B2', alpha=0.8)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(clean_labels)
    ax2.invert_yaxis()
    ax2.set_xlabel('Relative Importance')
    ax2.set_title('(b) Dominant Climate Drivers', loc='left', fontweight='bold')
    ax2.grid(True, axis='x', alpha=0.3)
    
    # Save
    out_file = OUTPUT_DIR / "ml_h3_analysis_publication_quality.png"
    plt.savefig(out_file, dpi=300, bbox_inches='tight')
    print(f"Saved simplified figure to {out_file}")

def main():
    print("Running Simplified ML Analysis...")
    vel, clim = load_and_prepare_data()
    features = create_ml_features_all_climate(clim, vel)
    train_and_visualize(features)
    print("Done.")

if __name__ == "__main__":
    main()
