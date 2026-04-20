#!/usr/bin/env python3
"""
Assess image quality for Q1 journal publication and analyze glacier movement
from three key dates: 09/12, 09/17, and 10/25
"""

import os
import json
import numpy as np
from PIL import Image, ImageEnhance, ImageStat
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
import cv2
from skimage import filters, measure
from pathlib import Path

# Configuration
VIS_DIR = "planet_images/visualizations"
RESOLUTION_M_PER_PIXEL = 5.88  # From Planet metadata
MIN_DPI_FOR_PUBLICATION = 300  # Minimum DPI for Q1 journal
RECOMMENDED_DPI = 600  # Recommended DPI for high-quality figures

def assess_image_quality(image_path):
    """
    Assess image quality metrics for publication suitability
    Returns dictionary with quality metrics
    """
    print(f"\n{'='*60}")
    print(f"Assessing: {os.path.basename(image_path)}")
    print(f"{'='*60}")
    
    # Load image
    img = Image.open(image_path)
    img_array = np.array(img)
    
    # Basic metrics
    width, height = img.size
    file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
    
    # Calculate effective DPI (if we know the physical size)
    # For screenshots, we estimate based on typical display DPI
    # Planet website typically displays at ~96-150 DPI
    estimated_dpi = 150  # Conservative estimate for web screenshots
    
    # Image statistics
    stats = ImageStat.Stat(img)
    mean_brightness = sum(stats.mean) / len(stats.mean)
    std_brightness = sum(stats.stddev) / len(stats.mean)
    
    # Sharpness assessment using Laplacian variance
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    
    # Cloud cover estimation (brightness threshold)
    # High brightness areas might indicate clouds
    bright_pixels = np.sum(gray > 200) / gray.size * 100
    
    # Contrast assessment
    contrast = std_brightness / mean_brightness if mean_brightness > 0 else 0
    
    # Quality assessment
    quality_score = 0
    quality_issues = []
    quality_strengths = []
    
    # Resolution check
    if width >= 2000 and height >= 2000:
        quality_score += 25
        quality_strengths.append("High resolution")
    elif width >= 1000 and height >= 1000:
        quality_score += 15
        quality_issues.append("Moderate resolution - may need upscaling")
    else:
        quality_issues.append("Low resolution - not suitable for publication")
    
    # Sharpness check
    if laplacian_var > 500:
        quality_score += 25
        quality_strengths.append("High sharpness")
    elif laplacian_var > 200:
        quality_score += 15
        quality_issues.append("Moderate sharpness - may need enhancement")
    else:
        quality_issues.append("Low sharpness - needs enhancement")
    
    # Cloud cover check
    if bright_pixels < 10:
        quality_score += 25
        quality_strengths.append("Low cloud cover")
    elif bright_pixels < 30:
        quality_score += 15
        quality_issues.append(f"Moderate cloud cover ({bright_pixels:.1f}%)")
    else:
        quality_score += 5
        quality_issues.append(f"High cloud cover ({bright_pixels:.1f}%) - may obscure details")
    
    # Contrast check
    if contrast > 0.3:
        quality_score += 25
        quality_strengths.append("Good contrast")
    elif contrast > 0.2:
        quality_score += 15
        quality_issues.append("Moderate contrast - may need enhancement")
    else:
        quality_issues.append("Low contrast - needs enhancement")
    
    # Publication suitability
    if quality_score >= 80:
        publication_status = "✅ EXCELLENT - Suitable for Q1 journal"
    elif quality_score >= 60:
        publication_status = "⚠️ GOOD - May need minor enhancements"
    elif quality_score >= 40:
        publication_status = "⚠️ MODERATE - Needs enhancement"
    else:
        publication_status = "❌ POOR - Not suitable without significant processing"
    
    results = {
        'filename': os.path.basename(image_path),
        'dimensions': (width, height),
        'file_size_mb': file_size_mb,
        'estimated_dpi': estimated_dpi,
        'mean_brightness': mean_brightness,
        'std_brightness': std_brightness,
        'sharpness_laplacian_var': laplacian_var,
        'cloud_cover_percent': bright_pixels,
        'contrast_ratio': contrast,
        'quality_score': quality_score,
        'publication_status': publication_status,
        'issues': quality_issues,
        'strengths': quality_strengths
    }
    
    # Print results
    print(f"Dimensions: {width} x {height} pixels")
    print(f"File size: {file_size_mb:.2f} MB")
    print(f"Estimated DPI: {estimated_dpi} (web screenshot)")
    print(f"Sharpness (Laplacian variance): {laplacian_var:.1f}")
    print(f"Cloud cover estimate: {bright_pixels:.1f}%")
    print(f"Contrast ratio: {contrast:.3f}")
    print(f"\nQuality Score: {quality_score}/100")
    print(f"Publication Status: {publication_status}")
    
    if quality_strengths:
        print(f"\n✅ Strengths:")
        for strength in quality_strengths:
            print(f"   - {strength}")
    
    if quality_issues:
        print(f"\n⚠️ Issues:")
        for issue in quality_issues:
            print(f"   - {issue}")
    
    return results

