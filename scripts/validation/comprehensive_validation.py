#!/usr/bin/env python3
"""
Comprehensive validation comparison script.

This script compares all validation datasets (same-track, optical, stable-ground)
and quantifies biases to determine if velocity estimates need revision.

Requirements:
    - Same-track velocity results
    - Optical feature tracking results (if available)
    - Stable-ground validation results
    - Cross-track velocity time series
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# Configuration
OUTPUT_DIR = Path("processed_data/velocity_validation")
CROSS_TRACK_FILE = Path("satellite_data/sentinel1/processed/velocity_timeseries_python.csv")

# Bias threshold (10% as per reviewer requirement)
BIAS_THRESHOLD_PCT = 10

def load_validation_results():
    """Load all available validation results."""
    results = {
        'same_track': None,
        'optical': None,
        'stable_ground': None,
        'cross_track': None
    }
    
    # Load cross-track velocities
    if CROSS_TRACK_FILE.exists():
        results['cross_track'] = pd.read_csv(CROSS_TRACK_FILE)
        results['cross_track']['date'] = pd.to_datetime(results['cross_track']['date'])
        print("✓ Loaded cross-track velocities")
    else:
        print("⚠️  Cross-track velocities not found")
    
    # Load same-track validation
    same_track_file = OUTPUT_DIR / "same_track_cross_track_comparison.csv"
    if same_track_file.exists():
        results['same_track'] = pd.read_csv(same_track_file)
        print("✓ Loaded same-track validation")
    else:
        print("⚠️  Same-track validation not found (run process_same_track_validation.py)")
    
    # Load optical validation
    optical_file = OUTPUT_DIR / "optical" / "optical_sar_comparison.csv"
    if optical_file.exists():
        results['optical'] = pd.read_csv(optical_file)
        print("✓ Loaded optical validation")
    else:
        print("⚠️  Optical validation not found (run optical_feature_tracking.py)")
    
    # Load stable-ground validation
    stable_ground_file = OUTPUT_DIR / "stable_ground_validation_results.json"
    if stable_ground_file.exists():
        with open(stable_ground_file, 'r') as f:
            results['stable_ground'] = json.load(f)
        print("✓ Loaded stable-ground validation")
    else:
        print("⚠️  Stable-ground validation not found (run stable_ground_validation.py)")
    
    return results

def analyze_biases(validation_results):
    """Analyze biases from all validation sources."""
    print("\n" + "=" * 80)
    print("BIAS ANALYSIS")
    print("=" * 80)
    
    bias_summary = {
        'same_track': None,
        'optical': None,
        'stable_ground': None,
        'overall': None
    }
    
    all_biases = []
    
    # Same-track bias analysis
    if validation_results['same_track'] is not None:
        st_df = validation_results['same_track']
        mean_bias = st_df['bias_m_per_day'].mean()
        mean_rel_bias = st_df['relative_bias_percent'].mean()
        max_rel_bias = st_df['relative_bias_percent'].abs().max()
        
        bias_summary['same_track'] = {
            'mean_bias_m_per_day': float(mean_bias),
            'mean_relative_bias_percent': float(mean_rel_bias),
            'max_relative_bias_percent': float(max_rel_bias),
            'n_comparisons': len(st_df),
            'exceeds_threshold': max_rel_bias > BIAS_THRESHOLD_PCT
        }
        
        all_biases.extend(st_df['relative_bias_percent'].abs().tolist())
        
        print(f"\nSame-Track Validation:")
        print(f"  Mean bias: {mean_bias:.2f} m/day ({mean_rel_bias:.1f}%)")
        print(f"  Max relative bias: {max_rel_bias:.1f}%")
        print(f"  Exceeds {BIAS_THRESHOLD_PCT}% threshold: {'YES ⚠️' if max_rel_bias > BIAS_THRESHOLD_PCT else 'NO ✓'}")
    
    # Optical bias analysis
    if validation_results['optical'] is not None:
        opt_df = validation_results['optical']
        if 'bias_m_per_day' in opt_df.columns:
            mean_bias = opt_df['bias_m_per_day'].mean()
            mean_rel_bias = opt_df['relative_bias_percent'].mean() if 'relative_bias_percent' in opt_df.columns else np.nan
            max_rel_bias = opt_df['relative_bias_percent'].abs().max() if 'relative_bias_percent' in opt_df.columns else np.nan
            
            bias_summary['optical'] = {
                'mean_bias_m_per_day': float(mean_bias),
                'mean_relative_bias_percent': float(mean_rel_bias) if not np.isnan(mean_rel_bias) else None,
                'max_relative_bias_percent': float(max_rel_bias) if not np.isnan(max_rel_bias) else None,
                'n_comparisons': len(opt_df),
                'exceeds_threshold': max_rel_bias > BIAS_THRESHOLD_PCT if not np.isnan(max_rel_bias) else None
            }
            
            if not np.isnan(mean_rel_bias):
                all_biases.extend(opt_df['relative_bias_percent'].abs().tolist())
            
            print(f"\nOptical Feature Tracking Validation:")
            print(f"  Mean bias: {mean_bias:.2f} m/day")
            if not np.isnan(max_rel_bias):
                print(f"  Max relative bias: {max_rel_bias:.1f}%")
                print(f"  Exceeds {BIAS_THRESHOLD_PCT}% threshold: {'YES ⚠️' if max_rel_bias > BIAS_THRESHOLD_PCT else 'NO ✓'}")
    
    # Stable-ground bias analysis
    if validation_results['stable_ground'] is not None:
        sg_data = validation_results['stable_ground']
        if 'mean_offset_m_per_day' in sg_data:
            mean_bias = sg_data['mean_offset_m_per_day']
            
            bias_summary['stable_ground'] = {
                'mean_bias_m_per_day': float(mean_bias),
                'n_pairs': sg_data.get('n_pairs', 0),
                'note': 'Stable-ground offsets indicate systematic geolocation bias'
            }
            
            print(f"\nStable-Ground Validation:")
            print(f"  Mean offset: {mean_bias:.2f} m/day")
            print(f"  Note: This indicates systematic geolocation bias")
    
    # Overall assessment
    if all_biases:
        max_overall_bias = max(all_biases)
        mean_overall_bias = np.mean(all_biases)
        
        bias_summary['overall'] = {
            'max_relative_bias_percent': float(max_overall_bias),
            'mean_relative_bias_percent': float(mean_overall_bias),
            'exceeds_threshold': max_overall_bias > BIAS_THRESHOLD_PCT,
            'recommendation': 'REVISE_VELOCITY_ESTIMATES' if max_overall_bias > BIAS_THRESHOLD_PCT else 'ACCEPTABLE'
        }
        
        print(f"\n{'='*80}")
        print("OVERALL ASSESSMENT")
        print("=" * 80)
        print(f"  Maximum relative bias: {max_overall_bias:.1f}%")
        print(f"  Mean relative bias: {mean_overall_bias:.1f}%")
        print(f"  Exceeds {BIAS_THRESHOLD_PCT}% threshold: {'YES ⚠️' if max_overall_bias > BIAS_THRESHOLD_PCT else 'NO ✓'}")
        
        if max_overall_bias > BIAS_THRESHOLD_PCT:
            print(f"\n  ⚠️  RECOMMENDATION: REVISE VELOCITY ESTIMATES")
            print(f"     All velocity-dependent conclusions must be revised.")
            print(f"     Apply bias correction and update uncertainty budget.")
        else:
            print(f"\n  ✓ RECOMMENDATION: ACCEPTABLE")
            print(f"     Velocities are within acceptable range.")
            print(f"     Document biases in paper but no revision needed.")
    
    return bias_summary

def create_comprehensive_validation_report(bias_summary, validation_results):
    """Create comprehensive validation report."""
    report = {
        'validation_date': pd.Timestamp.now().strftime('%Y-%m-%d'),
        'bias_threshold_percent': BIAS_THRESHOLD_PCT,
        'validation_sources': {
            'same_track': bias_summary['same_track'] is not None,
            'optical': bias_summary['optical'] is not None,
            'stable_ground': bias_summary['stable_ground'] is not None
        },
        'bias_analysis': bias_summary,
        'recommendations': []
    }
    
    # Add recommendations
    if bias_summary['overall']:
        if bias_summary['overall']['exceeds_threshold']:
            report['recommendations'].append({
                'priority': 'HIGH',
                'action': 'Revise velocity estimates and all dependent analyses',
                'reason': f"Bias exceeds {BIAS_THRESHOLD_PCT}% threshold"
            })
            report['recommendations'].append({
                'priority': 'HIGH',
                'action': 'Apply bias correction to velocity time series',
                'reason': 'Systematic bias detected'
            })
            report['recommendations'].append({
                'priority': 'HIGH',
                'action': 'Update uncertainty budget to include validation-derived uncertainties',
                'reason': 'Validation reveals additional uncertainty sources'
            })
        else:
            report['recommendations'].append({
                'priority': 'MEDIUM',
                'action': 'Document biases in paper',
                'reason': 'Biases are within acceptable range but should be reported'
            })
    
    # Save report
    report_file = OUTPUT_DIR / "comprehensive_validation_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n✅ Comprehensive validation report saved: {report_file}")
    
    return report

def main():
    """Main execution."""
    print("=" * 80)
    print("COMPREHENSIVE VALIDATION ANALYSIS")
    print("=" * 80)
    
    # Load validation results
    validation_results = load_validation_results()
    
    # Analyze biases
    bias_summary = analyze_biases(validation_results)
    
    # Create comprehensive report
    report = create_comprehensive_validation_report(bias_summary, validation_results)
    
    print("\n" + "=" * 80)
    print("✅ VALIDATION ANALYSIS COMPLETE")
    print("=" * 80)
    
    # Print summary
    print("\nSUMMARY:")
    print(f"  Validation sources: {sum([v is not None for v in validation_results.values()])}/4")
    if bias_summary['overall']:
        print(f"  Maximum bias: {bias_summary['overall']['max_relative_bias_percent']:.1f}%")
        print(f"  Recommendation: {bias_summary['overall']['recommendation']}")

if __name__ == "__main__":
    main()
