"""Particle Analysis Core Package

This package contains the core functionality for 3D particle analysis:
- Image processing and mask cleaning
- 3D volume operations
- Particle splitting and labeling
- Contact analysis
- Visualization
"""

__version__ = "2.0.0"
__author__ = "3D Particle Analysis Team"

from .processing import clean_mask, process_masks
from .volume import (
    stack_masks, split_particles, label_volume,
    optimize_radius, optimize_radius_advanced,
    OptimizationResult, OptimizationSummary,
    calculate_particle_volumes, calculate_largest_particle_ratio,
    determine_best_radius_advanced
)
from .contact import count_contacts, save_contact_csv, analyze_contacts

from .config import DEFAULT_CONFIG, PipelineConfig
from .utils import setup_logging, Timer, ensure_directory, get_image_files, natural_sort_key
from .visualize import view_volume, NapariUnavailable

# GUI (optional, requires additional dependencies)
try:
    from .gui import launch_gui, ParticleAnalysisGUI, GUIUnavailable, GUI_AVAILABLE
except ImportError:
    GUI_AVAILABLE = False
    def launch_gui():
        raise ImportError("GUI dependencies not available. Install with: pip install napari[all] qtpy")
    def ParticleAnalysisGUI():
        raise ImportError("GUI dependencies not available. Install with: pip install napari[all] qtpy")
    class GUIUnavailable(RuntimeError):
        pass

__all__ = [
    # Processing
    "clean_mask",
    "process_masks",
    
    # Volume operations
    "stack_masks", 
    "split_particles",
    "label_volume",
    
    # Advanced optimization
    "optimize_radius",
    "optimize_radius_advanced",
    "OptimizationResult",
    "OptimizationSummary",
    "calculate_particle_volumes",
    "calculate_largest_particle_ratio",
    "determine_best_radius_advanced",
    
    # Contact analysis
    "count_contacts",
    "save_contact_csv",
    "analyze_contacts",
    
    # Configuration
    "DEFAULT_CONFIG",
    "PipelineConfig",
    
    # Utilities
    "setup_logging",
    "Timer",
    "ensure_directory",
    "get_image_files",
    "natural_sort_key",
    
    # Visualization
    "view_volume",
    "NapariUnavailable",
    
    # GUI
    "launch_gui",
    "ParticleAnalysisGUI",
    "GUIUnavailable"
] 