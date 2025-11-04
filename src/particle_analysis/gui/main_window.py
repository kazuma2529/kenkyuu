"""Main window for 3D Particle Analysis GUI.

This module contains the primary application window with all UI components
and interaction logic for the particle analysis pipeline.
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s: %(message)s'
)

from qtpy.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QSpinBox, QProgressBar,
    QFileDialog, QTextEdit, QGroupBox, QTabWidget, QMessageBox
)
from qtpy.QtCore import Qt
from qtpy.QtGui import QFont

from .workers import OptimizationWorker
from .widgets import ResultsTable, ResultsPlotter
from .launcher import _ensure_gui_available
from .pipeline_handler import PipelineHandler

logger = logging.getLogger(__name__)

try:
    import napari
except ImportError:
    napari = None


class ParticleAnalysisGUI(QWidget):
    """Main GUI application for 3D Particle Analysis."""
    
    def __init__(self):
        super().__init__()
        _ensure_gui_available()
        
        self.ct_folder_path = ""
        self.output_dir = ""
        self.optimization_worker = None
        self.optimization_summary = None
        self.napari_viewer = None
        self.pipeline_handler = None
        
        self.setup_ui()
        self.connect_signals()
        
        # Set window properties
        self.setWindowTitle("3D Particle Analysis Pipeline")
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)
    
    def setup_ui(self):
        """Setup the main user interface."""
        layout = QHBoxLayout(self)
        
        # Left panel: Controls
        left_panel = self.create_control_panel()
        layout.addWidget(left_panel, 1)
        
        # Right panel: Results
        right_panel = self.create_results_panel()
        layout.addWidget(right_panel, 2)
        
        # Initialize default values
        self.max_radius_spinbox.setValue(10)
        self.update_radius_preview()
    
    def create_control_panel(self):
        """Create the left control panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # File Selection
        file_group = QGroupBox("CT Image Selection")
        file_layout = QVBoxLayout(file_group)
        
        self.folder_label = QLabel("📁 No folder selected")
        self.folder_label.setObjectName("folderLabel")
        
        self.select_folder_btn = QPushButton("📁 Select CT Images Folder...")
        self.select_folder_btn.setObjectName("selectFolderButton")
        self.select_folder_btn.setMinimumHeight(40)
        
        self.image_count_label = QLabel("")
        self.image_count_label.setObjectName("imageCountLabel")
        
        file_layout.addWidget(self.folder_label)
        file_layout.addWidget(self.select_folder_btn)
        file_layout.addWidget(self.image_count_label)
        
        # Optimization Parameters
        params_group = QGroupBox("Optimization Parameters")
        params_layout = QGridLayout(params_group)
        
        params_layout.addWidget(QLabel("Maximum Radius:"), 0, 0)
        self.max_radius_spinbox = QSpinBox()
        self.max_radius_spinbox.setRange(2, 15)
        self.max_radius_spinbox.setValue(10)
        params_layout.addWidget(self.max_radius_spinbox, 0, 1)
        
        self.radius_preview_label = QLabel("")
        self.radius_preview_label.setStyleSheet("color: #5a9bd3; font-size: 11px;")
        params_layout.addWidget(self.radius_preview_label, 1, 0, 1, 2)
        
        # Execution Controls
        exec_group = QGroupBox("Execution")
        exec_layout = QVBoxLayout(exec_group)
        
        self.start_btn = QPushButton("🚀 Start Analysis (GO)")
        self.start_btn.setObjectName("startButton")
        self.start_btn.setMinimumHeight(50)
        self.start_btn.setEnabled(False)
        
        self.cancel_btn = QPushButton("❌ Cancel")
        self.cancel_btn.setObjectName("cancelButton")
        self.cancel_btn.setEnabled(False)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setStyleSheet("color: #5cb85c;")
        
        exec_layout.addWidget(self.start_btn)
        exec_layout.addWidget(self.cancel_btn)
        exec_layout.addWidget(self.progress_bar)
        exec_layout.addWidget(self.status_label)
        
        # Final Results Display
        results_group = QGroupBox("🎯 Optimization Results")
        results_layout = QVBoxLayout(results_group)
        
        self.final_results_text = QTextEdit()
        self.final_results_text.setObjectName("finalResultsText")
        self.final_results_text.setMaximumHeight(150)
        self.final_results_text.setReadOnly(True)
        
        self.view_3d_btn = QPushButton("🔍 View 3D Results")
        self.view_3d_btn.setObjectName("view3dButton")
        self.view_3d_btn.setEnabled(False)
        self.view_3d_btn.setMinimumHeight(40)
        
        results_layout.addWidget(self.final_results_text)
        results_layout.addWidget(self.view_3d_btn)
        
        # Add all groups to panel
        layout.addWidget(file_group)
        layout.addWidget(params_group)
        layout.addWidget(exec_group)
        layout.addWidget(results_group)
        layout.addStretch()
        
        return panel
    
    def create_results_panel(self):
        """Create the right results panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Create tab widget
        tab_widget = QTabWidget()
        
        # Results table tab
        self.results_table = ResultsTable()
        tab_widget.addTab(self.results_table, "📊 Data Table")
        
        # Analysis graphs tab
        self.results_plotter = ResultsPlotter()
        tab_widget.addTab(self.results_plotter, "📈 Analysis Graphs")
        
        layout.addWidget(tab_widget)
        
        return panel
    
    def connect_signals(self):
        """Connect UI signals to methods."""
        self.select_folder_btn.clicked.connect(self.select_ct_folder)
        self.max_radius_spinbox.valueChanged.connect(self.update_radius_preview)
        self.start_btn.clicked.connect(self.start_analysis)
        self.cancel_btn.clicked.connect(self.cancel_analysis)
        self.view_3d_btn.clicked.connect(self.view_3d_results)
        self.results_table.itemSelectionChanged.connect(self.on_table_selection_changed)
    
    def select_ct_folder(self):
        """Select CT images folder for complete processing."""
        folder = QFileDialog.getExistingDirectory(
            self, 
            "Select CT Images Folder", 
            "",
            QFileDialog.ShowDirsOnly
        )
        
        if folder:
            self.ct_folder_path = folder
            self.folder_label.setText(f"📁 {folder}")
            self.folder_label.setStyleSheet("")
            
            # Validate folder and count images (support multiple formats)
            from ..utils import get_image_files
            image_files = get_image_files(Path(folder))
            
            if len(image_files) > 0:
                self.start_btn.setEnabled(True)
                self.image_count_label.setStyleSheet("color: #5cb85c;")
                
                # Show file format info
                formats_found = set(f.suffix.lower() for f in image_files)
                format_text = ", ".join(formats_found)
                self.image_count_label.setText(
                    f"✅ Found {len(image_files)} images ({format_text}) for processing"
                )
            else:
                self.start_btn.setEnabled(False)
                self.image_count_label.setStyleSheet("color: #d9534f;")
                self.image_count_label.setText("⚠️ No supported image files found (PNG, JPG, TIFF, BMP)")
    
    def update_radius_preview(self):
        """Update radius range preview."""
        max_radius = self.max_radius_spinbox.value()
        radii_list = list(range(1, max_radius + 1))
        self.radius_preview_label.setText(f"Will test radii: {radii_list}")
    
    def start_analysis(self):
        """Start the analysis process."""
        if not self.ct_folder_path:
            QMessageBox.warning(self, "Warning", "Please select CT images folder first.")
            return
        
        # Setup output directory and pipeline handler
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        self.output_dir = Path("output") / f"gui_run_{timestamp}"
        self.pipeline_handler = PipelineHandler(self.output_dir)
        
        # Clear previous results
        self.results_table.clear_results()
        self.results_plotter.clear_plots()
        self.optimization_summary = None
        
        # Prepare UI for analysis
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, self.max_radius_spinbox.value())
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting analysis...")
        
        # Process CT images through complete pipeline
        try:
            # Process CT images
            processed_count = self.pipeline_handler.process_ct_images(
                self.ct_folder_path,
                progress_callback=self.status_label.setText
            )
            
            self.status_label.setText(f"Processed {processed_count} CT images into masks...")
            
            # Create 3D volume
            volume_path = self.pipeline_handler.create_volume(
                progress_callback=self.status_label.setText
            )
            
            # Start optimization worker
            radii = list(range(1, self.max_radius_spinbox.value() + 1))
            self.optimization_worker = OptimizationWorker(
                vol_path=str(volume_path),
                output_dir=str(self.output_dir),
                radii=radii
            )
            
            # Connect worker signals
            self.optimization_worker.progress_updated.connect(self.on_progress_updated)
            self.optimization_worker.optimization_complete.connect(self.on_optimization_complete)
            self.optimization_worker.error_occurred.connect(self.on_error_occurred)
            
            # Start worker
            self.optimization_worker.start()
            
        except Exception as e:
            logger.error(f"Analysis setup failed: {e}")
            QMessageBox.critical(self, "Error", f"Failed to start analysis:\n\n{str(e)}")
            self.reset_ui_after_analysis()
    
    def cancel_analysis(self):
        """Cancel the ongoing analysis."""
        if self.optimization_worker and self.optimization_worker.isRunning():
            self.optimization_worker.cancel()
            self.optimization_worker.wait()
            
        self.status_label.setText("Analysis cancelled")
        self.reset_ui_after_analysis()
    
    def on_progress_updated(self, result):
        """Handle progress updates from optimization worker."""
        # Update progress bar
        self.progress_bar.setValue(result.radius)
        
        # Update status
        self.status_label.setText(f"Testing radius {result.radius}: {result.particle_count} particles")
        
        # Calculate new metrics for display
        new_metrics = self._calculate_current_metrics(result)
        
        # Add to table
        self.results_table.add_result(result, new_metrics)
        
        # Update plots
        if hasattr(self, 'temp_results'):
            self.temp_results.append(result)
            self.temp_metrics.append(new_metrics)
        else:
            self.temp_results = [result]
            self.temp_metrics = [new_metrics]
        
        self.results_plotter.update_plots(self.temp_results, new_metrics_data=self.temp_metrics)
    
    def _calculate_current_metrics(self, result):
        """Calculate metrics for real-time display during optimization."""
        from ..volume.metrics import calculate_hhi
        from ..volume.optimization.utils import detect_knee_point
        
        # Calculate HHI
        hhi = 0.0
        if hasattr(result, 'labels_path') and result.labels_path:
            try:
                labels = np.load(result.labels_path)
                hhi = calculate_hhi(labels)
            except:
                hhi = result.largest_particle_ratio
        
        # Calculate knee distance if enough data
        knee_dist = 0.0
        if hasattr(self, 'temp_results') and len(self.temp_results) >= 2:
            all_results = self.temp_results + [result]
            radii = [r.radius for r in all_results]
            counts = [r.particle_count for r in all_results]
            try:
                knee_idx = detect_knee_point(radii, counts)
                knee_dist = abs(result.radius - radii[knee_idx])
            except:
                pass
        
        return {
            'hhi': hhi,
            'knee_dist': knee_dist, 
            'vi_stability': 0.5  # Placeholder for real-time display
        }
    
    def on_optimization_complete(self, summary):
        """Handle optimization completion."""
        logger.info("=" * 70)
        logger.info("on_optimization_complete CALLED!")
        logger.info(f"Summary received: {summary}")
        logger.info(f"Optimization complete: {len(summary.results)} radii tested, best r={summary.best_radius}")
        logger.info("=" * 70)
        self.optimization_summary = summary
        
        # Calculate final metrics for all results
        final_metrics_data = [
            self._calculate_final_metrics(result, summary.results) 
            for result in summary.results
        ]
        
        # Update final results display
        best_result = summary.get_result_by_radius(summary.best_radius)
        if best_result:
            best_metrics = final_metrics_data[summary.results.index(best_result)]
            results_text = f"""🎯 OPTIMAL RADIUS: r = {summary.best_radius}

