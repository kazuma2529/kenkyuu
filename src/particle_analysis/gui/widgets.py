"""GUI widgets for displaying analysis results.

This module contains specialized Qt widgets for displaying optimization
results in tabular and graphical formats with new Pareto+distance indicators.
"""

import logging
from typing import List, Dict

import numpy as np
from qtpy.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem
from qtpy.QtGui import QColor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

logger = logging.getLogger(__name__)


class ResultsTable(QTableWidget):
    """Table widget for displaying optimization results."""
    
    def __init__(self):
        super().__init__()
        self.setup_table()
    
    def setup_table(self):
        """Setup table headers and formatting."""
        headers = [
            "Radius", "Particles", "Mean Contacts", "HHI", "Knee Dist", 
            "VI Stability", "Processing Time (s)", "Status"
        ]
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        
        # Set column widths
        self.setColumnWidth(0, 60)   # Radius
        self.setColumnWidth(1, 80)   # Particles
        self.setColumnWidth(2, 100)  # Mean Contacts
        self.setColumnWidth(3, 80)   # HHI
        self.setColumnWidth(4, 80)   # Knee Distance
        self.setColumnWidth(5, 90)   # VI Stability
        self.setColumnWidth(6, 130)  # Processing Time
        self.setColumnWidth(7, 100)  # Status
        
        # Enable selection
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setAlternatingRowColors(True)
    
    def add_result(self, result, new_metrics: Dict = None, is_best: bool = False):
        """Add a new result row to the table."""
        row = self.rowCount()
        self.insertRow(row)
        
        # Default metrics if not provided
        if new_metrics is None:
            new_metrics = {'hhi': 0.0, 'knee_dist': 0.0, 'vi_stability': 0.0}
        
        # Add data
        self.setItem(row, 0, QTableWidgetItem(str(result.radius)))
        self.setItem(row, 1, QTableWidgetItem(str(result.particle_count)))
        self.setItem(row, 2, QTableWidgetItem(f"{result.mean_contacts:.1f}"))
        self.setItem(row, 3, QTableWidgetItem(f"{new_metrics.get('hhi', 0.0):.3f}"))
        self.setItem(row, 4, QTableWidgetItem(f"{new_metrics.get('knee_dist', 0.0):.1f}"))
        self.setItem(row, 5, QTableWidgetItem(f"{new_metrics.get('vi_stability', 0.0):.3f}"))
        self.setItem(row, 6, QTableWidgetItem(f"{result.processing_time:.1f}"))
        
        # Status
        if is_best:
            self.setItem(row, 7, QTableWidgetItem("★ OPTIMAL"))
        elif new_metrics.get('hhi', 1.0) > 0.5:
            self.setItem(row, 7, QTableWidgetItem("Under-segmented"))
        elif new_metrics.get('hhi', 0.0) < 0.01:
            self.setItem(row, 7, QTableWidgetItem("Well-segmented"))
        else:
            self.setItem(row, 7, QTableWidgetItem("Partial"))
        
        # Highlight best result
        if is_best:
            for col in range(self.columnCount()):
                item = self.item(row, col)
                if item:
                    item.setBackground(QColor(255, 215, 0))  # Gold
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
    
    def clear_results(self):
        """Clear all results from the table."""
        self.setRowCount(0)


