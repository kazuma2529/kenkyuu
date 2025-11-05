"""GUI widgets for displaying analysis results.

This module contains specialized Qt widgets for displaying optimization
results in tabular and graphical formats, plus research-oriented histogram plots.
"""

import logging
from typing import List, Dict, Optional

import numpy as np
from qtpy.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QLabel
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

logger = logging.getLogger(__name__)


class MplWidget(QWidget):
    """Simple Matplotlib canvas widget for embedding plots in Qt.
    
    This widget provides a dark-themed matplotlib canvas that integrates
    seamlessly with the application's dark theme.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_canvas()
    
    def setup_canvas(self):
        """Setup matplotlib canvas with dark theme."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create matplotlib figure
        self.figure = Figure(figsize=(8, 6), facecolor='#2c313a')
        self.canvas = FigureCanvas(self.figure)
        
        # Apply dark theme
        self.canvas.figure.patch.set_facecolor('#2c313a')
        
        layout.addWidget(self.canvas)
        self.setLayout(layout)
    
    def clear(self):
        """Clear the figure."""
        self.figure.clear()
        self.canvas.draw()


class ResultsTable(QTableWidget):
    """Table widget for displaying optimization results."""
    
    def __init__(self):
        super().__init__()
        self.setup_table()
    
    def setup_table(self):
        """Setup table headers and formatting."""
        headers = [
            "Radius", "Particles", "Mean Contacts", "Largest Particle (%)",
            "Processing Time (s)", "Status"
        ]
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        
        # Set column widths
        self.setColumnWidth(0, 60)   # Radius
        self.setColumnWidth(1, 80)   # Particles
        self.setColumnWidth(2, 110)  # Mean Contacts
        self.setColumnWidth(3, 130)  # Largest Particle (%)
        self.setColumnWidth(4, 130)  # Processing Time
        self.setColumnWidth(5, 100)  # Status
        
        # Enable selection
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setAlternatingRowColors(True)
    
    def add_result(self, result, new_metrics: Dict = None, is_best: bool = False):
        """Add a new result row to the table."""
        row = self.rowCount()
        self.insertRow(row)
        
        # Get largest_particle_ratio (default to 0.0 if not available)
        largest_ratio = getattr(result, 'largest_particle_ratio', 0.0)
        
        # Add data
        self.setItem(row, 0, QTableWidgetItem(str(result.radius)))
        self.setItem(row, 1, QTableWidgetItem(str(result.particle_count)))
        self.setItem(row, 2, QTableWidgetItem(f"{result.mean_contacts:.1f}"))
        self.setItem(row, 3, QTableWidgetItem(f"{largest_ratio * 100:.1f}"))  # Convert to percentage
        self.setItem(row, 4, QTableWidgetItem(f"{result.processing_time:.1f}"))
        
        # Status (now last column)
        if is_best:
            self.setItem(row, 5, QTableWidgetItem("★ OPTIMAL"))
        else:
            self.setItem(row, 5, QTableWidgetItem("Computed"))
        
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
        from .metrics_calculator import MetricsCalculator
        
        try:
            return MetricsCalculator.calculate_metrics_for_plots(results_data)
        except Exception as e:
            logger.warning(f"Failed to calculate plot metrics: {e}")
            return [{'hhi': 0.0, 'knee_dist': 0.0, 'vi': 0.0} for _ in results_data]

