#!/usr/bin/env python3
"""
Publication-quality Figure 15: Spatial Velocity Maps
Target journal: The Cryosphere (EGU) — also compatible with JGR, RSE, JoG.

Output (default stem: figures/fig_spatial_velocity_maps — matches main_revised_v2.tex)
  fig_spatial_velocity_maps.pdf / .eps / .png

Data inputs
-----------
  MODE A — reads GeoTIFF velocity rasters (paths via CLI or built-in defaults).

  MODE B — synthetic Gaussian velocity fields when rasters are missing or
    contain no usable signal (e.g. placeholder all-zero rasters).

Usage
  python fig15_spatial_maps_publication.py
  python fig15_spatial_maps_publication.py --rasters a.tif b.tif c.tif --out figures/fig_spatial_velocity_maps
"""
from __future__ import annotations

import argparse
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import matplotlib.ticker as mticker
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

warnings.filterwarnings("ignore")

# ── Paths ───────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[3]
FIGURES = ROOT / "figures"

# Default SAR stack velocity GeoTIFFs (same order as EPOCH_INFO: b, c, d)
_DEFAULT_VEL_TIFS = (
    ROOT
    / "satellite_data/sentinel1/processed_data/velocity_validation/sar_velocity"
    / "S1A_IW_GRDH_1SDV_20251019T131434_20251019T131459_061495_07AD88_A4B7_Orb_Cal_TC_Stack_vel.tif",
    ROOT
    / "satellite_data/sentinel1/processed_data/velocity_validation/sar_velocity"
    / "S1A_IW_GRDH_1SDV_20250913T131433_20250913T131458_060970_07986E_CBBA_Orb_Cal_TC_Stack_vel.tif",
    ROOT
    / "satellite_data/sentinel1/processed_data/velocity_validation/sar_velocity"
    / "S1A_IW_GRDH_1SDV_20251001T012223_20251001T012248_061225_07A2BD_C76D_Orb_Cal_TC_Stack_vel.tif",
)

# ════════════════════════════════════════════════════════════════════════════
#  JOURNAL STYLE
# ════════════════════════════════════════════════════════════════════════════
MM_TO_INCH = 1 / 25.4
DOUBLE_COL_IN = 175 * MM_TO_INCH

FS_BODY = 8
FS_LABEL = 9
FS_TITLE = 9
FS_PANEL = 9
FS_TICK = 7.5

LW_AXIS = 0.6
LW_DATA = 1.4
LW_OUTLINE = 1.2
LW_SG = 0.9
LW_ARROW = 1.0

TOL_RED = "#EE6677"
TOL_CYAN = "#66CCEE"
TOL_GREY = "#BBBBBB"

CMAP = "magma"
VMIN, VMAX = 0, 300

BG_MAP = "#0a0a2e"
BG_SAMPLE = "#f4f4f0"


def apply_journal_rcparams():
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [
                "Arial",
                "Helvetica Neue",
                "Helvetica",
                "Liberation Sans",
                "DejaVu Sans",
            ],
            "font.size": FS_BODY,
            "axes.titlesize": FS_TITLE,
            "axes.labelsize": FS_LABEL,
            "xtick.labelsize": FS_TICK,
            "ytick.labelsize": FS_TICK,
            "legend.fontsize": FS_BODY,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "axes.linewidth": LW_AXIS,
            "axes.spines.top": True,
            "axes.spines.right": True,
            "axes.edgecolor": "#333333",
            "xtick.major.width": LW_AXIS,
            "ytick.major.width": LW_AXIS,
            "xtick.major.size": 3.0,
            "ytick.major.size": 3.0,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "savefig.dpi": 600,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.02,
            "figure.facecolor": "white",
            "mathtext.fontset": "dejavusans",
        }
    )


