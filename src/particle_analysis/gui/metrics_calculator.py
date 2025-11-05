"""Metrics calculation utilities for GUI components.

This module provides centralized metrics calculation logic to avoid
code duplication across GUI components.
"""

import logging
from typing import List, Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Calculate various metrics for optimization results."""
    
    @staticmethod
    def calculate_current_metrics(result, temp_results: Optional[List] = None) -> Dict[str, float]:
        """Calculate metrics for real-time display during optimization.
        
        Args:
            result: OptimizationResult object
            temp_results: List of previous results for context-dependent metrics
            
        Returns:
            Dict with keys: 'hhi', 'knee_dist', 'vi_stability'
        """
        from ..volume.metrics import calculate_hhi
        from ..volume.optimization.utils import detect_knee_point
        
        # Calculate HHI
        hhi = 0.0
        if hasattr(result, 'labels_path') and result.labels_path:
            try:
                labels = np.load(result.labels_path)
                hhi = calculate_hhi(labels)
            except Exception as e:
                logger.warning(f"HHI calculation failed: {e}")
                hhi = result.largest_particle_ratio
        
        # Calculate knee distance if enough data
        knee_dist = 0.0
        if temp_results and len(temp_results) >= 2:
            all_results = temp_results + [result]
            radii = [r.radius for r in all_results]
            counts = [r.particle_count for r in all_results]
            try:
                knee_idx = detect_knee_point(radii, counts)
                knee_dist = abs(result.radius - radii[knee_idx])
            except Exception as e:
                logger.warning(f"Knee distance calculation failed: {e}")
        
        return {
            'hhi': hhi,
            'knee_dist': knee_dist, 
            'vi_stability': 0.5  # Placeholder for real-time display
        }
    
    @staticmethod
    def calculate_final_metrics(result, all_results: List) -> Dict[str, float]:
        """Calculate comprehensive metrics for final display.
        
        Args:
            result: OptimizationResult object
            all_results: List of all results for context-dependent metrics
            
        Returns:
            Dict with keys: 'hhi', 'knee_dist', 'vi_stability'
        """
        from ..volume.metrics import calculate_hhi
        from ..volume.optimization.utils import detect_knee_point
        
        # Calculate HHI
        hhi = 0.0
        if hasattr(result, 'labels_path') and result.labels_path:
            try:
                labels = np.load(result.labels_path)
                hhi = calculate_hhi(labels)
            except Exception as e:
                logger.warning(f"HHI calculation failed: {e}")
                hhi = result.largest_particle_ratio
        
        # Calculate knee distance
        knee_dist = 0.0
        if len(all_results) >= 2:
            radii = [r.radius for r in all_results]
            counts = [r.particle_count for r in all_results]
            try:
                knee_idx = detect_knee_point(radii, counts)
                knee_dist = abs(result.radius - radii[knee_idx])
            except Exception as e:
                logger.warning(f"Knee distance calculation failed: {e}")
        
        # Calculate VI stability
        vi_stability = MetricsCalculator._calculate_vi_for_result(result, all_results)
        
        return {
            'hhi': hhi,
            'knee_dist': knee_dist,
            'vi_stability': vi_stability
        }
    
    @staticmethod
    def _calculate_vi_for_result(result, all_results: List) -> float:
        """Calculate VI (Variation of Information) stability for a single result.
        
        Args:
            result: OptimizationResult object
            all_results: List of all results
            
        Returns:
            VI stability score (lower is more stable)
        """
        from ..volume.metrics import calculate_variation_of_information
        
        # Find current index
        try:
            current_idx = next(i for i, r in enumerate(all_results) if r.radius == result.radius)
        except StopIteration:
            return 0.5
        
        # First result has no previous comparison
        if current_idx == 0:
            return 0.5
        
        # Check if both current and previous have labels
        prev_result = all_results[current_idx - 1]
        if not (hasattr(result, 'labels_path') and result.labels_path and 
                hasattr(prev_result, 'labels_path') and prev_result.labels_path):
            return 0.5
        
        # Calculate VI
        try:
            labels_curr = np.load(result.labels_path)
            labels_prev = np.load(prev_result.labels_path)
            return calculate_variation_of_information(labels_prev, labels_curr)
        except Exception as e:
            logger.warning(f"Failed to calculate VI for r={result.radius}: {e}")
            return 0.5
    
    @staticmethod
    def calculate_metrics_for_plots(results_data: List) -> List[Dict]:
        """Calculate metrics for plot visualization.
        
        Args:
            results_data: List of OptimizationResult objects
            
        Returns:
            List of metric dictionaries with keys: 'hhi', 'knee_dist', 'vi_stability'
        """
        from ..volume.metrics import calculate_hhi, calculate_variation_of_information
        from ..volume.optimization.utils import detect_knee_point
        
        if not results_data:
            return []
        
        # Detect knee point once for all results
        radii = [r.radius for r in results_data]
        particle_counts = [r.particle_count for r in results_data]
        knee_idx = detect_knee_point(radii, particle_counts) if len(radii) >= 3 else 0
        knee_radius = radii[knee_idx]
        
        metrics = []
        
        for i, result in enumerate(results_data):
            # HHI calculation
            hhi = 0.0
            if hasattr(result, 'labels_path') and result.labels_path:
                try:
                    labels = np.load(result.labels_path)
                    hhi = calculate_hhi(labels)
                except Exception as e:
                    logger.warning(f"HHI calculation failed for r={result.radius}: {e}")
                    hhi = result.largest_particle_ratio
            
            # Knee distance (from global knee point)
            knee_dist = abs(result.radius - knee_radius)
            
            # VI calculation
            vi_stability = 0.5
            if i > 0:
                prev_result = results_data[i-1]
                if (hasattr(result, 'labels_path') and result.labels_path and
                    hasattr(prev_result, 'labels_path') and prev_result.labels_path):
                    try:
                        labels_curr = np.load(result.labels_path)
                        labels_prev = np.load(prev_result.labels_path)
                        vi_stability = calculate_variation_of_information(labels_prev, labels_curr)
                    except Exception as e:
                        logger.warning(f"VI calculation failed for r={result.radius}: {e}")
            
            metrics.append({
                'hhi': hhi,
                'knee_dist': knee_dist,
                'vi_stability': vi_stability
            })
        
        return metrics


__all__ = ['MetricsCalculator']

