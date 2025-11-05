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
    QFileDialog, QTextEdit, QGroupBox, QTabWidget, QMessageBox,
    QScrollArea, QSizePolicy
)
from qtpy.QtCore import Qt
from qtpy.QtGui import QFont

from .workers import OptimizationWorker
from .widgets import ResultsTable, ResultsPlotter, MplWidget, HistogramPlotter
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
        # Advanced section wrapped by a scroll area to avoid cramped layout
        self.advanced_container = QScrollArea()
        self.advanced_container.setWidgetResizable(True)
        self.advanced_container.setVisible(False)
        advanced_inner = self.create_advanced_section()
        self.advanced_container.setWidget(advanced_inner)
        self.advanced_container.setMinimumHeight(280)
        self.advanced_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        main_layout.addWidget(self.advanced_container)
        
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
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancelButton")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setMaximumWidth(120)
        
        progress_layout.addWidget(self.progress_bar, 1)
        progress_layout.addWidget(self.cancel_btn)
        
        layout.addWidget(progress_controls)
        
        # Tab Widget for Results
        self.results_tabs = QTabWidget()
        
        # Tab 1: Real-time Optimization Results Table
        self.results_table = ResultsTable()
        self.results_tabs.addTab(self.results_table, "📊 Optimization Progress")
        
        # Removed Optimization Curves tab per design
        
        # Tab 2: Contact Number Distribution Histogram
        self.contact_histogram_widget = MplWidget()
        self.contact_histogram_widget.setMinimumHeight(400)
        # Add placeholder text
        contact_placeholder = QWidget()
        contact_placeholder_layout = QVBoxLayout(contact_placeholder)
        contact_placeholder_label = QLabel("📊 Contact number distribution will appear here after analysis completes")
        contact_placeholder_label.setAlignment(Qt.AlignCenter)
        contact_placeholder_label.setStyleSheet("color: #a0a0a0; font-size: 12pt; padding: 50px;")
        contact_placeholder_layout.addWidget(contact_placeholder_label)
        self.contact_histogram_widget.layout().addWidget(contact_placeholder)
        self.results_tabs.addTab(self.contact_histogram_widget, "📊 Contact Distribution")
        
        # Tab 3: Particle Volume Distribution Histogram
        self.volume_histogram_widget = MplWidget()
        self.volume_histogram_widget.setMinimumHeight(400)
        # Add placeholder text
        volume_placeholder = QWidget()
        volume_placeholder_layout = QVBoxLayout(volume_placeholder)
        volume_placeholder_label = QLabel("📊 Particle volume distribution will appear here after analysis completes")
        volume_placeholder_label.setAlignment(Qt.AlignCenter)
        volume_placeholder_label.setStyleSheet("color: #a0a0a0; font-size: 12pt; padding: 50px;")
        volume_placeholder_layout.addWidget(volume_placeholder_label)
        self.volume_histogram_widget.layout().addWidget(volume_placeholder)
        self.results_tabs.addTab(self.volume_histogram_widget, "📊 Volume Distribution")
        
        # Tab 4: Final Results and 3D View
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
        
        # Set default tab to optimization progress
        self.results_tabs.setCurrentIndex(0)
        
        layout.addWidget(self.results_tabs)
        
        return panel
    
    def create_advanced_section(self):
        """Create advanced settings section (hidden by default)."""
        group = QGroupBox("⚙️ Advanced Settings")
        layout = QVBoxLayout(group)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Erosion Radius Range
        radius_widget = QWidget()
        radius_layout = QGridLayout(radius_widget)
        radius_layout.setHorizontalSpacing(12)
        radius_layout.setVerticalSpacing(8)
        radius_layout.setContentsMargins(0, 0, 0, 0)
        
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
        contact_layout.setHorizontalSpacing(12)
        contact_layout.setVerticalSpacing(8)
        contact_layout.setContentsMargins(0, 0, 0, 0)
        
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
        
        # Make value column stretch to keep labels compact
        contact_layout.setColumnStretch(0, 0)
        contact_layout.setColumnStretch(1, 1)
        layout.addWidget(contact_widget)

        # Constraint-based selection parameters
        params_widget = QWidget()
        params_layout = QGridLayout(params_widget)
        params_layout.setHorizontalSpacing(12)
        params_layout.setVerticalSpacing(8)
        params_layout.setContentsMargins(0, 0, 0, 0)

        params_title = QLabel("Constraint-based Selection Parameters:")
        params_title.setStyleSheet("font-weight: bold;")
        params_layout.addWidget(params_title, 0, 0, 1, 2)

        # tau_ratio (largest_particle_ratio threshold)
        from qtpy.QtWidgets import QDoubleSpinBox
        params_layout.addWidget(QLabel("τratio (largest particle ratio):"), 1, 0)
        self.tau_ratio_spin = QDoubleSpinBox()
        self.tau_ratio_spin.setRange(0.0, 1.0)
        self.tau_ratio_spin.setSingleStep(0.01)
        self.tau_ratio_spin.setDecimals(3)
        self.tau_ratio_spin.setValue(0.05)
        self.tau_ratio_spin.setToolTip("Threshold for largest_particle_ratio (default 0.05)")
        self.tau_ratio_spin.setMaximumWidth(160)
        params_layout.addWidget(self.tau_ratio_spin, 1, 1)

        # tau_gain (relative %, e.g., 0.3%)
        params_layout.addWidget(QLabel("τgain (% of base count):"), 2, 0)
        self.tau_gain_percent_spin = QDoubleSpinBox()
        self.tau_gain_percent_spin.setRange(0.0, 5.0)
        self.tau_gain_percent_spin.setSingleStep(0.1)
        self.tau_gain_percent_spin.setDecimals(2)
        self.tau_gain_percent_spin.setValue(0.30)
        self.tau_gain_percent_spin.setToolTip("Relative threshold as percent of base count (default 0.30%)")
        self.tau_gain_percent_spin.setMaximumWidth(160)
        params_layout.addWidget(self.tau_gain_percent_spin, 2, 1)

        # contacts range [cmin, cmax]
        params_layout.addWidget(QLabel("Mean contacts range [min, max]:"), 3, 0)
        range_box = QWidget()
        range_layout = QHBoxLayout(range_box)
        range_layout.setContentsMargins(0, 0, 0, 0)
        range_layout.setSpacing(8)
        self.contacts_min_spin = QSpinBox()
        self.contacts_min_spin.setRange(0, 50)
        self.contacts_min_spin.setValue(4)
        self.contacts_max_spin = QSpinBox()
        self.contacts_max_spin.setRange(1, 100)
        self.contacts_max_spin.setValue(10)
        self.contacts_min_spin.setMaximumWidth(100)
        self.contacts_max_spin.setMaximumWidth(100)
        range_layout.addWidget(self.contacts_min_spin)
        range_layout.addWidget(QLabel("to"))
        range_layout.addWidget(self.contacts_max_spin)
        params_layout.addWidget(range_box, 3, 1)

        # smoothing window (None/1/2)
        params_layout.addWidget(QLabel("Smoothing window (moving average):"), 4, 0)
        self.smoothing_combo = QComboBox()
        self.smoothing_combo.addItem("None", None)
        self.smoothing_combo.addItem("1", 1)
        self.smoothing_combo.addItem("2", 2)
        self.smoothing_combo.setCurrentIndex(0)
        params_layout.addWidget(self.smoothing_combo, 4, 1)

        # Stretch columns so inputs have space
        params_layout.setColumnStretch(0, 0)
        params_layout.setColumnStretch(1, 1)

        layout.addWidget(params_widget)
        
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
        is_visible = self.advanced_container.isVisible()
        self.advanced_container.setVisible(not is_visible)
        
        # Update button text
        if self.advanced_container.isVisible():
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
        self.contact_histogram_widget.clear()
        self.volume_histogram_widget.clear()
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
            
            binary_volume, binarization_info = self.pipeline_handler.create_volume_from_3d_binarization(
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
            # Read selector params from UI
            tau_ratio = float(self.tau_ratio_spin.value())
            tau_gain_rel = float(self.tau_gain_percent_spin.value()) / 100.0
            cmin = int(self.contacts_min_spin.value())
            cmax = int(self.contacts_max_spin.value())
            smoothing_window = self.smoothing_combo.currentData()
            
            logger.info(f"Starting optimization with connectivity={connectivity}")
            
            self.optimization_worker = OptimizationWorker(
                volume=binary_volume,
                output_dir=str(self.output_dir),
                radii=radii,
                connectivity=connectivity,
                tau_ratio=tau_ratio,
                tau_gain_rel=tau_gain_rel,
                contacts_range=(cmin, cmax),
                smoothing_window=smoothing_window
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
        
        # Note: Histograms are plotted once at the end (in on_optimization_complete)
        # Real-time plot updates are not needed for research-oriented histograms
        
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
    
    def on_optimization_complete(self, summary, contact_histogram, volume_histogram):
        """Handle optimization completion with histogram data."""
        logger.info("=" * 70)
        logger.info("on_optimization_complete CALLED!")
        logger.info(f"Summary received: {summary}")
        logger.info(f"Contact histogram: {contact_histogram is not None}")
        logger.info(f"Volume histogram: {volume_histogram is not None}")
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
            labels_path = self.output_dir / f"labels_r{summary.best_radius}.npy"
            labels_exists = "✅" if labels_path.exists() else "❌"
            
            # Add largest particle ratio to results
            largest_ratio = getattr(best_result, 'largest_particle_ratio', 0.0)
            
            results_text = f"""🎯 OPTIMAL RADIUS: r = {summary.best_radius}

📊 Constraint-based Selection:
• Particles: {best_result.particle_count:,}
• Mean Contacts: {best_result.mean_contacts:.1f}
• Largest Particle: {largest_ratio * 100:.1f}%

🔗 Contact Method: {connectivity_name}
✅ Optimization: {summary.optimization_method}
🔬 Explanation: Selected via HardConstraint + MarginalGain + ContactsRange

📁 Saved Results:
{csv_exists} CSV: optimization_results.csv
{labels_exists} Labels: labels_r{summary.best_radius}.npy
📂 Location: {self.output_dir}

💡 View "📊 Contact Distribution" and "📊 Volume Distribution" for insights
"""
            self.final_results_text.setText(results_text)
        
        # Clear and rebuild table with final metrics
        self.results_table.clear_results()
        for i, result in enumerate(summary.results):
            is_best = (result.radius == summary.best_radius)
            self.results_table.add_result(result, final_metrics_data[i], is_best)
        
        # Plot histograms
        if contact_histogram:
            HistogramPlotter.plot_contact_histogram(
                self.contact_histogram_widget, 
                contact_histogram
            )
        else:
            logger.warning("No contact histogram data available")
        
        if volume_histogram:
            HistogramPlotter.plot_volume_histogram(
                self.volume_histogram_widget, 
                volume_histogram
            )
        else:
            logger.warning("No volume histogram data available")
        
        # Enable 3D viewing
        self.view_3d_btn.setEnabled(True)
        
        # Clean up temporary results
        if hasattr(self, 'temp_results'):
            delattr(self, 'temp_results')
        
        self.status_label.setText("✅ Analysis completed successfully!")
        self.reset_ui_after_analysis()
    
    def _calculate_final_metrics(self, result, all_results):
        """Calculate comprehensive metrics for final display."""
        return MetricsCalculator.calculate_final_metrics(result, all_results)
    
    
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
            if not NAPARI_AVAILABLE:
                QMessageBox.warning(
                    self, 
                    "Napari Not Available", 
                    "Napari is not installed.\n\n"
                    "Install it with:\n"
                    "pip install napari[all]"
                )
                return
            
            # Use NapariViewerManager to load best labels (no volume background)
            best_r = self.optimization_summary.best_radius
            best_result = self.optimization_summary.get_result_by_radius(best_r)
            
            # Prepare metadata
            metadata = {
                'Best Radius': best_r,
                'Particle Count': best_result.particle_count,
                'Mean Contacts': f"{best_result.mean_contacts:.2f}"
            }
            
            # Use manager to open viewer
            self.napari_manager.load_best_labels(
                best_labels_path=best_labels_path,
                volume_path=None,
                best_radius=best_r,
                metadata=metadata
            )
            
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
        
        # Load selected radius labels
        if not self.optimization_summary:
            QMessageBox.warning(self, "Warning", "No optimization summary available.")
            return
        best_r = self.optimization_summary.best_radius
        best_labels_path = self.output_dir / f"labels_r{best_r}.npy"
        if best_labels_path.exists():
            self.load_best_labels_in_napari(best_labels_path)
        else:
            QMessageBox.warning(self, "Warning", f"labels_r{best_r}.npy not found.")
    
    def load_3d_results(self, radius: int = None):
        """Load 3D results for specific radius (labels only)."""
        try:
            if not self.optimization_summary:
                QMessageBox.warning(self, "Warning", "No optimization results available.")
                return
            
            # Load selected or best radius labels
            selected_radius = radius if radius is not None else self.optimization_summary.best_radius
            labels_path = self.output_dir / f"labels_r{selected_radius}.npy"
            if labels_path.exists():
                self.load_best_labels_in_napari(labels_path)
            else:
                QMessageBox.warning(self, "Warning", f"labels_r{selected_radius}.npy not found.")
            
        except Exception as e:
            QMessageBox.critical(self, "3D Viewer Error", f"Failed to load 3D results:\n\n{str(e)}")

__all__ = ["ParticleAnalysisGUI"] 