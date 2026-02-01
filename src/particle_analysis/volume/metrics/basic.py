"""Basic particle metrics calculation functions.

This module provides fundamental metrics for particle analysis:
- Volume calculations
- Size distribution metrics
"""

import logging
from typing import Dict

import numpy as np

logger = logging.getLogger(__name__)


def calculate_particle_volumes(labels: np.ndarray) -> Dict[int, int]:
    """Calculate volume (voxel count) for each particle.
    
    Args:
        labels: 3D labeled volume where each particle has unique integer ID
        
    Returns:
        Dict mapping particle_id -> volume_in_voxels
    """
    if labels.size == 0:
        return {}

    counts = np.bincount(labels.ravel())
    if counts.size <= 1:
        return {}

    counts[0] = 0
    nonzero_ids = np.nonzero(counts)[0]
    volumes = {int(label_id): int(counts[label_id]) for label_id in nonzero_ids}
    return volumes


def calculate_largest_particle_ratio(labels: np.ndarray) -> tuple[float, int, int]:
    """Calculate the ratio of the largest particle to total volume.

    Args:
        labels: 3D labeled volume
        
    Returns:
        tuple: (ratio, largest_particle_volume, total_volume)
    """
    if labels.size == 0:
        return 0.0, 0, 0

    counts = np.bincount(labels.ravel())
    if counts.size <= 1:
        return 0.0, 0, 0

    counts[0] = 0
    total_volume = int(counts.sum())
    if total_volume == 0:
        return 0.0, 0, 0

    largest_volume = int(counts.max())
    ratio = largest_volume / total_volume
    return float(ratio), largest_volume, total_volume


__all__ = ["calculate_particle_volumes", "calculate_largest_particle_ratio"]
