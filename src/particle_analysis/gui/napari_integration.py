"""Napari 3D visualization integration.

This module provides a clean interface for opening and managing Napari viewers
from the GUI, with proper error handling and resource management.
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np

from .config import (
    NAPARI_VOLUME_OPACITY,
    NAPARI_LABELS_OPACITY,
    NAPARI_VOLUME_COLORMAP,
    NAPARI_DEFAULT_CAMERA_ANGLES,
    NAPARI_NDISPLAY_3D,
)

logger = logging.getLogger(__name__)

# Try to import napari
try:
    import napari
    NAPARI_AVAILABLE = True
except ImportError:
    napari = None
    NAPARI_AVAILABLE = False


class NapariViewerManager:
    """Manage Napari viewer instances for 3D visualization."""
    
    def __init__(self):
        self.viewer: Optional['napari.Viewer'] = None
    
    def is_napari_available(self) -> bool:
        """Check if Napari is available."""
        return NAPARI_AVAILABLE
    
    def is_viewer_valid(self) -> bool:
        """Check if the current viewer is still valid."""
        if self.viewer is None:
            return False
        
        try:
            # Try to access the viewer to check if it's still valid
            _ = self.viewer.layers
            return True
        except (RuntimeError, AttributeError):
            self.viewer = None
            return False
    
    def create_viewer(self, title: str) -> 'napari.Viewer':
        """Create a new Napari viewer.
        
        Args:
            title: Window title
            
        Returns:
            Napari Viewer instance
            
        Raises:
            RuntimeError: If Napari is not available
        """
        if not NAPARI_AVAILABLE:
            raise RuntimeError("Napari is not installed")
        
        self.viewer = napari.Viewer(title=title)
        
        # Note: Napari Viewer is a Pydantic model, so we can't set attributes directly
        # The viewer reference will be cleared automatically when is_viewer_valid() 
        # detects it's no longer valid (checked via viewer.layers access)
        
        return self.viewer
    
    def get_or_create_viewer(self, title: str) -> 'napari.Viewer':
        """Get existing viewer or create a new one.
        
        Args:
            title: Window title for new viewer
            
        Returns:
            Napari Viewer instance
        """
        if self.is_viewer_valid():
            # Clear existing layers
            self.viewer.layers.clear()
            return self.viewer
        else:
            return self.create_viewer(title)
    
    def load_best_labels(
        self,
        best_labels_path: Path,
        volume_path: Optional[Path] = None,
        best_radius: int = 0,
        metadata: Optional[dict] = None
    ) -> 'napari.Viewer':
        """Load best optimization result in Napari viewer.
        
        Args:
            best_labels_path: Path to best_labels.npy file
            volume_path: Optional path to volume.npy for background
            best_radius: Best radius value for display
            metadata: Optional metadata dictionary
            
        Returns:
            Napari Viewer instance
            
        Raises:
            FileNotFoundError: If required files don't exist
            RuntimeError: If Napari is not available
        """
        if not NAPARI_AVAILABLE:
            raise RuntimeError("Napari is not installed")
        
        if not best_labels_path.exists():
            raise FileNotFoundError(f"Labels file not found: {best_labels_path}")
        
        # Load data
        best_labels = np.load(best_labels_path)
        
        logger.info(f"Opening Napari with best result (r={best_radius})")
        logger.info(f"Labels shape: {best_labels.shape}")
        logger.info(f"Unique particles: {best_labels.max()}")
        
        # Create or reuse viewer
        title = f"3D Particle Analysis - Best Result (r={best_radius})"
        viewer = self.get_or_create_viewer(title)
        
        # Load volume if available (as background)
        if volume_path and volume_path.exists():
            volume = np.load(volume_path)
            viewer.add_image(
                volume,
                name="Binary Volume",
                rendering="mip",
                opacity=NAPARI_VOLUME_OPACITY,
                colormap=NAPARI_VOLUME_COLORMAP
            )
        
        # Load best labels (main layer)
        viewer.add_labels(
            best_labels,
            name=f"Optimized Particles (r={best_radius})",
            opacity=NAPARI_LABELS_OPACITY
        )
        
        # Log metadata if provided
        if metadata:
            metadata_text = "\n".join([f"{k}: {v}" for k, v in metadata.items()])
            logger.info(f"Best result metadata:\n{metadata_text}")
        
        # Set optimal view
        viewer.dims.ndisplay = NAPARI_NDISPLAY_3D  # 3D mode
        viewer.camera.angles = NAPARI_DEFAULT_CAMERA_ANGLES  # Nice viewing angle
        
        # Show viewer window
        viewer.window.show()
        
        logger.info("✅ Napari viewer opened successfully")
        
        return viewer
    
    def load_all_radii(
        self,
        output_dir: Path,
        volume_path: Path,
        radii: list,
        best_radius: Optional[int] = None
    ) -> 'napari.Viewer':
        """Load all radius results in Napari viewer.
        
        Args:
            output_dir: Output directory containing label files
            volume_path: Path to volume.npy
            radii: List of radii to load
            best_radius: Optional best radius to highlight
            
        Returns:
            Napari Viewer instance
        """
        if not NAPARI_AVAILABLE:
            raise RuntimeError("Napari is not installed")
        
        if not volume_path.exists():
            raise FileNotFoundError(f"Volume file not found: {volume_path}")
        
        # Create viewer
        title = "3D Particle Analysis - All Radii"
        viewer = self.get_or_create_viewer(title)
        
        # Load volume once
        volume = np.load(volume_path)
        viewer.add_image(
            volume,
            name="Binary Volume",
            rendering="mip",
            opacity=NAPARI_VOLUME_OPACITY,
            colormap=NAPARI_VOLUME_COLORMAP
        )
        
        # Load labels for each radius
        for r in sorted(radii):
            labels_path = output_dir / f"labels_r{r}.npy"
            
            if labels_path.exists():
                labels = np.load(labels_path)
                
                # Highlight best radius
                is_best = (r == best_radius) if best_radius else False
                layer_name = f"r={r}" + (" ⭐ BEST" if is_best else "")
                
                viewer.add_labels(
                    labels,
                    name=layer_name,
                    visible=is_best,  # Only show best by default
                    opacity=NAPARI_LABELS_OPACITY
                )
        
        # Set optimal view
        viewer.dims.ndisplay = NAPARI_NDISPLAY_3D
        viewer.camera.angles = NAPARI_DEFAULT_CAMERA_ANGLES
        viewer.window.show()
        
        logger.info(f"✅ Napari viewer opened with {len(radii)} radius results")
        
        return viewer


__all__ = ['NapariViewerManager', 'NAPARI_AVAILABLE']

