#!/usr/bin/env python3
"""
Process ERA5-Land climate data and compute climate derivatives.

Computes:
- PDD (Positive Degree Days)
- SWE metrics (SWE_max, SWE_max date, days to SWE_0)
- MLT (Melt-rate proxy)
- ROS (Rain-on-Snow potential)

Study Area: 38.97°N, 70.75°E
Period: January 1 - December 31, 2025

Requirements:
    pip install xarray netcdf4 numpy pandas

Output:
    - Climate derivatives time series (CSV)
    - Summary statistics
    - Visualization plots
"""

import os
import sys
import numpy as np
import pandas as pd
import xarray as xr
from pathlib import Path
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import zipfile
import tempfile
import shutil

# Study area coordinates
GLACIER_LAT = 38.97
GLACIER_LON = 70.75

# Input/Output directories
INPUT_DIR = Path("satellite_data/era5_land")
OUTPUT_DIR = Path("satellite_data/era5_land/processed")
OUTPUT_DIR.mkdir(exist_ok=True)

def extract_netcdf_from_zip(zip_path, extract_dir):
    """Extract NetCDF file from ZIP archive."""
    with zipfile.ZipFile(zip_path, 'r') as z:
        files = z.namelist()
        # Find .nc file in the archive
        nc_files = [f for f in files if f.endswith('.nc')]
        if not nc_files:
            raise ValueError(f"No .nc file found in {zip_path}")
        
        # Extract the first .nc file
        nc_file = nc_files[0]
        z.extract(nc_file, extract_dir)
        return extract_dir / nc_file

def load_era5_monthly_files():
    """Load all monthly ERA5-Land NetCDF files."""
    print("=" * 70)
    print("Loading ERA5-Land Monthly Files")
    print("=" * 70)
    print()
    
    monthly_files = sorted(INPUT_DIR.glob("ERA5-Land_Didal_Glacier_2025_*.nc"))
    
    if not monthly_files:
        print(f"❌ No ERA5-Land files found in {INPUT_DIR}")
        return None
    
    print(f"Found {len(monthly_files)} monthly files")
    print()
    
    # Create temporary extraction directory
    extract_dir = INPUT_DIR / "extracted"
    extract_dir.mkdir(exist_ok=True)
    
    # Load and concatenate
    datasets = []
    extracted_files = []
    
    for i, f in enumerate(monthly_files):
        print(f"Processing: {f.name}")
        try:
            # Check if it's a ZIP file
            if zipfile.is_zipfile(f):
                # Extract NetCDF from ZIP - use unique filename
                month_label = f.name.split('_')[-1].replace('.nc', '')
                
                with zipfile.ZipFile(f, 'r') as z:
                    nc_files = [fname for fname in z.namelist() if fname.endswith('.nc')]
                    if nc_files:
                        # Use unique filename for extraction to avoid overwriting
                        unique_nc_name = f"data_{month_label}_{nc_files[0].split('/')[-1]}"
                        nc_file = extract_dir / unique_nc_name
                        
                        # Extract if not exists
                        if not nc_file.exists():
                            with z.open(nc_files[0]) as source:
                                with open(nc_file, 'wb') as target:
                                    target.write(source.read())
                        
                        extracted_files.append(nc_file)
                        ds = xr.open_dataset(nc_file, engine='netcdf4')
            else:
                # Direct NetCDF file
                ds = xr.open_dataset(f, engine='netcdf4')
            
            # Check time dimension and verify before loading
            time_dim = 'valid_time' if 'valid_time' in ds.dims else 'time'
            times_preview = pd.to_datetime(ds[time_dim].values[:5]) if time_dim in ds.dims else []
            
            # Load into memory to avoid HDF errors during concatenation
            ds = ds.load()
            
            # Verify after loading
            times_loaded = pd.to_datetime(ds[time_dim].values)
            actual_months = sorted(set([t.month for t in times_loaded]))
            time_steps = len(ds[time_dim])
            
            datasets.append(ds)
            print(f"  ✅ Loaded successfully ({time_steps} time steps, months: {actual_months})")
        except Exception as e:
            print(f"  ⚠️  Error loading {f.name}: {e}")
            import traceback
            traceback.print_exc()
    
    if not datasets:
        print("❌ No datasets loaded successfully")
        return None
    
    # Concatenate along time dimension
    print()
    print("Concatenating monthly files...")
    # Determine time dimension name
    time_dim = 'valid_time' if 'valid_time' in datasets[0].dims else 'time'
    
    # Check for overlapping times before concatenation
    print("  Checking for time overlaps...")
    all_time_values = []
    for i, ds in enumerate(datasets):
        times = pd.to_datetime(ds[time_dim].values)
        all_time_values.extend(times)
        print(f"    Dataset {i+1}: {times[0]} to {times[-1]} ({len(times)} steps)")
    
    # Check for duplicates in raw time list
    unique_times_raw = len(set(all_time_values))
    print(f"  Total time values: {len(all_time_values)}, Unique: {unique_times_raw}")
    
    try:
        # Use concat - let it handle duplicates naturally
        combined = xr.concat(datasets, dim=time_dim, combine_attrs='drop_conflicts')
        combined = combined.sortby(time_dim)
        
        # Remove duplicate times - use pandas to handle datetime properly
        combined_times_pd = pd.to_datetime(combined[time_dim].values)
        _, unique_idx = np.unique(combined_times_pd, return_index=True)
        
        if len(unique_idx) < len(combined[time_dim]):
            print(f"  Removing {len(combined[time_dim]) - len(unique_idx)} duplicate time steps...")
            combined = combined.isel({time_dim: np.sort(unique_idx)})
        
    except Exception as e:
        print(f"⚠️  Error concatenating: {e}")
        print("Trying alternative method: combining by coordinates...")
        import traceback
        traceback.print_exc()
        # Alternative: use combine_by_coords
        try:
            combined = xr.combine_by_coords(datasets, combine_attrs='drop_conflicts')
            combined = combined.sortby(time_dim)
            
            # Remove duplicates
            combined_times_pd = pd.to_datetime(combined[time_dim].values)
            _, unique_idx = np.unique(combined_times_pd, return_index=True)
            if len(unique_idx) < len(combined[time_dim]):
                combined = combined.isel({time_dim: np.sort(unique_idx)})
        except Exception as e2:
            print(f"⚠️  Alternative method also failed: {e2}")
            raise
    
    # Verify final dataset
    final_times = pd.to_datetime(combined[time_dim].values)
    unique_months = sorted(set([t.month for t in final_times]))
    unique_years = sorted(set([t.year for t in final_times]))
    
    print(f"✅ Loaded data: {len(combined[time_dim])} time steps")
    print(f"   Time range: {combined[time_dim].min().values} to {combined[time_dim].max().values}")
    print(f"   Contains months: {unique_months}")
    print(f"   Contains years: {unique_years}")
    
    # Verify we have all months
    expected_months = len(monthly_files)
    if len(unique_months) == expected_months and unique_months == list(range(1, expected_months + 1)):
        print(f"   ✅ All {expected_months} months present!")
    else:
        print(f"   ⚠️  Expected {expected_months} months, got {len(unique_months)}")
    print()
    
    # Clean up extracted files (optional - comment out if you want to keep them)
    # for f in extracted_files:
    #     f.unlink()
    # extract_dir.rmdir()
    
    return combined