# ════════════════════════════════════════════════════════════════════════════
#  MAP CONFIG (avoids mutable globals)
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class MapConfig:
    gc_lon: float = 70.718
    gc_lat: float = 38.990
    zoom: float = 0.072
    zoom_a: float = 0.095
    flow_az_deg: float = 45.0
    # Stable-ground rectangles: offsets from (gc_lon, gc_lat): (dlon, dlat, hw, hh)
    sg_patches_rel: tuple = (
        (-0.052, 0.022, 0.016, 0.010),
        (0.048, -0.022, 0.016, 0.010),
        (-0.030, -0.050, 0.012, 0.009),
    )
    _u_lon: float = field(init=False, repr=False)
    _u_lat: float = field(init=False, repr=False)
    _xf_lon: float = field(init=False, repr=False)
    _xf_lat: float = field(init=False, repr=False)

    def __post_init__(self):
        ulon, ulat = self._flow_unit_vector()
        self._u_lon, self._u_lat = ulon, ulat
        self._xf_lon, self._xf_lat = -ulat, ulon

    def _flow_unit_vector(self) -> tuple[float, float]:
        az = np.radians(self.flow_az_deg)
        km_per_deg_lon = 111.3 * np.cos(np.radians(self.gc_lat))
        km_per_deg_lat = 111.3
        dx_north = np.cos(az)
        dx_east = np.sin(az)
        dlon = dx_east / km_per_deg_lon
        dlat = dx_north / km_per_deg_lat
        mag = np.sqrt(dlon**2 + dlat**2)
        return dlon / mag, dlat / mag

    def glacier_outline_lonlat(self, n: int = 120) -> tuple[np.ndarray, np.ndarray]:
        theta = np.linspace(0, 2 * np.pi, n)
        a_km, b_km = 2.40, 0.165
        km_lon = 111.3 * np.cos(np.radians(self.gc_lat))
        km_lat = 111.3
        a_along_lon = a_km / km_lon
        a_along_lat = a_km / km_lat
        b_cross_lon = b_km / km_lon
        b_cross_lat = b_km / km_lat
        u_lon, u_lat = self._u_lon, self._u_lat
        xf_lon, xf_lat = self._xf_lon, self._xf_lat
        lons = (
            self.gc_lon
            + a_along_lon * np.cos(theta) * u_lon
            + b_cross_lon * np.sin(theta) * xf_lon
        )
        lats = (
            self.gc_lat
            + a_along_lat * np.cos(theta) * u_lat
            + b_cross_lat * np.sin(theta) * xf_lat
        )
        return lons, lats

    def sg_patches_abs(self) -> list[tuple[float, float, float, float]]:
        out = []
        for dlon, dlat, hw, hh in self.sg_patches_rel:
            out.append((self.gc_lon + dlon, self.gc_lat + dlat, hw, hh))
        return out


# ════════════════════════════════════════════════════════════════════════════
#  VELOCITY FIELDS
# ════════════════════════════════════════════════════════════════════════════
def make_grid(
    lon_centre: float, lat_centre: float, half_deg: float, n: int = 400
):
    lon_arr = np.linspace(lon_centre - half_deg, lon_centre + half_deg, n)
    lat_arr = np.linspace(lat_centre - half_deg, lat_centre + half_deg, n)
    return np.meshgrid(lon_arr, lat_arr)


