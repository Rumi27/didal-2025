#!/usr/bin/env python3
"""
Window + Glacier-Fraction Sensitivity for Vindex Extraction

Purpose: Address reviewer concern about valley-wall mixing in template matching.

Key features:
1. Glacier-fraction filtering: Only accept templates with ≥70% glacier coverage
2. Parameterized window size: 32, 64, 128 px
3. Fixed, eroded Ω masks across all epochs
4. Outputs per-window Vindex time series + quality metrics

Usage:
  python3 window_mask_sensitivity.py --window_px 32 --glacier_fraction 0.7
  python3 window_mask_sensitivity.py --window_px 64 --glacier_fraction 0.7
  python3 window_mask_sensitivity.py --window_px 128 --glacier_fraction 0.7
"""

from __future__ import annotations
import argparse
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
import warnings

from osgeo import gdal
import numpy as np
import pandas as pd

try:
    import fiona
    from shapely.geometry import shape, Point, box
    from shapely.ops import unary_union
except Exception as e:
    raise RuntimeError("Missing GIS dependencies (fiona/shapely).") from e

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------
GLACIER_LAT = 38.97
GLACIER_LON = 70.75
PROCESSED_DIR = Path("satellite_data/sentinel1/processed")
VELOCITY_TS_FILE = PROCESSED_DIR / "velocity_timeseries_python.csv"
GLACIER_OUTLINE_SHP = Path("satellite_data/dem/processed/didal_glacier_rgi_outline.shp")
STABLE_GROUND_MASK_SHP = Path("stable_ground_mask.shp")
OUTPUT_BASE_DIR = Path("processed_data/window_sensitivity")
OUTPUT_BASE_DIR.mkdir(parents=True, exist_ok=True)

# Stable-ground debiasing parameters
STABLE_BBOX_BUFFER_DEG = 0.20
GLACIER_EXCLUDE_BUFFER_DEG = 0.002
SAMPLE_STEP_PX = 100
MIN_VALID_STABLE_MATCHES = 80
COARSE_WIN_SIZE = 2048
COARSE_DOWNSAMPLE = 8
STABLE_PHASECORR_WIN = 256
MIN_CORR = 0.0

# Glacier sampling
GLACIER_SAMPLE_STEP_PX = 1
GLACIER_MIN_CORR = 0.0
LOCAL_SEARCH_RANGE = 120

# Omega buffer settings (fixed erosion in degrees)
# ~30m erosion = -0.0003 deg is the primary "base" mask
OMEGA_EROSION_BASE_DEG = -0.0003
OMEGA_EROSION_NARROW_DEG = -0.0005
OMEGA_EROSION_WIDE_DEG = -0.0001