def extract_grid_cell(ds, lat_target, lon_target):
    """Extract time series for grid cell closest to target coordinates."""
    print("=" * 70)
    print("Extracting Grid Cell Time Series")
    print("=" * 70)
    print()
    print(f"Target location: {lat_target}°N, {lon_target}°E")
    
    # Find closest grid cell
    lat_diff = np.abs(ds.latitude.values - lat_target)
    lon_diff = np.abs(ds.longitude.values - lon_target)
    
    lat_idx = np.argmin(lat_diff)
    lon_idx = np.argmin(lon_diff)
    
    closest_lat = ds.latitude.values[lat_idx]
    closest_lon = ds.longitude.values[lon_idx]
    
    print(f"Closest grid cell: {closest_lat:.4f}°N, {closest_lon:.4f}°E")
    print(f"   Distance: ~{np.sqrt((closest_lat-lat_target)**2 + (closest_lon-lon_target)**2)*111:.1f} km")
    print()
    
    # Extract time series
    ts = ds.isel(latitude=lat_idx, longitude=lon_idx)
    
    return ts, closest_lat, closest_lon

def compute_pdd(temperature_daily):
    """Compute Positive Degree Days (PDD) from daily mean temperature."""
    # PDD = sum of max(T_daily, 0) over days
    pdd = np.maximum(temperature_daily, 0).cumsum()
    return pdd

