
# IMPORT GDAL FIRST TO AVOID PANDAS CONFLICT
try:
    from osgeo import gdal, ogr, osr
except ImportError:
    import gdal, ogr, osr

import numpy as np
import pandas as pd
from scipy import ndimage, signal
from pathlib import Path
from datetime import datetime
import sys
import os
import traceback

# LOGGING SETUP
LOG_FILE = "sensitivity_debug_v2.log"
def log(msg):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"{datetime.now()}: {msg}\n")
    except:
        pass
    print(msg, flush=True)

# Clear log
with open(LOG_FILE, "w") as f:
    f.write("Starting script v2...\n")

log("Imports started")

# Set backend BEFORE importing pyplot
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    log("Matplotlib imported")
except Exception as e:
    log(f"Matplotlib import error: {e}")

# --- Config ---
WINDOW_SIZES = [32, 64, 128]
SEARCH_RANGE = 100
STEP = 32
PIXEL_SIZE_METERS = 10.0
MIN_CORRELATION = 0.3

# Paths - relative to project root
INPUT_DIR = Path("satellite_data/sentinel1/processed")
OUTPUT_DIR = Path("processed_data/window_sensitivity")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR = OUTPUT_DIR / "temp_crops"
TEMP_DIR.mkdir(exist_ok=True)

# Prioritize Manual Mask
SHAPEFILE_PATH = Path("Didal_Glacier_GIS_Data/Glacier_Outline/didal_glacier_manual.shp")

# Bbox (Expanded to ensure coverage)
# Didal approx: 39.03N, 70.75E.
# BBox for cropping images
CROP_BBOX = [70.50, 39.20, 71.00, 38.70]

# --- Helpers ---

def parabolic_refinement(corr_map, y, x):
    h, w = corr_map.shape
    if y <= 0 or y >= h - 1 or x <= 0 or x >= w - 1:
        return 0.0, 0.0

    c1 = corr_map[y, x - 1]
    c2 = corr_map[y, x]
    c3 = corr_map[y, x + 1]
    denom_x = 2 * (2 * c2 - c1 - c3)
    dx = (c1 - c3) / denom_x if abs(denom_x) > 1e-6 else 0.0

    c1 = corr_map[y - 1, x]
    c2 = corr_map[y, x]
    c3 = corr_map[y + 1, x]
    denom_y = 2 * (2 * c2 - c1 - c3)
    dy = (c1 - c3) / denom_y if abs(denom_y) > 1e-6 else 0.0
    
    return dy, dx

def offset_tracking_masked(image1, image2, window_size, step, mask):
    h, w = image1.shape
    dx = np.full((h, w), np.nan, dtype=np.float32)
    dy = np.full((h, w), np.nan, dtype=np.float32)
    corr = np.full((h, w), np.nan, dtype=np.float32)
    
    half_win = window_size // 2
    
    ys = np.arange(half_win, h - half_win, step)
    xs = np.arange(half_win, w - half_win, step)
    
    count = 0
    skipped_mask = 0
    
    for y in ys:
        for x in xs:
            if mask[y, x] == 0:
                skipped_mask += 1
                continue
                
            count += 1
            
            template = image1[y-half_win:y+half_win, x-half_win:x+half_win]
            if np.std(template) < 1e-6: continue
            template = template - np.mean(template)
            
            y_min_s = max(0, y - half_win - SEARCH_RANGE)
            y_max_s = min(h, y + half_win + SEARCH_RANGE)
            x_min_s = max(0, x - half_win - SEARCH_RANGE)
            x_max_s = min(w, x + half_win + SEARCH_RANGE)
            
            search_area = image2[y_min_s:y_max_s, x_min_s:x_max_s]
            if np.std(search_area) < 1e-6: continue
            
            corr_map = signal.correlate2d(search_area, template, mode='valid')
            if corr_map.size == 0: continue
            
            y_peak, x_peak = np.unravel_index(np.argmax(corr_map), corr_map.shape)
            max_val = corr_map[y_peak, x_peak]
            
            norm = np.std(search_area) * np.std(template) * template.size
            best_corr = max_val / norm if norm > 0 else 0
            
            if best_corr >= MIN_CORRELATION:
                dy_local = y_peak - SEARCH_RANGE
                dx_local = x_peak - SEARCH_RANGE
                dy_sub, dx_sub = parabolic_refinement(corr_map, y_peak, x_peak)
                
                dx[y, x] = dx_local + dx_sub
                dy[y, x] = dy_local + dy_sub
                corr[y, x] = best_corr
    
    log(f"    Calculated {count} points (Skipped {skipped_mask} on mask).")
    return dx, dy, corr

