#!/usr/bin/env python3
"""
Q1-Quality ML Analysis for H3: Nonlinear Climate-Velocity Relationships
======================================================================

This script performs sophisticated machine learning analysis to quantify
the relationship between climate drivers (PDD, SWE, ROS) and glacier velocity,
providing publication-quality results for H3 mechanism testing.

Key Features:
- Multiple ML algorithms (Random Forest, Gradient Boosting, Neural Networks)
- Temporal lag analysis (when do climate variables matter most?)
- Feature importance with SHAP values (state-of-the-art interpretation)
- Uncertainty quantification (ensemble methods, cross-validation)
- Proper train/test splits and validation
- Publication-quality visualizations

Run: python3 ml_h3_climate_velocity_analysis.py
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import rcParams
import seaborn as sns
from pathlib import Path
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ML Libraries
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
import shap

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
    
    # Merge velocity and climate on date
    vel['date_only'] = vel['date'].dt.date
    clim_daily['date_only'] = clim_daily['datetime'].dt.date
    
    merged = pd.merge(vel, clim_daily, on='date_only', how='inner')
    
    # Ensure 'date' column exists (use from velocity)
    if 'date' not in merged.columns:
        merged['date'] = merged['date_x'] if 'date_x' in merged.columns else pd.to_datetime(merged['date_only'])
    
    merged = merged.sort_values('date').reset_index(drop=True)
    
    print(f"✅ Merged dataset: {len(merged)} records")
    
    return merged

def create_ml_features(df, use_all_climate_data=False):
    """
    Create comprehensive ML features from climate data.
    
    Features include:
    - PDD in multiple time windows (30, 60, 90, 120, 180 days)
    - SWE metrics (current, max, depletion rate)
    - ROS events (count, intensity, timing)
    - Temporal features (day of year, month)
    - Lagged climate variables
    
    Parameters:
    - use_all_climate_data: If True, use all climate data and interpolate velocity
    """
    print("\n" + "=" * 70)
    print("CREATING ML FEATURES")
    print("=" * 70)
    
    df = df.sort_values('date').reset_index(drop=True)
    
    # If dataset is small and use_all_climate_data is True, expand to all climate dates
    if use_all_climate_data and len(df) < 20:
        print("   ⚠️  Small dataset detected. Expanding to all available climate data...")
        # Get all unique dates from climate data
        all_dates = pd.date_range(
            start=df['date'].min(), 
            end=df['date'].max(), 
            freq='D'
        )
        
        # Create expanded dataframe
        expanded_df = pd.DataFrame({'date': all_dates})
        expanded_df['date_only'] = expanded_df['date'].dt.date
        
        # Merge with original data
        df['date_only'] = df['date'].dt.date
        expanded_df = pd.merge(expanded_df, df.drop('date', axis=1, errors='ignore'), 
                               on='date_only', how='left')
        
        # Interpolate velocity for missing dates
        if 'velocity_m_per_day' in expanded_df.columns:
            expanded_df['velocity_m_per_day'] = expanded_df['velocity_m_per_day'].interpolate(method='linear', limit_direction='both')
        
        # Forward fill climate variables
        climate_cols = ['temperature_C', 'precipitation_mm', 'swe_mm', 'pdd']
        for col in climate_cols:
            if col in expanded_df.columns:
                expanded_df[col] = expanded_df[col].fillna(method='ffill').fillna(method='bfill')
        
        df = expanded_df.drop('date_only', axis=1, errors='ignore').reset_index(drop=True)
        print(f"   ✅ Expanded to {len(df)} records (interpolated velocity)")
    
    features_df = df[['date', 'velocity_m_per_day']].copy()
    
    # Calculate cumulative PDD for multiple windows
    print("   Calculating cumulative PDD for multiple time windows...")
    for window in [30, 60, 90, 120, 180]:
        pdd_cumulative = []
        for i in range(len(df)):
            window_start = max(0, i - window)
            window_data = df.iloc[window_start:i+1]
            pdd_sum = window_data['pdd'].sum()
            pdd_cumulative.append(pdd_sum)
        features_df[f'pdd_cumulative_{window}d'] = pdd_cumulative
    
    # SWE metrics
    print("   Calculating SWE metrics...")
    features_df['swe_current'] = df['swe_mm'].values
    features_df['swe_max'] = df['swe_mm'].expanding().max()
    features_df['swe_depletion'] = features_df['swe_max'] - features_df['swe_current']
    
    # SWE change rates
    features_df['swe_change_30d'] = df['swe_mm'].diff(30).fillna(0)
    features_df['swe_change_60d'] = df['swe_mm'].diff(60).fillna(0)
    
    # ROS detection and metrics
    print("   Calculating ROS metrics...")
    ros_temp_threshold = 0.5
    ros_swe_threshold = 0.1
    ros_precip_threshold = 0.1
    
    # ROS events in different time windows
    for window in [7, 14, 30, 60, 90]:
        ros_count = []
        ros_intensity_sum = []
        for i in range(len(df)):
            window_start = max(0, i - window)
            window_data = df.iloc[window_start:i+1]
            
            ros_mask = (
                (window_data['temperature_C'] > ros_temp_threshold) &
                (window_data['precipitation_mm'] > ros_precip_threshold) &
                (window_data['swe_mm'] > ros_swe_threshold)
            )
            ros_events = window_data[ros_mask]
            
            ros_count.append(len(ros_events))
            if len(ros_events) > 0:
                ros_intensity = (ros_events['precipitation_mm'] * 
                               (ros_events['temperature_C'] - ros_temp_threshold)).sum()
                ros_intensity_sum.append(ros_intensity)
            else:
                ros_intensity_sum.append(0)
        
        features_df[f'ros_count_{window}d'] = ros_count
        features_df[f'ros_intensity_{window}d'] = ros_intensity_sum
    
    # Temporal features
    print("   Adding temporal features...")
    features_df['day_of_year'] = pd.to_datetime(features_df['date']).dt.dayofyear
    features_df['month'] = pd.to_datetime(features_df['date']).dt.month
    features_df['day_of_year_sin'] = np.sin(2 * np.pi * features_df['day_of_year'] / 365.25)
    features_df['day_of_year_cos'] = np.cos(2 * np.pi * features_df['day_of_year'] / 365.25)
    
    # Lagged climate variables (1, 3, 7, 14 days)
    print("   Adding lagged climate variables...")
    for lag in [1, 3, 7, 14]:
        features_df[f'pdd_lag_{lag}d'] = df['pdd'].shift(lag).fillna(0)
        features_df[f'precip_lag_{lag}d'] = df['precipitation_mm'].shift(lag).fillna(0)
        features_df[f'temp_lag_{lag}d'] = df['temperature_C'].shift(lag).fillna(0)
    
    # Current climate variables
    features_df['pdd_current'] = df['pdd'].values
    features_df['precip_current'] = df['precipitation_mm'].values
    features_df['temp_current'] = df['temperature_C'].values
    
    # Remove rows with NaN (from feature creation)
    features_df = features_df.dropna().reset_index(drop=True)
    
    print(f"✅ Created {len(features_df.columns) - 2} features (excluding date and target)")
    print(f"   Final dataset: {len(features_df)} records")
    
    return features_df

def train_ml_models(X, y, test_size=0.2):
    """
    Train multiple ML models with proper time-series cross-validation.
    
    Models:
    - Random Forest (interpretable, robust)
    - Gradient Boosting (high performance)
    - Neural Network (nonlinear relationships)
    """
    print("\n" + "=" * 70)
    print("TRAINING ML MODELS")
    print("=" * 70)
    
    # Time-series split (no shuffling, respect temporal order)
    n_train = int(len(X) * (1 - test_size))
    X_train, X_test = X[:n_train], X[n_train:]
    y_train, y_test = y[:n_train], y[n_train:]
    
    print(f"   Training set: {len(X_train)} samples")
    print(f"   Test set: {len(X_test)} samples")
    
    # Scale features for neural network
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    models = {}
    results = {}
    
    # Adjust model complexity based on dataset size
    if len(X_train) < 30:
        # Smaller, more regularized models for small datasets
        rf_n_estimators = 50
        rf_max_depth = 5
        gb_n_estimators = 50
        gb_max_depth = 3
        print("   ⚠️  Small dataset: Using regularized models to prevent overfitting")
    else:
        rf_n_estimators = 200
        rf_max_depth = 15
        gb_n_estimators = 200
        gb_max_depth = 8
    
    # 1. Random Forest
    print("\n   Training Random Forest...")
    rf = RandomForestRegressor(
        n_estimators=rf_n_estimators,
        max_depth=rf_max_depth,
        min_samples_split=max(5, len(X_train) // 10),  # Adaptive based on dataset size
        min_samples_leaf=max(2, len(X_train) // 20),
        random_state=42,
        n_jobs=-1
    )
    rf.fit(X_train, y_train)
    models['Random Forest'] = rf
    
    # 2. Gradient Boosting
    print("   Training Gradient Boosting...")
    gb = GradientBoostingRegressor(
        n_estimators=gb_n_estimators,
        max_depth=gb_max_depth,
        learning_rate=0.05,
        min_samples_split=max(5, len(X_train) // 10),
        min_samples_leaf=max(2, len(X_train) // 20),
        random_state=42
    )
    gb.fit(X_train, y_train)
    models['Gradient Boosting'] = gb
    
    # 3. Neural Network (adjust for small datasets)
    print("   Training Neural Network...")
    # Adjust validation fraction based on dataset size
    val_fraction = max(0.1, min(0.2, 2.0 / len(X_train))) if len(X_train) < 20 else 0.1
    
    nn = MLPRegressor(
        hidden_layer_sizes=(64, 32) if len(X_train) < 20 else (128, 64, 32),  # Smaller network for small datasets
        activation='relu',
        solver='adam',
        alpha=0.01,
        learning_rate='adaptive',
        max_iter=1000,
        random_state=42,
        early_stopping=True if len(X_train) >= 10 else False,  # Disable early stopping for very small datasets
        validation_fraction=val_fraction if len(X_train) >= 10 else 0.0
    )
    nn.fit(X_train_scaled, y_train)
    models['Neural Network'] = nn
    models['scaler'] = scaler  # Store scaler for NN
    
    # Evaluate models
    print("\n   Model Performance:")
    print("   " + "-" * 60)
    
    for name, model in models.items():
        if name == 'scaler':
            continue
        
        if name == 'Neural Network':
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
            'y_test': y_test
        }
        
        print(f"   {name:20s} | R² (train): {r2_train:.3f} | R² (test): {r2_test:.3f} | RMSE: {rmse_test:.2f} m/d")
    
    # Cross-validation for robustness (only if enough data)
    if len(X_train) >= 5:
        print("\n   Cross-Validation (TimeSeriesSplit):")
        n_splits = min(5, len(X_train) - 1)  # Adjust splits for small datasets
        tscv = TimeSeriesSplit(n_splits=n_splits)
        
        for name, model in models.items():
            if name == 'scaler':
                continue
            
            try:
                if name == 'Neural Network':
                    cv_scores = cross_val_score(model, X_train_scaled, y_train, 
                                               cv=tscv, scoring='r2', n_jobs=-1)
                else:
                    cv_scores = cross_val_score(model, X_train, y_train, 
                                               cv=tscv, scoring='r2', n_jobs=-1)
                
                print(f"   {name:20s} | CV R²: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
                results[name]['cv_r2_mean'] = cv_scores.mean()
                results[name]['cv_r2_std'] = cv_scores.std()
            except Exception as e:
                print(f"   {name:20s} | CV failed: {e}")
                results[name]['cv_r2_mean'] = np.nan
                results[name]['cv_r2_std'] = np.nan
    else:
        print("\n   ⚠️  Dataset too small for cross-validation (need ≥5 samples)")
        for name in results.keys():
            results[name]['cv_r2_mean'] = np.nan
            results[name]['cv_r2_std'] = np.nan
    
    return models, results, X_train, X_test, y_train, y_test

def calculate_feature_importance(models, X_train, feature_names):
    """
    Calculate feature importance using multiple methods.
    
    Methods:
    - Permutation importance (model-agnostic)
    - Tree-based importance (for RF and GB)
    - SHAP values (state-of-the-art interpretation)
    """
    print("\n" + "=" * 70)
    print("CALCULATING FEATURE IMPORTANCE")
    print("=" * 70)
    
    importance_results = {}
    
    # Use Random Forest for feature importance (most interpretable)
    rf_model = models['Random Forest']
    
    # 1. Tree-based importance (Gini importance)
    print("   Calculating tree-based importance...")
    tree_importance = rf_model.feature_importances_
    importance_df = pd.DataFrame({
        'feature': feature_names,
        'importance': tree_importance
    }).sort_values('importance', ascending=False)
    
    importance_results['tree_based'] = importance_df
    
    # 2. Permutation importance
    print("   Calculating permutation importance...")
    from sklearn.inspection import permutation_importance
    
    perm_importance = permutation_importance(
        rf_model, X_train, 
        models['Random Forest'].predict(X_train),
        n_repeats=10,
        random_state=42,
        n_jobs=-1
    )
    
    perm_df = pd.DataFrame({
        'feature': feature_names,
        'importance_mean': perm_importance.importances_mean,
        'importance_std': perm_importance.importances_std
    }).sort_values('importance_mean', ascending=False)
    
    importance_results['permutation'] = perm_df
    
    # 3. SHAP values (for top model)
    print("   Calculating SHAP values (this may take a moment)...")
    try:
        # Use subset for SHAP (faster)
        shap_sample_size = min(100, len(X_train))
        X_train_sample = X_train[:shap_sample_size]
        
        explainer = shap.TreeExplainer(rf_model)
        shap_values = explainer.shap_values(X_train_sample)
        
        # Calculate mean absolute SHAP values
        shap_importance = np.abs(shap_values).mean(axis=0)
        shap_df = pd.DataFrame({
            'feature': feature_names,
            'shap_importance': shap_importance
        }).sort_values('shap_importance', ascending=False)
        
        importance_results['shap'] = shap_df
        importance_results['shap_values'] = shap_values
        importance_results['shap_explainer'] = explainer
        importance_results['X_train_sample'] = X_train_sample
        
        print(f"   ✅ SHAP values calculated for {shap_sample_size} samples")
    except Exception as e:
        print(f"   ⚠️  SHAP calculation failed: {e}")
        print("   Continuing without SHAP values...")
    
    return importance_results

def create_publication_visualizations(models, results, importance_results, 
                                     features_df, feature_names):
    """Create publication-quality visualizations for H3 ML analysis."""
    print("\n" + "=" * 70)
    print("CREATING PUBLICATION-QUALITY VISUALIZATIONS")
    print("=" * 70)
    
    fig = plt.figure(figsize=FIGURE_SIZE, dpi=100)
    gs = fig.add_gridspec(3, 3, height_ratios=[1, 1, 1], hspace=0.35, wspace=0.3)
    
    # Panel (a): Model performance comparison
    ax1 = fig.add_subplot(gs[0, 0])
    model_names = [name for name in results.keys() if name != 'scaler']
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
    ax1.set_xticklabels(model_names, rotation=45, ha='right')
    ax1.set_title('(a) Model Performance Comparison', fontsize=13, loc='left', pad=10)
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.set_facecolor('#FAFAFA')
    
    # Panel (b): Predicted vs Observed (best model)
    best_model_name = max(model_names, key=lambda x: results[x]['r2_test'])
    best_result = results[best_model_name]
    
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.scatter(best_result['y_test'], best_result['y_pred_test'], 
               s=60, alpha=0.7, color='#6A994E', edgecolors='darkgreen', linewidths=1)
    
    # 1:1 line
    min_val = min(best_result['y_test'].min(), best_result['y_pred_test'].min())
    max_val = max(best_result['y_test'].max(), best_result['y_pred_test'].max())
    ax2.plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=2, label='1:1 line')
    
    ax2.set_xlabel('Observed Velocity (m d⁻¹)', fontsize=12)
    ax2.set_ylabel('Predicted Velocity (m d⁻¹)', fontsize=12)
    ax2.set_title(f'(b) Predicted vs Observed ({best_model_name})', fontsize=13, loc='left', pad=10)
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)
    ax2.set_facecolor('#FAFAFA')
    
    # Add R² text
    r2_text = f"R² = {best_result['r2_test']:.3f}\nRMSE = {best_result['rmse_test']:.2f} m/d"
    ax2.text(0.05, 0.95, r2_text, transform=ax2.transAxes, 
            fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Panel (c): Time series of predictions
    ax3 = fig.add_subplot(gs[0, 2])
    
    # Get dates for test set
    n_train = int(len(features_df) * 0.8)
    test_dates = features_df['date'].iloc[n_train:].values
    
    ax3.plot(test_dates, best_result['y_test'], 'o-', linewidth=2, 
            markersize=6, color='#2E86AB', label='Observed', alpha=0.8)
    ax3.plot(test_dates, best_result['y_pred_test'], 's-', linewidth=2, 
            markersize=5, color='#C73E1D', label='Predicted', alpha=0.8)
    
    ax3.set_xlabel('Date', fontsize=12)
    ax3.set_ylabel('Velocity (m d⁻¹)', fontsize=12)
    ax3.set_title('(c) Time Series: Observed vs Predicted', fontsize=13, loc='left', pad=10)
    ax3.legend(fontsize=9)
    ax3.grid(True, alpha=0.3)
    ax3.set_facecolor('#FAFAFA')
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=9)
    
    # Panel (d): Feature importance (Top 15)
    ax4 = fig.add_subplot(gs[1, :])
    
    if 'tree_based' in importance_results:
        top_features = importance_results['tree_based'].head(15)
        
        y_pos = np.arange(len(top_features))
        ax4.barh(y_pos, top_features['importance'].values, color='#2E86AB', alpha=0.8)
        ax4.set_yticks(y_pos)
        ax4.set_yticklabels(top_features['feature'].values, fontsize=9)
        ax4.set_xlabel('Feature Importance', fontsize=12)
        ax4.set_title('(d) Top 15 Feature Importance (Random Forest)', fontsize=13, loc='left', pad=10)
        ax4.grid(True, alpha=0.3, axis='x')
        ax4.set_facecolor('#FAFAFA')
        ax4.invert_yaxis()
    
    # Panel (e): SHAP summary plot (if available)
    if 'shap' in importance_results and 'shap_values' in importance_results:
        ax5 = fig.add_subplot(gs[2, 0])
        
        shap_values = importance_results['shap_values']
        X_sample = importance_results['X_train_sample']
        
        # Get top 10 features by SHAP importance
        top_shap_features = importance_results['shap'].head(10)
        top_feature_indices = [feature_names.index(f) for f in top_shap_features['feature'].values]
        
        # Plot SHAP values for top features
        shap_summary = np.abs(shap_values[:, top_feature_indices]).mean(axis=0)
        y_pos = np.arange(len(top_feature_indices))
        
        ax5.barh(y_pos, shap_summary, color='#6A994E', alpha=0.8)
        ax5.set_yticks(y_pos)
        ax5.set_yticklabels([feature_names[i] for i in top_feature_indices], fontsize=9)
        ax5.set_xlabel('Mean |SHAP Value|', fontsize=12)
        ax5.set_title('(e) SHAP Feature Importance (Top 10)', fontsize=13, loc='left', pad=10)
        ax5.grid(True, alpha=0.3, axis='x')
        ax5.set_facecolor('#FAFAFA')
        ax5.invert_yaxis()
    else:
        ax5 = fig.add_subplot(gs[2, 0])
        ax5.text(0.5, 0.5, 'SHAP values\nnot available', 
                transform=ax5.transAxes, ha='center', va='center', fontsize=12)
        ax5.set_title('(e) SHAP Feature Importance', fontsize=13, loc='left', pad=10)
    
    # Panel (f): Feature importance comparison (PDD windows)
    ax6 = fig.add_subplot(gs[2, 1])
    
    if 'tree_based' in importance_results:
        pdd_features = [f for f in importance_results['tree_based']['feature'] 
                       if 'pdd_cumulative' in f]
        pdd_importance = importance_results['tree_based'][
            importance_results['tree_based']['feature'].isin(pdd_features)
        ].sort_values('feature')
        
        if len(pdd_importance) > 0:
            windows = [int(f.split('_')[-1].replace('d', '')) for f in pdd_importance['feature']]
            ax6.bar(range(len(windows)), pdd_importance['importance'].values, 
                   color='#F18F01', alpha=0.8)
            ax6.set_xticks(range(len(windows)))
            ax6.set_xticklabels([f'{w}d' for w in windows], fontsize=9)
            ax6.set_xlabel('PDD Time Window', fontsize=12)
            ax6.set_ylabel('Feature Importance', fontsize=12)
            ax6.set_title('(f) PDD Window Importance', fontsize=13, loc='left', pad=10)
            ax6.grid(True, alpha=0.3, axis='y')
            ax6.set_facecolor('#FAFAFA')
    
    # Panel (g): ROS vs PDD importance comparison
    ax7 = fig.add_subplot(gs[2, 2])
    
    if 'tree_based' in importance_results:
        ros_features = [f for f in importance_results['tree_based']['feature'] 
                       if 'ros' in f.lower()]
        pdd_features_all = [f for f in importance_results['tree_based']['feature'] 
                           if 'pdd' in f.lower()]
        swe_features = [f for f in importance_results['tree_based']['feature'] 
                       if 'swe' in f.lower()]
        
        ros_importance = importance_results['tree_based'][
            importance_results['tree_based']['feature'].isin(ros_features)
        ]['importance'].sum()
        pdd_importance_sum = importance_results['tree_based'][
            importance_results['tree_based']['feature'].isin(pdd_features_all)
        ]['importance'].sum()
        swe_importance = importance_results['tree_based'][
            importance_results['tree_based']['feature'].isin(swe_features)
        ]['importance'].sum()
        
        categories = ['PDD\nFeatures', 'SWE\nFeatures', 'ROS\nFeatures']
        importances = [pdd_importance_sum, swe_importance, ros_importance]
        colors = ['#F18F01', '#6A994E', '#C73E1D']
        
        ax7.bar(categories, importances, color=colors, alpha=0.8)
        ax7.set_ylabel('Total Feature Importance', fontsize=12)
        ax7.set_title('(g) Climate Driver Category Importance', fontsize=13, loc='left', pad=10)
        ax7.grid(True, alpha=0.3, axis='y')
        ax7.set_facecolor('#FAFAFA')
    
    # Overall title
    fig.suptitle('H3 ML Analysis: Nonlinear Climate-Velocity Relationships', 
                fontsize=14, y=0.995)
    
    # Save
    output_file = OUTPUT_DIR / "ml_h3_analysis.png"
    plt.savefig(output_file, dpi=PUBLICATION_DPI, bbox_inches='tight', 
                facecolor='white', edgecolor='none', format='png')
    print(f"\n✅ Publication-quality figure saved: {output_file}")
    print(f"   Resolution: {PUBLICATION_DPI} DPI")
    
    plt.close()
    return output_file

def save_results(models, results, importance_results, feature_names):
    """Save ML analysis results to JSON and CSV files."""
    print("\n" + "=" * 70)
    print("SAVING RESULTS")
    print("=" * 70)
    
    # Save model performance
    performance_df = pd.DataFrame({
        'model': list(results.keys()),
        'r2_train': [results[m]['r2_train'] for m in results.keys()],
        'r2_test': [results[m]['r2_test'] for m in results.keys()],
        'rmse_test': [results[m]['rmse_test'] for m in results.keys()],
        'mae_test': [results[m]['mae_test'] for m in results.keys()],
        'cv_r2_mean': [results[m].get('cv_r2_mean', np.nan) for m in results.keys()],
        'cv_r2_std': [results[m].get('cv_r2_std', np.nan) for m in results.keys()]
    })
    
    perf_file = OUTPUT_DIR / "model_performance.csv"
    performance_df.to_csv(perf_file, index=False)
    print(f"✅ Model performance saved: {perf_file}")
    
    # Save feature importance
    if 'tree_based' in importance_results:
        importance_file = OUTPUT_DIR / "feature_importance.csv"
        importance_results['tree_based'].to_csv(importance_file, index=False)
        print(f"✅ Feature importance saved: {importance_file}")
    
    # Save summary statistics
    summary = {
        'best_model': max(results.keys(), key=lambda x: results[x]['r2_test']),
        'best_r2_test': max([results[m]['r2_test'] for m in results.keys()]),
        'best_rmse_test': min([results[m]['rmse_test'] for m in results.keys()]),
        'total_features': len(feature_names),
        'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    import json
    summary_file = OUTPUT_DIR / "ml_analysis_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"✅ Summary saved: {summary_file}")
    
    return summary

def main():
    """Main function."""
    print("=" * 70)
    print("Q1-QUALITY ML ANALYSIS FOR H3: CLIMATE-VELOCITY RELATIONSHIPS")
    print("=" * 70)
    print()
    
    # Load and prepare data
    merged = load_and_prepare_data()
    
    # Create ML features (expand dataset if too small)
    if len(merged) < 20:
        print("\n⚠️  Small dataset detected. Expanding to all available climate data...")
        features_df = create_ml_features(merged, use_all_climate_data=True)
    else:
        features_df = create_ml_features(merged, use_all_climate_data=False)
    
    # Prepare features and target
    feature_columns = [col for col in features_df.columns 
                      if col not in ['date', 'velocity_m_per_day']]
    X = features_df[feature_columns].values
    y = features_df['velocity_m_per_day'].values
    feature_names = feature_columns
    
    print(f"\n✅ Feature matrix: {X.shape[0]} samples × {X.shape[1]} features")
    print(f"✅ Target vector: {len(y)} velocity measurements")
    
    # Check dataset size
    if len(X) < 5:
        print("\n" + "=" * 70)
        print("⚠️  WARNING: SMALL DATASET")
        print("=" * 70)
        print(f"   Only {len(X)} samples available after feature creation.")
        print("   ML models may have limited predictive power.")
        print("   Consider:")
        print("   1. Using all available climate data (interpolate velocity if needed)")
        print("   2. Reducing feature complexity")
        print("   3. Using simpler models (linear regression)")
        print("\n   Continuing with available data...")
        print("=" * 70)
    
    # Train ML models
    models, results, X_train, X_test, y_train, y_test = train_ml_models(X, y)
    
    # Calculate feature importance
    importance_results = calculate_feature_importance(models, X_train, feature_names)
    
    # Create visualizations
    vis_file = create_publication_visualizations(
        models, results, importance_results, features_df, feature_names
    )
    
    # Save results
    summary = save_results(models, results, importance_results, feature_names)
    
    # Print summary
    print("\n" + "=" * 70)
    print("ML ANALYSIS SUMMARY")
    print("=" * 70)
    print(f"\nBest Model: {summary['best_model']}")
    print(f"Test R²: {summary['best_r2_test']:.3f}")
    print(f"Test RMSE: {summary['best_rmse_test']:.2f} m/d")
    print(f"\nTotal Features: {summary['total_features']}")
    
    if 'tree_based' in importance_results:
        print("\nTop 5 Most Important Features:")
        for i, row in importance_results['tree_based'].head(5).iterrows():
            print(f"  {i+1}. {row['feature']}: {row['importance']:.4f}")
    
    print("\n" + "=" * 70)
    print("✅ Q1-QUALITY ML ANALYSIS COMPLETE!")
    print("=" * 70)
    print(f"\nResults saved to: {OUTPUT_DIR}")
    print(f"Figure saved: {vis_file}")
    print("\nReady for publication integration!")

if __name__ == "__main__":
    main()