def analyze_glacier_movement_interactive():
    """
    Interactive tool to analyze glacier tail movement from three dates
    """
    print("\n" + "="*60)
    print("GLACIER MOVEMENT ANALYSIS")
    print("="*60)
    print("\nThis tool will help you measure glacier tail movement")
    print("from three key dates: 09/12, 09/17, and 10/25")
    print("\nResolution: 5.88 m/pixel")
    print("\nYou need to:")
    print("1. Identify a fixed reference point (stable feature)")
    print("2. Mark the glacier tail/front edge for each date")
    print("3. Calculate distances and movements")
    
    # Check for existing measurements
    measurement_file = os.path.join(VIS_DIR, "glacier_movement_measurements.json")
    if os.path.exists(measurement_file):
        print(f"\n⚠️ Found existing measurements in: {measurement_file}")
        with open(measurement_file, 'r') as f:
            existing = json.load(f)
            print("Existing measurements:")
            for date, data in existing.get('measurements', {}).items():
                if data.get('glacier_front'):
                    print(f"  {date}: Glacier front at ({data['glacier_front']['x']}, {data['glacier_front']['y']})")
    
    # Image paths
    images = {
        '2025-09-12': os.path.join(VIS_DIR, 'glacier_cropped_2025-09-12.png'),
        '2025-09-17': os.path.join(VIS_DIR, 'glacier_cropped_2025-09-17.png'),
        '2025-10-25': os.path.join(VIS_DIR, 'glacier_cropped_2025-10-25.png')
    }
    
    # Check if images exist
    missing = [date for date, path in images.items() if not os.path.exists(path)]
    if missing:
        print(f"\n⚠️ Missing images for dates: {', '.join(missing)}")
        print("Using alternative: glacier_movement_cropped.png")
        alt_image = os.path.join(VIS_DIR, 'glacier_movement_cropped.png')
        if os.path.exists(alt_image):
            print(f"✅ Found: {alt_image}")
            print("Note: This is a 3-panel image, you'll need to measure within each panel")
    
    return images