def load_image(dim_path):
    import subprocess
    
    data_dir = dim_path.with_suffix(".data")
    img_path = data_dir / "Sigma0_VV.img"
    # Use _manual to force new crop
    crop_path = TEMP_DIR / f"crop_{dim_path.stem}_manual.tif"
    
    if not crop_path.exists():
        cmd = [
            "gdal_translate", "-projwin", str(CROP_BBOX[0]), str(CROP_BBOX[1]), str(CROP_BBOX[2]), str(CROP_BBOX[3]),
            "-projwin_srs", "EPSG:4326", "-of", "GTiff", str(img_path), str(crop_path)
        ]
        log(f"Running gdal_translate for {crop_path.name}")
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    ds = gdal.Open(str(crop_path))
    if ds is None:
        raise Exception(f"Could not open {crop_path}")
    
    band = ds.GetRasterBand(1)
    data = band.ReadAsArray()
    geotransform = ds.GetGeoTransform()
    projection = ds.GetProjection()
    
    return data, geotransform, projection, ds.RasterXSize, ds.RasterYSize

def get_mask(shapefile_path, geotransform, cols, rows, projection, erode_px):
    target_ds = gdal.GetDriverByName('MEM').Create('', cols, rows, 1, gdal.GDT_Byte)
    target_ds.SetGeoTransform(geotransform)
    target_ds.SetProjection(projection)
    
    if shapefile_path.exists():
        log(f"Loading mask from {shapefile_path}")
        source_ds = ogr.Open(str(shapefile_path))
        source_layer = source_ds.GetLayer()
        source_srs = source_layer.GetSpatialRef()
        
        target_srs = osr.SpatialReference()
        target_srs.ImportFromWkt(projection)
        target_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        
        # REPROJECT IF NEEDED
        if not source_srs.IsSame(target_srs):
            coord_trans = osr.CoordinateTransformation(source_srs, target_srs)
            
            mem_driver = ogr.GetDriverByName('Memory')
            mem_ds = mem_driver.CreateDataSource('mem')
            mem_layer = mem_ds.CreateLayer('mask', target_srs, geom_type=ogr.wkbPolygon)
            
            source_layer.ResetReading()
            for feature in source_layer:
                geom = feature.GetGeometryRef()
                if geom:
                    geom_clone = geom.Clone()
                    geom_clone.Transform(coord_trans)
                    new_feature = ogr.Feature(mem_layer.GetLayerDefn())
                    new_feature.SetGeometry(geom_clone)
                    mem_layer.CreateFeature(new_feature)
            
            gdal.RasterizeLayer(target_ds, [1], mem_layer, burn_values=[1])
        else:
            gdal.RasterizeLayer(target_ds, [1], source_layer, burn_values=[1])
    else:
        log("Shapefile not found. Falling back to IN-MEMORY manual box.")
        # Manual Box 
        min_lon = 70.72
        max_lon = 70.78
        min_lat = 38.99
        max_lat = 39.07
        
        mem_driver = ogr.GetDriverByName('Memory')
        mem_ds = mem_driver.CreateDataSource('mem')
        target_srs = osr.SpatialReference()
        target_srs.ImportFromWkt(projection) # Assume projection is compatible (WGS84)
        mem_layer = mem_ds.CreateLayer('mask', target_srs, geom_type=ogr.wkbPolygon)
        
        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(min_lon, min_lat)
        ring.AddPoint(max_lon, min_lat)
        ring.AddPoint(max_lon, max_lat)
        ring.AddPoint(min_lon, max_lat)
        ring.AddPoint(min_lon, min_lat)
        poly = ogr.Geometry(ogr.wkbPolygon)
        poly.AddGeometry(ring)
        
        feat = ogr.Feature(mem_layer.GetLayerDefn())
        feat.SetGeometry(poly)
        mem_layer.CreateFeature(feat)
        
        gdal.RasterizeLayer(target_ds, [1], mem_layer, burn_values=[1])

    mask = target_ds.GetRasterBand(1).ReadAsArray()
    
    if erode_px > 0:
        mask = ndimage.binary_erosion(mask, iterations=erode_px).astype('uint8')
        
    return mask