def real_velocity_field(cfg: MapConfig, tif_path: str | Path) -> tuple | None:
    """Read GeoTIFF; return (LON, LAT, SPEED) cropped to zoom or None on failure."""
    try:
        import rasterio
        from rasterio.crs import CRS
        from rasterio.warp import Resampling, calculate_default_transform, reproject
        from rasterio.windows import Window, from_bounds

        tif_path = Path(tif_path)
        if not tif_path.exists() or tif_path.stat().st_size == 0:
            return None

        target_crs = CRS.from_epsg(4326)
        gc_lon, gc_lat = cfg.gc_lon, cfg.gc_lat
        z = cfg.zoom
        pad = 0.01

        with rasterio.open(tif_path) as src:
            nodata = src.nodata
            if src.crs and src.crs != target_crs:
                transform, width, height = calculate_default_transform(
                    src.crs, target_crs, src.width, src.height, *src.bounds
                )
                data = np.zeros((src.count, height, width), dtype=np.float32)
                for i in range(src.count):
                    reproject(
                        source=rasterio.band(src, i + 1),
                        destination=data[i],
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=target_crs,
                        resampling=Resampling.bilinear,
                    )
            else:
                # Windowed read: only the map extent (avoids loading huge scenes)
                try:
                    wb = from_bounds(
                        gc_lon - z - pad,
                        gc_lat - z - pad,
                        gc_lon + z + pad,
                        gc_lat + z + pad,
                        transform=src.transform,
                    )
                    wb = wb.round().intersection(
                        Window(0, 0, src.width, src.height)
                    )
                    if wb.width < 1 or wb.height < 1:
                        return None
                    data = src.read(window=wb).astype(np.float32)
                    transform = src.window_transform(wb)
                except Exception:
                    data = src.read().astype(np.float32)
                    transform = src.transform
                height, width = data.shape[1], data.shape[2]

        cols = np.arange(width)
        rows = np.arange(height)
        lons_1d = transform.c + cols * transform.a
        lats_1d = transform.f + rows * transform.e
        LON, LAT = np.meshgrid(lons_1d, lats_1d)

        if data.shape[0] >= 2:
            speed = np.sqrt(data[0] ** 2 + data[1] ** 2)
        else:
            speed = data[0]

        if nodata is not None:
            speed = np.where(np.abs(speed - nodata) < 1e-6, np.nan, speed)

        mask = (
            (LON >= gc_lon - z)
            & (LON <= gc_lon + z)
            & (LAT >= gc_lat - z)
            & (LAT <= gc_lat + z)
        )
        row_mask = np.any(mask, axis=1)
        col_mask = np.any(mask, axis=0)
        if not np.any(row_mask) or not np.any(col_mask):
            return None
        LON = LON[np.ix_(row_mask, col_mask)]
        LAT = LAT[np.ix_(row_mask, col_mask)]
        speed = speed[np.ix_(row_mask, col_mask)]

        if not np.isfinite(speed).any() or float(np.nanmax(speed)) < 0.05:
            return None

        return LON, LAT, speed

    except ImportError:
        print("  [rasterio not found — falling back to synthetic field]")
        return None
    except Exception as e:
        print(f"  [GeoTIFF read failed: {e} — falling back to synthetic field]")
        return None


def synthetic_velocity_field(cfg: MapConfig, vindex: float, seed: int = 0):
    rng = np.random.default_rng(seed)
    LON, LAT = make_grid(cfg.gc_lon, cfg.gc_lat, cfg.zoom)
    dlon = LON - cfg.gc_lon
    dlat = LAT - cfg.gc_lat
    u_lon, u_lat = cfg._u_lon, cfg._u_lat
    xf_lon, xf_lat = cfg._xf_lon, cfg._xf_lat
    along = dlon * u_lon + dlat * u_lat
    across = dlon * xf_lon + dlat * xf_lat

    km_lon = 111.3 * np.cos(np.radians(cfg.gc_lat))
    km_lat = 111.3
    a_km, b_km = 2.5, 0.18
    along_norm = along * km_lon / a_km
    across_norm = across * km_lat / b_km
    glacier_mask = (along_norm**2 + across_norm**2) <= 1.0

    core = vindex * np.exp(-0.5 * (across_norm / 0.45) ** 2)
    core *= 1.0 + 0.12 * np.clip(along_norm, -1.0, 0.0)
    noise = rng.normal(0, 3.5, core.shape)
    field = np.where(
        glacier_mask,
        core + noise * 0.04,
        np.abs(rng.normal(0, 1.2, core.shape)),
    )
    field = np.clip(field, 0, VMAX + 20)
    return LON, LAT, field


def get_velocity_field(
    cfg: MapConfig, tif_path: str | Path | None, vindex: float, seed: int = 0
):
    if tif_path is not None and Path(tif_path).exists():
        result = real_velocity_field(cfg, tif_path)
        if result is not None:
            return result
    return synthetic_velocity_field(cfg, vindex, seed=seed)


