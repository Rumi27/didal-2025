
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
from pathlib import Path
import zipfile
import subprocess
import sys
from typing import Tuple, List, Dict, Optional

# Try to import optional libraries
try:
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
except ImportError:
    print("⚠️  PIL not installed. Install with: pip install Pillow")
    Image = None

try:
    import scipy
    from scipy import ndimage
    from scipy import signal
except ImportError:
    print("⚠️  scipy not installed. Install with: pip install scipy")
    scipy = None


# Study area coordinates for Didal Glacier
# Bbox: [70.65, 39.05, 70.80, 38.90] (ulx uly lrx lry) - Tighter crop for speed
CROP_BBOX = [70.65, 39.05, 70.80, 38.90]

# Input/Output directories
# We use the 'processed' directory which contains Terrain Corrected (TC) products
INPUT_DIR = Path("satellite_data/sentinel1/processed")
OUTPUT_DIR = Path("satellite_data/sentinel1/processed_subpixel")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR = OUTPUT_DIR / "temp_crops"
TEMP_DIR.mkdir(exist_ok=True)

# Processing parameters
WINDOW_SIZES = [128]
SEARCH_RANGE = 100
STABLE_BEDROCK_THRESHOLD = 0.1
MIN_CORRELATION = 0.3
PIXEL_SIZE_METERS = 10.0  # Approx pixel size for 0.00008983 deg


def parabolic_refinement(corr_map, y, x):
    """
    Perform 1D parabolic refinement around the peak (y, x).
    Returns sub-pixel offsets (dy_sub, dx_sub) relative to (y, x).
    """
    h, w = corr_map.shape
    if y <= 0 or y >= h - 1 or x <= 0 or x >= w - 1:
        return 0.0, 0.0

    # 1D Parabolic fit in X
    c1 = corr_map[y, x - 1]
    c2 = corr_map[y, x]
    c3 = corr_map[y, x + 1]
    denominator_x = 2 * (2 * c2 - c1 - c3)
    if abs(denominator_x) < 1e-6:
        dx_sub = 0.0
    else:
        dx_sub = (c1 - c3) / denominator_x

    # 1D Parabolic fit in Y
    c1 = corr_map[y - 1, x]
    c2 = corr_map[y, x]
    c3 = corr_map[y + 1, x]
    denominator_y = 2 * (2 * c2 - c1 - c3)
    if abs(denominator_y) < 1e-6:
        dy_sub = 0.0
    else:
        dy_sub = (c1 - c3) / denominator_y
        
    return dy_sub, dx_sub


