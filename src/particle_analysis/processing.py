"""Core image processing functions for particle analysis."""

import logging
from pathlib import Path
from typing import Optional, Tuple, Literal

import cv2
import numpy as np
from skimage.filters import threshold_otsu, threshold_triangle
from skimage.exposure import equalize_adapthist
from skimage.morphology import (
    binary_closing,
    ball,
    remove_small_objects
)
from skimage.util import img_as_float, img_as_uint

from .config import PostprocessConfig, DEFAULT_CONFIG
from .utils.common import Timer
from .utils.file_utils import get_image_files

logger = logging.getLogger(__name__)


def apply_clahe_slice_by_slice(volume: np.ndarray) -> np.ndarray:
    """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to each slice.
    
    This improves local contrast and is robust for low-contrast CT scans.
    """
    z_slices = volume.shape[0]
    # Use float32 for processing to avoid precision loss during CLAHE
    # equalize_adapthist returns float64 [0, 1] usually
    
    # We'll normalize first if not float
    vol_float = img_as_float(volume)
    
    # Create empty output array
    enhanced_volume = np.zeros_like(vol_float)
    
    # Process slice by slice
    for i in range(z_slices):
        enhanced_volume[i] = equalize_adapthist(vol_float[i], kernel_size=None, clip_limit=0.01, nbins=256)
        
        if (i + 1) % 50 == 0:
            logger.info(f"CLAHE processing: {i + 1}/{z_slices} slices")
            
    # Convert back to original range/dtype if needed, but thresholding functions work fine on float
    # We will return the float volume [0, 1] which is standard for skimage filters
    return enhanced_volume


