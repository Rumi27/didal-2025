#!/usr/bin/env python3
"""
Pair-wise stable-ground de-biasing + empirical uncertainty (per pair) for Sentinel-1 offset tracking.

What this script produces (minimum required reviewer outputs):
- Per-pair stable-ground bias statistics (mean E/N, optional planar bias terms)
- Empirical uncertainty from stable-ground residuals (NMAD + std per component)
- Valid-sample fraction and median correlation for stable-ground matches
- Glacier velocity index (Vindex) before vs after de-biasing, with error bars
- Publication-quality figures (example bias histograms; Vindex time series with error bars)

Design notes:
- Uses fast NCC template matching via OpenCV (`cv2.matchTemplate`) on the terrain-corrected SNAP products.
- Samples stable-ground matches on a grid around the glacier and excludes the glacier polygon (RGI outline).
- Bias model:
  - constant mean (E,N), and
  - optional planar model: dE = a + bx + cy; dN = a + bx + cy (x,y in pixel coordinates, centered)
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
from matplotlib import rcParams

try:
    import fiona
    from shapely.geometry import shape, Point
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "Missing GIS dependencies (fiona/shapely). Install them or run in the project environment."
    ) from e

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------
# User/project settings
# ---------------------------------------------------------------------

# Glacier location (for Vindex extraction and pixel-size conversion consistency)
GLACIER_LAT = 38.97
GLACIER_LON = 70.75

# Inputs
PROCESSED_DIR = Path("satellite_data/sentinel1/processed")
VELOCITY_TS_FILE = PROCESSED_DIR / "velocity_timeseries_python.csv"
GLACIER_OUTLINE_SHP = Path("satellite_data/dem/processed/didal_glacier_rgi_outline.shp")
STABLE_GROUND_MASK_SHP = Path("stable_ground_mask.shp")

# Output
OUTPUT_DIR = Path("processed_data/stable_ground_debiasing")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Template matching parameters (match the existing NCC setup)
WINDOW_SIZE = 128          # template window (pixels)
SEARCH_RANGE = 200         # +/- pixels

# Coarse global shift estimation (phase correlation on a downsampled window)
COARSE_WIN_SIZE = 2048
COARSE_DOWNSAMPLE = 8
LOCAL_SEARCH_RANGE = 120   # local refinement around coarse shift
STABLE_PHASECORR_WIN = 256

# Stable-ground sampling strategy
STABLE_BBOX_BUFFER_DEG = 0.20     # expand glacier bounding box by this many degrees
GLACIER_EXCLUDE_BUFFER_DEG = 0.002  # exclude a small buffer around glacier boundary
SAMPLE_STEP_PX = 100             # grid spacing in pixels for stable-ground sampling (denser = more robust)

# Glacier-proximal sampling for Vindex (median over samples within the glacier outline)
GLACIER_SAMPLE_STEP_PX = 1
GLACIER_MIN_CORR = 0.0

# Stable-ground quality filters
# NOTE: our stable-ground matching uses phase-correlation "response" (not SNAP correlation),
# which is typically small (~0.01–0.1). We therefore keep this permissive and rely on
# robust statistics + top-N selection downstream.
MIN_CORR = 0.0
MIN_VALID_STABLE_MATCHES = 80

# ---------------------------------------------------------------------
# Plot styling (non-bold, readable)
# ---------------------------------------------------------------------
rcParams["font.family"] = "sans-serif"
rcParams["font.sans-serif"] = ["Arial", "Helvetica", "DejaVu Sans"]
rcParams["font.size"] = 11
rcParams["axes.labelsize"] = 11
rcParams["axes.titlesize"] = 11
rcParams["xtick.labelsize"] = 10
rcParams["ytick.labelsize"] = 10
rcParams["legend.fontsize"] = 10
rcParams["axes.titleweight"] = "normal"
rcParams["axes.labelweight"] = "normal"


@dataclass
class BiasModel:
    """Planar bias model for one component: d = a + b*x + c*y (x,y centered pixel coords)."""
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
    # Prefer VV
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
    # Fallback patterns
    fallback = (
        list(data_folder.glob("*Sigma0*.img"))
        or list(data_folder.glob("*Gamma0*.img"))
        or list(data_folder.glob("Intensity*.img"))
    )
    if not fallback:
        raise FileNotFoundError(f"No Sigma0/Gamma0/Intensity band found in {data_folder}")
    ds = gdal.Open(str(fallback[0]), gdal.GA_ReadOnly)
    if ds is None:
        raise RuntimeError(f"GDAL could not open {fallback[0]}")
    return ds


def _pixel_size_m(geotransform: tuple[float, float, float, float, float, float], lat_deg: float) -> tuple[float, float]:
    """
    Convert geocoded pixel size (degrees) to meters using latitude.
    This mirrors the conversion logic used in `calculate_velocity_python.py`.
    """
    # geotransform[1] = pixel width (deg), geotransform[5] = pixel height (deg, negative)
    lat_rad = np.radians(lat_deg)
    meters_per_degree_lat = 111320.0
    meters_per_degree_lon = 111320.0 * np.cos(lat_rad)
    px_x = abs(geotransform[1]) * meters_per_degree_lon
    px_y = abs(geotransform[5]) * meters_per_degree_lat
    return float(px_x), float(px_y)


def _read_window(ds: gdal.Dataset, row0: int, col0: int, height: int, width: int) -> np.ndarray | None:
    """Read a window centered on (row0,col0) with shape (height,width)."""
    r0 = int(row0 - height // 2)
    c0 = int(col0 - width // 2)
    nrows = ds.RasterYSize
    ncols = ds.RasterXSize
    if r0 < 0 or c0 < 0 or (r0 + height) >= nrows or (c0 + width) >= ncols:
        return None
    band = ds.GetRasterBand(1)
    arr = band.ReadAsArray(c0, r0, width, height)
    if arr is None:
        return None
    arr = arr.astype(np.float32)
    # Replace NaNs/Infs
    if not np.isfinite(arr).all():
        arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    return arr


def _match_offset_cv2(
    master_ds: gdal.Dataset,
    slave_ds: gdal.Dataset,
    center_row: int,
    center_col: int,
    slave_center_row: int | None = None,
    slave_center_col: int | None = None,
    window_size: int = WINDOW_SIZE,
    search_range: int = SEARCH_RANGE,
) -> tuple[int, int, float] | None:
    """
    Fast NCC offset tracking using cv2.matchTemplate (TM_CCOEFF_NORMED).

    Returns (row_offset_px, col_offset_px, corr_max) or None if window invalid.
    """
    # Delay OpenCV import so GDAL/PROJ load their dependencies first (avoids libstdc++ ABI conflicts).
    import cv2

    if slave_center_row is None:
        slave_center_row = center_row
    if slave_center_col is None:
        slave_center_col = center_col

    def preprocess(img: np.ndarray) -> np.ndarray:
        """SAR-friendly preprocessing for matching: log-intensity, high-pass, normalize."""
        img = img.astype(np.float32)
        img = np.maximum(img, 1e-6)
        img = 10.0 * np.log10(img)
        img = img - cv2.GaussianBlur(img, (0, 0), sigmaX=3.0)
        img = img - float(np.mean(img))
        s = float(np.std(img))
        if s > 0:
            img = img / s
        return img.astype(np.float32)

    half = window_size // 2
    # Template (master)
    templ = _read_window(master_ds, center_row, center_col, window_size, window_size)
    if templ is None:
        return None

    # Search image (slave): center +/- search_range plus half-window margin
    search_size = window_size + 2 * search_range
    search = _read_window(slave_ds, slave_center_row, slave_center_col, search_size, search_size)
    if search is None:
        return None

    # OpenCV requires template <= search
    # Ensure float32
    templ = preprocess(templ)
    search = preprocess(search)

    res = cv2.matchTemplate(search, templ, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

    # max_loc is (x,y) top-left of the best match
    dc = int(max_loc[0] - search_range)
    dr = int(max_loc[1] - search_range)
    return dr, dc, float(max_val)


def _estimate_global_shift_phasecorr(
    master_ds: gdal.Dataset,
    slave_ds: gdal.Dataset,
    center_row: int,
    center_col: int,
    win_size: int = COARSE_WIN_SIZE,
    downsample: int = COARSE_DOWNSAMPLE,
) -> tuple[int, int, float]:
    """
    Estimate a coarse global translation (row, col) using phase correlation on a downsampled window.

    Returns (dr0_px, dc0_px, response).
    """
    import cv2

    a = _read_window(master_ds, center_row, center_col, win_size, win_size)
    b = _read_window(slave_ds, center_row, center_col, win_size, win_size)
    if a is None or b is None:
        return 0, 0, np.nan

    a_ds = a[::downsample, ::downsample].astype(np.float32)
    b_ds = b[::downsample, ::downsample].astype(np.float32)

    # Similar preprocessing as template matching
    def preprocess(img: np.ndarray) -> np.ndarray:
        img = img.astype(np.float32)
        img = np.maximum(img, 1e-6)
        img = 10.0 * np.log10(img)
        img = img - cv2.GaussianBlur(img, (0, 0), sigmaX=2.0)
        img = img - float(np.mean(img))
        s = float(np.std(img))
        if s > 0:
            img = img / s
        return img.astype(np.float32)

    a_ds = preprocess(a_ds)
    b_ds = preprocess(b_ds)

    win = cv2.createHanningWindow((a_ds.shape[1], a_ds.shape[0]), cv2.CV_32F)
    a_ds = a_ds * win
    b_ds = b_ds * win

    (shift_x, shift_y), response = cv2.phaseCorrelate(a_ds, b_ds)
    dc0 = int(round(shift_x * downsample))
    dr0 = int(round(shift_y * downsample))
    return dr0, dc0, float(response)


def _estimate_local_shift_phasecorr(
    master_ds: gdal.Dataset,
    slave_ds: gdal.Dataset,
    center_row: int,
    center_col: int,
    slave_center_row: int,
    slave_center_col: int,
    win_size: int = STABLE_PHASECORR_WIN,
) -> tuple[float, float, float] | None:
    """
    Estimate a local shift between two same-size patches using phase correlation.
    Returns (dr_loc_px, dc_loc_px, response) or None if patch is invalid.
    """
    import cv2

    a = _read_window(master_ds, center_row, center_col, win_size, win_size)
    b = _read_window(slave_ds, slave_center_row, slave_center_col, win_size, win_size)
    if a is None or b is None:
        return None

    def preprocess(img: np.ndarray) -> np.ndarray:
        img = img.astype(np.float32)
        img = np.maximum(img, 1e-6)
        img = 10.0 * np.log10(img)
        img = img - cv2.GaussianBlur(img, (0, 0), sigmaX=2.0)
        img = img - float(np.mean(img))
        s = float(np.std(img))
        if s > 0:
            img = img / s
        return img.astype(np.float32)

    a = preprocess(a)
    b = preprocess(b)
    win = cv2.createHanningWindow((a.shape[1], a.shape[0]), cv2.CV_32F)
    (shift_x, shift_y), response = cv2.phaseCorrelate(a * win, b * win)
    # phaseCorrelate returns (x,y) shift; convert to (row, col)
    return float(shift_y), float(shift_x), float(response)


def _load_glacier_polygon() -> tuple[object, tuple[float, float, float, float]]:
    """Load glacier outline polygon in EPSG:4326."""
    if not GLACIER_OUTLINE_SHP.exists():
        raise FileNotFoundError(f"Glacier outline not found: {GLACIER_OUTLINE_SHP}")
    with fiona.open(GLACIER_OUTLINE_SHP) as src:
        geom = None
        for feat in src:
            geom = shape(feat["geometry"])
            break
    if geom is None:
        raise ValueError(f"No features found in {GLACIER_OUTLINE_SHP}")
    return geom, geom.bounds  # (minx,miny,maxx,maxy)

def _load_stable_ground_mask() -> object | None:
    """Load stable-ground mask polygon (union) in EPSG:4326. Returns None if empty/missing."""
    if not STABLE_GROUND_MASK_SHP.exists():
        return None
    try:
        with fiona.open(STABLE_GROUND_MASK_SHP) as src:
            geoms = [shape(feat["geometry"]) for feat in src if feat.get("geometry")]
        if not geoms:
            return None
        g = geoms[0]
        for gg in geoms[1:]:
            g = g.union(gg)
        return g
    except Exception:
        return None


def _stable_sample_points(
    master_ds: gdal.Dataset,
    glacier_poly,
    glacier_bounds,
    bbox_buffer_deg: float = STABLE_BBOX_BUFFER_DEG,
    exclude_buffer_deg: float = GLACIER_EXCLUDE_BUFFER_DEG,
    step_px: int = SAMPLE_STEP_PX,
) -> list[tuple[int, int, float, float]]:
    """
    Generate a grid of stable-ground sample points as (row, col, lon, lat),
    within a buffered glacier bounding box, excluding the glacier polygon (plus buffer).
    """
    # Prefer explicit stable-ground mask if it exists and is non-empty
    stable_mask_poly = _load_stable_ground_mask()
    if stable_mask_poly is not None:
        minx, miny, maxx, maxy = stable_mask_poly.bounds
    else:
        minx, miny, maxx, maxy = glacier_bounds
        minx -= bbox_buffer_deg
        miny -= bbox_buffer_deg
        maxx += bbox_buffer_deg
        maxy += bbox_buffer_deg

    gt = master_ds.GetGeoTransform()
    if gt is None:
        raise RuntimeError("Missing geotransform on TC product; cannot sample stable ground.")

    def lonlat_to_rowcol(lon: float, lat: float) -> tuple[int, int]:
        # Assumes north-up, no rotation
        col = int((lon - gt[0]) / gt[1])
        row = int((lat - gt[3]) / gt[5])  # gt[5] is negative
        return row, col

    def rowcol_to_lonlat(row: int, col: int) -> tuple[float, float]:
        lon = gt[0] + col * gt[1] + row * gt[2]
        lat = gt[3] + col * gt[4] + row * gt[5]
        return float(lon), float(lat)

    # Convert bbox lon/lat to row/col ranges (master grid)
    r_min, c_min = lonlat_to_rowcol(minx, maxy)  # UL
    r_max, c_max = lonlat_to_rowcol(maxx, miny)  # LR
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


def _glacier_sample_points(
    master_ds: gdal.Dataset,
    glacier_poly,
    glacier_bounds,
    bbox_buffer_deg: float = 0.10,
    step_px: int = GLACIER_SAMPLE_STEP_PX,
) -> list[tuple[int, int, float, float]]:
    """
    Sample points within the glacier outline to compute a glacier-proximal velocity index.
    Returns list of (row, col, lon, lat).
    """
    minx, miny, maxx, maxy = glacier_bounds
    minx -= bbox_buffer_deg
    miny -= bbox_buffer_deg
    maxx += bbox_buffer_deg
    maxy += bbox_buffer_deg

    gt = master_ds.GetGeoTransform()
    if gt is None:
        raise RuntimeError("Missing geotransform on TC product; cannot sample glacier points.")

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

def _fit_plane(z: np.ndarray, x: np.ndarray, y: np.ndarray) -> BiasModel:
    """Least-squares fit z = a + b*x + c*y."""
    A = np.column_stack([np.ones_like(x), x, y]).astype(np.float64)
    coef, *_ = np.linalg.lstsq(A, z.astype(np.float64), rcond=None)
    return BiasModel(a=float(coef[0]), b=float(coef[1]), c=float(coef[2]))


def _nmad(x: np.ndarray) -> float:
    """Normalized median absolute deviation (robust sigma)."""
    x = np.asarray(x, dtype=np.float64)
    med = np.nanmedian(x)
    return float(1.4826 * np.nanmedian(np.abs(x - med)))


def process_pair(
    date1: str,
    date2: str,
    master_dim: Path,
    slave_dim: Path,
    time_delta_days: float,
    glacier_poly,
    glacier_bounds,
    omega_masks: dict = None,
) -> dict:
    """Compute stable-ground bias + uncertainty for one pair."""
    mst = _open_sigma0_band(master_dim)
    slv = _open_sigma0_band(slave_dim)
    try:
        gt = mst.GetGeoTransform()
        if gt is None:
            raise RuntimeError(f"Missing geotransform for {master_dim}")
        # Pixel size in meters (use glacier latitude for consistency with existing workflow)
        px_x_m, px_y_m = _pixel_size_m(gt, GLACIER_LAT)

        # Glacier pixel location
        g_col = int((GLACIER_LON - gt[0]) / gt[1])
        g_row = int((GLACIER_LAT - gt[3]) / gt[5])

        # Coarse global shift estimate (helps avoid false local maxima; reveals large cross-track shifts)
        dr0, dc0, pc_response = _estimate_global_shift_phasecorr(mst, slv, g_row, g_col)

        glacier_match = _match_offset_cv2(
            mst,
            slv,
            g_row,
            g_col,
            slave_center_row=g_row + dr0,
            slave_center_col=g_col + dc0,
            search_range=LOCAL_SEARCH_RANGE,
        )
        if glacier_match is None:
            raise RuntimeError(f"Glacier match failed for pair {date1} -> {date2}")
        g_dr_loc, g_dc_loc, g_corr = glacier_match
        g_dr = dr0 + g_dr_loc
        g_dc = dc0 + g_dc_loc
        g_dx = g_dc * px_x_m
        g_dy = g_dr * px_y_m
        g_disp = float(np.hypot(g_dx, g_dy))
        g_vel = g_disp / time_delta_days if time_delta_days > 0 else np.nan

        # Stable-ground sample points
        pts = _stable_sample_points(mst, glacier_poly, glacier_bounds)
        if len(pts) == 0:
            raise RuntimeError("No stable-ground sample points generated; check outline/CRS and bbox buffer.")

        rows = []
        cols = []
        corrs = []
        dxs = []
        dys = []
        is_saturated = []

        for (r, c, lon, lat) in pts:
            m = _estimate_local_shift_phasecorr(
                mst,
                slv,
                r,
                c,
                slave_center_row=r + dr0,
                slave_center_col=c + dc0,
                win_size=STABLE_PHASECORR_WIN,
            )
            if m is None:
                continue
            dr_loc, dc_loc, corr = m
            # Treat very large local shifts as unstable (likely mismatch)
            sat = (abs(dr_loc) >= LOCAL_SEARCH_RANGE) or (abs(dc_loc) >= LOCAL_SEARCH_RANGE)
            dr = dr0 + int(round(dr_loc))
            dc = dc0 + int(round(dc_loc))
            rows.append(r)
            cols.append(c)
            corrs.append(corr)
            dxs.append(dc * px_x_m)
            dys.append(dr * px_y_m)
            is_saturated.append(sat)

        n_total = len(pts)
        n_success = len(dxs)
        if n_success == 0:
            # No stable-ground matches at all (likely no overlap / severe decorrelation)
            return {
                "date1": date1,
                "date2": date2,
                "time_delta_days": float(time_delta_days),
                "n_stable_total": int(n_total),
                "n_stable_success": 0,
                "n_stable_valid": 0,
                "valid_fraction": 0.0,
                "stable_corr_median": np.nan,
                "stable_corr_q25": np.nan,
                "stable_corr_q75": np.nan,
                "stable_saturated_fraction": np.nan,
                "bias_mean_E_m": np.nan,
                "bias_mean_N_m": np.nan,
                "plane_E_a_m": np.nan,
                "plane_E_b_m_per_px": np.nan,
                "plane_E_c_m_per_px": np.nan,
                "plane_N_a_m": np.nan,
                "plane_N_b_m_per_px": np.nan,
                "plane_N_c_m_per_px": np.nan,
                "resid_nmad_E_m": np.nan,
                "resid_nmad_N_m": np.nan,
                "resid_std_E_m": np.nan,
                "resid_std_N_m": np.nan,
                "glacier_corr": float(g_corr),
                "glacier_dE_m_raw": float(g_dx),
                "glacier_dN_m_raw": float(g_dy),
                "glacier_speed_m_per_day_raw": float(g_vel),
                "bias_E_at_glacier_m": np.nan,
                "bias_N_at_glacier_m": np.nan,
                "glacier_dE_m_debiased": np.nan,
                "glacier_dN_m_debiased": np.nan,
                "glacier_speed_m_per_day_debiased": np.nan,
                "glacier_speed_sigma_m_per_day": np.nan,
                "vindex_m_per_day_raw": np.nan,
                "vindex_m_per_day_debiased": np.nan,
                "vindex_sigma_m_per_day": np.nan,
                "vindex_sample_n": 0,
                "vindex_corr_median": np.nan,
                "stable_ground_status": "no_stable_matches",
                "global_shift_row_px": int(dr0),
                "global_shift_col_px": int(dc0),
                "phasecorr_response": float(pc_response),
            }

        dxs = np.asarray(dxs, dtype=np.float64)
        dys = np.asarray(dys, dtype=np.float64)
        corrs = np.asarray(corrs, dtype=np.float64)
        rows = np.asarray(rows, dtype=np.float64)
        cols = np.asarray(cols, dtype=np.float64)
        is_saturated = np.asarray(is_saturated, dtype=bool)

        sat_frac = float(np.mean(is_saturated)) if len(is_saturated) else np.nan

        # Candidate set for bias estimation: non-saturated
        cand = (~is_saturated)
        if np.sum(cand) < MIN_VALID_STABLE_MATCHES:
            # Not enough non-saturated stable-ground ties to estimate bias reliably
            return {
                "date1": date1,
                "date2": date2,
                "time_delta_days": float(time_delta_days),
                "n_stable_total": int(n_total),
                "n_stable_success": int(n_success),
                "n_stable_valid": int(np.sum(cand)),
                "valid_fraction": float(np.sum(cand) / n_total) if n_total > 0 else np.nan,
                "stable_corr_median": float(np.nanmedian(corrs)),
                "stable_corr_q25": float(np.nanpercentile(corrs, 25)),
                "stable_corr_q75": float(np.nanpercentile(corrs, 75)),
                "stable_saturated_fraction": sat_frac,
                "bias_mean_E_m": np.nan,
                "bias_mean_N_m": np.nan,
                "plane_E_a_m": np.nan,
                "plane_E_b_m_per_px": np.nan,
                "plane_E_c_m_per_px": np.nan,
                "plane_N_a_m": np.nan,
                "plane_N_b_m_per_px": np.nan,
                "plane_N_c_m_per_px": np.nan,
                "resid_nmad_E_m": np.nan,
                "resid_nmad_N_m": np.nan,
                "resid_std_E_m": np.nan,
                "resid_std_N_m": np.nan,
                "glacier_corr": float(g_corr),
                "glacier_dE_m_raw": float(g_dx),
                "glacier_dN_m_raw": float(g_dy),
                "glacier_speed_m_per_day_raw": float(g_vel),
                "bias_E_at_glacier_m": np.nan,
                "bias_N_at_glacier_m": np.nan,
                "glacier_dE_m_debiased": np.nan,
                "glacier_dN_m_debiased": np.nan,
                "glacier_speed_m_per_day_debiased": np.nan,
                "glacier_speed_sigma_m_per_day": np.nan,
                "vindex_m_per_day_raw": np.nan,
                "vindex_m_per_day_debiased": np.nan,
                "vindex_sigma_m_per_day": np.nan,
                "vindex_sample_n": 0,
                "vindex_corr_median": np.nan,
                "stable_ground_status": "insufficient_non_saturated_ties",
                "global_shift_row_px": int(dr0),
                "global_shift_col_px": int(dc0),
                "phasecorr_response": float(pc_response),
            }

        # From candidate set, take a high-quality subset for plane fitting.
        # Use an adaptive threshold: max(MIN_CORR, 60th percentile), and ensure at least MIN_VALID_STABLE_MATCHES.
        corr_cand = corrs[cand]
        thr = float(max(MIN_CORR, np.nanpercentile(corr_cand, 60)))
        good = cand & (corrs >= thr)
        if np.sum(good) < MIN_VALID_STABLE_MATCHES:
            # Fall back to top-N by correlation within candidate set
            idx_cand = np.where(cand)[0]
            order = idx_cand[np.argsort(corrs[idx_cand])[::-1]]
            keep = order[:MIN_VALID_STABLE_MATCHES]
            good = np.zeros_like(cand, dtype=bool)
            good[keep] = True

        n_valid = int(np.sum(good))
        valid_frac = n_valid / n_total if n_total > 0 else np.nan

        # Centered coordinates for plane fit
        col_mean = float(np.nanmean(cols[good]))
        row_mean = float(np.nanmean(rows[good]))
        x = cols[good] - col_mean
        y = rows[good] - row_mean

        # Constant bias (mean)
        mean_dx = float(np.nanmean(dxs[good]))
        mean_dy = float(np.nanmean(dys[good]))

        # Optional planar bias (per component)
        plane_dx = _fit_plane(dxs[good], x, y)
        plane_dy = _fit_plane(dys[good], x, y)

        # Residuals after plane removal
        dx_pred = plane_dx.predict(x, y)
        dy_pred = plane_dy.predict(x, y)
        dx_res = dxs[good] - dx_pred
        dy_res = dys[good] - dy_pred

        nmad_dx = _nmad(dx_res)
        nmad_dy = _nmad(dy_res)
        std_dx = float(np.nanstd(dx_res))
        std_dy = float(np.nanstd(dy_res))

        # Bias evaluated at glacier pixel (use centered coords)
        gx = float(g_col - col_mean)
        gy = float(g_row - row_mean)
        bias_dx_glacier = float(plane_dx.predict(np.asarray([gx]), np.asarray([gy]))[0])
        bias_dy_glacier = float(plane_dy.predict(np.asarray([gx]), np.asarray([gy]))[0])

        # Apply de-biasing to glacier displacement at the reference point (for diagnostics)
        g_dx_db = float(g_dx - bias_dx_glacier)
        g_dy_db = float(g_dy - bias_dy_glacier)
        g_disp_db = float(np.hypot(g_dx_db, g_dy_db))
        g_vel_db = g_disp_db / time_delta_days if time_delta_days > 0 else np.nan

        # Uncertainty propagation to speed using robust component sigmas (NMAD)
        # disp = sqrt(dx^2 + dy^2); v = disp / dt
        def sigma_speed(dx_m: float, dy_m: float) -> float:
            disp = float(np.hypot(dx_m, dy_m))
            if disp <= 0 or not np.isfinite(disp):
                return np.nan
            sigma_disp = float(np.sqrt((dx_m / disp) ** 2 * nmad_dx ** 2 + (dy_m / disp) ** 2 * nmad_dy ** 2))
            return float(sigma_disp / time_delta_days)

        sigma_v = sigma_speed(g_dx_db, g_dy_db)

        # ------------------------------------------------------------------
        # Vindex: median speed over glacier-proximal samples within outline
        # Step 3: Fixed Analysis Region (Omega) and Sensitivity
        # ------------------------------------------------------------------
        
        if omega_masks is None:
             omega_masks = create_omega_masks(glacier_poly)
             
        omega_wide = omega_masks['wide']
        omega_base = omega_masks['base']
        omega_narrow = omega_masks['narrow']
        
        glacier_pts = _glacier_sample_points(mst, glacier_poly, glacier_bounds)
        
        # Lists for base mask stats
        base_speeds_db = []
        base_speeds_raw = []
        base_corrs = []
        
        # Lists for sensitivity
        wide_speeds_db = []
        narrow_speeds_db = []
        
        # Valid pixel counting for base mask
        base_total_possible = 0
        
        for (r, c, lon, lat) in glacier_pts:
            p_geom = Point(lon, lat)
            in_wide = omega_wide.covers(p_geom)
            in_base = omega_base.covers(p_geom)
            in_narrow = omega_narrow.covers(p_geom)
            
            if not in_wide: # Optimization: Wide contains Base contains Narrow
                continue

            if in_base:
                base_total_possible += 1

            # Use local NCC match around coarse shift
            m = _match_offset_cv2(
                mst,
                slv,
                r,
                c,
                slave_center_row=r + dr0,
                slave_center_col=c + dc0,
                search_range=LOCAL_SEARCH_RANGE,
            )
            
            # Check for valid match
            has_valid_match = False
            v_db = np.nan
            v_raw = np.nan
            corr = np.nan
            
            if m is not None:
                dr_loc, dc_loc, corr = m
                if corr >= GLACIER_MIN_CORR and (abs(dr_loc) < LOCAL_SEARCH_RANGE and abs(dc_loc) < LOCAL_SEARCH_RANGE):
                    dr = dr0 + dr_loc
                    dc = dc0 + dc_loc
                    dx_m = dc * px_x_m
                    dy_m = dr * px_y_m
                    
                    # Bias at this point
                    bx = float(c - col_mean)
                    by = float(r - row_mean)
                    bE = float(plane_dx.predict(np.asarray([bx]), np.asarray([by]))[0])
                    bN = float(plane_dy.predict(np.asarray([bx]), np.asarray([by]))[0])
                    
                    dx_db = float(dx_m - bE)
                    dy_db = float(dy_m - bN)
                    
                    v_raw = float(np.hypot(dx_m, dy_m) / time_delta_days)
                    v_db = float(np.hypot(dx_db, dy_db) / time_delta_days)
                    has_valid_match = True

            # Accumulate stats
            if has_valid_match:
                if in_wide:
                    wide_speeds_db.append(v_db)
                if in_base:
                    base_speeds_db.append(v_db)
                    base_speeds_raw.append(v_raw)
                    base_corrs.append(corr)
                if in_narrow:
                    narrow_speeds_db.append(v_db)
        
        # Calculate Base Metrics (Primary Vindex)
        if len(base_speeds_db) > 0:
            vindex_db = float(np.nanmedian(base_speeds_db))
            vindex_raw = float(np.nanmedian(base_speeds_raw))
            
            vindex_omega_base = vindex_db
            vindex_omega_narrow = float(np.nanmedian(narrow_speeds_db)) if narrow_speeds_db else np.nan
            vindex_omega_wide = float(np.nanmedian(wide_speeds_db)) if wide_speeds_db else np.nan
            
            vindex_corr_median = float(np.nanmedian(base_corrs))
            vindex_n = int(len(base_speeds_db))
            omega_valid_frac = float(vindex_n / base_total_possible) if base_total_possible > 0 else 0.0
            omega_iqr = np.nanpercentile(base_corrs, 75) - np.nanpercentile(base_corrs, 25)
        else:
            vindex_db = np.nan
            vindex_raw = np.nan
            vindex_omega_base = np.nan
            vindex_omega_narrow = np.nan
            vindex_omega_wide = np.nan
            vindex_corr_median = np.nan
            vindex_n = 0
            omega_valid_frac = 0.0
            omega_iqr = np.nan 


        return {
            "date1": date1,
            "date2": date2,
            "time_delta_days": float(time_delta_days),
            "n_stable_total": int(n_total),
            "n_stable_success": int(n_success),
            "n_stable_valid": int(n_valid),
            "valid_fraction": float(valid_frac),
            "stable_corr_median": float(np.nanmedian(corrs[good])),
            "stable_corr_q25": float(np.nanpercentile(corrs[good], 25)),
            "stable_corr_q75": float(np.nanpercentile(corrs[good], 75)),
            "stable_saturated_fraction": sat_frac,
            "bias_mean_E_m": mean_dx,
            "bias_mean_N_m": mean_dy,
            "plane_E_a_m": plane_dx.a,
            "plane_E_b_m_per_px": plane_dx.b,
            "plane_E_c_m_per_px": plane_dx.c,
            "plane_N_a_m": plane_dy.a,
            "plane_N_b_m_per_px": plane_dy.b,
            "plane_N_c_m_per_px": plane_dy.c,
            "resid_nmad_E_m": float(nmad_dx),
            "resid_nmad_N_m": float(nmad_dy),
            "resid_std_E_m": float(std_dx),
            "resid_std_N_m": float(std_dy),
            "glacier_corr": float(g_corr),
            "glacier_dE_m_raw": float(g_dx),
            "glacier_dN_m_raw": float(g_dy),
            "glacier_speed_m_per_day_raw": float(g_vel),
            "bias_E_at_glacier_m": float(bias_dx_glacier),
            "bias_N_at_glacier_m": float(bias_dy_glacier),
            "glacier_dE_m_debiased": float(g_dx_db),
            "glacier_dN_m_debiased": float(g_dy_db),
            "glacier_speed_m_per_day_debiased": float(g_vel_db),
            "glacier_speed_sigma_m_per_day": float(sigma_v),
            "vindex_m_per_day_raw": float(vindex_raw) if np.isfinite(vindex_raw) else np.nan,
            "vindex_m_per_day_debiased": float(vindex_db) if np.isfinite(vindex_db) else np.nan,
            "vindex_omega_base": float(vindex_omega_base) if np.isfinite(vindex_omega_base) else np.nan,
            "vindex_omega_narrow": float(vindex_omega_narrow) if np.isfinite(vindex_omega_narrow) else np.nan,
            "vindex_omega_wide": float(vindex_omega_wide) if np.isfinite(vindex_omega_wide) else np.nan,
            "omega_valid_fraction": float(omega_valid_frac),
            "omega_corr_iqr": float(omega_iqr) if np.isfinite(omega_iqr) else np.nan,
            "vindex_sigma_m_per_day": float(sigma_speed(g_dx_db, g_dy_db)),
            "vindex_sample_n": int(vindex_n),
            "vindex_corr_median": float(vindex_corr_median) if np.isfinite(vindex_corr_median) else np.nan,
            "stable_ground_status": "ok",
            "global_shift_row_px": int(dr0),
            "global_shift_col_px": int(dc0),
            "phasecorr_response": float(pc_response),
        }
    finally:
        mst = None
        slv = None


def make_figures(df_pairs: pd.DataFrame, stable_examples: dict[str, np.ndarray]) -> None:
    """Create publication-quality figures."""
    # Figure 1: Vindex before/after with error bars
    dates = pd.to_datetime(df_pairs["date2"])
    fig, ax = plt.subplots(1, 1, figsize=(7.2, 3.6), dpi=150)
    ax.plot(dates, df_pairs["vindex_m_per_day_raw"], "-", color="#2E86AB", linewidth=2.2, label="Vindex (raw)")
    ax.plot(dates, df_pairs["vindex_m_per_day_debiased"], "-", color="#C73E1D", linewidth=2.2, label="Vindex (de-biased)")
    ax.errorbar(
        dates,
        df_pairs["vindex_m_per_day_debiased"],
        yerr=df_pairs["vindex_sigma_m_per_day"],
        fmt="none",
        ecolor="#C73E1D",
        elinewidth=1.2,
        capsize=2,
        alpha=0.9,
        label="Empirical ±1σ (NMAD)"
    )
    ax.set_ylabel("Velocity (m d$^{-1}$)")
    ax.set_xlabel("Date")
    ax.set_title("Glacier velocity index (Vindex) before vs after stable-ground de-biasing", loc="left", pad=8)
    ax.grid(True, alpha=0.25, linestyle="--")
    ax.legend(loc="best", frameon=True, fancybox=False, framealpha=0.95)
    fig.tight_layout()
    out_png = OUTPUT_DIR / "vindex_before_after.png"
    out_pdf = OUTPUT_DIR / "vindex_before_after.pdf"
    fig.savefig(out_png, dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(out_pdf, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    # Figure 2: Example stable-ground residual histograms (E/N) for a representative pair
    # stable_examples contains arrays: dx_res, dy_res for one pair
    if stable_examples:
        key = list(stable_examples.keys())[0]
        dx_res, dy_res = stable_examples[key]

        fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), dpi=150)
        for ax, data, title in [
            (axes[0], dx_res, "E residuals (after plane removal)"),
            (axes[1], dy_res, "N residuals (after plane removal)"),
        ]:
            ax.hist(data, bins=60, color="#6C757D", alpha=0.7, edgecolor="none")
            ax.axvline(np.nanmedian(data), color="#2E86AB", linewidth=1.8, label="median")
            ax.set_title(title, loc="left", pad=6)
            ax.set_xlabel("Residual displacement (m)")
            ax.grid(True, alpha=0.2, linestyle="--")
        axes[0].set_ylabel("Count")
        fig.suptitle(f"Stable-ground residual distributions (example pair: {key})", y=1.02)
        fig.tight_layout()
        out_png = OUTPUT_DIR / "stable_ground_residuals_example.png"
        out_pdf = OUTPUT_DIR / "stable_ground_residuals_example.pdf"
        fig.savefig(out_png, dpi=600, bbox_inches="tight", facecolor="white")
        fig.savefig(out_pdf, bbox_inches="tight", facecolor="white")
        plt.close(fig)

def make_bias_vectors_and_nmad_figure(df_pairs: pd.DataFrame) -> None:
    """
    Compact reviewer-facing figure:
    (a) per-pair mean stable-ground bias vectors (E,N) in m/day
    (b) per-pair residual spread (NMAD) magnitude in m/day
    """
    ok = df_pairs[df_pairs.get("stable_ground_status") == "ok"].copy()
    if len(ok) == 0:
        return

    ok["date2_dt"] = pd.to_datetime(ok["date2"])
    ok = ok.sort_values("date2_dt")

    # Bias and NMAD in m/day
    dt = ok["time_delta_days"].astype(float).replace(0, np.nan)
    ok["bias_E_md"] = ok["bias_mean_E_m"].astype(float) / dt
    ok["bias_N_md"] = ok["bias_mean_N_m"].astype(float) / dt
    ok["nmad_E_md"] = ok["resid_nmad_E_m"].astype(float) / dt
    ok["nmad_N_md"] = ok["resid_nmad_N_m"].astype(float) / dt
    ok["nmad_mag_md"] = np.sqrt(ok["nmad_E_md"] ** 2 + ok["nmad_N_md"] ** 2)

    import matplotlib.dates as mdates
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), dpi=150, gridspec_kw={"wspace": 0.42})

    # (a) Bias vectors in E-N space
    ax = axes[0]
    ax.axhline(0, color="#444444", linewidth=1.0, alpha=0.6)
    ax.axvline(0, color="#444444", linewidth=1.0, alpha=0.6)
    ax.quiver(
        np.zeros(len(ok)),
        np.zeros(len(ok)),
        ok["bias_E_md"].values,
        ok["bias_N_md"].values,
        angles="xy",
        scale_units="xy",
        scale=1,
        color="#2E86AB",
        alpha=0.85,
        width=0.004,
    )
    # Label only a subset to avoid clutter (first/middle/last)
    label_rows = [ok.iloc[0], ok.iloc[len(ok)//2], ok.iloc[-1]]
    for r in label_rows:
        ax.text(
            float(r["bias_E_md"]),
            float(r["bias_N_md"]),
            pd.to_datetime(r["date2"]).strftime("%d %b"),
            fontsize=8,
            ha="left",
            va="bottom",
        )
    ax.set_xlabel("Mean bias E (m d$^{-1}$)")
    ax.set_ylabel("Mean bias N (m d$^{-1}$)")
    ax.set_title("(a) Mean stable-ground bias vectors", loc="left", pad=6)
    ax.grid(True, alpha=0.2, linestyle="--")

    # Make axes symmetric around zero for readability
    lim = np.nanmax(np.abs(np.r_[ok["bias_E_md"].values, ok["bias_N_md"].values]))
    if np.isfinite(lim) and lim > 0:
        ax.set_xlim(-1.1 * lim, 1.1 * lim)
        ax.set_ylim(-1.1 * lim, 1.1 * lim)

    # (b) NMAD magnitude time series
    ax2 = axes[1]
    ax2.plot(ok["date2_dt"], ok["nmad_mag_md"], "o-", color="#C73E1D", linewidth=2.2, markersize=6, alpha=0.9)
    ax2.set_ylabel("Residual NMAD magnitude (m d$^{-1}$)")
    ax2.set_xlabel("Date")
    ax2.set_title("(b) Empirical per-pair uncertainty (NMAD)", loc="left", pad=6)
    ax2.grid(True, alpha=0.2, linestyle="--")
    ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    for lab in ax2.get_xticklabels():
        lab.set_rotation(0)
        lab.set_ha("center")

    fig.tight_layout()
    out_png = OUTPUT_DIR / "stable_ground_bias_vectors_nmad.png"
    out_pdf = OUTPUT_DIR / "stable_ground_bias_vectors_nmad.pdf"
    fig.savefig(out_png, dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(out_pdf, bbox_inches="tight", facecolor="white")
    plt.close(fig)

def make_multipair_before_after_histograms(df_pairs: pd.DataFrame) -> None:
    """
    Make a reviewer-oriented multi-panel figure: stable-ground residual distributions
    before vs after de-biasing for 3 representative pairs.

    We use the per-pair stable-ground mean bias terms and residual NMAD as summary stats,
    and re-sample stable-ground tie points for each selected pair to create histograms.
    """
    # Choose 3 pairs:
    # - one "good" (highest stable_corr_median among ok)
    # - one "typical" (median stable_corr_median among ok)
    # - one "low" (lowest stable_corr_median among ok)
    ok = df_pairs[df_pairs.get("stable_ground_status") == "ok"].copy()
    if len(ok) < 3:
        return
    ok = ok.sort_values("stable_corr_median")
    low = ok.iloc[0]
    mid = ok.iloc[len(ok) // 2]
    high = ok.iloc[-1]
    selected = [high, mid, low]

    tc_map = _find_tc_products()
    glacier_poly, glacier_bounds = _load_glacier_polygon()

    fig, axes = plt.subplots(3, 4, figsize=(7.2, 7.6), dpi=150)
    for row_i, r in enumerate(selected):
        date1 = r["date1"]
        date2 = r["date2"]
        dt = float(r["time_delta_days"])

        mst = _open_sigma0_band(tc_map[date1])
        slv = _open_sigma0_band(tc_map[date2])
        try:
            gt = mst.GetGeoTransform()
            px_x_m, px_y_m = _pixel_size_m(gt, GLACIER_LAT)

            g_col = int((GLACIER_LON - gt[0]) / gt[1])
            g_row = int((GLACIER_LAT - gt[3]) / gt[5])
            dr0, dc0, _ = _estimate_global_shift_phasecorr(mst, slv, g_row, g_col)

            # Sample stable-ground points (mask-only if mask exists)
            pts = _stable_sample_points(mst, glacier_poly, glacier_bounds)

            dx_raw = []
            dy_raw = []
            corr = []
            for (rr, cc, lon, lat) in pts:
                m = _estimate_local_shift_phasecorr(
                    mst, slv,
                    rr, cc,
                    slave_center_row=rr + dr0,
                    slave_center_col=cc + dc0,
                    win_size=STABLE_PHASECORR_WIN
                )
                if m is None:
                    continue
                dr_loc, dc_loc, cval = m
                if not np.isfinite(cval):
                    continue
                if abs(dr_loc) >= LOCAL_SEARCH_RANGE or abs(dc_loc) >= LOCAL_SEARCH_RANGE:
                    continue
                dr = dr0 + int(round(dr_loc))
                dc = dc0 + int(round(dc_loc))
                dx_raw.append(dc * px_x_m)
                dy_raw.append(dr * px_y_m)
                corr.append(cval)

            dx_raw = np.asarray(dx_raw, dtype=np.float64)
            dy_raw = np.asarray(dy_raw, dtype=np.float64)
            if len(dx_raw) < MIN_VALID_STABLE_MATCHES:
                continue

            # De-bias by subtracting mean bias (for "after" visualization)
            dx_db = dx_raw - float(r["bias_mean_E_m"])
            dy_db = dy_raw - float(r["bias_mean_N_m"])

            # Plot histograms: raw E, raw N, debiased E, debiased N
            titles = ["E (raw)", "N (raw)", "E (de-biased)", "N (de-biased)"]
            data_list = [dx_raw, dy_raw, dx_db, dy_db]
            for col_i, (ax, data, title) in enumerate(zip(axes[row_i], data_list, titles)):
                ax.hist(data, bins=60, color="#6C757D", alpha=0.7, edgecolor="none")
                ax.axvline(np.nanmedian(data), color="#2E86AB", linewidth=1.4)
                if row_i == 0:
                    ax.set_title(title, loc="left", pad=4)
                if col_i == 0:
                    ax.set_ylabel(f"{date1}→{date2}\nCount")
                ax.grid(True, alpha=0.2, linestyle="--")

            # Caption-like annotation on the rightmost axis of the row
            axes[row_i, 3].text(
                0.02, 0.98,
                f"Bias(E,N)=({float(r['bias_mean_E_m']):.0f},{float(r['bias_mean_N_m']):.0f}) m\n"
                f"NMAD(E,N)=({float(r['resid_nmad_E_m']):.0f},{float(r['resid_nmad_N_m']):.0f}) m\n"
                f"Valid frac={float(r['valid_fraction']):.2f}\n"
                f"Median match={float(r['stable_corr_median']):.3f}",
                transform=axes[row_i, 3].transAxes,
                va="top",
                ha="left",
                fontsize=9,
                bbox=dict(boxstyle="round,pad=0.25", facecolor="white", alpha=0.9, edgecolor="#CCCCCC")
            )
        finally:
            mst = None
            slv = None

    fig.suptitle("Stable-ground offsets: residual distributions before vs after de-biasing (3 representative pairs)", y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    out_png = OUTPUT_DIR / "stable_ground_before_after_multipair.png"
    out_pdf = OUTPUT_DIR / "stable_ground_before_after_multipair.pdf"
    fig.savefig(out_png, dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(out_pdf, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    if not VELOCITY_TS_FILE.exists():
        raise FileNotFoundError(f"Velocity time series not found: {VELOCITY_TS_FILE}")

    tc_map = _find_tc_products()
    if len(tc_map) < 2:
        raise RuntimeError("Not enough terrain-corrected products found to process pairs.")

    glacier_poly, glacier_bounds = _load_glacier_polygon()

    df_ts = pd.read_csv(VELOCITY_TS_FILE)
    # Ensure date strings
    for col in ["date1", "date2", "date"]:
        if col in df_ts.columns:
            df_ts[col] = df_ts[col].astype(str)

    results = []
    stable_examples = {}

    print("=" * 80)
    print("PAIR-WISE STABLE-GROUND DE-BIASING + EMPIRICAL UNCERTAINTY")
    print("=" * 80)
    print(f"Pairs: {len(df_ts)}")

    # Create fixed analysis regions once
    omega_masks = create_omega_masks(glacier_poly)

    for i, row in df_ts.iterrows():
        date1 = row["date1"]
        date2 = row["date2"]
        dt_days = float(row.get("time_delta_days", 6.0))

        if date1 not in tc_map or date2 not in tc_map:
            raise RuntimeError(f"Missing TC products for pair {date1}->{date2}. Found: {date1 in tc_map}, {date2 in tc_map}")

        print(f"\nProcessing {date1} -> {date2} (Δt={dt_days:.1f} days)")
        res = process_pair(date1, date2, tc_map[date1], tc_map[date2], dt_days, glacier_poly, glacier_bounds, omega_masks=omega_masks)
        results.append(res)

        # Store one example residual distribution for plotting (first non-saturated pair)
        if not stable_examples:
            # Recompute residual arrays quickly from stored plane terms is non-trivial; instead, we sample again
            # but only once for figure creation.
            mst = _open_sigma0_band(tc_map[date1])
            slv = _open_sigma0_band(tc_map[date2])
            try:
                gt = mst.GetGeoTransform()
                if gt is None:
                    continue
                px_x_m, px_y_m = _pixel_size_m(gt, GLACIER_LAT)
                pts = _stable_sample_points(mst, glacier_poly, glacier_bounds)
                rows_l = []
                cols_l = []
                dxs = []
                dys = []
                corrs = []
                # Coarse shift around glacier pixel for this pair
                g_col = int((GLACIER_LON - gt[0]) / gt[1])
                g_row = int((GLACIER_LAT - gt[3]) / gt[5])
                dr0, dc0, _ = _estimate_global_shift_phasecorr(mst, slv, g_row, g_col)
                for (r, c, lon, lat) in pts:
                    m = _estimate_local_shift_phasecorr(
                        mst,
                        slv,
                        r,
                        c,
                        slave_center_row=r + dr0,
                        slave_center_col=c + dc0,
                        win_size=STABLE_PHASECORR_WIN,
                    )
                    if m is None:
                        continue
                    dr_loc, dc_loc, corr = m
                    if corr < MIN_CORR:
                        continue
                    if abs(dr_loc) >= LOCAL_SEARCH_RANGE or abs(dc_loc) >= LOCAL_SEARCH_RANGE:
                        continue
                    rows_l.append(r)
                    cols_l.append(c)
                    dxs.append((dc0 + int(round(dc_loc))) * px_x_m)
                    dys.append((dr0 + int(round(dr_loc))) * px_y_m)
                    corrs.append(corr)
                if len(dxs) >= 50:
                    rows_a = np.asarray(rows_l, dtype=np.float64)
                    cols_a = np.asarray(cols_l, dtype=np.float64)
                    x = cols_a - np.nanmean(cols_a)
                    y = rows_a - np.nanmean(rows_a)
                    dxs_a = np.asarray(dxs, dtype=np.float64)
                    dys_a = np.asarray(dys, dtype=np.float64)
                    plane_dx = _fit_plane(dxs_a, x, y)
                    plane_dy = _fit_plane(dys_a, x, y)
                    dx_res = dxs_a - plane_dx.predict(x, y)
                    dy_res = dys_a - plane_dy.predict(x, y)
                    stable_examples[f"{date1}→{date2}"] = np.vstack([dx_res, dy_res])
            finally:
                mst = None
                slv = None

    df_pairs = pd.DataFrame(results).sort_values("date2").reset_index(drop=True)

    # Save per-pair table (reviewer-required)
    out_table = OUTPUT_DIR / "pairwise_stable_ground_stats.csv"
    df_pairs.to_csv(out_table, index=False)
    print(f"\n✅ Saved per-pair stable-ground table: {out_table}")

    # Also write a compact LaTeX table for the manuscript
    # Required fields: mean bias (E,N), NMAD, valid fraction, median match metric
    def fmt(x, nd=1):
        if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))):
            return "NA"
        try:
            return f"{float(x):.{nd}f}"
        except Exception:
            return "NA"

    tex_path = OUTPUT_DIR / "pairwise_stable_ground_stats_table.tex"
    lines = []
    lines.append("\\begin{tabular}{lrrrrrrrr}")
    lines.append("\\toprule")
    lines.append("Pair & Bias$_E$ (m d$^{-1}$) & Bias$_N$ (m d$^{-1}$) & Slopes$_E$ ($10^{-3}$) & Slopes$_N$ ($10^{-3}$) & NMAD$_E$ (m d$^{-1}$) & NMAD$_N$ (m d$^{-1}$) & Valid frac. & Median match \\\\")
    lines.append("\\midrule")
    for _, r in df_pairs.iterrows():
        pair = f"{r['date1']}--{r['date2']}"
        dt = float(r.get("time_delta_days", 6.0)) if r.get("time_delta_days") else 6.0
        if dt == 0:
            dt = 6.0
        bE = r.get("bias_mean_E_m")
        bN = r.get("bias_mean_N_m")
        nE = r.get("resid_nmad_E_m")
        nN = r.get("resid_nmad_N_m")
        bE_md = (float(bE) / dt) if bE is not None and str(bE) != "nan" else np.nan
        bN_md = (float(bN) / dt) if bN is not None and str(bN) != "nan" else np.nan
        nE_md = (float(nE) / dt) if nE is not None and str(nE) != "nan" else np.nan
        nN_md = (float(nN) / dt) if nN is not None and str(nN) != "nan" else np.nan
        lines.append(
            f"{pair} & {fmt(bE_md,1)} & {fmt(bN_md,1)} & "
            f"{fmt(r.get('plane_E_b_m_per_px')*1000, 2)}/{fmt(r.get('plane_E_c_m_per_px')*1000, 2)} & "
            f"{fmt(r.get('plane_N_b_m_per_px')*1000, 2)}/{fmt(r.get('plane_N_c_m_per_px')*1000, 2)} & "
            f"{fmt(nE_md,1)} & {fmt(nN_md,1)} & "
            f"{fmt(r.get('valid_fraction'),2)} & {fmt(r.get('stable_corr_median'),3)} \\\\"
        )
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    tex_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✅ Saved LaTeX table: {tex_path}")

    # Save Vindex before/after (easy to re-use in plotting/LaTeX if needed)
    out_vindex = OUTPUT_DIR / "vindex_before_after.csv"
    df_pairs[[
        "date1", "date2", "time_delta_days",
        "vindex_m_per_day_raw",
        "vindex_m_per_day_debiased",
        "vindex_sigma_m_per_day",
        "vindex_sample_n",
        "vindex_corr_median",
        "bias_E_at_glacier_m",
        "bias_N_at_glacier_m",
        "stable_corr_median",
        "valid_fraction"
    ]].to_csv(out_vindex, index=False)
    print(f"✅ Saved Vindex before/after CSV: {out_vindex}")

    # Create figures
    stable_examples_for_plot = {}
    if stable_examples:
        k = list(stable_examples.keys())[0]
        arr = stable_examples[k]
        stable_examples_for_plot[k] = (arr[0], arr[1])
    make_figures(df_pairs, stable_examples_for_plot)
    make_bias_vectors_and_nmad_figure(df_pairs)
    make_multipair_before_after_histograms(df_pairs)
    make_sensitivity_figure(df_pairs)
    print("✅ Saved figures:")
    print(f"   - {OUTPUT_DIR / 'vindex_before_after.pdf'}")
    print(f"   - {OUTPUT_DIR / 'stable_ground_residuals_example.pdf'}")
    print(f"   - {OUTPUT_DIR / 'stable_ground_before_after_multipair.pdf'}")
    print(f"   - {OUTPUT_DIR / 'stable_ground_bias_vectors_nmad.pdf'}")

def create_omega_masks(glacier_poly):
    """
    Create fixed analysis regions (Omega) using negative buffers on the glacier outline.
    Approximation: 100m approx 0.001 deg (conservative).
    
    Returns dict: {'base': poly, 'narrow': poly, 'wide': poly}
    
    - Wide: -100m buffer (approx -0.001 deg)
    - Base: -150m buffer (approx -0.0015 deg) [Primary Ω]
    - Narrow: -200m buffer (approx -0.002 deg)
    
    Note: Buffered in degrees is approximate (non-isotropic), but sufficient for sensitivity testing
    to prove ROI drift isn't driving the signal.
    """
def create_omega_masks(glacier_poly):
    """
    Create fixed analysis regions (Omega) using negative buffers on the glacier outline.
    Approximation: 100m approx 0.001 deg.
    
    Returns dict: {'base': poly, 'narrow': poly, 'wide': poly}
    
    - Wide: -10m buffer (approx -0.0001 deg)
    - Base: -30m buffer (approx -0.0003 deg) [Primary Ω]
    - Narrow: -50m buffer (approx -0.0005 deg)
    """
    deg_10m = 0.0001
    deg_30m = 0.0003
    deg_50m = 0.0005
    
    wide = glacier_poly.buffer(-deg_10m)
    base = glacier_poly.buffer(-deg_30m)
    narrow = glacier_poly.buffer(-deg_50m)
    
    print(f"Mask areas (deg^2): Wide={wide.area:.8f}, Base={base.area:.8f}, Narrow={narrow.area:.8f}", flush=True)
    if base.is_empty:
        print("⚠️  WARNING: Base mask is empty! Buffer too large?", flush=True)
    
    return {
        'wide': wide,
        'base': base,
        'narrow': narrow
    }

def make_sensitivity_figure(df_pairs: pd.DataFrame) -> None:
    """
    Figure 3: Vindex sensitivity to Omega definition.
    Current Vindex (base) vs Narrow vs Wide.
    """
    dates = pd.to_datetime(df_pairs["date2"])
    
    # Check if we have the columns (in case of partial run or old CSV)
    if "vindex_omega_base" not in df_pairs.columns:
        return

    fig, ax = plt.subplots(1, 1, figsize=(7.2, 3.6), dpi=150)
    
    # Plot spread
    ax.fill_between(
        dates, 
        df_pairs["vindex_omega_narrow"], 
        df_pairs["vindex_omega_wide"], 
        color="#2E86AB", 
        alpha=0.15, 
        label="Sensitivity Range (±50m buffer)"
    )
    
    # Plot base
    ax.plot(dates, df_pairs["vindex_omega_base"], "o-", color="#2E86AB", linewidth=2.0, label="Vindex (Ω: -150m buffer)")
    
    # Add error bars from main uncertainty to show scale
    # We use the debiased sigma from the main analysis for context
    ax.errorbar(
        dates,
        df_pairs["vindex_omega_base"],
        yerr=df_pairs["vindex_sigma_m_per_day"], # Use the sigma from Step 2
        fmt="none",
        ecolor="#2E86AB",
        elinewidth=1.0,
        capsize=2,
        alpha=0.5,
        label="Empirical Uncertainty (1σ)"
    )
    
    ax.set_ylabel("Velocity (m d$^{-1}$)", fontsize=18)
    ax.set_xlabel("Date", fontsize=18)
    ax.set_title("Sensitivity of Velocity Index to Analysis Region (Ω)", loc="left", pad=10, fontsize=20)
    ax.tick_params(axis='both', which='major', labelsize=16)
    ax.grid(True, alpha=0.25, linestyle="--")
    ax.legend(loc="best", frameon=True, fancybox=False, framealpha=0.95, fontsize=16)
    
    fig.tight_layout()
    out_png = OUTPUT_DIR / "vindex_sensitivity.png"
    out_pdf = OUTPUT_DIR / "vindex_sensitivity.pdf"
    fig.savefig(out_png, dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(out_pdf, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"   - {out_pdf}")


if __name__ == "__main__":
    main()

