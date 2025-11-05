"""GUI launcher and dependency management.

This module handles GUI application startup, dependency checking,
and error handling for the particle analysis interface.
"""

import logging

logger = logging.getLogger(__name__)


class GUIUnavailable(RuntimeError):
    """Raised when GUI functionality is called without required dependencies."""
    pass


def _ensure_gui_available():
    """Check if GUI dependencies are available and raise error if not."""
    missing_deps = []
    
    try:
        import napari
    except ImportError:
        missing_deps.append("napari")
    
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        missing_deps.append("matplotlib")
    
    try:
        from qtpy.QtWidgets import QWidget
    except ImportError:
        missing_deps.append("qtpy")
    
    if missing_deps:
        raise GUIUnavailable(
            f"Missing GUI dependencies: {', '.join(missing_deps)}. "
            f"Install with: pip install napari[all] matplotlib qtpy"
        )


def launch_gui():
    """Launch the particle analysis GUI application."""
    try:
        _ensure_gui_available()
        
        # Create QApplication if it doesn't exist
        from qtpy.QtWidgets import QApplication
        import sys
        from pathlib import Path
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Load and apply dark theme stylesheet
        style_path = Path(__file__).parent / "style.qss"
        if style_path.exists():
            with open(style_path, 'r', encoding='utf-8') as f:
                app.setStyleSheet(f.read())
            logger.info("Dark theme stylesheet loaded successfully")
        else:
            logger.warning(f"Stylesheet not found at {style_path}")
        
        # Import and create main window
        from .main_window import ParticleAnalysisGUI
        window = ParticleAnalysisGUI()
        window.show()
        
        # Run application
        if app is not None:
            app.exec_()
        
    except GUIUnavailable as e:
        logger.error(f"GUI Error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.exception("GUI launch failed")
        return False
    
    return True

__all__ = ["launch_gui", "GUIUnavailable"] 