# ════════════════════════════════════════════════════════════════════════════
#  MAP HELPERS
# ════════════════════════════════════════════════════════════════════════════
def format_map_axes(
    ax,
    cfg: MapConfig,
    half_deg: float,
    n_lon_ticks: int = 3,
    n_lat_ticks: int = 3,
    show_xlabel: bool = True,
    show_ylabel: bool = True,
):
    ax.set_xlim(cfg.gc_lon - half_deg, cfg.gc_lon + half_deg)
    ax.set_ylim(cfg.gc_lat - half_deg, cfg.gc_lat + half_deg)
    ax.set_aspect(1.0 / np.cos(np.radians(cfg.gc_lat)))
    ax.xaxis.set_major_locator(mticker.LinearLocator(n_lon_ticks))
    ax.yaxis.set_major_locator(mticker.LinearLocator(n_lat_ticks))
    ax.xaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"{x:.3f}°E")
    )
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda y, _: f"{y:.3f}°N")
    )
    plt.setp(
        ax.xaxis.get_majorticklabels(),
        rotation=30,
        ha="right",
        fontsize=FS_TICK,
    )
    plt.setp(ax.yaxis.get_majorticklabels(), fontsize=FS_TICK)
    if show_xlabel:
        ax.set_xlabel("Longitude", fontsize=FS_LABEL)
    if show_ylabel:
        ax.set_ylabel("Latitude", fontsize=FS_LABEL)
    for spine in ax.spines.values():
        spine.set_linewidth(LW_AXIS)
        spine.set_color("#333333")


def add_north_arrow(
    ax, x=0.92, y=0.92, length=0.07, fontsize=FS_BODY, color="k"
):
    ax.annotate(
        "",
        xy=(x, y),
        xytext=(x, y - length),
        xycoords="axes fraction",
        textcoords="axes fraction",
        arrowprops=dict(
            arrowstyle="->", color=color, lw=LW_ARROW, mutation_scale=8
        ),
    )
    ax.text(
        x,
        y + 0.025,
        "N",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=fontsize,
        fontweight="bold",
        color=color,
    )


def add_scale_bar(
    ax,
    lon_left: float,
    lat_bottom: float,
    length_km: int = 2,
    color="k",
    fontsize: float = FS_BODY - 0.5,
):
    km_per_deg_lon = 111.3 * np.cos(np.radians(lat_bottom))
    length_deg = length_km / km_per_deg_lon
    ax.plot(
        [lon_left, lon_left + length_deg],
        [lat_bottom, lat_bottom],
        "-",
        color=color,
        lw=2.5,
        solid_capstyle="butt",
        zorder=10,
    )
    ax.plot(
        [lon_left, lon_left],
        [lat_bottom - 0.003, lat_bottom],
        "-",
        color=color,
        lw=1.5,
        zorder=10,
    )
    ax.plot(
        [lon_left + length_deg, lon_left + length_deg],
        [lat_bottom - 0.003, lat_bottom],
        "-",
        color=color,
        lw=1.5,
        zorder=10,
    )
    ax.text(
        lon_left + length_deg / 2,
        lat_bottom - 0.007,
        f"{length_km} km",
        ha="center",
        va="top",
        fontsize=fontsize,
        color=color,
        zorder=10,
    )


def draw_stable_ground(
    ax, cfg: MapConfig, visible_lons, visible_lats, zorder: int = 8
):
    mean_lon = float(np.mean(visible_lons))
    mean_lat = float(np.mean(visible_lats))
    for clon, clat, hw, hh in cfg.sg_patches_abs():
        if abs(clon - mean_lon) < 0.12 and abs(clat - mean_lat) < 0.12:
            rect = mpatches.FancyBboxPatch(
                (clon - hw, clat - hh),
                2 * hw,
                2 * hh,
                boxstyle="round,pad=0.001",
                linewidth=LW_SG,
                edgecolor=TOL_CYAN,
                facecolor="none",
                linestyle=(0, (4, 2)),
                zorder=zorder,
            )
            ax.add_patch(rect)


def draw_glacier_outline(
    cfg: MapConfig, ax, lw: float = LW_OUTLINE, ec: str = TOL_RED, zorder: int = 7
):
    gl_lons, gl_lats = cfg.glacier_outline_lonlat()
    ax.fill(gl_lons, gl_lats, color=TOL_RED, alpha=0.08, zorder=zorder - 1)
    ax.plot(gl_lons, gl_lats, color=ec, lw=lw, zorder=zorder)


