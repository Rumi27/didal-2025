#!/usr/bin/env python3
"""
Create visualization with movement measurements overlaid
Allows manual input of measurement coordinates or automatic detection
"""

import os
import re
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Arrow, FancyBboxPatch, Rectangle, ConnectionPatch
import json
import math

def parse_date_from_filename(filename):
    """Parse date from filename - only letter format"""
    base_name = filename.replace('.jpg', '').replace('.JPG', '')
    
    month_map = {
        'Sep': '09', 'October': '10',
        'Oct': '10', 'November': '11',
        'Nov': '11', 'December': '12',
        'Dec': '12',
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

def enhance_image_quality_max(img):
    """Maximum quality enhancement"""
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.6)
    
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.25)
    
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.1)
    
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(1.1)
    
    return img

def calculate_distance_pixels(point1, point2):
    """Calculate pixel distance between two points"""
    return math.sqrt((point2[0] - point1[0])**2 + (point2[1] - point1[1])**2)

def pixels_to_meters(pixels, resolution_m_per_px):
    """Convert pixels to meters"""
    return pixels * resolution_m_per_px

def create_measured_visualization():
    """Create visualization with movement measurements"""
    screenshot_dir = Path('planet_images/screenshot_planet')
    output_dir = Path('planet_images/visualizations')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get letter format images
    all_screenshots = list(screenshot_dir.glob('*.jpg')) + list(screenshot_dir.glob('*.JPG'))
    screenshots = [s for s in all_screenshots if parse_date_from_filename(s.name)]
    
    # Key dates
    key_dates = {
        datetime(2025, 9, 12): {'label': 'Baseline', 'short': 'Sep 12'},
        datetime(2025, 9, 17): {'label': 'First Movement', 'short': 'Sep 17'},
        datetime(2025, 10, 25): {'label': 'Second Movement', 'short': 'Oct 25'}
    }
    
    # Find images
    selected_images = []
    for key_date, info in key_dates.items():
        matching = [s for s in screenshots if parse_date_from_filename(s.name) == key_date]
        if matching:
            selected_images.append((key_date, matching[0], info))
    
    if len(selected_images) != 3:
        print(f"Error: Need 3 images, found {len(selected_images)}")
        return
    
    # Load and enhance images
    images_data = []
    resolution = 5.88  # m/pixel
    
    for date, path, info in selected_images:
        img = Image.open(path)
        img = enhance_image_quality_max(img)
        
        width, height = img.size
        # Crop to center 70%
        crop_ratio = 0.70
        crop_width = int(width * crop_ratio)
        crop_height = int(height * crop_ratio)
        left = (width - crop_width) // 2
        top = (height - crop_height) // 2
        
        cropped = img.crop((left, top, left + crop_width, top + crop_height))
        
        images_data.append({
            'date': date,
            'image': cropped,
            'label': info['label'],
            'short': info['short'],
            'crop_offset': (left, top)  # Store offset for coordinate conversion
        })
    
    # Create visualization with measurement framework
    fig, axes = plt.subplots(1, 3, figsize=(30, 10))
    fig.suptitle('Didal Glacier Movement Analysis - Measurement Framework\n'
                 f'Resolution: {resolution} m/pixel | '
                 'Mark reference point and glacier front to measure movement',
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
        
        # Add measurement guide text
        guide_text = f"Resolution: {resolution} m/px\n"
        guide_text += "1. Mark fixed reference point\n"
        guide_text += "2. Mark glacier front edge\n"
        guide_text += "3. Measure pixel distance\n"
        guide_text += "4. Convert: pixels × {resolution} m"
        
        # Add text box with instructions
        textbox = FancyBboxPatch((0.02, 0.02), 0.25, 0.15,
                                 transform=ax.transAxes,
                                 boxstyle="round,pad=0.01",
                                 facecolor='white', alpha=0.8,
                                 edgecolor='black', linewidth=1.5)
        ax.add_patch(textbox)
        ax.text(0.145, 0.095, guide_text, transform=ax.transAxes,
               fontsize=9, ha='center', va='center',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    output_path = output_dir / 'glacier_movement_measurement_framework.png'
    plt.savefig(output_path, dpi=600, bbox_inches='tight', facecolor='white')
    print(f"\n✓ Created measurement framework: {output_path}")
    
    # Create measurement template JSON
    measurement_template = {
        'resolution_m_per_pixel': resolution,
        'instructions': {
            'step1': 'Open the cropped images in an image viewer',
            'step2': 'Identify a fixed reference point (stable feature)',
            'step3': 'Mark the glacier front edge for each date',
            'step4': 'Measure pixel distance from reference to glacier front',
            'step5': 'Calculate: distance_pixels × 5.88 = distance_meters'
        },
        'measurements': {
            '2025-09-12': {
                'reference_point': {'x': None, 'y': None, 'note': 'Fixed point coordinates'},
                'glacier_front': {'x': None, 'y': None, 'note': 'Glacier front edge'},
                'distance_pixels': None,
                'distance_meters': None
            },
            '2025-09-17': {
                'reference_point': {'x': None, 'y': None, 'note': 'Same fixed point'},
                'glacier_front': {'x': None, 'y': None, 'note': 'Glacier front edge'},
                'distance_pixels': None,
                'distance_meters': None
            },
            '2025-10-25': {
                'reference_point': {'x': None, 'y': None, 'note': 'Same fixed point'},
                'glacier_front': {'x': None, 'y': None, 'note': 'Glacier front edge'},
                'distance_pixels': None,
                'distance_meters': None
            }
        },
        'calculations': {
            'first_movement_pixels': None,
            'first_movement_meters': None,
            'second_movement_pixels': None,
            'second_movement_meters': None,
            'total_movement_pixels': None,
            'total_movement_meters': None
        }
    }
    
    template_path = output_dir / 'measurement_template.json'
    with open(template_path, 'w') as f:
        json.dump(measurement_template, f, indent=2)
    
    print(f"✓ Created measurement template: {template_path}")
    print(f"\nTo perform measurements:")
    print(f"  1. Open the cropped images: glacier_cropped_*.png")
    print(f"  2. Use an image viewer with pixel coordinates (e.g., GIMP, ImageJ, or online tools)")
    print(f"  3. Mark reference point and glacier front for each date")
    print(f"  4. Record coordinates in: {template_path.name}")
    print(f"  5. Calculate distances using: pixels × {resolution} m/pixel")
    
    return output_path, measurement_template

if __name__ == '__main__':
    create_measured_visualization()

