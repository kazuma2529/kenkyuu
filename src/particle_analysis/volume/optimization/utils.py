"""Optimization utility functions.

This module provides utility functions for optimization algorithms:
- Knee point detection (kneedle algorithm)
"""

import logging
from typing import List

import numpy as np

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


__all__ = [
    "detect_knee_point",
]
