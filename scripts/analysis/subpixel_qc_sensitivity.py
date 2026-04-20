#!/usr/bin/env python3
"""
Sub-pixel Refinement + QC Threshold Sensitivity Analysis

Purpose: Address reviewer questions:
1. Are offsets integer or sub-pixel? 
2. What does enhanced sub-pixel refinement change?
3. Are conclusions robust to stricter QC thresholds (corr ≥ 0.5, 0.6)?

Approach:
- Compare current sub-pixel (phase correlation) vs enhanced (parabolic interpolation)
- Test QC thresholds: 0.3 (legacy), 0.5 (primary), 0.6 (strict)
- Report impact on Vindex, NMAD, and time-series structure

Outputs:
- CSV: subpixel_comparison.csv (per-pair comparison)
- CSV: qc_threshold_sensitivity.csv (Vindex under different QC)
- Figure: vindex_subpixel_comparison.pdf
- Figure: qc_threshold_sensitivity.pdf
- Table: LaTeX tables for manuscript
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
import warnings

from osgeo import gdal
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates

try:
    import fiona
    from shapely.geometry import shape, Point
    from shapely.ops import unary_union
except Exception as e:
    raise RuntimeError("Missing GIS dependencies (fiona/shapely).") from e

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------
GLACIER_LAT = 38.97
GLACIER_LON = 70.75
PROCESSED_DIR = Path("satellite_data/sentinel1/processed")
GLACIER_OUTLINE_SHP = Path("satellite_data/dem/processed/didal_glacier_rgi_outline.shp")
STABLE_GROUND_MASK_SHP = Path("stable_ground_mask.shp")
OUTPUT_DIR = Path("processed_data/subpixel_qc_sensitivity")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Template matching parameters
WINDOW_SIZE = 128
STABLE_PHASECORR_WIN = 256
COARSE_WIN_SIZE = 2048
COARSE_DOWNSAMPLE = 8
LOCAL_SEARCH_RANGE = 120

# Sampling parameters
STABLE_BBOX_BUFFER_DEG = 0.20
GLACIER_EXCLUDE_BUFFER_DEG = 0.002
SAMPLE_STEP_PX = 100
GLACIER_SAMPLE_STEP_PX = 1
MIN_VALID_STABLE_MATCHES = 80

# QC thresholds to test
QC_THRESHOLDS = [0.3, 0.5, 0.6]
PRIMARY_QC_THRESHOLD = 0.5

# Omega erosion (fixed)
OMEGA_EROSION_BASE_DEG = -0.0003


@dataclass
class BiasModel:
    a: float
    b: float
    c: float

    def predict(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        return self.a + self.b * x + self.c * y


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


def _read_window(ds: gdal.Dataset, row: int, col: int, height: int, width: int = None) -> np.ndarray | None:
    """Read and preprocess a window from GDAL dataset (log-intensity, high-pass, normalize)."""
    if width is None:
        width = height
    band = ds.GetRasterBand(1)
    if band is None:
        return None
    half_h = height // 2
    half_w = width // 2
    try:
        arr = band.ReadAsArray(col - half_w, row - half_h, width, height)
        if arr is None or arr.size == 0:
            return None
    except Exception:
        return None

    arr = arr.astype(np.float64)
    arr[arr <= 0] = 1e-6
    arr = np.log10(arr)

    # High-pass filter
    kernel_size = max(5, height // 16)
    if kernel_size % 2 == 0:
        kernel_size += 1
    from scipy.ndimage import uniform_filter
    low_freq = uniform_filter(arr, size=kernel_size)
    arr = arr - low_freq

    # Normalize
    arr = (arr - np.nanmean(arr)) / (np.nanstd(arr) + 1e-8)
    return arr


def _parabolic_subpixel_2d(corr_surface: np.ndarray, peak_y: int, peak_x: int) -> tuple[float, float]:
    """
    2D parabolic sub-pixel refinement around a correlation peak.
    
    Fits a 2D quadratic surface to the 3x3 neighborhood around (peak_y, peak_x)
    and estimates the sub-pixel peak location.
    
    Returns: (dy_subpixel, dx_subpixel) relative to integer peak
    """
    h, w = corr_surface.shape
    
    # Boundary check
    if peak_y <= 0 or peak_y >= h - 1 or peak_x <= 0 or peak_x >= w - 1:
        return 0.0, 0.0
    
    # Extract 3x3 neighborhood
    c = corr_surface[peak_y - 1:peak_y + 2, peak_x - 1:peak_x + 2]
    if c.shape != (3, 3):
        return 0.0, 0.0
    
    # Parabolic fit in X direction (using center row)
    c_left = float(c[1, 0])
    c_center = float(c[1, 1])
    c_right = float(c[1, 2])
    denom_x = 2 * (2 * c_center - c_left - c_right)
    dx = (c_left - c_right) / denom_x if abs(denom_x) > 1e-9 else 0.0
    
    # Parabolic fit in Y direction (using center column)
    c_top = float(c[0, 1])
    c_center = float(c[1, 1])
    c_bottom = float(c[2, 1])
    denom_y = 2 * (2 * c_center - c_top - c_bottom)
    dy = (c_top - c_bottom) / denom_y if abs(denom_y) > 1e-9 else 0.0
    
    # Clamp to ±0.5 px (physically reasonable)
    dx = np.clip(dx, -0.5, 0.5)
    dy = np.clip(dy, -0.5, 0.5)
    
    return float(dy), float(dx)


def _estimate_shift_with_parabolic_refinement(
    master_ds: gdal.Dataset,
    slave_ds: gdal.Dataset,
    center_row: int,
    center_col: int,
    slave_center_row: int,
    slave_center_col: int,
    win_size: int = STABLE_PHASECORR_WIN,
) -> tuple[float, float, float, float, float] | None:
    """
    Estimate shift using phase correlation + parabolic sub-pixel refinement.
    
    Returns: (dr_integer, dc_integer, dr_subpixel, dc_subpixel, response) or None
    """
    import cv2
    from scipy import fft

    a = _read_window(master_ds, center_row, center_col, win_size, win_size)
    b = _read_window(slave_ds, slave_center_row, slave_center_col, win_size, win_size)
    if a is None or b is None:
        return None

    # Phase correlation (gives sub-pixel via OpenCV)
    a_f32 = a.astype(np.float32)
    b_f32 = b.astype(np.float32)
    win = cv2.createHanningWindow((a_f32.shape[1], a_f32.shape[0]), cv2.CV_32F)
    (shift_x_cv, shift_y_cv), response_cv = cv2.phaseCorrelate(a_f32 * win, b_f32 * win)
    
    # Also compute correlation surface explicitly for parabolic refinement
    f1 = fft.fft2(a)
    f2 = fft.fft2(b)
    cross = f1 * np.conj(f2)
    cross_norm = cross / (np.abs(cross) + 1e-10)
    corr = np.real(fft.ifft2(cross_norm))
    corr = fft.fftshift(corr)
    
    # Find integer peak
    peak_idx = np.unravel_index(np.argmax(corr), corr.shape)
    peak_y, peak_x = peak_idx
    h, w = corr.shape
    
    # Integer shift
    dy_int = peak_y - h // 2
    dx_int = peak_x - w // 2
    
    # Parabolic sub-pixel refinement
    dy_sub, dx_sub = _parabolic_subpixel_2d(corr, peak_y, peak_x)
    
    # Enhanced sub-pixel shift
    dr_subpixel = dy_int + dy_sub
    dc_subpixel = dx_int + dx_sub
    
    return float(dy_int), float(dx_int), float(dr_subpixel), float(dc_subpixel), float(response_cv)


def fmt_day_mon_en(x, pos):
    """Format date as 'DD Mon' in English (locale-independent)."""
    d = mdates.num2date(x)
    months_en = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    return f"{d.day:02d} {months_en[d.month]}"


def process_pair_subpixel_comparison(
    date1: str,
    date2: str,
    tc_path1: Path,
    tc_path2: Path,
    dt_days: float,
    glacier_poly,
    glacier_bounds,
    stable_mask_poly,
    omega_base,
    qc_threshold: float = 0.5,
) -> dict:
    """
    Process one pair with both integer-rounded and enhanced sub-pixel refinement.
    
    Returns dict with:
    - Integer-rounded stable-ground stats
    - Enhanced sub-pixel stable-ground stats
    - Comparison metrics (% improvement in NMAD, Vindex difference)
    - Results for each QC threshold
    """
    print(f"\n{'='*60}")
    print(f"Processing {date1} → {date2} (QC corr≥{qc_threshold:.1f})")
    print(f"{'='*60}")
    
    mst = _open_sigma0_band(tc_path1)
    slv = _open_sigma0_band(tc_path2)
    
    gt = mst.GetGeoTransform()
    px_x_m = abs(gt[1] * 111320 * np.cos(np.radians(GLACIER_LAT)))
    px_y_m = abs(gt[5] * 111320)
    
    # Step 1: Stable-ground sampling
    stable_pts = _stable_sample_points(mst, glacier_poly, glacier_bounds, stable_mask_poly)
    print(f"  Stable-ground sample points: {len(stable_pts)}")
    
    # Coarse global shift (integer-rounded for initial search)
    dr0, dc0, pc_response = _estimate_global_shift_phasecorr(mst, slv, glacier_bounds)
    print(f"  Global shift: dr={dr0:.1f}, dc={dc0:.1f} px")
    
    # Collect offsets with BOTH integer and enhanced sub-pixel
    n_total = len(stable_pts)
    rows = np.zeros(n_total, dtype=np.int32)
    cols = np.zeros(n_total, dtype=np.int32)
    
    # Integer-rounded offsets (current baseline)
    dxs_int = np.full(n_total, np.nan, dtype=np.float64)
    dys_int = np.full(n_total, np.nan, dtype=np.float64)
    corrs_int = np.full(n_total, np.nan, dtype=np.float64)
    
    # Enhanced sub-pixel offsets (with parabolic refinement)
    dxs_sub = np.full(n_total, np.nan, dtype=np.float64)
    dys_sub = np.full(n_total, np.nan, dtype=np.float64)
    corrs_sub = np.full(n_total, np.nan, dtype=np.float64)
    
    for i, (r, c, lon, lat) in enumerate(stable_pts):
        rows[i] = r
        cols[i] = c
        
        # Get both integer and enhanced sub-pixel
        result = _estimate_shift_with_parabolic_refinement(
            mst, slv, r, c,
            r + int(dr0), c + int(dc0),
            win_size=STABLE_PHASECORR_WIN
        )
        
        if result is not None:
            dy_int, dx_int, dy_sub_full, dx_sub_full, resp = result
            
            # Integer version (round to nearest integer pixel)
            dxs_int[i] = round(dx_int) * px_x_m
            dys_int[i] = round(dy_int) * px_y_m
            corrs_int[i] = resp
            
            # Enhanced sub-pixel version
            dxs_sub[i] = dx_sub_full * px_x_m
            dys_sub[i] = dy_sub_full * px_y_m
            corrs_sub[i] = resp
    
    # Quality filter
    cand_int = np.isfinite(dxs_int) & np.isfinite(dys_int) & (corrs_int >= qc_threshold)
    cand_sub = np.isfinite(dxs_sub) & np.isfinite(dys_sub) & (corrs_sub >= qc_threshold)
    
    n_valid_int = int(np.sum(cand_int))
    n_valid_sub = int(np.sum(cand_sub))
    
    if n_valid_int < MIN_VALID_STABLE_MATCHES or n_valid_sub < MIN_VALID_STABLE_MATCHES:
        return {
            "date1": date1,
            "date2": date2,
            "qc_threshold": qc_threshold,
            "time_delta_days": dt_days,
            "n_stable_valid_int": n_valid_int,
            "n_stable_valid_sub": n_valid_sub,
            "status": "insufficient_matches",
        }
    
    # Fit planar bias (integer version)
    good_int = cand_int
    col_mean = float(np.nanmean(cols[good_int]))
    row_mean = float(np.nanmean(rows[good_int]))
    x = cols[good_int] - col_mean
    y = rows[good_int] - row_mean
    
    plane_dx_int = _fit_plane(dxs_int[good_int], x, y)
    plane_dy_int = _fit_plane(dys_int[good_int], x, y)
    
    dx_pred_int = plane_dx_int.predict(x, y)
    dy_pred_int = plane_dy_int.predict(x, y)
    dx_res_int = dxs_int[good_int] - dx_pred_int
    dy_res_int = dys_int[good_int] - dy_pred_int
    
    nmad_dx_int = _nmad(dx_res_int)
    nmad_dy_int = _nmad(dy_res_int)
    nmad_total_int = float(np.sqrt(nmad_dx_int**2 + nmad_dy_int**2))
    
    # Fit planar bias (sub-pixel version)
    good_sub = cand_sub
    x_sub = cols[good_sub] - col_mean
    y_sub = rows[good_sub] - row_mean
    
    plane_dx_sub = _fit_plane(dxs_sub[good_sub], x_sub, y_sub)
    plane_dy_sub = _fit_plane(dys_sub[good_sub], x_sub, y_sub)
    
    dx_pred_sub = plane_dx_sub.predict(x_sub, y_sub)
    dy_pred_sub = plane_dy_sub.predict(x_sub, y_sub)
    dx_res_sub = dxs_sub[good_sub] - dx_pred_sub
    dy_res_sub = dys_sub[good_sub] - dy_pred_sub
    
    nmad_dx_sub = _nmad(dx_res_sub)
    nmad_dy_sub = _nmad(dy_res_sub)
    nmad_total_sub = float(np.sqrt(nmad_dx_sub**2 + nmad_dy_sub**2))
    
    # NMAD improvement
    nmad_improvement_pct = 100 * (nmad_total_int - nmad_total_sub) / nmad_total_int if nmad_total_int > 0 else 0.0
    
    print(f"  Integer NMAD: {nmad_total_int:.2f} m | Sub-pixel NMAD: {nmad_total_sub:.2f} m | Improvement: {nmad_improvement_pct:.1f}%")
    
    # Step 2: Glacier Vindex (using sub-pixel offsets with QC threshold)
    glacier_pts = _glacier_sample_points(mst, glacier_poly, glacier_bounds)
    
    base_speeds = []
    base_corrs = []
    
    for (r, c, lon, lat) in glacier_pts:
        p_geom = Point(lon, lat)
        if not omega_base.covers(p_geom):
            continue
        
        # Match with enhanced sub-pixel
        result = _estimate_shift_with_parabolic_refinement(
            mst, slv, r, c,
            r + int(dr0), c + int(dc0),
            win_size=STABLE_PHASECORR_WIN
        )
        
        if result is None:
            continue
        
        _, _, dy_sub, dx_sub, cor = result
        
        if cor < qc_threshold:
            continue
        
        dx_m = dx_sub * px_x_m
        dy_m = dy_sub * px_y_m
        
        # De-bias using sub-pixel plane
        bx = float(c - col_mean)
        by = float(r - row_mean)
        bE = float(plane_dx_sub.predict(np.asarray([bx]), np.asarray([by]))[0])
        bN = float(plane_dy_sub.predict(np.asarray([bx]), np.asarray([by]))[0])
        
        dx_db = float(dx_m - bE)
        dy_db = float(dy_m - bN)
        v_db = float(np.hypot(dx_db, dy_db) / dt_days)
        
        base_speeds.append(v_db)
        base_corrs.append(cor)
    
    # Compute Vindex
    if len(base_speeds) > 0:
        vindex = float(np.nanmedian(base_speeds))
        vindex_corr_median = float(np.nanmedian(base_corrs))
        vindex_n = len(base_speeds)
        sigma_v = nmad_total_sub / dt_days
        status = "ok"
        print(f"  ✅ Vindex: {vindex:.1f} m/d ±{sigma_v:.1f} (n={vindex_n}, corr_median={vindex_corr_median:.3f})")
    else:
        vindex = np.nan
        vindex_corr_median = np.nan
        vindex_n = 0
        sigma_v = np.nan
        status = "no_valid_glacier_matches"
        print(f"  ❌ No valid Vindex")
    
    return {
        "date1": date1,
        "date2": date2,
        "qc_threshold": qc_threshold,
        "time_delta_days": dt_days,
        "n_stable_valid_int": n_valid_int,
        "n_stable_valid_sub": n_valid_sub,
        "nmad_total_m_integer": nmad_total_int,
        "nmad_total_m_subpixel": nmad_total_sub,
        "nmad_improvement_pct": nmad_improvement_pct,
        "bias_mean_E_m_per_day_sub": plane_dx_sub.a / dt_days,
        "bias_mean_N_m_per_day_sub": plane_dy_sub.a / dt_days,
        "vindex_m_per_day": vindex,
        "vindex_sigma_m_per_day": sigma_v,
        "vindex_n": vindex_n,
        "vindex_corr_median": vindex_corr_median,
        "status": status,
    }


def _estimate_global_shift_phasecorr(master_ds, slave_ds, glacier_bounds):
    """Estimate coarse global shift."""
    import cv2
    minx, miny, maxx, maxy = glacier_bounds
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    
    gt = master_ds.GetGeoTransform()
    def lonlat_to_rowcol(lon, lat):
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
    except:
        return 0, 0, 0.0
    
    if m_arr is None or s_arr is None:
        return 0, 0, 0.0
    
    m_small = m_arr[::COARSE_DOWNSAMPLE, ::COARSE_DOWNSAMPLE].astype(np.float32)
    s_small = s_arr[::COARSE_DOWNSAMPLE, ::COARSE_DOWNSAMPLE].astype(np.float32)
    
    if m_small.size < 16 or s_small.size < 16:
        return 0, 0, 0.0
    
    m_small = np.maximum(m_small, 1e-6)
    s_small = np.maximum(s_small, 1e-6)
    m_small = 10.0 * np.log10(m_small)
    s_small = 10.0 * np.log10(s_small)
    
    m_small = (m_small - np.mean(m_small)) / (np.std(m_small) + 1e-8)
    s_small = (s_small - np.mean(s_small)) / (np.std(s_small) + 1e-8)
    
    m_small = m_small.astype(np.float32)
    s_small = s_small.astype(np.float32)
    win = cv2.createHanningWindow((m_small.shape[1], m_small.shape[0]), cv2.CV_32F)
    
    (shift_x, shift_y), response = cv2.phaseCorrelate(m_small * win, s_small * win)
    dc0 = int(round(shift_x * COARSE_DOWNSAMPLE))
    dr0 = int(round(shift_y * COARSE_DOWNSAMPLE))
    
    return dr0, dc0, float(response)


def _stable_sample_points(master_ds, glacier_poly, glacier_bounds, stable_mask_poly):
    """Sample stable-ground points."""
    minx, miny, maxx, maxy = glacier_bounds
    minx -= STABLE_BBOX_BUFFER_DEG
    miny -= STABLE_BBOX_BUFFER_DEG
    maxx += STABLE_BBOX_BUFFER_DEG
    maxy += STABLE_BBOX_BUFFER_DEG
    
    gt = master_ds.GetGeoTransform()
    def lonlat_to_rowcol(lon, lat):
        col = int((lon - gt[0]) / gt[1])
        row = int((lat - gt[3]) / gt[5])
        return row, col
    
    def rowcol_to_lonlat(row, col):
        lon = gt[0] + col * gt[1]
        lat = gt[3] + row * gt[5]
        return float(lon), float(lat)
    
    r_min, c_min = lonlat_to_rowcol(minx, maxy)
    r_max, c_max = lonlat_to_rowcol(maxx, miny)
    r0 = max(0, min(r_min, r_max))
    r1 = min(master_ds.RasterYSize - 1, max(r_min, r_max))
    c0 = max(0, min(c_min, c_max))
    c1 = min(master_ds.RasterXSize - 1, max(c_min, c_max))
    
    poly_excl = glacier_poly.buffer(GLACIER_EXCLUDE_BUFFER_DEG)
    
    pts = []
    for r in range(r0, r1, SAMPLE_STEP_PX):
        for c in range(c0, c1, SAMPLE_STEP_PX):
            lon, lat = rowcol_to_lonlat(r, c)
            p = Point(lon, lat)
            if stable_mask_poly is not None and not stable_mask_poly.covers(p):
                continue
            if poly_excl.contains(p):
                continue
            pts.append((r, c, float(lon), float(lat)))
    return pts


def _glacier_sample_points(master_ds, glacier_poly, glacier_bounds):
    """Sample glacier points."""
    minx, miny, maxx, maxy = glacier_bounds
    minx -= 0.10
    miny -= 0.10
    maxx += 0.10
    maxy += 0.10
    
    gt = master_ds.GetGeoTransform()
    def lonlat_to_rowcol(lon, lat):
        col = int((lon - gt[0]) / gt[1])
        row = int((lat - gt[3]) / gt[5])
        return row, col
    
    def rowcol_to_lonlat(row, col):
        lon = gt[0] + col * gt[1]
        lat = gt[3] + row * gt[5]
        return float(lon), float(lat)
    
    r_min, c_min = lonlat_to_rowcol(minx, maxy)
    r_max, c_max = lonlat_to_rowcol(maxx, miny)
    r0 = max(0, min(r_min, r_max))
    r1 = min(master_ds.RasterYSize - 1, max(r_min, r_max))
    c0 = max(0, min(c_min, c_max))
    c1 = min(master_ds.RasterXSize - 1, max(c_min, c_max))
    
    pts = []
    for r in range(r0, r1, GLACIER_SAMPLE_STEP_PX):
        for c in range(c0, c1, GLACIER_SAMPLE_STEP_PX):
            lon, lat = rowcol_to_lonlat(r, c)
            if glacier_poly.covers(Point(lon, lat)):
                pts.append((r, c, float(lon), float(lat)))
    return pts


def main():
    print(f"\n{'='*70}")
    print("SUB-PIXEL REFINEMENT + QC THRESHOLD SENSITIVITY")
    print(f"{'='*70}\n")
    
    # Load glacier outline
    with fiona.open(GLACIER_OUTLINE_SHP) as src:
        glacier_geoms = [shape(f["geometry"]) for f in src]
    glacier_poly = unary_union(glacier_geoms)
    glacier_bounds = glacier_poly.bounds
    
    # Load stable-ground mask
    with fiona.open(STABLE_GROUND_MASK_SHP) as src:
        mask_geoms = [shape(f["geometry"]) for f in src]
    stable_mask_poly = unary_union(mask_geoms) if mask_geoms else None
    
    # Create omega_base
    omega_base = glacier_poly.buffer(OMEGA_EROSION_BASE_DEG)
    
    # Load pair list from existing velocity TS
    df_ts = pd.read_csv(PROCESSED_DIR / "velocity_timeseries_python.csv")
    pairs = df_ts[["date1", "date2"]].drop_duplicates().values.tolist()
    
    # Find TC products
    tc_map = _find_tc_products()
    
    # Process all pairs for each QC threshold
    all_results = []
    
    for qc_thr in QC_THRESHOLDS:
        print(f"\n{'='*70}")
        print(f"QC THRESHOLD: corr ≥ {qc_thr:.1f}")
        print(f"{'='*70}")
        
        for date1, date2 in pairs:
            if date1 not in tc_map or date2 not in tc_map:
                continue
            
            d1 = datetime.strptime(date1, "%Y-%m-%d")
            d2 = datetime.strptime(date2, "%Y-%m-%d")
            dt_days = (d2 - d1).days
            
            try:
                res = process_pair_subpixel_comparison(
                    date1, date2,
                    tc_map[date1], tc_map[date2],
                    dt_days,
                    glacier_poly, glacier_bounds,
                    stable_mask_poly,
                    omega_base,
                    qc_threshold=qc_thr,
                )
                all_results.append(res)
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()
    
    # Save comprehensive results
    df_all = pd.DataFrame(all_results)
    csv_out = OUTPUT_DIR / "subpixel_qc_comprehensive.csv"
    df_all.to_csv(csv_out, index=False)
    print(f"\n✅ Saved: {csv_out}")
    
    # Generate summary tables
    generate_summary_tables(df_all)
    
    # Generate figures
    generate_figures(df_all)
    
    print(f"\n{'='*70}")
    print("✅ PART D COMPLETE")
    print(f"{'='*70}\n")


def generate_summary_tables(df: pd.DataFrame):
    """Generate LaTeX tables for manuscript."""
    print(f"\n{'='*70}")
    print("GENERATING SUMMARY TABLES")
    print(f"{'='*70}")
    
    # Table 1: Sub-pixel improvement (QC=0.5 only)
    df_primary = df[df["qc_threshold"] == PRIMARY_QC_THRESHOLD].copy()
    df_ok = df_primary[df_primary["status"] == "ok"]
    
    if len(df_ok) > 0:
        print("\n📊 Sub-pixel vs Integer Comparison (QC corr≥0.5):")
        print(df_ok[["date1", "date2", "nmad_total_m_integer", "nmad_total_m_subpixel", "nmad_improvement_pct"]].to_string(index=False))
        
        # Summary statistics
        median_improvement = df_ok["nmad_improvement_pct"].median()
        mean_nmad_int = df_ok["nmad_total_m_integer"].mean()
        mean_nmad_sub = df_ok["nmad_total_m_subpixel"].mean()
        
        print(f"\nSummary:")
        print(f"  Median NMAD improvement: {median_improvement:.1f}%")
        print(f"  Mean NMAD (integer): {mean_nmad_int:.2f} m")
        print(f"  Mean NMAD (sub-pixel): {mean_nmad_sub:.2f} m")
    
    # Table 2: QC threshold sensitivity
    print(f"\n{'='*70}")
    print("📊 QC Threshold Sensitivity:")
    print(f"{'='*70}")
    
    summary_rows = []
    for qc_thr in QC_THRESHOLDS:
        df_qc = df[df["qc_threshold"] == qc_thr]
        df_qc_ok = df_qc[df_qc["status"] == "ok"]
        
        if len(df_qc_ok) > 0:
            summary_rows.append({
                "QC_threshold": qc_thr,
                "n_pairs_valid": len(df_qc_ok),
                "median_corr": df_qc_ok["vindex_corr_median"].median(),
                "vindex_mean_m_per_day": df_qc_ok["vindex_m_per_day"].mean(),
                "vindex_std_m_per_day": df_qc_ok["vindex_m_per_day"].std(),
                "median_sigma_m_per_day": df_qc_ok["vindex_sigma_m_per_day"].median(),
            })
    
    df_qc_summary = pd.DataFrame(summary_rows)
    print(df_qc_summary.to_string(index=False))
    
    # Save tables
    csv_out = OUTPUT_DIR / "qc_threshold_sensitivity_summary.csv"
    df_qc_summary.to_csv(csv_out, index=False)
    print(f"\n✅ Saved: {csv_out}")
    
    # Generate LaTeX table
    latex_table = df_qc_summary.to_latex(
        index=False,
        float_format="%.2f",
        column_format="cccccc",
        caption="QC threshold sensitivity summary",
        label="tab:qc_sensitivity",
    )
    
    latex_out = OUTPUT_DIR / "qc_sensitivity_table.tex"
    with open(latex_out, "w") as f:
        f.write(latex_table)
    print(f"✅ Saved: {latex_out}")


def generate_figures(df: pd.DataFrame):
    """Generate comparison figures."""
    print(f"\n{'='*70}")
    print("GENERATING FIGURES")
    print(f"{'='*70}\n")
    
    # Figure 1: Sub-pixel improvement scatter
    df_primary = df[df["qc_threshold"] == PRIMARY_QC_THRESHOLD].copy()
    df_ok = df_primary[df_primary["status"] == "ok"]
    
    if len(df_ok) > 0:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        
        # Panel 1: NMAD comparison
        ax1.scatter(df_ok["nmad_total_m_integer"], df_ok["nmad_total_m_subpixel"], 
                    s=100, alpha=0.7, color='#2E86AB', edgecolors='black', linewidths=1)
        max_val = max(df_ok["nmad_total_m_integer"].max(), df_ok["nmad_total_m_subpixel"].max())
        ax1.plot([0, max_val], [0, max_val], 'k--', alpha=0.5, label='1:1 line')
        ax1.set_xlabel('NMAD (integer-rounded) [m]', fontsize=18)
        ax1.set_ylabel('NMAD (enhanced sub-pixel) [m]', fontsize=18)
        ax1.set_title('Stable-Ground Uncertainty: Integer vs Sub-pixel', fontsize=20, fontweight='normal')
        ax1.tick_params(axis='both', labelsize=16)
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.legend(fontsize=16, frameon=True, framealpha=0.95)
        
        # Panel 2: Improvement percentage
        df_ok_sorted = df_ok.sort_values("date1")
        dates = pd.to_datetime(df_ok_sorted["date1"])
        improvements = df_ok_sorted["nmad_improvement_pct"].values
        
        ax2.bar(dates, improvements, width=4, color='#A23B72', alpha=0.7, edgecolor='black', linewidth=1)
        ax2.axhline(0, color='k', linewidth=1, alpha=0.5)
        ax2.set_xlabel('Date', fontsize=18)
        ax2.set_ylabel('NMAD Improvement (%)', fontsize=18)
        ax2.set_title('Sub-pixel Refinement Improvement', fontsize=20, fontweight='normal')
        ax2.tick_params(axis='both', labelsize=16)
        ax2.xaxis.set_major_formatter(plt.FuncFormatter(fmt_day_mon_en))
        ax2.grid(True, alpha=0.3, linestyle='--', axis='y')
        
        plt.tight_layout()
        pdf_out = OUTPUT_DIR / "subpixel_improvement.pdf"
        png_out = OUTPUT_DIR / "subpixel_improvement.png"
        plt.savefig(pdf_out, dpi=300, bbox_inches='tight')
        plt.savefig(png_out, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✅ Saved: {pdf_out}")
    
    # Figure 2: QC threshold sensitivity (Vindex time series)
    fig, ax = plt.subplots(figsize=(12, 6))
    
    colors = {0.3: '#95A3A4', 0.5: '#2E86AB', 0.6: '#A23B72'}
    markers = {0.3: 'o', 0.5: 's', 0.6: '^'}
    
    for qc_thr in QC_THRESHOLDS:
        df_qc = df[df["qc_threshold"] == qc_thr]
        df_qc_ok = df_qc[df_qc["status"] == "ok"].copy()
        
        if len(df_qc_ok) > 0:
            df_qc_ok["mid_date"] = pd.to_datetime(df_qc_ok["date1"]) + (pd.to_datetime(df_qc_ok["date2"]) - pd.to_datetime(df_qc_ok["date1"])) / 2
            df_qc_ok = df_qc_ok.sort_values("mid_date")
            
            label = f'Corr ≥{qc_thr:.1f} (n={len(df_qc_ok)})'
            if qc_thr == PRIMARY_QC_THRESHOLD:
                label += ' [PRIMARY]'
            
            ax.errorbar(
                df_qc_ok["mid_date"],
                df_qc_ok["vindex_m_per_day"],
                yerr=df_qc_ok["vindex_sigma_m_per_day"],
                marker=markers[qc_thr],
                markersize=8,
                linestyle='-',
                linewidth=2 if qc_thr == PRIMARY_QC_THRESHOLD else 1,
                alpha=0.8 if qc_thr == PRIMARY_QC_THRESHOLD else 0.6,
                color=colors[qc_thr],
                label=label,
                capsize=4,
                capthick=1.5,
            )
    
    ax.set_xlabel('Date', fontsize=18)
    ax.set_ylabel('Glacier velocity index (m d$^{-1}$)', fontsize=18)
    ax.set_title('QC Threshold Sensitivity: Vindex Robustness', fontsize=20, fontweight='normal')
    ax.tick_params(axis='both', labelsize=16)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(fmt_day_mon_en))
    ax.legend(fontsize=14, frameon=True, framealpha=0.95, loc='upper left')
    ax.grid(True, alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    pdf_out = OUTPUT_DIR / "qc_threshold_sensitivity.pdf"
    png_out = OUTPUT_DIR / "qc_threshold_sensitivity.png"
    plt.savefig(pdf_out, dpi=300, bbox_inches='tight')
    plt.savefig(png_out, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ Saved: {pdf_out}")


if __name__ == "__main__":
    main()
