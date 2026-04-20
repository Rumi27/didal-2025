#!/usr/bin/env python3
"""
Verify PlanetScope terminus displacement from AnalyticMS SR imagery.

Method (reproducible):
  - Flow axis: LineString from northernmost to southernmost point of glacier outline (WGS84 -> UTM 42N).
  - For each scene (warped to a common Sep-13 reference grid): use NIR band (band 4) inside
    glacier polygon buffer; Otsu threshold to separate ice/snow from darker surroundings; keep
    largest connected component; take the most-downstream pixel (max projection onto flow unit vector).
  - Position s = projection of terminus point onto flow axis (meters from arbitrary origin on axis).
  - Cumulative advance = s(date) - s(reference_date).

Uncertainty (digitisation / classification):
  - Report ±1--2 pixels at 3 m GSD for manual picking; for automated edge = ±1 px (3 m) as lower bound
    and RSS √(σ₁²+σ₂²) for interval displacements (conservative σ = 6 m per scene from manuscript).

Outputs:
  - processed_data/planet_terminus_verification/terminus_verification.csv
  - processed_data/planet_terminus_verification/terminus_verification_table.tex
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import fiona
import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.features import rasterize
from scipy import ndimage
from scipy.ndimage import map_coordinates
from shapely.geometry import shape, mapping, LineString, box, Point
from shapely.ops import unary_union, transform as shp_transform
import pyproj

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = ROOT / "processed_data/planet_terminus_verification"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Reference grid (Sep 13 clip — same as autoRIFT / paper clips)
REF_PATH = ROOT / "planet_images/sep_2025/09_13_09_17/20250913_062702_66_2516_3B_AnalyticMS_SR_clip.tif"
GLACIER_SHP = ROOT / "Didal_Glacier_GIS_Data/Glacier_Outline/didal_glacier_manual.shp"

# Scenes to measure: (label_date, path) — use coregistered Sep17 when available
SCENES: list[tuple[str, Path]] = [
    ("2025-09-13", ROOT / "planet_images/sep_2025/09_13_09_17/20250913_062702_66_2516_3B_AnalyticMS_SR_clip.tif"),
    ("2025-09-17", ROOT / "planet_images/sep_2025/09_13_09_17/20250917_064330_29_24b7_coreg_to_sep13.tif"),
    ("2025-10-25", ROOT / "planet_images/newa_planet/20251025_062608_36_251d_3B_AnalyticMS_SR.tif"),
]

# Manuscript comparison (Sep 12 used as nominal start in table; Sep 13 is first full SR clip here)
PUBLISHED = {
    "sep12_17_m": 300.0,
    "sep17_oct25_m": 2175.0,
    "sep12_oct25_m": 2475.0,
}


def load_glacier_utm():
    with fiona.open(GLACIER_SHP) as src:
        geoms = [shape(f["geometry"]) for f in src]
    poly_ll = unary_union(geoms)
    if poly_ll.geom_type == "MultiPolygon":
        poly_ll = max(poly_ll.geoms, key=lambda p: p.area)
    wgs84 = pyproj.CRS("EPSG:4326")
    utm = pyproj.CRS("EPSG:32642")
    project = pyproj.Transformer.from_crs(wgs84, utm, always_xy=True).transform
    poly = shp_transform(project, poly_ll)
    return poly


def flow_axis(poly) -> tuple[np.ndarray, np.ndarray, LineString]:
    """Unit vector pointing downstream (southern), origin at northern vertex."""
    coords = np.array(poly.exterior.coords)
    iy = np.argmax(coords[:, 1])
    ix = np.argmin(coords[:, 1])
    head = coords[iy]
    tail = coords[ix]
    line = LineString([head, tail])
    v = tail - head
    length = np.linalg.norm(v)
    u = v / length
    return head, u, line


def otsu_threshold(x: np.ndarray) -> float:
    x = x[np.isfinite(x) & (x > 0)]
    if x.size < 256:
        return float(np.median(x))
    x = x.astype(np.uint16)
    hist, bin_edges = np.histogram(x, bins=256, range=(0, x.max() + 1))
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0
    weight1 = np.cumsum(hist)
    weight2 = np.cumsum(hist[::-1])[::-1]
    mean1 = np.cumsum(hist * bin_centers) / np.maximum(weight1, 1e-9)
    mean2 = np.cumsum((hist * bin_centers)[::-1]) / np.maximum(weight2[::-1], 1e-9)
    mean2 = mean2[::-1]
    variance = weight1[:-1] * weight2[1:] * (mean1[:-1] - mean2[1:]) ** 2
    idx = int(np.argmax(variance))
    return float(bin_centers[idx])


def _sample_nir_along_flow(
    nir: np.ndarray,
    transform: rasterio.Affine,
    poly_utm,
    head: np.ndarray,
    u: np.ndarray,
    t_max_m: float = 4500.0,
    step_m: float = 3.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Sample NIR along ray head + t*u. Returns (t_m, nir_profile, valid_mask).
    valid_mask: point inside glacier polygon (small negative buffer to avoid sides).
    """
    try:
        poly = poly_utm.buffer(-15.0)  # shrink slightly to stay on ice
        if poly.is_empty:
            poly = poly_utm
    except Exception:
        poly = poly_utm
    ts = np.arange(0.0, t_max_m, step_m)
    vals = np.full(ts.shape, np.nan, dtype=np.float64)
    inside = np.zeros(ts.shape, dtype=bool)
    inv = ~transform
    for i, t in enumerate(ts):
        e = head[0] + u[0] * t
        n = head[1] + u[1] * t
        pt = Point(e, n)
        inside[i] = poly.contains(pt) or poly.touches(pt)
        col, row = inv * (e, n)
        # subpixel sample
        c0 = float(col)
        r0 = float(row)
        if c0 < 0 or r0 < 0 or c0 >= nir.shape[1] - 1 or r0 >= nir.shape[0] - 1:
            continue
        z = map_coordinates(
            nir,
            [[r0], [c0]],
            order=1,
            mode="constant",
            cval=np.nan,
        )[0]
        vals[i] = z
    return ts, vals, inside


