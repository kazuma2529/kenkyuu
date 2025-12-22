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
    
    def _create_contact_color_mapping(
        self, 
        contact_counts: dict[int, int]
    ) -> dict[int, tuple[float, float, float, float]]:
        """Create particle_id -> RGBA color mapping based on contact counts.
        
        Args:
            contact_counts: Dictionary mapping particle_id -> contact_count
            
        Returns:
            Dictionary mapping particle_id -> (R, G, B, A) tuple (0-1 range)
        """
        from ..contact.visualization import get_discrete_contact_colormap
        
        _, color_ranges = get_discrete_contact_colormap()
        
        labels_colors = {}
        for particle_id, contact_count in contact_counts.items():
            # Find which color range this contact count belongs to
            for min_contact, max_contact_range, name, color in color_ranges:
                if name == "Background":
                    continue
                if max_contact_range is None:
                    if contact_count >= min_contact:
                        labels_colors[particle_id] = (
                            float(color[0]), float(color[1]), float(color[2]), 1.0
                        )
                        break
                else:
                    if min_contact <= contact_count <= max_contact_range:
                        labels_colors[particle_id] = (
                            float(color[0]), float(color[1]), float(color[2]), 1.0
                        )
                        break
        
        logger.info(f"Created color mapping for {len(labels_colors)} particles")
        return labels_colors
    
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
    
    def load_best_labels_with_contacts(
        self,
        best_labels_path: Path,
        connectivity: int = 6,
        volume_path: Optional[Path] = None,
        best_radius: int = 0,
        metadata: Optional[dict] = None
    ) -> 'napari.Viewer':
        """Load best optimization result with contact count coloring in Napari viewer.
        
        Args:
            best_labels_path: Path to best_labels.npy file
            connectivity: Connectivity for contact counting (6 or 26)
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
        
        logger.info(f"Opening Napari with contact-colored result (r={best_radius})")
        logger.info(f"Labels shape: {best_labels.shape}")
        logger.info(f"Unique particles: {best_labels.max()}")
        
        # Calculate contact counts
        from ..contact import count_contacts
        from ..contact.visualization import get_discrete_contact_colormap
        
        logger.info("Calculating contact counts...")
        contact_counts = count_contacts(best_labels, connectivity=connectivity)
        logger.info(f"Calculated contacts for {len(contact_counts)} particles")
        
        # Create particle_id -> color mapping based on contact counts
        labels_colors = self._create_contact_color_mapping(contact_counts)
        
        # Create or reuse viewer
        title = f"3D Particle Analysis - Contact Visualization (r={best_radius})"
        viewer = self.get_or_create_viewer(title)
        
        # ========================================
        # Layer 1: Particle Contact Heatmap (Property Mapping)
        # ========================================
        logger.info("Creating Layer 1: Particle Contact Heatmap...")
        
        # Create contact count map: replace each voxel's label ID with its particle's contact count
        from ..contact.visualization import create_contact_count_map
        contact_map = create_contact_count_map(best_labels, contact_counts)
        
        # Add as Image layer with colormap
        # Use 'turbo' colormap: blue (low contacts) -> red (high contacts)
        viewer.add_image(
            contact_map,
            name=f"Contact Heatmap (r={best_radius})",
            colormap='turbo',
            opacity=1.0,
            rendering='mip',  # Maximum Intensity Projection
            visible=True  # Default: visible
        )
        logger.info("✅ Layer 1 added: Contact Heatmap (visible)")
        
        # ========================================
        # Layer 2: Weak Zone Map (Thresholding & Transparency)
        # ========================================
        logger.info("Creating Layer 2: Weak Zone Map...")
        
        # Create weak zone map: same as contact_map but only showing 0-4 contacts
        weak_zone_mask = (contact_map >= 0) & (contact_map <= 4)
        weak_zone_data = np.where(weak_zone_mask, contact_map, np.nan)
        
        viewer.add_image(
            weak_zone_data,
            name=f"Weak Zones (0-4 contacts) (r={best_radius})",
            colormap='turbo',
            opacity=1.0,
            rendering='mip',
            visible=False  # Default: hidden
        )
        logger.info("✅ Layer 2 added: Weak Zones (hidden)")
        
        # ========================================
        # Layer 3: Centroids (Point Cloud)
        # ========================================
        logger.info("Creating Layer 3: Centroids...")
        
        try:
            from scipy.ndimage import center_of_mass  # type: ignore

            label_ids = np.array(sorted(labels_colors.keys()), dtype=np.int32)
            if label_ids.size > 0:
                # Use scipy's center_of_mass with index parameter for efficiency
                centroids = center_of_mass(best_labels, labels=best_labels, index=label_ids)
                centroids_arr = np.asarray(centroids, dtype=np.float32)
                
                # Filter out invalid entries (NaN/Inf)
                valid_mask = np.isfinite(centroids_arr).all(axis=1)
                centroids_arr = centroids_arr[valid_mask]
                valid_ids = label_ids[valid_mask]
                
                if centroids_arr.shape[0] > 0:
                    # Get colors for valid particles (RGB only, no alpha for points)
                    face_colors = np.array([
                        [labels_colors[int(i)][0], labels_colors[int(i)][1], labels_colors[int(i)][2]]
                        for i in valid_ids
                    ], dtype=np.float32)

                    viewer.add_points(
                        centroids_arr,
                        name=f"Centroids (r={best_radius})",
                        size=3,
                        face_color=face_colors,
                        opacity=0.9,
                        visible=False  # Default: hidden
                    )
                    logger.info(f"✅ Layer 3 added: Centroids ({centroids_arr.shape[0]} points, hidden)")
                else:
                    logger.warning("No valid centroids calculated")
        except Exception as e:
            logger.warning(f"Failed to create centroids layer: {e}")
            # Non-critical, continue without centroids
        
        # Log metadata if provided
        if metadata:
            metadata_text = "\n".join([f"{k}: {v}" for k, v in metadata.items()])
            logger.info(f"Best result metadata:\n{metadata_text}")
        
        # Log contact statistics
        if contact_counts:
            contact_values = list(contact_counts.values())
            logger.info(
                f"Contact statistics: "
                f"mean={np.mean(contact_values):.2f}, "
                f"median={np.median(contact_values):.1f}, "
                f"range=[{min(contact_values)}, {max(contact_values)}]"
            )
        
        # Set optimal view
        viewer.dims.ndisplay = NAPARI_NDISPLAY_3D  # 3D mode
        viewer.camera.angles = NAPARI_DEFAULT_CAMERA_ANGLES  # Nice viewing angle
        
        # Show viewer window
        viewer.window.show()
        
        logger.info("✅ Napari viewer opened with contact coloring")
        
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

