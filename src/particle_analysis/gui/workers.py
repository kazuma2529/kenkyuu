"""Background worker threads for GUI operations.

This module contains QThread-based workers that handle computationally
intensive tasks without blocking the GUI main thread.
"""

import logging
from typing import List

from qtpy.QtCore import QThread
from qtpy.QtCore import Signal as pyqtSignal

logger = logging.getLogger(__name__)


class OptimizationWorker(QThread):
    """Worker thread for radius optimization to prevent GUI freezing."""
    
    # Signals
    progress_updated = pyqtSignal(object)  # OptimizationResult
    optimization_complete = pyqtSignal(object)  # OptimizationSummary
    error_occurred = pyqtSignal(str)  # Error message
    
    def __init__(self, vol_path: str, output_dir: str, radii: List[int], connectivity: int = 6):
        super().__init__()
        self.vol_path = vol_path
        self.output_dir = output_dir
        self.radii = radii
        self.connectivity = connectivity
        self.is_cancelled = False
    
    def run(self):
        """Execute the optimization in a separate thread."""
        try:
            from ..volume import optimize_radius_advanced
            
            def progress_callback(result):
                if not self.is_cancelled:
                    self.progress_updated.emit(result)
            
            # Run optimization
            logger.info(f"Starting optimization for radii: {self.radii}")
            logger.info(f"Using connectivity: {self.connectivity}")
            summary = optimize_radius_advanced(
                vol_path=self.vol_path,
                output_dir=self.output_dir,
                radii=self.radii,
                connectivity=self.connectivity,
                progress_callback=progress_callback,
                complete_analysis=True,
                early_stopping=False
            )
            
            logger.info(f"Optimization completed. Summary: {summary}")
            logger.info(f"Best radius: {summary.best_radius if summary else 'None'}")
            logger.info(f"Is cancelled: {self.is_cancelled}")
            
            if not self.is_cancelled:
                logger.info("Emitting optimization_complete signal...")
                self.optimization_complete.emit(summary)
                logger.info("Signal emitted successfully")
                
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            self.error_occurred.emit(str(e))
    
    def cancel(self):
        """Cancel the optimization."""
        self.is_cancelled = True
        self.terminate()

__all__ = ["OptimizationWorker"] 