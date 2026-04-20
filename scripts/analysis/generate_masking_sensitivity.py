import os
import sys
import numpy as np
import pandas as pd
from scipy import signal
from pathlib import Path
from datetime import datetime

try:
    from osgeo import gdal, ogr, osr
except ImportError:
    import gdal, ogr, osr

# Configure parameters
WINDOW_SIZE = 32
SEARCH_RANGE = 100
STEP = 16
PIXEL_SIZE_METERS = 10.0
MIN_CORRELATION = 0.3

INPUT_DIR = Path("satellite_data/sentinel1/processed")
OUTPUT_DIR = Path("processed_data/masking_sensitivity")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SHAPEFILE_PATH = Path("Didal_Glacier_GIS_Data/Glacier_Outline/didal_glacier_manual.shp")
TEMP_DIR = Path("processed_data/window_sensitivity/temp_crops")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

def parabolic_refinement(corr_map, y, x):
    h, w = corr_map.shape
    if y <= 0 or y >= h - 1 or x <= 0 or x >= w - 1:
        return 0.0, 0.0
    c1 = corr_map[y, x - 1]; c2 = corr_map[y, x]; c3 = corr_map[y, x + 1]
    denom_x = 2 * (2 * c2 - c1 - c3)
    dx = (c1 - c3) / denom_x if abs(denom_x) > 1e-6 else 0.0
    c1 = corr_map[y - 1, x]; c2 = corr_map[y, x]; c3 = corr_map[y + 1, x]
    denom_y = 2 * (2 * c2 - c1 - c3)
    dy = (c1 - c3) / denom_y if abs(denom_y) > 1e-6 else 0.0
    return dy, dx

def tracking_with_fraction(image1, image2, mask):
    h, w = image1.shape
    half_win = WINDOW_SIZE // 2
    ys = np.arange(half_win, h - half_win, STEP)
    xs = np.arange(half_win, w - half_win, STEP)
    
    results = []
    
    for y in ys:
        for x in xs:
            template_mask = mask[y-half_win:y+half_win, x-half_win:x+half_win]
            frac = np.mean(template_mask)
            
            if frac < 0.50:
                continue
                
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
                D = np.sqrt((dx_local+dx_sub)**2 + (dy_local+dy_sub)**2)
                
                results.append({
                    'D_px': D,
                    'corr': best_corr,
                    'frac': frac
                })
    return results

def load_image(dim_path):
    crop_path = TEMP_DIR / f"crop_{dim_path.stem}_manual.tif"
    ds = gdal.Open(str(crop_path))
    band = ds.GetRasterBand(1)
    data = band.ReadAsArray()
    data[data == 0] = np.nan
    return data, ds.GetGeoTransform(), ds.GetProjection(), ds.RasterXSize, ds.RasterYSize

def get_mask(gt, cols, rows, proj):
    target_ds = gdal.GetDriverByName('MEM').Create('', cols, rows, 1, gdal.GDT_Byte)
    target_ds.SetGeoTransform(gt)
    target_ds.SetProjection(proj)
    
    source_ds = ogr.Open(str(SHAPEFILE_PATH))
    source_layer = source_ds.GetLayer()
    
    source_srs = source_layer.GetSpatialRef()
    target_srs = osr.SpatialReference()
    target_srs.ImportFromWkt(proj)
    target_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    
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
        
    return target_ds.GetRasterBand(1).ReadAsArray()

def main():
    dim_files = sorted(INPUT_DIR.glob("*Orb_Cal_TC.dim"))
    products = []
    for f in dim_files:
        try:
            dt = datetime.strptime(f.name.split('_')[4], "%Y%m%dT%H%M%S")
            products.append({'path': f, 'date': dt})
        except: continue
    products.sort(key=lambda x: x['date'])
    
    table_lines = []
    table_lines.append("\\begin{table}[ht]")
    table_lines.append("\\centering")
    table_lines.append("\\caption{Sensitivity of $V_{\\text{index}}$ (m d$^{-1}$) and template correlation quality to imposing strict glacier-fraction thresholds on the tracking templates. Results use $32\\times 32$ px templates matched within a strictly non-drifting manual glacier outline $\\Omega$.}")
    table_lines.append("\\label{tab:masking_sensitivity}")
    table_lines.append("\\begin{tabular}{lrrrrr}")
    table_lines.append("\\toprule")
    table_lines.append("Epoch & Valid Vol. & Med. Corr & $V_{50\\%}$ & $V_{70\\%}$ & $V_{90\\%}$ \\\\")
    table_lines.append("\\midrule")
    
    print("Loading geometry mask...")
    try:
        _, gt, proj, cols, rows = load_image(products[0]['path'])
        mask = get_mask(gt, cols, rows, proj)
    except Exception as e:
        print(f"Mask err: {e}")
        return
        
    print(f"Mask loaded. Sum of mask pixels: {np.sum(mask)}")
    
    for i in range(len(products) - 1):
        p1 = products[i]
        p2 = products[i+1]
        dt = (p2['date'] - p1['date']).total_seconds() / 86400
        pair_str = f"{p1['date'].strftime('%Y-%m-%d')} -- {p2['date'].strftime('%m-%d')}"
        
        print(f"Processing {pair_str}...")
        try:
            img1, _, _, _, _ = load_image(p1['path'])
            img2, _, _, _, _ = load_image(p2['path'])
        except Exception as e:
            print(f"Failed to process {pair_str}: {e}")
            continue
            
        img1 = np.nan_to_num(img1, nan=0.0)
        img2 = np.nan_to_num(img2, nan=0.0)
        
        results = tracking_with_fraction(img1, img2, mask)
        
        if len(results) == 0:
            table_lines.append(f"{pair_str} & 0 & NaN & NaN & NaN & NaN \\\\")
            continue
            
        df = pd.DataFrame(results)
        df['velocity'] = df['D_px'] * PIXEL_SIZE_METERS / dt
        
        n_valid = len(df)
        med_corr = df['corr'].median()
        
        v50 = df[df['frac'] >= 0.50]['velocity'].median()
        v70 = df[df['frac'] >= 0.70]['velocity'].median()
        v90 = df[df['frac'] >= 0.90]['velocity'].median()
        
        def fmt(v): return f"{v:.1f}" if pd.notna(v) else "NaN"
        
        table_lines.append(f"{pair_str} & {n_valid} & {med_corr:.3f} & {fmt(v50)} & {fmt(v70)} & {fmt(v90)} \\\\")
        
    table_lines.append("\\bottomrule")
    table_lines.append("\\end{tabular}")
    table_lines.append("\\end{table}")
    
    with open(OUTPUT_DIR / "masking_sensitivity_table.tex", 'w') as f:
        f.write('\n'.join(table_lines) + '\n')
        
    print("Saved masking sensitivity table.")

if __name__ == "__main__":
    main()