def offset_tracking_subpixel(image1: np.ndarray, image2: np.ndarray,
                            window_size: int, search_range: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Perform offset tracking with sub-pixel refinement.
    """
    h, w = image1.shape
    step = window_size  # No overlap for speed
    
    out_h = h
    out_w = w
    
    dx = np.full((h, w), np.nan, dtype=np.float32)
    dy = np.full((h, w), np.nan, dtype=np.float32)
    correlation = np.full((h, w), np.nan, dtype=np.float32)
    
    half_window = window_size // 2
    
    print(f"    Grid tracking (Win={window_size}, Search={search_range})...", flush=True)

    # Simplified search for demonstration
    
    for y in range(half_window, h - half_window, step):
        for x in range(half_window, w - half_window, step):
            
            # Extract template from Image 1
            template = image1[y-half_window:y+half_window, x-half_window:x+half_window]
            template = template - np.mean(template)
            std_t = np.std(template)
            if std_t == 0:
                continue
            
            # Extract search area from Image 2
            y_min_s = max(0, y - half_window - search_range)
            y_max_s = min(h, y + half_window + search_range)
            x_min_s = max(0, x - half_window - search_range)
            x_max_s = min(w, x + half_window + search_range)
            
            search_area = image2[y_min_s:y_max_s, x_min_s:x_max_s]
            
            # Simple NCC
            if np.std(search_area) == 0:
                continue

            if scipy:
                from scipy import signal
                corr_map_raw = signal.correlate2d(search_area, template, mode='valid')
                
                # Find peak
                y_peak, x_peak = np.unravel_index(np.argmax(corr_map_raw), corr_map_raw.shape)
                max_val = corr_map_raw[y_peak, x_peak]
                
                # Normalize approx
                norm_factor = np.std(search_area) * std_t * template.size
                if norm_factor > 0:
                    best_corr = max_val / norm_factor
                else:
                    best_corr = 0
                
                # Map peak back to offsets
                dy_local = y_peak - search_range
                dx_local = x_peak - search_range
                
                best_dy_int = dy_local
                best_dx_int = dx_local
                
                if best_corr >= MIN_CORRELATION:
                    # Sub-pixel refinement
                    dy_sub, dx_sub = parabolic_refinement(corr_map_raw, y_peak, x_peak)
                    
                    dx[y, x] = best_dx_int + dx_sub
                    dy[y, x] = best_dy_int + dy_sub
                    correlation[y, x] = best_corr
            
    return dx, dy, correlation


def compute_velocity(dx, dy, pixel_size, time_delta_days):
    displacement = np.sqrt(dx**2 + dy**2) * pixel_size
    velocity = displacement / time_delta_days
    return velocity


def compute_lod_from_stable_bedrock(velocity, correlation):
    valid_mask = (correlation > 0.5) & (~np.isnan(velocity))
    if np.sum(valid_mask) == 0:
        return np.nan
    
    vals = np.sort(velocity[valid_mask])
    n_stable = max(1, int(len(vals) * 0.2))
    stable_vals = vals[:n_stable]
    
    lod = np.mean(stable_vals) + 2 * np.std(stable_vals)
    return lod


def find_sentinel1_products():
    """Find all Sentinel-1 GRD TC products (.dim)."""
    print("=" * 70, flush=True)
    print("Finding Sentinel-1 TC Products", flush=True)
    print("=" * 70, flush=True)
    # Look for Orb_Cal_TC.dim
    dim_files = sorted(INPUT_DIR.glob("*Orb_Cal_TC.dim"))
    if not dim_files:
        print(f"❌ No Sentinel-1 TC products found in {INPUT_DIR}", flush=True)
        return []
    print(f"Found {len(dim_files)} Sentinel-1 TC products", flush=True)
    return dim_files


def parse_sentinel1_metadata(file_path: Path) -> Dict:
    """Parse Sentinel-1 metadata from filename."""
    metadata = {
        'file_path': str(file_path),
        'acquisition_date': None
    }
    # Parse filename: S1A_...20250907T...
    name = file_path.name
    parts = name.split('_')
    for part in parts:
        if 'T' in part and len(part) == 15:
            try:
                metadata['acquisition_date'] = datetime.strptime(part, '%Y%m%dT%H%M%S')
                break
            except:
                pass
    return metadata


def load_sentinel1_image(dim_path: Path, band: str = 'VV') -> Tuple[np.ndarray, Dict]:
    """Load crop from Sentinel-1 TC product (.data/Sigma0_VV.img) using GDAL."""
    print(f"  Loading {dim_path.name}...", flush=True)
    
    safe_name_base = dim_path.stem
    
    # Path to .data directory
    data_dir = dim_path.with_suffix(".data")
    # Path to image file
    img_path = data_dir / f"Sigma0_{band}.img"
    
    if not img_path.exists():
         print(f"    ⚠️ Image file not found: {img_path}", flush=True)
         return None, None
             
    crop_name = f"crop_{safe_name_base}_tight.tif"
    crop_path = TEMP_DIR / crop_name
    
    if not crop_path.exists():
        print(f"    Cropping...", flush=True)
        
        cmd = [
            "gdal_translate",
            "-projwin", str(CROP_BBOX[0]), str(CROP_BBOX[1]), str(CROP_BBOX[2]), str(CROP_BBOX[3]),
            "-projwin_srs", "EPSG:4326",
            "-of", "GTiff",
            str(img_path),
            str(crop_path)
        ]
        try:
            # We remove stdout=DEVNULL to see errors if any, but capture stderr
            result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("    GDAL success.", flush=True)
        except subprocess.CalledProcessError as e:
            print(f"    ⚠️ GDAL crop failed: {e.stderr.decode()}", flush=True)
            return None, None
    else:
        print(f"    Using cached crop", flush=True)
    
    if Image and crop_path.exists():
        try:
            with Image.open(crop_path) as img:
                data = np.array(img)
                # If multi-band (VV/VH), pick VV. 
                # PIL loads as (H, W) or (H, W, Channels).
                if data.ndim == 3:
                    # Assume band 0 is VV
                    data = data[:, :, 0]
                    
                metadata = {
                    'width': img.width,
                    'height': img.height,
                    'transform': [PIXEL_SIZE_METERS, 0, 0, 0, -PIXEL_SIZE_METERS, 0]
                }
                print(f"    Loaded crop: {data.shape}", flush=True)
                return data, metadata
        except Exception as e:
            print(f"    ⚠️ Error loading crop with PIL: {e}", flush=True)
            return None, None
    return None, None


def process_pairs(products):
    print("Processing Sentinel-1 Pairs with Sub-pixel Refinement...", flush=True)
    
    product_metadata = []
    for f in products:
        meta = parse_sentinel1_metadata(f)
        product_metadata.append(meta)
    
    product_metadata.sort(key=lambda x: x['acquisition_date'] if x['acquisition_date'] else datetime.min)
    
    velocity_results = []
    
    for i in range(len(product_metadata) - 1):
        meta1 = product_metadata[i]
        meta2 = product_metadata[i + 1]
        
        date1 = meta1['acquisition_date']
        date2 = meta2['acquisition_date']
        
        if not date1 or not date2:
            continue
            
        time_delta = (date2 - date1).total_seconds() / 86400
        print(f"Processing pair {i+1}/{len(product_metadata)-1}: {date1.date()} -> {date2.date()} ({time_delta:.1f} d)", flush=True)
        
        img1, m1 = load_sentinel1_image(Path(meta1['file_path']))
        img2, m2 = load_sentinel1_image(Path(meta2['file_path']))
        
        if img1 is None or img2 is None:
             print("  ⚠️ Skipped: Failed to load images.", flush=True)
             continue
            
        pixel_size = PIXEL_SIZE_METERS
        
        # We only use 128px for this refinement test as requested
        window_size = 128
        
        dx, dy, corr = offset_tracking_subpixel(img1, img2, window_size, SEARCH_RANGE)
        vel = compute_velocity(dx, dy, pixel_size, time_delta)
        lod = compute_lod_from_stable_bedrock(vel, corr)
        
        valid_vel = vel[~np.isnan(vel)]
        mean_v = np.nanmean(valid_vel) if len(valid_vel)>0 else np.nan
        std_v = np.nanstd(valid_vel) if len(valid_vel)>0 else np.nan
        
        velocity_results.append({
            'date1': date1.strftime('%Y-%m-%d'),
            'date2': date2.strftime('%Y-%m-%d'),
            'time_delta_days': time_delta,
            'velocity_m_per_day': mean_v,
            'velocity_std': std_v,
            'lod_m_per_day': lod
        })
            
    return pd.DataFrame(velocity_results)


if __name__ == "__main__":
    products = find_sentinel1_products()
    if products:
        df = process_pairs(products)
        output_path = OUTPUT_DIR / "velocity_timeseries_subpixel.csv"
        df.to_csv(output_path, index=False)
        print(f"\n✅ Processing complete. Saved to {output_path}", flush=True)
        print(df, flush=True)
    else:
        print("❌ No products found.", flush=True)
