#!/usr/bin/env python3
"""
Create high-quality 3-image time series visualization
Focuses on the 3 main dates with maximum quality and clarity
"""

import os
import re
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageEnhance, ImageFilter
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
    
    # Check for month name format
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
    
    # Handle numeric formats
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
    """Check if image has measurement line (numeric date format)"""
    base_name = filename.replace('.jpg', '').replace('.JPG', '')
    return base_name[0].isdigit() and '_' in base_name

def enhance_image_quality(img):
    """Enhance image quality using various techniques"""
    # Convert to RGB if needed
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Enhance sharpness
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.2)
    
    # Enhance contrast slightly
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.1)
    
    # Enhance brightness if needed
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.05)
    
    return img

def create_high_quality_3image():
    """Create high-quality 3-image visualization for main dates"""
    screenshot_dir = Path('planet_images/screenshot_planet')
    output_dir = Path('planet_images/visualizations')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not screenshot_dir.exists():
        print(f"Directory not found: {screenshot_dir}")
        return
    
    # Get all screenshots
    screenshots = list(screenshot_dir.glob('*.jpg')) + list(screenshot_dir.glob('*.JPG'))
    
    # Parse dates and organize
    dated_screenshots = []
    for screenshot in screenshots:
        date = parse_date_from_filename(screenshot.name)
        if date:
            has_measurement = has_measurement_line(screenshot.name)
            dated_screenshots.append((date, screenshot, has_measurement))
    
    # Key dates
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
    
    # Select best image for each key date (prefer measurement line images)
    selected_images = []
    
    for key_date, info in key_dates.items():
        # Find all images for this date
        date_images = [(d, s, m) for d, s, m in dated_screenshots if d == key_date]
        
        if not date_images:
            print(f"Warning: No image found for {key_date.strftime('%Y-%m-%d')}")
            continue
        
        # Prefer image with measurement line
        best_image = None
        for date, screenshot, has_measurement in date_images:
            if has_measurement:
                best_image = (date, screenshot, has_measurement, info)
                break
        
        # If no measurement line image, use any available
        if not best_image:
            date, screenshot, has_measurement = date_images[0]
            best_image = (date, screenshot, has_measurement, info)
        
        selected_images.append(best_image)
        print(f"✓ Selected for {key_date.strftime('%Y-%m-%d')}: {best_image[1].name} "
              f"(measurement line: {'Yes' if best_image[2] else 'No'})")
    
    if len(selected_images) != 3:
        print(f"Warning: Expected 3 images, found {len(selected_images)}")
    
    # Create high-quality visualization
    fig, axes = plt.subplots(1, 3, figsize=(24, 8))
    fig.suptitle('Didal Glacier - Key Movement Dates\n'
                 '(Bottom right shows zoom level, resolution, and scale)', 
                 fontsize=18, fontweight='bold', y=0.98)
    
    for idx, (date, screenshot_path, has_measurement, info) in enumerate(selected_images):
        ax = axes[idx]
        
        try:
            # Load and enhance image
            img = Image.open(screenshot_path)
            img = enhance_image_quality(img)
            
            # Display with high quality
            ax.imshow(img, interpolation='lanczos')  # High-quality interpolation
            ax.axis('off')
            
            # Add title with date and label
            title_parts = [
                info['description'],
                info['label']
            ]
            if has_measurement:
                title_parts.append("(with measurement line)")
            
            title = "\n".join(title_parts)
            ax.set_title(title, fontsize=14, fontweight='bold', 
                        color='red' if idx == 0 else 'orange' if idx == 1 else 'darkred',
                        pad=15)
            
        except Exception as e:
            ax.text(0.5, 0.5, f"Error loading\n{screenshot_path.name}\n{str(e)}", 
                   ha='center', va='center', transform=ax.transAxes,
                   fontsize=12, wrap=True)
            ax.axis('off')
            print(f"Error loading {screenshot_path}: {e}")
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    # Save at very high resolution
    output_path = output_dir / 'screenshot_3key_dates_high_quality.png'
    plt.savefig(output_path, dpi=600, bbox_inches='tight', facecolor='white')
    print(f"\n✓ Created high-quality visualization: {output_path}")
    print(f"  Resolution: 600 DPI")
    print(f"  Images: {len(selected_images)}")
    
    # Also create a version with even larger individual images
    fig2, axes2 = plt.subplots(1, 3, figsize=(30, 10))
    fig2.suptitle('Didal Glacier - Key Movement Dates (Large Format)\n'
                 '(Bottom right shows zoom level, resolution, and scale)', 
                 fontsize=20, fontweight='bold', y=0.98)
    
    for idx, (date, screenshot_path, has_measurement, info) in enumerate(selected_images):
        ax = axes2[idx]
        
        try:
            img = Image.open(screenshot_path)
            img = enhance_image_quality(img)
            
            ax.imshow(img, interpolation='lanczos')
            ax.axis('off')
            
            title_parts = [
                info['description'],
                info['label']
            ]
            if has_measurement:
                title_parts.append("(with measurement line)")
            
            title = "\n".join(title_parts)
            ax.set_title(title, fontsize=16, fontweight='bold', 
                        color='red' if idx == 0 else 'orange' if idx == 1 else 'darkred',
                        pad=20)
            
        except Exception as e:
            ax.text(0.5, 0.5, f"Error loading\n{screenshot_path.name}", 
                   ha='center', va='center', transform=ax.transAxes, fontsize=14)
            ax.axis('off')
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    output_path2 = output_dir / 'screenshot_3key_dates_large_format.png'
    plt.savefig(output_path2, dpi=600, bbox_inches='tight', facecolor='white')
    print(f"✓ Created large-format visualization: {output_path2}")
    print(f"  Resolution: 600 DPI")
    print(f"  Figure size: 30x10 inches")
    
    return output_path, output_path2

if __name__ == '__main__':
    create_high_quality_3image()

