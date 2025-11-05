"""Dominance metrics for particle distribution analysis.

This module provides metrics to quantify distribution inequality
and dominance in particle volume distributions:
- Top-k share metrics
- Herfindahl-Hirschman Index (HHI)
- Gini coefficient
"""

import logging
from typing import List

import numpy as np

from .basic import calculate_particle_volumes

logger = logging.getLogger(__name__)


def _get_sorted_volumes(labels: np.ndarray) -> List[int]:
    """Return particle volumes sorted descending (exclude background).

    Args:
        labels: 3D labeled volume

    Returns:
        List of particle volumes sorted in descending order.
    """
    volumes_dict = calculate_particle_volumes(labels)
    if not volumes_dict:
        return []
    volumes = sorted(volumes_dict.values(), reverse=True)
    return volumes


def calculate_topk_share(labels: np.ndarray, k: int = 1) -> float:
    """Calculate cumulative share of top-k largest particles.

    Args:
        labels: 3D labeled volume
        k: Number of top particles to include (k>=1)

    Returns:
        float: cumulative share in [0,1]. 0 if no particles.
    """
    if k < 1:
        raise ValueError("k must be >= 1")
    volumes = _get_sorted_volumes(labels)
    if not volumes:
        return 0.0
    k = min(k, len(volumes))
    total = float(sum(volumes))
    return float(sum(volumes[:k])) / total if total > 0 else 0.0


def calculate_hhi(labels: np.ndarray) -> float:
    """Calculate Herfindahl–Hirschman Index over particle volume shares.

    HHI = sum_i (s_i^2), where s_i is volume share of particle i.

    Args:
        labels: 3D labeled volume

    Returns:
        float: HHI in (0,1]. Approaches 1 when a single particle dominates.
    """
    volumes = _get_sorted_volumes(labels)
    if not volumes:
        return 0.0
    total = float(sum(volumes))
    if total == 0.0:
        return 0.0
    shares = [v / total for v in volumes]
    return float(sum(s * s for s in shares))


def calculate_gini(labels: np.ndarray) -> float:
    """Calculate Gini coefficient of particle volume distribution.

    Uses the definition based on Lorenz curve. Returns 0 for equal sizes
    and approaches 1 for extreme inequality.

    Args:
        labels: 3D labeled volume

    Returns:
        float: Gini coefficient in [0,1].
    """
    volumes = _get_sorted_volumes(labels)
    n = len(volumes)
    if n == 0:
        return 0.0
    if n == 1:
        return 0.0
    # Sort ascending for standard formula
    x = np.array(sorted(volumes), dtype=float)
    cumx = np.cumsum(x)
    # Gini = (n+1 - 2 * sum((n+1 - i) * x_i) / sum(x)) / n
    # Equivalent efficient formula using cumulative sums (Brown, 1994)
    total = cumx[-1]
    if total == 0.0:
        return 0.0
    index = np.arange(1, n + 1)
    gini = (n + 1 - 2.0 * np.sum((n + 1 - index) * x) / total) / n
    # Numerical guardrails
    return float(max(0.0, min(1.0, gini)))


__all__ = [
    "calculate_topk_share",
    "calculate_hhi",
    "calculate_gini",
]