def compute_swe_metrics(swe, time_dim='time'):
    """Compute SWE metrics: SWE_max, SWE_max date, days to SWE_0."""
    swe_max = swe.max().values
    swe_max_idx = swe.argmax().values
    swe_max_date = swe[time_dim].isel({time_dim: swe_max_idx}).values
    
    # Find when SWE reaches 0 after maximum
    swe_after_max = swe.isel({time_dim: slice(swe_max_idx, None)})
    swe_zero_idx = np.where(swe_after_max.values <= 0.1)[0]  # 0.1 mm threshold
    
    if len(swe_zero_idx) > 0:
        swe_zero_date = swe_after_max[time_dim].isel({time_dim: swe_zero_idx[0]}).values
        days_to_zero = (pd.to_datetime(swe_zero_date) - pd.to_datetime(swe_max_date)).days
    else:
        swe_zero_date = None
        days_to_zero = None
    
    return {
        'swe_max': swe_max,
        'swe_max_date': pd.to_datetime(swe_max_date),
        'swe_zero_date': pd.to_datetime(swe_zero_date) if swe_zero_date is not None else None,
        'days_to_swe_zero': days_to_zero
    }

def compute_mlt(swe_metrics):
    """Compute Melt-rate proxy (MLT)."""
    if swe_metrics['days_to_swe_zero'] is not None and swe_metrics['days_to_swe_zero'] > 0:
        mlt = swe_metrics['swe_max'] / swe_metrics['days_to_swe_zero']
    else:
        mlt = None
    return mlt

def compute_ros(precipitation, temperature, swe):
    """Compute Rain-on-Snow potential (ROS)."""
    # ROS = P × I(T > 0.5°C) × I(Snow > 0)
    # Indicator functions
    temp_above_threshold = (temperature > 0.5).astype(float)
    snow_present = (swe > 0.1).astype(float)  # 0.1 mm threshold
    
    ros = precipitation * temp_above_threshold * snow_present
    return ros

def compute_daily_aggregates(df_raw):
    """Aggregate hourly data to daily values and fix accumulated precipitation."""
    df_raw = df_raw.sort_values('datetime').copy()
    df_raw['date'] = df_raw['datetime'].dt.floor('D')

    agg_map = {
        'temperature_C': 'mean',
    }
    if 'swe_mm' in df_raw.columns:
        agg_map['swe_mm'] = 'mean'

    daily = df_raw.groupby('date', sort=True).agg(agg_map)

    if 'precipitation_mm' in df_raw.columns:
        # ERA5-Land total_precipitation is accumulated since 00:00.
        # Use the final value of each day as the daily total.
        daily['precipitation_mm'] = (
            df_raw.groupby('date', sort=True)['precipitation_mm'].last()
        )

    daily = daily.reset_index().rename(columns={'date': 'datetime'})
    daily['datetime'] = pd.to_datetime(daily['datetime'])
    return daily

def compute_swe_metrics_from_df(df_daily):
    """Compute SWE metrics from daily SWE time series."""
    swe_series = df_daily['swe_mm']
    swe_max = swe_series.max()
    swe_max_idx = swe_series.idxmax()
    swe_max_date = df_daily.loc[swe_max_idx, 'datetime']

    swe_after_max = df_daily.loc[swe_max_idx:]
    swe_zero = swe_after_max[swe_after_max['swe_mm'] <= 0.1]

    if len(swe_zero) > 0:
        swe_zero_date = swe_zero.iloc[0]['datetime']
        days_to_zero = (swe_zero_date - swe_max_date).days
    else:
        swe_zero_date = None
        days_to_zero = None

    return {
        'swe_max': float(swe_max),
        'swe_max_date': pd.to_datetime(swe_max_date),
        'swe_zero_date': pd.to_datetime(swe_zero_date) if swe_zero_date is not None else None,
        'days_to_swe_zero': days_to_zero
    }

