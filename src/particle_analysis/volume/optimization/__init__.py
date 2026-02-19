"""Optimization algorithms package.

This package provides:
- utils: Knee point detection
- algorithms: Pareto+distance fallback selection

The primary selection logic is in optimizer.select_radius_by_constraints().
"""

from .utils import detect_knee_point
from .algorithms import determine_best_radius_pareto_distance

__all__ = [
    "detect_knee_point",
    "determine_best_radius_pareto_distance",
]