📊 New Pareto+Distance Results:
• Particles: {best_result.particle_count:,}
• HHI Dominance: {best_metrics['hhi']:.3f}
• Knee Distance: {best_metrics['knee_dist']:.1f}
• VI Stability: {best_metrics['vi_stability']:.3f}

✅ Method: {summary.optimization_method}
🔬 Explanation: Selected via Pareto optimality and distance minimization
"""
            self.final_results_text.setText(results_text)
        
        # Update plots with best radius highlighted
        self.results_plotter.update_plots(summary.results, summary.best_radius, final_metrics_data)
        
        # Clear and rebuild table with final metrics
        self.results_table.clear_results()
        for i, result in enumerate(summary.results):
            is_best = (result.radius == summary.best_radius)
            self.results_table.add_result(result, final_metrics_data[i], is_best)
        
        # Enable 3D viewing
        self.view_3d_btn.setEnabled(True)
        
        # Clean up temporary results
        if hasattr(self, 'temp_results'):
            delattr(self, 'temp_results')
        
        self.status_label.setText("✅ Analysis completed successfully!")
        self.reset_ui_after_analysis()
    
    def _calculate_final_metrics(self, result, all_results):
        """Calculate comprehensive metrics for final display."""
        from ..volume.metrics import calculate_hhi, calculate_variation_of_information
        from ..volume.optimization.utils import detect_knee_point
        
        # Calculate HHI
        hhi = 0.0
        if hasattr(result, 'labels_path') and result.labels_path:
            try:
                labels = np.load(result.labels_path)
                hhi = calculate_hhi(labels)
            except Exception as e:
                logger.warning(f"Failed to calculate HHI for r={result.radius}: {e}")
                hhi = result.largest_particle_ratio
        
        # Calculate knee distance
        knee_dist = 0.0
        radii = [r.radius for r in all_results]
        counts = [r.particle_count for r in all_results]
        if len(radii) >= 3:
            try:
                knee_idx = detect_knee_point(radii, counts)
                knee_dist = abs(result.radius - radii[knee_idx])
            except Exception as e:
                logger.warning(f"Failed to detect knee point: {e}")
        
        # Calculate VI stability
        vi_stability = self._calculate_vi_for_result(result, all_results)
        
        return {
            'hhi': hhi,
            'knee_dist': knee_dist,
            'vi_stability': vi_stability
        }
    
    def _calculate_vi_for_result(self, result, all_results):
        """Calculate VI stability for a single result."""
        from ..volume.metrics import calculate_variation_of_information
        
        # Find current index
        try:
            current_idx = next(i for i, r in enumerate(all_results) if r.radius == result.radius)
        except StopIteration:
            return 0.5
        
        # First result has no previous comparison
        if current_idx == 0:
            return 0.5
        
        # Check if both current and previous have labels
        prev_result = all_results[current_idx - 1]
        if not (hasattr(result, 'labels_path') and result.labels_path and 
                hasattr(prev_result, 'labels_path') and prev_result.labels_path):
            return 0.5
        
        # Calculate VI
        try:
            labels_curr = np.load(result.labels_path)
            labels_prev = np.load(prev_result.labels_path)
            return calculate_variation_of_information(labels_prev, labels_curr)
        except Exception as e:
            logger.warning(f"Failed to calculate VI for r={result.radius}: {e}")
            return 0.5
    
    def on_error_occurred(self, error_msg):
        """Handle errors from optimization worker."""
        QMessageBox.critical(self, "Analysis Error", f"Analysis failed:\n\n{error_msg}")
        self.status_label.setText("❌ Analysis failed")
        self.reset_ui_after_analysis()
    
    def reset_ui_after_analysis(self):
        """Reset UI elements after analysis completion or cancellation."""
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.optimization_worker = None
    
    def on_table_selection_changed(self):
        """Handle table selection changes."""
        # Optional: Could trigger 3D view updates based on selected radius
        pass
    
    def view_3d_results(self):
        """Open 3D viewer with all radius results."""
        if not self.optimization_summary:
            QMessageBox.warning(self, "Warning", "No analysis results available.")
            return
        
        self.load_3d_results()  # Load all radii, not specific one
    
    def load_3d_results(self, radius: int = None):
        """Load 3D results for specific radius or all radii."""
        try:
            volume_path = self.output_dir / "volume.npy"
            
            if not volume_path.exists():
                QMessageBox.warning(self, "Warning", "Volume file not found.")
                return
            
            if napari is None:
                QMessageBox.warning(self, "Warning", "Napari not available for 3D viewing.")
                return
            
            # Check if viewer exists and is still valid
            viewer_needs_creation = True
            if self.napari_viewer is not None:
                try:
                    # Try to access the viewer to check if it's still valid
                    _ = self.napari_viewer.layers
                    viewer_needs_creation = False
                except (RuntimeError, AttributeError):
                    # Viewer has been deleted/closed
                    self.napari_viewer = None
                    viewer_needs_creation = True
            
            # Create new viewer if needed
            if viewer_needs_creation:
                self.napari_viewer = napari.Viewer(title="3D Particle Analysis - All Radii")
                
                # Store original close method and override with cleanup
                original_close = self.napari_viewer.close
                
                def close_with_cleanup():
                    self.napari_viewer = None
                    original_close()
                
                # Override close method instead of using events
                self.napari_viewer.close = close_with_cleanup
                
                # Load volume once
                volume = np.load(volume_path)
                self.napari_viewer.add_image(volume, name="Volume", rendering="mip")
            
            # Clear existing label layers (with safety check)
            try:
                for layer in list(self.napari_viewer.layers):
                    if layer.name.startswith("Particles"):
                        self.napari_viewer.layers.remove(layer)
            except (RuntimeError, AttributeError):
                # If viewer became invalid during operation, recreate it
                self.napari_viewer = None
                return self.load_3d_results(radius)  # Recursive call to restart
            
            # Add all available radius results
            if self.optimization_summary:
                try:
                    # Sort results by radius
                    sorted_results = sorted(self.optimization_summary.results, key=lambda x: x.radius)
                    
                    for result in sorted_results:
                        labels_path = self.output_dir / f"labels_r{result.radius}.npy"
                        
                        if labels_path.exists():
                            labels = np.load(labels_path)
                            
                            # Create layer name with details
                            layer_name = f"Particles r={result.radius} ({result.particle_count}p, {result.mean_contacts:.1f}c)"
                            
                            # Add layer with unique colormap
                            layer = self.napari_viewer.add_labels(
                                labels.astype(np.int32), 
                                name=layer_name,
                                blending="translucent",
                                opacity=0.7
                            )
                            
                            # Highlight best radius
                            if result.radius == self.optimization_summary.best_radius:
                                layer.name = f"★ {layer_name} (BEST)"
                                layer.opacity = 1.0
                            
                            # Initially show only best radius
                            if result.radius != self.optimization_summary.best_radius:
                                layer.visible = False
                    
                    # Update window title
                    best_r = self.optimization_summary.best_radius
                    self.napari_viewer.title = f"3D Particle Analysis - Best: r={best_r} (click layers to compare)"
                    
                except (RuntimeError, AttributeError):
                    # If viewer became invalid during operation
                    QMessageBox.warning(self, "Warning", "3D viewer became unavailable during setup. Please try again.")
                    self.napari_viewer = None
                    return
            
            # Show viewer (with safety check)
            try:
                self.napari_viewer.show()
            except (RuntimeError, AttributeError):
                QMessageBox.warning(self, "Warning", "Failed to show 3D viewer. Please try again.")
                self.napari_viewer = None
                return
            
            # Add instruction message
            if self.optimization_summary:
                logger.info("3D Viewer launched successfully")
                logger.info(f"Best radius (r={self.optimization_summary.best_radius}) is shown by default")
                logger.info("Use layer panel to toggle and compare different radius results")
            
        except Exception as e:
            QMessageBox.critical(self, "3D Viewer Error", f"Failed to load 3D results:\n\n{str(e)}")

__all__ = ["ParticleAnalysisGUI"] 