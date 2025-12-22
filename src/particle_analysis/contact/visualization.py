"""Contact visualization utilities.

This module provides functions for visualizing particle contact counts
in 3D space, including discrete color schemes for contact-based coloring.
"""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


def get_discrete_contact_colormap() -> Tuple[Dict[Tuple[int, int], Tuple[float, float, float, float]], List[Tuple[int, Optional[int], str, Tuple[float, float, float, float]]]]:
    """Get discrete color map for contact counts.
    
    Default color scheme (3 bins; low/medium/high) to keep interpretation simple:
    - 0-4 contacts:   Low (low contacts; potential weak zone)
    - 5-9 contacts:   Mid (typical)
    - 10+ contacts:    High (high contacts; dense/strong)
    
    Returns:
        Tuple of:
        - color_map: Dict mapping (min_contact, max_contact) -> RGBA color
        - color_ranges: List of (min, max, color_name) tuples for legend
    """
    # Define color ranges (RGBA, values 0-1)
    # 研究目的（破断起点などの"ゾーン"把握）では、色は細かすぎると読めなくなるため、
    # デフォルトは3段階に絞る（必要なら将来GUIで閾値を調整できるよう拡張可能）。
    color_ranges = [
        (0, 0, "Background", (0.0, 0.0, 0.0, 0.0)),          # 背景（透明）
        (0, 4, "Low (0-4)", (0.6, 0.9, 0.2, 1.0)),          # 明るい黄緑（低接触）
        (5, 9, "Mid (5-9)", (0.10, 0.70, 0.90, 1.0)),       # 明るめシアン（中接触）
        (10, None, "High (10+)", (1.00, 0.35, 0.15, 1.0)),  # 明るい赤橙（高接触）
    ]
    
    # Create mapping dictionary
    color_map = {}
    for min_contact, max_contact, name, color in color_ranges:
        if max_contact is None:
            # Open-ended range (10+)
            key = (min_contact, 999)  # Use large number for upper bound
        else:
            key = (min_contact, max_contact)
        color_map[key] = color
    
    logger.info(f"Created discrete contact colormap with {len(color_ranges)} ranges")
    
    return color_map, color_ranges


def create_contact_count_map(
    labels: np.ndarray,
    contact_counts: Dict[int, int]
) -> np.ndarray:
    """Create a 3D array mapping each voxel to its particle's contact count.
    
    This function replaces each voxel's particle ID with the contact count
    of that particle, creating a volume where each voxel value represents
    the contact count of its particle.
    
    Args:
        labels: 3D labeled volume (particle IDs)
        contact_counts: Dictionary mapping particle_id -> contact_count
        
    Returns:
        3D array with same shape as labels, where each voxel contains
        the contact count of its particle (0 for background)
    """
    contact_map = np.zeros_like(labels, dtype=np.float32)
    
    for particle_id, contact_count in contact_counts.items():
        mask = (labels == particle_id)
        contact_map[mask] = float(contact_count)
    
    logger.info(
        f"Created contact count map: shape={contact_map.shape}, "
        f"range=[{contact_map.min():.0f}, {contact_map.max():.0f}], "
        f"non-zero voxels={np.count_nonzero(contact_map)}"
    )
    
    return contact_map


__all__ = [
    "get_discrete_contact_colormap",
    "create_contact_count_map",
]

