"""Optimization utility functions.

This module provides utility functions for optimization algorithms:
- Knee point detection
- Scoring functions  
- Helper calculations
"""

import logging
from typing import List

import numpy as np

from ..data_structures import OptimizationResult

logger = logging.getLogger(__name__)


def detect_knee_point(x_values: List[float], y_values: List[float]) -> int:
    """Detect the knee point in a curve using the kneedle algorithm.

    Args:
        x_values: X coordinates (radius values)
        y_values: Y coordinates (particle counts)

    Returns:
        Index of the knee point
    """
    if len(x_values) < 3:
        return 0

    # Normalize values to [0, 1]
    x_norm = np.array(x_values)
    y_norm = np.array(y_values)

    x_norm = (x_norm - x_norm.min()) / (x_norm.max() - x_norm.min())
    y_norm = (y_norm - y_norm.min()) / (y_norm.max() - y_norm.min())

    # Calculate differences from diagonal line
    differences = []
    for i in range(len(x_norm)):
        diff = y_norm[i] - x_norm[i]
        differences.append(diff)

    # Find maximum difference (knee point)
    knee_idx = np.argmax(differences)

    return knee_idx


def calculate_coordination_score(mean_contacts: float, target_range: tuple = (6.0, 8.0)) -> float:
    """Calculate score based on physical coordination number validity.

    Args:
        mean_contacts: Calculated mean coordination number
        target_range: Physically reasonable range for coordination number

    Returns:
        Score from 0 to 1 (1 = perfect, 0 = very bad)
    """
    min_coord, max_coord = target_range

    if min_coord <= mean_contacts <= max_coord:
        # Perfect score if within target range
        return 1.0
    elif mean_contacts < min_coord:
        # Penalty for too low coordination
        if mean_contacts <= 0:
            return 0.0
        # Linear penalty
        return max(0.0, mean_contacts / min_coord)
    else:
        # Penalty for too high coordination
        if mean_contacts >= max_coord * 2:
            return 0.0
        # Linear penalty
        return max(0.0, 1.0 - (mean_contacts - max_coord) / max_coord)


def calculate_composite_score(result: OptimizationResult, all_results: List[OptimizationResult]) -> float:
    """Calculate composite optimization score based on multiple criteria.

    Args:
        result: Current result to score
        all_results: All results for comparison

    Returns:
        Composite score from 0 to 1
    """
    if not all_results:
        return 0.0

    scores = {}
    weights = {
        'particle_count': 0.3,
        'largest_particle_ratio': 0.4,
        'coordination_number': 0.3
    }

    # 1. Particle count score (prefer stable, not too high)
    particle_counts = [r.particle_count for r in all_results]
    if len(particle_counts) >= 3:
        radii = [r.radius for r in all_results]
        knee_idx = detect_knee_point(radii, particle_counts)
        # Higher score for points near or after knee
        distance_from_knee = abs(all_results.index(result) - knee_idx)
        scores['particle_count'] = max(0.0, 1.0 - distance_from_knee * 0.2)
    else:
        scores['particle_count'] = 0.5

    # 2. Largest particle ratio score (lower is better)
    if result.largest_particle_ratio <= 0.05:  # <= 5%
        scores['largest_particle_ratio'] = 1.0
    elif result.largest_particle_ratio <= 0.10:  # <= 10%
        scores['largest_particle_ratio'] = 0.8
    elif result.largest_particle_ratio <= 0.20:  # <= 20%
        scores['largest_particle_ratio'] = 0.5
    elif result.largest_particle_ratio <= 0.50:  # <= 50%
        scores['largest_particle_ratio'] = 0.2
    else:  # > 50%
        scores['largest_particle_ratio'] = 0.0

    # 3. Coordination number score
    scores['coordination_number'] = calculate_coordination_score(result.mean_contacts)

    # Calculate weighted composite score
    composite_score = sum(scores[key] * weights[key] for key in scores)

    logger.debug(f"Radius {result.radius} scores: {scores}, composite: {composite_score:.3f}")

    return composite_score


__all__ = [
    "detect_knee_point",
    "calculate_coordination_score",
    "calculate_composite_score"  # Legacy support
]
