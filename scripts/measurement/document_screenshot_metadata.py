#!/usr/bin/env python3
"""
Document metadata from Planet webpage screenshots
Extracts zoom level, resolution, and scale information visible in images
"""

import os
import re
from pathlib import Path
from datetime import datetime
from PIL import Image
import json

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

def document_screenshots():
    """Document all screenshots with their metadata"""
    screenshot_dir = Path('planet_images/screenshot_planet')
    output_file = Path('planet_images/screenshot_metadata.json')
    
    if not screenshot_dir.exists():
        print(f"Directory not found: {screenshot_dir}")
        return
    
    screenshots = list(screenshot_dir.glob('*.jpg')) + list(screenshot_dir.glob('*.JPG'))
    
    metadata_list = []
    
    for screenshot in screenshots:
        date = parse_date_from_filename(screenshot.name)
        has_measurement = has_measurement_line(screenshot.name)
        
        try:
            img = Image.open(screenshot)
            width, height = img.size
            
            info = {
                'filename': screenshot.name,
                'date': date.strftime('%Y-%m-%d') if date else None,
                'has_measurement_line': has_measurement,
                'image_size': {
                    'width': width,
                    'height': height
                },
                'metadata_note': 'Zoom level, resolution (m/px), and scale (m) visible in bottom right corner',
                'file_path': str(screenshot)
            }
            
            metadata_list.append(info)
            
        except Exception as e:
            print(f"Error processing {screenshot.name}: {e}")
    
    # Sort by date
    metadata_list.sort(key=lambda x: x['date'] if x['date'] else '')
    
    # Save to JSON
    output_data = {
        'total_screenshots': len(metadata_list),
        'screenshots_with_measurements': sum(1 for m in metadata_list if m['has_measurement_line']),
        'date_range': {
            'start': min(m['date'] for m in metadata_list if m['date']),
            'end': max(m['date'] for m in metadata_list if m['date'])
        },
        'screenshots': metadata_list
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n✓ Documented {len(metadata_list)} screenshots")
    print(f"✓ Saved to: {output_file}")
    print(f"\nSummary:")
    print(f"  Total screenshots: {len(metadata_list)}")
    print(f"  With measurement lines: {sum(1 for m in metadata_list if m['has_measurement_line'])}")
    print(f"  Date range: {output_data['date_range']['start']} to {output_data['date_range']['end']}")
    
    # Print key dates
    key_dates = ['2025-09-12', '2025-09-17', '2025-10-25']
    print(f"\nKey dates coverage:")
    for key_date in key_dates:
        matches = [m for m in metadata_list if m['date'] == key_date]
        if matches:
            has_meas = any(m['has_measurement_line'] for m in matches)
            print(f"  ✓ {key_date}: {len(matches)} image(s), measurement line: {'Yes' if has_meas else 'No'}")
        else:
            print(f"  ✗ {key_date}: Not found")
    
    return output_file

if __name__ == '__main__':
    document_screenshots()

