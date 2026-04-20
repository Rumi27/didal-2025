#!/usr/bin/env python3
"""
Create publication-quality figure for Q1 journal from three key dates
Enhances and upscales individual date images, then creates a 3-panel figure
"""

import os
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib.patches as mpatches

# Configuration
VIS_DIR = "planet_images/visualizations"
RESOLUTION_M_PER_PIXEL = 5.88
TARGET_DPI = 600  # High quality for publication
TARGET_WIDTH_SINGLE = 2000  # Pixels for single-column figure
TARGET_WIDTH_FULL = 4000  # Pixels for full-width figure

def enhance_image_for_publication(img, upscale_factor=2.0):
    """
    Enhance image quality for publication
    - Sharpening
    - Contrast enhancement
    - Brightness optimization
    - Upscaling with Lanczos
    """
    # Convert to RGB if needed
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Step 1: Sharpening (1.4x - stronger than before)
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.4)
    
    # Step 2: Contrast enhancement (1.2x)
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.2)
    
    # Step 3: Brightness optimization (1.05x)
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.05)
    
    # Step 4: Upscale using Lanczos (high quality)
    if upscale_factor > 1.0:
        original_size = img.size
        new_size = (int(original_size[0] * upscale_factor), 
                   int(original_size[1] * upscale_factor))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    
    return img

def create_publication_quality_3panel():
    """
    Create publication-quality 3-panel figure from individual date images
    """
    print("\n" + "="*70)
    print("CREATING PUBLICATION-QUALITY 3-PANEL FIGURE")
    print("="*70)
    
    # Image paths
    images = {
        '2025-09-12': {
            'path': os.path.join(VIS_DIR, 'glacier_cropped_2025-09-12.png'),
            'label': 'Baseline\n(5 days before\ninitial movement)',
            'color': 'blue'
        },
        '2025-09-17': {
            'path': os.path.join(VIS_DIR, 'glacier_cropped_2025-09-17.png'),
            'label': 'Initial movement\ndetected',
            'color': 'orange'
        },
        '2025-10-25': {
            'path': os.path.join(VIS_DIR, 'glacier_cropped_2025-10-25.png'),
            'label': 'Second movement',
            'color': 'red'
        }
    }
    
    # Check if images exist
    missing = []
    loaded_images = {}
    
    for date, info in images.items():
        if os.path.exists(info['path']):
            print(f"\n✅ Loading: {date}")
            img = Image.open(info['path'])
            print(f"   Original size: {img.size}")
            
            # Calculate upscale factor to reach target width
            current_width = img.size[0]
            upscale_factor = max(1.0, TARGET_WIDTH_SINGLE / current_width)
            
            if upscale_factor > 1.0:
                print(f"   Upscaling by {upscale_factor:.2f}x to {int(current_width * upscale_factor)} pixels width")
            
            # Enhance and upscale
            enhanced = enhance_image_for_publication(img, upscale_factor=upscale_factor)
            print(f"   Enhanced size: {enhanced.size}")
            
            loaded_images[date] = {
                'image': enhanced,
                'label': info['label'],
                'color': info['color']
            }
        else:
            missing.append(date)
            print(f"\n❌ Missing: {info['path']}")
    
    if missing:
        print(f"\n⚠️ Missing images for: {', '.join(missing)}")
        print("Cannot create complete figure.")
        return None
    
    # Create figure
    print("\n📊 Creating 3-panel figure...")
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 6), dpi=300)
    fig.suptitle('Didal Glacier Movement - Three Key Dates', 
                 fontsize=16, fontweight='bold', y=0.98)
    
    dates = ['2025-09-12', '2025-09-17', '2025-10-25']
    
    for idx, date in enumerate(dates):
        ax = axes[idx]
        info = loaded_images[date]
        
        # Display image
        ax.imshow(info['image'])
        ax.axis('off')
        
        # Add date label
        ax.text(0.02, 0.98, date, 
                transform=ax.transAxes,
                fontsize=12, fontweight='bold',
                color='white',
                bbox=dict(boxstyle='round', facecolor='black', alpha=0.7),
                verticalalignment='top')
        
        # Add movement label
        ax.text(0.5, 0.02, info['label'],
                transform=ax.transAxes,
                fontsize=11, fontweight='bold',
                color=info['color'],
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.9),
                horizontalalignment='center',
                verticalalignment='bottom')
        
        # Add resolution note
        ax.text(0.98, 0.02, f'Resolution: {RESOLUTION_M_PER_PIXEL} m/pixel',
                transform=ax.transAxes,
                fontsize=9,
                color='gray',
                horizontalalignment='right',
                verticalalignment='bottom')
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    # Save high-quality version
    output_path = os.path.join(VIS_DIR, 'glacier_movement_publication_quality.png')
    print(f"\n💾 Saving publication-quality figure to: {output_path}")
    fig.savefig(output_path, dpi=TARGET_DPI, bbox_inches='tight', 
                facecolor='white', format='png')
    print(f"   Saved at {TARGET_DPI} DPI")
    print(f"   File size: {os.path.getsize(output_path) / (1024*1024):.2f} MB")
    
    # Also save a version for LaTeX (lower DPI but still high quality)
    output_path_tex = os.path.join(VIS_DIR, 'glacier_movement_for_latex.png')
    fig.savefig(output_path_tex, dpi=300, bbox_inches='tight', 
                facecolor='white', format='png')
    print(f"   Also saved LaTeX version (300 DPI) to: {output_path_tex}")
    
    plt.close()
    
    return output_path

