#!/usr/bin/env python3
"""
XGBoost Analysis for H3: Climate-Velocity Relationships
======================================================

This script uses XGBoost (eXtreme Gradient Boosting) to analyze
climate-velocity relationships for H3 mechanism testing.

XGBoost advantages:
- Excellent performance on small datasets
- Built-in feature importance
- Handles non-linear relationships
- Regularization to prevent overfitting
- Cross-validation support

Run: python3 ml_h3_xgboost_analysis.py
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
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("⚠️  XGBoost not installed. Install with: pip install xgboost")

from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from scipy.stats import pearsonr

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
FIGURE_SIZE = (16, 12)

def load_and_prepare_data():
    """Load velocity and climate data."""
    print("=" * 70)
    print("LOADING DATA FOR XGBOOST ANALYSIS")
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
    
    print(f"✅ Created features for {len(features_df)} velocity measurements")
    print(f"   Total features: {len(feature_cols)}")
    
    return features_df

def train_xgboost_model(X, y, feature_names):
    """Train XGBoost model with cross-validation."""
    print("\n" + "=" * 70)
    print("TRAINING XGBOOST MODEL")
    print("=" * 70)
    
    if not XGBOOST_AVAILABLE:
        print("❌ XGBoost not available. Please install: pip install xgboost")
        return None, None, None
    
    # XGBoost parameters (regularized for small dataset)
    params = {
        'objective': 'reg:squarederror',
        'n_estimators': 100,
        'max_depth': 3,  # Shallow to prevent overfitting
        'learning_rate': 0.1,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'min_child_weight': 2,  # Regularization
        'gamma': 0.1,  # Regularization
        'reg_alpha': 0.1,  # L1 regularization
        'reg_lambda': 1.0,  # L2 regularization
        'random_state': 42,
        'n_jobs': -1
    }
    
    print(f"\n   Dataset: {len(X)} samples × {len(feature_names)} features")
    print(f"   XGBoost parameters:")
    print(f"     - n_estimators: {params['n_estimators']}")
    print(f"     - max_depth: {params['max_depth']}")
    print(f"     - learning_rate: {params['learning_rate']}")
    print(f"     - Regularization: L1={params['reg_alpha']}, L2={params['reg_lambda']}")
    
    # Train model on all data (for feature importance)
    model = xgb.XGBRegressor(**params)
    model.fit(X, y)
    
    # Predictions
    y_pred = model.predict(X)
    
    # Metrics
    r2 = r2_score(y, y_pred)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    mae = mean_absolute_error(y, y_pred)
    
    print(f"\n   Model Performance (on all data):")
    print(f"     R²: {r2:.3f}")
    print(f"     RMSE: {rmse:.2f} m/d")
    print(f"     MAE: {mae:.2f} m/d")
    
    # Cross-validation (if enough samples)
    if len(X) >= 5:
        print(f"\n   Cross-Validation (TimeSeriesSplit):")
        n_splits = min(5, len(X) - 1)
        tscv = TimeSeriesSplit(n_splits=n_splits)
        
        cv_scores = cross_val_score(model, X, y, cv=tscv, scoring='r2', n_jobs=-1)
        cv_rmse = -cross_val_score(model, X, y, cv=tscv, scoring='neg_root_mean_squared_error', n_jobs=-1)
        
        print(f"     CV R²: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
        print(f"     CV RMSE: {cv_rmse.mean():.2f} ± {cv_rmse.std():.2f} m/d")
    else:
        print(f"\n   ⚠️  Dataset too small for cross-validation (need ≥5 samples)")
        cv_scores = None
        cv_rmse = None
    
    # Feature importance
    print(f"\n   Feature Importance (XGBoost):")
    importance_gain = model.feature_importances_  # Gain-based importance
    importance_df = pd.DataFrame({
        'feature': feature_names,
        'importance_gain': importance_gain
    }).sort_values('importance_gain', ascending=False)
    
    print(f"     Top 10 Features:")
    for i, row in importance_df.head(10).iterrows():
        print(f"       {i+1:2d}. {row['feature']:30s} {row['importance_gain']:.4f}")
    
    results = {
        'model': model,
        'r2': r2,
        'rmse': rmse,
        'mae': mae,
        'y_pred': y_pred,
        'y_true': y,
        'cv_r2_mean': cv_scores.mean() if cv_scores is not None else np.nan,
        'cv_r2_std': cv_scores.std() if cv_scores is not None else np.nan,
        'cv_rmse_mean': cv_rmse.mean() if cv_rmse is not None else np.nan,
        'cv_rmse_std': cv_rmse.std() if cv_rmse is not None else np.nan,
        'feature_importance': importance_df
    }
    
    return model, results, importance_df

def compute_category_importance(importance_df):
    """Compute total importance by climate driver category."""
    print("\n" + "=" * 70)
    print("COMPUTING CATEGORY IMPORTANCE")
    print("=" * 70)
    
    pdd_features = importance_df[importance_df['feature'].str.contains('pdd', case=False)]
    swe_features = importance_df[importance_df['feature'].str.contains('swe', case=False)]
    ros_features = importance_df[importance_df['feature'].str.contains('ros', case=False)]
    
    pdd_total = pdd_features['importance_gain'].sum()
    swe_total = swe_features['importance_gain'].sum()
    ros_total = ros_features['importance_gain'].sum()
    
    total = pdd_total + swe_total + ros_total
    
    pdd_pct = (pdd_total / total) * 100 if total > 0 else 0
    swe_pct = (swe_total / total) * 100 if total > 0 else 0
    ros_pct = (ros_total / total) * 100 if total > 0 else 0
    
    print(f"\nCategory Importance (sum of XGBoost importance):")
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

def create_publication_visualizations(features_df, results, importance_df, category_importance):
    """Create publication-quality visualizations."""
    print("\n" + "=" * 70)
    print("CREATING PUBLICATION-QUALITY VISUALIZATIONS")
    print("=" * 70)
    
    fig = plt.figure(figsize=FIGURE_SIZE, dpi=100)
    gs = fig.add_gridspec(3, 3, height_ratios=[1, 1, 1], hspace=0.35, wspace=0.3)
    
    # Panel (a): Predicted vs Observed
    ax1 = fig.add_subplot(gs[0, 0])
    
    y_true = results['y_true']
    y_pred = results['y_pred']
    
    ax1.scatter(y_true, y_pred, s=100, alpha=0.7, color='#2E86AB', 
               edgecolors='darkblue', linewidths=1.5, zorder=3)
    
    # 1:1 line
    min_val = min(y_true.min(), y_pred.min())
    max_val = max(y_true.max(), y_pred.max())
    ax1.plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=2, 
            label='1:1 line', zorder=2)
    
    ax1.set_xlabel('Observed Velocity (m d⁻¹)', fontsize=12)
    ax1.set_ylabel('Predicted Velocity (m d⁻¹)', fontsize=12)
    ax1.set_title('(a) Predicted vs Observed (XGBoost)', fontsize=13, loc='left', pad=10)
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3, zorder=1)
    ax1.set_facecolor('#FAFAFA')
    
    # Add metrics text
    r2_text = f"R² = {results['r2']:.3f}\nRMSE = {results['rmse']:.2f} m/d"
    ax1.text(0.05, 0.95, r2_text, transform=ax1.transAxes, 
            fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Panel (b): Time series
    ax2 = fig.add_subplot(gs[0, 1])
    
    dates = features_df['date'].values
    
    ax2.plot(dates, y_true, 'o-', linewidth=2.5, markersize=10, 
            color='#2E86AB', label='Observed', alpha=0.8, zorder=3)
    ax2.plot(dates, y_pred, 's-', linewidth=2, markersize=8,
            color='#C73E1D', label='Predicted', alpha=0.8, zorder=2)
    
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel('Velocity (m d⁻¹)', fontsize=12)
    ax2.set_title('(b) Time Series: Observed vs Predicted', fontsize=13, loc='left', pad=10)
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3, zorder=1)
    ax2.set_facecolor('#FAFAFA')
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=9)
    
    # Panel (c): Feature importance (Top 15)
    ax3 = fig.add_subplot(gs[0, 2])
    
    top_features = importance_df.head(15)
    y_pos = np.arange(len(top_features))
    
    ax3.barh(y_pos, top_features['importance_gain'].values, color='#2E86AB', alpha=0.8)
    ax3.set_yticks(y_pos)
    ax3.set_yticklabels(top_features['feature'].values, fontsize=8)
    ax3.set_xlabel('XGBoost Feature Importance (Gain)', fontsize=12)
    ax3.set_title('(c) Top 15 Feature Importance', fontsize=13, loc='left', pad=10)
    ax3.grid(True, alpha=0.3, axis='x', zorder=1)
    ax3.set_facecolor('#FAFAFA')
    ax3.invert_yaxis()
    
    # Panel (d): All features importance
    ax4 = fig.add_subplot(gs[1, :])
    
    y_pos_all = np.arange(len(importance_df))
    ax4.barh(y_pos_all, importance_df['importance_gain'].values, color='#6A994E', alpha=0.8)
    ax4.set_yticks(y_pos_all)
    ax4.set_yticklabels(importance_df['feature'].values, fontsize=9)
    ax4.set_xlabel('XGBoost Feature Importance (Gain)', fontsize=12)
    ax4.set_title('(d) All Features Importance Ranking', fontsize=13, loc='left', pad=10)
    ax4.grid(True, alpha=0.3, axis='x', zorder=1)
    ax4.set_facecolor('#FAFAFA')
    ax4.invert_yaxis()
    
    # Panel (e): PDD window importance
    ax5 = fig.add_subplot(gs[2, 0])
    
    pdd_features = importance_df[importance_df['feature'].str.contains('pdd_cumulative')]
    if len(pdd_features) > 0:
        windows = [int(f.split('_')[-1].replace('d', '')) for f in pdd_features['feature']]
        importances = pdd_features['importance_gain'].values
        
        ax5.bar(range(len(windows)), importances, color='#F18F01', alpha=0.8)
        ax5.set_xticks(range(len(windows)))
        ax5.set_xticklabels([f'{w}d' for w in windows], fontsize=9)
        ax5.set_xlabel('PDD Time Window', fontsize=12)
        ax5.set_ylabel('Feature Importance', fontsize=12)
        ax5.set_title('(e) PDD Window Importance', fontsize=13, loc='left', pad=10)
        ax5.grid(True, alpha=0.3, axis='y', zorder=1)
        ax5.set_facecolor('#FAFAFA')
    
    # Panel (f): Category importance
    ax6 = fig.add_subplot(gs[2, 1])
    
    categories = ['PDD\nFeatures', 'SWE\nFeatures', 'ROS\nFeatures']
    importances = [
        category_importance['pdd_total'],
        category_importance['swe_total'],
        category_importance['ros_total']
    ]
    colors = ['#F18F01', '#6A994E', '#C73E1D']
    
    bars = ax6.bar(categories, importances, color=colors, alpha=0.8)
    ax6.set_ylabel('Total Feature Importance', fontsize=12)
    ax6.set_title('(f) Climate Driver Category Importance', fontsize=13, loc='left', pad=10)
    ax6.grid(True, alpha=0.3, axis='y', zorder=1)
    ax6.set_facecolor('#FAFAFA')
    
    # Add percentage labels
    for i, (bar, pct) in enumerate(zip(bars, [category_importance['pdd_pct'], 
                                               category_importance['swe_pct'],
                                               category_importance['ros_pct']])):
        height = bar.get_height()
        ax6.text(bar.get_x() + bar.get_width()/2., height,
                f'{pct:.1f}%', ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    # Panel (g): Model performance metrics
    ax7 = fig.add_subplot(gs[2, 2])
    ax7.axis('off')
    
    metrics_text = f"""