def load_and_binarize_3d_volume(
    folder_path: str,
    min_object_size: int = 100,
    closing_radius: int = 0,
    return_info: bool = False,
    enable_clahe: bool = False,
    threshold_method: Literal["otsu", "triangle"] = "otsu",
    backend: Literal["cpu", "gpu"] = "cpu",
) -> np.ndarray:
    """Load TIF images and perform high-precision 3D binarization.
    
    This function implements the M2 plan from APP_IMPLEMENTATION_PLAN.md:
    - Preserves uint16 precision (no 8-bit downscaling)
    - 3D Otsu or Triangle threshold on entire volume
    - Optional CLAHE enhancement
    - Automatic polarity detection
    - Optional morphological post-processing
    
    Args:
        folder_path: Path to folder containing TIF/TIFF images
        min_object_size: Minimum object size for small object removal (0 to disable)
        closing_radius: Radius for binary closing operation (0 to disable)
        return_info: If True, returns tuple (binary_volume, info_dict)
        enable_clahe: If True, applies CLAHE contrast enhancement before thresholding
        threshold_method: "otsu" or "triangle". Triangle is better for unimodal histograms.
        
    Returns:
        Binary 3D volume (bool array) with shape (Z, Y, X)
        Or tuple (binary_volume, info_dict) if return_info=True
        
    Raises:
        ValueError: If no valid images found or loading fails
    backend:
        "cpu" または "gpu"（現時点では "cpu" のみ実装。"gpu" は将来の拡張用）
    """
    if backend not in ("cpu", "gpu"):
        raise ValueError(f"Unsupported backend: {backend}")
    folder = Path(folder_path)
    if not folder.exists():
        raise ValueError(f"Folder does not exist: {folder_path}")
    
    # Step 1: Get all TIF/TIFF files
    logger.info(f"Scanning folder: {folder_path}")
    image_files = get_image_files(folder, supported_formats=["*.tif", "*.tiff"])
    
    if len(image_files) == 0:
        raise ValueError(f"No TIF/TIFF images found in {folder_path}")
    
    logger.info(f"Found {len(image_files)} images")
    
    # Step 2: Load first image to get dimensions
    first_img = cv2.imread(str(image_files[0]), cv2.IMREAD_UNCHANGED)
    if first_img is None:
        raise ValueError(f"Failed to load first image: {image_files[0]}")
    
    height, width = first_img.shape
    dtype = first_img.dtype
    z_slices = len(image_files)
    
    logger.info(f"Volume dimensions: Z={z_slices}, H={height}, W={width}, dtype={dtype}")
    
    # Step 3: Load all images into 3D volume (preserve uint16!)
    with Timer("Loading 3D volume"):
        volume = np.zeros((z_slices, height, width), dtype=dtype)
        
        for i, img_path in enumerate(image_files):
            img = cv2.imread(str(img_path), cv2.IMREAD_UNCHANGED)
            if img is None:
                logger.warning(f"Failed to load image: {img_path}, skipping")
                continue
            
            volume[i] = img
            
            if (i + 1) % 50 == 0 or i == z_slices - 1:
                logger.info(f"Loaded {i + 1}/{z_slices} images...")
    
    # Step 3.5: CLAHE Contrast Enhancement
    if enable_clahe:
        with Timer("Applying CLAHE contrast enhancement"):
            logger.info("Applying CLAHE slice-by-slice...")
            volume = apply_clahe_slice_by_slice(volume)
            # volume is now float64 [0, 1]
            logger.info("CLAHE completed. Volume converted to float64 [0, 1].")

    # Step 4: Thresholding
    with Timer(f"3D Thresholding ({threshold_method})"):
        threshold_val = 0.0
        threshold1 = 0.0 # For backward compatibility in info dict
        
        # Always perform Stage 1 (ROI detection) using Global Otsu
        # This separates the Object (Container + Particles) from the Background (Air/Black)
        threshold1 = threshold_otsu(volume)
        logger.info(f"Stage 1 (ROI) Otsu threshold: {threshold1} (range: {volume.min()}-{volume.max()})")
        
        # Extract voxels above Stage 1 threshold (The ROI)
        roi_mask = volume > threshold1
        roi_voxels = volume[roi_mask]
        
        if len(roi_voxels) == 0:
            logger.warning("No voxels in ROI! Using Stage 1 threshold")
            threshold_val = threshold1
        else:
            # Stage 2: Apply selected method on ROI voxels ONLY
            if threshold_method == "triangle":
                # Triangle method on ROI (Good for unimodal "Gray" histograms inside ROI)
                threshold_val = threshold_triangle(roi_voxels)
                logger.info(f"Stage 2 (Triangle) threshold: {threshold_val} (on ROI)")
            else: # Default to Otsu
                # Otsu on ROI (Standard 2-stage Otsu)
                threshold_val = threshold_otsu(roi_voxels)
                logger.info(f"Stage 2 (Otsu) threshold: {threshold_val} (on ROI)")
        
        logger.info(f"Final threshold: {threshold_val}")
    
    # Step 5: Automatic polarity detection
    with Timer("Automatic polarity detection"):
        # Calculate statistics on each side of final threshold
        below_threshold = volume <= threshold_val
        above_threshold = volume > threshold_val
        
        mean_below = volume[below_threshold].mean() if below_threshold.any() else 0
        mean_above = volume[above_threshold].mean() if above_threshold.any() else 0
        
        count_below = below_threshold.sum()
        count_above = above_threshold.sum()
        
        logger.info(f"Below threshold: mean={mean_below:.3f}, count={count_below:,}")
        logger.info(f"Above threshold: mean={mean_above:.3f}, count={count_above:,}")
        
        # Determine polarity based on which side has fewer voxels
        # Particles are typically the minority phase in CT scans
        if count_below < count_above:
            # Fewer voxels below threshold → particles are below threshold
            binary_volume = below_threshold
            polarity = "inverted (foreground is darker)"
            logger.info(f"✓ Detected polarity: Foreground is BELOW threshold (inverted)")
            logger.info(f"   Minority phase: {count_below:,} voxels ({count_below/volume.size:.2%})")
        else:
            # Fewer voxels above threshold → particles are above threshold
            binary_volume = above_threshold
            polarity = "normal (foreground is brighter)"
            logger.info(f"✓ Detected polarity: Foreground is ABOVE threshold (normal)")
            logger.info(f"   Minority phase: {count_above:,} voxels ({count_above/volume.size:.2%})")
    
    # Step 6: Post-processing
    foreground_before = binary_volume.sum()
    logger.info(f"Foreground voxels before post-processing: {foreground_before:,}")
    
    # Binary closing (fill small holes)
    if closing_radius > 0:
        with Timer(f"Binary closing (radius={closing_radius})"):
            selem = ball(closing_radius)
            binary_volume = binary_closing(binary_volume, selem)
            logger.info(f"Applied binary closing with radius {closing_radius}")
    
    # Small object removal (remove noise)
    if min_object_size > 0:
        with Timer(f"Small object removal (min_size={min_object_size})"):
            # Use connectivity=1 for 3D (6-connectivity, face neighbors only)
            binary_volume = remove_small_objects(
                binary_volume,
                min_size=min_object_size,
                connectivity=1
            )
            logger.info(f"Removed objects smaller than {min_object_size} voxels")
    
    foreground_after = binary_volume.sum()
    foreground_ratio = foreground_after / binary_volume.size
    logger.info(f"Foreground voxels after post-processing: {foreground_after:,} ({foreground_ratio:.2%})")
    
    # Prepare info dictionary
    info = {
        'folder_path': str(folder_path),
        'num_images': z_slices,
        'volume_shape': binary_volume.shape,
        'original_dtype': str(dtype),
        'threshold': float(threshold_val),
        'threshold_stage1': float(threshold1),
        'threshold_stage2': float(threshold_val),
        'polarity': polarity,
        'foreground_voxels': int(foreground_after),
        'foreground_ratio': float(foreground_ratio),
        'mean_below_threshold': float(mean_below),
        'mean_above_threshold': float(mean_above),
        'closing_radius': closing_radius,
        'min_object_size': min_object_size,
        'clahe_enabled': enable_clahe,
        'threshold_method': threshold_method
    }
    
    if return_info:
        return binary_volume, info
    else:
        return binary_volume


# Method A (per-slice 2D mask processing) and related CLI-oriented helpers have been removed.
