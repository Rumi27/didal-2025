#!/usr/bin/env python3
"""
fig15_spatial_maps_publication_v2.py
====================================
Publication-quality Figure 15: Spatial Velocity Maps (v2).

Fixes vs v1: higher grid resolution (GRID_N=1200), transparent low-velocity
magma so hillshade shows through, off-glacier synthetic = NaN, synthetic or
real DEM hillshade background.

Output (default: figures/fig_spatial_velocity_maps — matches main_revised_v2.tex)

  MODE B (default): synthetic velocity + synthetic hillshade
  MODE A: --rasters + optional --glacier + optional --dem

Dependencies: numpy, matplotlib; optional rasterio, geopandas, scipy
  pip install rasterio geopandas scipy
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
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[3]
FIGURES = ROOT / "figures"

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

MM = 1 / 25.4
DOUBLE_COL_IN = 175 * MM

FS_BODY = 8
FS_LABEL = 9
FS_TITLE = 9
FS_TICK = 7.5
FS_PANEL = 9

LW_AXIS = 0.6
LW_OUTLINE = 1.2
LW_SG = 0.9

TOL_RED = "#EE6677"
TOL_CYAN = "#66CCEE"
TOL_GREY = "#BBBBBB"

VMIN, VMAX = 0, 300
BG_VEL_PANEL = "#05001a"
BG_SAMPLE = "#f0ede8"

GRID_N = 1200
GRID_N_PANEL_A = 600


def make_transparent_magma(threshold: float = 10.0, vmax: float = 300.0):
    """Magma colormap with alpha ramp so low velocities reveal hillshade below."""
    base = plt.cm.magma
    n = 512
    vals = np.linspace(0, 1, n)
    rgba = base(vals)
    v_arr = vals * vmax
    fade = np.clip((v_arr - threshold) / 20.0, 0, 1)
    rgba[:, 3] = fade
    return mcolors.ListedColormap(rgba, name="magma_transparent")


CMAP_VEL = make_transparent_magma(threshold=10.0, vmax=300.0)
CMAP_HILL = plt.cm.Greys_r


def apply_rcparams():
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
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "axes.linewidth": LW_AXIS,
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


@dataclass
class MapConfig:
    gc_lon: float = 70.718
    gc_lat: float = 38.990
    zoom_a: float = 0.095
    zoom_v: float = 0.072
    flow_az_deg: float = 45.0
    grid_n_vel: int = GRID_N
    sg_patches_rel: tuple = (
        (-0.052, 0.022, 0.016, 0.010),
        (0.048, -0.022, 0.016, 0.010),
        (-0.030, -0.050, 0.012, 0.009),
    )
    _u_lon: float = field(init=False, repr=False)
    _u_lat: float = field(init=False, repr=False)
    _x_lon: float = field(init=False, repr=False)
    _x_lat: float = field(init=False, repr=False)

    def __post_init__(self):
        km_lon = 111.3 * np.cos(np.radians(self.gc_lat))
        km_lat = 111.3
        az = np.radians(self.flow_az_deg)
        dx_e = np.sin(az)
        dx_n = np.cos(az)
        ulon = dx_e / km_lon
        ulat = dx_n / km_lat
        mag = np.sqrt(ulon**2 + ulat**2)
        self._u_lon, self._u_lat = ulon / mag, ulat / mag
        self._x_lon, self._x_lat = -self._u_lat, self._u_lon

    @property
    def km_per_deg_lon(self) -> float:
        return 111.3 * np.cos(np.radians(self.gc_lat))

    @property
    def km_per_deg_lat(self) -> float:
        return 111.3

    def glacier_outline(self, n: int = 200) -> tuple[np.ndarray, np.ndarray]:
        theta = np.linspace(0, 2 * np.pi, n)
        a_km, b_km = 2.40, 0.165
        a_lon = a_km / self.km_per_deg_lon
        a_lat = a_km / self.km_per_deg_lat
        b_lon = b_km / self.km_per_deg_lon
        b_lat = b_km / self.km_per_deg_lat
        u, v = self._u_lon, self._u_lat
        x, y = self._x_lon, self._x_lat
        lons = (
            self.gc_lon
            + a_lon * np.cos(theta) * u
            + b_lon * np.sin(theta) * x
        )
        lats = (
            self.gc_lat
            + a_lat * np.cos(theta) * v
            + b_lat * np.sin(theta) * y
        )
        return lons, lats

    def sg_patches_abs(self) -> list[tuple[float, float, float, float]]:
        out = []
        for dlon, dlat, hw, hh in self.sg_patches_rel:
            out.append((self.gc_lon + dlon, self.gc_lat + dlat, hw, hh))
        return out

    def make_grid(self, half_deg: float, n: int):
        lon = np.linspace(self.gc_lon - half_deg, self.gc_lon + half_deg, n)
        lat = np.linspace(self.gc_lat - half_deg, self.gc_lat + half_deg, n)
        return np.meshgrid(lon, lat)

    def glacier_mask_grid(self, LON: np.ndarray, LAT: np.ndarray) -> np.ndarray:
        dlon = LON - self.gc_lon
        dlat = LAT - self.gc_lat
        along = dlon * self._u_lon + dlat * self._u_lat
        across = dlon * self._x_lon + dlat * self._x_lat
        a_km, b_km = 2.50, 0.185
        along_km = along * self.km_per_deg_lon
        across_km = across * self.km_per_deg_lat
        return (along_km / a_km) ** 2 + (across_km / b_km) ** 2 <= 1.0


def synthetic_hillshade(cfg: MapConfig, LON: np.ndarray, LAT: np.ndarray) -> np.ndarray:
    dlon = LON - cfg.gc_lon
    dlat = LAT - cfg.gc_lat
    along = dlon * cfg._u_lon + dlat * cfg._u_lat
    across = dlon * cfg._x_lon + dlat * cfg._x_lat
    valley_depth_km = 0.8
    across_km = across * cfg.km_per_deg_lat
    elev = (across_km / valley_depth_km) ** 2
    elev -= 0.5 * along * cfg.km_per_deg_lat
    rng = np.random.default_rng(seed=42)
    elev += 0.08 * rng.standard_normal(elev.shape)
    dy, dx = np.gradient(elev)
    azimuth_rad = np.radians(315)
    altitude_rad = np.radians(45)
    light = np.array(
        [
            np.cos(altitude_rad) * np.cos(azimuth_rad),
            np.cos(altitude_rad) * np.sin(azimuth_rad),
            np.sin(altitude_rad),
        ]
    )
    slope = np.sqrt(dx**2 + dy**2)
    nz = 1.0 / np.sqrt(1 + slope**2)
    nx = -dx * nz
    ny = -dy * nz
    intensity = nx * light[0] + ny * light[1] + nz * light[2]
    intensity = np.clip(intensity, 0, 1)
    return 0.3 + 0.7 * intensity


def real_hillshade(
    dem_tif: str | Path, LON: np.ndarray, LAT: np.ndarray, cfg: MapConfig
) -> np.ndarray | None:
    try:
        from scipy.interpolate import RegularGridInterpolator

        import rasterio
        from rasterio.crs import CRS
        from rasterio.warp import Resampling, calculate_default_transform, reproject

        dem_tif = Path(dem_tif)
        if not dem_tif.exists():
            return None

        tgt_crs = CRS.from_epsg(4326)
        with rasterio.open(dem_tif) as src:
            if src.crs is None:
                return None
            if src.crs != tgt_crs:
                transform, w, h = calculate_default_transform(
                    src.crs, tgt_crs, src.width, src.height, *src.bounds
                )
                data = np.zeros((1, h, w), dtype=np.float32)
                reproject(
                    rasterio.band(src, 1),
                    data[0],
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=tgt_crs,
                    resampling=Resampling.bilinear,
                )
            else:
                from rasterio.windows import Window, from_bounds

                pad = 0.02
                z = max(cfg.zoom_v, cfg.zoom_a)
                wb = from_bounds(
                    cfg.gc_lon - z - pad,
                    cfg.gc_lat - z - pad,
                    cfg.gc_lon + z + pad,
                    cfg.gc_lat + z + pad,
                    transform=src.transform,
                )
                wb = wb.round().intersection(Window(0, 0, src.width, src.height))
                if wb.width < 1 or wb.height < 1:
                    data = src.read(1).astype(np.float32)[np.newaxis]
                else:
                    data = src.read(1, window=wb).astype(np.float32)[np.newaxis]
                transform = (
                    src.window_transform(wb)
                    if wb.width >= 1
                    else src.transform
                )
            h, w = data.shape[1], data.shape[2]
            lons_1d = transform.c + np.arange(w) * transform.a
            lats_1d = transform.f + np.arange(h) * transform.e

        dem = data[0]
        dy, dx = np.gradient(dem)
        light_az = np.radians(315)
        light_el = np.radians(45)
        lv = np.array(
            [
                np.cos(light_el) * np.cos(light_az),
                np.cos(light_el) * np.sin(light_az),
                np.sin(light_el),
            ]
        )
        slope = np.sqrt(dx**2 + dy**2)
        nz = 1 / np.sqrt(1 + slope**2)
        nx, ny = -dx * nz, -dy * nz
        hs = np.clip(nx * lv[0] + ny * lv[1] + nz * lv[2], 0, 1)

        lats_desc = lats_1d[::-1]
        hs_flip = hs[::-1]
        interp = RegularGridInterpolator(
            (lats_desc, lons_1d),
            hs_flip,
            method="linear",
            bounds_error=False,
            fill_value=0.5,
        )
        pts = np.column_stack([LAT.ravel(), LON.ravel()])
        hs_interp = interp(pts).reshape(LON.shape)
        return 0.3 + 0.7 * hs_interp
    except Exception as e:
        print(f"  [Hillshade from DEM failed ({e}) — using synthetic]")
        return None


def real_velocity_field(
    cfg: MapConfig, tif_path: str | Path, LON: np.ndarray, LAT: np.ndarray
) -> np.ndarray | None:
    try:
        from scipy.interpolate import RegularGridInterpolator

        import rasterio
        from rasterio.crs import CRS
        from rasterio.warp import Resampling, calculate_default_transform, reproject
        from rasterio.windows import Window, from_bounds

        tif_path = Path(tif_path)
        if not tif_path.exists() or tif_path.stat().st_size == 0:
            return None

        tgt_crs = CRS.from_epsg(4326)
        pad = 0.01
        z = cfg.zoom_v
        lon_min = cfg.gc_lon - z - pad
        lon_max = cfg.gc_lon + z + pad
        lat_min = cfg.gc_lat - z - pad
        lat_max = cfg.gc_lat + z + pad

        with rasterio.open(tif_path) as src:
            nodata = src.nodata
            if src.crs is not None and src.crs != tgt_crs:
                transform, w, h = calculate_default_transform(
                    src.crs, tgt_crs, src.width, src.height, *src.bounds
                )
                data = np.zeros((src.count, h, w), dtype=np.float32)
                for i in range(src.count):
                    reproject(
                        rasterio.band(src, i + 1),
                        data[i],
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=tgt_crs,
                        resampling=Resampling.bilinear,
                    )
            else:
                wb = from_bounds(lon_min, lat_min, lon_max, lat_max, src.transform)
                wb = wb.round().intersection(Window(0, 0, src.width, src.height))
                if wb.width < 1 or wb.height < 1:
                    return None
                data = src.read(window=wb).astype(np.float32)
                transform = src.window_transform(wb)

            h, w = data.shape[1], data.shape[2]
            lons_1d = transform.c + np.arange(w) * transform.a
            lats_1d = transform.f + np.arange(h) * transform.e

            if data.shape[0] >= 2:
                speed = np.sqrt(data[0] ** 2 + data[1] ** 2)
            else:
                speed = data[0]

            if nodata is not None:
                speed = np.where(np.abs(speed - nodata) < 1e-6, np.nan, speed)

        if not np.isfinite(speed).any() or float(np.nanmax(speed)) < 0.05:
            return None

        lats_desc = lats_1d[::-1]
        spd_flip = speed[::-1]
        interp = RegularGridInterpolator(
            (lats_desc, lons_1d),
            spd_flip,
            method="linear",
            bounds_error=False,
            fill_value=np.nan,
        )
        pts = np.column_stack([LAT.ravel(), LON.ravel()])
        spd = interp(pts).reshape(LON.shape)
        return spd
    except Exception as e:
        print(f"  [GeoTIFF velocity read failed ({e}) — synthetic fallback]")
        return None


def synthetic_velocity_field(
    cfg: MapConfig, LON: np.ndarray, LAT: np.ndarray, vindex: float, seed: int = 0
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    dlon = LON - cfg.gc_lon
    dlat = LAT - cfg.gc_lat
    along_km = (dlon * cfg._u_lon + dlat * cfg._u_lat) * cfg.km_per_deg_lon
    across_km = (dlon * cfg._x_lon + dlat * cfg._x_lat) * cfg.km_per_deg_lat
    gl_mask = cfg.glacier_mask_grid(LON, LAT)
    sigma_across = 0.080
    sigma_along = 2.0
    profile = np.exp(-0.5 * (across_km / sigma_across) ** 2) * np.exp(
        -0.5 * (along_km / sigma_along) ** 2
    )
    pmax = float(np.nanmax(profile[gl_mask])) if gl_mask.any() else 1.0
    vel = vindex * profile / (pmax if pmax > 0 else 1.0)
    vel += rng.normal(0, vindex * 0.03, vel.shape)
    vel = np.clip(vel, 0, VMAX + 20)
    vel[~gl_mask] = np.nan
    return vel


def get_velocity(
    cfg: MapConfig,
    tif_path: str | Path | None,
    LON: np.ndarray,
    LAT: np.ndarray,
    vindex: float,
    seed: int = 0,
) -> np.ndarray:
    if tif_path is not None and Path(tif_path).exists():
        spd = real_velocity_field(cfg, tif_path, LON, LAT)
        if spd is not None:
            return spd
    return synthetic_velocity_field(cfg, LON, LAT, vindex, seed=seed)


def load_glacier_outline(
    shp_path: str | Path, cfg: MapConfig
) -> tuple[np.ndarray, np.ndarray] | None:
    try:
        import geopandas as gpd

        gdf = gpd.read_file(shp_path).to_crs("EPSG:4326")
        if hasattr(gdf, "union_all"):
            geom = gdf.union_all()
        else:
            geom = gdf.unary_union
        from shapely.geometry import MultiPolygon, Polygon

        if isinstance(geom, MultiPolygon):
            geom = max(geom.geoms, key=lambda p: p.area)
        if not isinstance(geom, Polygon):
            return None
        coords = list(geom.exterior.coords)
        lons = np.array([c[0] for c in coords])
        lats = np.array([c[1] for c in coords])
        return lons, lats
    except Exception as e:
        print(f"  [Shapefile read failed ({e}) — synthetic outline]")
        return None


def format_axes(
    cfg: MapConfig,
    ax,
    half: float,
    nticks: int = 3,
    xlabel: bool = True,
    ylabel: bool = True,
):
    ax.set_xlim(cfg.gc_lon - half, cfg.gc_lon + half)
    ax.set_ylim(cfg.gc_lat - half, cfg.gc_lat + half)
    ax.set_aspect(1.0 / np.cos(np.radians(cfg.gc_lat)))
    ax.xaxis.set_major_locator(mticker.LinearLocator(nticks))
    ax.yaxis.set_major_locator(mticker.LinearLocator(nticks))
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.3f}°E"))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.3f}°N"))
    plt.setp(
        ax.xaxis.get_majorticklabels(),
        rotation=30,
        ha="right",
        fontsize=FS_TICK,
    )
    plt.setp(ax.yaxis.get_majorticklabels(), fontsize=FS_TICK)
    if xlabel:
        ax.set_xlabel("Longitude", fontsize=FS_LABEL)
    if ylabel:
        ax.set_ylabel("Latitude", fontsize=FS_LABEL)
    for sp in ax.spines.values():
        sp.set_linewidth(LW_AXIS)
        sp.set_color("#333333")


def north_arrow(ax, x=0.91, y=0.93, length=0.07, color="k"):
    ax.annotate(
        "",
        xy=(x, y),
        xytext=(x, y - length),
        xycoords="axes fraction",
        textcoords="axes fraction",
        arrowprops=dict(arrowstyle="->", color=color, lw=1.0, mutation_scale=8),
    )
    ax.text(
        x,
        y + 0.02,
        "N",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=FS_BODY,
        fontweight="bold",
        color=color,
    )


def scale_bar(ax, cfg: MapConfig, lon0: float, lat0: float, km: int = 2, color="k"):
    deg = km / cfg.km_per_deg_lon
    ax.plot(
        [lon0, lon0 + deg],
        [lat0, lat0],
        "-",
        color=color,
        lw=2.5,
        solid_capstyle="butt",
        zorder=10,
    )
    for x in [lon0, lon0 + deg]:
        ax.plot([x, x], [lat0 - 0.002, lat0], "-", color=color, lw=1.5, zorder=10)
    ax.text(
        lon0 + deg / 2,
        lat0 - 0.006,
        f"{km} km",
        ha="center",
        va="top",
        fontsize=FS_BODY - 1,
        color=color,
        zorder=10,
    )


def draw_sg_patches(cfg: MapConfig, ax):
    for cx, cy, hw, hh in cfg.sg_patches_abs():
        rect = mpatches.FancyBboxPatch(
            (cx - hw, cy - hh),
            2 * hw,
            2 * hh,
            boxstyle="round,pad=0.001",
            linewidth=LW_SG,
            edgecolor=TOL_CYAN,
            facecolor="none",
            linestyle=(0, (4, 2)),
            zorder=8,
        )
        ax.add_patch(rect)


def draw_outline(
    ax,
    lons: np.ndarray,
    lats: np.ndarray,
    lw: float = LW_OUTLINE,
):
    ax.fill(lons, lats, color=TOL_RED, alpha=0.06, zorder=6)
    ax.plot(lons, lats, color=TOL_RED, lw=lw, zorder=7)


def flow_arrow(cfg: MapConfig, ax, color="white", length=0.030):
    x0 = cfg.gc_lon - cfg._u_lon * length * 0.5
    y0 = cfg.gc_lat - cfg._u_lat * length * 0.5
    ax.annotate(
        "",
        xy=(x0 + cfg._u_lon * length, y0 + cfg._u_lat * length),
        xytext=(x0, y0),
        arrowprops=dict(arrowstyle="->", color=color, lw=1.2, mutation_scale=10),
        zorder=10,
    )
    ax.text(
        x0 + cfg._u_lon * length * 1.05,
        y0 + cfg._u_lat * length * 1.05,
        "flow",
        color=color,
        fontsize=FS_BODY - 1.5,
        va="bottom",
        ha="left",
        zorder=10,
        path_effects=[pe.withStroke(linewidth=1.5, foreground=BG_VEL_PANEL)],
    )


def panel_label(ax, txt: str, bg: str = "white"):
    ax.text(
        0.025,
        0.975,
        txt,
        transform=ax.transAxes,
        fontsize=FS_PANEL,
        fontweight="bold",
        va="top",
        ha="left",
        zorder=20,
        bbox=dict(boxstyle="round,pad=0.20", facecolor=bg, edgecolor="none", alpha=0.88),
    )


def stats_box(ax, vindex: float, sigma: float, pcr: float):
    txt = (
        f"$V_\\mathrm{{index}}$ = {vindex:.1f} m d$^{{-1}}$\n"
        f"± {sigma:.1f} m d$^{{-1}}$ (1$\\sigma$)\n"
        f"PCR = {pcr:.3f}"
    )
    ax.text(
        0.025,
        0.025,
        txt,
        transform=ax.transAxes,
        fontsize=FS_BODY - 0.5,
        va="bottom",
        ha="left",
        color="white",
        linespacing=1.4,
        zorder=15,
        bbox=dict(
            boxstyle="round,pad=0.28",
            facecolor=BG_VEL_PANEL,
            edgecolor="white",
            linewidth=0.5,
            alpha=0.85,
        ),
    )


def plot_panel_a(ax, cfg: MapConfig):
    ax.set_facecolor(BG_SAMPLE)
    LON_a, LAT_a = cfg.make_grid(cfg.zoom_a, GRID_N_PANEL_A)
    hs = synthetic_hillshade(cfg, LON_a, LAT_a)
    ax.pcolormesh(
        LON_a,
        LAT_a,
        hs,
        cmap=CMAP_HILL,
        vmin=0,
        vmax=1,
        shading="gouraud",
        rasterized=True,
        zorder=1,
    )

    draw_sg_patches(cfg, ax)
    glons, glats = cfg.glacier_outline()
    draw_outline(ax, glons, glats)

    ax.text(
        cfg.gc_lon + cfg._u_lon * 0.058 + 0.008,
        cfg.gc_lat + cfg._u_lat * 0.058,
        "Glacier\noutline ($\\Omega$)",
        color=TOL_RED,
        fontsize=FS_BODY - 1.5,
        va="bottom",
        ha="left",
        fontweight="bold",
        path_effects=[pe.withStroke(linewidth=1.5, foreground=BG_SAMPLE)],
    )
    ax.text(
        cfg.gc_lon - 0.068,
        cfg.gc_lat + 0.035,
        "Stable\nground",
        color=TOL_CYAN,
        fontsize=FS_BODY - 2,
        ha="center",
        path_effects=[pe.withStroke(linewidth=1.5, foreground=BG_SAMPLE)],
    )
    ax.text(
        cfg.gc_lon + 0.060,
        cfg.gc_lat - 0.033,
        "Stable\nground",
        color=TOL_CYAN,
        fontsize=FS_BODY - 2,
        ha="center",
        path_effects=[pe.withStroke(linewidth=1.5, foreground=BG_SAMPLE)],
    )

    north_arrow(ax, color="#333333")
    scale_bar(
        ax,
        cfg,
        cfg.gc_lon - cfg.zoom_a * 0.85,
        cfg.gc_lat - cfg.zoom_a * 0.83,
        km=2,
        color="#333333",
    )

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
            label="Stable-ground\ncontrol areas",
        ),
    ]
    ax.legend(
        handles=legend_handles,
        loc="lower right",
        fontsize=FS_BODY - 1.5,
        framealpha=0.90,
        edgecolor=TOL_GREY,
        borderpad=0.4,
        handlelength=1.6,
    )

    format_axes(cfg, ax, cfg.zoom_a)
    panel_label(ax, "(a)", bg=BG_SAMPLE)
    ax.set_title("Sampling regions", fontsize=FS_TITLE, loc="center", pad=3)


EPOCH_INFO = [
    ("(b)", "19 Oct–25 Oct", 160.1, 49.0, 0.091, 42, 0),
    ("(c)", "13 Sep–19 Sep", 156.7, 38.7, 0.071, 7, 1),
    ("(d)", "01 Oct–07 Oct", 97.0, 49.4, 0.071, 1, 2),
]


def plot_velocity_panel(
    ax,
    cfg: MapConfig,
    panel: str,
    title: str,
    vindex: float,
    sigma: float,
    pcr: float,
    tif_path: str | Path | None,
    seed: int,
    gl_lons: np.ndarray,
    gl_lats: np.ndarray,
    dem_path: str | Path | None,
    show_ylabel: bool,
):
    ax.set_facecolor(BG_VEL_PANEL)
    LON, LAT = cfg.make_grid(cfg.zoom_v, cfg.grid_n_vel)

    if dem_path and Path(dem_path).exists():
        hs = real_hillshade(dem_path, LON, LAT, cfg)
        if hs is None:
            hs = synthetic_hillshade(cfg, LON, LAT)
    else:
        hs = synthetic_hillshade(cfg, LON, LAT)

    ax.pcolormesh(
        LON,
        LAT,
        hs,
        cmap=CMAP_HILL,
        vmin=0,
        vmax=1,
        shading="gouraud",
        rasterized=True,
        zorder=1,
        alpha=0.85,
    )

    speed = get_velocity(cfg, tif_path, LON, LAT, vindex, seed=seed)

    ax.pcolormesh(
        LON,
        LAT,
        speed,
        cmap=CMAP_VEL,
        norm=Normalize(vmin=VMIN, vmax=VMAX),
        shading="gouraud",
        rasterized=True,
        zorder=3,
    )

    draw_outline(ax, gl_lons, gl_lats)
    draw_sg_patches(cfg, ax)
    flow_arrow(cfg, ax, color="white")
    stats_box(ax, vindex, sigma, pcr)

    format_axes(cfg, ax, cfg.zoom_v, ylabel=show_ylabel)
    panel_label(ax, panel, bg=BG_VEL_PANEL)
    ax.set_title(title, fontsize=FS_TITLE, loc="center", pad=3)


def add_colorbar(fig, ref_axes):
    fig.canvas.draw()
    positions = [ax.get_position() for ax in ref_axes]
    y0 = min(p.y0 for p in positions)
    y1 = max(p.y1 for p in positions)
    x1 = max(p.x1 for p in positions)
    cax = fig.add_axes([x1 + 0.015, y0, 0.018, y1 - y0])

    sm = ScalarMappable(cmap="magma", norm=Normalize(vmin=VMIN, vmax=VMAX))
    sm.set_array([])
    cb = fig.colorbar(sm, cax=cax)
    cb.set_label("Velocity (m d$^{-1}$)", fontsize=FS_LABEL, labelpad=4)
    cb.ax.tick_params(labelsize=FS_TICK, width=LW_AXIS, length=3)
    cb.outline.set_linewidth(LW_AXIS)
    return cb


def make_figure15(
    raster_paths: Sequence[str | Path | None] | None = None,
    glacier_shp: str | Path | None = None,
    dem_path: str | Path | None = None,
    out_stem: Path | str | None = None,
    cfg: MapConfig | None = None,
):
    apply_rcparams()
    cfg = cfg or MapConfig()

    if raster_paths is None:
        raster_paths = [None, None, None]

    if out_stem is None:
        out_stem = FIGURES / "fig_spatial_velocity_maps"
    out_stem = Path(out_stem)
    out_stem.parent.mkdir(parents=True, exist_ok=True)

    gl_out = load_glacier_outline(glacier_shp, cfg) if glacier_shp else None
    if gl_out is not None:
        gl_lons, gl_lats = gl_out
    else:
        gl_lons, gl_lats = cfg.glacier_outline()

    fig_w = DOUBLE_COL_IN
    fig_h = fig_w * 0.44

    fig = plt.figure(figsize=(fig_w, fig_h))
    import matplotlib.gridspec as gridspec

    gs = gridspec.GridSpec(
        1,
        4,
        figure=fig,
        width_ratios=[1.1, 1, 1, 1],
        wspace=0.14,
        left=0.07,
        right=0.88,
        top=0.90,
        bottom=0.14,
    )

    ax_a = fig.add_subplot(gs[0, 0])
    ax_vb = fig.add_subplot(gs[0, 1])
    ax_vc = fig.add_subplot(gs[0, 2])
    ax_vd = fig.add_subplot(gs[0, 3])
    vel_axes = [ax_vb, ax_vc, ax_vd]

    plot_panel_a(ax_a, cfg)

    for ax, (panel, title, vi, sig, pcr, seed, ri) in zip(vel_axes, EPOCH_INFO):
        tif = raster_paths[ri] if ri < len(raster_paths) else None
        plot_velocity_panel(
            ax,
            cfg,
            panel,
            title,
            vi,
            sig,
            pcr,
            tif,
            seed,
            gl_lons,
            gl_lats,
            dem_path,
            show_ylabel=(ax is ax_vb),
        )

    add_colorbar(fig, vel_axes)

    for ext, dpi in [(".pdf", None), (".eps", None), (".png", 600)]:
        kw = dict(bbox_inches="tight", pad_inches=0.02)
        if dpi:
            kw["dpi"] = dpi
        p = out_stem.with_suffix(ext)
        fig.savefig(p, **kw)
        print(f"  Saved: {p}")

    plt.close(fig)
    print("Figure 15 (v2) complete.")


def _resolve_raster_paths(
    cli: Sequence[str | None] | None,
) -> list[str | Path | None] | None:
    if cli and any(r for r in cli):
        return [Path(r) if r else None for r in cli]
    resolved = []
    for p in _DEFAULT_VEL_TIFS:
        if p.exists() and p.stat().st_size > 0:
            resolved.append(p)
        else:
            resolved.append(None)
    if all(x is None for x in resolved):
        return None
    return resolved


if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="Publication Figure 15 — spatial velocity maps (v2, hillshade + transparent magma)."
    )
    p.add_argument(
        "--rasters",
        nargs=3,
        metavar=("B", "C", "D"),
        default=None,
        help="Three velocity GeoTIFFs: Oct19–25, Sep13–19, Oct01–07",
    )
    p.add_argument("--glacier", default=None, help="Glacier outline shapefile (.shp)")
    p.add_argument("--dem", default=None, help="DEM GeoTIFF for hillshade (e.g. SRTM)")
    p.add_argument("--centre_lon", type=float, default=70.718)
    p.add_argument("--centre_lat", type=float, default=38.990)
    p.add_argument("--zoom_v", type=float, default=0.072, help="Velocity panel half-width (°)")
    p.add_argument(
        "--grid_n",
        type=int,
        default=GRID_N,
        help=f"Velocity-panel grid size per axis (default {GRID_N}; use 600–800 for faster drafts)",
    )
    p.add_argument(
        "--out",
        default=None,
        help="Output stem without extension (default: figures/fig_spatial_velocity_maps)",
    )
    args = p.parse_args()

    cfg = MapConfig(
        gc_lon=args.centre_lon,
        gc_lat=args.centre_lat,
        zoom_v=args.zoom_v,
        grid_n_vel=max(200, int(args.grid_n)),
    )
    raster_paths = _resolve_raster_paths(args.rasters)
    out = Path(args.out) if args.out else FIGURES / "fig_spatial_velocity_maps"

    make_figure15(
        raster_paths=raster_paths,
        glacier_shp=args.glacier,
        dem_path=args.dem,
        out_stem=out,
        cfg=cfg,
    )
