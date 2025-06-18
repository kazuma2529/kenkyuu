"""3D volume operations for particle analysis."""

import logging
from pathlib import Path
from typing import Optional

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
    # Get sorted list of mask files
    mask_files = sorted(Path(mask_dir).glob("*.png"))
    if not mask_files:
        logger.warning(f"No PNG files found in {mask_dir}")
        return

    # Check total number against expected 196
    if len(mask_files) != 196:
        logger.warning(
            f"Found {len(mask_files)} slices, "
            f"which differs from expected 196 slices"
        )

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

    # Save volume
    Path(out_vol).parent.mkdir(parents=True, exist_ok=True)
    np.save(out_vol, volume)
    
    logger.info(f"Stacked {Z} slices: shape: {volume.shape}")


def split_particles(
    vol_path: str, 
    out_labels: str, 
    radius: int = 2, 
    connectivity: int = 6
) -> int:
    """Split touching particles using erosion-watershed approach.
    
    Args:
        vol_path: Path to 3D volume (.npy file)
        out_labels: Output path for labeled volume
        radius: Erosion radius for particle splitting
        connectivity: Connectivity for labeling (6 or 26)
    
    Returns:
        int: Number of particles detected
    """
    # Load volume
    volume = np.load(vol_path)
    if volume.dtype != bool:
        volume = volume > 0
    
    logger.info(f"Eroding volume (radius={radius})")
    # Erode to separate touching particles
    struct_elem = ball(radius)
    eroded = ndimage.binary_erosion(volume, structure=struct_elem)
    
    logger.info(f"Labeling eroded volume (connectivity={connectivity})")
    # Label connected components in eroded volume
    eroded_labels, num_eroded = ndimage.label(eroded, 
                                            structure=ndimage.generate_binary_structure(3, connectivity))
    logger.info(f"Eroded particles detected: {num_eroded}")
    
    if num_eroded == 0:
        logger.warning("No particles found after erosion")
        # Save empty labels
        labels = np.zeros_like(volume, dtype=np.int32)
        np.save(out_labels, labels)
        return 0
    
    logger.info("Propagating labels to full mask via watershed")
    # Use watershed to propagate labels back to full mask
    distance = ndimage.distance_transform_edt(volume)
    labels = watershed(-distance, eroded_labels, mask=volume)
    
    # Ensure labels are contiguous starting from 1
    unique_labels = np.unique(labels)
    unique_labels = unique_labels[unique_labels > 0]  # Remove background
    num_particles = len(unique_labels)
    
    # Relabel to ensure contiguous IDs
    final_labels = np.zeros_like(labels)
    for i, old_label in enumerate(unique_labels):
        final_labels[labels == old_label] = i + 1
    
    # Save labeled volume
    Path(out_labels).parent.mkdir(parents=True, exist_ok=True)
    np.save(out_labels, final_labels)
    
    logger.info(f"split radius={radius} → particles: {num_particles}")
    return num_particles


def label_volume(vol_path: str, out_labels: str, connectivity: int = 6) -> int:
    """Label connected components in a 3D volume.
    
    Args:
        vol_path: Path to 3D volume (.npy file)
        out_labels: Output path for labeled volume
        connectivity: Connectivity for labeling (6 or 26)
    
    Returns:
        int: Number of connected components found
    """
    # Load volume
    volume = np.load(vol_path)
    if volume.dtype != bool:
        volume = volume > 0
    
    # Label connected components
    labels, num_labels = ndimage.label(volume, 
                                     structure=ndimage.generate_binary_structure(3, connectivity))
    
    # Save labeled volume
    Path(out_labels).parent.mkdir(parents=True, exist_ok=True)
    np.save(out_labels, labels)
    
    logger.info(f"Labeled {num_labels} connected components")
    return num_labels 