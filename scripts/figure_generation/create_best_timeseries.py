#!/usr/bin/env python3
"""
Create final time series using the BEST focused images for each date:
- Nov 1: glacier_focused.png
- Nov 2-3: fixed_crop.png
- Also include Sept 12 and Oct 25 if available
"""

import os
import glob
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from datetime import datetime
from PIL import Image

OUTPUT_DIR = "planet_images/visualizations"

def create_best_timeseries():
    """Create time series using the best images for each date."""
    print("=" * 70)
    print("Create Final Time Series - Best Images")
    print("=" * 70)
    print()
    
    # Define the best images for each date
    best_images = {
        "2025-09-12": {
            "pattern": "*20250912*_fixed_crop.png",
            "label": "Before Initial Movement",
            "event": "Baseline (5 days before initial movement)"
        },
        "2025-10-25": {
            "pattern": "*20251025*_fixed_crop.png",
            "label": "Second Movement",
            "event": "Second movement event"
        },
        "2025-11-01": {
            "pattern": "*20251101*_glacier_focused.png",  # Best version
            "label": "Continued Movement",
            "event": "Continued movement"
        },
        "2025-11-02": {
            "pattern": "*20251102*_fixed_crop.png",  # Best version
            "label": "Continued Movement",
            "event": "Continued movement"
        },
        "2025-11-03": {
            "pattern": "*20251103*_fixed_crop.png",  # Best version
            "label": "Earthquake Day",
            "event": "Earthquake occurred (M4-7)"
        }
    }
    
    # Find images
    found_images = []
    for date_str, info in best_images.items():
        pattern = os.path.join(OUTPUT_DIR, info["pattern"])
        matches = glob.glob(pattern)
        
        if matches:
            img_file = matches[0]  # Take first match
            date = datetime.strptime(date_str, "%Y-%m-%d")
            found_images.append({
                "file": img_file,
                "date": date_str,
                "date_obj": date,
                "label": info["label"],
                "event": info["event"]
            })
            print(f"✓ Found: {date_str} - {os.path.basename(img_file)}")
        else:
            print(f"✗ Missing: {date_str} - {info['pattern']}")
    
    print()
    print(f"Found {len(found_images)} out of {len(best_images)} images")
    print()
    
    if len(found_images) < 3:
        print("⚠️  Warning: Need at least 3 images for time series")
        return
    
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
    fig.suptitle("Didal Glacier Time Series - Best Available Images\n"
                "PlanetScope Imagery (3 m resolution, glacier-focused crop)\n"
                "Glacier location: 39.0005°N, 70.7385°E", 
                fontsize=16, fontweight='bold', y=0.98)
    
    # Save
    output_file = os.path.join(OUTPUT_DIR, "final_timeseries_best.png")
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white', pad_inches=0.5)
    plt.close()
    
    print(f"✓ Saved: {output_file}")
    print()
    
    # Create change detection with best images
    print("Creating change detection with best images...")
    
    # Use Sept 12 as before, Nov 3 as after
    before_file = None
    after_file = None
    
    for img_info in found_images:
        if img_info["date"] == "2025-09-12":
            before_file = img_info["file"]
        elif img_info["date"] == "2025-11-03":
            after_file = img_info["file"]
    
    if before_file and after_file:
        # Load images
        before_img = np.array(Image.open(before_file))
        after_img = np.array(Image.open(after_file))
        
        # Create comparison figure
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        
        # Before
        axes[0].imshow(before_img, interpolation='bilinear')
        axes[0].set_title(f"Before\n2025-09-12\n(Before Initial Movement)", 
                         fontsize=12, fontweight='bold')
        axes[0].axis('off')
        
        # After
        axes[1].imshow(after_img, interpolation='bilinear')
        axes[1].set_title(f"After\n2025-11-03\n(Earthquake Day)", 
                         fontsize=12, fontweight='bold')
        axes[1].axis('off')
        
        # Difference
        try:
            # Convert to float and normalize
            before_float = before_img.astype(np.float32) / 255.0
            after_float = after_img.astype(np.float32) / 255.0
            
            # Resize if needed (simple numpy-based)
            if before_float.shape != after_float.shape:
                h_ratio = after_float.shape[0] / before_float.shape[0]
                w_ratio = after_float.shape[1] / before_float.shape[1]
                h_indices = (np.arange(after_float.shape[0]) / h_ratio).astype(int)
                w_indices = (np.arange(after_float.shape[1]) / w_ratio).astype(int)
                h_indices = np.clip(h_indices, 0, before_float.shape[0] - 1)
                w_indices = np.clip(w_indices, 0, before_float.shape[1] - 1)
                before_resized = before_float[h_indices[:, None], w_indices]
            else:
                before_resized = before_float
            
            # Calculate difference
            diff = np.abs(after_float - before_resized)
            diff = np.clip(diff * 3, 0, 1)  # Enhance contrast
            
            axes[2].imshow(diff, interpolation='bilinear')
            axes[2].set_title("Change Detection\n(Difference)", 
                            fontsize=12, fontweight='bold')
            axes[2].axis('off')
        except Exception as e:
            print(f"  Warning: Could not create difference image: {e}")
            axes[2].imshow(after_img, interpolation='bilinear')
            axes[2].set_title("After (Detail)", fontsize=12, fontweight='bold')
            axes[2].axis('off')
        
        fig.suptitle("Didal Glacier - Before/After Change Detection\n"
                    "Best Available Images (Glacier-Focused)", 
                    fontsize=14, fontweight='bold')
        
        output_file_cd = os.path.join(OUTPUT_DIR, "change_detection_before_after.png")
        plt.savefig(output_file_cd, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"✓ Saved: {output_file_cd}")
    else:
        print("⚠️  Could not create change detection (missing before/after images)")
    
    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print()
    print("Timeline:")
    for img_info in found_images:
        print(f"  {img_info['date']}: {img_info['label']}")
    print()
    print(f"Total images: {len(found_images)}")
    print(f"Time span: {found_images[0]['date']} to {found_images[-1]['date']}")

if __name__ == "__main__":
    import numpy as np
    create_best_timeseries()

