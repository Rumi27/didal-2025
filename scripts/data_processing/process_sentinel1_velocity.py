#!/usr/bin/env python3
"""
Process Sentinel-1 SAR data for glacier velocity time series.

This script performs:
1. Sentinel-1 GRD data loading and preprocessing
2. Offset tracking / feature tracking between image pairs
3. Velocity time series extraction
4. Uncertainty quantification (LOD from stable bedrock)
5. Ensemble uncertainty (multiple window sizes)

Requirements:
    pip install rasterio numpy scipy matplotlib pandas geopandas
    # Optional but recommended:
    # pip install sarsen  # For SAR processing
    # pip install pyroSAR  # Alternative SAR processing

Output:
    - Velocity time series (CSV)
    - Velocity maps (GeoTIFF)
    - Uncertainty maps (GeoTIFF)
    - Level of Detection (LOD) from stable bedrock
    - Ensemble statistics

Note: This is a framework. Some steps may require specialized SAR processing
tools (SNAP, ISCE) or additional libraries for full implementation.
"""

import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import json
import zipfile
import shutil
from typing import Tuple, List, Dict, Optional

try:
    import rasterio
    from rasterio.transform import from_bounds
    from rasterio.warp import calculate_default_transform, reproject, Resampling
except ImportError:
    print("⚠️  rasterio not installed. Install with: pip install rasterio")
    rasterio = None

try:
    from scipy import ndimage
    from scipy.ndimage import uniform_filter, gaussian_filter
    from scipy.optimize import minimize_scalar
except ImportError:
    print("⚠️  scipy not installed. Install with: pip install scipy")
    scipy = None

import matplotlib.pyplot as plt

# Study area coordinates
GLACIER_LAT = 38.97
GLACIER_LON = 70.75
GLACIER_BBOX = {
    'west': 70.6,
    'east': 70.9,
    'south': 38.85,
    'north': 39.1
}