@dataclass
class BiasModel:
    """Planar bias model: d = a + b*x + c*y (x,y centered pixel coords)."""
    a: float
    b: float
    c: float

    def predict(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        return self.a + self.b * x + self.c * y


def _extract_date_from_filename(filename: str | Path) -> datetime | None:
    import re
    dates = re.findall(r"(\d{8})", str(filename))
    if dates:
        try:
            return datetime.strptime(dates[0], "%Y%m%d")
        except Exception:
            return None
    return None


def _find_tc_products() -> dict[str, Path]:
    """Map YYYY-MM-DD -> *_Orb_Cal_TC.dim Path."""
    products = sorted(PROCESSED_DIR.glob("*_Orb_Cal_TC.dim"))
    out: dict[str, Path] = {}
    for p in products:
        d = _extract_date_from_filename(p.name)
        if d is not None:
            out[d.strftime("%Y-%m-%d")] = p
    return out


def _open_sigma0_band(tc_dim: Path) -> gdal.Dataset:
    """Open a terrain-corrected Sigma0 band inside SNAP .data folder (ENVI .img) using GDAL."""
    data_folder = tc_dim.with_suffix(".data")
    vv = list(data_folder.glob("Sigma0_VV.img"))
    vh = list(data_folder.glob("Sigma0_VH.img"))
    if vv:
        ds = gdal.Open(str(vv[0]), gdal.GA_ReadOnly)
        if ds is None:
            raise RuntimeError(f"GDAL could not open {vv[0]}")
        return ds
    if vh:
        ds = gdal.Open(str(vh[0]), gdal.GA_ReadOnly)
        if ds is None:
            raise RuntimeError(f"GDAL could not open {vh[0]}")
        return ds
    raise FileNotFoundError(f"No Sigma0_VV.img or Sigma0_VH.img in {data_folder}")


def _nmad(x: np.ndarray) -> float:
    """Normalized median absolute deviation (robust sigma)."""
    x = np.asarray(x, dtype=np.float64)
    med = np.nanmedian(x)
    return float(1.4826 * np.nanmedian(np.abs(x - med)))


def _fit_plane(z: np.ndarray, x: np.ndarray, y: np.ndarray) -> BiasModel:
    """Least-squares fit z = a + b*x + c*y."""
    A = np.column_stack([np.ones_like(x), x, y]).astype(np.float64)
    coef, *_ = np.linalg.lstsq(A, z.astype(np.float64), rcond=None)
    return BiasModel(a=float(coef[0]), b=float(coef[1]), c=float(coef[2]))


def _read_window(ds: gdal.Dataset, row: int, col: int, window_size: int) -> np.ndarray | None:
    """Read and preprocess a window from GDAL dataset (log-intensity, high-pass, normalize)."""
    band = ds.GetRasterBand(1)
    if band is None:
        return None
    half = window_size // 2
    try:
        arr = band.ReadAsArray(col - half, row - half, window_size, window_size)
        if arr is None or arr.size == 0:
            return None
    except Exception:
        return None

    arr = arr.astype(np.float64)
    arr[arr <= 0] = 1e-6
    arr = np.log10(arr)

    # High-pass filter (remove large-scale gradients)
    kernel_size = max(5, window_size // 16)
    if kernel_size % 2 == 0:
        kernel_size += 1
    from scipy.ndimage import uniform_filter
    low_freq = uniform_filter(arr, size=kernel_size)
    arr = arr - low_freq

    # Normalize
    arr = (arr - np.nanmean(arr)) / (np.nanstd(arr) + 1e-8)
    return arr


def _estimate_global_shift_phasecorr(
    master_ds: gdal.Dataset,
    slave_ds: gdal.Dataset,
    glacier_bounds,
) -> tuple[float, float, float]:
    """Estimate a coarse global shift using phase correlation on a downsampled window."""
    from scipy import fft

    minx, miny, maxx, maxy = glacier_bounds
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2

    gt = master_ds.GetGeoTransform()
    if gt is None:
        raise RuntimeError("Missing geotransform on master.")

    def lonlat_to_rowcol(lon: float, lat: float) -> tuple[int, int]:
        col = int((lon - gt[0]) / gt[1])
        row = int((lat - gt[3]) / gt[5])
        return row, col

    cr, cc = lonlat_to_rowcol(cx, cy)

    half = COARSE_WIN_SIZE // 2
    r0, c0 = cr - half, cc - half

    m_band = master_ds.GetRasterBand(1)
    s_band = slave_ds.GetRasterBand(1)

    try:
        m_arr = m_band.ReadAsArray(c0, r0, COARSE_WIN_SIZE, COARSE_WIN_SIZE)
        s_arr = s_band.ReadAsArray(c0, r0, COARSE_WIN_SIZE, COARSE_WIN_SIZE)
    except Exception:
        return 0.0, 0.0, 0.0

    if m_arr is None or s_arr is None:
        return 0.0, 0.0, 0.0

    # Downsample
    m_small = m_arr[::COARSE_DOWNSAMPLE, ::COARSE_DOWNSAMPLE].astype(np.float64)
    s_small = s_arr[::COARSE_DOWNSAMPLE, ::COARSE_DOWNSAMPLE].astype(np.float64)

    if m_small.size < 16 or s_small.size < 16:
        return 0.0, 0.0, 0.0

    # Log-intensity
    m_small[m_small <= 0] = 1e-6
    s_small[s_small <= 0] = 1e-6
    m_small = np.log10(m_small)
    s_small = np.log10(s_small)

    # Normalize
    m_small = (m_small - np.nanmean(m_small)) / (np.nanstd(m_small) + 1e-8)
    s_small = (s_small - np.nanmean(s_small)) / (np.nanstd(s_small) + 1e-8)

    # Phase correlation
    f1 = fft.fft2(m_small)
    f2 = fft.fft2(s_small)
    cross = f1 * np.conj(f2)
    cross_norm = cross / (np.abs(cross) + 1e-10)
    corr = np.abs(fft.ifft2(cross_norm))
    corr = fft.fftshift(corr)

    peak_idx = np.unravel_index(np.argmax(corr), corr.shape)
    peak_val = float(corr[peak_idx])
    cy_shift, cx_shift = peak_idx
    h, w = corr.shape
    dy_coarse = (cy_shift - h // 2) * COARSE_DOWNSAMPLE
    dx_coarse = (cx_shift - w // 2) * COARSE_DOWNSAMPLE

    return float(dy_coarse), float(dx_coarse), peak_val


def _estimate_local_shift_phasecorr(
    master_ds: gdal.Dataset,
    slave_ds: gdal.Dataset,
    row: int,
    col: int,
    coarse_dr: int = 0,
    coarse_dc: int = 0,
    window_size: int = STABLE_PHASECORR_WIN,
) -> tuple[float, float, float] | None:
    """Local phase-correlation refinement around a coarse shift."""
    from scipy import fft

    half = window_size // 2
    m_win = _read_window(master_ds, row, col, window_size)
    s_win = _read_window(slave_ds, row + coarse_dr, col + coarse_dc, window_size)

    if m_win is None or s_win is None:
        return None
    if m_win.shape != (window_size, window_size) or s_win.shape != (window_size, window_size):
        return None

    f1 = fft.fft2(m_win)
    f2 = fft.fft2(s_win)
    cross = f1 * np.conj(f2)
    cross_norm = cross / (np.abs(cross) + 1e-10)
    corr = np.abs(fft.ifft2(cross_norm))
    corr = fft.fftshift(corr)

    peak_idx = np.unravel_index(np.argmax(corr), corr.shape)
    peak_val = float(corr[peak_idx] / (window_size * window_size))
    cy_shift, cx_shift = peak_idx
    h, w = corr.shape
    dy_local = cy_shift - h // 2
    dx_local = cx_shift - w // 2

    # Total shift in pixels
    dr_total = coarse_dr + dy_local
    dc_total = coarse_dc + dx_local

    return float(dr_total), float(dc_total), peak_val


def _glacier_sample_points(
    master_ds: gdal.Dataset,
    glacier_poly,
    glacier_bounds,
    bbox_buffer_deg: float = 0.10,
    step_px: int = GLACIER_SAMPLE_STEP_PX,
) -> list[tuple[int, int, float, float]]:
    """
    Sample points within the glacier outline to compute Vindex.
    Returns list of (row, col, lon, lat).
    """
    minx, miny, maxx, maxy = glacier_bounds
    minx -= bbox_buffer_deg
    miny -= bbox_buffer_deg
    maxx += bbox_buffer_deg
    maxy += bbox_buffer_deg

    gt = master_ds.GetGeoTransform()
    if gt is None:
        raise RuntimeError("Missing geotransform.")

    def lonlat_to_rowcol(lon: float, lat: float) -> tuple[int, int]:
        col = int((lon - gt[0]) / gt[1])
        row = int((lat - gt[3]) / gt[5])
        return row, col

    def rowcol_to_lonlat(row: int, col: int) -> tuple[float, float]:
        lon = gt[0] + col * gt[1] + row * gt[2]
        lat = gt[3] + col * gt[4] + row * gt[5]
        return float(lon), float(lat)

    r_min, c_min = lonlat_to_rowcol(minx, maxy)
    r_max, c_max = lonlat_to_rowcol(maxx, miny)
    r0 = max(0, min(r_min, r_max))
    r1 = min(master_ds.RasterYSize - 1, max(r_min, r_max))
    c0 = max(0, min(c_min, c_max))
    c1 = min(master_ds.RasterXSize - 1, max(c_min, c_max))

    pts: list[tuple[int, int, float, float]] = []
    for r in range(r0, r1, step_px):
        for c in range(c0, c1, step_px):
            lon, lat = rowcol_to_lonlat(r, c)
            if glacier_poly.covers(Point(lon, lat)):
                pts.append((r, c, float(lon), float(lat)))
    return pts


def _stable_sample_points(
    master_ds: gdal.Dataset,
    glacier_poly,
    glacier_bounds,
    stable_mask_poly=None,
    bbox_buffer_deg: float = STABLE_BBOX_BUFFER_DEG,
    exclude_buffer_deg: float = GLACIER_EXCLUDE_BUFFER_DEG,
    step_px: int = SAMPLE_STEP_PX,
) -> list[tuple[int, int, float, float]]:
    """
    Sample stable-ground points for bias estimation.
    If stable_mask_poly is provided: sample only within the mask.
    Otherwise: sample around glacier, excluding the glacier itself.
    """
    minx, miny, maxx, maxy = glacier_bounds
    minx -= bbox_buffer_deg
    miny -= bbox_buffer_deg
    maxx += bbox_buffer_deg
    maxy += bbox_buffer_deg

    gt = master_ds.GetGeoTransform()
    if gt is None:
        raise RuntimeError("Missing geotransform.")

    def lonlat_to_rowcol(lon: float, lat: float) -> tuple[int, int]:
        col = int((lon - gt[0]) / gt[1])
        row = int((lat - gt[3]) / gt[5])
        return row, col

    def rowcol_to_lonlat(row: int, col: int) -> tuple[float, float]:
        lon = gt[0] + col * gt[1] + row * gt[2]
        lat = gt[3] + col * gt[4] + row * gt[5]
        return float(lon), float(lat)

    r_min, c_min = lonlat_to_rowcol(minx, maxy)
    r_max, c_max = lonlat_to_rowcol(maxx, miny)
    r0 = max(0, min(r_min, r_max))
    r1 = min(master_ds.RasterYSize - 1, max(r_min, r_max))
    c0 = max(0, min(c_min, c_max))
    c1 = min(master_ds.RasterXSize - 1, max(c_min, c_max))

    poly_excl = glacier_poly.buffer(exclude_buffer_deg)

    pts: list[tuple[int, int, float, float]] = []
    for r in range(r0, r1, step_px):
        for c in range(c0, c1, step_px):
            lon, lat = rowcol_to_lonlat(r, c)
            p = Point(lon, lat)
            if stable_mask_poly is not None and not stable_mask_poly.covers(p):
                continue
            if poly_excl.contains(p):
                continue
            pts.append((r, c, float(lon), float(lat)))
    return pts


def _compute_glacier_fraction_raster(
    glacier_poly,
    gt,
    raster_shape: tuple[int, int],
) -> np.ndarray:
    """
    Rasterize glacier polygon onto the same grid as the velocity raster.
    Returns a binary mask (1=glacier, 0=not glacier).
    """
    from osgeo import ogr
    driver = ogr.GetDriverByName('Memory')
    ds = driver.CreateDataSource('memData')
    srs = ogr.osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    layer = ds.CreateLayer('glacier', srs, ogr.wkbPolygon)

    from shapely import wkt
    wkt_str = glacier_poly.wkt
    geom = ogr.CreateGeometryFromWkt(wkt_str)
    feat = ogr.Feature(layer.GetLayerDefn())
    feat.SetGeometry(geom)
    layer.CreateFeature(feat)

    # Create target raster
    mem_driver = gdal.GetDriverByName('MEM')
    target_ds = mem_driver.Create('', raster_shape[1], raster_shape[0], 1, gdal.GDT_Byte)
    target_ds.SetGeoTransform(gt)
    target_ds.SetProjection(srs.ExportToWkt())

    # Rasterize
    gdal.RasterizeLayer(target_ds, [1], layer, burn_values=[1])

    mask = target_ds.ReadAsArray()
    target_ds = None
    ds = None
    return mask


def _compute_template_glacier_fraction(
    glacier_mask: np.ndarray,
    row: int,
    col: int,
    window_size: int,
) -> float:
    """
    Compute fraction of template window that overlaps with glacier.
    glacier_mask: binary raster (1=glacier, 0=not)
    Returns: fraction in [0, 1]
    """
    half = window_size // 2
    h, w = glacier_mask.shape
    
    r0 = max(0, row - half)
    r1 = min(h, row + half)
    c0 = max(0, col - half)
    c1 = min(w, col + half)
    
    if r1 <= r0 or c1 <= c0:
        return 0.0
    
    template_region = glacier_mask[r0:r1, c0:c1]
    n_glacier = np.sum(template_region)
    n_total = template_region.size
    
    return float(n_glacier / n_total) if n_total > 0 else 0.0


def create_omega_masks(glacier_poly):
    """
    Create fixed analysis regions (Omega) using negative buffers on the glacier outline.
    
    Returns dict: {'base': poly, 'narrow': poly, 'wide': poly}
    
    - Wide: ~10m erosion (-0.0001 deg)
    - Base: ~30m erosion (-0.0003 deg) [Primary Ω, default]
    - Narrow: ~50m erosion (-0.0005 deg)
    """
    wide = glacier_poly.buffer(OMEGA_EROSION_WIDE_DEG)
    base = glacier_poly.buffer(OMEGA_EROSION_BASE_DEG)
    narrow = glacier_poly.buffer(OMEGA_EROSION_NARROW_DEG)
    
    print(f"  Ω areas (deg²): Wide={wide.area:.8f}, Base={base.area:.8f}, Narrow={narrow.area:.8f}", flush=True)
    if base.is_empty:
        print("  ⚠️  WARNING: Base Ω is empty! Erosion too large?", flush=True)
    
    return {
        'wide': wide,
        'base': base,
        'narrow': narrow
    }


def process_pair_with_glacier_fraction(
    date1: str,
    date2: str,
    tc_path1: Path,
    tc_path2: Path,
    dt_days: float,
    glacier_poly,
    glacier_bounds,
    glacier_mask: np.ndarray,
    omega_masks: dict,
    window_size: int,
    glacier_fraction_threshold: float,
) -> dict:
    """
    Process one pair with stable-ground debiasing and glacier-fraction filtering.
    
    Returns dict with:
    - Stable-ground bias (E/N mean + plane)
    - NMAD uncertainty
    - Vindex (omega_base, omega_narrow, omega_wide) with glacier-fraction filtering
    - QC metrics: glacier fraction statistics, valid counts
    """
    print(f"\n{'='*60}")
    print(f"Processing {date1} → {date2} (window={window_size} px, glacier_frac≥{glacier_fraction_threshold:.0%})")
    print(f"{'='*60}")
    
    mst = _open_sigma0_band(tc_path1)
    slv = _open_sigma0_band(tc_path2)
    
    gt = mst.GetGeoTransform()
    px_x_m = abs(gt[1] * 111320 * np.cos(np.radians(GLACIER_LAT)))
    px_y_m = abs(gt[5] * 111320)
    
    # Step 1: Stable-ground sampling and bias estimation
    with fiona.open(STABLE_GROUND_MASK_SHP) as mask_src:
        mask_geoms = [shape(f["geometry"]) for f in mask_src]
    stable_mask_poly = unary_union(mask_geoms) if mask_geoms else None
    
    stable_pts = _stable_sample_points(mst, glacier_poly, glacier_bounds, stable_mask_poly)
    print(f"  Stable-ground sample points: {len(stable_pts)}")
    
    # Coarse global shift
    dr0, dc0, pc_response = _estimate_global_shift_phasecorr(mst, slv, glacier_bounds)
    print(f"  Global shift: dr={dr0:.1f}, dc={dc0:.1f} px (phase-corr response={pc_response:.4f})")
    
    # Stable-ground offsets
    n_total = len(stable_pts)
    rows = np.zeros(n_total, dtype=np.int32)
    cols = np.zeros(n_total, dtype=np.int32)
    dxs = np.full(n_total, np.nan, dtype=np.float64)
    dys = np.full(n_total, np.nan, dtype=np.float64)
    corrs = np.full(n_total, np.nan, dtype=np.float64)
    
    for i, (r, c, lon, lat) in enumerate(stable_pts):
        rows[i] = r
        cols[i] = c
        m = _estimate_local_shift_phasecorr(mst, slv, r, c, int(dr0), int(dc0), window_size=window_size)
        if m is not None:
            dr, dc, cor = m
            dxs[i] = dc * px_x_m
            dys[i] = dr * px_y_m
            corrs[i] = cor
    
    # Filter stable-ground matches
    cand = np.isfinite(dxs) & np.isfinite(dys) & (corrs >= MIN_CORR)
    n_success = int(np.sum(cand))
    
    # Check for saturation (large offsets at search limit)
    # Note: For stable ground, we expect near-zero motion. Large offsets indicate either:
    # 1) True saturation (glacier motion exceeded search range)
    # 2) Matching failure
    # We use a conservative threshold: 5x the window size in meters
    SAT_THRESH_M = window_size * px_x_m * 5.0
    disp_m = np.sqrt(dxs**2 + dys**2)
    sat = disp_m > SAT_THRESH_M
    sat_frac = float(np.sum(sat & np.isfinite(dxs)) / n_total) if n_total > 0 else 0.0
    
    # For stable ground, high saturation fraction indicates systematic failure
    # But we're more lenient here because we're using phase correlation (not SNAP correlation)
    if n_success < MIN_VALID_STABLE_MATCHES or sat_frac > 0.5:
        return {
            "date1": date1,
            "date2": date2,
            "window_size_px": window_size,
            "glacier_fraction_threshold": glacier_fraction_threshold,
            "time_delta_days": float(dt_days),
            "n_stable_total": int(n_total),
            "n_stable_success": int(n_success),
            "stable_saturated_fraction": sat_frac,
            "stable_ground_status": "insufficient_or_saturated",
            "bias_mean_E_m_per_day": np.nan,
            "bias_mean_N_m_per_day": np.nan,
            "resid_nmad_E_m": np.nan,
            "resid_nmad_N_m": np.nan,
            "vindex_omega_base_m_per_day": np.nan,
            "vindex_omega_narrow_m_per_day": np.nan,
            "vindex_omega_wide_m_per_day": np.nan,
            "vindex_sigma_m_per_day": np.nan,
            "vindex_sample_n_omega_base": 0,
            "vindex_sample_n_passing_glacier_fraction": 0,
            "vindex_corr_median": np.nan,
            "omega_valid_fraction": 0.0,
            "glacier_fraction_median": np.nan,
            "glacier_fraction_mean": np.nan,
        }
    
    # Fit plane to stable-ground offsets
    corr_cand = corrs[cand]
    thr = float(max(MIN_CORR, np.nanpercentile(corr_cand, 60)))
    good = cand & (corrs >= thr)
    if np.sum(good) < MIN_VALID_STABLE_MATCHES:
        idx_cand = np.where(cand)[0]
        order = idx_cand[np.argsort(corrs[idx_cand])[::-1]]
        keep = order[:MIN_VALID_STABLE_MATCHES]
        good = np.zeros_like(cand, dtype=bool)
        good[keep] = True
    
    n_valid = int(np.sum(good))
    col_mean = float(np.nanmean(cols[good]))
    row_mean = float(np.nanmean(rows[good]))
    x = cols[good] - col_mean
    y = rows[good] - row_mean
    
    mean_dx = float(np.nanmean(dxs[good]))
    mean_dy = float(np.nanmean(dys[good]))
    
    plane_dx = _fit_plane(dxs[good], x, y)
    plane_dy = _fit_plane(dys[good], x, y)
    
    dx_pred = plane_dx.predict(x, y)
    dy_pred = plane_dy.predict(x, y)
    dx_res = dxs[good] - dx_pred
    dy_res = dys[good] - dy_pred
    
    nmad_dx = _nmad(dx_res)
    nmad_dy = _nmad(dy_res)
    
    # Conservative uncertainty for speed
    sigma_v_m_per_day = float(np.sqrt(nmad_dx**2 + nmad_dy**2) / dt_days)
    
    print(f"  Stable-ground: {n_valid} valid, bias=({mean_dx/dt_days:.2f}, {mean_dy/dt_days:.2f}) m/d, NMAD={nmad_dx:.2f}/{nmad_dy:.2f} m")
    
    # Step 2: Glacier sampling with glacier-fraction filtering
    omega_wide = omega_masks['wide']
    omega_base = omega_masks['base']
    omega_narrow = omega_masks['narrow']
    
    glacier_pts = _glacier_sample_points(mst, glacier_poly, glacier_bounds, step_px=GLACIER_SAMPLE_STEP_PX)
    print(f"  Glacier sample points (before filtering): {len(glacier_pts)}")
    
    # Lists for omega_base (primary)
    base_speeds_db = []
    base_corrs = []
    base_glacier_fractions = []
    
    # Sensitivity variants
    wide_speeds_db = []
    narrow_speeds_db = []
    
    base_total_possible = 0
    n_rejected_glacier_fraction = 0
    n_rejected_low_corr = 0
    
    for (r, c, lon, lat) in glacier_pts:
        p_geom = Point(lon, lat)
        in_wide = omega_wide.covers(p_geom)
        in_base = omega_base.covers(p_geom)
        in_narrow = omega_narrow.covers(p_geom)
        
        if not in_wide:
            continue
        
        if in_base:
            base_total_possible += 1
        
        # Compute glacier fraction for this template
        glac_frac = _compute_template_glacier_fraction(glacier_mask, r, c, window_size)
        
        # Apply glacier-fraction filter
        if glac_frac < glacier_fraction_threshold:
            n_rejected_glacier_fraction += 1
            continue
        
        # Match with local phase correlation
        m = _estimate_local_shift_phasecorr(mst, slv, r, c, int(dr0), int(dc0), window_size=window_size)
        
        if m is None:
            continue
        
        dr, dc, cor = m
        
        if cor < GLACIER_MIN_CORR:
            n_rejected_low_corr += 1
            continue
        
        dx_m = dc * px_x_m
        dy_m = dr * px_y_m
        
        # De-bias
        bx = float(c - col_mean)
        by = float(r - row_mean)
        bE = float(plane_dx.predict(np.asarray([bx]), np.asarray([by]))[0])
        bN = float(plane_dy.predict(np.asarray([bx]), np.asarray([by]))[0])
        
        dx_db = float(dx_m - bE)
        dy_db = float(dy_m - bN)
        v_db = float(np.hypot(dx_db, dy_db) / dt_days)
        
        # Accumulate by omega region
        if in_wide:
            wide_speeds_db.append(v_db)
        if in_base:
            base_speeds_db.append(v_db)
            base_corrs.append(cor)
            base_glacier_fractions.append(glac_frac)
        if in_narrow:
            narrow_speeds_db.append(v_db)
    
    # Compute Vindex from omega_base (primary analysis region)
    if len(base_speeds_db) > 0:
        vindex_base = float(np.nanmedian(base_speeds_db))
        vindex_narrow = float(np.nanmedian(narrow_speeds_db)) if narrow_speeds_db else np.nan
        vindex_wide = float(np.nanmedian(wide_speeds_db)) if wide_speeds_db else np.nan
        vindex_corr_median = float(np.nanmedian(base_corrs))
        vindex_n = int(len(base_speeds_db))
        omega_valid_frac = float(vindex_n / base_total_possible) if base_total_possible > 0 else 0.0
        glacier_frac_median = float(np.nanmedian(base_glacier_fractions))
        glacier_frac_mean = float(np.nanmean(base_glacier_fractions))
        status = "ok"
        print(f"  ✅ Vindex: {vindex_base:.1f} m/d ±{sigma_v_m_per_day:.1f} (n={vindex_n}, ω_valid_frac={omega_valid_frac:.2%})")
        print(f"     Glacier fraction: median={glacier_frac_median:.2%}, mean={glacier_frac_mean:.2%}")
        print(f"     Rejected: glacier_frac<{glacier_fraction_threshold:.0%} ({n_rejected_glacier_fraction}), low_corr ({n_rejected_low_corr})")
    else:
        vindex_base = np.nan
        vindex_narrow = np.nan
        vindex_wide = np.nan
        vindex_corr_median = np.nan
        vindex_n = 0
        omega_valid_frac = 0.0
        glacier_frac_median = np.nan
        glacier_frac_mean = np.nan
        status = "no_valid_glacier_matches"
        print(f"  ❌ No valid Vindex: all templates rejected")
    
    return {
        "date1": date1,
        "date2": date2,
        "window_size_px": window_size,
        "glacier_fraction_threshold": glacier_fraction_threshold,
        "time_delta_days": float(dt_days),
        "n_stable_total": int(n_total),
        "n_stable_success": int(n_success),
        "n_stable_valid": int(n_valid),
        "stable_saturated_fraction": sat_frac,
        "stable_ground_status": status,
        "bias_mean_E_m_per_day": mean_dx / dt_days,
        "bias_mean_N_m_per_day": mean_dy / dt_days,
        "resid_nmad_E_m": nmad_dx,
        "resid_nmad_N_m": nmad_dy,
        "vindex_omega_base_m_per_day": vindex_base,
        "vindex_omega_narrow_m_per_day": vindex_narrow,
        "vindex_omega_wide_m_per_day": vindex_wide,
        "vindex_sigma_m_per_day": sigma_v_m_per_day,
        "vindex_sample_n_omega_base": vindex_n,
        "vindex_sample_n_passing_glacier_fraction": vindex_n,
        "vindex_corr_median": vindex_corr_median,
        "omega_valid_fraction": omega_valid_frac,
        "glacier_fraction_median": glacier_frac_median,
        "glacier_fraction_mean": glacier_frac_mean,
        "n_rejected_glacier_fraction": n_rejected_glacier_fraction,
        "n_rejected_low_corr": n_rejected_low_corr,
    }


def main():
    parser = argparse.ArgumentParser(description="Window + Glacier-Fraction Sensitivity for Vindex")
    parser.add_argument("--window_px", type=int, required=True, choices=[32, 64, 128], help="Template window size (pixels)")
    parser.add_argument("--glacier_fraction", type=float, default=0.7, help="Minimum glacier fraction (0.0-1.0)")
    args = parser.parse_args()
    
    WINDOW_SIZE = args.window_px
    GLACIER_FRACTION_THRESHOLD = args.glacier_fraction
    
    print(f"\n{'='*70}")
    print(f"WINDOW + GLACIER-FRACTION SENSITIVITY")
    print(f"Window size: {WINDOW_SIZE} px")
    print(f"Glacier fraction threshold: {GLACIER_FRACTION_THRESHOLD:.0%}")
    print(f"{'='*70}\n")
    
    # Load glacier outline
    with fiona.open(GLACIER_OUTLINE_SHP) as src:
        glacier_geoms = [shape(f["geometry"]) for f in src]
    glacier_poly = unary_union(glacier_geoms)
    glacier_bounds = glacier_poly.bounds
    print(f"Glacier bounds: {glacier_bounds}")
    
    # Create fixed Omega masks (eroded glacier outline)
    omega_masks = create_omega_masks(glacier_poly)
    
    # Load velocity time series to get pair list
    df_ts = pd.read_csv(VELOCITY_TS_FILE)
    pairs = df_ts[["date1", "date2"]].drop_duplicates().values.tolist()
    print(f"Total pairs: {len(pairs)}\n")
    
    # Find TC products
    tc_map = _find_tc_products()
    
    # Rasterize glacier mask once (use first image as reference grid)
    first_date = pairs[0][0]
    if first_date not in tc_map:
        raise RuntimeError(f"TC product for {first_date} not found")
    
    ref_ds = _open_sigma0_band(tc_map[first_date])
    ref_gt = ref_ds.GetGeoTransform()
    ref_shape = (ref_ds.RasterYSize, ref_ds.RasterXSize)
    print(f"Rasterizing glacier mask (shape={ref_shape})...")
    glacier_mask = _compute_glacier_fraction_raster(glacier_poly, ref_gt, ref_shape)
    print(f"  Glacier mask: {np.sum(glacier_mask)} pixels = glacier\n")
    
    # Process all pairs
    results = []
    for date1, date2 in pairs:
        if date1 not in tc_map or date2 not in tc_map:
            print(f"⚠️  Skipping {date1}→{date2}: TC product missing")
            continue
        
        d1 = datetime.strptime(date1, "%Y-%m-%d")
        d2 = datetime.strptime(date2, "%Y-%m-%d")
        dt_days = (d2 - d1).days
        
        try:
            res = process_pair_with_glacier_fraction(
                date1, date2,
                tc_map[date1], tc_map[date2],
                dt_days,
                glacier_poly, glacier_bounds,
                glacier_mask,
                omega_masks,
                window_size=WINDOW_SIZE,
                glacier_fraction_threshold=GLACIER_FRACTION_THRESHOLD,
            )
            results.append(res)
        except Exception as e:
            print(f"❌ Error processing {date1}→{date2}: {e}")
            import traceback
            traceback.print_exc()
    
    # Save results
    df = pd.DataFrame(results)
    output_dir = OUTPUT_BASE_DIR / f"window_{WINDOW_SIZE}px_glacfrac_{int(GLACIER_FRACTION_THRESHOLD*100)}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    csv_out = output_dir / "vindex_stats.csv"
    df.to_csv(csv_out, index=False)
    print(f"\n✅ Saved: {csv_out}")
    
    # Quick summary
    print(f"\n{'='*70}")
    print(f"SUMMARY (window={WINDOW_SIZE}px, glacier_frac≥{GLACIER_FRACTION_THRESHOLD:.0%})")
    print(f"{'='*70}")
    print(f"Total pairs processed: {len(results)}")
    ok = df["stable_ground_status"] == "ok"
    print(f"Pairs with valid Vindex: {ok.sum()}")
    if ok.sum() > 0:
        print(f"Vindex range: {df.loc[ok, 'vindex_omega_base_m_per_day'].min():.1f} – {df.loc[ok, 'vindex_omega_base_m_per_day'].max():.1f} m/d")
        print(f"Median glacier fraction: {df.loc[ok, 'glacier_fraction_median'].median():.2%}")
        print(f"Mean rejected (glacier frac): {df.loc[ok, 'n_rejected_glacier_fraction'].mean():.0f}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
