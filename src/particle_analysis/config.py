"""Configuration settings for the particle analysis pipeline."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PostprocessConfig:
    """Configuration for mask postprocessing."""
    closing_radius: int = 0  # Binary closing radius (0 = disabled)
    min_object_size: int = 50  # Minimum object size for removal
    clahe_clip_limit: float = 2.0  # CLAHE clip limit
    clahe_tile_size: tuple = (8, 8)  # CLAHE tile grid size
    gaussian_kernel: tuple = (5, 5)  # Gaussian blur kernel size
    invert_default: bool = False  # Default inversion setting


@dataclass
class LabelingConfig:
    """Configuration for 3D labeling."""
    connectivity: int = 6  # Default connectivity (6, 18, or 26)
    expected_slices: int = 196  # Expected number of CT slices


@dataclass
class SplittingConfig:
    """Configuration for particle splitting."""
    erosion_radius: int = 2  # Default erosion radius
    connectivity: int = 6  # Connectivity for labeling
    min_particles: int = 100  # Minimum expected particles
    max_particles: int = 5000  # Maximum expected particles


@dataclass
class ContactConfig:
    """Configuration for contact analysis."""
    auto_exclude_threshold: int = 1000  # Auto-exclude particles with > N contacts
    max_reasonable_contacts: int = 50  # Maximum reasonable contacts per particle
    histogram_bins: int = 30  # Number of histogram bins


@dataclass
class VisualizationConfig:
    """Configuration for visualization."""
    figure_size: tuple = (10, 6)  # Default figure size
    dpi: int = 300  # Figure DPI
    colormap_labels: str = 'gist_ncar'  # Colormap for labels
    colormap_mask: str = 'gray'  # Colormap for masks


@dataclass
class PipelineConfig:
    """Main pipeline configuration."""
    postprocess: PostprocessConfig = None
    labeling: LabelingConfig = None
    splitting: SplittingConfig = None
    contact: ContactConfig = None
    visualization: VisualizationConfig = None
    
    def __post_init__(self):
        if self.postprocess is None:
            self.postprocess = PostprocessConfig()
        if self.labeling is None:
            self.labeling = LabelingConfig()
        if self.splitting is None:
            self.splitting = SplittingConfig()
        if self.contact is None:
            self.contact = ContactConfig()
        if self.visualization is None:
            self.visualization = VisualizationConfig()
    
    # Global settings
    random_seed: Optional[int] = 42
    verbose: bool = True
    
    @classmethod
    def load_from_file(cls, config_path: str) -> 'PipelineConfig':
        """Load configuration from YAML file."""
        try:
            import yaml
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
            # TODO: Implement YAML loading logic
            return cls()
        except ImportError:
            raise ImportError("PyYAML required for config file loading")
    
    def save_to_file(self, config_path: str) -> None:
        """Save configuration to YAML file."""
        try:
            import yaml
            with open(config_path, 'w') as f:
                yaml.dump(self.__dict__, f, default_flow_style=False)
        except ImportError:
            raise ImportError("PyYAML required for config file saving")


# Default configuration instance
DEFAULT_CONFIG = PipelineConfig() 