class HistogramPlotter:
    """Utility class for plotting histograms on matplotlib widgets."""
    
    @staticmethod
    def plot_contact_histogram(mpl_widget: MplWidget, contact_data: Dict) -> None:
        """Plot contact number distribution histogram.
        
        Args:
            mpl_widget: MplWidget to plot on
            contact_data: Dict with keys 'values' (list of contact counts),
                          'min', 'max', 'mean', 'median'
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if not contact_data or 'values' not in contact_data:
            logger.warning("Invalid contact histogram data")
            return
        
        try:
            # Clear previous plot
            mpl_widget.clear()
            
            # Create subplot
            ax = mpl_widget.figure.add_subplot(111)
            
            # Plot histogram
            values = contact_data['values']
            min_contact = int(min(values))
            max_contact = int(max(values))
            
            # Calculate appropriate bin range
            # Use integer bins for contact counts (each bin represents one contact number)
            bin_range = range(min_contact, max_contact + 2)  # +2 to include max value
            
            # Plot histogram with proper binning
            n, bins, patches = ax.hist(values, bins=bin_range, 
                                      color='#5a9bd3', edgecolor='white', alpha=0.8)
            
            # Add mean and median lines
            mean_val = contact_data.get('mean', np.mean(values))
            median_val = contact_data.get('median', np.median(values))
            
            ax.axvline(mean_val, color='#5cb85c', linestyle='--', linewidth=2, 
                      label=f'Mean: {mean_val:.1f}')
            ax.axvline(median_val, color='#f0ad4e', linestyle='--', linewidth=2, 
                      label=f'Median: {median_val:.1f}')
            
            # Add reference lines for 6-neighborhood
            if mean_val < 15:  # Likely 6-neighborhood
                ax.axvline(6.0, color='green', linestyle=':', linewidth=2, alpha=0.5, 
                          label='Theory (Random Close Pack): 6.0')
            
            # Set X-axis limits to fit the data with small padding
            # Use max of (data_max, theory_line, mean+some_padding) to ensure visibility
            x_max = max(max_contact, mean_val * 1.5, 6.0 if mean_val < 15 else 0)
            x_max = int(x_max) + 2  # Add small padding
            ax.set_xlim(-0.5, x_max)  # -0.5 to show the first bin properly
            
            # Styling
            ax.set_xlabel('Number of Contacts per Particle', fontsize=12, color='white')
            ax.set_ylabel('Frequency (Particle Count)', fontsize=12, color='white')
            ax.set_title('Contact Number Distribution', fontsize=14, fontweight='bold', color='white')
            ax.legend(facecolor='#23272e', edgecolor='white', fontsize=10)
            ax.grid(True, alpha=0.3, color='white')
            
            # Set integer ticks on X-axis for better readability
            # Show ticks every 1 unit if range is small, otherwise every 2-5 units
            if x_max <= 10:
                tick_step = 1
            elif x_max <= 20:
                tick_step = 2
            else:
                tick_step = max(2, x_max // 10)
            ax.set_xticks(range(0, x_max + 1, tick_step))
            
            # Dark theme styling
            ax.set_facecolor('#2c313a')
            ax.spines['bottom'].set_color('white')
            ax.spines['top'].set_color('white')
            ax.spines['left'].set_color('white')
            ax.spines['right'].set_color('white')
            ax.tick_params(colors='white')
            
            mpl_widget.figure.tight_layout()
            mpl_widget.canvas.draw()
            
            logger.info(f"✅ Plotted contact histogram: {len(values)} particles, mean={mean_val:.2f}")
        
        except Exception as e:
            logger.error(f"Failed to plot contact histogram: {e}")
            import traceback
            traceback.print_exc()
    
    @staticmethod
    def plot_volume_histogram(mpl_widget: MplWidget, volume_data: Dict) -> None:
        """Plot particle volume distribution histogram.
        
        Args:
            mpl_widget: MplWidget to plot on
            volume_data: Dict with keys 'values' (list of volumes),
                         'min', 'max', 'mean', 'median'
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if not volume_data or 'values' not in volume_data:
            logger.warning("Invalid volume histogram data")
            return
        
        try:
            # Clear previous plot
            mpl_widget.clear()
            
            # Create subplot
            ax = mpl_widget.figure.add_subplot(111)
            
            # Plot histogram with logarithmic bins for better visualization
            values = volume_data['values']
            ax.hist(values, bins=50, color='#d9534f', edgecolor='white', alpha=0.8)
            
            # Add mean and median lines
            mean_val = volume_data.get('mean', np.mean(values))
            median_val = volume_data.get('median', np.median(values))
            
            ax.axvline(mean_val, color='#5cb85c', linestyle='--', linewidth=2, 
                      label=f'Mean: {mean_val:.0f} voxels')
            ax.axvline(median_val, color='#f0ad4e', linestyle='--', linewidth=2, 
                      label=f'Median: {median_val:.0f} voxels')
            
            # Styling
            ax.set_xlabel('Particle Volume (voxels)', fontsize=12, color='white')
            ax.set_ylabel('Frequency (Particle Count)', fontsize=12, color='white')
            ax.set_title('Particle Volume Distribution', fontsize=14, fontweight='bold', color='white')
            ax.legend(facecolor='#23272e', edgecolor='white', fontsize=10)
            ax.grid(True, alpha=0.3, color='white')
            
            # Dark theme styling
            ax.set_facecolor('#2c313a')
            ax.spines['bottom'].set_color('white')
            ax.spines['top'].set_color('white')
            ax.spines['left'].set_color('white')
            ax.spines['right'].set_color('white')
            ax.tick_params(colors='white')
            
            # Add statistics text
            stats_text = (
                f"Total Particles: {len(values)}\n"
                f"Range: [{volume_data['min']}, {volume_data['max']}]"
            )
            ax.text(0.98, 0.98, stats_text, transform=ax.transAxes, 
                   verticalalignment='top', horizontalalignment='right',
                   bbox=dict(boxstyle='round', facecolor='#23272e', alpha=0.8, edgecolor='white'),
                   fontsize=9, color='white')
            
            mpl_widget.figure.tight_layout()
            mpl_widget.canvas.draw()
            
            logger.info(f"✅ Plotted volume histogram: {len(values)} particles, mean={mean_val:.0f}")
        
        except Exception as e:
            logger.error(f"Failed to plot volume histogram: {e}")
            import traceback
            traceback.print_exc()


