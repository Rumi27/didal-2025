#!/usr/bin/env python3
"""
Analyze and organize Planet webpage screenshots
"""

import os
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def parse_date_from_filename(filename):
    """Parse date from various filename formats"""
    base_name = filename.replace('.jpg', '').replace('.JPG', '')
    
    # Handle month name formats: Sep_12_2025, Oct_25_2025
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
    
    # Check for month name format (Sep_12_2025, Oct_25_2025)
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
    
    # Handle numeric formats: 08_09_2025, 12_09_2025, 1_10_2025
    numbers = re.findall(r'\d+', base_name)
    if len(numbers) >= 3:
        try:
            # Try DD_MM_YYYY format
            day = int(numbers[0])
            month = int(numbers[1])
            year = int(numbers[2])
            # Validate reasonable date
            if 1 <= month <= 12 and 1 <= day <= 31 and 2000 <= year <= 2100:
                return datetime(year, month, day)
        except:
            pass
    
    return None

def analyze_screenshots():
    """Analyze all screenshots in the folder"""
    screenshot_dir = Path('planet_images/screenshot_planet')
    
    if not screenshot_dir.exists():
        print(f"Directory not found: {screenshot_dir}")
        return
    
    screenshots = list(screenshot_dir.glob('*.jpg')) + list(screenshot_dir.glob('*.JPG'))
    
    print(f"Found {len(screenshots)} screenshots")
    print("=" * 60)
    
    # Organize by date
    dated_screenshots = []
    for screenshot in screenshots:
        date = parse_date_from_filename(screenshot.name)
        if date:
            dated_screenshots.append((date, screenshot))
        else:
            print(f"Could not parse date from: {screenshot.name}")
    
    # Sort by date
    dated_screenshots.sort(key=lambda x: x[0])
    
    print("\nScreenshots organized by date:")
    print("-" * 60)
    for date, screenshot in dated_screenshots:
        print(f"{date.strftime('%Y-%m-%d')}: {screenshot.name}")
    
    # Key dates for glacier movement
    key_dates = {
        '2025-09-12': 'Baseline (5 days before initial movement)',
        '2025-09-17': 'Initial movement detected',
        '2025-10-25': 'Second movement',
        '2025-11-01': 'Continued movement',
        '2025-11-02': 'Continued movement',
        '2025-11-03': 'Earthquake day',
    }
    
    print("\n" + "=" * 60)
    print("Key dates coverage:")
    print("-" * 60)
    for key_date, description in key_dates.items():
        found = any(date.strftime('%Y-%m-%d') == key_date for date, _ in dated_screenshots)
        status = "✓" if found else "✗"
        print(f"{status} {key_date}: {description}")
    
    # Date range
    if dated_screenshots:
        first_date = dated_screenshots[0][0]
        last_date = dated_screenshots[-1][0]
        print(f"\nDate range: {first_date.strftime('%Y-%m-%d')} to {last_date.strftime('%Y-%m-%d')}")
        print(f"Total days covered: {(last_date - first_date).days + 1} days")
        print(f"Number of images: {len(dated_screenshots)}")
    
    return dated_screenshots

if __name__ == '__main__':
    analyze_screenshots()

