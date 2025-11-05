"""Core volume processing operations.

This module contains the fundamental operations for 3D volume processing
including mask stacking, particle splitting, and volume labeling.
"""

import logging
from pathlib import Path
import numpy as np
from scipy import ndimage
from skimage.segmentation import watershed
from skimage.morphology import ball

logger = logging.getLogger(__name__)


# Method A dependent volume stacking (from 2D masks) has been removed.


def split_particles(
    vol_path: str, 
    out_labels: str, 
    radius: int = 2, 
    connectivity: int = 6
) -> int:
    """Split touching particles using erosion-watershed algorithm.
    
    Args:
        vol_path: Input volume (.npy file)
        out_labels: Output labeled volume (.npy file)
        radius: Erosion radius (structuring element size)
        connectivity: Connectivity for connected components (6 or 26)
    
    Returns:
        int: Number of particles found
    """
    # Load volume
    volume = np.load(vol_path).astype(bool)
    logger.info(f"Loaded volume: {vol_path} (shape={volume.shape})")
    
    # Create erosion structuring element
    struct_elem = ball(radius)
    logger.debug(f"Using ball structuring element with radius={radius}")
    
    # Erode to separate touching particles
    eroded = ndimage.binary_erosion(volume, structure=struct_elem)
    
    # Label eroded components as seeds
    seed_labels, n_seeds = ndimage.label(eroded, structure=np.ones((3, 3, 3)))
    logger.info(f"Found {n_seeds} seed regions after erosion")
    
    if n_seeds == 0:
        logger.warning("No seeds found after erosion - creating single label")
        labels = volume.astype(np.int32)
        np.save(out_labels, labels)
        return int(volume.any())
    
    # Use watershed to grow seeds back to original boundaries
    distance = ndimage.distance_transform_edt(volume)
    labels = watershed(-distance, seed_labels, mask=volume)
    
    # Convert to appropriate dtype and save
    labels = labels.astype(np.int32)
    np.save(out_labels, labels)
    
    num_particles = int(labels.max())
    logger.info(f"Particle splitting complete: {num_particles} particles")
    
    return num_particles


def label_volume(vol_path: str, out_labels: str, connectivity: int = 6) -> int:
    """Label connected components in a binary volume without splitting.
    
    Args:
        vol_path: Input volume (.npy file) 
        out_labels: Output labeled volume (.npy file)
        connectivity: Connectivity for connected components
    
    Returns:
        int: Number of connected components found
    """
    # Load volume
    volume = np.load(vol_path).astype(bool)
    logger.info(f"Loaded volume: {vol_path} (shape={volume.shape})")
    
    # Define connectivity structure
    if connectivity == 6:
        struct = ndimage.generate_binary_structure(3, 1)  # Face connectivity
    elif connectivity == 26:
        struct = ndimage.generate_binary_structure(3, 3)  # Full connectivity
    else:
        raise ValueError(f"Unsupported connectivity: {connectivity}")
    
    # Label connected components
    labels, num_labels = ndimage.label(volume, structure=struct)
    
    # Convert to appropriate dtype and save
    labels = labels.astype(np.int32)
    np.save(out_labels, labels)
    
    logger.info(f"Volume labeling complete: {num_labels} components")
    
    return num_labels

__all__ = ["split_particles", "label_volume"]