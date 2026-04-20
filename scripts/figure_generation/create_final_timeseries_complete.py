#!/usr/bin/env python3
"""
Create final complete time series visualization with all available dates:
- September 12: Before initial movement
- October 25: Second movement  
- November 1-3: Continued movement
"""

import os
import glob
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from datetime import datetime
from PIL import Image

OUTPUT_DIR = "planet_images/visualizations"

def extract_date_from_filename(filename):
    """Extract date from filename."""
    basename = os.path.basename(filename)
    # Try different formats
    for fmt in ["%Y-%m-%d", "%Y%m%d"]:
        try:
            if fmt == "%Y-%m-%d":
                date_str = basename[:10]
            else:
                date_str = basename[:8]
            date = datetime.strptime(date_str, fmt)
            return date
        except:
            continue
    return None

def create_final_timeseries():
    """Create final time series with all available dates."""
    print("=" * 70)
    print("Create Final Complete Time Series")
    print("=" * 70)
    print()
    
    # Define the images we want (in chronological order)
    target_images = {
        "2025-09-12": {
            "filename": "2025-09-12_*_fixed_crop.png",
            "label": "Before Initial Movement",
            "event": "Baseline (5 days before initial movement)"
        },
        "2025-10-25": {
            "filename": "2025-10-25_*_fixed_crop.png",
            "label": "Second Movement",
            "event": "Second movement event"
        },
        "2025-11-01": {
            "filename": "2025-11-01_*_fixed_crop.png",
            "label": "Continued Movement",
            "event": "Continued movement"
        },
        "2025-11-02": {
            "filename": "2025-11-02_*_fixed_crop.png",
            "label": "Continued Movement",
            "event": "Continued movement"
        },
        "2025-11-03": {
            "filename": "2025-11-03_*_fixed_crop.png",
            "label": "Earthquake Day",
            "event": "Earthquake occurred (M4-7)"
        }
    }
    
    # Find images
    found_images = []
    for date_str, info in target_images.items():
        pattern = os.path.join(OUTPUT_DIR, info["filename"])
        matches = glob.glob(pattern)
        
        if matches:
            img_file = matches[0]  # Take first match
            date = extract_date_from_filename(img_file)
            found_images.append({
                "file": img_file,
                "date": date_str,
                "date_obj": date,
                "label": info["label"],
                "event": info["event"]
            })
            print(f"✓ Found: {date_str} - {os.path.basename(img_file)}")
        else:
            print(f"✗ Missing: {date_str} - {info['filename']}")
    
    print()
    print(f"Found {len(found_images)} out of {len(target_images)} images")
    print()
    
    if len(found_images) < 3:
        print("⚠️  Warning: Need at least 3 images for time series")
        print("   Available images may not show complete timeline")
        print()
    
    # Sort by date
    found_images.sort(key=lambda x: x["date"])
    
    # Create time series figure
    n_images = len(found_images)
    cols = min(3, n_images)
    rows = (n_images + cols - 1) // cols
    
    fig = plt.figure(figsize=(18, 6 * rows))
    gs = GridSpec(rows, cols, figure=fig, hspace=0.35, wspace=0.25)
    
    for i, img_info in enumerate(found_images):
        row = i // cols
        col = i % cols
        ax = fig.add_subplot(gs[row, col])
        
        # Load and display image
        try:
            img = Image.open(img_info["file"])
            ax.imshow(img, interpolation='bilinear')
        except Exception as e:
            print(f"Error loading {img_info['file']}: {e}")
            ax.text(0.5, 0.5, f"Error loading image\n{img_info['date']}", 
                   ha='center', va='center', fontsize=12)
            ax.axis('off')
            continue
        
        # Title with date and event info
        title = f"{img_info['date']}\n{img_info['label']}"
        if img_info['event']:
            title += f"\n({img_info['event']})"
        
        ax.set_title(title, fontsize=13, fontweight='bold', pad=10)
        ax.axis('off')
    
    # Overall title
    fig.suptitle("Didal Glacier Time Series - Complete Event Timeline\n"
                "PlanetScope Imagery (3 m resolution, 5 km × 5 km crop)\n"
                "Glacier location: 39.0005°N, 70.7385°E", 
                fontsize=16, fontweight='bold', y=0.98)
    
    # Save
    output_file = os.path.join(OUTPUT_DIR, "final_timeseries_complete.png")
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white', pad_inches=0.5)
    plt.close()
    
    print(f"✓ Saved: {output_file}")
    print()
    
    # Create a summary
    print("=" * 70)
    print("Time Series Summary")
    print("=" * 70)
    print()
    print("Timeline:")
    for img_info in found_images:
        print(f"  {img_info['date']}: {img_info['label']}")
        if img_info['event']:
            print(f"    → {img_info['event']}")
    print()
    print(f"Total images: {len(found_images)}")
    print(f"Time span: {found_images[0]['date']} to {found_images[-1]['date']}")
    print()
    
    # Note about missing dates
    missing = [date for date in target_images.keys() if date not in [img["date"] for img in found_images]]
    if missing:
        print("Missing dates:")
        for date in missing:
            print(f"  - {date}: {target_images[date]['label']}")
        print()

if __name__ == "__main__":
    create_final_timeseries()

