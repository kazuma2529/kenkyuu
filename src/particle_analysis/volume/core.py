"""Core volume processing operations.

This module contains the fundamental operations for 3D volume processing
including mask stacking, particle splitting, and volume labeling.
"""

import logging
from pathlib import Path

import cv2
import numpy as np
from scipy import ndimage
from skimage.segmentation import watershed
from skimage.morphology import ball

logger = logging.getLogger(__name__)


def stack_masks(mask_dir: str, out_vol: str, dtype: str = "bool", invert: bool = False) -> None:
    """Stack 2D masks into a 3D volume and save as .npy file.
    
    Args:
        mask_dir: Directory containing mask PNG files
        out_vol: Output path for .npy file
        dtype: Output dtype ("bool" or "uint8")
        invert: Invert voxel polarity (background↔particle)
    """
    # Get sorted list of mask files (support multiple formats)
    from ..utils import get_image_files
    mask_files = get_image_files(Path(mask_dir))
    
    if not mask_files:
        logger.warning(f"No supported image files found in {mask_dir}")
        return

    # Log the number of slices found
    logger.info(f"Found {len(mask_files)} slices for processing")
    
    # Provide guidance for common cases
    if len(mask_files) < 50:
        logger.warning(f"Only {len(mask_files)} slices found - results may be less reliable with fewer slices")
    elif len(mask_files) > 500:
        logger.info(f"Large dataset ({len(mask_files)} slices) - processing may take longer")

    # Read first mask to get dimensions
    first_mask = cv2.imread(str(mask_files[0]), cv2.IMREAD_GRAYSCALE)
    if first_mask is None:
        logger.error(f"Failed to read first mask: {mask_files[0]}")
        return

    H, W = first_mask.shape
    Z = len(mask_files)

    # Pre-allocate volume array
    volume = np.zeros((Z, H, W), dtype=bool)

    # Stack masks
    for i, mask_path in enumerate(mask_files):
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if mask is None:
            logger.error(f"Failed to read mask: {mask_path}")
            return
        if mask.shape != (H, W):
            logger.error(
                f"Inconsistent dimensions: {mask_path} "
                f"has shape {mask.shape}, expected {(H, W)}"
            )
            return

        # Convert to boolean
        voxel = mask > 0  # White(>0) assumed as particle
        if invert:
            voxel = ~voxel
        volume[i] = voxel

    # Convert dtype if needed
    if dtype == "uint8":
        volume = volume.astype(np.uint8) * 255
    elif dtype == "bool":
        volume = volume.astype(bool)
    else:
        raise ValueError(f"Unsupported dtype: {dtype}")

    # Save volume
    np.save(out_vol, volume)
    logger.info(f"Saved 3D volume: {out_vol} (shape={volume.shape}, dtype={volume.dtype})")


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

__all__ = ["stack_masks", "split_particles", "label_volume"] 