def create_quality_assessment_report():
    """
    Create comprehensive quality assessment report
    """
    print("\n" + "="*70)
    print("IMAGE QUALITY ASSESSMENT FOR Q1 JOURNAL PUBLICATION")
    print("="*70)
    
    # Check main image
    main_image = os.path.join(VIS_DIR, 'glacier_movement_cropped.png')
    
    if not os.path.exists(main_image):
        print(f"\n❌ Main image not found: {main_image}")
        return
    
    # Assess main image
    main_results = assess_image_quality(main_image)
    
    # Check for individual date images
    individual_images = {
        '2025-09-12': os.path.join(VIS_DIR, 'glacier_cropped_2025-09-12.png'),
        '2025-09-17': os.path.join(VIS_DIR, 'glacier_cropped_2025-09-17.png'),
        '2025-10-25': os.path.join(VIS_DIR, 'glacier_cropped_2025-10-25.png')
    }
    
    individual_results = {}
    for date, path in individual_images.items():
        if os.path.exists(path):
            individual_results[date] = assess_image_quality(path)
    
    # Check for high-quality alternatives
    alt_images = [
        'screenshot_3key_dates_high_quality.png',
        'screenshot_3key_dates_upscaled.png',
        'screenshot_3key_dates_large_format.png'
    ]
    
    alt_results = {}
    for alt_name in alt_images:
        alt_path = os.path.join(VIS_DIR, alt_name)
        if os.path.exists(alt_path):
            alt_results[alt_name] = assess_image_quality(alt_path)
    
    # Create summary report
    print("\n" + "="*70)
    print("QUALITY ASSESSMENT SUMMARY")
    print("="*70)
    
    print(f"\n📊 Main Image (glacier_movement_cropped.png):")
    print(f"   Quality Score: {main_results['quality_score']}/100")
    print(f"   Status: {main_results['publication_status']}")
    
    if individual_results:
        print(f"\n📊 Individual Date Images:")
        for date, results in individual_results.items():
            print(f"   {date}:")
            print(f"      Quality Score: {results['quality_score']}/100")
            print(f"      Status: {results['publication_status']}")
            if results['cloud_cover_percent'] > 20:
                print(f"      ⚠️ High cloud cover: {results['cloud_cover_percent']:.1f}%")
    
    if alt_results:
        print(f"\n📊 Alternative High-Quality Images:")
        for name, results in alt_results.items():
            print(f"   {name}:")
            print(f"      Quality Score: {results['quality_score']}/100")
            print(f"      Status: {results['publication_status']}")
    
    # Recommendations
    print("\n" + "="*70)
    print("RECOMMENDATIONS FOR PUBLICATION")
    print("="*70)
    
    best_score = main_results['quality_score']
    best_image = main_image
    best_name = "glacier_movement_cropped.png"
    
    for name, results in {**individual_results, **alt_results}.items():
        if results['quality_score'] > best_score:
            best_score = results['quality_score']
            best_image = None  # We'd need to track the path
            best_name = name
    
    print(f"\n✅ Best Quality Image: {best_name} (Score: {best_score}/100)")
    
    if best_score < 80:
        print("\n⚠️ RECOMMENDATIONS:")
        print("1. Image Enhancement:")
        print("   - Apply sharpening (1.3-1.5x)")
        print("   - Enhance contrast (1.15-1.25x)")
        print("   - Adjust brightness if needed")
        print("   - Use Lanczos resampling for upscaling if needed")
        
        print("\n2. Resolution:")
        if main_results['dimensions'][0] < 2000:
            print("   - Current resolution may be low for publication")
            print("   - Consider upscaling using Lanczos interpolation")
            print("   - Target: ≥2000 pixels width for single-column figure")
            print("   - Target: ≥4000 pixels width for full-width figure")
        
        print("\n3. Cloud Cover:")
        if main_results['cloud_cover_percent'] > 20:
            print(f"   - High cloud cover ({main_results['cloud_cover_percent']:.1f}%)")
            print("   - October 25 image particularly affected")
            print("   - Consider:")
            print("     * Using cloud-free alternative dates if available")
            print("     * Applying cloud masking/removal if possible")
            print("     * Using SAR data (Sentinel-1) for cloud-free analysis")
        
        print("\n4. For Q1 Journal Publication:")
        print("   - Minimum DPI: 300 (for print)")
        print("   - Recommended DPI: 600 (for high-quality)")
        print("   - Format: PNG or TIFF (lossless)")
        print("   - Color space: RGB")
        print("   - Consider creating separate panels for each date")
    
    # Save results
    report = {
        'assessment_date': str(Path(__file__).stat().st_mtime),
        'resolution_m_per_pixel': RESOLUTION_M_PER_PIXEL,
        'main_image': main_results,
        'individual_images': individual_results,
        'alternative_images': alt_results,
        'recommendations': {
            'best_image': best_name,
            'best_score': int(best_score),
            'needs_enhancement': bool(best_score < 80),
            'needs_upscaling': bool(main_results['dimensions'][0] < 2000),
            'cloud_issues': bool(main_results['cloud_cover_percent'] > 20)
        }
    }
    
    report_file = os.path.join(VIS_DIR, 'quality_assessment_report.json')
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Quality assessment report saved to: {report_file}")
    
    return report

def main():
    """Main function"""
    print("\n" + "="*70)
    print("DIDAL GLACIER IMAGE QUALITY ASSESSMENT & MOVEMENT ANALYSIS")
    print("="*70)
    
    # Create visualizations directory if it doesn't exist
    os.makedirs(VIS_DIR, exist_ok=True)
    
    # Step 1: Quality assessment
    print("\n" + "="*70)
    print("STEP 1: IMAGE QUALITY ASSESSMENT")
    print("="*70)
    report = create_quality_assessment_report()
    
    # Step 2: Movement analysis setup
    print("\n" + "="*70)
    print("STEP 2: GLACIER MOVEMENT ANALYSIS SETUP")
    print("="*70)
    images = analyze_glacier_movement_interactive()
    
    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)
    print("\n1. Review quality assessment above")
    print("2. If quality is insufficient, run image enhancement script")
    print("3. Use interactive measurement tool to mark glacier positions")
    print("4. Calculate movements using the measurement data")
    print("\nFor interactive measurement, run:")
    print("   python interactive_measure_sequential.py")
    
    return report

if __name__ == "__main__":
    main()

