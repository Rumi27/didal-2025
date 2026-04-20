#!/usr/bin/env python3
"""
Process DEM (SRTM) for topographic analysis.

Computes:
- Slope
- Aspect
- Hillshade
- Along-flowline profiles
- Topographic metrics for mechanism testing

Requirements:
    pip install rasterio numpy matplotlib scipy

Output:
    - Slope raster
    - Aspect raster
    - Hillshade raster
    - Flowline profiles
    - Topographic statistics
"""

import os
import sys
import numpy as np
import rasterio
from rasterio import transform
from rasterio.features import shapes
from rasterio.plot import show
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import ndimage
import json

# Study area coordinates
GLACIER_LAT = 38.97
GLACIER_LON = 70.75

# Input/Output directories
INPUT_DIR = Path("satellite_data")
DEM_DIR = INPUT_DIR / "SRTM1_Arc_Second_Global"
OUTPUT_DIR = Path("satellite_data/dem/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def find_dem_file():
    """Find the DEM file covering the glacier."""
    print("=" * 70)
    print("Finding DEM File")
    print("=" * 70)
    print()
    
    # Look for .tif or .hgt files
    dem_files = list(DEM_DIR.glob("*.tif")) + list(DEM_DIR.glob("*.hgt"))
    
    if not dem_files:
        # Also check in dem/ directory
        alt_dem_dir = INPUT_DIR / "dem"
        if alt_dem_dir.exists():
            dem_files = list(alt_dem_dir.glob("*.tif")) + list(alt_dem_dir.glob("*.hgt"))
    
    if not dem_files:
        print(f"❌ No DEM files found in {DEM_DIR} or {INPUT_DIR / 'dem'}")
        return None
    
    print(f"Found {len(dem_files)} DEM file(s):")
    for f in dem_files:
        print(f"  - {f.name}")
    print()
    
    # Use the first file (or you can add logic to select the correct one)
    return dem_files[0]

def load_dem(dem_file):
    """Load DEM and return data, transform, and metadata."""
    print("=" * 70)
    print("Loading DEM")
    print("=" * 70)
    print()
    print(f"File: {dem_file.name}")
    
    with rasterio.open(dem_file) as src:
        dem_data = src.read(1)  # Read first band
        transform = src.transform
        crs = src.crs
        nodata = src.nodata
        
        print(f"  Shape: {dem_data.shape}")
        print(f"  CRS: {crs}")
        print(f"  NoData value: {nodata}")
        print(f"  Resolution: {transform[0]:.2f} m")
        print()
        
        # Get bounds
        bounds = src.bounds
        print(f"  Bounds:")
        print(f"    West: {bounds.left:.4f}°E")
        print(f"    East: {bounds.right:.4f}°E")
        print(f"    South: {bounds.bottom:.4f}°N")
        print(f"    North: {bounds.top:.4f}°N")
        print()
        
        # Check if glacier location is within bounds
        if bounds.left <= GLACIER_LON <= bounds.right and bounds.bottom <= GLACIER_LAT <= bounds.top:
            print(f"  ✅ Glacier location ({GLACIER_LAT}°N, {GLACIER_LON}°E) is within DEM bounds")
        else:
            print(f"  ⚠️  Glacier location may be outside DEM bounds")
        
        print()
        
        metadata = {
            'transform': transform,
            'crs': crs,
            'nodata': nodata,
            'bounds': bounds,
            'width': src.width,
            'height': src.height
        }
    
    return dem_data, metadata

def compute_slope_aspect(dem_data, pixel_size):
    """Compute slope and aspect from DEM."""
    print("Computing slope and aspect...")
    
    # Compute gradients
    dy, dx = np.gradient(dem_data, pixel_size)
    
    # Compute slope (in degrees)
    slope_rad = np.arctan(np.sqrt(dx**2 + dy**2))
    slope_deg = np.degrees(slope_rad)
    
    # Compute aspect (in degrees, 0-360, 0=North)
    aspect_rad = np.arctan2(-dx, dy)  # Negative dx because y increases upward
    aspect_deg = np.degrees(aspect_rad)
    aspect_deg = np.where(aspect_deg < 0, aspect_deg + 360, aspect_deg)
    
    print(f"  Slope range: {np.nanmin(slope_deg):.1f}° - {np.nanmax(slope_deg):.1f}°")
    print(f"  Mean slope: {np.nanmean(slope_deg):.1f}°")
    print()
    
    return slope_deg, aspect_deg

def compute_hillshade(dem_data, pixel_size, azimuth=315, altitude=45):
    """Compute hillshade from DEM."""
    print("Computing hillshade...")
    
    # Compute gradients
    dy, dx = np.gradient(dem_data, pixel_size)
    
    # Convert azimuth and altitude to radians
    azimuth_rad = np.radians(azimuth)
    altitude_rad = np.radians(altitude)
    
    # Compute hillshade
    slope_rad = np.arctan(np.sqrt(dx**2 + dy**2))
    aspect_rad = np.arctan2(-dx, dy)
    
    hillshade = np.cos(altitude_rad) * np.cos(slope_rad) + \
                np.sin(altitude_rad) * np.sin(slope_rad) * \
                np.cos(azimuth_rad - aspect_rad)
    
    # Normalize to 0-255
    hillshade = (hillshade * 255).astype(np.uint8)
    
    print(f"  Hillshade range: {hillshade.min()} - {hillshade.max()}")
    print()
    
    return hillshade

def save_raster(data, output_file, metadata, dtype=rasterio.float32):
    """Save raster data to GeoTIFF."""
    with rasterio.open(
        output_file,
        'w',
        driver='GTiff',
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype=dtype,
        crs=metadata['crs'],
        transform=metadata['transform'],
        nodata=metadata['nodata'] if dtype == rasterio.float32 else None,
        compress='lzw'
    ) as dst:
        dst.write(data, 1)
    
    print(f"  ✅ Saved: {output_file}")

def create_visualizations(dem_data, slope, aspect, hillshade, metadata, output_dir):
    """Create visualization plots."""
    print("Creating visualizations...")
    print()
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    
    # DEM
    ax = axes[0, 0]
    im = ax.imshow(dem_data, cmap='terrain', aspect='auto')
    ax.set_title('DEM (Elevation)')
    ax.set_xlabel('Pixel X')
    ax.set_ylabel('Pixel Y')
    plt.colorbar(im, ax=ax, label='Elevation (m)')
    
    # Slope
    ax = axes[0, 1]
    im = ax.imshow(slope, cmap='YlOrRd', aspect='auto')
    ax.set_title('Slope')
    ax.set_xlabel('Pixel X')
    ax.set_ylabel('Pixel Y')
    plt.colorbar(im, ax=ax, label='Slope (degrees)')
    
    # Aspect
    ax = axes[1, 0]
    im = ax.imshow(aspect, cmap='hsv', aspect='auto', vmin=0, vmax=360)
    ax.set_title('Aspect')
    ax.set_xlabel('Pixel X')
    ax.set_ylabel('Pixel Y')
    plt.colorbar(im, ax=ax, label='Aspect (degrees)')
    
    # Hillshade
    ax = axes[1, 1]
    im = ax.imshow(hillshade, cmap='gray', aspect='auto')
    ax.set_title('Hillshade')
    ax.set_xlabel('Pixel X')
    ax.set_ylabel('Pixel Y')
    
    plt.tight_layout()
    
    plot_file = output_dir / "dem_analysis_plot.png"
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"✅ Plot saved: {plot_file}")
    plt.close()
    
    return plot_file

