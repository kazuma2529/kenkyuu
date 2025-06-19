"""Particle Analysis Core Package

This package contains the core functionality for 3D particle analysis:
- Image processing and mask cleaning
- 3D volume operations
- Particle splitting and labeling
- Contact analysis
"""

from .processing import clean_mask, process_masks
from .volume_ops import stack_masks, split_particles, label_volume
from .contact_analysis import count_contacts, save_contact_csv, analyze_contacts
from .evaluation import compute_dice, compute_iou, evaluate_masks
from .config import DEFAULT_CONFIG, PipelineConfig
from .utils.common import setup_logging, Timer, ensure_directory

__all__ = [
    "clean_mask",
    "process_masks",
    "stack_masks", 
    "split_particles",
    "label_volume",
    "count_contacts",
    "save_contact_csv",
    "analyze_contacts",
    "compute_dice",
    "compute_iou",
    "evaluate_masks",
    "DEFAULT_CONFIG",
    "PipelineConfig",
    "setup_logging",
    "Timer",
    "ensure_directory",
    "view_volume",
    "NapariUnavailable"
] 