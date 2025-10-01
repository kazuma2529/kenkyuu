"""Volume Operations Package

This package handles 3D volume operations including:
- Volume stacking from 2D masks
- Particle splitting and labeling 
- Radius optimization algorithms
- Particle analysis metrics
"""

# Import from modular components
from .data_structures import OptimizationResult, OptimizationSummary
from .core import stack_masks, split_particles, label_volume
from .optimizer import optimize_radius_advanced, optimize_radius

# Import from reorganized metrics package
from .metrics import (
    # Basic metrics
    calculate_particle_volumes,
    calculate_largest_particle_ratio,
    # Dominance metrics  
    calculate_topk_share,
    calculate_hhi,
    calculate_gini,
    # Stability metrics
    calculate_variation_of_information,
    dice_coefficient_2d,
    calculate_mean_slice_dice,
)

# Import from reorganized optimization package
from .optimization import (
    # Utility functions
    detect_knee_point,
    calculate_coordination_score,
    calculate_composite_score,
    # Selection algorithms
    determine_best_radius_advanced,
    determine_best_radius_pareto_distance,
)

__all__ = [
    # Core volume operations
    "stack_masks",
    "split_particles", 
    "label_volume",
    
    # Optimization orchestration
    "optimize_radius",
    "optimize_radius_advanced",
    
    # Data structures
    "OptimizationResult",
    "OptimizationSummary",
    
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
    
    # Optimization utilities
    "detect_knee_point",
    "calculate_coordination_score",
    "calculate_composite_score",
    
    # Selection algorithms
    "determine_best_radius_advanced",
    "determine_best_radius_pareto_distance",
] 