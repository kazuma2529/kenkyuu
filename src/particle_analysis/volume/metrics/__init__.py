"""Particle metrics calculation package.

This package provides functions for calculating various metrics
from labeled 3D particle volumes, organized by category:

- basic: Volume and size metrics
- dominance: Distribution inequality metrics (HHI, Gini, top-k shares)  
- stability: Label consistency metrics (VI, Dice)
"""

from .basic import (
    calculate_particle_volumes,
    calculate_largest_particle_ratio,
)

from .dominance import (
    calculate_topk_share,
    calculate_hhi,
    calculate_gini,
)

from .stability import (
    calculate_variation_of_information,
    dice_coefficient_2d,
    calculate_mean_slice_dice,
)

__all__ = [
    # Basic metrics
    "calculate_particle_volumes",
    "calculate_largest_particle_ratio",
    
    # Dominance metrics
    "calculate_topk_share",
    "calculate_hhi", 
    "calculate_gini",
    
    # Stability metrics
    "calculate_variation_of_information",
    "dice_coefficient_2d",
    "calculate_mean_slice_dice",
]