def compute_topographic_statistics(dem_data, slope, aspect, metadata, output_dir):
    """Compute and save topographic statistics."""
    print("Computing topographic statistics...")
    print()
    
    stats = {
        'elevation': {
            'min': float(np.nanmin(dem_data)),
            'max': float(np.nanmax(dem_data)),
            'mean': float(np.nanmean(dem_data)),
            'std': float(np.nanstd(dem_data)),
            'median': float(np.nanmedian(dem_data))
        },
        'slope': {
            'min': float(np.nanmin(slope)),
            'max': float(np.nanmax(slope)),
            'mean': float(np.nanmean(slope)),
            'std': float(np.nanstd(slope)),
            'median': float(np.nanmedian(slope))
        },
        'aspect': {
            'mean': float(np.nanmean(aspect)),
            'std': float(np.nanstd(aspect))
        },
        'glacier_location': {
            'latitude': GLACIER_LAT,
            'longitude': GLACIER_LON
        },
        'dem_info': {
            'resolution_m': float(metadata['transform'][0]),
            'bounds': {
                'west': float(metadata['bounds'].left),
                'east': float(metadata['bounds'].right),
                'south': float(metadata['bounds'].bottom),
                'north': float(metadata['bounds'].top)
            }
        }
    }
    
    # Save statistics
    stats_file = output_dir / "topographic_statistics.json"
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f"✅ Statistics saved: {stats_file}")
    print()
    print("Topographic Summary:")
    print(f"  Elevation: {stats['elevation']['min']:.0f} - {stats['elevation']['max']:.0f} m")
    print(f"  Mean elevation: {stats['elevation']['mean']:.0f} m")
    print(f"  Mean slope: {stats['slope']['mean']:.1f}°")
    print()
    
    return stats_file

def main():
    """Main processing function."""
    print("=" * 70)
    print("DEM Topographic Analysis")
    print("=" * 70)
    print()
    
    # Find DEM file
    dem_file = find_dem_file()
    if dem_file is None:
        return False
    
    # Load DEM
    dem_data, metadata = load_dem(dem_file)
    
    # Get pixel size from transform
    pixel_size = abs(metadata['transform'][0])  # Assuming square pixels
    
    # Compute slope and aspect
    slope, aspect = compute_slope_aspect(dem_data, pixel_size)
    
    # Compute hillshade
    hillshade = compute_hillshade(dem_data, pixel_size)
    
    # Save rasters
    print("Saving rasters...")
    print()
    save_raster(slope, OUTPUT_DIR / "slope.tif", metadata)
    save_raster(aspect, OUTPUT_DIR / "aspect.tif", metadata)
    save_raster(hillshade, OUTPUT_DIR / "hillshade.tif", metadata, dtype=rasterio.uint8)
    
    # Create visualizations
    plot_file = create_visualizations(dem_data, slope, aspect, hillshade, metadata, OUTPUT_DIR)
    
    # Compute statistics
    stats_file = compute_topographic_statistics(dem_data, slope, aspect, metadata, OUTPUT_DIR)
    
    print("=" * 70)
    print("✅ Processing Complete!")
    print("=" * 70)
    print()
    print("Output files:")
    print(f"  - {OUTPUT_DIR / 'slope.tif'}")
    print(f"  - {OUTPUT_DIR / 'aspect.tif'}")
    print(f"  - {OUTPUT_DIR / 'hillshade.tif'}")
    print(f"  - {plot_file}")
    print(f"  - {stats_file}")
    print()
    print("📋 Next steps:")
    print("  1. Extract along-flowline profiles (if flowline data available)")
    print("  2. Identify topographic pinning points (H1 mechanism)")
    print("  3. Compute topographic metrics for mechanism testing")
    print()
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

