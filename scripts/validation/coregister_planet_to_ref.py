#!/usr/bin/env python3
"""
Reproject a secondary PlanetScope (or any) GeoTIFF to match a reference's grid.
Output: same CRS, transform, and shape as ref. Use for autoRIFT pre-check / run.

Usage:
  python coregister_planet_to_ref.py --ref ref.tif --sec sec.tif --out sec_coreg_to_ref.tif
"""

import argparse
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling


def main():
    p = argparse.ArgumentParser(description="Coregister sec raster to ref grid")
    p.add_argument("--ref", required=True, help="Reference GeoTIFF (defines grid)")
    p.add_argument("--sec", required=True, help="Secondary GeoTIFF to reproject")
    p.add_argument("--out", required=True, help="Output path (coregistered sec)")
    p.add_argument("--band", type=int, default=1, help="Band to use from sec (1-based); default 1; ignored if --all-bands")
    p.add_argument("--all-bands", action="store_true", help="Coregister all bands from sec (for NIR band 4 etc.)")
    args = p.parse_args()

    ref_path = Path(args.ref)
    sec_path = Path(args.sec)
    out_path = Path(args.out)
    if not ref_path.exists() or not sec_path.exists():
        raise SystemExit("Ref or sec file not found.")

    with rasterio.open(ref_path) as ref:
        ref_shape = ref.shape
        ref_transform = ref.transform
        ref_crs = ref.crs
        ref_dtype = ref.dtypes[0]
        ref_nodata = ref.nodata

    with rasterio.open(sec_path) as sec:
        src_transform = sec.transform
        src_crs = sec.crs
        src_nodata = sec.nodata
        if src_nodata is None:
            src_nodata = np.nan
        nbands = sec.count if args.all_bands else 1
        band_list = list(range(1, nbands + 1)) if args.all_bands else [args.band]

    dest_list = []
    for b in band_list:
        with rasterio.open(sec_path) as sec:
            sec_data = sec.read(b, out_dtype=np.float32)
        dest = np.full((ref_shape[0], ref_shape[1]), np.nan, dtype=np.float32)
        reproject(
            source=sec_data,
            destination=dest,
            src_transform=src_transform,
            src_crs=src_crs,
            dst_transform=ref_transform,
            dst_crs=ref_crs,
            resampling=Resampling.cubic,
            src_nodata=src_nodata,
            dst_nodata=np.nan,
        )
        dest_list.append(dest)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        out_path,
        "w",
        driver="GTiff",
        height=ref_shape[0],
        width=ref_shape[1],
        count=len(dest_list),
        dtype=dest_list[0].dtype,
        crs=ref_crs,
        transform=ref_transform,
        nodata=np.nan,
    ) as dst:
        for i, d in enumerate(dest_list, 1):
            dst.write(d, i)

    print("Wrote", out_path)
    print("Pre-check: python run_autorift_didal_optical.py --check-only --ref", ref_path, "--sec", out_path)


if __name__ == "__main__":
    main()