def create_enhanced_individual_images():
    """
    Create enhanced versions of individual date images
    """
    print("\n" + "="*70)
    print("CREATING ENHANCED INDIVIDUAL IMAGES")
    print("="*70)
    
    images = {
        '2025-09-12': os.path.join(VIS_DIR, 'glacier_cropped_2025-09-12.png'),
        '2025-09-17': os.path.join(VIS_DIR, 'glacier_cropped_2025-09-17.png'),
        '2025-10-25': os.path.join(VIS_DIR, 'glacier_cropped_2025-10-25.png')
    }
    
    enhanced_paths = {}
    
    for date, path in images.items():
        if os.path.exists(path):
            print(f"\n📸 Processing: {date}")
            img = Image.open(path)
            print(f"   Original: {img.size}")
            
            # Calculate upscale to reach publication quality
            current_width = img.size[0]
            upscale_factor = max(1.0, TARGET_WIDTH_SINGLE / current_width)
            
            # Enhance
            enhanced = enhance_image_for_publication(img, upscale_factor=upscale_factor)
            print(f"   Enhanced: {enhanced.size} (upscaled {upscale_factor:.2f}x)")
            
            # Save
            output_path = os.path.join(VIS_DIR, f'glacier_enhanced_{date}.png')
            enhanced.save(output_path, 'PNG', dpi=(TARGET_DPI, TARGET_DPI))
            enhanced_paths[date] = output_path
            print(f"   ✅ Saved: {output_path}")
            print(f"   File size: {os.path.getsize(output_path) / (1024*1024):.2f} MB")
        else:
            print(f"\n❌ Missing: {path}")
    
    return enhanced_paths

def main():
    """Main function"""
    print("\n" + "="*70)
    print("PUBLICATION QUALITY FIGURE CREATION")
    print("="*70)
    
    # Create output directory
    os.makedirs(VIS_DIR, exist_ok=True)
    
    # Step 1: Create enhanced individual images
    enhanced = create_enhanced_individual_images()
    
    # Step 2: Create 3-panel publication figure
    figure_path = create_publication_quality_3panel()
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print("\n✅ Enhanced individual images created:")
    for date, path in enhanced.items():
        print(f"   {date}: {os.path.basename(path)}")
    
    if figure_path:
        print(f"\n✅ Publication-quality 3-panel figure created:")
        print(f"   {os.path.basename(figure_path)}")
        print(f"\n📋 For Q1 Journal Publication:")
        print(f"   - Resolution: {TARGET_DPI} DPI")
        print(f"   - Format: PNG (lossless)")
        print(f"   - Suitable for: Single-column or full-width figures")
        print(f"   - File size: {os.path.getsize(figure_path) / (1024*1024):.2f} MB")
    
    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)
    print("\n1. Review the publication-quality figure")
    print("2. Use it in your LaTeX document (Figure 1 or 2)")
    print("3. For movement analysis, use the interactive measurement tool")
    print("4. Consider adding measurement overlays if needed")
    
    return figure_path

if __name__ == "__main__":
    main()