def terminus_position(
    nir: np.ndarray,
    transform: rasterio.Affine,
    poly_utm,
    head: np.ndarray,
    u: np.ndarray,
) -> tuple[float, float, float]:
    """
    Ice-front position along flow from NIR profile: maximum downward gradient
    (bright ice -> dark proglacial) within the glacier polygon corridor.
    Returns (s, E, N) where s is projection onto flow axis from origin=head.
    """
    ts, vals, inside = _sample_nir_along_flow(nir, transform, poly_utm, head, u)
    m = inside & np.isfinite(vals)
    if m.sum() < 20:
        raise RuntimeError("Insufficient profile samples inside glacier polygon")

    # Restrict to valid segment
    v = vals.copy()
    v[~m] = np.nan
    vm = v[m]
    med = float(np.nanmedian(vm))
    sprof = ndimage.gaussian_filter1d(np.nan_to_num(vm, nan=med), sigma=2.0)

    # Gradient: strongest negative gradient ≈ ice front
    grad = np.gradient(sprof)
    if not np.any(np.isfinite(grad)):
        raise RuntimeError("Bad gradient profile")

    lo = max(1, int(len(grad) * 0.1))
    hi = max(lo + 2, int(len(grad) * 0.92))
    subg = grad[lo:hi]
    j_rel = int(np.argmin(subg)) + lo

    idx_arr = np.where(m)[0]
    j = idx_arr[j_rel]
    t_snout = ts[j]
    e = head[0] + u[0] * t_snout
    n = head[1] + u[1] * t_snout
    s = float(t_snout)  # head is origin; u is unit -> t is distance along axis
    return s, float(e), float(n)


def warp_to_ref(src_path: Path, ref_profile: dict) -> tuple[np.ndarray, rasterio.Affine]:
    with rasterio.open(src_path) as src:
        # Planet AnalyticMS SR: DN × 0.0001 = surface reflectance
        nir = src.read(4).astype(np.float32) * 0.0001

        dst = np.zeros((ref_profile["height"], ref_profile["width"]), dtype=np.float32)
        reproject(
            source=nir,
            destination=dst,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=ref_profile["transform"],
            dst_crs=ref_profile["crs"],
            resampling=Resampling.bilinear,
        )
        return dst, ref_profile["transform"]


