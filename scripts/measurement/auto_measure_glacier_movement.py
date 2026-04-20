#!/usr/bin/env python3
"""
Automatically detect and measure glacier movement using image analysis
"""

import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Arrow, Rectangle
from pathlib import Path
from scipy import ndimage
from skimage import filters, feature, segmentation
import cv2

def detect_glacier_front(img_array):
    """Detect glacier front using edge detection"""
    # Convert to grayscale if needed
    if len(img_array.shape) == 3:
        gray = np.mean(img_array, axis=2)
    else:
        gray = img_array
    
    # Apply edge detection
    edges = filters.sobel(gray)
    
    # Threshold to get strong edges
    threshold = np.percentile(edges, 90)
    strong_edges = edges > threshold
    
    return strong_edges, edges

def analyze_movement():
    """Analyze glacier movement from images"""
    output_dir = Path('planet_images/visualizations')
    
    # Load images
    img_sep12 = np.array(Image.open(output_dir / 'glacier_cropped_2025-09-12.png'))
    img_sep17 = np.array(Image.open(output_dir / 'glacier_cropped_2025-09-17.png'))
    img_oct25 = np.array(Image.open(output_dir / 'glacier_cropped_2025-10-25.png'))
    
    resolution = 5.88  # m/pixel
    
    print("=" * 60)
    print("AUTOMATIC GLACIER MOVEMENT DETECTION")
    print("=" * 60)
    print(f"\nResolution: {resolution} meters per pixel")
    print("\nAnalyzing images for glacier front detection...")
    
    # Get image dimensions
    h, w = img_sep12.shape[:2]
    print(f"Image size: {w} x {h} pixels")
    
    # Calculate change detection
    # Convert to grayscale for comparison
    gray_sep12 = np.mean(img_sep12, axis=2) if len(img_sep12.shape) == 3 else img_sep12
    gray_sep17 = np.mean(img_sep17, axis=2) if len(img_sep17.shape) == 3 else img_sep17
    gray_oct25 = np.mean(img_oct25, axis=2) if len(img_oct25.shape) == 3 else img_oct25
    
    # Calculate differences
    diff_sep12_sep17 = np.abs(gray_sep17.astype(float) - gray_sep12.astype(float))
    diff_sep17_oct25 = np.abs(gray_oct25.astype(float) - gray_sep17.astype(float))
    diff_sep12_oct25 = np.abs(gray_oct25.astype(float) - gray_sep12.astype(float))
    
    # Find regions of maximum change (likely glacier movement)
    # Focus on lower portion of image where glacier front typically is
    lower_half = h // 2
    
    # Find maximum change in lower half (glacier front area)
    change_region_1 = diff_sep12_sep17[lower_half:, :]
    change_region_2 = diff_sep17_oct25[lower_half:, :]
    
    # Find peak change locations
    max_change_1 = np.unravel_index(np.argmax(change_region_1), change_region_1.shape)
    max_change_2 = np.unravel_index(np.argmax(change_region_2), change_region_2.shape)
    
    # Adjust coordinates (add offset for lower half)
    peak_1 = (max_change_1[1], max_change_1[0] + lower_half)
    peak_2 = (max_change_2[1], max_change_2[0] + lower_half)
    
    print(f"\nDetected change peaks:")
    print(f"  Sep 12 → Sep 17: ({peak_1[0]:.0f}, {peak_1[1]:.0f}) pixels")
    print(f"  Sep 17 → Oct 25: ({peak_2[0]:.0f}, {peak_2[1]:.0f}) pixels")
    
    # Create visualization
    fig, axes = plt.subplots(2, 3, figsize=(24, 16))
    
    # Top row: Original images
    axes[0, 0].imshow(img_sep12)
    axes[0, 0].set_title('Sep 12, 2025\nBaseline', fontsize=12, fontweight='bold')
    axes[0, 0].axis('off')
    
    axes[0, 1].imshow(img_sep17)
    axes[0, 1].set_title('Sep 17, 2025\nFirst Movement', fontsize=12, fontweight='bold')
    axes[0, 1].axis('off')
    
    axes[0, 2].imshow(img_oct25)
    axes[0, 2].set_title('Oct 25, 2025\nSecond Movement', fontsize=12, fontweight='bold')
    axes[0, 2].axis('off')
    
    # Bottom row: Change detection
    axes[1, 0].imshow(diff_sep12_sep17, cmap='hot')
    axes[1, 0].plot(peak_1[0], peak_1[1], 'b*', markersize=20, label='Peak change')
    axes[1, 0].set_title('Change: Sep 12 → Sep 17', fontsize=12, fontweight='bold')
    axes[1, 0].axis('off')
    axes[1, 0].legend()
    
    axes[1, 1].imshow(diff_sep17_oct25, cmap='hot')
    axes[1, 1].plot(peak_2[0], peak_2[1], 'b*', markersize=20, label='Peak change')
    axes[1, 1].set_title('Change: Sep 17 → Oct 25', fontsize=12, fontweight='bold')
    axes[1, 1].axis('off')
    axes[1, 1].legend()
    
    axes[1, 2].imshow(diff_sep12_oct25, cmap='hot')
    axes[1, 2].set_title('Total Change: Sep 12 → Oct 25', fontsize=12, fontweight='bold')
    axes[1, 2].axis('off')
    
    plt.suptitle('Glacier Movement Detection Analysis\n'
                 'Red/Yellow areas indicate change (potential glacier movement)',
                 fontsize=14, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    output_path = output_dir / 'glacier_movement_auto_detection.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n✓ Created analysis visualization: {output_path}")
    
    print("\n" + "=" * 60)
    print("NOTE: Automatic detection provides approximate locations.")
    print("For accurate measurements, manual point selection is recommended.")
    print("=" * 60)
    print("\nTo get precise measurements:")
    print("1. Open the cropped images in an image viewer")
    print("2. Identify a fixed reference point")
    print("3. Mark glacier front edge for each date")
    print("4. Use calculate_movement.py with your coordinates")
    
    return peak_1, peak_2

if __name__ == '__main__':
    try:
        analyze_movement()
    except ImportError:
        print("Note: scipy/skimage not available. Using basic analysis...")
        print("\nFor automatic detection, install: pip install scipy scikit-image")
        print("Or use manual measurement method with calculate_movement.py")

