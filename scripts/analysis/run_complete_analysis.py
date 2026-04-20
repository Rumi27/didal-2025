#!/usr/bin/env python3
"""
Master script to run complete analysis pipeline.

This script runs all analysis steps in sequence:
1. Process ERA5-Land climate derivatives
2. Process DEM topography
3. Apply change-point detection (if velocity data available)
4. Align change-points with climate events
5. Test mechanisms

Run this after:
- ERA5-Land data is downloaded correctly
- Sentinel-1 velocity data is processed and exported to CSV

Requirements:
    All dependencies from individual scripts
"""

import os
import sys
from pathlib import Path
import subprocess

# Scripts to run in order
SCRIPTS = [
    {
        'name': 'ERA5-Land Climate Derivatives',
        'script': 'process_era5_climate_derivatives.py',
        'required': True,
        'check_output': 'satellite_data/era5_land/processed/climate_derivatives_timeseries.csv'
    },
    {
        'name': 'DEM Topographic Analysis',
        'script': 'process_dem_topography.py',
        'required': True,
        'check_output': 'satellite_data/dem/processed/slope.tif'
    },
    {
        'name': 'Change-Point Detection',
        'script': 'apply_changepoint_detection.py',
        'required': False,  # Optional - needs velocity data
        'check_output': 'satellite_data/sentinel1/processed/velocity_timeseries.csv',
        'skip_if_missing': True
    },
    {
        'name': 'Change-Point Climate Alignment',
        'script': 'align_changepoints_climate.py',
        'required': False,
        'check_output': 'satellite_data/sentinel1/processed/velocity_timeseries.csv',
        'skip_if_missing': True
    },
    {
        'name': 'Mechanism Testing',
        'script': 'test_mechanism_integration.py',
        'required': True,
        'check_output': 'satellite_data/analysis/mechanism_test_results.json'
    }
]


def check_prerequisites():
    """Check if required data and packages are available."""
    print("=" * 70)
    print("Checking Prerequisites")
    print("=" * 70)
    print()
    
    issues = []
    
    # Check packages
    try:
        import ruptures
        print("✅ ruptures installed")
    except ImportError:
        print("❌ ruptures not installed")
        issues.append("pip install ruptures")
    
    try:
        import xarray
        print("✅ xarray installed")
    except ImportError:
        print("❌ xarray not installed")
        issues.append("pip install xarray")
    
    # Check data
    era5_files = list(Path("satellite_data/era5_land").glob("ERA5-Land_Didal_Glacier_2025_*.nc"))
    if era5_files:
        print(f"✅ ERA5-Land files found: {len(era5_files)}")
    else:
        print("❌ No ERA5-Land files found")
        issues.append("Download ERA5-Land data")
    
    dem_file = Path("satellite_data/SRTM1_Arc_Second_Global/n38_e070_1arc_v3.tif")
    if dem_file.exists():
        print("✅ DEM file found")
    else:
        print("❌ DEM file not found")
        issues.append("Download DEM data")
    
    velocity_file = Path("satellite_data/sentinel1/processed/velocity_timeseries.csv")
    if velocity_file.exists():
        print("✅ Velocity time series found")
    else:
        print("⚠️  Velocity time series not found (optional)")
    
    print()
    
    if issues:
        print("Issues found:")
        for issue in issues:
            print(f"  - {issue}")
        print()
        return False
    
    return True


def run_script(script_info):
    """Run a single analysis script."""
    script_name = script_info['name']
    script_file = script_info['script']
    required = script_info['required']
    check_output = script_info.get('check_output')
    skip_if_missing = script_info.get('skip_if_missing', False)
    
    print("=" * 70)
    print(f"Running: {script_name}")
    print("=" * 70)
    print()
    
    # Check if output already exists
    if check_output and Path(check_output).exists():
        print(f"✅ Output already exists: {check_output}")
        print("   Skipping...")
        print()
        return True
    
    # Check if required input is missing
    if skip_if_missing and check_output:
        if not Path(check_output).exists():
            print(f"⚠️  Required input not found: {check_output}")
            print("   Skipping this step...")
            print()
            return True
    
    # Check if script exists
    if not Path(script_file).exists():
        print(f"❌ Script not found: {script_file}")
        if required:
            return False
        else:
            print("   Skipping...")
            return True
    
    # Run script
    try:
        result = subprocess.run(
            ['python3', script_file],
            capture_output=False,  # Show output
            text=True
        )
        
        if result.returncode == 0:
            print()
            print(f"✅ {script_name} completed successfully")
            print()
            return True
        else:
            print()
            print(f"❌ {script_name} failed (exit code: {result.returncode})")
            if required:
                print("   This is a required step - fix errors and re-run")
            print()
            return not required  # Return False only if required
            
    except Exception as e:
        print(f"❌ Error running {script_file}: {e}")
        if required:
            return False
        return True


def main():
    """Main function."""
    print("=" * 70)
    print("Complete Analysis Pipeline")
    print("=" * 70)
    print()
    
    # Check prerequisites
    if not check_prerequisites():
        print("⚠️  Some prerequisites are missing")
        print("   Fix issues above and re-run")
        print()
        return False
    
    print()
    print("=" * 70)
    print("Starting Analysis Pipeline")
    print("=" * 70)
    print()
    
    # Run each script
    results = []
    
    for script_info in SCRIPTS:
        success = run_script(script_info)
        results.append((script_info['name'], success))
    
    # Summary
    print()
    print("=" * 70)
    print("Analysis Pipeline Summary")
    print("=" * 70)
    print()
    
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {name}")
    
    print()
    
    # Check if all required steps succeeded
    required_failed = [
        name for (name, success), info in zip(results, SCRIPTS)
        if not success and info['required']
    ]
    
    if required_failed:
        print("❌ Some required steps failed:")
        for name in required_failed:
            print(f"   - {name}")
        print()
        return False
    else:
        print("✅ All required steps completed!")
        print()
        print("Output files are in:")
        print("  - satellite_data/era5_land/processed/")
        print("  - satellite_data/dem/processed/")
        print("  - satellite_data/sentinel1/processed/")
        print("  - satellite_data/analysis/")
        print()
        return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

