#!/usr/bin/env python3
"""
Create ultra-high-quality 3-image visualization with optional upscaling
Uses advanced image processing to enhance screenshot quality
"""

import os
import re
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import matplotlib.pyplot as plt
import numpy as np

def parse_date_from_filename(filename):
    """Parse date from various filename formats"""
    base_name = filename.replace('.jpg', '').replace('.JPG', '')
    
    month_map = {
        'Sep': '09', 'September': '09',
        'Oct': '10', 'October': '10',
        'Nov': '11', 'November': '11',
        'Dec': '12', 'December': '12',
        'Jan': '01', 'January': '01',
        'Feb': '02', 'February': '02',
        'Mar': '03', 'March': '03',
        'Apr': '04', 'April': '04',
        'May': '05',
        'Jun': '06', 'June': '06',
        'Jul': '07', 'July': '07',
        'Aug': '08', 'August': '08',
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
    
    numbers = re.findall(r'\d+', base_name)
    if len(numbers) >= 3:
        try:
            day = int(numbers[0])
            month = int(numbers[1])
            year = int(numbers[2])
            if 1 <= month <= 12 and 1 <= day <= 31 and 2000 <= year <= 2100:
                return datetime(year, month, day)
        except:
            pass
    
    return None

def has_measurement_line(filename):
    """Check if image has measurement line"""
    base_name = filename.replace('.jpg', '').replace('.JPG', '')
    return base_name[0].isdigit() and '_' in base_name

def enhance_and_upscale(img, upscale_factor=1.5):
    """Enhance image quality and optionally upscale"""
    # Convert to RGB
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Enhance sharpness
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.3)
    
    # Enhance contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.15)
    
    # Slight brightness adjustment
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.05)
    
    # Optional upscaling using LANCZOS resampling (high quality)
    if upscale_factor > 1.0:
        original_size = img.size
        new_size = (int(original_size[0] * upscale_factor), 
                   int(original_size[1] * upscale_factor))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    
    return img

def create_upscaled_3image():
    """Create ultra-high-quality 3-image visualization"""
    screenshot_dir = Path('planet_images/screenshot_planet')
    output_dir = Path('planet_images/visualizations')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not screenshot_dir.exists():
        print(f"Directory not found: {screenshot_dir}")
        return
    
    screenshots = list(screenshot_dir.glob('*.jpg')) + list(screenshot_dir.glob('*.JPG'))
    
    dated_screenshots = []
    for screenshot in screenshots:
        date = parse_date_from_filename(screenshot.name)
        if date:
            has_measurement = has_measurement_line(screenshot.name)
            dated_screenshots.append((date, screenshot, has_measurement))
    
    key_dates = {
        datetime(2025, 9, 12): {
            'label': 'Baseline\n(5 days before\ninitial movement)',
            'description': 'September 12, 2025'
        },
        datetime(2025, 9, 17): {
            'label': 'Initial movement\ndetected',
            'description': 'September 17, 2025'
        },
        datetime(2025, 10, 25): {
            'label': 'Second movement',
            'description': 'October 25, 2025'
        }
    }
    
    selected_images = []
    for key_date, info in key_dates.items():
        date_images = [(d, s, m) for d, s, m in dated_screenshots if d == key_date]
        
        if not date_images:
            print(f"Warning: No image found for {key_date.strftime('%Y-%m-%d')}")
            continue
        
        # Prefer measurement line image
        best_image = None
        for date, screenshot, has_measurement in date_images:
            if has_measurement:
                best_image = (date, screenshot, has_measurement, info)
                break
        
        if not best_image:
            date, screenshot, has_measurement = date_images[0]
            best_image = (date, screenshot, has_measurement, info)
        
        selected_images.append(best_image)
    
    # Create visualization with enhanced images
    fig, axes = plt.subplots(1, 3, figsize=(27, 9))
    fig.suptitle('Didal Glacier - Key Movement Dates (Enhanced Quality)\n'
                 '(Bottom right shows zoom level, resolution, and scale)', 
                 fontsize=19, fontweight='bold', y=0.98)
    
    for idx, (date, screenshot_path, has_measurement, info) in enumerate(selected_images):
        ax = axes[idx]
        
        try:
            img = Image.open(screenshot_path)
            # Enhance and upscale by 1.5x
            img = enhance_and_upscale(img, upscale_factor=1.5)
            
            ax.imshow(img, interpolation='lanczos')
            ax.axis('off')
            
            title_parts = [
                info['description'],
                info['label']
            ]
            if has_measurement:
                title_parts.append("(with measurement line)")
            
            title = "\n".join(title_parts)
            ax.set_title(title, fontsize=15, fontweight='bold', 
                        color='red' if idx == 0 else 'orange' if idx == 1 else 'darkred',
                        pad=18)
            
        except Exception as e:
            ax.text(0.5, 0.5, f"Error loading\n{screenshot_path.name}", 
                   ha='center', va='center', transform=ax.transAxes, fontsize=14)
            ax.axis('off')
            print(f"Error loading {screenshot_path}: {e}")
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    output_path = output_dir / 'screenshot_3key_dates_upscaled.png'
    plt.savefig(output_path, dpi=600, bbox_inches='tight', facecolor='white')
    print(f"\n✓ Created upscaled visualization: {output_path}")
    print(f"  Resolution: 600 DPI")
    print(f"  Upscale factor: 1.5x")
    print(f"  Images: {len(selected_images)}")
    
    return output_path

if __name__ == '__main__':
    create_upscaled_3image()