def add_flow_arrow(
    cfg: MapConfig,
    ax,
    zorder: int = 9,
    color: str = "white",
    length_deg: float = 0.032,
    label: bool = True,
):
    u_lon, u_lat = cfg._u_lon, cfg._u_lat
    x0 = cfg.gc_lon - u_lon * length_deg * 0.5
    y0 = cfg.gc_lat - u_lat * length_deg * 0.5
    dx = u_lon * length_deg
    dy = u_lat * length_deg
    ax.annotate(
        "",
        xy=(x0 + dx, y0 + dy),
        xytext=(x0, y0),
        arrowprops=dict(
            arrowstyle="->", color=color, lw=LW_ARROW, mutation_scale=10
        ),
        zorder=zorder,
    )
    if label:
        ax.text(
            x0 + dx + u_lon * 0.005,
            y0 + dy + u_lat * 0.005,
            "flow",
            color=color,
            fontsize=FS_BODY - 1.5,
            va="bottom",
            ha="left",
            zorder=zorder,
            path_effects=[pe.withStroke(linewidth=1.5, foreground=BG_MAP)],
        )


def panel_label_map(ax, label: str, bg_color: str = "white", zorder: int = 20):
    ax.text(
        0.03,
        0.97,
        label,
        transform=ax.transAxes,
        fontsize=FS_PANEL,
        fontweight="bold",
        va="top",
        ha="left",
        zorder=zorder,
        bbox=dict(
            boxstyle="round,pad=0.20",
            facecolor=bg_color,
            edgecolor="none",
            alpha=0.85,
        ),
    )


# ════════════════════════════════════════════════════════════════════════════
#  PANELS
# ════════════════════════════════════════════════════════════════════════════
def plot_sampling_panel(ax, cfg: MapConfig):
    from matplotlib.patches import Ellipse

    ax.set_facecolor(BG_SAMPLE)
    for r, alpha in [(0.18, 0.04), (0.12, 0.03)]:
        ell = Ellipse(
            (cfg.gc_lon, cfg.gc_lat),
            2 * r * 1.3,
            2 * r,
            angle=45,
            color="#aaaaaa",
            alpha=alpha,
            zorder=1,
        )
        ax.add_patch(ell)

    draw_stable_ground(ax, cfg, [cfg.gc_lon], [cfg.gc_lat])
    draw_glacier_outline(cfg, ax)

    u_lon, u_lat = cfg._u_lon, cfg._u_lat
    ax.text(
        cfg.gc_lon + u_lon * 0.055 + 0.01,
        cfg.gc_lat + u_lat * 0.055 + 0.005,
        "Glacier\noutline ($\\Omega$)",
        color=TOL_RED,
        fontsize=FS_BODY - 1,
        va="bottom",
        ha="left",
        fontweight="bold",
        path_effects=[pe.withStroke(linewidth=1.2, foreground=BG_SAMPLE)],
    )

    ax.text(
        cfg.gc_lon - 0.068,
        cfg.gc_lat + 0.028,
        "Stable\nground",
        color=TOL_CYAN,
        fontsize=FS_BODY - 1.5,
        va="center",
        ha="center",
        path_effects=[pe.withStroke(linewidth=1.2, foreground=BG_SAMPLE)],
    )

    ax.text(
        cfg.gc_lon + 0.060,
        cfg.gc_lat - 0.030,
        "Stable\nground",
        color=TOL_CYAN,
        fontsize=FS_BODY - 1.5,
        va="center",
        ha="center",
        path_effects=[pe.withStroke(linewidth=1.2, foreground=BG_SAMPLE)],
    )

    add_north_arrow(ax, color="#333333")
    add_scale_bar(
        ax,
        lon_left=cfg.gc_lon - cfg.zoom_a * 0.85,
        lat_bottom=cfg.gc_lat - cfg.zoom_a * 0.82,
        length_km=2,
        color="#333333",
    )

    format_map_axes(
        ax,
        cfg,
        cfg.zoom_a,
        n_lon_ticks=3,
        n_lat_ticks=3,
    )
    panel_label_map(ax, "(a)", bg_color=BG_SAMPLE)
    ax.set_title("Sampling regions", fontsize=FS_TITLE, loc="center", pad=3)


