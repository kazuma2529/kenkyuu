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
from .config import (
    WINDOW_TITLE, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT,
    DEFAULT_MAX_RADIUS, SUPPORTED_TIF_FORMATS,
    OUTPUT_CSV_NAME, OUTPUT_BEST_LABELS_NAME,
    CONNECTIVITY_NAMES
)
from .metrics_calculator import MetricsCalculator
from .napari_integration import NapariViewerManager, NAPARI_AVAILABLE

logger = logging.getLogger(__name__)


class ParticleAnalysisGUI(QWidget):
    """Main GUI application for 3D Particle Analysis."""
    
    def __init__(self):
        super().__init__()
        _ensure_gui_available()
        
        self.ct_folder_path = ""
        self.output_dir = ""
        self.optimization_worker = None
        self.optimization_summary = None
        self.pipeline_handler = None
        self.napari_manager = NapariViewerManager()
        
        self.setup_ui()
        self.connect_signals()
        
        # Set window properties
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)
    
    def setup_ui(self):
        """Setup the main user interface with simplified UX."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # === Top Section: Simple Controls ===
        simple_controls = self.create_simple_controls()
        main_layout.addWidget(simple_controls)
        
        # === Middle Section: Progress & Results ===
        progress_section = self.create_progress_section()
        main_layout.addWidget(progress_section, 1)
        
        # === Bottom Section: Advanced Settings (collapsible) ===
        self.advanced_section = self.create_advanced_section()
        self.advanced_section.setVisible(False)  # Hidden by default
        main_layout.addWidget(self.advanced_section)
        
        # Initialize default values
        self.max_radius_spinbox.setValue(DEFAULT_MAX_RADIUS)
        self.update_radius_preview()
    
    def create_simple_controls(self):
        """Create simplified control panel for non-technical users."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(20)
        
        # Title and Instructions
        title_label = QLabel("3D Particle Analysis - Simple Mode")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #5a9bd3;")
        
        instruction_label = QLabel("Just 2 simple steps to analyze your CT images:")
        instruction_label.setStyleSheet("color: #a0a0a0; font-size: 11pt;")
        
        layout.addWidget(title_label)
        layout.addWidget(instruction_label)
        
        # Buttons Layout
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(20)
        
        # Step 1: Folder Selection
        step1_widget = QWidget()
        step1_layout = QVBoxLayout(step1_widget)
        step1_layout.setSpacing(10)
        
        step1_label = QLabel("Step 1️⃣")
        step1_label.setStyleSheet("font-size: 13pt; font-weight: bold; color: #5a9bd3;")
        
        self.select_folder_btn = QPushButton("📁 Select CT Images Folder")
        self.select_folder_btn.setObjectName("selectFolderButton")
        self.select_folder_btn.setMinimumHeight(60)
        self.select_folder_btn.setMinimumWidth(280)
        
        self.folder_status_label = QLabel("No folder selected")
        self.folder_status_label.setObjectName("folderLabel")
        self.folder_status_label.setAlignment(Qt.AlignCenter)
        self.folder_status_label.setWordWrap(True)
        
        step1_layout.addWidget(step1_label, alignment=Qt.AlignCenter)
        step1_layout.addWidget(self.select_folder_btn)
        step1_layout.addWidget(self.folder_status_label)
        
        # Step 2: Start Analysis
        step2_widget = QWidget()
        step2_layout = QVBoxLayout(step2_widget)
        step2_layout.setSpacing(10)
        
        step2_label = QLabel("Step 2️⃣")
        step2_label.setStyleSheet("font-size: 13pt; font-weight: bold; color: #5a9bd3;")
        
        self.start_btn = QPushButton("🚀 Start Analysis (GO)")
        self.start_btn.setObjectName("startButton")
        self.start_btn.setMinimumHeight(60)
        self.start_btn.setMinimumWidth(280)
        self.start_btn.setEnabled(False)
        
        self.status_label = QLabel("Ready to start")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #5cb85c;")
        
        step2_layout.addWidget(step2_label, alignment=Qt.AlignCenter)
        step2_layout.addWidget(self.start_btn)
        step2_layout.addWidget(self.status_label)
        
        buttons_layout.addWidget(step1_widget)
        buttons_layout.addWidget(step2_widget)
        
        layout.addLayout(buttons_layout)
        
        # Advanced Settings Toggle
        advanced_toggle_layout = QHBoxLayout()
        advanced_toggle_layout.addStretch()
        
        self.advanced_toggle_btn = QPushButton("⚙️ Advanced Settings")
        self.advanced_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #5a9bd3;
                border: 1px solid #5a9bd3;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #3a4049;
            }
            QPushButton:checked {
                background-color: #5a9bd3;
                color: #ffffff;
            }
        """)
        self.advanced_toggle_btn.setCheckable(True)
        self.advanced_toggle_btn.clicked.connect(self.toggle_advanced_settings)
        
        advanced_toggle_layout.addWidget(self.advanced_toggle_btn)
        layout.addLayout(advanced_toggle_layout)
        
        return panel
    
    def create_progress_section(self):
        """Create progress monitoring section."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Progress Controls
        progress_controls = QWidget()
        progress_layout = QHBoxLayout(progress_controls)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(30)
        
        self.cancel_btn = QPushButton("❌ Cancel")
        self.cancel_btn.setObjectName("cancelButton")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setMaximumWidth(120)
        
        progress_layout.addWidget(self.progress_bar, 1)
        progress_layout.addWidget(self.cancel_btn)
        
        layout.addWidget(progress_controls)
        
        # Tab Widget for Results
        self.results_tabs = QTabWidget()
        
        # Real-time Results Table Tab
        self.results_table = ResultsTable()
        self.results_tabs.addTab(self.results_table, "📊 Real-time Results")
        
        # Analysis Graphs Tab
        self.results_plotter = ResultsPlotter()
        self.results_tabs.addTab(self.results_plotter, "📈 Analysis Graphs")
        
        # Final Results Tab
        final_results_widget = QWidget()
        final_results_layout = QVBoxLayout(final_results_widget)
        
        self.final_results_text = QTextEdit()
        self.final_results_text.setObjectName("finalResultsText")
        self.final_results_text.setReadOnly(True)
        self.final_results_text.setPlaceholderText("Final optimization results will appear here after analysis completes...")
        
        self.view_3d_btn = QPushButton("🔍 View 3D Results")
        self.view_3d_btn.setObjectName("view3dButton")
        self.view_3d_btn.setEnabled(False)
        self.view_3d_btn.setMinimumHeight(40)
        
        final_results_layout.addWidget(self.final_results_text)
        final_results_layout.addWidget(self.view_3d_btn)
        
        self.results_tabs.addTab(final_results_widget, "🎯 Final Results")
        
        layout.addWidget(self.results_tabs)
        
        return panel
    
    def create_advanced_section(self):
        """Create advanced settings section (hidden by default)."""
        group = QGroupBox("⚙️ Advanced Settings")
        layout = QVBoxLayout(group)
        
        # Erosion Radius Range
        radius_widget = QWidget()
        radius_layout = QGridLayout(radius_widget)
        
        radius_label = QLabel("Erosion Radius Range:")
        radius_label.setStyleSheet("font-weight: bold;")
        
        radius_layout.addWidget(radius_label, 0, 0, 1, 2)
        radius_layout.addWidget(QLabel("Maximum Radius:"), 1, 0)
        
        self.max_radius_spinbox = QSpinBox()
        self.max_radius_spinbox.setRange(2, 15)
        self.max_radius_spinbox.setValue(10)
        self.max_radius_spinbox.setToolTip("Maximum erosion radius to test (default: 10)")
        radius_layout.addWidget(self.max_radius_spinbox, 1, 1)
        
        self.radius_preview_label = QLabel("")
        self.radius_preview_label.setStyleSheet("color: #5a9bd3; font-size: 10pt; padding: 8px;")
        radius_layout.addWidget(self.radius_preview_label, 2, 0, 1, 2)
        
        layout.addWidget(radius_widget)
        
        # Contact Analysis Method
        from qtpy.QtWidgets import QComboBox
        
        contact_widget = QWidget()
        contact_layout = QGridLayout(contact_widget)
        
        contact_label = QLabel("Contact Analysis Method:")
        contact_label.setStyleSheet("font-weight: bold;")
        
        contact_layout.addWidget(contact_label, 0, 0, 1, 2)
        contact_layout.addWidget(QLabel("Connectivity:"), 1, 0)
        
        self.connectivity_combo = QComboBox()
        self.connectivity_combo.addItem("6-Neighborhood (Face Contact) 🔷 Recommended", 6)
        self.connectivity_combo.addItem("26-Neighborhood (Face+Edge+Corner)", 26)
        self.connectivity_combo.setCurrentIndex(0)  # Default to 6-neighborhood
        self.connectivity_combo.setToolTip(
            "6-Neighborhood: Only face-to-face contacts (more conservative)\n"
            "26-Neighborhood: Includes edge and corner contacts (more permissive)"
        )
        contact_layout.addWidget(self.connectivity_combo, 1, 1)
        
        # Description label
        self.connectivity_desc_label = QLabel(
            "Face contacts only (physical touching surfaces)"
        )
        self.connectivity_desc_label.setStyleSheet("color: #5a9bd3; font-size: 10pt; padding: 8px;")
        self.connectivity_desc_label.setWordWrap(True)
        contact_layout.addWidget(self.connectivity_desc_label, 2, 0, 1, 2)
        
        # Connect signal to update description
        self.connectivity_combo.currentIndexChanged.connect(self.update_connectivity_description)
        
        layout.addWidget(contact_widget)
        
        # Info Label
        info_label = QLabel(
            "ℹ️ Advanced mode allows you to customize optimization parameters.\n"
            "For most users, the default automatic settings work best.\n\n"
            "💡 Tip: 6-neighborhood is recommended for accurate physical contact analysis."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #a0a0a0; font-size: 9pt; padding: 10px;")
        layout.addWidget(info_label)
        
        return group
    
    def toggle_advanced_settings(self):
        """Toggle visibility of advanced settings section."""
        is_visible = self.advanced_section.isVisible()
        self.advanced_section.setVisible(not is_visible)
        
        # Update button text
        if self.advanced_section.isVisible():
            self.advanced_toggle_btn.setText("⚙️ Hide Advanced Settings")
        else:
            self.advanced_toggle_btn.setText("⚙️ Advanced Settings")
    
    def update_connectivity_description(self):
        """Update connectivity description based on selected option."""
        connectivity = self.connectivity_combo.currentData()
        if connectivity == 6:
            self.connectivity_desc_label.setText(
                "🔷 Face contacts only (physical touching surfaces)\n"
                "More accurate for real particle analysis"
            )
            self.connectivity_desc_label.setStyleSheet("color: #5cb85c; font-size: 10pt; padding: 8px;")
        else:  # 26
            self.connectivity_desc_label.setText(
                "⬛ Face + Edge + Corner contacts (all 26 neighbors)\n"
                "May overestimate contacts, useful for dense packing"
            )
            self.connectivity_desc_label.setStyleSheet("color: #5a9bd3; font-size: 10pt; padding: 8px;")
    
    
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
            "Select CT Images Folder (TIF/TIFF)", 
            "",
            QFileDialog.ShowDirsOnly
        )
        
        if folder:
            self.ct_folder_path = folder
            
            # Validate folder and count images (TIF/TIFF only for 3D Otsu)
            from ..utils import get_image_files
            # Prioritize TIF/TIFF for high-precision 3D Otsu
            image_files = get_image_files(
                Path(folder), 
                supported_formats=SUPPORTED_TIF_FORMATS
            )
            
            if len(image_files) > 0:
                self.start_btn.setEnabled(True)
                
                # Show file format info
                formats_found = set(f.suffix.lower() for f in image_files)
                format_text = ", ".join(formats_found)
                
                # Update folder status label
                folder_name = Path(folder).name
                self.folder_status_label.setText(
                    f"✅ Selected: {folder_name}\n"
                    f"{len(image_files)} TIF/TIFF images ({format_text})"
                )
                self.folder_status_label.setStyleSheet("color: #5cb85c; font-weight: bold;")
                
                # Update status
                self.status_label.setText(
                    f"Ready - {len(image_files)} TIF images for 3D Otsu"
                )
                self.status_label.setStyleSheet("color: #5cb85c; font-weight: bold;")
                
                logger.info(f"Selected folder: {folder}")
                logger.info(f"Found {len(image_files)} TIF/TIFF images")
            else:
                self.start_btn.setEnabled(False)
                self.folder_status_label.setText(
                    "⚠️ No TIF/TIFF images found\n"
                    "3D Otsu requires TIF/TIFF format"
                )
                self.folder_status_label.setStyleSheet("color: #d9534f; font-weight: bold;")
                self.status_label.setText("Error: No TIF/TIFF images found")
                self.status_label.setStyleSheet("color: #d9534f; font-weight: bold;")
                logger.warning(f"No TIF/TIFF images found in {folder}")
    
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
        self.progress_bar.setRange(0, 100)  # Use percentage (0-100)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting analysis...")
        
        # Process CT images through NEW high-precision 3D binarization pipeline
        try:
            # NEW: Direct 3D Otsu binarization (M2 implementation)
            self.status_label.setText("Performing high-precision 3D Otsu binarization...")
            logger.info("=" * 70)
            logger.info("Starting NEW 3D binarization pipeline (M2)")
            logger.info(f"CT folder: {self.ct_folder_path}")
            logger.info("=" * 70)
            
            volume_path, binarization_info = self.pipeline_handler.create_volume_from_3d_binarization(
                ct_folder_path=self.ct_folder_path,
                progress_callback=self.status_label.setText
            )
            
            # Log binarization info
            logger.info("Binarization completed successfully:")
            logger.info(f"  - Images processed: {binarization_info['num_images']}")
            logger.info(f"  - Volume shape: {binarization_info['volume_shape']}")
            logger.info(f"  - Otsu threshold: {binarization_info['threshold']:.1f}")
            logger.info(f"  - Polarity: {binarization_info['polarity']}")
            logger.info(f"  - Foreground: {binarization_info['foreground_ratio']:.2%}")
            
            self.status_label.setText(
                f"3D Otsu completed: {binarization_info['num_images']} images, "
                f"{binarization_info['polarity']}"
            )
            
            # Start optimization worker
            radii = list(range(1, self.max_radius_spinbox.value() + 1))
            connectivity = self.connectivity_combo.currentData()  # Get selected connectivity (6 or 26)
            
            logger.info(f"Starting optimization with connectivity={connectivity}")
            
            self.optimization_worker = OptimizationWorker(
                vol_path=str(volume_path),
                output_dir=str(self.output_dir),
                radii=radii,
                connectivity=connectivity
            )
            
            # Connect worker signals
            self.optimization_worker.progress_updated.connect(self.on_progress_updated)
            self.optimization_worker.optimization_complete.connect(self.on_optimization_complete)
            self.optimization_worker.error_occurred.connect(self.on_error_occurred)
            
            # NEW: Connect detailed progress signals
            self.optimization_worker.progress_text_updated.connect(self.update_status_text)
            self.optimization_worker.progress_percentage_updated.connect(self.update_progress_bar)
            self.optimization_worker.stage_changed.connect(self.update_stage_indicator)
            
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
        """Handle progress updates from optimization worker.
        
        This receives OptimizationResult objects and updates the real-time table and graphs.
        """
        # Calculate new metrics for display
        new_metrics = self._calculate_current_metrics(result)
        
        # Add to table (リアルタイムテーブル更新)
        self.results_table.add_result(result, new_metrics)
        
        # Update plots (グラフ更新)
        if hasattr(self, 'temp_results'):
            self.temp_results.append(result)
            self.temp_metrics.append(new_metrics)
        else:
            self.temp_results = [result]
            self.temp_metrics = [new_metrics]
        
        self.results_plotter.update_plots(self.temp_results, new_metrics_data=self.temp_metrics)
        
        logger.info(
            f"Table updated: r={result.radius}, particles={result.particle_count}, "
            f"contacts={result.mean_contacts:.1f}"
        )
    
    def update_status_text(self, text: str):
        """Update status label with progress text.
        
        Args:
            text: Progress text (e.g., "r = 3: 1234 particles, 6.2 avg contacts")
        """
        self.status_label.setText(text)
        self.status_label.setStyleSheet("color: #5a9bd3; font-weight: bold;")
    
    def update_progress_bar(self, percentage: int):
        """Update progress bar value.
        
        Args:
            percentage: Progress percentage (0-100)
        """
        self.progress_bar.setValue(percentage)
        logger.debug(f"Progress bar updated: {percentage}%")
    
    def update_stage_indicator(self, stage: str):
        """Update processing stage indicator.
        
        Args:
            stage: Current stage (e.g., "initialization", "optimization", "finalization")
        """
        stage_text_map = {
            "initialization": "🔄 初期化中...",
            "optimization": "⚙️ 最適化実行中...",
            "finalization": "🎯 最適r選定中...",
        }
        
        display_text = stage_text_map.get(stage, f"処理中: {stage}")
        logger.info(f"Stage changed: {display_text}")
        
        # Optionally update a stage label if you have one
        # self.stage_label.setText(display_text)
    
    def _calculate_current_metrics(self, result):
        """Calculate metrics for real-time display during optimization."""
        return MetricsCalculator.calculate_current_metrics(
            result,
            getattr(self, 'temp_results', None)
        )
    
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
            
            # Get connectivity info
            connectivity = self.connectivity_combo.currentData()
            connectivity_name = CONNECTIVITY_NAMES.get(connectivity, f"{connectivity}-Neighborhood")
            
            # Get output directory info
            csv_path = self.output_dir / "optimization_results.csv"
            csv_exists = "✅" if csv_path.exists() else "❌"
            
            results_text = f"""🎯 OPTIMAL RADIUS: r = {summary.best_radius}

📊 Pareto+Distance Results:
• Particles: {best_result.particle_count:,}
• Mean Contacts: {best_result.mean_contacts:.1f}
• HHI Dominance: {best_metrics['hhi']:.3f}
• Knee Distance: {best_metrics['knee_dist']:.1f}
• VI Stability: {best_metrics['vi_stability']:.3f}

🔗 Contact Method: {connectivity_name}
✅ Optimization: {summary.optimization_method}
🔬 Explanation: Selected via Pareto optimality and distance minimization

📁 Saved Results:
{csv_exists} CSV: optimization_results.csv
{csv_exists} Summary: optimization_summary.txt
{csv_exists} Best Labels: best_labels.npy
📂 Location: {self.output_dir}

💡 Click "🔍 View 3D Results" to visualize in Napari
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
    
    def load_best_labels_in_napari(self, best_labels_path: Path):
        """Load the best optimization result in Napari viewer.
        
        Args:
            best_labels_path: Path to best_labels.npy file
        """
        try:
            if napari is None:
                QMessageBox.warning(
                    self, 
                    "Napari Not Available", 
                    "Napari is not installed.\n\n"
                    "Install it with:\n"
                    "pip install napari[all]"
                )
                return
            
            # Load data
            volume_path = self.output_dir / "volume.npy"
            best_labels = np.load(best_labels_path)
            
            best_r = self.optimization_summary.best_radius
            best_result = self.optimization_summary.get_result_by_radius(best_r)
            
            logger.info(f"Opening Napari with best result (r={best_r})")
            logger.info(f"Labels shape: {best_labels.shape}")
            logger.info(f"Unique particles: {best_labels.max()}")
            
            # Check if viewer exists and is still valid
            viewer_needs_creation = True
            if self.napari_viewer is not None:
                try:
                    _ = self.napari_viewer.layers
                    viewer_needs_creation = False
                    # Clear existing layers
                    self.napari_viewer.layers.clear()
                except (RuntimeError, AttributeError):
                    self.napari_viewer = None
                    viewer_needs_creation = True
            
            # Create new viewer if needed
            if viewer_needs_creation:
                title = f"3D Particle Analysis - Best Result (r={best_r})"
                self.napari_viewer = napari.Viewer(title=title)
                
                # Setup cleanup on close
                original_close = self.napari_viewer.close
                def close_with_cleanup():
                    self.napari_viewer = None
                    original_close()
                self.napari_viewer.close = close_with_cleanup
            
            # Load volume if available (as background)
            if volume_path.exists():
                volume = np.load(volume_path)
                self.napari_viewer.add_image(
                    volume, 
                    name="Binary Volume", 
                    rendering="mip",
                    opacity=0.3,
                    colormap="gray"
                )
            
            # Load best labels (main layer)
            self.napari_viewer.add_labels(
                best_labels, 
                name=f"Optimized Particles (r={best_r})",
                opacity=0.8
            )
            
            # Add metadata as text overlay
            if best_result:
                metadata_text = (
                    f"Best Radius: {best_r}\n"
                    f"Particles: {best_result.particle_count}\n"
                    f"Mean Contacts: {best_result.mean_contacts:.1f}\n"
                    f"Largest Ratio: {best_result.largest_particle_ratio:.2%}"
                )
                logger.info(f"Best result metadata:\n{metadata_text}")
            
            # Set optimal view
            self.napari_viewer.dims.ndisplay = 3  # 3D mode
            self.napari_viewer.camera.angles = (45, 45, 45)  # Nice viewing angle
            
            # Show viewer window
            self.napari_viewer.window.show()
            
            logger.info("✅ Napari viewer opened successfully")
            
        except FileNotFoundError as e:
            QMessageBox.warning(
                self, 
                "File Not Found", 
                f"Required file not found:\n{e}"
            )
            logger.error(f"File not found: {e}")
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Napari Error", 
                f"Failed to open 3D viewer:\n\n{str(e)}"
            )
            logger.error(f"Napari error: {e}")
            import traceback
            traceback.print_exc()
    
    def view_3d_results(self):
        """Open 3D viewer with best optimization result.
        
        Shows the best_labels.npy file in Napari for visual inspection.
        Also loads the original volume for context.
        """
        if not self.optimization_summary:
            QMessageBox.warning(self, "Warning", "No analysis results available.")
            return
        
        # Try to load best labels first
        best_labels_path = self.output_dir / "best_labels.npy"
        if best_labels_path.exists():
            self.load_best_labels_in_napari(best_labels_path)
        else:
            # Fallback to loading all radii
            logger.warning("best_labels.npy not found, loading all radii instead")
            self.load_3d_results()  # Load all radii as fallback
    
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