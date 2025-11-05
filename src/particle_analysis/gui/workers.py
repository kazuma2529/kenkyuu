"""Background worker threads for GUI operations.

This module contains QThread-based workers that handle computationally
intensive tasks without blocking the GUI main thread.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
from qtpy.QtCore import QThread
from qtpy.QtCore import Signal as pyqtSignal

logger = logging.getLogger(__name__)


class OptimizationWorker(QThread):
    """Worker thread for radius optimization to prevent GUI freezing."""
    
    # Signals for GUI updates
    progress_updated = pyqtSignal(object)  # OptimizationResult (for table updates)
    optimization_complete = pyqtSignal(object, object, object)  # (OptimizationSummary, contact_histogram_data, volume_histogram_data)
    error_occurred = pyqtSignal(str)  # Error message
    
    # NEW: Additional signals for detailed progress tracking
    progress_text_updated = pyqtSignal(str)  # Status text (e.g., "r=3の解析中...")
    progress_percentage_updated = pyqtSignal(int)  # Progress bar value (0-100)
    stage_changed = pyqtSignal(str)  # Processing stage (e.g., "watershed", "contacts", "optimization")
    
    def __init__(self, vol_path: str, output_dir: str, radii: List[int], connectivity: int = 6):
        super().__init__()
        self.vol_path = vol_path
        self.output_dir = output_dir
        self.radii = radii
        self.connectivity = connectivity
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
                    
                    # Emit detailed progress text
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
                # Final stage: Selecting best radius
                self.stage_changed.emit("finalization")
                self.progress_text_updated.emit("最適rを選定中...")
                self.progress_percentage_updated.emit(95)
                
                # NEW: Save results to CSV and best labels (M6)
                logger.info("Saving results to CSV and best labels...")
                try:
                    self._save_results(summary)
                    logger.info("Results saved successfully")
                except Exception as e:
                    logger.error(f"Failed to save results: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Calculate histogram data for final visualization
                logger.info("Calculating histogram data for visualization...")
                contact_histogram, volume_histogram = self._calculate_histogram_data(summary)
                
                # Emit completion with histogram data
                logger.info("Emitting optimization_complete signal with histogram data...")
                self.optimization_complete.emit(summary, contact_histogram, volume_histogram)
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
    
    def _save_results(self, summary):
        """Save optimization results to CSV and best labels to file.
        
        This implements M6 from APP_IMPLEMENTATION_PLAN.md:
        - Save detailed CSV with all radii results
        - Save best labels for 3D visualization
        
        Args:
            summary: OptimizationSummary with all results
        """
        output_dir = Path(self.output_dir)
        
        # 1. Create results DataFrame
        results_data = []
        for result in summary.results:
            results_data.append({
                'radius': result.radius,
                'particle_count': result.particle_count,
                'mean_contacts': result.mean_contacts,
                'largest_particle_ratio': result.largest_particle_ratio,
                'processing_time_sec': result.processing_time,
                'total_volume': result.total_volume,
                'largest_particle_volume': result.largest_particle_volume,
            })
        
        df = pd.DataFrame(results_data)
        
        # Add summary info
        df.attrs['best_radius'] = summary.best_radius
        df.attrs['optimization_method'] = summary.optimization_method
        df.attrs['total_processing_time'] = summary.total_processing_time
        
        # Save to CSV
        csv_path = output_dir / "optimization_results.csv"
        df.to_csv(csv_path, index=False)
        logger.info(f"✅ Saved results CSV: {csv_path}")
        
        # Also save summary info to separate file
        summary_path = output_dir / "optimization_summary.txt"
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(f"Optimization Summary\n")
            f.write(f"{'=' * 50}\n\n")
            f.write(f"Best Radius: {summary.best_radius}\n")
            f.write(f"Optimization Method: {summary.optimization_method}\n")
            f.write(f"Total Processing Time: {summary.total_processing_time:.2f}s\n")
            f.write(f"Radii Tested: {len(summary.results)}\n\n")
            
            best_result = summary.get_result_by_radius(summary.best_radius)
            if best_result:
                f.write(f"Best Result (r={summary.best_radius}):\n")
                f.write(f"  Particles: {best_result.particle_count}\n")
                f.write(f"  Mean Contacts: {best_result.mean_contacts:.2f}\n")
                f.write(f"  Largest Particle Ratio: {best_result.largest_particle_ratio:.3f}\n")
        
        logger.info(f"✅ Saved summary text: {summary_path}")
        
        # 2. Save best labels for 3D visualization
        best_labels_src = output_dir / f"labels_r{summary.best_radius}.npy"
        best_labels_dst = output_dir / "best_labels.npy"
        
        if best_labels_src.exists():
            # Copy or create symlink
            labels = np.load(best_labels_src)
            np.save(best_labels_dst, labels)
            logger.info(f"✅ Saved best labels: {best_labels_dst}")
            logger.info(f"   Best radius: r={summary.best_radius}")
            logger.info(f"   Labels shape: {labels.shape}")
            logger.info(f"   Unique particles: {labels.max()}")
        else:
            logger.warning(f"⚠️ Best labels file not found: {best_labels_src}")
    
    def _calculate_histogram_data(self, summary):
        """Calculate histogram data for final visualization.
        
        This calculates:
        1. Contact number distribution histogram
        2. Particle volume distribution histogram
        
        Args:
            summary: OptimizationSummary with best_radius
            
        Returns:
            tuple: (contact_histogram_data, volume_histogram_data)
                   Each is a dict with 'values' and 'bins' keys, or None if calculation fails
        """
        output_dir = Path(self.output_dir)
        best_labels_path = output_dir / "best_labels.npy"
        
        contact_histogram_data = None
        volume_histogram_data = None
        
        try:
            if not best_labels_path.exists():
                logger.warning(f"Best labels not found at {best_labels_path}, cannot calculate histogram data")
                return contact_histogram_data, volume_histogram_data
            
            # Load best labels
            labels = np.load(best_labels_path)
            logger.info(f"Loaded best labels for histogram calculation: {labels.shape}, {labels.max()} particles")
            
            # 1. Calculate particle volumes
            # Skip background (label 0)
            unique_labels = np.unique(labels)
            unique_labels = unique_labels[unique_labels > 0]  # Remove background
            
            if len(unique_labels) == 0:
                logger.warning("No particles found in best labels")
                return contact_histogram_data, volume_histogram_data
            
            volumes = []
            for label_id in unique_labels:
                volume = np.count_nonzero(labels == label_id)
                volumes.append(volume)
            
            volume_histogram_data = {
                'values': volumes,
                'min': int(np.min(volumes)),
                'max': int(np.max(volumes)),
                'mean': float(np.mean(volumes)),
                'median': float(np.median(volumes))
            }
            logger.info(f"✅ Calculated volume histogram: {len(volumes)} particles, "
                       f"range [{volume_histogram_data['min']}, {volume_histogram_data['max']}]")
            
            # 2. Calculate contact numbers directly from best_labels
            # Import count_contacts function
            from ..contact import count_contacts
            
            best_radius = summary.best_radius
            logger.info(f"Calculating contact distribution for best radius r={best_radius}...")
            
            try:
                # Calculate contacts directly from labels using the same connectivity as optimization
                contact_counts_dict = count_contacts(labels, connectivity=self.connectivity)
                
                # Extract just the counts (values) for histogram
                contact_counts = list(contact_counts_dict.values())
                
                if len(contact_counts) > 0:
                    contact_histogram_data = {
                        'values': contact_counts,
                        'min': int(np.min(contact_counts)),
                        'max': int(np.max(contact_counts)),
                        'mean': float(np.mean(contact_counts)),
                        'median': float(np.median(contact_counts))
                    }
                    logger.info(f"✅ Calculated contact histogram: {len(contact_counts)} particles, "
                               f"range [{contact_histogram_data['min']}, {contact_histogram_data['max']}], "
                               f"mean={contact_histogram_data['mean']:.2f}")
                else:
                    logger.warning("No contact data calculated")
            except Exception as e:
                logger.error(f"Failed to calculate contacts: {e}")
                import traceback
                traceback.print_exc()
        
        except Exception as e:
            logger.error(f"Failed to calculate histogram data: {e}")
            import traceback
            traceback.print_exc()
        
        return contact_histogram_data, volume_histogram_data

__all__ = ["OptimizationWorker"] 