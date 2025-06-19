"""Particle Analysis Core Package

This package contains the core functionality for 3D particle analysis:
- Image processing and mask cleaning
- 3D volume operations
- Particle splitting and labeling
- Contact analysis
- Visualization
"""

from .processing import clean_mask, process_masks
from .volume_ops import stack_masks, split_particles, label_volume
from .contact_analysis import count_contacts, save_contact_csv, analyze_contacts
from .evaluation import compute_dice, compute_iou, evaluate_masks
from .config import DEFAULT_CONFIG, PipelineConfig
from .utils.common import setup_logging, Timer, ensure_directory
from .visualize import view_volume, NapariUnavailable

__all__ = [
    # Processing
    "clean_mask",
    "process_masks",
    
    # Volume operations
    "stack_masks", 
    "split_particles",
    "label_volume",
    
    # Contact analysis
    "count_contacts",
    "save_contact_csv",
    "analyze_contacts",
    
    # Evaluation
    "compute_dice",
    "compute_iou",
    "evaluate_masks",
    
    # Configuration
    "DEFAULT_CONFIG",
    "PipelineConfig",
    
    # Utilities
    "setup_logging",
    "Timer",
    "ensure_directory",
    
    # Visualization
    "view_volume",
    "NapariUnavailable"
] 