XGBoost Model Performance:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

R² Score: {results['r2']:.3f}
RMSE: {results['rmse']:.2f} m/d
MAE: {results['mae']:.2f} m/d

Cross-Validation:
  CV R²: {results['cv_r2_mean']:.3f} ± {results['cv_r2_std']:.3f}
  CV RMSE: {results['cv_rmse_mean']:.2f} ± {results['cv_rmse_std']:.2f} m/d

Dataset:
  Samples: {len(y_true)}
  Features: {len(importance_df)}
  
Top Feature:
  {importance_df.iloc[0]['feature']}
  Importance: {importance_df.iloc[0]['importance_gain']:.4f}
    """
    
    ax7.text(0.05, 0.95, metrics_text.strip(), transform=ax7.transAxes,
            fontsize=10, verticalalignment='top', family='monospace',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='gray'))
    ax7.set_title('(g) Model Performance Summary', fontsize=13, loc='left', pad=10)
    
    # Overall title
    fig.suptitle('H3 XGBoost Analysis: Climate-Velocity Relationships', 
                fontsize=14, y=0.995)
    
    # Save
    output_file = OUTPUT_DIR / "ml_h3_xgboost_analysis.png"
    plt.savefig(output_file, dpi=PUBLICATION_DPI, bbox_inches='tight', 
                facecolor='white', edgecolor='none', format='png')
    print(f"\n✅ Publication-quality figure saved: {output_file}")
    print(f"   Resolution: {PUBLICATION_DPI} DPI")
    
    plt.close()
    return output_file

def save_results(results, importance_df, category_importance):
    """Save results to files."""
    print("\n" + "=" * 70)
    print("SAVING RESULTS")
    print("=" * 70)
    
    # Save feature importance
    importance_file = OUTPUT_DIR / "xgboost_feature_importance.csv"
    importance_df.to_csv(importance_file, index=False)
    print(f"✅ Feature importance saved: {importance_file}")
    
    # Save summary
    import json
    # Convert all values to native Python types for JSON serialization
    def convert_to_python_type(val):
        if isinstance(val, (np.integer, np.int64, np.int32)):
            return int(val)
        elif isinstance(val, (np.floating, np.float64, np.float32)):
            return float(val)
        elif isinstance(val, np.ndarray):
            return val.tolist()
        elif pd.isna(val):
            return None
        return val
    
    category_importance_clean = {k: convert_to_python_type(v) for k, v in category_importance.items()}
    
    summary = {
        'model': 'XGBoost',
        'r2': convert_to_python_type(results['r2']),
        'rmse': convert_to_python_type(results['rmse']),
        'mae': convert_to_python_type(results['mae']),
        'cv_r2_mean': convert_to_python_type(results['cv_r2_mean']),
        'cv_r2_std': convert_to_python_type(results['cv_r2_std']),
        'cv_rmse_mean': convert_to_python_type(results['cv_rmse_mean']),
        'cv_rmse_std': convert_to_python_type(results['cv_rmse_std']),
        'top_feature': importance_df.iloc[0]['feature'],
        'top_importance': convert_to_python_type(importance_df.iloc[0]['importance_gain']),
        'category_importance': category_importance_clean,
        'total_features': len(importance_df),
        'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    summary_file = OUTPUT_DIR / "xgboost_analysis_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"✅ Summary saved: {summary_file}")
    
    return summary

def main():
    """Main function."""
    print("=" * 70)
    print("XGBOOST ANALYSIS FOR H3: CLIMATE-VELOCITY RELATIONSHIPS")
    print("=" * 70)
    print()
    
    if not XGBOOST_AVAILABLE:
        print("❌ XGBoost not available.")
        print("   Install with: pip install xgboost")
        return
    
    # Load data
    vel, clim_daily = load_and_prepare_data()
    
    # Create features
    features_df = create_features_for_velocity_dates(vel, clim_daily)
    
    # Prepare features and target
    feature_cols = [col for col in features_df.columns 
                    if col not in ['date', 'velocity_m_per_day']]
    X = features_df[feature_cols].values
    y = features_df['velocity_m_per_day'].values
    feature_names = feature_cols
    
    print(f"\n✅ Feature matrix: {X.shape[0]} samples × {X.shape[1]} features")
    print(f"✅ Target vector: {len(y)} velocity measurements")
    
    # Train XGBoost model
    model, results, importance_df = train_xgboost_model(X, y, feature_names)
    
    if model is None:
        return
    
    # Compute category importance
    category_importance = compute_category_importance(importance_df)
    
    # Create visualizations
    vis_file = create_publication_visualizations(features_df, results, importance_df, category_importance)
    
    # Save results
    summary = save_results(results, importance_df, category_importance)
    
    # Print summary
    print("\n" + "=" * 70)
    print("XGBOOST ANALYSIS SUMMARY")
    print("=" * 70)
    print(f"\nModel Performance:")
    print(f"  R²: {summary['r2']:.3f}")
    print(f"  RMSE: {summary['rmse']:.2f} m/d")
    print(f"  MAE: {summary['mae']:.2f} m/d")
    
    if summary['cv_r2_mean'] is not None:
        print(f"\nCross-Validation:")
        print(f"  CV R²: {summary['cv_r2_mean']:.3f} ± {summary['cv_r2_std']:.3f}")
        print(f"  CV RMSE: {summary['cv_rmse_mean']:.2f} ± {summary['cv_rmse_std']:.2f} m/d")
    
    print(f"\nCategory Importance:")
    print(f"  PDD: {category_importance['pdd_pct']:.1f}%")
    print(f"  SWE: {category_importance['swe_pct']:.1f}%")
    print(f"  ROS: {category_importance['ros_pct']:.1f}%")
    
    print(f"\nTop 5 Features:")
    for i, row in importance_df.head(5).iterrows():
        print(f"  {i+1}. {row['feature']:30s} {row['importance_gain']:.4f}")
    
    print("\n" + "=" * 70)
    print("✅ XGBOOST ANALYSIS COMPLETE!")
    print("=" * 70)

if __name__ == "__main__":
    main()