# Input/Output directories
INPUT_DIR = Path("satellite_data/sentinel1")
OUTPUT_DIR = Path("satellite_data/sentinel1/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Processing parameters
WINDOW_SIZES = [32, 64, 128]  # Pixels for offset tracking (multiple for ensemble)
SEARCH_RANGE = 100  # Maximum displacement to search (pixels)
STABLE_BEDROCK_THRESHOLD = 0.1  # Velocity threshold for stable bedrock (m/day)
MIN_CORRELATION = 0.3  # Minimum correlation for valid offset


def find_sentinel1_products():
    """Find all Sentinel-1 GRD products."""
    print("=" * 70)
    print("Finding Sentinel-1 Products")
    print("=" * 70)
    print()
    
    # Look for .SAFE.zip files
    zip_files = sorted(INPUT_DIR.glob("*.SAFE.zip"))
    
    if not zip_files:
        print(f"❌ No Sentinel-1 products found in {INPUT_DIR}")
        return []
    
    print(f"Found {len(zip_files)} Sentinel-1 products:")
    for f in zip_files:
        print(f"  - {f.name}")
    print()
    
    return zip_files


def extract_safe_archive(zip_file: Path, extract_dir: Path) -> Path:
    """Extract Sentinel-1 SAFE archive."""
    safe_name = zip_file.stem  # Remove .zip extension
    safe_dir = extract_dir / safe_name
    
    if safe_dir.exists():
        print(f"  Archive already extracted: {safe_name}")
        return safe_dir
    
    print(f"  Extracting: {safe_name}...")
    with zipfile.ZipFile(zip_file, 'r') as z:
        z.extractall(extract_dir)
    
    return safe_dir


def parse_sentinel1_metadata(safe_dir: Path) -> Dict:
    """Parse Sentinel-1 SAFE metadata to extract acquisition info."""
    # Look for manifest.safe or annotation files
    manifest_file = safe_dir / "manifest.safe"
    
    metadata = {
        'safe_dir': str(safe_dir),
        'product_type': 'GRD',
        'acquisition_date': None,
        'orbit_direction': None,
        'polarization': None,
        'mode': None
    }
    
    # Try to extract date from directory name
    # Format: S1A_IW_GRDH_1SDV_20250907T012223_20250907T012248_...
    dir_name = safe_dir.name
    date_match = None
    for part in dir_name.split('_'):
        if 'T' in part and len(part) == 15:
            try:
                date_match = datetime.strptime(part, '%Y%m%dT%H%M%S')
                break
            except:
                pass
    
    if date_match:
        metadata['acquisition_date'] = date_match
    
    # Try to extract other info from filename
    if 'IW' in dir_name:
        metadata['mode'] = 'IW'
    if 'VV' in dir_name:
        metadata['polarization'] = 'VV'
    elif 'VH' in dir_name:
        metadata['polarization'] = 'VH'
    if 'ASCENDING' in dir_name or 'ASC' in dir_name:
        metadata['orbit_direction'] = 'ASCENDING'
    elif 'DESCENDING' in dir_name or 'DES' in dir_name:
        metadata['orbit_direction'] = 'DESCENDING'
    
    return metadata


def load_sentinel1_image(safe_dir: Path, band: str = 'VV') -> Tuple[np.ndarray, Dict]:
    """
    Load Sentinel-1 GRD image.
    
    This is a placeholder. Full implementation requires:
    - Reading measurement files (.tiff in measurement/)
    - Applying calibration
    - Applying terrain correction
    - Converting to backscatter (dB)
    
    For now, returns a framework structure.
    """
    print(f"  Loading image from: {safe_dir.name}")
    
    # Look for measurement files
    measurement_dir = safe_dir / "measurement"
    if not measurement_dir.exists():
        # Try alternative structure
        measurement_dir = safe_dir / "GRD" / "measurement"
    
    if not measurement_dir.exists():
        print(f"    ⚠️  Measurement directory not found")
        return None, None
    
    # Find measurement file for the requested band
    tiff_files = list(measurement_dir.glob(f"*{band}*.tiff"))
    if not tiff_files:
        tiff_files = list(measurement_dir.glob(f"*.tiff"))
    
    if not tiff_files:
        print(f"    ⚠️  No measurement files found")
        return None, None
    
    # Load first available file (simplified - should handle all bands)
    if rasterio:
        try:
            with rasterio.open(tiff_files[0]) as src:
                data = src.read(1)  # Read first band
                transform = src.transform
                crs = src.crs
                metadata = {
                    'transform': transform,
                    'crs': crs,
                    'width': src.width,
                    'height': src.height,
                    'bounds': src.bounds
                }
                print(f"    ✅ Loaded: {data.shape}, CRS: {crs}")
                return data, metadata
        except Exception as e:
            print(f"    ⚠️  Error loading: {e}")
            return None, None
    else:
        print(f"    ⚠️  rasterio not available")
        return None, None


def offset_tracking(image1: np.ndarray, image2: np.ndarray,
                   window_size: int, search_range: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Perform offset tracking between two images.
    
    Uses normalized cross-correlation (NCC) to find displacement.
    
    Returns:
        - dx: displacement in x direction (pixels)
        - dy: displacement in y direction (pixels)
        - correlation: correlation coefficient map
    """
    print(f"    Performing offset tracking (window={window_size}px)...")
    
    h, w = image1.shape
    dx = np.full((h, w), np.nan)
    dy = np.full((h, w), np.nan)
    correlation = np.full((h, w), np.nan)
    
    half_window = window_size // 2
    step = window_size // 2  # 50% overlap
    
    for y in range(half_window, h - half_window, step):
        for x in range(half_window, w - half_window, step):
            # Extract template from image1
            y1 = max(0, y - half_window)
            y2 = min(h, y + half_window)
            x1 = max(0, x - half_window)
            x2 = min(w, x + half_window)
            
            template = image1[y1:y2, x1:x2]
            
            if np.std(template) < 1e-6:  # Skip uniform regions
                continue
            
            # Search in image2
            best_corr = -1
            best_dx = 0
            best_dy = 0
            
            for dy_search in range(-search_range, search_range + 1, 2):
                for dx_search in range(-search_range, search_range + 1, 2):
                    y2_start = max(0, y1 + dy_search)
                    y2_end = min(h, y2 + dy_search)
                    x2_start = max(0, x1 + dx_search)
                    x2_end = min(w, x2 + dx_search)
                    
                    if (y2_end - y2_start != template.shape[0] or
                        x2_end - x2_start != template.shape[1]):
                        continue
                    
                    search_patch = image2[y2_start:y2_end, x2_start:x2_end]
                    
                    if np.std(search_patch) < 1e-6:
                        continue
                    
                    # Normalized cross-correlation
                    corr = np.corrcoef(template.flatten(), search_patch.flatten())[0, 1]
                    
                    if not np.isnan(corr) and corr > best_corr:
                        best_corr = corr
                        best_dx = dx_search
                        best_dy = dy_search
            
            # Store results
            if best_corr >= MIN_CORRELATION:
                dx[y, x] = best_dx
                dy[y, x] = best_dy
                correlation[y, x] = best_corr
    
    # Interpolate to fill gaps
    if scipy:
        dx = ndimage.gaussian_filter(dx, sigma=window_size/4)
        dy = ndimage.gaussian_filter(dy, sigma=window_size/4)
    
    print(f"      Valid offsets: {np.sum(~np.isnan(dx))} / {h * w}")
    print(f"      Mean correlation: {np.nanmean(correlation):.3f}")
    
    return dx, dy, correlation


def compute_velocity(dx: np.ndarray, dy: np.ndarray, pixel_size: float,
                   time_delta_days: float) -> np.ndarray:
    """
    Compute velocity from displacement.
    
    Args:
        dx, dy: Displacement in pixels
        pixel_size: Pixel size in meters
        time_delta_days: Time difference in days
    
    Returns:
        Velocity magnitude in m/day
    """
    # Convert pixel displacement to meters
    dx_m = dx * pixel_size
    dy_m = dy * pixel_size
    
    # Compute velocity
    velocity = np.sqrt(dx_m**2 + dy_m**2) / time_delta_days
    
    return velocity


def compute_lod_from_stable_bedrock(velocity_map: np.ndarray,
                                   correlation_map: np.ndarray,
                                   threshold: float = STABLE_BEDROCK_THRESHOLD) -> float:
    """
    Compute Level of Detection (LOD) from stable bedrock areas.
    
    Stable bedrock is identified as areas with:
    - Low velocity (< threshold m/day)
    - High correlation (> MIN_CORRELATION)
    """
    print("    Computing LOD from stable bedrock...")
    
    # Identify stable bedrock
    stable_mask = (velocity_map < threshold) & (correlation_map > MIN_CORRELATION)
    
    if np.sum(stable_mask) < 100:
        print(f"      ⚠️  Insufficient stable bedrock pixels ({np.sum(stable_mask)})")
        return np.nan
    
    # Compute standard deviation of velocity in stable areas
    stable_velocities = velocity_map[stable_mask]
    lod = np.std(stable_velocities)
    
    print(f"      Stable bedrock pixels: {np.sum(stable_mask)}")
    print(f"      LOD: {lod:.4f} m/day")
    
    return lod


def process_sentinel1_pairs(products: List[Path]) -> pd.DataFrame:
    """
    Process all Sentinel-1 image pairs for velocity time series.
    """
    print("=" * 70)
    print("Processing Sentinel-1 Image Pairs")
    print("=" * 70)
    print()
    
    # Extract and parse all products
    extract_dir = OUTPUT_DIR / "extracted"
    extract_dir.mkdir(exist_ok=True)
    
    product_metadata = []
    for zip_file in products:
        safe_dir = extract_safe_archive(zip_file, extract_dir)
        metadata = parse_sentinel1_metadata(safe_dir)
        product_metadata.append(metadata)
    
    # Sort by acquisition date
    product_metadata.sort(key=lambda x: x['acquisition_date'] if x['acquisition_date'] else datetime.min)
    
    print(f"Processing {len(product_metadata)} products")
    print(f"Date range: {product_metadata[0]['acquisition_date']} to {product_metadata[-1]['acquisition_date']}")
    print()
    
    # Process consecutive pairs
    velocity_results = []
    
    for i in range(len(product_metadata) - 1):
        meta1 = product_metadata[i]
        meta2 = product_metadata[i + 1]
        
        date1 = meta1['acquisition_date']
        date2 = meta2['acquisition_date']
        
        if not date1 or not date2:
            continue
        
        time_delta = (date2 - date1).total_seconds() / 86400  # days
        
        print(f"Processing pair {i+1}/{len(product_metadata)-1}:")
        print(f"  {date1.strftime('%Y-%m-%d')} → {date2.strftime('%Y-%m-%d')} ({time_delta:.1f} days)")
        
        # Load images
        safe_dir1 = Path(meta1['safe_dir'])
        safe_dir2 = Path(meta2['safe_dir'])
        
        image1, metadata1 = load_sentinel1_image(safe_dir1)
        image2, metadata2 = load_sentinel1_image(safe_dir2)
        
        if image1 is None or image2 is None:
            print(f"  ⚠️  Skipping pair (failed to load images)")
            continue
        
        # Get pixel size (assume square pixels)
        pixel_size = abs(metadata1['transform'][0])  # meters
        
        # Process with multiple window sizes (ensemble)
        ensemble_results = []
        
        for window_size in WINDOW_SIZES:
            print(f"  Window size: {window_size}px")
            
            # Offset tracking
            dx, dy, correlation = offset_tracking(image1, image2, window_size, SEARCH_RANGE)
            
            # Compute velocity
            velocity = compute_velocity(dx, dy, pixel_size, time_delta)
            
            # Compute LOD
            lod = compute_lod_from_stable_bedrock(velocity, correlation)
            
            ensemble_results.append({
                'window_size': window_size,
                'velocity': velocity,
                'dx': dx,
                'dy': dy,
                'correlation': correlation,
                'lod': lod
            })
        
        # Ensemble mean velocity
        velocities = [r['velocity'] for r in ensemble_results]
        mean_velocity = np.nanmean(velocities, axis=0)
        std_velocity = np.nanstd(velocities, axis=0)
        
        # Mean LOD
        lods = [r['lod'] for r in ensemble_results if not np.isnan(r['lod'])]
        mean_lod = np.nanmean(lods) if lods else np.nan
        
        # Store results
        result = {
            'date1': date1,
            'date2': date2,
            'time_delta_days': time_delta,
            'mean_velocity': mean_velocity,
            'std_velocity': std_velocity,
            'lod': mean_lod,
            'ensemble_results': ensemble_results
        }
        
        velocity_results.append(result)
        
        # Save intermediate results
        output_file = OUTPUT_DIR / f"velocity_{date1.strftime('%Y%m%d')}_{date2.strftime('%Y%m%d')}.tif"
        if rasterio and metadata1:
            with rasterio.open(
                output_file,
                'w',
                driver='GTiff',
                height=mean_velocity.shape[0],
                width=mean_velocity.shape[1],
                count=1,
                dtype=rasterio.float32,
                crs=metadata1['crs'],
                transform=metadata1['transform'],
                compress='lzw'
            ) as dst:
                dst.write(mean_velocity, 1)
            print(f"  ✅ Saved: {output_file.name}")
        
        print()
    
    # Create time series DataFrame
    print("Creating velocity time series...")
    
    ts_data = []
    for result in velocity_results:
        # Extract velocity at glacier location (simplified - should use proper geocoding)
        # For now, use mean velocity over valid pixels
        valid_vel = result['mean_velocity'][~np.isnan(result['mean_velocity'])]
        if len(valid_vel) > 0:
            mean_vel = np.nanmean(valid_vel)
            std_vel = np.nanstd(valid_vel)
        else:
            mean_vel = np.nan
            std_vel = np.nan
        
        ts_data.append({
            'date': result['date2'],
            'time_delta_days': result['time_delta_days'],
            'velocity_m_per_day': mean_vel,
            'velocity_std': std_vel,
            'lod_m_per_day': result['lod']
        })
    
    df = pd.DataFrame(ts_data)
    df = df.sort_values('date')
    
    return df


def save_results(df: pd.DataFrame, output_dir: Path):
    """Save velocity time series and summary statistics."""
    print("=" * 70)
    print("Saving Results")
    print("=" * 70)
    print()
    
    # Save time series CSV
    csv_file = output_dir / "velocity_timeseries.csv"
    df.to_csv(csv_file, index=False)
    print(f"✅ Time series saved: {csv_file}")
    
    # Save summary statistics
    summary_file = output_dir / "velocity_summary.txt"
    with open(summary_file, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("Sentinel-1 Velocity Time Series Summary\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Total pairs processed: {len(df)}\n")
        f.write(f"Date range: {df['date'].min()} to {df['date'].max()}\n\n")
        
        f.write("Velocity Statistics:\n")
        f.write(f"  Mean: {df['velocity_m_per_day'].mean():.4f} m/day\n")
        f.write(f"  Min: {df['velocity_m_per_day'].min():.4f} m/day\n")
        f.write(f"  Max: {df['velocity_m_per_day'].max():.4f} m/day\n")
        f.write(f"  Std: {df['velocity_m_per_day'].std():.4f} m/day\n\n")
        
        f.write("LOD Statistics:\n")
        valid_lod = df['lod_m_per_day'].dropna()
        if len(valid_lod) > 0:
            f.write(f"  Mean LOD: {valid_lod.mean():.4f} m/day\n")
            f.write(f"  Min LOD: {valid_lod.min():.4f} m/day\n")
            f.write(f"  Max LOD: {valid_lod.max():.4f} m/day\n")
    
    print(f"✅ Summary saved: {summary_file}")
    print()
    
    return csv_file, summary_file


def create_visualizations(df: pd.DataFrame, output_dir: Path):
    """Create visualization plots."""
    print("Creating visualizations...")
    print()
    
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))
    
    # Velocity time series
    ax = axes[0]
    ax.errorbar(df['date'], df['velocity_m_per_day'],
                yerr=df['velocity_std'], fmt='o-', capsize=3, alpha=0.7)
    ax.set_ylabel('Velocity (m/day)')
    ax.set_title('Glacier Velocity Time Series')
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    
    # LOD time series
    ax = axes[1]
    valid_lod = df[df['lod_m_per_day'].notna()]
    if len(valid_lod) > 0:
        ax.plot(valid_lod['date'], valid_lod['lod_m_per_day'], 's-', color='orange', alpha=0.7)
        ax.set_ylabel('Level of Detection (m/day)')
        ax.set_xlabel('Date')
        ax.set_title('Uncertainty (LOD) Time Series')
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    plot_file = output_dir / "velocity_timeseries_plot.png"
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"✅ Plot saved: {plot_file}")
    plt.close()
    
    return plot_file


def main():
    """Main processing function."""
    print("=" * 70)
    print("Sentinel-1 Velocity Processing")
    print("=" * 70)
    print()
    
    # Find products
    products = find_sentinel1_products()
    if not products:
        print("❌ No Sentinel-1 products found. Please download data first.")
        return False
    
    # Process pairs
    df = process_sentinel1_pairs(products)
    
    if df.empty:
        print("❌ No velocity data extracted")
        return False
    
    # Save results
    csv_file, summary_file = save_results(df, OUTPUT_DIR)
    
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
    print("  1. Review velocity time series")
    print("  2. Apply PELT algorithm for change-point detection")
    print("  3. Align with climate derivatives for mechanism testing")
    print()
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

