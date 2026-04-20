#!/usr/bin/env python3
"""
Check whether Sep 13 and Sep 17 PlanetScope scenes are full-scene (not clips).
Run before autoRIFT: both scenes should match the reference extent and contain the glacier.

Usage:
  python check_planetscope_sep13_sep17_extent.py [path_to_sep13.tif] [path_to_sep17.tif]
  If no paths given, looks for planetscope_sep13.tif and planetscope_sep17.tif in cwd.
"""

import sys
from pathlib import Path

import rasterio

# Reference: Oct 25 full scene (target extent)
REF_PATH = Path(__file__).resolve().parents[3] / "planet_images/newa_planet/20251025_062608_36_251d_3B_AnalyticMS_SR.tif"
GLACIER_SHP = Path(__file__).resolve().parents[3] / "Didal_Glacier_GIS_Data/Glacier_Outline/didal_glacier_outline.shp"


def main():
    if len(sys.argv) >= 3:
        files = [sys.argv[1], sys.argv[2]]
    else:
        files = ["planetscope_sep13.tif", "planetscope_sep17.tif"]

    print("Reference extent (what you need to match):")
    ref_bounds = None
    ref_shape = (8392, 11840)
    if REF_PATH.exists():
        with rasterio.open(REF_PATH) as src:
            ref_shape = src.shape
            ref_bounds = src.bounds
            print(f"  {REF_PATH.name}: shape={ref_shape}, bounds={ref_bounds}")
    else:
        print("  (Reference file not found; using 8392×11840 as target.)")

    print("\nGlacier must fall inside both scene bounds.")
    if GLACIER_SHP.exists() and REF_PATH.exists():
        import geopandas as gpd
        g = gpd.read_file(GLACIER_SHP)
        with rasterio.open(REF_PATH) as r:
            if g.crs != r.crs:
                g = g.to_crs(r.crs)
            b = g.total_bounds
        print(f"  Glacier bounds (ref CRS): left={b[0]:.1f}, bottom={b[1]:.1f}, right={b[2]:.1f}, top={b[3]:.1f}")
    else:
        print("  (Glacier shapefile not found.)")

    print("\nScene check:")
    ok = True
    for f in files:
        path = Path(f)
        if not path.exists():
            print(f"  {f}: NOT FOUND — no such file.")
            ok = False
            continue
        try:
            with rasterio.open(path) as src:
                shape = src.shape
                bounds = src.bounds
                print(f"  {path.name}: shape={shape}, bounds={bounds}")
            if ref_bounds is not None:
                if shape != ref_shape:
                    print(f"    -> Different shape from reference {ref_shape}; coregister to ref grid.")
                if abs(bounds[0] - ref_bounds[0]) > 1 or abs(bounds[2] - ref_bounds[2]) > 1:
                    print(f"    -> Different horizontal extent; coregister to ref.")
        except Exception as e:
            print(f"  {f}: ERROR — {e}")
            ok = False

    if ok and len(files) == 2:
        print("\nBoth scenes found. If shapes match the reference, you can run autoRIFT.")
    elif not ok:
        print("\nMissing or invalid scene(s). Download Sep 13 and Sep 17 AnalyticMS SR and place as above.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
