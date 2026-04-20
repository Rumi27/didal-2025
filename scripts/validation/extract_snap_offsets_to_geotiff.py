#!/usr/bin/env python3
"""
extract_snap_offsets_to_geotiff.py (CORRECTED)
================================================
Extract raw SAR offset bands from SNAP BEAM-DIMAP velocity products.
"""

import argparse
import os
import glob
import numpy as np
import rasterio
from pathlib import Path


def find_offset_bands(data_dir):
    """Search SNAP .data directory for offset band .img files."""
    img_files = glob.glob(os.path.join(data_dir, "*.img"))
    
    offset_x_pattern = ["offset_x", "crs_offset_x", "x_offset", "east"]
    offset_y_pattern = ["offset_y", "crs_offset_y", "y_offset", "north"]
    
    offset_x_file = None
    offset_y_file = None
    
    for img in img_files:
        basename = os.path.basename(img).lower()
        if any(p in basename for p in offset_x_pattern):
            offset_x_file = img
        if any(p in basename for p in offset_y_pattern):
            offset_y_file = img
    
    if offset_x_file is None or offset_y_file is None:
        print(f"\nAvailable bands in {data_dir}:")
        for i, img in enumerate(img_files):
            print(f"  [{i}] {os.path.basename(img)}")
        
        if offset_x_file is None and len(img_files) >= 2:
            offset_x_file = img_files[0]
            print("\nUsing first band as offset_x (East)")
        
        if offset_y_file is None and len(img_files) >= 2:
            offset_y_file = img_files[1]
            print("Using second band as offset_y (North)")
    
    if offset_x_file is None or offset_y_file is None:
        raise ValueError(f"Could not find offset bands in {data_dir}")
    
    return offset_x_file, offset_y_file


def read_envi_img(img_path):
    """Read SNAP ENVI .img file using rasterio."""
    with rasterio.open(img_path, "r") as src:
        data = src.read(1)
        profile = src.profile.copy()
    return data, profile


def extract_offsets_from_snap(vel_dim_path, dt_days):
    """Extract E and N offsets from SNAP velocity product."""
    dim_path = Path(vel_dim_path)
    data_dir = dim_path.with_suffix(".data")
    
    if not data_dir.exists():
        raise FileNotFoundError(f"SNAP .data directory not found: {data_dir}")
    
    print(f"  Searching in: {data_dir}")
    
    offset_x_img, offset_y_img = find_offset_bands(data_dir)
    
    print(f"  Reading East offset from: {os.path.basename(offset_x_img)}")
    print(f"  Reading North offset from: {os.path.basename(offset_y_img)}")
    
    offset_x, prof_x = read_envi_img(offset_x_img)
    offset_y, prof_y = read_envi_img(offset_y_img)
    
    if offset_x.shape != offset_y.shape:
        raise ValueError(f"Offset bands have mismatched shapes")
    
    if "transform" in prof_x and prof_x["transform"] is not None:
        pixel_size_x = abs(prof_x["transform"][0])
        pixel_size_y = abs(prof_x["transform"][4])
        print(f"  Pixel spacing: {pixel_size_x:.1f} m (E), {pixel_size_y:.1f} m (N)")
    else:
        pixel_size_x = pixel_size_y = 10.0
        print(f"  WARNING: No geotransform found; assuming 10m pixel spacing")
    
    dE = (offset_x * pixel_size_x) / dt_days
    dN = (offset_y * pixel_size_y) / dt_days
    
    return dE, dN, prof_x


def write_2band_geotiff(dE, dN, profile, out_path):
    """Write 2-band GeoTIFF (Band 1 = dE, Band 2 = dN)."""
    profile.update({
        "count": 2,
        "dtype": rasterio.float32,
        "compress": "lzw",
        "nodata": np.nan,
    })
    
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(dE.astype(np.float32), 1)
        dst.write(dN.astype(np.float32), 2)
        dst.set_band_description(1, "dE_m_per_day")
        dst.set_band_description(2, "dN_m_per_day")
    
    print(f"  ✓ Written: {out_path}")


def main():
    p = argparse.ArgumentParser(description="Extract raw SAR offsets from SNAP velocity product.")
    p.add_argument("--vel-dim", required=True, help="Path to SNAP *_Stack_vel.dim file")
    p.add_argument("--out", required=True, help="Output 2-band GeoTIFF path")
    p.add_argument("--dt-days", type=float, required=True, help="Time interval (days)")
    
    args = p.parse_args()
    
    print(f"\nProcessing: {args.vel_dim}")
    print(f"Time interval: {args.dt_days} days")
    
    dE, dN, prof = extract_offsets_from_snap(args.vel_dim, args.dt_days)
    
    print(f"\nOffset arrays shape: {dE.shape}")
    print(f"  dE range: [{np.nanmin(dE):.2f}, {np.nanmax(dE):.2f}] m/day")
    print(f"  dN range: [{np.nanmin(dN):.2f}, {np.nanmax(dN):.2f}] m/day")
    
    write_2band_geotiff(dE, dN, prof, args.out)
    
    print(f"\n✓ DONE\n")


if __name__ == "__main__":
    main()