__all__ = ["MplWidget", "ResultsTable", "ResultsPlotter", "HistogramPlotter"] 


class OptimizationCurvesPlot(MplWidget):
    """Simple 2-panel plot: particle_count and largest_particle_ratio vs radius.
    Shows a vertical line at selected radius and a horizontal line at τratio on the ratio panel.
    """

    def plot(self, results: list, selected_radius: int | None = None, tau_ratio: float | None = None):
        self.clear()
        if not results:
            return

        ax1 = self.figure.add_subplot(2, 1, 1)
        ax2 = self.figure.add_subplot(2, 1, 2)

        radii = [r.radius for r in results]
        counts = [r.particle_count for r in results]
        lpr = [getattr(r, 'largest_particle_ratio', 0.0) for r in results]

        # Panel 1: particle_count
        ax1.plot(radii, counts, 'o-', color='#5a9bd3', label='particle_count')
        ax1.set_title('Particle Count vs Radius', color='white')
        ax1.set_xlabel('Radius', color='white')
        ax1.set_ylabel('Particle Count', color='white')
        ax1.grid(True, alpha=0.3, color='white')

        # Panel 2: largest_particle_ratio
        ax2.plot(radii, lpr, 'o-', color='#d9534f', label='largest_particle_ratio')
        ax2.set_title('Largest Particle Ratio vs Radius', color='white')
        ax2.set_xlabel('Radius', color='white')
        ax2.set_ylabel('Largest Ratio', color='white')
        ax2.grid(True, alpha=0.3, color='white')
        if tau_ratio is not None:
            ax2.axhline(y=float(tau_ratio), color='orange', linestyle='--', alpha=0.8, label=f'τratio={float(tau_ratio):.3f}')

        # Vertical line at selected radius
        if selected_radius is not None:
            for ax in (ax1, ax2):
                ax.axvline(x=int(selected_radius), color='white', linestyle=':', alpha=0.8, label=f'r*={selected_radius}')

        # Dark theme ticks/spines
        for ax in (ax1, ax2):
            ax.set_facecolor('#2c313a')
            for side in ('bottom', 'top', 'left', 'right'):
                ax.spines[side].set_color('white')
            ax.tick_params(colors='white')
            ax.legend(facecolor='#23272e', edgecolor='white', fontsize=9)

        self.figure.tight_layout()
        self.canvas.draw()


__all__.append("OptimizationCurvesPlot")