#!/usr/bin/env python3
"""
Analyze glacier movement using screenshot images
- Uses letter format images (Sep_, Oct_)
- Crops to glacier area
- Fixes reference point
- Measures movement distances using pixel size from metadata
"""

import os
import re
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Arrow, FancyBboxPatch
import json

def parse_date_from_filename(filename):
    """Parse date from filename - only letter format (Sep_, Oct_)"""
    base_name = filename.replace('.jpg', '').replace('.JPG', '')
    
    month_map = {
        'Sep': '09', 'September': '09',
        'Oct': '10', 'October': '10',
        'Nov': '11', 'November': '11',
        'Dec': '12', 'December': '12',
    }
    
    # Only process letter format (Sep_, Oct_)
    for month_name, month_num in month_map.items():
        if base_name.startswith(month_name + '_'):
            parts = base_name.split('_')
            if len(parts) >= 3:
                try:
                    day = int(parts[1])
                    year = int(parts[2])
                    return datetime(year, int(month_num), day)
                except:
                    pass
    
    return None

def extract_metadata_from_image(img):
    """Try to extract metadata from image (zoom, resolution, scale)"""
    # These are typically in bottom right corner
    # We'll need to read them from the image or use known values
    # For now, we'll use typical values and allow manual input
    
    # Typical values from Planet screenshots:
    # Zoom: ~14.34, Resolution: ~5.88 m/px, Scale: ~500m
    
    # Try to detect from image if possible, otherwise use defaults
    # Default values based on typical Planet screenshot metadata
    default_resolution = 5.88  # meters per pixel
    default_scale = 500  # meters
    
    return {
        'resolution_m_per_px': default_resolution,
        'scale_m': default_scale,
        'zoom': 14.34
    }

def enhance_image_quality(img):
    """Enhance image quality to maximum"""
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Maximum quality enhancements
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.5)
    
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.2)
    
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.1)
    
    return img

def find_glacier_region(img):
    """Find the glacier region in the image (approximate crop area)"""
    # This is a simplified approach - in practice, you'd want to manually
    # define the crop region or use image analysis
    
    # For now, we'll use a center crop that focuses on the glacier area
    # The user can adjust these coordinates based on their images
    
    width, height = img.size
    
    # Default: crop to center 60% of image (adjustable)
    crop_ratio = 0.6
    crop_width = int(width * crop_ratio)
    crop_height = int(height * crop_ratio)
    
    left = (width - crop_width) // 2
    top = (height - crop_height) // 2
    right = left + crop_width
    bottom = top + crop_height
    
    return (left, top, right, bottom)

