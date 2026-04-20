#!/usr/bin/env python3
"""
Calculate LOD values, σ_alg maps, and masked pixel statistics per epoch.
"""

import numpy as np
import pandas as pd
import rasterio
from pathlib import Path
from datetime import datetime
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams

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
VELOCITY_MAPS_DIR = Path("satellite_data/sentinel1/processed/velocity_maps")
VELOCITY_TS_FILE = Path("satellite_data/sentinel1/processed/velocity_timeseries_python.csv")
OUTPUT_DIR = Path("processed_data/uncertainty_analysis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Parameters
STABLE_BEDROCK_THRESHOLD = 0.1  # m/day
MIN_CORRELATION = 0.3
LOD_FACTOR = 2.0  # μ + 2σ
GLACIER_LOCATION = (70.75, 38.97)  # lon, lat

print("=" * 80)
print("CALCULATING LOD VALUES AND UNCERTAINTY STATISTICS")
print("=" * 80)

# Load velocity time series
df_vel = pd.read_csv(VELOCITY_TS_FILE)
df_vel['date'] = pd.to_datetime(df_vel['date'])

# Find all velocity map files
velocity_map_files = sorted(VELOCITY_MAPS_DIR.glob("velocity_*.tif"))

print(f"\nFound {len(velocity_map_files)} velocity maps")
print(f"Found {len(df_vel)} velocity time series records")

# Storage for results
lod_results = []
mask_stats = []
sigma_alg_results = []

for vel_map_file in velocity_map_files:
    print(f"\nProcessing: {vel_map_file.name}")
    
    # Extract dates from filename
    filename_parts = vel_map_file.stem.split('_')
    date1_str = filename_parts[1] if len(filename_parts) > 1 else None
    date2_str = filename_parts[2] if len(filename_parts) > 2 else None
    
    if date1_str and date2_str:
        try:
            date1 = datetime.strptime(date1_str, '%Y%m%d')
            date2 = datetime.strptime(date2_str, '%Y%m%d')
        except:
            print(f"  ⚠️  Could not parse dates from filename")
            continue
    else:
        # Try to match with time series
        print(f"  ⚠️  Could not extract dates, skipping")
        continue
    
    # Find matching velocity from time series
    matching_vel = df_vel[(df_vel['date1'] == date1.strftime('%Y-%m-%d')) & 
                          (df_vel['date2'] == date2.strftime('%Y-%m-%d'))]
    if matching_vel.empty:
        # Try date match
        matching_vel = df_vel[df_vel['date'] == date2.strftime('%Y-%m-%d')]
    
    glacier_velocity = matching_vel['velocity_m_per_day'].values[0] if not matching_vel.empty else np.nan
    
    print(f"  Date pair: {date1.strftime('%Y-%m-%d')} to {date2.strftime('%Y-%m-%d')}")
    print(f"  Glacier velocity: {glacier_velocity:.2f} m/day")
    
    # Load velocity map
    try:
        with rasterio.open(vel_map_file) as src:
            velocity_map = src.read(1).astype(np.float32)
            transform = src.transform
            crs = src.crs
            
            # Check for no-data values
            if src.nodata is not None:
                velocity_map[velocity_map == src.nodata] = np.nan
            elif np.isnan(velocity_map).any():
                # Already has NaN
                pass
            else:
                # Check for zeros (might indicate no-data)
                velocity_map[velocity_map == 0] = np.nan
            
            # Valid pixels (not NaN, not masked)
            valid_mask = ~np.isnan(velocity_map)
            total_pixels = velocity_map.size
            valid_pixels = np.sum(valid_mask)
            masked_pixels = total_pixels - valid_pixels
            mask_percentage = (masked_pixels / total_pixels) * 100
            
            print(f"  Total pixels: {total_pixels:,}")
            print(f"  Valid pixels: {valid_pixels:,} ({100-mask_percentage:.1f}%)")
            print(f"  Masked pixels: {masked_pixels:,} ({mask_percentage:.1f}%)")
            
            if valid_pixels < 100:
                print(f"  ⚠️  Insufficient valid pixels, skipping LOD calculation")
                continue
            
            # Identify stable bedrock (low velocity, likely outside glacier)
            # For now, use simple threshold (velocity < threshold)
            # In practice, you'd use a bedrock mask or DEM-based mask
            stable_mask = (velocity_map < STABLE_BEDROCK_THRESHOLD) & valid_mask
            
            # If not enough stable pixels, relax threshold slightly
            if np.sum(stable_mask) < 100:
                stable_mask = (velocity_map < STABLE_BEDROCK_THRESHOLD * 2) & valid_mask
            
            if np.sum(stable_mask) < 100:
                print(f"  ⚠️  Insufficient stable bedrock pixels ({np.sum(stable_mask)})")
                print(f"      Using percentiles of all low-velocity pixels")
                # Use bottom 10% of velocities as stable reference
                low_vel_percentile = np.nanpercentile(velocity_map[valid_mask], 10)
                stable_mask = (velocity_map < low_vel_percentile) & valid_mask
            
            stable_velocities = velocity_map[stable_mask]
            
            if len(stable_velocities) < 10:
                print(f"  ⚠️  Too few stable pixels ({len(stable_velocities)}), skipping")
                continue
            
            # Calculate LOD statistics
            mu_stable = np.nanmean(stable_velocities)
            sigma_stable = np.nanstd(stable_velocities)
            lod_value = mu_stable + LOD_FACTOR * sigma_stable
            
            print(f"  Stable bedrock pixels: {len(stable_velocities):,}")
            print(f"  μ (mean): {mu_stable:.4f} m/day")
            print(f"  σ (std): {sigma_stable:.4f} m/day")
            print(f"  LOD (μ + 2σ): {lod_value:.4f} m/day")
            print(f"  Glacier velocity / LOD: {glacier_velocity / lod_value:.2f}x")
            
            # Store results
            lod_results.append({
                'date1': date1.strftime('%Y-%m-%d'),
                'date2': date2.strftime('%Y-%m-%d'),
                'date': date2.strftime('%Y-%m-%d'),
                'mu_stable': float(mu_stable),
                'sigma_stable': float(sigma_stable),
                'lod_value': float(lod_value),
                'stable_pixels': int(len(stable_velocities)),
                'glacier_velocity': float(glacier_velocity),
                'velocity_lod_ratio': float(glacier_velocity / lod_value) if lod_value > 0 else np.nan
            })
            
            mask_stats.append({
                'date1': date1.strftime('%Y-%m-%d'),
                'date2': date2.strftime('%Y-%m-%d'),
                'date': date2.strftime('%Y-%m-%d'),
                'total_pixels': int(total_pixels),
                'valid_pixels': int(valid_pixels),
                'masked_pixels': int(masked_pixels),
                'mask_percentage': float(mask_percentage),
                'valid_percentage': float(100 - mask_percentage)
            })
            
            # Calculate σ_alg if we had ensemble (multiple window sizes)
            # For now, estimate from spatial variability in stable areas
            # In practice, σ_alg would come from ensemble of window sizes
            sigma_alg_map = np.full_like(velocity_map, np.nan)
            
            # Estimate σ_alg as local spatial standard deviation (7x7 window)
            from scipy.ndimage import uniform_filter, generic_filter
            
            # Simple approach: use spatial variability as proxy for algorithmic uncertainty
            # Create a local std map using 7x7 window
            kernel_size = 7
            valid_pixels_window = uniform_filter(valid_mask.astype(float), size=kernel_size)
            
            # For valid regions, compute local std
            for i in range(kernel_size//2, velocity_map.shape[0] - kernel_size//2):
                for j in range(kernel_size//2, velocity_map.shape[1] - kernel_size//2):
                    if valid_mask[i, j]:
                        window = velocity_map[i-kernel_size//2:i+kernel_size//2+1,
                                            j-kernel_size//2:j+kernel_size//2+1]
                        window_valid = window[~np.isnan(window)]
                        if len(window_valid) >= 9:  # At least half window valid
                            sigma_alg_map[i, j] = np.std(window_valid)
            
            # Store σ_alg statistics
            sigma_alg_valid = sigma_alg_map[~np.isnan(sigma_alg_map)]
            if len(sigma_alg_valid) > 0:
                sigma_alg_results.append({
                    'date1': date1.strftime('%Y-%m-%d'),
                    'date2': date2.strftime('%Y-%m-%d'),
                    'date': date2.strftime('%Y-%m-%d'),
                    'sigma_alg_mean': float(np.nanmean(sigma_alg_valid)),
                    'sigma_alg_median': float(np.nanmedian(sigma_alg_valid)),
                    'sigma_alg_std': float(np.nanstd(sigma_alg_valid)),
                    'sigma_alg_q75': float(np.nanpercentile(sigma_alg_valid, 75)),
                    'sigma_alg_q95': float(np.nanpercentile(sigma_alg_valid, 95))
                })
                
                print(f"  σ_alg statistics:")
                print(f"    Mean: {np.nanmean(sigma_alg_valid):.4f} m/day")
                print(f"    Median: {np.nanmedian(sigma_alg_valid):.4f} m/day")
                print(f"    Q75: {np.nanpercentile(sigma_alg_valid, 75):.4f} m/day")
                
                # Save σ_alg map
                sigma_alg_file = OUTPUT_DIR / f"sigma_alg_{date1.strftime('%Y%m%d')}_{date2.strftime('%Y%m%d')}.tif"
                with rasterio.open(
                    sigma_alg_file,
                    'w',
                    driver='GTiff',
                    height=sigma_alg_map.shape[0],
                    width=sigma_alg_map.shape[1],
                    count=1,
                    dtype=rasterio.float32,
                    crs=crs,
                    transform=transform,
                    compress='lzw',
                    nodata=np.nan
                ) as dst:
                    dst.write(sigma_alg_map, 1)
                    dst.update_tags(
                        date1=date1.strftime('%Y-%m-%d'),
                        date2=date2.strftime('%Y-%m-%d'),
                        description='Algorithmic uncertainty (σ_alg) from local spatial variability'
                    )
                print(f"  ✅ Saved σ_alg map: {sigma_alg_file.name}")
            
    except Exception as e:
        print(f"  ❌ Error processing {vel_map_file.name}: {e}")
        import traceback
        traceback.print_exc()

# Create summary DataFrames
df_lod = pd.DataFrame(lod_results)
df_mask = pd.DataFrame(mask_stats)
df_sigma_alg = pd.DataFrame(sigma_alg_results)

# Save results
if len(df_lod) > 0:
    df_lod = df_lod.sort_values('date')
    lod_file = OUTPUT_DIR / "lod_statistics_per_epoch.csv"
    df_lod.to_csv(lod_file, index=False)
    print(f"\n✅ LOD statistics saved: {lod_file}")

if len(df_mask) > 0:
    df_mask = df_mask.sort_values('date')
    mask_file = OUTPUT_DIR / "mask_statistics_per_epoch.csv"
    df_mask.to_csv(mask_file, index=False)
    print(f"✅ Mask statistics saved: {mask_file}")

if len(df_sigma_alg) > 0:
    df_sigma_alg = df_sigma_alg.sort_values('date')
    sigma_file = OUTPUT_DIR / "sigma_alg_statistics_per_epoch.csv"
    df_sigma_alg.to_csv(sigma_file, index=False)
    print(f"✅ σ_alg statistics saved: {sigma_file}")

# Create summary JSON
summary = {
    'lod_statistics': df_lod.to_dict('records') if len(df_lod) > 0 else [],
    'mask_statistics': df_mask.to_dict('records') if len(df_mask) > 0 else [],
    'sigma_alg_statistics': df_sigma_alg.to_dict('records') if len(df_sigma_alg) > 0 else [],
    'summary': {
        'total_epochs': len(df_lod),
        'mean_lod': float(df_lod['lod_value'].mean()) if len(df_lod) > 0 else np.nan,
        'mean_mu': float(df_lod['mu_stable'].mean()) if len(df_lod) > 0 else np.nan,
        'mean_sigma': float(df_lod['sigma_stable'].mean()) if len(df_lod) > 0 else np.nan,
        'mean_mask_percentage': float(df_mask['mask_percentage'].mean()) if len(df_mask) > 0 else np.nan,
        'mean_sigma_alg': float(df_sigma_alg['sigma_alg_mean'].mean()) if len(df_sigma_alg) > 0 else np.nan
    }
}

summary_file = OUTPUT_DIR / "uncertainty_summary.json"
with open(summary_file, 'w') as f:
    json.dump(summary, f, indent=2)
print(f"✅ Summary saved: {summary_file}")

# Create visualization
if len(df_lod) > 0 and len(df_mask) > 0:
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))
    
    # Panel (a): LOD values and glacier velocity
    ax1 = axes[0]
    dates = pd.to_datetime(df_lod['date'])
    ax1.plot(dates, df_lod['mu_stable'], 'o-', label='μ (mean)', linewidth=2, markersize=8)
    ax1.fill_between(dates, 
                     df_lod['mu_stable'] - df_lod['sigma_stable'],
                     df_lod['mu_stable'] + df_lod['sigma_stable'],
                     alpha=0.3, label='±1σ')
    ax1.plot(dates, df_lod['lod_value'], 's-', label='LOD (μ + 2σ)', linewidth=2, markersize=8, color='red')
    ax1.plot(dates, df_lod['glacier_velocity'], '^-', label='Glacier Velocity', linewidth=2, markersize=8, color='blue')
    ax1.set_ylabel('Velocity (m d⁻¹)', fontsize=12)
    ax1.set_title('(a) LOD Values and Glacier Velocity Comparison', fontsize=13, loc='left', pad=10)
    ax1.legend(loc='best', fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_facecolor('#FAFAFA')
    
    # Panel (b): Velocity / LOD ratio
    ax2 = axes[1]
    ax2.plot(dates, df_lod['velocity_lod_ratio'], 'o-', linewidth=2, markersize=8, color='green')
    ax2.axhline(y=1.0, color='red', linestyle='--', linewidth=1.5, label='LOD threshold')
    ax2.set_ylabel('Velocity / LOD', fontsize=12)
    ax2.set_title('(b) Glacier Velocity Relative to LOD', fontsize=13, loc='left', pad=10)
    ax2.legend(loc='best', fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.set_facecolor('#FAFAFA')
    
    # Panel (c): Mask percentage
    ax3 = axes[2]
    dates_mask = pd.to_datetime(df_mask['date'])
    ax3.plot(dates_mask, df_mask['mask_percentage'], 's-', linewidth=2, markersize=8, color='orange')
    ax3.set_ylabel('Masked Pixels (%)', fontsize=12)
    ax3.set_xlabel('Date', fontsize=12)
    ax3.set_title('(c) Percentage of Masked Pixels Through Time', fontsize=13, loc='left', pad=10)
    ax3.grid(True, alpha=0.3)
    ax3.set_facecolor('#FAFAFA')
    
    plt.tight_layout()
    vis_file = OUTPUT_DIR / "lod_uncertainty_analysis.png"
    plt.savefig(vis_file, dpi=300, bbox_inches='tight')
    print(f"✅ Visualization saved: {vis_file}")
    plt.close()

# Print summary table
if len(df_lod) > 0:
    print("\n" + "=" * 80)
    print("LOD STATISTICS SUMMARY")
    print("=" * 80)
    print(f"\n{'Date':<12} {'μ (m/d)':<10} {'σ (m/d)':<10} {'LOD (m/d)':<12} {'V_glacier':<12} {'V/LOD':<10} {'Mask %':<10}")
    print("-" * 80)
    for _, row in df_lod.iterrows():
        mask_pct = df_mask[df_mask['date'] == row['date']]['mask_percentage'].values
        mask_pct_str = f"{mask_pct[0]:.1f}%" if len(mask_pct) > 0 else "N/A"
        print(f"{row['date']:<12} {row['mu_stable']:<10.4f} {row['sigma_stable']:<10.4f} "
              f"{row['lod_value']:<12.4f} {row['glacier_velocity']:<12.2f} "
              f"{row['velocity_lod_ratio']:<10.2f} {mask_pct_str:<10}")
    
    print("\n" + "=" * 80)
    print(f"Mean LOD: {df_lod['lod_value'].mean():.4f} m/day")
    print(f"Mean μ: {df_lod['mu_stable'].mean():.4f} m/day")
    print(f"Mean σ: {df_lod['sigma_stable'].mean():.4f} m/day")
    if len(df_mask) > 0:
        print(f"Mean mask percentage: {df_mask['mask_percentage'].mean():.1f}%")
    print("=" * 80)

print("\n✅ Analysis complete!")

