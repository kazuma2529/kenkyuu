import sys
from qtpy.QtWidgets import QApplication

from particle_analysis.gui.widgets import OptimizationCurvesPlot
from particle_analysis.volume.data_structures import OptimizationResult


def _ensure_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_optimization_curves_plot_renders_without_error(qtbot=None):
    _ensure_app()
    widget = OptimizationCurvesPlot()

    # Prepare synthetic results covering several radii
    results = [
        OptimizationResult(radius=1, particle_count=50,  mean_contacts=2.0, largest_particle_ratio=0.80),
        OptimizationResult(radius=2, particle_count=120, mean_contacts=3.5, largest_particle_ratio=0.20),
        OptimizationResult(radius=3, particle_count=300, mean_contacts=6.0, largest_particle_ratio=0.04),
        OptimizationResult(radius=4, particle_count=302, mean_contacts=6.5, largest_particle_ratio=0.03),
    ]

    # Should not raise
    widget.plot(results, selected_radius=4, tau_ratio=0.05)

    # Basic assertions on internal figure state
    assert widget.figure is not None
    # Two axes should have been added
    assert len(widget.figure.axes) == 2


