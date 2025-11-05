"""Optimization algorithms package.

This package provides algorithms for radius selection based on multiple criteria:

- utils: Utility functions (knee point detection, scoring)
- algorithms: Selection algorithms (weighted composite, Pareto+distance)
"""

from .utils import (
    detect_knee_point,
    calculate_coordination_score,
    calculate_composite_score,
)

from .algorithms import (
    determine_best_radius_advanced,
    determine_best_radius_pareto_distance,
)

__all__ = [
    # Utility functions
    "detect_knee_point",
    "calculate_coordination_score", 
    "calculate_composite_score",
    
    # Selection algorithms
    "determine_best_radius_advanced",
    "determine_best_radius_pareto_distance",
]