def process_climate_derivatives(ts):
    """Process ERA5-Land time series and compute all climate derivatives."""
    print("=" * 70)
    print("Computing Climate Derivatives")
    print("=" * 70)
    print()
    
    # Extract variables
    # Note: Variable names may vary - adjust based on actual file structure
    # Common names: 't2m' (2m temperature), 'tp' (total precipitation), 'sd' (snow depth)
    
    # Try to find temperature variable
    temp_vars = ['t2m', 'temperature', '2m_temperature', 'T2M']
    temp_var = None
    for v in temp_vars:
        if v in ts.data_vars:
            temp_var = v
            break
    
    if temp_var is None:
        print("⚠️  Available variables:", list(ts.data_vars))
        print("❌ Temperature variable not found")
        return None
    
    # Try to find precipitation variable
    precip_vars = ['tp', 'precipitation', 'total_precipitation', 'TP']
    precip_var = None
    for v in precip_vars:
        if v in ts.data_vars:
            precip_var = v
            break
    
    # Try to find SWE variable
    swe_vars = ['sd', 'swe', 'snow_depth_water_equivalent', 'SD']
    swe_var = None
    for v in swe_vars:
        if v in ts.data_vars:
            swe_var = v
            break
    
    print(f"Using variables:")
    print(f"  Temperature: {temp_var}")
    print(f"  Precipitation: {precip_var if precip_var else 'NOT FOUND'}")
    print(f"  SWE: {swe_var if swe_var else 'NOT FOUND'}")
    print()
    
    # Extract time series
    # Determine time dimension name
    time_dim = 'valid_time' if 'valid_time' in ts.dims else 'time'
    time = pd.to_datetime(ts[time_dim].values)
    temperature = ts[temp_var].values - 273.15  # Convert K to °C
    
    if precip_var:
        precipitation = ts[precip_var].values * 1000  # Convert m to mm
    else:
        precipitation = None
        print("⚠️  Precipitation not available")
    
    if swe_var:
        swe = ts[swe_var].values * 1000  # Convert m to mm (if needed)
    else:
        swe = None
        print("⚠️  SWE not available")
    
    # Build raw DataFrame
    df_raw = pd.DataFrame({
        'datetime': time,
        'temperature_C': temperature,
    })

    if precipitation is not None:
        df_raw['precipitation_mm'] = precipitation

    if swe is not None:
        df_raw['swe_mm'] = swe

    # Aggregate to daily and fix precipitation accumulation
    df = compute_daily_aggregates(df_raw)

    # Compute PDD from daily mean temperature
    print("Computing PDD (Positive Degree Days)...")
    df['pdd'] = compute_pdd(df['temperature_C'].values)

    # Compute SWE metrics
    if swe is not None:
        print("Computing SWE metrics...")
        swe_metrics = compute_swe_metrics_from_df(df)
        print(f"  SWE_max: {swe_metrics['swe_max']:.1f} mm")
        print(f"  SWE_max date: {swe_metrics['swe_max_date']}")
        if swe_metrics['days_to_swe_zero']:
            print(f"  Days to SWE_0: {swe_metrics['days_to_swe_zero']} days")

        # Compute MLT
        print("Computing MLT (Melt-rate proxy)...")
        mlt = compute_mlt(swe_metrics)
        if mlt:
            print(f"  MLT: {mlt:.2f} mm/day")

        # Store metrics
        df['swe_max'] = swe_metrics['swe_max']
        df['swe_max_date'] = swe_metrics['swe_max_date']
    else:
        swe_metrics = None
        mlt = None

    # Compute ROS from daily values
    if 'precipitation_mm' in df.columns and 'swe_mm' in df.columns:
        print("Computing ROS (Rain-on-Snow potential)...")
        df['ros'] = compute_ros(
            df['precipitation_mm'].values,
            df['temperature_C'].values,
            df['swe_mm'].values
        )
        ros_events = df[df['ros'] > 0.1]  # Events with >0.1 mm ROS
        print(f"  ROS events: {len(ros_events)} days")
        if len(ros_events) > 0:
            print(f"  Max ROS: {df['ros'].max():.2f} mm")
    else:
        df['ros'] = 0
        print("⚠️  ROS not computed (missing precipitation or SWE)")
    
    print()
    print("=" * 70)
    print("✅ Climate Derivatives Computed")
    print("=" * 70)
    print()
    
    return df, swe_metrics, mlt

