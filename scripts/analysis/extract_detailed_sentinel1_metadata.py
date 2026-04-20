#!/usr/bin/env python3
"""
Extract detailed Sentinel-1 metadata from SAFE files including:
- Actual relative orbit numbers (from manifest)
- Incidence angles (from annotation XML)
- Burst coverage details
- Track numbers
"""

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import re
import json
from datetime import datetime

sentinel1_dir = Path('satellite_data/sentinel1')

def extract_relative_orbit_from_manifest(manifest_data):
    """Extract relative orbit number from manifest.safe."""
    # Look for relativeOrbitNumber or similar
    matches = re.findall(r'relativeOrbitNumber[^>]*>(\d+)', manifest_data, re.IGNORECASE)
    if matches:
        return int(matches[0])
    
    # Alternative pattern
    matches = re.findall(r'relative\s*orbit[^>]*>(\d+)', manifest_data, re.IGNORECASE)
    if matches:
        return int(matches[0])
    
    # Look in XML structure
    try:
        root = ET.fromstring(manifest_data.encode())
        for elem in root.iter():
            if 'relativeOrbitNumber' in elem.tag or 'relativeOrbit' in elem.tag:
                if elem.text and elem.text.isdigit():
                    return int(elem.text)
    except:
        pass
    
    return None

def extract_incidence_angles_from_annotation(ann_data):
    """Extract incidence angles from annotation XML."""
    angles = []
    
    # Try regex first
    matches = re.findall(r'<incidenceAngle[^>]*>([0-9.]+)</incidenceAngle>', ann_data)
    if matches:
        angles.extend([float(x) for x in matches])
    
    # Also try XML parsing
    try:
        root = ET.fromstring(ann_data.encode())
        for elem in root.iter():
            if 'incidenceAngle' in elem.tag.lower():
                if elem.text:
                    try:
                        angles.append(float(elem.text))
                    except:
                        pass
    except:
        pass
    
    if angles:
        return {
            'min': min(angles),
            'max': max(angles),
            'mean': sum(angles) / len(angles),
            'all': sorted(set(angles))
        }
    return None

def extract_swath_info_from_annotation(ann_data):
    """Extract swath information from annotation XML."""
    swath = None
    
    # Look for swath in filename or content
    if 'IW1' in ann_data or 'iw1' in ann_data:
        swath = 'IW1'
    elif 'IW2' in ann_data or 'iw2' in ann_data:
        swath = 'IW2'
    elif 'IW3' in ann_data or 'iw3' in ann_data:
        swath = 'IW3'
    
    return swath

def extract_burst_count_from_annotation(ann_data):
    """Extract burst count from annotation XML."""
    # Count burst elements
    burst_count = len(re.findall(r'<burst[^>]*>', ann_data, re.IGNORECASE))
    if burst_count == 0:
        # Try alternative patterns
        burst_count = len(re.findall(r'burstNumber', ann_data, re.IGNORECASE))
    return burst_count if burst_count > 0 else None

def extract_track_from_filename(filename):
    """Extract track number from filename if present."""
    # Filename format may contain track info
    # For now, track = relative orbit for Sentinel-1
    parts = filename.split('_')
    if len(parts) >= 8:
        # The orbit identifier might help
        return parts[7]
    return None

print('=' * 80)
print('EXTRACTING DETAILED SENTINEL-1 METADATA')
print('=' * 80)

zip_files = sorted(sentinel1_dir.glob('*.SAFE.zip'))
detailed_acquisitions = []

