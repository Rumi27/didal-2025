#!/usr/bin/env python3
"""
Visualize spatial bias structure for raw SAR offset fields.

Expected input for each --pairX:
  - 2-band GeoTIFF
    Band 1: dE (eastward offset, m/day or m over baseline)
    Band 2: dN (northward offset, same units)

The script:
  - Reads raw offsets
  - Extracts stable-ground samples using a polygon shapefile
  - Fits a planar bias model (constant + linear trend in x,y) to stable-ground offsets
  - Computes residuals and NMAD
  - Produces, for each pair, a 3-panel PNG:
      (a) raw stable-ground offset magnitude
      (b) fitted planar bias magnitude
      (c) residual magnitude after de-biasing
  - Writes a JSON summary with mean bias vector, plane coefficients, and residual NMAD.
"""

import argparse
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import geometry_mask
import matplotlib.pyplot as plt


def nmad(x: np.ndarray) -> float:
    """Normalized Median Absolute Deviation (robust scatter)."""
    x = x[np.isfinite(x)]
    if x.size == 0:
        return float("nan")
    med = np.median(x)
    return float(1.4826 * np.median(np.abs(x - med)))


def fit_plane(x: np.ndarray, y: np.ndarray, z: np.ndarray):
    """Fit z = a + b*x + c*y by least squares."""
    A = np.column_stack([np.ones_like(x), x, y])
    coeffs, *_ = np.linalg.lstsq(A, z, rcond=None)
    return coeffs  # a, b, c


def process_pair(pair_path: Path, stable_shp: Path, dem_path: Path | None, out_dir: Path):
    pair_path = Path(pair_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    with rasterio.open(pair_path) as src:
        dE = src.read(1).astype(np.float32)
        dN = src.read(2).astype(np.float32)
        transform = src.transform
        crs = src.crs
        H, W = dE.shape

    # Load stable-ground mask shapefile and rasterize to mask
    gdf = gpd.read_file(stable_shp)
    if gdf.crs != crs:
        gdf = gdf.to_crs(crs)
    geoms = [geom for geom in gdf.geometry if geom is not None]
    stable_mask = ~geometry_mask(
        geoms, out_shape=(H, W), transform=transform, invert=True
    )  # True where inside polygons

    # Stable-ground samples
    valid = stable_mask & np.isfinite(dE) & np.isfinite(dN)
    if not np.any(valid):
        raise RuntimeError(f"No valid stable-ground samples in {pair_path}")

    # Coordinates for each pixel center
    rows, cols = np.indices(dE.shape)
    xs = transform.c + (cols + 0.5) * transform.a + (rows + 0.5) * transform.b
    ys = transform.f + (cols + 0.5) * transform.d + (rows + 0.5) * transform.e

    # Stable-ground vectors and magnitudes
    dE_s = dE[valid]
    dN_s = dN[valid]
    x_s = xs[valid]
    y_s = ys[valid]
    mag_s = np.hypot(dE_s, dN_s)

    # Mean bias vector on stable ground
    mean_dE = float(np.nanmean(dE_s))
    mean_dN = float(np.nanmean(dN_s))

    # Fit planar model separately to dE and dN
    aE, bE, cE = fit_plane(x_s, y_s, dE_s)
    aN, bN, cN = fit_plane(x_s, y_s, dN_s)

    # Evaluate plane over full grid
    dE_plane = aE + bE * xs + cE * ys
    dN_plane = aN + bN * xs + cN * ys
    mag_plane = np.hypot(dE_plane, dN_plane)

    # Residuals (data - plane)
    dE_res = dE - dE_plane
    dN_res = dN - dN_plane
    mag_res = np.hypot(dE_res, dN_res)

    # Residual stats on stable ground
    mag_res_s = mag_res[valid]
    nmad_res = nmad(mag_res_s)

    # Plot 3-panel figure
    name = pair_path.stem
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    vmin, vmax = 0, np.nanpercentile(mag_s, 99)

    im0 = axes[0].imshow(
        mag_s.reshape(-1, 1),
        aspect="auto",
        cmap="viridis",
        vmin=vmin,
        vmax=vmax,
    )
    axes[0].set_title("Stable-ground |raw offset| (histogram proxy)")
    axes[0].set_yticks([])
    axes[0].set_xticks([])

    # For panels (b) and (c), show full-field maps
    im1 = axes[1].imshow(
        mag_plane,
        origin="upper",
        cmap="viridis",
        vmin=vmin,
        vmax=vmax,
    )
    axes[1].set_title("Fitted planar bias |dE,dN|")
    axes[1].set_xticks([])
    axes[1].set_yticks([])

    im2 = axes[2].imshow(
        mag_res,
        origin="upper",
        cmap="viridis",
        vmin=0,
        vmax=np.nanpercentile(mag_res_s, 99),
    )
    axes[2].set_title("Residual |dE,dN| after de-bias")
    axes[2].set_xticks([])
    axes[2].set_yticks([])

    fig.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04, label="Offset magnitude")
    fig.colorbar(im2, ax=axes[2], fraction=0.046, pad=0.04, label="Residual magnitude")
    fig.suptitle(f"Stable-ground bias diagnostics: {name}", fontsize=12)

    out_png = out_dir / f"bias_spatial_map_{name}.png"
    fig.tight_layout(rect=[0, 0.03, 1, 0.95])
    fig.savefig(out_png, dpi=150)
    plt.close(fig)

    # Collect summary stats
    summary = {
        "pair": name,
        "mean_bias_dE": mean_dE,
        "mean_bias_dN": mean_dN,
        "plane_dE": {"a": float(aE), "b": float(bE), "c": float(cE)},
        "plane_dN": {"a": float(aN), "b": float(bN), "c": float(cN)},
        "residual_nmad": nmad_res,
        "n_stable_samples": int(valid.sum()),
    }
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Visualize spatial bias for raw SAR offset fields (three pairs)."
    )
    parser.add_argument(
        "--pair1",
        required=True,
        help="Path to first SAR offset GeoTIFF (2-band dE,dN).",
    )
    parser.add_argument(
        "--pair2",
        required=True,
        help="Path to second SAR offset GeoTIFF (2-band dE,dN).",
    )
    parser.add_argument(
        "--pair3",
        required=True,
        help="Path to third SAR offset GeoTIFF (2-band dE,dN).",
    )
    parser.add_argument(
        "--stable-shp",
        required=True,
        help="Stable-ground polygon shapefile (ring outside glacier).",
    )
    parser.add_argument(
        "--dem",
        required=False,
        help="DEM GeoTIFF (optional; currently not used but kept for interface compatibility).",
    )
    parser.add_argument(
        "--out-dir",
        required=True,
        help="Output directory for PNGs and JSON summary.",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    summaries = []
    for pair in [args.pair1, args.pair2, args.pair3]:
        summary = process_pair(
            Path(pair),
            Path(args.stable_shp),
            Path(args.dem) if args.dem else None,
            out_dir,
        )
        summaries.append(summary)

    out_json = out_dir / "bias_diagnosis_summary.json"
    with out_json.open("w") as f:
        json.dump(summaries, f, indent=2)

    print(f"Wrote {out_json}")


if __name__ == "__main__":
    main()

