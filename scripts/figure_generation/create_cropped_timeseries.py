#!/usr/bin/env python3
"""
Create time series and change detection using the cropped (focused) images.
Uses the *_fixed_crop.png images that are already cropped to the glacier area.
"""

import os
import glob
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from datetime import datetime
from PIL import Image

OUTPUT_DIR = "planet_images/visualizations"

def extract_date_from_filename(filename):
    """Extract date from filename."""
    basename = os.path.basename(filename)
    date_str = basename[:10]  # YYYY-MM-DD
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        return date
    except:
        return None

def create_cropped_timeseries():
    """Create time series using cropped images."""
    print("=" * 70)
    print("Create Cropped Time Series (Glacier-Focused)")
    print("=" * 70)
    print()
    
    # Find all fixed_crop images
    pattern = os.path.join(OUTPUT_DIR, "*_fixed_crop.png")
    image_files = glob.glob(pattern)
    
    # Filter and sort by date
    images_data = []
    for img_file in image_files:
        date = extract_date_from_filename(img_file)
        if date:
            images_data.append((date, img_file))
    
    images_data.sort(key=lambda x: x[0])
    
    if not images_data:
        print("No cropped images found!")
        return
    
    print(f"Found {len(images_data)} cropped images:")
    for date, img_file in images_data:
        print(f"  {date.strftime('%Y-%m-%d')}: {os.path.basename(img_file)}")
    print()
    
    # Create time series figure
    n_images = len(images_data)
    cols = min(3, n_images)
    rows = (n_images + cols - 1) // cols
    
    fig = plt.figure(figsize=(18, 6 * rows))
    gs = GridSpec(rows, cols, figure=fig, hspace=0.3, wspace=0.2)
    
    for i, (date, img_file) in enumerate(images_data):
        row = i // cols
        col = i % cols
        ax = fig.add_subplot(gs[row, col])
        
        # Load and display image
        img = Image.open(img_file)
        ax.imshow(img, interpolation='bilinear')
        
        date_str = date.strftime("%Y-%m-%d")
        event_label = ""
        if date_str == "2025-09-12":
            event_label = " (Before Initial Movement)"
        elif date_str == "2025-09-17":
            event_label = " (Before Initial Movement - Edge)"
        elif date_str == "2025-10-25":
            event_label = " (Second Movement)"
        elif date_str == "2025-11-01":
            event_label = " (Continued Movement)"
        elif date_str == "2025-11-02":
            event_label = " (Continued Movement)"
        elif date_str == "2025-11-03":
            event_label = " (Earthquake Day)"
        
        ax.set_title(f"{date_str}{event_label}", fontsize=12, fontweight='bold')
        ax.axis('off')
    
    # Overall title
    fig.suptitle("Didal Glacier Time Series - Glacier-Focused View\n"
                "5 km × 5 km crop centered on glacier (39.0005°N, 70.7385°E)\n"
                "PlanetScope Imagery (3 m resolution)", 
                fontsize=16, fontweight='bold', y=0.98)
    
    output_file = os.path.join(OUTPUT_DIR, "timeseries_comparison.png")
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"✓ Saved: {output_file}")

def create_cropped_change_detection():
    """Create change detection using cropped images."""
    print("\nCreating cropped change detection visualization...")
    
    # Find before and after images
    before_files = glob.glob(os.path.join(OUTPUT_DIR, "2025-09-*_fixed_crop.png"))
    after_files = glob.glob(os.path.join(OUTPUT_DIR, "2025-11-*_fixed_crop.png"))
    
    # Use September 12 as "before" (best quality)
    before_file = None
    for f in before_files:
        if "2025-09-12" in f:
            before_file = f
            break
    if not before_file and before_files:
        before_file = sorted(before_files)[0]  # Use first available
    
    # Use November 3 as "after" (latest)
    after_file = None
    for f in after_files:
        if "2025-11-03" in f:
            after_file = f
            break
    if not after_file and after_files:
        after_file = sorted(after_files)[-1]  # Use last available
    
    if not before_file or not after_file:
        print(f"  Need both before and after images")
        print(f"  Before: {before_file}")
        print(f"  After: {after_file}")
        return
    
    print(f"  Before: {os.path.basename(before_file)}")
    print(f"  After: {os.path.basename(after_file)}")
    
    # Load images
    before_img = np.array(Image.open(before_file))
    after_img = np.array(Image.open(after_file))
    
    # Create comparison figure
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    # Before
    axes[0].imshow(before_img, interpolation='bilinear')
    before_date = extract_date_from_filename(before_file)
    before_date_str = before_date.strftime("%Y-%m-%d") if before_date else "Before"
    axes[0].set_title(f"Before\n{before_date_str}", 
                     fontsize=12, fontweight='bold')
    axes[0].axis('off')
    
    # After
    axes[1].imshow(after_img, interpolation='bilinear')
    after_date = extract_date_from_filename(after_file)
    after_date_str = after_date.strftime("%Y-%m-%d") if after_date else "After"
    axes[1].set_title(f"After\n{after_date_str}", 
                     fontsize=12, fontweight='bold')
    axes[1].axis('off')
    
    # Difference
    try:
        # Convert to float and normalize
        before_float = before_img.astype(np.float32) / 255.0
        after_float = after_img.astype(np.float32) / 255.0
        
        # Resize if needed (simple numpy-based)
        if before_float.shape != after_float.shape:
            # Simple nearest neighbor resize
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
        # Show after image instead
        axes[2].imshow(after_img, interpolation='bilinear')
        axes[2].set_title("After (Detail)", 
                         fontsize=12, fontweight='bold')
        axes[2].axis('off')
    
    fig.suptitle("Didal Glacier - Before/After Change Detection\n"
                "Glacier-Focused View (5 km × 5 km crop)", 
                fontsize=14, fontweight='bold')
    
    output_file = os.path.join(OUTPUT_DIR, "change_detection_before_after.png")
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"  ✓ Saved: {output_file}")

def main():
    """Main function."""
    create_cropped_timeseries()
    create_cropped_change_detection()
    
    print()
    print("=" * 70)
    print("Complete!")
    print("=" * 70)
    print()
    print("Updated visualizations:")
    print("  - timeseries_comparison.png (glacier-focused)")
    print("  - change_detection_before_after.png (glacier-focused)")

if __name__ == "__main__":
    main()