class ResultsPlotter(QWidget):
    """Widget for plotting optimization results."""
    
    def __init__(self):
        super().__init__()
        self.setup_plots()
        self.results_data = []
    
    def setup_plots(self):
        """Setup matplotlib plots."""
        layout = QVBoxLayout(self)
        
        # Create figure with subplots (wider for 2x3 grid)
        self.figure = Figure(figsize=(15, 8))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # Create subplots (2x3 grid to accommodate Mean Contacts)
        self.ax1 = self.figure.add_subplot(2, 3, 1)
        self.ax2 = self.figure.add_subplot(2, 3, 2)
        self.ax3 = self.figure.add_subplot(2, 3, 3)
        self.ax4 = self.figure.add_subplot(2, 3, 4)
        self.ax5 = self.figure.add_subplot(2, 3, 5)
        
        self.figure.tight_layout(pad=3.0)
        
        # Initialize plots
        self.clear_plots()
    
    def clear_plots(self):
        """Clear all plots."""
        for ax in [self.ax1, self.ax2, self.ax3, self.ax4, self.ax5]:
            ax.clear()
        
        # New plots based on Pareto+distance method
        self.ax1.set_title("HHI Dominance Index vs Radius")
        self.ax1.set_xlabel("Erosion Radius")
        self.ax1.set_ylabel("HHI (lower = better)")
        self.ax1.axhline(y=0.01, color='green', linestyle='--', alpha=0.7, label='Ideal threshold')
        self.ax1.axhline(y=0.5, color='red', linestyle='--', alpha=0.7, label='Under-segmented')
        self.ax1.grid(True, alpha=0.3)
        self.ax1.legend()
        
        self.ax2.set_title("Knee Point Distance vs Radius")
        self.ax2.set_xlabel("Erosion Radius")
        self.ax2.set_ylabel("Distance from Knee Point")
        self.ax2.grid(True, alpha=0.3)
        
        self.ax3.set_title("VI Stability vs Radius")
        self.ax3.set_xlabel("Erosion Radius")
        self.ax3.set_ylabel("Variation of Information")
        self.ax3.axhline(y=1.0, color='orange', linestyle='--', alpha=0.7, label='Stability threshold')
        self.ax3.grid(True, alpha=0.3)
        self.ax3.legend()
        
        self.ax4.set_title("Mean Contacts vs Radius")
        self.ax4.set_xlabel("Erosion Radius")
        self.ax4.set_ylabel("Mean Contacts per Particle")
        self.ax4.axhline(y=6.0, color='green', linestyle='--', alpha=0.7, label='Target min (6)')
        self.ax4.axhline(y=8.0, color='orange', linestyle='--', alpha=0.7, label='Target max (8)')
        self.ax4.grid(True, alpha=0.3)
        self.ax4.legend()
        
        self.ax5.set_title("Pareto Frontier (3D Objectives)")
        self.ax5.set_xlabel("HHI Dominance")
        self.ax5.set_ylabel("Knee Distance")
        self.ax5.grid(True, alpha=0.3)
        
        self.canvas.draw()
    
    def update_plots(self, results_data: List, best_radius: int = None, new_metrics_data: List[Dict] = None):
        """Update plots with new data using Pareto+distance indicators."""
        if not results_data:
            return
        
        self.results_data = results_data
        
        # Extract basic data
        radii = [r.radius for r in results_data]
        particle_counts = [r.particle_count for r in results_data]
        
        # Calculate new metrics if not provided
        if new_metrics_data is None:
            new_metrics_data = self._calculate_new_metrics(results_data)
        
        # Extract new metric values
        hhi_values = [m.get('hhi', 0.0) for m in new_metrics_data]
        knee_distances = [m.get('knee_dist', 0.0) for m in new_metrics_data]
        vi_values = [m.get('vi_stability', 0.0) for m in new_metrics_data]
        
        # Clear and plot
        self.clear_plots()
        
        # Plot 1: HHI Dominance
        self.ax1.plot(radii, hhi_values, 'bo-', linewidth=2, markersize=6, label='HHI Index')
        if best_radius:
            best_idx = next((i for i, r in enumerate(results_data) if r.radius == best_radius), None)
            if best_idx is not None:
                self.ax1.plot(best_radius, hhi_values[best_idx], 'ro', markersize=12, 
                             label=f'★ Optimal (r={best_radius})')
        self.ax1.legend()
        
        # Plot 2: Knee Distance
        self.ax2.plot(radii, knee_distances, 'go-', linewidth=2, markersize=6, label='Knee Distance')
        if best_radius:
            best_idx = next((i for i, r in enumerate(results_data) if r.radius == best_radius), None)
            if best_idx is not None:
                self.ax2.plot(best_radius, knee_distances[best_idx], 'ro', markersize=12)
        self.ax2.legend()
        
        # Plot 3: VI Stability
        self.ax3.plot(radii, vi_values, 'mo-', linewidth=2, markersize=6, label='VI Stability')
        if best_radius:
            best_idx = next((i for i, r in enumerate(results_data) if r.radius == best_radius), None)
            if best_idx is not None:
                self.ax3.plot(best_radius, vi_values[best_idx], 'ro', markersize=12)
        self.ax3.legend()
        
        # Plot 4: Mean Contacts
        mean_contacts = [r.mean_contacts for r in results_data]
        self.ax4.plot(radii, mean_contacts, 'co-', linewidth=2, markersize=6, label='Mean Contacts')
        if best_radius:
            best_idx = next((i for i, r in enumerate(results_data) if r.radius == best_radius), None)
            if best_idx is not None:
                self.ax4.plot(best_radius, mean_contacts[best_idx], 'ro', markersize=12, 
                             label=f'★ Optimal ({mean_contacts[best_idx]:.1f})')
        self.ax4.legend()
        
        # Plot 5: Pareto Frontier (2D projection)
        colors = ['red' if radii[i] == best_radius else 'blue' for i in range(len(radii))]
        sizes = [120 if radii[i] == best_radius else 50 for i in range(len(radii))]
        scatter = self.ax5.scatter(hhi_values, knee_distances, c=colors, s=sizes, alpha=0.7)
        
        # Add radius labels
        for i, r in enumerate(radii):
            self.ax5.annotate(f'r{r}', (hhi_values[i], knee_distances[i]), 
                            xytext=(5, 5), textcoords='offset points', fontsize=8)
        
        if best_radius:
            self.ax5.set_title(f"Pareto Frontier (★ Optimal: r={best_radius})")
        
        # Update layout and draw
        self.figure.tight_layout(pad=3.0)
        self.canvas.draw()
    
    def _calculate_new_metrics(self, results_data: List) -> List[Dict]:
        """Calculate metrics for plot visualization."""
        from ..volume.metrics import calculate_hhi, calculate_variation_of_information
        from ..volume.optimization.utils import detect_knee_point
        
        try:
            radii = [r.radius for r in results_data]
            particle_counts = [r.particle_count for r in results_data]
            
            # Detect knee point
            knee_idx = detect_knee_point(radii, particle_counts) if len(radii) >= 3 else 0
            knee_radius = radii[knee_idx]
            
            metrics_list = []
            for i, result in enumerate(results_data):
                # HHI
                hhi = 0.0
                if hasattr(result, 'labels_path') and result.labels_path:
                    try:
                        labels = np.load(result.labels_path)
                        hhi = calculate_hhi(labels)
                    except:
                        hhi = result.largest_particle_ratio
                
                # Knee distance
                knee_dist = abs(result.radius - knee_radius)
                
                # VI stability
                vi_stability = 0.5
                if i > 0 and hasattr(result, 'labels_path') and result.labels_path:
                    prev_result = results_data[i-1]
                    if hasattr(prev_result, 'labels_path') and prev_result.labels_path:
                        try:
                            current_labels = np.load(result.labels_path)
                            prev_labels = np.load(prev_result.labels_path)
                            vi_stability = calculate_variation_of_information(prev_labels, current_labels)
                        except:
                            pass
                
                metrics_list.append({
                    'hhi': hhi,
                    'knee_dist': knee_dist,
                    'vi_stability': vi_stability
                })
            
            return metrics_list
            
        except Exception as e:
            logger.warning(f"Failed to calculate plot metrics: {e}")
            return [{'hhi': 0.0, 'knee_dist': 0.0, 'vi_stability': 0.0} for _ in results_data]

__all__ = ["ResultsTable", "ResultsPlotter"] 