def main():
    poly = load_glacier_utm()
    head, u, flow_line = flow_axis(poly)

    with rasterio.open(REF_PATH) as ref:
        ref_profile = ref.profile.copy()
        ref_crs = ref.crs
        ref_transform = ref.transform
        ref_shape = (ref.height, ref.width)

    # Reference profile dict for warping
    prof = {
        "height": ref_shape[0],
        "width": ref_shape[1],
        "transform": ref_transform,
        "crs": ref_crs,
    }

    rows: list[dict] = []
    for label, path in SCENES:
        if not path.exists():
            print(f"SKIP missing: {path}")
            continue
        nir, tf = warp_to_ref(path, prof)
        s, e, n = terminus_position(nir, tf, poly, head, u)
        rows.append(
            {
                "date": label,
                "scene": path.name,
                "s_along_flow_m": s,
                "E_m_utm42n": e,
                "N_m_utm42n": n,
            }
        )

    rows.sort(key=lambda r: r["date"])
    if len(rows) < 2:
        raise SystemExit("Need at least two scenes")

    s0 = rows[0]["s_along_flow_m"]
    for r in rows:
        r["cumulative_advance_m"] = r["s_along_flow_m"] - s0

    # Interval checks (compare to published)
    def find(d):
        for r in rows:
            if r["date"] == d:
                return r
        return None

    r13 = find("2025-09-13")
    r17 = find("2025-09-17")
    r25 = find("2025-10-25")
    sep13_17 = (r17["s_along_flow_m"] - r13["s_along_flow_m"]) if r13 and r17 else None
    sep17_oct25 = (r25["s_along_flow_m"] - r17["s_along_flow_m"]) if r17 and r25 else None
    sep13_oct25 = (r25["s_along_flow_m"] - r13["s_along_flow_m"]) if r13 and r25 else None

    # Uncertainty: ±6 m per scene (1–2 px at 3 m); RSS for difference
    sigma_scene = 6.0
    import math

    def sig_diff(a, b):
        return math.sqrt(a**2 + b**2) * sigma_scene / math.sqrt(2)  # actually two independent: sqrt(2)*sigma
    # For displacement D = s2-s1, σ_D = sqrt(σ1^2+σ2^2)
    sigma_disp = (sigma_scene**2) * 2
    sigma_disp = math.sqrt(sigma_disp)

    summary = {
        "published_sep12_17_m": PUBLISHED["sep12_17_m"],
        "published_sep17_oct25_m": PUBLISHED["sep17_oct25_m"],
        "published_sep12_oct25_m": PUBLISHED["sep12_oct25_m"],
        "auto_sep13_17_m": sep13_17,
        "auto_sep17_oct25_m": sep17_oct25,
        "auto_sep13_oct25_m": sep13_oct25,
        "sigma_scene_m": sigma_scene,
        "sigma_interval_m": sigma_disp,
    }

    import csv

    csv_path = OUT_DIR / "terminus_verification.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with open(OUT_DIR / "verification_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))
    print("Wrote", csv_path)

    # LaTeX table
    tex = []
    tex.append("\\begin{table}[ht]")
    tex.append("\\centering")
    tex.append("\\caption{PlanetScope terminus verification (automated ice-front pick along glacier outline flow axis; 3~m GSD). Cumulative advance is relative to the first scene in this table. Digitisation uncertainty is reported as $\\pm$ 6~m per scene (1--2 pixels), propagated as $\\sigma_{\\Delta d}=\\sqrt{2}\\times 6$~m $\\approx$ 8.5~m for interval displacements.}")
    tex.append("\\label{tab:planet_terminus_verification}")
    tex.append("\\footnotesize")
    tex.append("\\begin{tabular}{llrrrr}")
    tex.append("\\toprule")
    tex.append("\\textbf{Date} & \\textbf{Scene (excerpt)} & \\textbf{$E$ (m)} & \\textbf{$N$ (m)} & \\textbf{$s$ (m)} & \\textbf{Cum. adv. (m)} \\\\")
    tex.append(" & \\textbf{UTM 42N} & & & \\textbf{along flow} & \\textbf{(from Sep 13)} \\\\")
    tex.append("\\midrule")
    for r in rows:
        excerpt = r["scene"][:40] + ("..." if len(r["scene"]) > 40 else "")
        tex.append(
            f"{r['date'][:10]} & \\texttt{{{excerpt}}} & {r['E_m_utm42n']:.1f} & {r['N_m_utm42n']:.1f} & {r['s_along_flow_m']:.1f} & {r['cumulative_advance_m']:.1f} \\\\"
        )
    tex.append("\\midrule")
    auto_int = (
        f"\\multicolumn{{6}}{{l}}{{\\textit{{Automated intervals:}} Sep 13--Sep 17: {sep13_17:.1f}~m; "
        f"Sep 17--Oct 25: {sep17_oct25:.1f}~m; Sep 13--Oct 25: {sep13_oct25:.1f}~m}} \\\\"
    )
    tex.append(auto_int)
    pub = f"{PUBLISHED['sep12_17_m']:.0f} / {PUBLISHED['sep17_oct25_m']:.0f} / {PUBLISHED['sep12_oct25_m']:.0f}~m"
    tex.append(
        f"\\multicolumn{{6}}{{l}}{{\\textit{{Published (Table~\\ref{{tab:movement}})}} (Sep 12--17 / Sep 17--Oct 25 / total): {pub}}} \\\\"
    )
    tex.append("\\bottomrule")
    tex.append("\\end{tabular}")
    tex.append("\\end{table}")

    tex_path = OUT_DIR / "terminus_verification_table.tex"
    tex_path.write_text("\n".join(tex), encoding="utf-8")
    print("Wrote", tex_path)


if __name__ == "__main__":
    main()