def main():
    log("Starting Main v2...")
    
    dim_files = sorted(INPUT_DIR.glob("*Orb_Cal_TC.dim"))
    products = []
    for f in dim_files:
        try:
            dt = datetime.strptime(f.name.split('_')[4], "%Y%m%dT%H%M%S")
            products.append({'path': f, 'date': dt})
        except:
            continue
    products.sort(key=lambda x: x['date'])
    
    if len(products) < 2:
        log("Not enough products found.")
        sys.exit(1)

    log(f"Found {len(products)} products.")
    results = []
    
    for i in range(len(products) - 1):
        p1 = products[i]
        p2 = products[i+1]
        dt = (p2['date'] - p1['date']).total_seconds() / 86400
        
        log(f"Processing {p1['date'].date()} -> {p2['date'].date()} ({dt:.1f} d)...")
        
        try:
            img1, gt, proj, cols, rows = load_image(p1['path'])
            img2, _, _, _, _ = load_image(p2['path'])
        except Exception as e:
            log(f"  ⚠️ Error loading images: {e}")
            continue
        
        # ROI mask
        log("Creating ROI mask (dilated)...")
        roi_mask = get_mask(SHAPEFILE_PATH, gt, cols, rows, proj, erode_px=0)
        # roi_mask = ndimage.binary_dilation(roi_mask, iterations=5).astype('uint8') # No need to dilate manual box
        log(f"ROI pixels: {np.sum(roi_mask)}")
        
        if np.sum(roi_mask) == 0:
            log("CRITICAL: ROI mask is empty! Check coordinates!")
            continue

        for win in WINDOW_SIZES:
            log(f"  Window: {win} px")
            
            dx, dy, corr = offset_tracking_masked(img1, img2, win, STEP, roi_mask)
            vel = np.sqrt(dx**2 + dy**2) * PIXEL_SIZE_METERS / dt
            
            erode_px = win // 2
            log(f"  Creating strict mask (erode {erode_px})...")
            strict_mask = get_mask(SHAPEFILE_PATH, gt, cols, rows, proj, erode_px=erode_px)
            
            valid_vel = vel[(strict_mask == 1) & (~np.isnan(vel))]
            valid_corr = corr[(strict_mask == 1) & (~np.isnan(corr))]
            
            v_mean = np.mean(valid_vel) if len(valid_vel) > 0 else np.nan
            v_std = np.std(valid_vel) if len(valid_vel) > 0 else np.nan
            
            res = {
                'date1': p1['date'].strftime('%Y-%m-%d'),
                'date2': p2['date'].strftime('%Y-%m-%d'),
                'window_size': win,
                'v_mean': v_mean,
                'v_std': v_std,
                'corr_median': np.median(valid_corr) if len(valid_corr) > 0 else np.nan,
                'valid_pixels': len(valid_vel),
                'total_mask_pixels': np.sum(strict_mask),
                'valid_fraction': len(valid_vel) / np.sum(strict_mask) if np.sum(strict_mask) > 0 else 0
            }
            results.append(res)
            log(f"    V_mean: {res['v_mean']:.2f}, Valid: {res['valid_pixels']}/{res['total_mask_pixels']}")
            
    df = pd.DataFrame(results)
    df.to_csv(OUTPUT_DIR / "sensitivity_results.csv", index=False)
    log("Done. Saved results.")
    
    try:
        import matplotlib.ticker as mticker
        import matplotlib.dates as mdates
        
        # English date formatter (locale-independent)
        mon_en = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        def fmt_day_mon_en(x, pos):
            try:
                dt = mdates.num2date(x)
                return f"{dt.day:02d} {mon_en[dt.month - 1]}"
            except:
                return ""
        
        plt.figure(figsize=(10, 6))
        for win in WINDOW_SIZES:
            sub = df[df['window_size'] == win]
            if not sub.empty:
                plt.plot(pd.to_datetime(sub['date1']), sub['v_mean'], 'o-', label=f"Win {win}px")
                plt.fill_between(pd.to_datetime(sub['date1']), 
                                 sub['v_mean'] - sub['v_std'], 
                                 sub['v_mean'] + sub['v_std'], alpha=0.1)
        
        plt.legend(fontsize=12, frameon=True, framealpha=0.95)
        plt.grid(True, alpha=0.3)
        plt.title("Velocity Sensitivity to Window Size (Strict Masking)", fontsize=15, fontweight='normal')
        plt.ylabel("Velocity (m/d)", fontsize=14)
        plt.xlabel("Date", fontsize=14)
        
        # Format x-axis with English dates
        ax = plt.gca()
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_day_mon_en))
        ax.tick_params(axis='both', which='major', labelsize=12)
        
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / "sensitivity_plot.pdf")
        log("Saved plot")
    except Exception as e:
        log(f"Plot error: {e}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"CRITICAL ERROR: {e}")
        log(traceback.format_exc())