for zip_file in zip_files:
    print(f'\nProcessing: {zip_file.name}')
    
    filename = zip_file.name
    parts = filename.split('_')
    
    date1_str = parts[5]  # 20250907T012223
    date1 = datetime.strptime(date1_str, '%Y%m%dT%H%M%S')
    
    acquisition = {
        'filename': filename,
        'acquisition_date': date1.strftime('%Y-%m-%d'),
        'acquisition_time': date1.strftime('%H:%M:%S'),
        'datetime': date1.isoformat(),
        'product_id': parts[7] if len(parts) > 7 else None,
    }
    
    try:
        with zipfile.ZipFile(zip_file, 'r') as z:
            # Extract relative orbit from manifest
            manifest_files = [f for f in z.namelist() if 'manifest.safe' in f.lower()]
            if manifest_files:
                manifest_data = z.read(manifest_files[0]).decode('utf-8', errors='ignore')
                
                relative_orbit = extract_relative_orbit_from_manifest(manifest_data)
                if relative_orbit:
                    acquisition['relative_orbit'] = relative_orbit
                    print(f'  Relative Orbit: {relative_orbit}')
                
                # Orbit direction
                if 'ascending' in manifest_data.lower():
                    acquisition['orbit_direction'] = 'ASCENDING'
                elif 'descending' in manifest_data.lower():
                    acquisition['orbit_direction'] = 'DESCENDING'
            
            # Extract detailed info from annotation files
            ann_files = [f for f in z.namelist() if 'annotation' in f.lower() and '.xml' in f and 'vv' in f.lower()]
            
            if ann_files:
                ann_data = z.read(ann_files[0]).decode('utf-8', errors='ignore')
                
                # Incidence angles
                inc_info = extract_incidence_angles_from_annotation(ann_data)
                if inc_info:
                    acquisition['incidence_angle'] = inc_info
                    print(f'  Incidence Angle: {inc_info["min"]:.2f}° - {inc_info["max"]:.2f}° (mean: {inc_info["mean"]:.2f}°)')
                
                # Swath
                swath = extract_swath_info_from_annotation(ann_data)
                if swath:
                    acquisition['swath'] = swath
                    print(f'  Swath: {swath}')
                
                # Burst count
                burst_count = extract_burst_count_from_annotation(ann_data)
                if burst_count:
                    acquisition['burst_count'] = burst_count
                    print(f'  Burst Count: {burst_count}')
                
    except Exception as e:
        print(f'  Warning: Could not extract metadata: {e}')
    
    detailed_acquisitions.append(acquisition)

# Sort by date
detailed_acquisitions.sort(key=lambda x: x['datetime'])

# Save detailed metadata
output_file = sentinel1_dir / 'processed' / 'sentinel1_detailed_metadata.json'
with open(output_file, 'w') as f:
    json.dump({
        'acquisitions': detailed_acquisitions,
        'summary': {
            'total_acquisitions': len(detailed_acquisitions),
            'usable_pairs': len(detailed_acquisitions) - 1,
            'relative_orbits': sorted(set([a.get('relative_orbit') for a in detailed_acquisitions if 'relative_orbit' in a])),
            'unique_swaths': sorted(set([a.get('swath') for a in detailed_acquisitions if 'swath' in a])),
            'date_range': {
                'start': detailed_acquisitions[0]['acquisition_date'],
                'end': detailed_acquisitions[-1]['acquisition_date']
            }
        }
    }, f, indent=2)

print('\n' + '=' * 80)
print('SUMMARY')
print('=' * 80)
print(f'Total acquisitions: {len(detailed_acquisitions)}')
print(f'Usable pairs: {len(detailed_acquisitions) - 1}')

relative_orbits = [a.get('relative_orbit') for a in detailed_acquisitions if 'relative_orbit' in a]
if relative_orbits:
    print(f'Relative orbits: {sorted(set(relative_orbits))}')

swaths = [a.get('swath') for a in detailed_acquisitions if 'swath' in a]
if swaths:
    print(f'Swaths: {sorted(set(swaths))}')

inc_angles = [a.get('incidence_angle') for a in detailed_acquisitions if 'incidence_angle' in a]
if inc_angles:
    all_mins = [inc['min'] for inc in inc_angles if inc]
    all_maxs = [inc['max'] for inc in inc_angles if inc]
    if all_mins and all_maxs:
        print(f'Incidence angle range: {min(all_mins):.2f}° - {max(all_maxs):.2f}°')

print(f'\n✅ Detailed metadata saved to: {output_file}')

