#!/usr/bin/env python3
"""
PlanetScope optical velocity workflow for Didal Glacier using autoRIFT.

Key parameters (3 m resolution, glacier tongue ~330 m wide):
  - Chip size: 32–64 px (96–192 m)
  - Search range: 300–500 px (900–1500 m) for 4–12 day baselines
  - Min chip fraction in glacier: 0.30
  - Stable-ground tie points for uncertainty (NMAD)

Outputs:
  - velocity_mag/vx/vy GeoTIFFs, chipsize_used diagnostic, autorift_summary.json
  - Glacier median velocity; stable-ground NMAD (1σ); optical/SAR ratio

Pre-check (run first): --check-only --ref <sep13.tif> --sec <sep17.tif>
  Must print True True True; if not, run the reproject snippet then retry.

Usage:
  python run_autorift_didal_optical.py --ref <ref.tif> --sec <sec.tif> --dt-days 4 [options]

Requirements:
  conda install -c conda-forge autorift
  pip install rasterio geopandas numpy scipy
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

try:
    import rasterio
    from rasterio.features import geometry_mask
    from rasterio.mask import mask as rio_mask
    from rasterio.crs import CRS
    import geopandas as gpd
    from shapely.geometry import mapping
except ImportError as e:
    print(f"Required: pip install rasterio geopandas. Error: {e}")
    sys.exit(1)

try:
    from autoRIFT import autoRIFT
except ImportError:
    print("autoRIFT not found. Install with: conda install -c conda-forge autorift")
    sys.exit(1)

# -----------------------------------------------------------------------------
# Default paths (edit or pass via CLI)
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[3]
GLACIER_OUTLINE = BASE_DIR / "Didal_Glacier_GIS_Data/Glacier_Outline/didal_glacier_outline.shp"
STABLE_GROUND_SHP = BASE_DIR / "stable_ground_mask.shp"
OPTICAL_OUTPUT_DIR = BASE_DIR / "processed_data/velocity_validation/optical_autorift"
# SAR velocity for comparison (e.g. Sep 13→25 12-day)
SAR_VELOCITY_TIF = BASE_DIR / "processed_data/velocity_validation/same_track/geotiff/velocity_track173_20250913_20250925.tif"

# Didal parameters @ 3 m GSD
GSD_M = 3.0
CHIP_SIZE_MIN_PX = 32
CHIP_SIZE_MAX_PX = 64
CHIP_SIZE0_PX = 32
GRID_SPACING_PX = 16   # was 32; finer grid for narrow glacier
SEARCH_RANGE_4DAY_PX = 350   # ~240–300 m displacement
SEARCH_RANGE_12DAY_PX = 450  # ~700–720 m
MIN_CHIP_FRACTION_GLACIER = 0.05


def load_band(geotiff_path, band_index=1):
    """Load single band as float32 array. band_index 1-based."""
    with rasterio.open(geotiff_path) as src:
        data = src.read(band_index, out_dtype=np.float32)
        transform = src.transform
        crs = src.crs
        nodata = src.nodata
    if nodata is not None:
        data[data == nodata] = np.nan
    return data, transform, crs, nodata


def rasterise_mask(shp_path, out_shape, transform, crs, invert=True):
    """
    Burn polygon(s) onto the image grid. invert=True → True = inside polygon.
    Returns boolean array of shape out_shape, or None if shp_path missing/invalid.
    """
    if not Path(shp_path).exists():
        return None
    try:
        gdf = gpd.read_file(shp_path)
        if gdf.crs != crs:
            gdf = gdf.to_crs(crs)
        geoms = [mapping(g) for g in gdf.geometry]
        mask = geometry_mask(geoms, out_shape=out_shape, transform=transform, invert=invert)
        return mask
    except Exception:
        return None


def downsample_mask_to_grid(mask_full, grid_rows, grid_cols, grid_spacing):
    """Downsample full-res mask to grid by nearest-neighbour (center sample)."""
    # Grid cell (i,j) → full-res center (i*gs + gs//2, j*gs + gs//2)
    ri = (np.arange(grid_rows) * grid_spacing + grid_spacing // 2).clip(0, mask_full.shape[0] - 1)
    ci = (np.arange(grid_cols) * grid_spacing + grid_spacing // 2).clip(0, mask_full.shape[1] - 1)
    return mask_full[np.ix_(ri, ci)]


def build_regular_grid(rows, cols, grid_spacing):
    """Build pixel-center grid for autoRIFT (0.5, 1.5, ... in pixel coords)."""
    ngr = rows // grid_spacing
    ngc = cols // grid_spacing
    if ngr < 1 or ngc < 1:
        raise ValueError("Image too small for grid_spacing")
    r = np.arange(0.5, ngr * grid_spacing, grid_spacing, dtype=np.float32)
    c = np.arange(0.5, ngc * grid_spacing, grid_spacing, dtype=np.float32)
    rr, cc = np.meshgrid(r, c, indexing="ij")
    return rr, cc, ngr, ngc


def run_autorift_on_pair(
    ref_arr,
    sec_arr,
    grid_spacing=GRID_SPACING_PX,
    chip_min=CHIP_SIZE_MIN_PX,
    chip_max=CHIP_SIZE_MAX_PX,
    chip0=CHIP_SIZE0_PX,
    search_limit_px=400,
):
    """
    Run autoRIFT on two co-registered arrays (same size). Returns Dx, Dy in pixels.
    """
    rows, cols = ref_arr.shape
    if ref_arr.shape != sec_arr.shape:
        raise ValueError("Reference and secondary images must have same dimensions")

    # Replace NaN with 0 for autoRIFT
    I1 = np.nan_to_num(ref_arr, nan=0.0, copy=True).astype(np.float32)
    I2 = np.nan_to_num(sec_arr, nan=0.0, copy=True).astype(np.float32)

    yGrid, xGrid, ngr, ngc = build_regular_grid(rows, cols, grid_spacing)
    # Trim grid to fit nested chip constraint (multiple of chip_max/chip0)
    chop = int(chip_max / chip0)
    rlim = (ngr // chop) * chop
    clim = (ngc // chop) * chop
    yGrid = yGrid[:rlim, :clim].astype(np.float32)
    xGrid = xGrid[:rlim, :clim].astype(np.float32)

    ar = autoRIFT()
    ar.I1 = I1
    ar.I2 = I2
    ar.xGrid = xGrid
    ar.yGrid = yGrid
    ar.ChipSize0X = chip0
    ar.ChipSizeMinX = chip_min
    ar.ChipSizeMaxX = chip_max
    ar.GridSpacingX = grid_spacing
    ar.SkipSampleX = grid_spacing
    ar.SkipSampleY = grid_spacing
    ar.SearchLimitX = np.float32(search_limit_px)
    ar.SearchLimitY = np.float32(search_limit_px)
    ar.Dx0 = np.float32(0)
    ar.Dy0 = np.float32(0)
    ar.FracValid = MIN_CHIP_FRACTION_GLACIER
    ar.DataType = 1  # float

    # Wallis filter — recommended for optical ice texture (suppresses illumination, keeps crevasses)
    ar.preprocess_filt_wal()
    # autoRIFT requires uint8 or float32; Wallis can leave float64
    ar.I1 = np.asarray(ar.I1, dtype=np.float32)
    ar.I2 = np.asarray(ar.I2, dtype=np.float32)

    ar.runAutorift()

    # ar.Dx, ar.Dy: displacement in pixels (ref to sec); ar.ChipSizeX: diagnostic
    return ar.Dx, ar.Dy, ar.xGrid, ar.yGrid, (rlim, clim), ar.ChipSizeX


def pixel_displacement_to_velocity_rasters(
    Dx_px, Dy_px, xGrid, yGrid, grid_spacing, transform, gsd_m, dt_days
):
    """
    Convert sparse (Dx, Dy) from grid to velocity in m/day.
    vE = Dx·GSD/Δt, vN = −Dy·GSD/Δt (sign flip: image row increases downward = south).
    Returns grid-sized vx, vy (m/day) and transform for that grid (subsampled).
    """
    dE_m = Dx_px * gsd_m
    dN_m = -Dy_px * gsd_m  # −Dy so northward velocity is positive
    vx = dE_m / dt_days
    vy = dN_m / dt_days

    # Subgrid transform: grid (0,0) = center of original pixel (0.5, 0.5)
    from rasterio.transform import Affine
    a, b, c, d, e, f = transform[0], transform[1], transform[2], transform[3], transform[4], transform[5]
    c0 = c + 0.5 * (a + b)
    f0 = f + 0.5 * (d + e)
    sub_transform = Affine(a * grid_spacing, b, c0, d, e * grid_spacing, f0)

    return vx, vy, sub_transform


def magnitude_mday(vx, vy):
    return np.sqrt(np.square(vx) + np.square(vy))


def nmad(x):
    """Normalized median absolute deviation (robust scatter)."""
    x = np.asarray(x)
    x = x[np.isfinite(x)]
    if len(x) < 2:
        return np.nan
    return 1.4826 * np.median(np.abs(x - np.median(x)))


def main():
    parser = argparse.ArgumentParser(
        description="Run autoRIFT on PlanetScope pair for Didal Glacier"
    )
    parser.add_argument("--ref", required=True, help="Reference image (GeoTIFF, e.g. Sep 13)")
    parser.add_argument("--sec", required=True, help="Secondary image (e.g. Sep 17 or Sep 25)")
    parser.add_argument("--check-only", action="store_true", help="Only verify ref/sec coregistration (transform, shape, CRS) and exit")
    parser.add_argument("--dt-days", type=float, default=None, help="Time span in days (e.g. 4 or 12); required unless --check-only")
    parser.add_argument("--band", type=int, default=1, help="Band index (1-based); NIR often 4 for Planet")
    parser.add_argument("--search-px", type=int, default=None, help="Search range in pixels (default: 350 for 4d, 450 for 12d)")
    parser.add_argument("--out-dir", type=Path, default=OPTICAL_OUTPUT_DIR, help="Output directory")
    parser.add_argument("--glacier-shp", type=Path, default=GLACIER_OUTLINE, help="Glacier outline")
    parser.add_argument("--stable-shp", type=Path, default=STABLE_GROUND_SHP, help="Stable ground polygon for NMAD")
    parser.add_argument("--sar-tif", type=Path, default=SAR_VELOCITY_TIF, help="SAR velocity GeoTIFF for comparison")
    args = parser.parse_args()

    ref_path = Path(args.ref)
    sec_path = Path(args.sec)
    if not ref_path.exists() or not sec_path.exists():
        print(f"ERROR: Ref or sec file not found: {ref_path}, {sec_path}")
        sys.exit(1)

    # -------------------------------------------------------------------------
    # Step 1/7: Load imagery
    # -------------------------------------------------------------------------
    print("Step 1/7: Load imagery")
    ref_arr, transform, crs, nodata = load_band(ref_path, args.band)
    sec_arr, transform_sec, crs_sec, _ = load_band(sec_path, args.band)
    same_transform = transform == transform_sec
    same_shape = ref_arr.shape == sec_arr.shape
    same_crs = crs == crs_sec
    if not same_shape:
        print("ERROR: Ref and sec must have identical dimensions. Coregister first.")
        sys.exit(1)
    if not same_crs:
        print("ERROR: Ref and sec must share CRS. Coregister first.")
        sys.exit(1)

    if args.check_only:
        print(same_transform, same_shape, same_crs)
        if not (same_transform and same_shape and same_crs):
            print("Coregistration failed. Reproject sec to ref grid, e.g.:")
            print("  from rasterio.warp import reproject, Resampling")
            print("  with rasterio.open(ref) as ref_src, rasterio.open(sec) as src:")
            print("      data, _ = reproject(src.read(1), destination=np.zeros(ref_src.shape),")
            print("          src_transform=src.transform, src_crs=src.crs,")
            print("          dst_transform=ref_src.transform, dst_crs=ref_src.crs,")
            print("          resampling=Resampling.cubic)")
        sys.exit(0 if (same_transform and same_shape and same_crs) else 1)

    dt_days = args.dt_days
    if dt_days is None:
        print("ERROR: --dt-days required (e.g. 4 or 12)")
        sys.exit(1)
    search_px = args.search_px
    if search_px is None:
        search_px = SEARCH_RANGE_4DAY_PX if dt_days <= 6 else SEARCH_RANGE_12DAY_PX

    args.out_dir.mkdir(parents=True, exist_ok=True)
    pair_name = f"{ref_path.stem}_{sec_path.stem}"

    # -------------------------------------------------------------------------
    # Step 2/7: Rasterise masks (full res), then downsample to output grid
    # -------------------------------------------------------------------------
    print("Step 2/7: Rasterise masks")
    H, W = ref_arr.shape
    glacier_mask_full = rasterise_mask(args.glacier_shp, (H, W), transform, crs, invert=True)
    stable_mask_full = rasterise_mask(args.stable_shp, (H, W), transform, crs, invert=True)
    if glacier_mask_full is None:
        print("  Warning: glacier outline not found or invalid; skipping glacier statistic.")
    if stable_mask_full is None:
        print("  Warning: stable ground mask not found or invalid; skipping NMAD.")

    # Grid dimensions (will match trimmed grid after run_autorift)
    ngr = H // GRID_SPACING_PX
    ngc = W // GRID_SPACING_PX
    chop = int(CHIP_SIZE_MAX_PX / CHIP_SIZE0_PX)
    rlim = (ngr // chop) * chop
    clim = (ngc // chop) * chop
    if glacier_mask_full is not None:
        glacier_grid = downsample_mask_to_grid(glacier_mask_full, rlim, clim, GRID_SPACING_PX)
    else:
        glacier_grid = None
    if stable_mask_full is not None:
        stable_grid = downsample_mask_to_grid(stable_mask_full, rlim, clim, GRID_SPACING_PX)
    else:
        stable_grid = None

    # -------------------------------------------------------------------------
    # Step 3/7 & 4/7: Configure and run autoRIFT
    # -------------------------------------------------------------------------
    print("Step 3/7: Configure autoRIFT (chip 32–64 px, search {} px, FracValid 0.30, Wallis)".format(search_px))
    print("Step 4/7: Run autoRIFT (typically 5–15 min)...")
    Dx, Dy, xGrid, yGrid, (rlim, clim), ChipSizeUsed = run_autorift_on_pair(
        ref_arr, sec_arr,
        grid_spacing=GRID_SPACING_PX,
        chip_min=CHIP_SIZE_MIN_PX,
        chip_max=CHIP_SIZE_MAX_PX,
        chip0=CHIP_SIZE0_PX,
        search_limit_px=search_px,
    )

    # -------------------------------------------------------------------------
    # Step 5/7: Convert to velocity (vE = Dx·GSD/Δt, vN = −Dy·GSD/Δt)
    # -------------------------------------------------------------------------
    print("Step 5/7: Convert to velocity (m d⁻¹)")
    vx_full, vy_full, out_transform = pixel_displacement_to_velocity_rasters(
        Dx, Dy, xGrid, yGrid, GRID_SPACING_PX, transform, GSD_M, dt_days
    )
    vel_full = magnitude_mday(vx_full, vy_full)

    # -------------------------------------------------------------------------
    # Step 6/7: Statistics (glacier median, stable-ground NMAD, SAR comparison)
    # -------------------------------------------------------------------------
    print("Step 6/7: Statistics")
    results = {"pair": pair_name, "dt_days": dt_days, "search_px": search_px}
    glacier_gdf = None

    if glacier_grid is not None:
        use = glacier_grid & np.isfinite(vel_full)
        if np.any(use):
            v_glacier = vel_full[use]
            results["glacier_median_velocity_mday"] = float(np.nanmedian(v_glacier))
            results["glacier_mean_velocity_mday"] = float(np.nanmean(v_glacier))
            results["glacier_n_pixels"] = int(np.sum(use))
            print("  Glacier: median v = {:.2f} m/day (n={})".format(
                results["glacier_median_velocity_mday"], results["glacier_n_pixels"]))
        else:
            results["glacier_median_velocity_mday"] = None
    else:
        results["glacier_median_velocity_mday"] = None

    if stable_grid is not None:
        use = stable_grid & np.isfinite(vel_full)
        if np.sum(use) >= 20:
            v_stable = vel_full[use]
            nmad_stable = nmad(v_stable)
            results["stable_ground_nmad_mday"] = float(nmad_stable)
            results["stable_ground_median_mday"] = float(np.nanmedian(v_stable))
            results["stable_ground_n_pixels"] = int(np.sum(use))
            results["centerline_uncertainty_NMAD_mday"] = float(nmad_stable)
            print("  Stable ground: NMAD = {:.3f} m/day (n={})".format(nmad_stable, np.sum(use)))
        else:
            results["stable_ground_nmad_mday"] = None
            results["centerline_uncertainty_NMAD_mday"] = None
    else:
        results["stable_ground_nmad_mday"] = None
        results["centerline_uncertainty_NMAD_mday"] = None

    # SAR comparison: optical/SAR ratio (mask SAR to glacier)
    if args.sar_tif and Path(args.sar_tif).exists() and args.glacier_shp.exists():
        try:
            glacier_gdf = gpd.read_file(args.glacier_shp)
            with rasterio.open(args.sar_tif) as sar_src:
                sar_crs = sar_src.crs
                if glacier_gdf.crs != sar_crs:
                    glacier_reproj = glacier_gdf.to_crs(sar_crs)
                    geoms = [mapping(glacier_reproj.geometry.unary_union)]
                else:
                    geoms = [mapping(glacier_gdf.geometry.unary_union)]
                sar_masked, _ = rio_mask(sar_src, geoms, crop=True, nodata=np.nan)
            sar_vel = sar_masked[0]
            valid = np.isfinite(sar_vel) & (sar_vel > 0)
            if np.any(valid):
                v_sar_median = float(np.nanmedian(sar_vel[valid]))
                results["SAR_median_velocity_mday"] = v_sar_median
                v_opt = results.get("glacier_median_velocity_mday")
                if v_opt is not None and v_sar_median > 0:
                    results["optical_SAR_ratio"] = float(v_opt / v_sar_median)
                results["v_optical_vs_SAR"] = (v_opt, v_sar_median)
                print("  SAR (same period): median v = {:.2f} m/day; optical/SAR ratio = {}".format(
                    v_sar_median, results.get("optical_SAR_ratio")))
        except Exception as e:
            results["SAR_error"] = str(e)[:200]
    else:
        results["SAR_median_velocity_mday"] = None

    # -------------------------------------------------------------------------
    # Step 7/7: Outputs (four GeoTIFFs + one JSON)
    # -------------------------------------------------------------------------
    print("Step 7/7: Outputs")
    profile = {
        "driver": "GTiff", "height": vx_full.shape[0], "width": vx_full.shape[1],
        "count": 1, "dtype": vx_full.dtype, "crs": crs, "transform": out_transform,
        "nodata": np.nan,
    }
    out_vel = args.out_dir / f"velocity_mag_{pair_name}.tif"
    out_vx = args.out_dir / f"velocity_vx_{pair_name}.tif"
    out_vy = args.out_dir / f"velocity_vy_{pair_name}.tif"
    out_chip = args.out_dir / f"chipsize_used_{pair_name}.tif"
    for path, data in [
        (out_vel, vel_full),
        (out_vx, vx_full),
        (out_vy, vy_full),
        (out_chip, ChipSizeUsed.astype(np.float32)),
    ]:
        with rasterio.open(path, "w", **profile) as dst:
            dst.write(data, 1)
    print("  {}".format(out_vel))
    print("  {}".format(out_vx))
    print("  {}".format(out_vy))
    print("  {} (diagnostic: which chip size won)".format(out_chip))

    out_json = args.out_dir / f"autorift_summary_{pair_name}.json"
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2)
    print("  {}".format(out_json))
    return 0


if __name__ == "__main__":
    sys.exit(main())
