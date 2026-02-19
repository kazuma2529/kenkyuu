"""Background worker threads for GUI operations.

This module contains QThread-based workers that handle computationally
intensive tasks without blocking the GUI main thread.
"""

import logging
from pathlib import Path
from typing import List

import numpy as np
from qtpy.QtCore import QThread
from qtpy.QtCore import Signal as pyqtSignal

logger = logging.getLogger(__name__)


class OptimizationWorker(QThread):
    """Worker thread for radius optimization to prevent GUI freezing."""
    
    # Signals for GUI updates
    progress_updated = pyqtSignal(object)  # OptimizationResult (for table updates)
    optimization_complete = pyqtSignal(object, object, object, object)  # (OptimizationSummary, contact_histogram_data, volume_histogram_data, scatter_data)
    error_occurred = pyqtSignal(str)  # Error message
    
    # NEW: Additional signals for detailed progress tracking
    progress_text_updated = pyqtSignal(str)  # Status text (e.g., "r=3の解析中...")
    progress_percentage_updated = pyqtSignal(int)  # Progress bar value (0-100)
    stage_changed = pyqtSignal(str)  # Processing stage (e.g., "watershed", "contacts", "optimization")
    
    def __init__(self, volume: np.ndarray, output_dir: str, radii: List[int], connectivity: int = 6,
                 tau_ratio: float = 0.03,
                 contacts_range: tuple[int, int] = (5, 9), smoothing_window: int | None = None):
        super().__init__()
        self.volume = volume
        self.output_dir = output_dir
        self.radii = radii
        self.connectivity = connectivity
        self.tau_ratio = tau_ratio
        self.contacts_range = contacts_range
        self.smoothing_window = smoothing_window
        self.is_cancelled = False
        self.total_steps = len(radii) if radii else 1  # For percentage calculation
    
    def run(self):
        """Execute the optimization in a separate thread."""
        try:
            from ..volume import optimize_radius_advanced
            
            # Enhanced progress callback with detailed GUI updates
            def progress_callback(result):
                if not self.is_cancelled:
                    # Emit the full result object (for internal processing)
                    self.progress_updated.emit(result)
                    
                    # Calculate and emit progress percentage
                    current_index = self.radii.index(result.radius) if result.radius in self.radii else 0
                    # Reserve last 10% for final optimization selection
                    progress_pct = int((current_index + 1) / self.total_steps * 90)
                    self.progress_percentage_updated.emit(progress_pct)
                    
                    # Emit detailed progress text (with guard volume info if available)
                    if hasattr(result, 'interior_particle_count') and result.interior_particle_count > 0:
                        text = (
                            f"r = {result.radius}: {result.particle_count} particles "
                            f"({result.interior_particle_count} interior, {result.excluded_particle_count} excluded), "
                            f"{result.mean_contacts:.1f} avg contacts (interior only)"
                        )
                    else:
                        text = (
                            f"r = {result.radius}: {result.particle_count} particles, "
                            f"{result.mean_contacts:.1f} avg contacts"
                        )
                    self.progress_text_updated.emit(text)
                    
                    logger.info(f"Progress update: {text} ({progress_pct}%)")
            
            # Initial status
            self.stage_changed.emit("initialization")
            self.progress_text_updated.emit("Starting radius optimization...")
            self.progress_percentage_updated.emit(0)
            
            # Run optimization
            logger.info(f"Starting optimization for radii: {self.radii}")
            logger.info(f"Using connectivity: {self.connectivity}")
            
            self.stage_changed.emit("optimization")
            summary = optimize_radius_advanced(
                vol_path=None,
                output_dir=self.output_dir,
                radii=self.radii,
                connectivity=self.connectivity,
                progress_callback=progress_callback,
                complete_analysis=True,
                early_stopping=False,
                tau_ratio=self.tau_ratio,
                contacts_range=self.contacts_range,
                smoothing_window=self.smoothing_window,
                volume=self.volume,
            )
            
            logger.info(f"Optimization completed. Summary: {summary}")
            logger.info(f"Best radius: {summary.best_radius if summary else 'None'}")
            logger.info(f"Is cancelled: {self.is_cancelled}")
            
            if not self.is_cancelled:
                # Final stage: Selecting best radius
                self.stage_changed.emit("finalization")
                self.progress_text_updated.emit("最適rを選定中...")
                self.progress_percentage_updated.emit(95)
                
                # Results are saved within optimizer (optimization_results.csv and labels_r{best}.npy)
                
                # Calculate histogram data for final visualization
                logger.info("Calculating histogram data for visualization...")
                contact_histogram, volume_histogram, scatter_data = self._calculate_histogram_data(summary)
                
                # Emit completion with histogram data and scatter data
                logger.info("Emitting optimization_complete signal with histogram data and scatter data...")
                self.optimization_complete.emit(summary, contact_histogram, volume_histogram, scatter_data)
                logger.info("Signal emitted successfully")
                
                # Final status
                self.progress_text_updated.emit(f"✅ 完了！最適r = {summary.best_radius}")
                self.progress_percentage_updated.emit(100)
                
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            self.error_occurred.emit(str(e))
            self.progress_text_updated.emit(f"❌ エラー: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def cancel(self):
        """Cancel the optimization."""
        self.is_cancelled = True
        self.terminate()
    
    def _calculate_histogram_data(self, summary):
        """Calculate histogram data for visualization and save CSVs.

        Delegates heavy lifting to :mod:`results_export` so that data
        computation and I/O are decoupled from the worker thread logic.

        Returns:
            tuple: (contact_histogram_data, volume_histogram_data, scatter_data)
                   Each is a dict or None if calculation fails.
        """
        from .results_export import (
            analyze_best_labels,
            build_contact_histogram,
            build_volume_histogram,
            build_scatter_data,
            save_analysis_csvs,
        )

        output_dir = Path(self.output_dir)
        labels_path = output_dir / f"labels_r{summary.best_radius}.npy"

        try:
            analysis = analyze_best_labels(labels_path, self.connectivity)
        except (FileNotFoundError, ValueError) as e:
            logger.warning(f"Skipping histogram/CSV: {e}")
            return None, None, None
        except Exception as e:
            logger.error(f"Failed to analyse best labels: {e}")
            import traceback
            traceback.print_exc()
            return None, None, None

        contact_histogram = build_contact_histogram(analysis)
        volume_histogram = build_volume_histogram(analysis)
        scatter_data = build_scatter_data(analysis)

        # Save CSV files for Excel graph generation
        save_analysis_csvs(output_dir, analysis)

        return contact_histogram, volume_histogram, scatter_data

__all__ = ["OptimizationWorker"]