#!/usr/bin/env python3
"""
IMPROVED Q1-Quality ML Analysis for H3: Climate-Velocity Relationships
======================================================================

This improved version addresses the small dataset issue by:
1. Using all available climate data (full year)
2. Only predicting on actual velocity measurement dates
3. Using feature selection to reduce overfitting
4. Regularized models appropriate for small datasets

Key Features:
- Feature selection (reduce from 39 to ~10-15 most important)
- Regularized models (prevent overfitting)
- Proper validation on actual velocity dates only
- Publication-quality results

Run: python3 ml_h3_improved_analysis.py
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import rcParams
from pathlib import Path
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ML Libraries
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import Ridge, Lasso, ElasticNet
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

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

# Publication settings
PUBLICATION_DPI = 600
FIGURE_SIZE = (16, 12)

def load_and_prepare_data():
    """Load velocity and climate data, prepare for ML analysis."""
    print("=" * 70)
    print("LOADING AND PREPARING DATA FOR ML ANALYSIS")
    print("=" * 70)
    
    # Load velocity
    vel_file = VELOCITY_DIR / "velocity_timeseries_python.csv"
    if not vel_file.exists():
        raise FileNotFoundError(f"Velocity file not found: {vel_file}")
    
    vel = pd.read_csv(vel_file)
    vel['date'] = pd.to_datetime(vel['date'])
    vel = vel.sort_values('date').reset_index(drop=True)
    vel = vel[['date', 'velocity_m_per_day']].copy()
    
    print(f"✅ Loaded {len(vel)} velocity measurements")
    print(f"   Date range: {vel['date'].min()} to {vel['date'].max()}")
    
    # Load climate
    clim_file = CLIMATE_DIR / "climate_derivatives_timeseries.csv"
    if not clim_file.exists():
        raise FileNotFoundError(f"Climate file not found: {clim_file}")
    
    clim = pd.read_csv(clim_file)
    clim['datetime'] = pd.to_datetime(clim['datetime'])
    clim = clim.sort_values('datetime').reset_index(drop=True)
    
    # Aggregate to daily if hourly
    if len(clim) > 365:
        print("   Aggregating hourly to daily...")
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
    
    # Calculate PDD
    clim_daily['pdd'] = np.maximum(clim_daily['temperature_C'], 0)
    clim_daily = clim_daily.sort_values('datetime').reset_index(drop=True)
    
    print(f"✅ Loaded {len(clim_daily)} daily climate records")
    print(f"   Date range: {clim_daily['datetime'].min()} to {clim_daily['datetime'].max()}")
    
    return vel, clim_daily

def create_ml_features_all_climate(clim_daily, vel_df):
    """
    Create ML features for ALL climate data, but only return features
    for dates where we have velocity measurements.
    
    This approach:
    - Uses full climate history for feature calculation
    - Only predicts on actual velocity measurement dates
    - Prevents overfitting from interpolated velocity
    """
    vel_dates = vel_df['date'].dt.date.values
    print("\n" + "=" * 70)
    print("CREATING ML FEATURES (Full Climate History)")
    print("=" * 70)
    
    clim_daily = clim_daily.sort_values('datetime').reset_index(drop=True)
    clim_daily['date'] = clim_daily['datetime']
    
    # Create features for ALL climate dates
    all_features = []
    all_dates = []
    
    print("   Calculating features for all climate dates...")
    for i in range(len(clim_daily)):
        date = clim_daily.iloc[i]['datetime']
        features = {}
        features['date'] = date
        
        # PDD cumulative for multiple windows
        for window in [30, 60, 90, 120, 180]:
            window_start = max(0, i - window)
            window_data = clim_daily.iloc[window_start:i+1]
            features[f'pdd_cumulative_{window}d'] = window_data['pdd'].sum()
        
        # SWE metrics
        features['swe_current'] = clim_daily.iloc[i]['swe_mm']
        features['swe_max'] = clim_daily.iloc[:i+1]['swe_mm'].max()
        features['swe_depletion'] = features['swe_max'] - features['swe_current']
        features['swe_change_30d'] = clim_daily.iloc[i]['swe_mm'] - clim_daily.iloc[max(0, i-30)]['swe_mm']
        features['swe_change_60d'] = clim_daily.iloc[i]['swe_mm'] - clim_daily.iloc[max(0, i-60)]['swe_mm']
        
        # ROS metrics (simplified - just count and intensity for key windows)
        for window in [30, 60, 90]:
            window_start = max(0, i - window)
            window_data = clim_daily.iloc[window_start:i+1]
            
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
        features['day_of_year'] = date.dayofyear
        features['month'] = date.month
        features['day_of_year_sin'] = np.sin(2 * np.pi * date.dayofyear / 365.25)
        features['day_of_year_cos'] = np.cos(2 * np.pi * date.dayofyear / 365.25)
        
        # Key lagged variables (only most important)
        for lag in [1, 7, 14]:
            if i >= lag:
                features[f'pdd_lag_{lag}d'] = clim_daily.iloc[i-lag]['pdd']
            else:
                features[f'pdd_lag_{lag}d'] = 0
        
        # Current climate
        features['pdd_current'] = clim_daily.iloc[i]['pdd']
        features['precip_current'] = clim_daily.iloc[i]['precipitation_mm']
        features['temp_current'] = clim_daily.iloc[i]['temperature_C']
        
        all_features.append(features)
        all_dates.append(date)
    
    # Convert to DataFrame
    features_df = pd.DataFrame(all_features)
    
    # Filter to only velocity measurement dates
    vel_date_set = set(vel_dates)
    features_df['has_velocity'] = features_df['date'].isin(vel_date_set)
    
    # Get velocity values for matching dates
    vel_dict = {}
    for d in vel_dates:
        vel_match = vel_df[vel_df['date'].dt.date == d]
        if len(vel_match) > 0:
            vel_dict[d] = vel_match['velocity_m_per_day'].values[0]
    features_df['velocity_m_per_day'] = features_df['date'].map(vel_dict)
    
    # Only keep rows with velocity measurements
    features_df = features_df[features_df['has_velocity']].drop('has_velocity', axis=1).reset_index(drop=True)
    
    # Fill NaN values (from feature calculation)
    feature_cols = [col for col in features_df.columns if col not in ['date', 'velocity_m_per_day']]
    for col in feature_cols:
        features_df[col] = features_df[col].fillna(0)
    
    print(f"✅ Created features for {len(features_df)} velocity measurement dates")
    print(f"   Total features: {len(features_df.columns) - 2} (excluding date and target)")
    
    return features_df

def select_features(X, y, feature_names, k=15):
    """Select top k features using univariate feature selection."""
    print(f"\n   Selecting top {k} features from {len(feature_names)} candidates...")
    
    selector = SelectKBest(score_func=f_regression, k=min(k, len(feature_names)))
    X_selected = selector.fit_transform(X, y)
    selected_features = [feature_names[i] for i in selector.get_support(indices=True)]
    
    print(f"   ✅ Selected {len(selected_features)} features")
    print(f"   Top features: {', '.join(selected_features[:5])}...")
    
    return X_selected, selected_features, selector

def train_regularized_models(X, y, feature_names):
    """Train regularized models appropriate for small datasets."""
    print("\n" + "=" * 70)
    print("TRAINING REGULARIZED ML MODELS")
    print("=" * 70)
    
    # Feature selection first
    X_selected, selected_features, selector = select_features(X, y, feature_names, k=min(12, len(feature_names)))
    
    # Time-series split (80/20)
    n_train = int(len(X_selected) * 0.8)
    X_train, X_test = X_selected[:n_train], X_selected[n_train:]
    y_train, y_test = y[:n_train], y[n_train:]
    
    print(f"\n   Training set: {len(X_train)} samples")
    print(f"   Test set: {len(X_test)} samples")
    print(f"   Features: {len(selected_features)}")
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    models = {}
    results = {}
    
    # 1. Ridge Regression (L2 regularization)
    print("\n   Training Ridge Regression...")
    ridge = Ridge(alpha=1.0, random_state=42)
    ridge.fit(X_train_scaled, y_train)
    models['Ridge'] = ridge
    
    # 2. Lasso Regression (L1 regularization)
    print("   Training Lasso Regression...")
    lasso = Lasso(alpha=0.1, random_state=42, max_iter=2000)
    lasso.fit(X_train_scaled, y_train)
    models['Lasso'] = lasso
    
    # 3. Elastic Net (L1 + L2)
    print("   Training Elastic Net...")
    elastic = ElasticNet(alpha=0.1, l1_ratio=0.5, random_state=42, max_iter=2000)
    elastic.fit(X_train_scaled, y_train)
    models['Elastic Net'] = elastic
    
    # 4. Regularized Random Forest
    print("   Training Regularized Random Forest...")
    rf = RandomForestRegressor(
        n_estimators=50,
        max_depth=3,  # Very shallow to prevent overfitting
        min_samples_split=max(3, len(X_train) // 5),
        min_samples_leaf=max(2, len(X_train) // 10),
        random_state=42,
        n_jobs=-1
    )
    rf.fit(X_train, y_train)
    models['Random Forest'] = rf
    
    # Evaluate models
    print("\n   Model Performance:")
    print("   " + "-" * 60)
    
    for name, model in models.items():
        if name == 'scaler':
            continue
        
        if name in ['Ridge', 'Lasso', 'Elastic Net']:
            y_pred_train = model.predict(X_train_scaled)
            y_pred_test = model.predict(X_test_scaled)
        else:
            y_pred_train = model.predict(X_train)
            y_pred_test = model.predict(X_test)
        
        r2_train = r2_score(y_train, y_pred_train)
        r2_test = r2_score(y_test, y_pred_test)
        rmse_test = np.sqrt(mean_squared_error(y_test, y_pred_test))
        mae_test = mean_absolute_error(y_test, y_pred_test)
        
        results[name] = {
            'model': model,
            'r2_train': r2_train,
            'r2_test': r2_test,
            'rmse_test': rmse_test,
            'mae_test': mae_test,
            'y_pred_test': y_pred_test,
            'y_test': y_test,
            'y_pred_train': y_pred_train,
            'y_train': y_train
        }
        
        print(f"   {name:20s} | R² (train): {r2_train:6.3f} | R² (test): {r2_test:6.3f} | RMSE: {rmse_test:6.2f} m/d")
    
    # Feature importance from Random Forest
    if 'Random Forest' in models:
        rf_model = models['Random Forest']
        feature_importance = pd.DataFrame({
            'feature': selected_features,
            'importance': rf_model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        results['feature_importance'] = feature_importance
        results['selected_features'] = selected_features
        results['selector'] = selector
        results['scaler'] = scaler
    
    return models, results, X_train, X_test, y_train, y_test, selected_features

def create_publication_visualizations(models, results, features_df, selected_features):
    """Create publication-quality visualizations."""
    print("\n" + "=" * 70)
    print("CREATING PUBLICATION-QUALITY VISUALIZATIONS")
    print("=" * 70)
    
    fig = plt.figure(figsize=FIGURE_SIZE, dpi=100)
    gs = fig.add_gridspec(3, 3, height_ratios=[1, 1, 1], hspace=0.35, wspace=0.3)
    
    # Panel (a): Model performance comparison
    ax1 = fig.add_subplot(gs[0, 0])
    model_names = [name for name in results.keys() if name not in ['feature_importance', 'selected_features', 'selector', 'scaler']]
    r2_scores = [results[name]['r2_test'] for name in model_names]
    rmse_scores = [results[name]['rmse_test'] for name in model_names]
    
    x = np.arange(len(model_names))
    width = 0.35
    
    ax1_twin = ax1.twinx()
    bars1 = ax1.bar(x - width/2, r2_scores, width, label='R²', color='#2E86AB', alpha=0.8)
    bars2 = ax1_twin.bar(x + width/2, rmse_scores, width, label='RMSE (m/d)', color='#F18F01', alpha=0.8)
    
    ax1.set_xlabel('Model', fontsize=12)
    ax1.set_ylabel('R² Score', fontsize=12, color='#2E86AB')
    ax1_twin.set_ylabel('RMSE (m/d)', fontsize=12, color='#F18F01')
    ax1.set_xticks(x)
    ax1.set_xticklabels(model_names, rotation=45, ha='right', fontsize=9)
    ax1.set_title('(a) Model Performance Comparison', fontsize=13, loc='left', pad=10)
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.set_facecolor('#FAFAFA')
    
    # Panel (b): Predicted vs Observed (best model)
    best_model_name = max([name for name in model_names], 
                          key=lambda x: results[x]['r2_test'])
    best_result = results[best_model_name]
    
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.scatter(best_result['y_test'], best_result['y_pred_test'], 
               s=80, alpha=0.7, color='#6A994E', edgecolors='darkgreen', linewidths=1.5)
    
    min_val = min(best_result['y_test'].min(), best_result['y_pred_test'].min())
    max_val = max(best_result['y_test'].max(), best_result['y_pred_test'].max())
    ax2.plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=2, label='1:1 line')
    
    ax2.set_xlabel('Observed Velocity (m d⁻¹)', fontsize=12)
    ax2.set_ylabel('Predicted Velocity (m d⁻¹)', fontsize=12)
    ax2.set_title(f'(b) Predicted vs Observed ({best_model_name})', fontsize=13, loc='left', pad=10)
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)
    ax2.set_facecolor('#FAFAFA')
    
    r2_text = f"R² = {best_result['r2_test']:.3f}\nRMSE = {best_result['rmse_test']:.2f} m/d"
    ax2.text(0.05, 0.95, r2_text, transform=ax2.transAxes, 
            fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Panel (c): Time series
    ax3 = fig.add_subplot(gs[0, 2])
    
    test_dates = features_df['date'].iloc[len(best_result['y_train']):].values
    
    ax3.plot(test_dates, best_result['y_test'], 'o-', linewidth=2.5, 
            markersize=8, color='#2E86AB', label='Observed', alpha=0.8)
    ax3.plot(test_dates, best_result['y_pred_test'], 's-', linewidth=2, 
            markersize=6, color='#C73E1D', label='Predicted', alpha=0.8)
    
    ax3.set_xlabel('Date', fontsize=12)
    ax3.set_ylabel('Velocity (m d⁻¹)', fontsize=12)
    ax3.set_title('(c) Time Series: Observed vs Predicted', fontsize=13, loc='left', pad=10)
    ax3.legend(fontsize=9)
    ax3.grid(True, alpha=0.3)
    ax3.set_facecolor('#FAFAFA')
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=9)
    
    # Panel (d): Feature importance
    ax4 = fig.add_subplot(gs[1, :])
    
    if 'feature_importance' in results:
        top_features = results['feature_importance'].head(12)
        
        y_pos = np.arange(len(top_features))
        ax4.barh(y_pos, top_features['importance'].values, color='#2E86AB', alpha=0.8)
        ax4.set_yticks(y_pos)
        ax4.set_yticklabels(top_features['feature'].values, fontsize=9)
        ax4.set_xlabel('Feature Importance', fontsize=12)
        ax4.set_title('(d) Feature Importance (Random Forest)', fontsize=13, loc='left', pad=10)
        ax4.grid(True, alpha=0.3, axis='x')
        ax4.set_facecolor('#FAFAFA')
        ax4.invert_yaxis()
    
    # Panel (e): PDD window importance
    ax5 = fig.add_subplot(gs[2, 0])
    
    if 'feature_importance' in results:
        pdd_features = results['feature_importance'][
            results['feature_importance']['feature'].str.contains('pdd_cumulative')
        ]
        
        if len(pdd_features) > 0:
            windows = [int(f.split('_')[-1].replace('d', '')) for f in pdd_features['feature']]
            importances = pdd_features['importance'].values
            
            ax5.bar(range(len(windows)), importances, color='#F18F01', alpha=0.8)
            ax5.set_xticks(range(len(windows)))
            ax5.set_xticklabels([f'{w}d' for w in windows], fontsize=9)
            ax5.set_xlabel('PDD Time Window', fontsize=12)
            ax5.set_ylabel('Feature Importance', fontsize=12)
            ax5.set_title('(e) PDD Window Importance', fontsize=13, loc='left', pad=10)
            ax5.grid(True, alpha=0.3, axis='y')
            ax5.set_facecolor('#FAFAFA')
    
    # Panel (f): Climate driver categories
    ax6 = fig.add_subplot(gs[2, 1])
    
    if 'feature_importance' in results:
        pdd_total = results['feature_importance'][
            results['feature_importance']['feature'].str.contains('pdd', case=False)
        ]['importance'].sum()
        
        swe_total = results['feature_importance'][
            results['feature_importance']['feature'].str.contains('swe', case=False)
        ]['importance'].sum()
        
        ros_total = results['feature_importance'][
            results['feature_importance']['feature'].str.contains('ros', case=False)
        ]['importance'].sum()
        
        categories = ['PDD\nFeatures', 'SWE\nFeatures', 'ROS\nFeatures']
        importances = [pdd_total, swe_total, ros_total]
        colors = ['#F18F01', '#6A994E', '#C73E1D']
        
        ax6.bar(categories, importances, color=colors, alpha=0.8)
        ax6.set_ylabel('Total Feature Importance', fontsize=12)
        ax6.set_title('(f) Climate Driver Category Importance', fontsize=13, loc='left', pad=10)
        ax6.grid(True, alpha=0.3, axis='y')
        ax6.set_facecolor('#FAFAFA')
    
    # Panel (g): Model coefficients (for linear models)
    ax7 = fig.add_subplot(gs[2, 2])
    
    if 'Ridge' in results and len(selected_features) <= 12:
        ridge_model = results['Ridge']['model']
        coefficients = ridge_model.coef_
        
        y_pos = np.arange(len(selected_features))
        colors_coef = ['#2E86AB' if c > 0 else '#C73E1D' for c in coefficients]
        ax7.barh(y_pos, coefficients, color=colors_coef, alpha=0.8)
        ax7.set_yticks(y_pos)
        ax7.set_yticklabels(selected_features, fontsize=8)
        ax7.set_xlabel('Coefficient Value', fontsize=12)
        ax7.set_title('(g) Ridge Regression Coefficients', fontsize=13, loc='left', pad=10)
        ax7.axvline(0, color='black', linewidth=1, linestyle='--')
        ax7.grid(True, alpha=0.3, axis='x')
        ax7.set_facecolor('#FAFAFA')
        ax7.invert_yaxis()
    else:
        ax7.text(0.5, 0.5, 'Coefficient plot\nnot available', 
                transform=ax7.transAxes, ha='center', va='center', fontsize=10)
        ax7.set_title('(g) Model Coefficients', fontsize=13, loc='left', pad=10)
    
    # Overall title
    fig.suptitle('H3 ML Analysis: Nonlinear Climate-Velocity Relationships', 
                fontsize=14, y=0.995)
    
    # Save
    output_file = OUTPUT_DIR / "ml_h3_analysis_improved.png"
    plt.savefig(output_file, dpi=PUBLICATION_DPI, bbox_inches='tight', 
                facecolor='white', edgecolor='none', format='png')
    print(f"\n✅ Publication-quality figure saved: {output_file}")
    print(f"   Resolution: {PUBLICATION_DPI} DPI")
    
    plt.close()
    return output_file

def save_results(models, results, selected_features):
    """Save results to files."""
    print("\n" + "=" * 70)
    print("SAVING RESULTS")
    print("=" * 70)
    
    # Model performance
    model_names = [name for name in results.keys() 
                  if name not in ['feature_importance', 'selected_features', 'selector', 'scaler']]
    performance_df = pd.DataFrame({
        'model': model_names,
        'r2_train': [results[m]['r2_train'] for m in model_names],
        'r2_test': [results[m]['r2_test'] for m in model_names],
        'rmse_test': [results[m]['rmse_test'] for m in model_names],
        'mae_test': [results[m]['mae_test'] for m in model_names]
    })
    
    perf_file = OUTPUT_DIR / "model_performance_improved.csv"
    performance_df.to_csv(perf_file, index=False)
    print(f"✅ Model performance saved: {perf_file}")
    
    # Feature importance
    if 'feature_importance' in results:
        importance_file = OUTPUT_DIR / "feature_importance_improved.csv"
        results['feature_importance'].to_csv(importance_file, index=False)
        print(f"✅ Feature importance saved: {importance_file}")
    
    # Summary
    import json
    best_model = max(model_names, key=lambda x: results[x]['r2_test'])
    summary = {
        'best_model': best_model,
        'best_r2_test': float(results[best_model]['r2_test']),
        'best_rmse_test': float(results[best_model]['rmse_test']),
        'selected_features': selected_features,
        'total_features': len(selected_features),
        'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    summary_file = OUTPUT_DIR / "ml_analysis_summary_improved.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"✅ Summary saved: {summary_file}")
    
    return summary

def main():
    """Main function."""
    print("=" * 70)
    print("IMPROVED Q1-QUALITY ML ANALYSIS FOR H3")
    print("=" * 70)
    print()
    
    # Load data
    vel, clim_daily = load_and_prepare_data()
    
    # Create features for all climate data, filter to velocity dates
    features_df = create_ml_features_all_climate(clim_daily, vel)
    
    # Prepare features and target
    feature_columns = [col for col in features_df.columns 
                      if col not in ['date', 'velocity_m_per_day']]
    X = features_df[feature_columns].values
    y = features_df['velocity_m_per_day'].values
    feature_names = feature_columns
    
    print(f"\n✅ Feature matrix: {X.shape[0]} samples × {X.shape[1]} features")
    print(f"✅ Target vector: {len(y)} velocity measurements")
    
    # Train models
    models, results, X_train, X_test, y_train, y_test, selected_features = train_regularized_models(X, y, feature_names)
    
    # Create visualizations
    vis_file = create_publication_visualizations(models, results, features_df, selected_features)
    
    # Save results
    summary = save_results(models, results, selected_features)
    
    # Print summary
    print("\n" + "=" * 70)
    print("ML ANALYSIS SUMMARY")
    print("=" * 70)
    print(f"\nBest Model: {summary['best_model']}")
    print(f"Test R²: {summary['best_r2_test']:.3f}")
    print(f"Test RMSE: {summary['best_rmse_test']:.2f} m/d")
    print(f"\nSelected Features: {summary['total_features']}")
    
    if 'feature_importance' in results:
        print("\nTop 5 Most Important Features:")
        for i, row in results['feature_importance'].head(5).iterrows():
            print(f"  {i+1}. {row['feature']}: {row['importance']:.4f}")
    
    print("\n" + "=" * 70)
    print("✅ IMPROVED ML ANALYSIS COMPLETE!")
    print("=" * 70)

if __name__ == "__main__":
    main()

