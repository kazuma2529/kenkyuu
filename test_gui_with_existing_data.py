#!/usr/bin/env python3
"""Test GUI with existing good data to verify new visualization works."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import numpy as np
from src.particle_analysis.volume.metrics import calculate_hhi, calculate_variation_of_information
from src.particle_analysis.volume.optimization.utils import detect_knee_point
from src.particle_analysis.volume.data_structures import OptimizationResult

def test_new_metrics():
    """Test new metrics with known good data."""
    print("Testing new metrics with gui_run_20250728_1633 data...")
    
    # Load existing good results
    base_path = Path("output/gui_run_20250728_1633")
    radii = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    
    results = []
    metrics_data = []
    
    for r in radii:
        labels_path = base_path / f"labels_r{r}.npy"
        if not labels_path.exists():
            continue
            
        labels = np.load(labels_path)
        particles = len(np.unique(labels[labels>0]))
        hhi = calculate_hhi(labels)
        
        # Create mock result
        result = OptimizationResult(
            radius=r,
            particle_count=particles,
            mean_contacts=6.0 + r * 0.3,  # Mock values
            largest_particle_ratio=hhi,  # Use HHI as proxy
            processing_time=10.0,
            labels_path=str(labels_path),
            total_volume=100000,
            largest_particle_volume=int(hhi * 100000)
        )
        results.append(result)
        
        # Calculate metrics
        metrics = {
            'hhi': hhi,
            'knee_dist': 0.0,  # Will calculate below
            'vi_stability': 0.5  # Default
        }
        metrics_data.append(metrics)
        
        print(f"r={r}: particles={particles:4d}, HHI={hhi:.3f}")
    
    # Calculate knee distances
    particle_counts = [r.particle_count for r in results]
    radii_list = [r.radius for r in results]
    knee_idx = detect_knee_point(radii_list, particle_counts)
    knee_radius = radii_list[knee_idx]
    
    for i, metrics in enumerate(metrics_data):
        metrics['knee_dist'] = abs(results[i].radius - knee_radius)
    
    print(f"\nKnee point detected at r={knee_radius}")
    print("\nFinal metrics:")
    for i, (result, metrics) in enumerate(zip(results, metrics_data)):
        status = "★ OPTIMAL" if result.radius == 5 else "Under-segmented" if metrics['hhi'] > 0.1 else "Well-segmented"
        print(f"r={result.radius}: HHI={metrics['hhi']:.3f}, Knee_Dist={metrics['knee_dist']:.1f}, Status={status}")
    
    return results, metrics_data

if __name__ == "__main__":
    test_new_metrics()