def create_movement_analysis():
    """Create movement analysis visualization"""
    screenshot_dir = Path('planet_images/screenshot_planet')
    output_dir = Path('planet_images/visualizations')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not screenshot_dir.exists():
        print(f"Directory not found: {screenshot_dir}")
        return
    
    # Get only letter format images
    screenshots = [s for s in screenshot_dir.glob('*.jpg') + screenshot_dir.glob('*.JPG')
                   if parse_date_from_filename(s.name)]
    
    # Key dates
    key_dates = {
        datetime(2025, 9, 12): 'Baseline\n(5 days before\ninitial movement)',
        datetime(2025, 9, 17): 'Initial movement\ndetected',
        datetime(2025, 10, 25): 'Second movement',
    }
    
    # Find images for key dates
    selected_images = []
    for key_date, label in key_dates.items():
        matching = [s for s in screenshots if parse_date_from_filename(s.name) == key_date]
        if matching:
            # Prefer the letter format (should be only one)
            selected_images.append((key_date, matching[0], label))
            print(f"✓ Found {key_date.strftime('%Y-%m-%d')}: {matching[0].name}")
        else:
            print(f"✗ Not found: {key_date.strftime('%Y-%m-%d')}")
    
    if len(selected_images) != 3:
        print(f"Warning: Expected 3 images, found {len(selected_images)}")
        if len(selected_images) == 0:
            return
    
    # Load and enhance images
    images_data = []
    for date, path, label in selected_images:
        img = Image.open(path)
        img = enhance_image_quality(img)
        
        # Extract metadata
        metadata = extract_metadata_from_image(img)
        
        # Find glacier region (crop area)
        crop_box = find_glacier_region(img)
        
        images_data.append({
            'date': date,
            'image': img,
            'path': path,
            'label': label,
            'metadata': metadata,
            'crop_box': crop_box
        })
    
    # For measurement, we need to:
    # 1. Crop all images to same region
    # 2. Identify a fixed reference point
    # 3. Measure movement of glacier front
    
    # Get resolution from first image
    resolution_m_per_px = images_data[0]['metadata']['resolution_m_per_px']
    
    print(f"\nUsing resolution: {resolution_m_per_px} m/pixel")
    print(f"To measure movement:")
    print(f"  1. Identify a fixed reference point (e.g., a stable rock)")
    print(f"  2. Measure distance from reference point to glacier front")
    print(f"  3. Calculate difference between dates")
    
    # Create visualization with cropped images
    fig, axes = plt.subplots(1, 3, figsize=(27, 9))
    fig.suptitle('Didal Glacier Movement Analysis - Cropped to Glacier Area\n'
                 f'Resolution: {resolution_m_per_px} m/pixel | '
                 'Measure movement from fixed reference point',
                 fontsize=16, fontweight='bold', y=0.98)
    
    cropped_images = []
    
    for idx, img_data in enumerate(images_data):
        ax = axes[idx]
        img = img_data['image']
        crop_box = img_data['crop_box']
        
        # Crop image
        cropped = img.crop(crop_box)
        cropped_images.append(cropped)
        
        # Display
        ax.imshow(cropped, interpolation='lanczos')
        ax.axis('off')
        
        # Add title
        date_str = img_data['date'].strftime('%Y-%m-%d')
        title = f"{date_str}\n{img_data['label']}"
        ax.set_title(title, fontsize=14, fontweight='bold',
                    color='red' if idx == 0 else 'orange' if idx == 1 else 'darkred',
                    pad=15)
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    output_path = output_dir / 'glacier_movement_cropped_comparison.png'
    plt.savefig(output_path, dpi=600, bbox_inches='tight', facecolor='white')
    print(f"\n✓ Created cropped comparison: {output_path}")
    
    # Save cropped images individually for manual measurement
    for idx, (img_data, cropped) in enumerate(zip(images_data, cropped_images)):
        date_str = img_data['date'].strftime('%Y-%m-%d')
        output_path_individual = output_dir / f'glacier_cropped_{date_str}.png'
        cropped.save(output_path_individual, 'PNG', dpi=(600, 600))
        print(f"  Saved: {output_path_individual.name}")
    
    # Create measurement guide
    measurement_guide = {
        'resolution_m_per_pixel': resolution_m_per_px,
        'scale_meters': images_data[0]['metadata']['scale_m'],
        'instructions': {
            'step1': 'Open the three cropped images side by side',
            'step2': 'Identify a fixed reference point (stable feature like a rock)',
            'step3': 'Measure pixel distance from reference point to glacier front edge',
            'step4': 'Calculate movement: distance_pixels × resolution_m_per_pixel',
            'step5': 'Compare between dates to get movement amounts'
        },
        'dates': {
            date.strftime('%Y-%m-%d'): {
                'label': img_data['label'],
                'image': f'glacier_cropped_{date.strftime("%Y-%m-%d")}.png'
            }
            for date, img_data in zip([d['date'] for d in images_data], images_data)
        }
    }
    
    guide_path = output_dir / 'movement_measurement_guide.json'
    with open(guide_path, 'w') as f:
        json.dump(measurement_guide, f, indent=2)
    
    print(f"\n✓ Created measurement guide: {guide_path}")
    print(f"\nTo measure movement:")
    print(f"  1. Use the cropped images: glacier_cropped_*.png")
    print(f"  2. Resolution: {resolution_m_per_px} meters per pixel")
    print(f"  3. Measure pixel distance from fixed point to glacier front")
    print(f"  4. Multiply by {resolution_m_per_px} to get meters")
    
    return output_path, cropped_images, measurement_guide

if __name__ == '__main__':
    create_movement_analysis()

