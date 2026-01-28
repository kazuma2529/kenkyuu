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

from .gpu_backend import binary_erosion_gpu, distance_transform_edt_gpu

logger = logging.getLogger(__name__)


# Method A dependent volume stacking (from 2D masks) has been removed.


def split_particles(
    vol_path: str,
    out_labels: str,
    radius: int = 2,
    connectivity: int = 6
) -> int:
    """Split touching particles using erosion-watershed algorithm (legacy file-based API).

    Note: This function remains for backward compatibility but should not be used
    in the GUI pipeline. Prefer `split_particles_in_memory` for in-memory processing.
    """
    volume = np.load(vol_path).astype(bool)
    labels = split_particles_in_memory(volume, radius=radius, connectivity=connectivity)
    np.save(out_labels, labels)
    num_particles = int(labels.max())
    logger.info(f"Particle splitting complete: {num_particles} particles (saved to {out_labels})")
    return num_particles


def split_particles_in_memory(
    volume: np.ndarray,
    *,
    radius: int = 2,
    connectivity: int = 6,
    backend: str = "cpu",
) -> np.ndarray:
    """Split touching particles using erosion-watershed algorithm (in-memory).

    Args:
        volume: Binary 3D volume (bool or int) with shape (Z, Y, X)
        radius: Erosion radius (structuring element size)
        connectivity: Connectivity for connected components (6 or 26)
        backend: "cpu" または "gpu"（現時点では "cpu" のみ実装。"gpu" は将来の拡張用）

    Returns:
        Labeled volume as np.int32 with labels in [0..N]
    """
    if backend not in ("cpu", "gpu"):
        raise ValueError(f"Unsupported backend: {backend}")

    volume = volume.astype(bool)

    struct_elem = ball(radius)
    logger.debug(f"Using ball structuring element with radius={radius}")

    if backend == "cpu":
        eroded = ndimage.binary_erosion(volume, structure=struct_elem)
        distance = ndimage.distance_transform_edt(volume)
    else:  # backend == "gpu"
        logger.info("Using GPU backend for erosion + distance transform")
        eroded = binary_erosion_gpu(volume, struct_elem)
        distance = distance_transform_edt_gpu(volume)

    # Label eroded components as seeds
    seed_labels, n_seeds = ndimage.label(eroded, structure=np.ones((3, 3, 3)))
    logger.info(f"Found {n_seeds} seed regions after erosion")

    if n_seeds == 0:
        logger.warning("No seeds found after erosion - returning binary as single component labels")
        return volume.astype(np.int32)

    # Use watershed to grow seeds back to original boundaries
    labels = watershed(-distance, seed_labels, mask=volume)
    return labels.astype(np.int32)


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

__all__ = ["split_particles", "split_particles_in_memory", "label_volume"]