def save_results(df, swe_metrics, mlt, output_dir):
    """Save processed results to files."""
    print("Saving results...")
    print()
    
    # Save time series CSV
    csv_file = output_dir / "climate_derivatives_timeseries.csv"
    df.to_csv(csv_file, index=False)
    print(f"✅ Time series saved: {csv_file}")
    
    # Save summary statistics
    summary_file = output_dir / "climate_derivatives_summary.txt"
    with open(summary_file, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("ERA5-Land Climate Derivatives Summary\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Location: {GLACIER_LAT}°N, {GLACIER_LON}°E\n")
        f.write(f"Period: {df['datetime'].min()} to {df['datetime'].max()}\n")
        f.write(f"Total time steps: {len(df)}\n\n")
        
        f.write("Temperature Statistics:\n")
        f.write(f"  Mean: {df['temperature_C'].mean():.2f} °C\n")
        f.write(f"  Min: {df['temperature_C'].min():.2f} °C\n")
        f.write(f"  Max: {df['temperature_C'].max():.2f} °C\n\n")
        
        f.write("PDD (Positive Degree Days):\n")
        f.write(f"  Final cumulative PDD: {df['pdd'].iloc[-1]:.1f} °C·days\n")
        f.write(f"  Mean daily PDD: {df['pdd'].iloc[-1] / len(df):.2f} °C·days/day\n\n")
        
        if swe_metrics:
            f.write("SWE Metrics:\n")
            f.write(f"  SWE_max: {swe_metrics['swe_max']:.1f} mm\n")
            f.write(f"  SWE_max date: {swe_metrics['swe_max_date']}\n")
            if swe_metrics['days_to_swe_zero']:
                f.write(f"  Days to SWE_0: {swe_metrics['days_to_swe_zero']} days\n")
            f.write("\n")
        
        if mlt:
            f.write("MLT (Melt-rate proxy):\n")
            f.write(f"  MLT: {mlt:.2f} mm/day\n\n")
        
        if 'ros' in df.columns:
            f.write("ROS (Rain-on-Snow):\n")
            f.write(f"  Total ROS events: {len(df[df['ros'] > 0.1])}\n")
            f.write(f"  Max ROS: {df['ros'].max():.2f} mm\n")
            f.write(f"  Total ROS: {df['ros'].sum():.2f} mm\n")
    
    print(f"✅ Summary saved: {summary_file}")
    print()
    
    return csv_file, summary_file

def create_visualizations(df, output_dir):
    """Create visualization plots of climate derivatives."""
    print("Creating visualizations...")
    print()
    
    fig, axes = plt.subplots(4, 1, figsize=(12, 10))
    
    # Temperature and PDD
    ax = axes[0]
    ax2 = ax.twinx()
    ax.plot(df['datetime'], df['temperature_C'], 'b-', alpha=0.5, label='Temperature')
    ax2.plot(df['datetime'], df['pdd'], 'r-', label='Cumulative PDD')
    ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax.set_ylabel('Temperature (°C)', color='b')
    ax2.set_ylabel('Cumulative PDD (°C·days)', color='r')
    ax.set_title('Temperature and Positive Degree Days (PDD)')
    ax.legend(loc='upper left')
    ax2.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    
    bar_width = timedelta(days=1) if len(df) <= 370 else timedelta(hours=1)

    # Precipitation
    if 'precipitation_mm' in df.columns:
        ax = axes[1]
        ax.bar(df['datetime'], df['precipitation_mm'], width=bar_width, alpha=0.6, color='blue')
        ax.set_ylabel('Precipitation (mm)')
        ax.set_title('Total Precipitation')
        ax.grid(True, alpha=0.3)
    
    # SWE
    if 'swe_mm' in df.columns:
        ax = axes[2]
        ax.plot(df['datetime'], df['swe_mm'], 'g-', linewidth=2)
        ax.set_ylabel('SWE (mm)')
        ax.set_title('Snow Water Equivalent (SWE)')
        ax.grid(True, alpha=0.3)
    
    # ROS
    if 'ros' in df.columns:
        ax = axes[3]
        ax.bar(df['datetime'], df['ros'], width=bar_width, alpha=0.6, color='orange')
        ax.set_ylabel('ROS (mm)')
        ax.set_xlabel('Date')
        ax.set_title('Rain-on-Snow Potential (ROS)')
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    plot_file = output_dir / "climate_derivatives_plot.png"
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"✅ Plot saved: {plot_file}")
    plt.close()
    
    return plot_file

def main():
    """Main processing function."""
    print("=" * 70)
    print("ERA5-Land Climate Derivatives Processing")
    print("=" * 70)
    print()
    
    # Load data
    ds = load_era5_monthly_files()
    if ds is None:
        return False
    
    # Extract grid cell
    ts, closest_lat, closest_lon = extract_grid_cell(ds, GLACIER_LAT, GLACIER_LON)
    
    # Compute derivatives
    df, swe_metrics, mlt = process_climate_derivatives(ts)
    if df is None:
        return False
    
    # Save results
    csv_file, summary_file = save_results(df, swe_metrics, mlt, OUTPUT_DIR)
    
    # Create visualizations
    plot_file = create_visualizations(df, OUTPUT_DIR)
    
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
    print("  1. Review climate derivatives time series")
    print("  2. Identify ROS events and PDD buildup patterns")
    print("  3. Align with velocity time series (once available)")
    print("  4. Test mechanisms H2 and H3 (hydrological switching)")
    print()
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
