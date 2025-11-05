"""UI component builders for the main window.

This module contains reusable UI construction logic, separated from
business logic and event handling to improve maintainability.
"""

from typing import Tuple

from qtpy.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QSpinBox, QProgressBar,
    QTextEdit, QGroupBox, QTabWidget, QComboBox
)
from qtpy.QtCore import Qt
from qtpy.QtGui import QFont

from .config import (
    DEFAULT_MAX_RADIUS,
    CONNECTIVITY_NAMES
)
from .widgets import ResultsTable, ResultsPlotter, MplWidget


class UIComponentBuilder:
    """Builder for creating GUI components with consistent styling."""
    
    @staticmethod
    def create_simple_controls() -> Tuple[QWidget, dict]:
        """Create simplified control panel for non-technical users.
        
        Returns:
            Tuple of (widget, components_dict) where components_dict contains
            references to interactive elements for event connection.
        """
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
        
        select_folder_btn = QPushButton("📁 Select CT Images Folder")
        select_folder_btn.setObjectName("selectFolderButton")
        select_folder_btn.setMinimumHeight(60)
        select_folder_btn.setMinimumWidth(280)
        
        folder_status_label = QLabel("No folder selected")
        folder_status_label.setObjectName("folderLabel")
        folder_status_label.setStyleSheet("color: #808080; font-size: 10pt; font-style: italic;")
        folder_status_label.setWordWrap(True)
        
        step1_layout.addWidget(step1_label)
        step1_layout.addWidget(select_folder_btn)
        step1_layout.addWidget(folder_status_label)
        step1_layout.addStretch()
        
        # Step 2: Run Analysis
        step2_widget = QWidget()
        step2_layout = QVBoxLayout(step2_widget)
        step2_layout.setSpacing(10)
        
        step2_label = QLabel("Step 2️⃣")
        step2_label.setStyleSheet("font-size: 13pt; font-weight: bold; color: #5a9bd3;")
        
        go_button = QPushButton("⚙️ GO - Start Analysis")
        go_button.setObjectName("goButton")
        go_button.setMinimumHeight(60)
        go_button.setMinimumWidth(280)
        go_button.setEnabled(False)
        
        cancel_button = QPushButton("⏹ Cancel")
        cancel_button.setObjectName("cancelButton")
        cancel_button.setMinimumHeight(40)
        cancel_button.setVisible(False)
        
        step2_layout.addWidget(step2_label)
        step2_layout.addWidget(go_button)
        step2_layout.addWidget(cancel_button)
        step2_layout.addStretch()
        
        buttons_layout.addWidget(step1_widget)
        buttons_layout.addWidget(step2_widget)
        layout.addLayout(buttons_layout)
        
        # Advanced Settings Toggle
        advanced_toggle_btn = QPushButton("⚙️ Advanced Settings (for experts)")
        advanced_toggle_btn.setObjectName("advancedToggleButton")
        advanced_toggle_btn.setCheckable(True)
        advanced_toggle_btn.setMaximumWidth(300)
        layout.addWidget(advanced_toggle_btn, alignment=Qt.AlignCenter)
        
        # Collect component references
        components = {
            'select_folder_btn': select_folder_btn,
            'folder_status_label': folder_status_label,
            'go_button': go_button,
            'cancel_button': cancel_button,
            'advanced_toggle_btn': advanced_toggle_btn
        }
        
        return panel, components
    
    @staticmethod
    def create_progress_section() -> Tuple[QWidget, dict]:
        """Create progress monitoring and results display section.
        
        Returns:
            Tuple of (widget, components_dict) with references to UI elements.
        """
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setSpacing(15)
        
        # Progress Bar
        progress_layout = QHBoxLayout()
        progress_label = QLabel("Progress:")
        progress_label.setStyleSheet("font-weight: bold; color: white;")
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)
        progress_bar.setMinimumHeight(30)
        progress_layout.addWidget(progress_label)
        progress_layout.addWidget(progress_bar, 1)
        
        # Status Label
        status_label = QLabel("Ready to start analysis")
        status_label.setStyleSheet("color: #a0a0a0; font-size: 11pt; padding: 5px;")
        status_label.setWordWrap(True)
        
        layout.addLayout(progress_layout)
        layout.addWidget(status_label)
        
        # Results Tabs
        results_tabs = QTabWidget()
        results_tabs.setObjectName("resultsTabs")
        
        # Tab 1: Optimization Progress (Real-time table + graphs)
        results_table = ResultsTable()
        results_plotter = ResultsPlotter()
        
        progress_tab = QWidget()
        progress_tab_layout = QVBoxLayout(progress_tab)
        progress_tab_layout.addWidget(results_table, 1)
        progress_tab_layout.addWidget(results_plotter, 1)
        results_tabs.addTab(progress_tab, "📈 Optimization Progress")
        
        # Tab 2: Contact Distribution Histogram
        contact_histogram_widget = MplWidget()
        contact_histogram_widget.setMinimumHeight(400)
        
        contact_placeholder = QWidget()
        contact_placeholder_layout = QVBoxLayout(contact_placeholder)
        contact_placeholder_label = QLabel("📊 Particle contact distribution will appear here after analysis completes")
        contact_placeholder_label.setAlignment(Qt.AlignCenter)
        contact_placeholder_label.setStyleSheet("color: #808080; font-size: 12pt;")
        contact_placeholder_layout.addWidget(contact_placeholder_label)
        
        contact_histogram_widget.layout().addWidget(contact_placeholder)
        results_tabs.addTab(contact_histogram_widget, "📊 Contact Distribution")
        
        # Tab 3: Particle Volume Distribution Histogram
        volume_histogram_widget = MplWidget()
        volume_histogram_widget.setMinimumHeight(400)
        
        volume_placeholder = QWidget()
        volume_placeholder_layout = QVBoxLayout(volume_placeholder)
        volume_placeholder_label = QLabel("📊 Particle volume distribution will appear here after analysis completes")
        volume_placeholder_label.setAlignment(Qt.AlignCenter)
        volume_placeholder_label.setStyleSheet("color: #808080; font-size: 12pt;")
        volume_placeholder_layout.addWidget(volume_placeholder_label)
        
        volume_histogram_widget.layout().addWidget(volume_placeholder)
        results_tabs.addTab(volume_histogram_widget, "📊 Volume Distribution")
        
        layout.addWidget(results_tabs, 1)
        
        # View 3D Button
        view_3d_btn = QPushButton("🔍 VIEW 3D RESULTS")
        view_3d_btn.setObjectName("view3DButton")
        view_3d_btn.setMinimumHeight(50)
        view_3d_btn.setEnabled(False)
        layout.addWidget(view_3d_btn)
        
        components = {
            'progress_bar': progress_bar,
            'status_label': status_label,
            'results_tabs': results_tabs,
            'results_table': results_table,
            'results_plotter': results_plotter,
            'contact_histogram_widget': contact_histogram_widget,
            'volume_histogram_widget': volume_histogram_widget,
            'view_3d_btn': view_3d_btn
        }
        
        return section, components
    
    @staticmethod
    def create_advanced_section() -> Tuple[QWidget, dict]:
        """Create advanced settings section (initially hidden).
        
        Returns:
            Tuple of (widget, components_dict) with configuration controls.
        """
        section = QGroupBox("⚙️ Advanced Configuration")
        section.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #5a9bd3;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QGridLayout(section)
        layout.setSpacing(15)
        
        # Max Radius Setting
        max_radius_label = QLabel("Maximum Erosion Radius:")
        max_radius_label.setToolTip(
            "Maximum radius to test (pixels).\n"
            "Larger values may find better results but take longer."
        )
        
        max_radius_spinbox = QSpinBox()
        max_radius_spinbox.setRange(5, 20)
        max_radius_spinbox.setValue(DEFAULT_MAX_RADIUS)
        max_radius_spinbox.setSuffix(" pixels")
        
        radius_preview_label = QLabel()
        radius_preview_label.setStyleSheet("color: #808080; font-size: 9pt; font-style: italic;")
        
        layout.addWidget(max_radius_label, 0, 0)
        layout.addWidget(max_radius_spinbox, 0, 1)
        layout.addWidget(radius_preview_label, 1, 0, 1, 2)
        
        # Connectivity Setting
        connectivity_label = QLabel("Connectivity:")
        connectivity_label.setToolTip(
            "Neighborhood connectivity for particle splitting.\n"
            "6: Face neighbors only (conservative)\n"
            "26: Full 3D neighborhood (aggressive)"
        )
        
        connectivity_combo = QComboBox()
        for conn_value, conn_name in CONNECTIVITY_NAMES.items():
            connectivity_combo.addItem(conn_name, conn_value)
        connectivity_combo.setCurrentIndex(0)  # Default to 6-connectivity
        
        connectivity_desc_label = QLabel()
        connectivity_desc_label.setStyleSheet("color: #808080; font-size: 9pt; font-style: italic;")
        connectivity_desc_label.setWordWrap(True)
        
        layout.addWidget(connectivity_label, 2, 0)
        layout.addWidget(connectivity_combo, 2, 1)
        layout.addWidget(connectivity_desc_label, 3, 0, 1, 2)
        
        components = {
            'max_radius_spinbox': max_radius_spinbox,
            'radius_preview_label': radius_preview_label,
            'connectivity_combo': connectivity_combo,
            'connectivity_desc_label': connectivity_desc_label
        }
        
        return section, components


__all__ = ['UIComponentBuilder']

