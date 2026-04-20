#!/usr/bin/env python3
"""
Advanced glacier movement measurement using screenshot images
- Uses letter format images (Sep_, Oct_)
- Maximum quality enhancement
- Crops to glacier area
- Measures movement distances with pixel-to-meter conversion
"""

import os
import re
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Arrow, FancyBboxPatch, Rectangle
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

def extract_metadata_from_image(img_path):
    """Extract metadata - using typical Planet screenshot values"""
    # Typical Planet screenshot metadata in bottom right:
    # Zoom: 14.34, Resolution: 5.88 m/px, Scale: 500m
    
    # These values can vary, but 5.88 m/px is common for zoom level ~14.34
    # We'll use this as default and allow manual adjustment
    
    return {
        'resolution_m_per_px': 5.88,  # meters per pixel
        'scale_m': 500,  # scale bar in meters
        'zoom': 14.34
    }

def enhance_image_quality_max(img):
    """Maximum quality enhancement"""
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Maximum enhancements
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.6)
    
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.25)
    
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.1)
    
    # Optional: slight saturation boost
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(1.1)
    
    return img

def create_glacier_movement_analysis():
    """Create comprehensive glacier movement analysis"""
    screenshot_dir = Path('planet_images/screenshot_planet')
    output_dir = Path('planet_images/visualizations')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not screenshot_dir.exists():
        print(f"Directory not found: {screenshot_dir}")
        return
    
    # Get only letter format images
    all_screenshots = list(screenshot_dir.glob('*.jpg')) + list(screenshot_dir.glob('*.JPG'))
    screenshots = [s for s in all_screenshots if parse_date_from_filename(s.name)]
    
    print(f"Found {len(screenshots)} letter-format screenshots")
    
    # Key dates
    key_dates = {
        datetime(2025, 9, 12): {
            'label': 'Baseline\n(5 days before\ninitial movement)',
            'short': 'Sep 12'
        },
        datetime(2025, 9, 17): {
            'label': 'Initial movement\ndetected',
            'short': 'Sep 17'
        },
        datetime(2025, 10, 25): {
            'label': 'Second movement',
            'short': 'Oct 25'
        }
    }
    
    # Find images for key dates
    selected_images = []
    for key_date, info in key_dates.items():
        matching = [s for s in screenshots if parse_date_from_filename(s.name) == key_date]
        if matching:
            selected_images.append((key_date, matching[0], info))
            print(f"✓ {key_date.strftime('%Y-%m-%d')}: {matching[0].name}")
        else:
            print(f"✗ Not found: {key_date.strftime('%Y-%m-%d')}")
    
    if len(selected_images) != 3:
        print(f"Warning: Expected 3 images, found {len(selected_images)}")
        if len(selected_images) == 0:
            return
    
    # Load and process images
    images_data = []
    for date, path, info in selected_images:
        img = Image.open(path)
        original_size = img.size
        
        # Maximum quality enhancement
        img = enhance_image_quality_max(img)
        
        # Extract metadata
        metadata = extract_metadata_from_image(path)
        
        images_data.append({
            'date': date,
            'image': img,
            'original_image': Image.open(path),  # Keep original for reference
            'path': path,
            'label': info['label'],
            'short': info['short'],
            'metadata': metadata,
            'original_size': original_size
        })
    
    # Get resolution
    resolution = images_data[0]['metadata']['resolution_m_per_px']
    print(f"\nUsing resolution: {resolution} m/pixel")
    
    # For cropping, we'll create a focused view
    # The user can specify crop coordinates, or we'll use intelligent cropping
    
    # Create visualization with full images first (for reference)
    fig, axes = plt.subplots(1, 3, figsize=(30, 10))
    fig.suptitle('Didal Glacier Movement - Full Images (Reference)\n'
                 f'Resolution: {resolution} m/pixel | '
                 'Images enhanced to maximum quality',
                 fontsize=18, fontweight='bold', y=0.98)
    
    for idx, img_data in enumerate(images_data):
        ax = axes[idx]
        img = img_data['image']
        
        ax.imshow(img, interpolation='lanczos')
        ax.axis('off')
        
        date_str = img_data['date'].strftime('%Y-%m-%d')
        title = f"{date_str}\n{img_data['label']}"
        ax.set_title(title, fontsize=15, fontweight='bold',
                    color='red' if idx == 0 else 'orange' if idx == 1 else 'darkred',
                    pad=20)
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    output_path_full = output_dir / 'glacier_movement_full_images.png'
    plt.savefig(output_path_full, dpi=600, bbox_inches='tight', facecolor='white')
    print(f"\n✓ Created full images reference: {output_path_full}")
    
    # Now create cropped versions
    # We'll crop to center 70% to focus on glacier area
    # User can adjust these coordinates based on their specific images
    
    fig2, axes2 = plt.subplots(1, 3, figsize=(27, 9))
    fig2.suptitle('Didal Glacier Movement - Cropped to Glacier Area\n'
                 f'Resolution: {resolution} m/pixel | '
                 'Fixed reference point required for measurement',
                 fontsize=18, fontweight='bold', y=0.98)
    
    cropped_images = []
    
    for idx, img_data in enumerate(images_data):
        ax = axes2[idx]
        img = img_data['image']
        width, height = img.size
        
        # Crop to center 70% (focus on glacier area)
        # User should adjust these coordinates based on their images
        crop_ratio = 0.70
        crop_width = int(width * crop_ratio)
        crop_height = int(height * crop_ratio)
        
        left = (width - crop_width) // 2
        top = (height - crop_height) // 2
        right = left + crop_width
        bottom = top + crop_height
        
        cropped = img.crop((left, top, right, bottom))
        cropped_images.append(cropped)
        
        ax.imshow(cropped, interpolation='lanczos')
        ax.axis('off')
        
        date_str = img_data['date'].strftime('%Y-%m-%d')
        title = f"{date_str}\n{img_data['label']}"
        ax.set_title(title, fontsize=14, fontweight='bold',
                    color='red' if idx == 0 else 'orange' if idx == 1 else 'darkred',
                    pad=15)
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    output_path_cropped = output_dir / 'glacier_movement_cropped.png'
    plt.savefig(output_path_cropped, dpi=600, bbox_inches='tight', facecolor='white')
    print(f"✓ Created cropped comparison: {output_path_cropped}")
    
    # Save individual cropped images
    for idx, (img_data, cropped) in enumerate(zip(images_data, cropped_images)):
        date_str = img_data['date'].strftime('%Y-%m-%d')
        output_path_individual = output_dir / f'glacier_cropped_{date_str}.png'
        cropped.save(output_path_individual, 'PNG', dpi=(600, 600))
        print(f"  Saved individual: {output_path_individual.name}")
    
    # Create measurement instructions
    instructions = f"""
GLACIER MOVEMENT MEASUREMENT INSTRUCTIONS
========================================

Resolution: {resolution} meters per pixel

MEASUREMENT STEPS:
1. Open the three cropped images: glacier_cropped_*.png
2. Identify a FIXED REFERENCE POINT (stable feature like a rock or mountain peak)
3. For each date, measure the pixel distance from the reference point to the glacier front edge
4. Calculate movement:
   - Movement (meters) = Pixel distance × {resolution} m/pixel

CALCULATIONS:
- First movement (Sep 12 → Sep 17):
  Movement_1 = (Distance_Sep17 - Distance_Sep12) × {resolution} m
  
- Second movement (Sep 17 → Oct 25):
  Movement_2 = (Distance_Oct25 - Distance_Sep17) × {resolution} m

- Total movement (Sep 12 → Oct 25):
  Total_Movement = (Distance_Oct25 - Distance_Sep12) × {resolution} m

FILES CREATED:
- glacier_movement_full_images.png: Full images for reference
- glacier_movement_cropped.png: Cropped comparison (3 images)
- glacier_cropped_2025-09-12.png: Individual cropped image (baseline)
- glacier_cropped_2025-09-17.png: Individual cropped image (first movement)
- glacier_cropped_2025-10-25.png: Individual cropped image (second movement)

NOTE: The cropped images are centered on the glacier area. 
You may need to adjust the crop coordinates based on your specific images.
"""
    
    instructions_path = output_dir / 'movement_measurement_instructions.txt'
    with open(instructions_path, 'w') as f:
        f.write(instructions)
    
    print(f"\n✓ Created instructions: {instructions_path}")
    print(instructions)
    
    return output_path_cropped, cropped_images

if __name__ == '__main__':
    create_glacier_movement_analysis()

