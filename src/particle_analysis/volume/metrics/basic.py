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
    unique_labels = np.unique(labels)
    unique_labels = unique_labels[unique_labels > 0]  # Remove background

    volumes = {}
    for label_id in unique_labels:
        volume = np.sum(labels == label_id)
        volumes[label_id] = volume

    return volumes


def calculate_largest_particle_ratio(labels: np.ndarray) -> tuple[float, int, int]:
    """Calculate the ratio of the largest particle to total volume.

    Args:
        labels: 3D labeled volume
        
    Returns:
        tuple: (ratio, largest_particle_volume, total_volume)
    """
    if labels.max() == 0:
        return 0.0, 0, 0

    volumes = calculate_particle_volumes(labels)

    if not volumes:
        return 0.0, 0, 0

    largest_volume = max(volumes.values())
    total_volume = sum(volumes.values())

    ratio = largest_volume / total_volume if total_volume > 0 else 0.0

    return ratio, largest_volume, total_volume


__all__ = ["calculate_particle_volumes", "calculate_largest_particle_ratio"]