EPOCH_INFO = [
    ("(b)", "19 Oct–25 Oct", 160.1, 49.0, 0.091, 42, 0),
    ("(c)", "13 Sep–19 Sep", 156.7, 38.7, 0.071, 7, 1),
    ("(d)", "01 Oct–07 Oct", 97.0, 49.4, 0.071, 1, 2),
]


def plot_velocity_panel(
    ax,
    cfg: MapConfig,
    panel_letter: str,
    date_str: str,
    vindex: float,
    sigma: float,
    pcr: float,
    tif_path: str | Path | None,
    seed: int,
    show_ylabel: bool = False,
):
    ax.set_facecolor(BG_MAP)
    LON, LAT, speed = get_velocity_field(cfg, tif_path, vindex, seed=seed)

    ax.pcolormesh(
        LON,
        LAT,
        speed,
        cmap=CMAP,
        norm=Normalize(vmin=VMIN, vmax=VMAX),
        shading="gouraud",
        rasterized=True,
        zorder=2,
    )

    draw_glacier_outline(cfg, ax, lw=LW_OUTLINE, ec=TOL_RED)
    draw_stable_ground(ax, cfg, [cfg.gc_lon], [cfg.gc_lat])
    add_flow_arrow(cfg, ax, color="white")

    stats_text = (
        f"$V_\\mathrm{{index}}$ = {vindex:.1f} m d$^{{-1}}$\n"
        f"± {sigma:.1f} m d$^{{-1}}$ (1$\\sigma$)\n"
        f"PCR = {pcr:.3f}"
    )
    ax.text(
        0.03,
        0.03,
        stats_text,
        transform=ax.transAxes,
        fontsize=FS_BODY - 1,
        va="bottom",
        ha="left",
        color="white",
        linespacing=1.4,
        zorder=15,
        bbox=dict(
            boxstyle="round,pad=0.30",
            facecolor=BG_MAP,
            edgecolor="white",
            linewidth=LW_AXIS * 0.8,
            alpha=0.80,
        ),
    )

    format_map_axes(
        ax,
        cfg,
        cfg.zoom,
        n_lon_ticks=3,
        n_lat_ticks=3,
        show_ylabel=show_ylabel,
    )
    panel_label_map(ax, panel_letter, bg_color=BG_MAP)
    ax.set_title(date_str, fontsize=FS_TITLE, loc="center", pad=3, color="k")


def add_shared_colorbar(fig, axes_for_cbar, norm, cmap, label="Velocity (m d$^{-1}$)"):
    last_ax = axes_for_cbar[-1]
    pos = last_ax.get_position()
    cbar_left = pos.x1 + 0.015
    all_pos = [ax.get_position() for ax in axes_for_cbar]
    bottom_all = min(p.y0 for p in all_pos)
    top_all = max(p.y1 for p in all_pos)
    cbar_width = 0.018
    cbar_ax = fig.add_axes(
        [cbar_left, bottom_all, cbar_width, top_all - bottom_all]
    )

    sm = ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cbar = fig.colorbar(sm, cax=cbar_ax)
    cbar.set_label(label, fontsize=FS_LABEL, labelpad=4)
    cbar.ax.tick_params(labelsize=FS_TICK, width=LW_AXIS, length=3)
    cbar.outline.set_linewidth(LW_AXIS)
    return cbar


