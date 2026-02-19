"""Configuration constants for GUI components.

This module contains all GUI-related constants and configuration values
to avoid magic numbers and improve maintainability.
"""

# === Window Configuration ===
WINDOW_TITLE = "3D Particle Analysis Pipeline"
WINDOW_MIN_WIDTH = 1400
WINDOW_MIN_HEIGHT = 900
WINDOW_DEFAULT_WIDTH = 1600
WINDOW_DEFAULT_HEIGHT = 1000

# === UI Styling ===
TITLE_FONT_SIZE = 16
INSTRUCTION_FONT_SIZE = 11
TITLE_COLOR = "#5a9bd3"
INSTRUCTION_COLOR = "#a0a0a0"
SUCCESS_COLOR = "#5cb85c"
ERROR_COLOR = "#d9534f"
PROGRESS_COLOR = "#5a9bd3"

# === Layout Spacing ===
MAIN_LAYOUT_SPACING = 20
MAIN_LAYOUT_MARGINS = (30, 30, 30, 30)
SECTION_SPACING = 15
BUTTON_MIN_HEIGHT = 40

# === Default Analysis Parameters ===
DEFAULT_MAX_RADIUS = 7
DEFAULT_MIN_RADIUS = 1
DEFAULT_CONNECTIVITY = 6  # 6-neighborhood (face contact)

# === Progress Bar Configuration ===
PROGRESS_BAR_HEIGHT = 30
PROGRESS_PERCENTAGE_MIN = 0
PROGRESS_PERCENTAGE_MAX = 100
OPTIMIZATION_PROGRESS_MAX = 90  # Reserve 10% for finalization

# === File Formats ===
SUPPORTED_TIF_FORMATS = ["*.tif", "*.tiff", "*.TIF", "*.TIFF"]
SUPPORTED_IMAGE_FORMATS = ["*.png", "*.jpg", "*.jpeg", "*.tif", "*.tiff", "*.bmp"]

# === Output File Names ===
OUTPUT_CSV_NAME = "optimization_results.csv"
OUTPUT_SUMMARY_NAME = "optimization_summary.txt"
OUTPUT_BEST_LABELS_NAME = "best_labels.npy"
OUTPUT_VOLUME_NAME = "volume.npy"

# === Napari Configuration ===
NAPARI_VOLUME_OPACITY = 0.3
NAPARI_LABELS_OPACITY = 0.8
NAPARI_VOLUME_COLORMAP = "gray"
NAPARI_DEFAULT_CAMERA_ANGLES = (45, 45, 45)
NAPARI_NDISPLAY_3D = 3

# === Guard Volume Visualization ===
NAPARI_GUARD_BOUNDARY_OPACITY = 0.3
NAPARI_GUARD_BOUNDARY_COLORMAP = "green"
NAPARI_BOUNDARY_PARTICLES_OPACITY = 0.15
NAPARI_GUARD_SHELL_THICKNESS = 2  # voxels

# === Stage Names (for progress tracking) ===
STAGE_INITIALIZATION = "initialization"
STAGE_OPTIMIZATION = "optimization"
STAGE_FINALIZATION = "finalization"

STAGE_TEXT_MAP = {
    STAGE_INITIALIZATION: "🔄 初期化中...",
    STAGE_OPTIMIZATION: "⚙️ 最適化実行中...",
    STAGE_FINALIZATION: "🎯 最適r選定中...",
}

# === Connectivity Names (for display) ===
CONNECTIVITY_NAMES = {
    6: "6-Neighborhood (Face)",
    26: "26-Neighborhood (Full)",
}

# === Metrics Display Configuration ===
METRICS_DECIMAL_PLACES = {
    'hhi': 3,
    'knee_dist': 1,
    'vi_stability': 3,
    'mean_contacts': 1,
    'largest_particle_ratio': 3,
    'foreground_ratio': 2,
}

__all__ = [
    'WINDOW_TITLE',
    'WINDOW_MIN_WIDTH',
    'WINDOW_MIN_HEIGHT',
    'WINDOW_DEFAULT_WIDTH',
    'WINDOW_DEFAULT_HEIGHT',
    'DEFAULT_MAX_RADIUS',
    'DEFAULT_CONNECTIVITY',
    'SUPPORTED_TIF_FORMATS',
    'OUTPUT_CSV_NAME',
    'OUTPUT_SUMMARY_NAME',
    'OUTPUT_BEST_LABELS_NAME',
    'OUTPUT_VOLUME_NAME',
    'NAPARI_VOLUME_OPACITY',
    'NAPARI_LABELS_OPACITY',
    'NAPARI_DEFAULT_CAMERA_ANGLES',
    'STAGE_TEXT_MAP',
    'CONNECTIVITY_NAMES',
]

