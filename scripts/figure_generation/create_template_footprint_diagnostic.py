#!/usr/bin/env python3
"""
Create a diagnostic figure showing template footprints for different window sizes
overlaid on the glacier outline, demonstrating valley-wall mixing risk.

Purpose: Visual proof that 128 px templates extend significantly beyond the glacier,
while 32/64 px templates are more glacier-confined.
"""

from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon
import fiona
from shapely.geometry import shape
from shapely.ops import unary_union

# Configuration
GLACIER_OUTLINE_SHP = Path("satellite_data/dem/processed/didal_glacier_rgi_outline.shp")
OUTPUT_DIR = Path("processed_data/window_sensitivity")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Window sizes to demonstrate (in pixels)
WINDOW_SIZES = [32, 64, 128]

# Pixel size in degrees (from GDAL geotransform)
PIXEL_SIZE_DEG = 0.00008983  # ~10m at 39°N

# Representative template center point (middle of glacier)
# We'll place a few templates to show the footprint
GLACIER_CENTER_LON = 70.750269
GLACIER_CENTER_LAT = 38.973211

def main():
    # Load glacier outline
    with fiona.open(GLACIER_OUTLINE_SHP) as src:
        glacier_geoms = [shape(f["geometry"]) for f in src]
    glacier_poly = unary_union(glacier_geoms)
    
    # Get glacier bounds
    minx, miny, maxx, maxy = glacier_poly.bounds
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Plot glacier outline
    if glacier_poly.geom_type == 'Polygon':
        x, y = glacier_poly.exterior.xy
        ax.fill(x, y, alpha=0.3, fc='lightblue', ec='blue', linewidth=2, label='Glacier outline')
    elif glacier_poly.geom_type == 'MultiPolygon':
        for poly in glacier_poly.geoms:
            x, y = poly.exterior.xy
            ax.fill(x, y, alpha=0.3, fc='lightblue', ec='blue', linewidth=2)
    
    # Define template center points (3 locations along glacier centerline)
    template_centers = [
        (GLACIER_CENTER_LON - 0.0005, GLACIER_CENTER_LAT),  # Upper
        (GLACIER_CENTER_LON, GLACIER_CENTER_LAT),           # Middle
        (GLACIER_CENTER_LON + 0.0005, GLACIER_CENTER_LAT - 0.0003),  # Lower
    ]
    
    # Colors for different window sizes
    colors = {
        32: '#2E86AB',   # Blue
        64: '#A23B72',   # Purple
        128: '#F18F01',  # Orange
    }
    
    # Plot template footprints for each window size
    for window_px in WINDOW_SIZES:
        half_window_deg = (window_px / 2) * PIXEL_SIZE_DEG
        
        for i, (cx, cy) in enumerate(template_centers):
            # Template bounding box
            x0 = cx - half_window_deg
            x1 = cx + half_window_deg
            y0 = cy - half_window_deg
            y1 = cy + half_window_deg
            
            # Create rectangle
            rect = Rectangle(
                (x0, y0),
                x1 - x0,
                y1 - y0,
                linewidth=2,
                edgecolor=colors[window_px],
                facecolor='none',
                linestyle='--' if window_px == 128 else '-',
                alpha=0.8,
                label=f'{window_px} px template' if i == 0 else None
            )
            ax.add_patch(rect)
            
            # Compute glacier fraction for this template
            from shapely.geometry import box
            template_box = box(x0, y0, x1, y1)
            intersection = glacier_poly.intersection(template_box)
            glacier_frac = intersection.area / template_box.area if template_box.area > 0 else 0.0
            
            # Add text annotation (only for middle template)
            if i == 1:
                ax.text(
                    cx, y1 + 0.00005,
                    f'{glacier_frac:.0%}',
                    ha='center', va='bottom',
                    fontsize=11,
                    color=colors[window_px],
                    fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=colors[window_px], alpha=0.8)
                )
    
    # Mark template centers
    for cx, cy in template_centers:
        ax.plot(cx, cy, 'ko', markersize=4, zorder=10)
    
    # Formatting
    ax.set_xlabel('Longitude (°E)', fontsize=14)
    ax.set_ylabel('Latitude (°N)', fontsize=14)
    ax.set_title('Template Footprint Diagnostic: Valley-Wall Mixing Risk\n(Glacier fraction shown for middle template)', 
                 fontsize=15, fontweight='normal')
    ax.tick_params(axis='both', which='major', labelsize=12)
    ax.grid(True, alpha=0.3, linestyle=':', linewidth=0.5)
    ax.set_aspect('equal')
    
    # Legend
    handles, labels = ax.get_legend_handles_labels()
    # Remove duplicate labels
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), 
              loc='upper left', fontsize=12, frameon=True, framealpha=0.95)
    
    # Add text box with interpretation
    textstr = ('128 px templates (orange, dashed) extend\n'
               'significantly beyond glacier boundary,\n'
               'capturing valley walls and stable terrain.\n\n'
               '32–64 px templates (blue/purple, solid)\n'
               'are more glacier-confined but still\n'
               'require glacier-fraction filtering (≥50%).')
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
    ax.text(0.98, 0.02, textstr, transform=ax.transAxes, fontsize=10,
            verticalalignment='bottom', horizontalalignment='right', bbox=props)
    
    plt.tight_layout()
    
    # Save
    pdf_out = OUTPUT_DIR / "template_footprint_demo.pdf"
    png_out = OUTPUT_DIR / "template_footprint_demo.png"
    plt.savefig(pdf_out, dpi=300, bbox_inches='tight')
    plt.savefig(png_out, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✅ Saved: {pdf_out}")
    print(f"✅ Saved: {png_out}")
    
    # Print glacier fraction summary
    print(f"\n{'='*60}")
    print("GLACIER FRACTION SUMMARY (middle template)")
    print(f"{'='*60}")
    cx, cy = template_centers[1]
    for window_px in WINDOW_SIZES:
        half_window_deg = (window_px / 2) * PIXEL_SIZE_DEG
        x0 = cx - half_window_deg
        x1 = cx + half_window_deg
        y0 = cy - half_window_deg
        y1 = cy + half_window_deg
        from shapely.geometry import box
        template_box = box(x0, y0, x1, y1)
        intersection = glacier_poly.intersection(template_box)
        glacier_frac = intersection.area / template_box.area if template_box.area > 0 else 0.0
        print(f"{window_px:3d} px: glacier fraction = {glacier_frac:5.1%}  {'✅ PASS (≥50%)' if glacier_frac >= 0.5 else '❌ FAIL (<50%)'}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
