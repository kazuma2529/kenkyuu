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
    NAPARI_GUARD_BOUNDARY_OPACITY,
    NAPARI_GUARD_BOUNDARY_COLORMAP,
    NAPARI_BOUNDARY_PARTICLES_OPACITY,
    NAPARI_GUARD_SHELL_THICKNESS,
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
    
    def load_best_labels_with_contacts(
        self,
        best_labels_path: Path,
        connectivity: int = 6,
        volume_path: Optional[Path] = None,
        best_radius: int = 0,
        metadata: Optional[dict] = None
    ) -> 'napari.Viewer':
        """Load best optimization result with contact count coloring in Napari viewer.
        
        Layers:
            1. All Particles Heatmap — full_contacts for full 3D spatial context
            2. Guard Volume Boundary — translucent shell at guard margin
            3. Boundary Particles — excluded particles in gray (hidden)
            4. Weak Zones — interior-only, 0-4 contacts (hidden)
            5. Centroids — interior-only point cloud (hidden)
        
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
        from scipy.ndimage import binary_erosion  # type: ignore
        from ..contact.guard_volume import (
            count_contacts_with_guard, calculate_guard_margin, create_guard_volume_mask,
        )
        from ..contact.visualization import create_contact_count_map
        
        if not NAPARI_AVAILABLE:
            raise RuntimeError("Napari is not installed")
        
        if not best_labels_path.exists():
            raise FileNotFoundError(f"Labels file not found: {best_labels_path}")
        
        # Load data
        best_labels = np.load(best_labels_path)
        
        logger.info(f"Opening Napari with contact-colored result (r={best_radius})")
        logger.info(f"Labels shape: {best_labels.shape}, unique particles: {best_labels.max()}")
        
        # Calculate contact counts with guard volume filtering
        logger.info("Calculating contact counts with guard volume filtering...")
        full_contacts, interior_contacts, guard_stats = count_contacts_with_guard(
            best_labels, connectivity=connectivity
        )
        logger.info(
            f"Guard volume: {guard_stats['interior_particles']} interior / "
            f"{guard_stats['total_particles']} total "
            f"({guard_stats['excluded_particles']} excluded)"
        )
        
        # Compute guard volume margin and mask
        margin = calculate_guard_margin(best_labels)
        guard_mask = create_guard_volume_mask(best_labels.shape, margin)
        
        # Create or reuse viewer
        title = f"3D Particle Analysis - Contact Visualization (r={best_radius})"
        viewer = self.get_or_create_viewer(title)
        
        # ========================================
        # Layer 1: All Particles Heatmap (full spatial context)
        # ========================================
        logger.info("Creating Layer 1: All Particles Heatmap...")
        full_contact_map = create_contact_count_map(best_labels, full_contacts)
        
        viewer.add_image(
            full_contact_map,
            name=f"All Particles Heatmap (r={best_radius})",
            colormap='turbo',
            opacity=1.0,
            rendering='mip',
            visible=True
        )
        logger.info("✅ Layer 1 added: All Particles Heatmap (visible)")
        
        # ========================================
        # Layer 2: Guard Volume Boundary (translucent shell)
        # ========================================
        logger.info("Creating Layer 2: Guard Volume Boundary...")
        eroded = binary_erosion(guard_mask, iterations=NAPARI_GUARD_SHELL_THICKNESS)
        boundary_shell = guard_mask.astype(np.uint8) - eroded.astype(np.uint8)
        
        viewer.add_image(
            boundary_shell.astype(np.float32),
            name=f"Guard Volume Boundary (margin={margin})",
            colormap=NAPARI_GUARD_BOUNDARY_COLORMAP,
            opacity=NAPARI_GUARD_BOUNDARY_OPACITY,
            rendering='mip',
            blending='additive',
            visible=True
        )
        logger.info(f"✅ Layer 2 added: Guard Volume Boundary (margin={margin} voxels)")
        
        # ========================================
        # Layer 3: Boundary Particles (excluded, shown in gray)
        # ========================================
        logger.info("Creating Layer 3: Boundary Particles...")
        boundary_particle_ids = set(full_contacts.keys()) - set(interior_contacts.keys())
        boundary_map = np.zeros_like(best_labels, dtype=np.float32)
        for pid in boundary_particle_ids:
            boundary_map[best_labels == pid] = 1.0
        
        viewer.add_image(
            boundary_map,
            name=f"Boundary Particles (excluded: {len(boundary_particle_ids)})",
            colormap='gray',
            opacity=NAPARI_BOUNDARY_PARTICLES_OPACITY,
            rendering='mip',
            blending='additive',
            visible=False
        )
        logger.info(f"✅ Layer 3 added: Boundary Particles ({len(boundary_particle_ids)}, hidden)")
        
        # ========================================
        # Layer 4: Weak Zones (interior only, reliable data)
        # ========================================
        logger.info("Creating Layer 4: Weak Zones (interior only)...")
        interior_contact_map = create_contact_count_map(best_labels, interior_contacts)
        weak_zone_mask = (interior_contact_map > 0) & (interior_contact_map <= 4)
        weak_zone_data = np.where(weak_zone_mask, interior_contact_map, np.nan)
        
        viewer.add_image(
            weak_zone_data,
            name=f"Weak Zones (interior, 0-4 contacts) (r={best_radius})",
            colormap='turbo',
            opacity=1.0,
            rendering='mip',
            visible=False
        )
        logger.info("✅ Layer 4 added: Weak Zones (hidden)")
        
        # Log metadata if provided
        if metadata:
            metadata_text = "\n".join([f"{k}: {v}" for k, v in metadata.items()])
            logger.info(f"Best result metadata:\n{metadata_text}")
        
        # Log contact statistics (both full and interior)
        if full_contacts:
            full_values = list(full_contacts.values())
            logger.info(
                f"Contact statistics (all): "
                f"mean={np.mean(full_values):.2f}, "
                f"median={np.median(full_values):.1f}, "
                f"range=[{min(full_values)}, {max(full_values)}]"
            )
        if interior_contacts:
            interior_values = list(interior_contacts.values())
            logger.info(
                f"Contact statistics (interior): "
                f"mean={np.mean(interior_values):.2f}, "
                f"median={np.median(interior_values):.1f}, "
                f"range=[{min(interior_values)}, {max(interior_values)}]"
            )
        
        # Set optimal view
        viewer.dims.ndisplay = NAPARI_NDISPLAY_3D
        viewer.camera.angles = NAPARI_DEFAULT_CAMERA_ANGLES
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