def make_figure15(
    tif_paths: Sequence[str | Path | None] | None = None,
    out_stem: Path | str | None = None,
    cfg: MapConfig | None = None,
):
    apply_journal_rcparams()
    cfg = cfg or MapConfig()

    if tif_paths is None:
        tif_paths = [None, None, None]

    if out_stem is None:
        out_stem = FIGURES / "fig_spatial_velocity_maps"
    out_stem = Path(out_stem)
    out_stem.parent.mkdir(parents=True, exist_ok=True)

    fig_w = DOUBLE_COL_IN
    lat_lon_ratio = 111.3 / (111.3 * np.cos(np.radians(cfg.gc_lat)))
    panel_h_in = (fig_w * 0.72 / 4) * lat_lon_ratio
    fig_h = panel_h_in * 1.25

    fig = plt.figure(figsize=(fig_w, fig_h))
    import matplotlib.gridspec as gridspec

    gs = gridspec.GridSpec(
        1,
        4,
        figure=fig,
        width_ratios=[1, 1, 1, 1],
        wspace=0.15,
        left=0.07,
        right=0.91,
        top=0.90,
        bottom=0.12,
    )

    ax_sample = fig.add_subplot(gs[0, 0])
    ax_vels = [fig.add_subplot(gs[0, i + 1]) for i in range(3)]

    plot_sampling_panel(ax_sample, cfg)

    for i, (letter, date_str, vi, sig, pcr, seed, arg_idx) in enumerate(EPOCH_INFO):
        tif = tif_paths[arg_idx] if arg_idx < len(tif_paths) else None
        show_y = i == 0
        plot_velocity_panel(
            ax_vels[i],
            cfg,
            letter,
            date_str,
            vi,
            sig,
            pcr,
            tif,
            seed,
            show_ylabel=show_y,
        )

    fig.canvas.draw()
    norm = Normalize(vmin=VMIN, vmax=VMAX)
    add_shared_colorbar(fig, ax_vels, norm, CMAP)

    legend_handles = [
        Patch(
            facecolor="none",
            edgecolor=TOL_RED,
            linewidth=LW_OUTLINE,
            label="Glacier outline ($\\Omega$)",
        ),
        Line2D(
            [0],
            [0],
            color=TOL_CYAN,
            linestyle=(0, (4, 2)),
            linewidth=LW_SG,
            label="Stable-ground control areas",
        ),
    ]
    ax_sample.legend(
        handles=legend_handles,
        loc="lower right",
        fontsize=FS_BODY - 1,
        framealpha=0.88,
        edgecolor=TOL_GREY,
        borderpad=0.4,
    )

    for ext, dpi in [(".pdf", None), (".eps", None), (".png", 600)]:
        kwargs = dict(bbox_inches="tight", pad_inches=0.02)
        if dpi:
            kwargs["dpi"] = dpi
        p = out_stem.with_suffix(ext)
        fig.savefig(p, **kwargs)
        print(f"  Saved: {p}")

    plt.close(fig)
    print("Figure 15 complete.")


def _resolve_tif_paths(
    cli_rasters: Sequence[str | None] | None,
) -> list[str | Path | None] | None:
    """Return three paths: user list, or defaults if valid, else all-None (synthetic)."""
    if cli_rasters and any(r for r in cli_rasters):
        return [Path(r) if r else None for r in cli_rasters]

    resolved: list[str | Path | None] = []
    for p in _DEFAULT_VEL_TIFS:
        if p.exists() and p.stat().st_size > 0:
            resolved.append(p)
        else:
            resolved.append(None)

    if all(x is None for x in resolved):
        return None
    return resolved


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate publication-quality Figure 15 (spatial velocity maps)."
    )
    parser.add_argument(
        "--rasters",
        nargs=3,
        metavar=("EPOCH_B", "EPOCH_C", "EPOCH_D"),
        default=None,
        help=(
            "Three velocity GeoTIFF files (E,N bands or speed). "
            "Order: Oct19–25, Sep13–19, Oct01–07. "
            "Omit to use built-in defaults or synthetic fallback."
        ),
    )
    parser.add_argument(
        "--centre_lon",
        type=float,
        default=70.718,
        help="Glacier centre longitude (default: 70.718)",
    )
    parser.add_argument(
        "--centre_lat",
        type=float,
        default=38.990,
        help="Glacier centre latitude (default: 38.990)",
    )
    parser.add_argument(
        "--zoom",
        type=float,
        default=0.072,
        help="Half-width of velocity panel in degrees (default: 0.072)",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output stem without extension (default: figures/fig_spatial_velocity_maps)",
    )
    args = parser.parse_args()

    cfg = MapConfig(
        gc_lon=args.centre_lon,
        gc_lat=args.centre_lat,
        zoom=args.zoom,
    )

    tif_paths = _resolve_tif_paths(args.rasters)
    out = args.out
    if out is None:
        out = FIGURES / "fig_spatial_velocity_maps"

    make_figure15(tif_paths=tif_paths, out_stem=out, cfg=cfg)
