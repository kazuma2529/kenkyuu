"""Common utilities for GUI components.

This module provides shared functionality for GUI components including
error handling, logging setup, and common UI helpers.
"""

import logging
from typing import Optional, Callable
from functools import wraps

from qtpy.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)


def setup_gui_logging(level: int = logging.INFO) -> None:
    """Setup logging configuration for GUI components.
    
    This should be called once at application startup.
    Avoids duplicate logging configuration.
    
    Args:
        level: Logging level (default: INFO)
    """
    # Only configure if not already configured
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=level,
            format='%(levelname)s:%(name)s: %(message)s'
        )


def handle_napari_error(parent_widget, error: Exception, context: str = "") -> None:
    """Handle Napari-related errors with user-friendly messages.
    
    Args:
        parent_widget: Parent widget for message box
        error: Exception that occurred
        context: Additional context string for the error message
    """
    error_msg = f"Failed to open 3D viewer"
    if context:
        error_msg += f" ({context})"
    error_msg += f":\n\n{str(error)}"
    
    QMessageBox.critical(parent_widget, "Napari Error", error_msg)
    logger.error(f"Napari error: {error}")
    import traceback
    traceback.print_exc()


def check_napari_available(parent_widget) -> bool:
    """Check if Napari is available, show warning if not.
    
    Args:
        parent_widget: Parent widget for message box
        
    Returns:
        True if Napari is available, False otherwise
    """
    try:
        import napari  # noqa: F401
        return True
    except ImportError:
        QMessageBox.warning(
            parent_widget,
            "Napari Not Available",
            "Napari is not installed.\n\n"
            "Install it with:\n"
            "pip install napari[all]"
        )
        return False


def safe_execute(func: Callable) -> Callable:
    """Decorator to safely execute a function and handle errors.
    
    Shows error message box if exception occurs.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred:\n\n{str(e)}"
            )
    return wrapper


__all__ = [
    "setup_gui_logging",
    "handle_napari_error",
    "check_napari_available",
    "safe_execute",
]

