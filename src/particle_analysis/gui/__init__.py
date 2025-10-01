"""GUI Package for 3D Particle Analysis

This package provides a comprehensive graphical user interface with modular components:
- Main application window
- Worker threads for background processing  
- Results display widgets
- 3D visualization integration
"""

from .main_window import ParticleAnalysisGUI
from .workers import OptimizationWorker
from .widgets import ResultsTable, ResultsPlotter
from .launcher import launch_gui, GUIUnavailable
from .pipeline_handler import PipelineHandler

# Check for GUI dependencies
GUI_AVAILABLE = True
MISSING_DEPS = []

try:
    import napari
    import matplotlib.pyplot as plt
    from qtpy.QtWidgets import QWidget
except ImportError as e:
    GUI_AVAILABLE = False
    MISSING_DEPS.append(str(e))

__all__ = [
    "ParticleAnalysisGUI",
    "OptimizationWorker", 
    "ResultsTable",
    "ResultsPlotter",
    "launch_gui",
    "GUIUnavailable",
    "PipelineHandler",
    "GUI_AVAILABLE"
] 