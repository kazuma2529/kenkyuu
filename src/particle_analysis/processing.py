"""Core image processing functions for particle analysis."""

import logging
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
from scipy import ndimage
from skimage.filters import threshold_otsu, threshold_sauvola
from skimage.morphology import (
    binary_closing,
    ball,
    remove_small_objects
)

from .config import PostprocessConfig, DEFAULT_CONFIG
from .utils.common import Timer
from .utils.file_utils import get_image_files

logger = logging.getLogger(__name__)


def load_and_binarize_3d_volume(
    folder_path: str,
    min_object_size: int = 100,
    closing_radius: int = 0,
    return_info: bool = False,
    polarity: str = "auto",
    thresholding: str = "otsu3d",
    roi_mode: str = "none",
    sauvola_window: int = 51,
    sauvola_k: float = 0.2,
    norm_p_low: float = 1.0,
    norm_p_high: float = 99.0
) -> np.ndarray:
    """Load TIF images and perform high-precision 3D Otsu binarization.
    
    This function implements the M2 plan from APP_IMPLEMENTATION_PLAN.md:
    - Preserves uint16 precision (no 8-bit downscaling)
    - 3D Otsu threshold on entire volume
    - Automatic polarity detection
    - Optional morphological post-processing
    
    Args:
        folder_path: Path to folder containing TIF/TIFF images
        min_object_size: Minimum object size for small object removal (0 to disable)
        closing_radius: Radius for binary closing operation (0 to disable)
        return_info: If True, returns tuple (binary_volume, info_dict)
        
    Returns:
        Binary 3D volume (bool array) with shape (Z, Y, X)
        Or tuple (binary_volume, info_dict) if return_info=True
        
    Raises:
        ValueError: If no valid images found or loading fails
    """
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
    
    # Step 4: 2-stage 3D Otsu thresholding (following sakai_code approach)
    # This is crucial for CT data with wide dynamic range
    roi_mask = None
    if (roi_mode or "none").lower() not in {"none", "off", "false", "0"}:
        roi_mask = volume > 0
        refined = np.zeros_like(roi_mask, dtype=bool)
        for z in range(roi_mask.shape[0]):
            m = roi_mask[z]
            m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)
            m = ndimage.binary_fill_holes(m)
            lbl, n = ndimage.label(m)
            if n > 0:
                counts = np.bincount(lbl.ravel())
                counts[0] = 0
                refined[z] = lbl == int(counts.argmax())
        roi_mask = refined

    thresholding_mode = (thresholding or "otsu3d").lower()
    threshold1 = 0.0
    threshold2 = 0.0

    if thresholding_mode in {"otsu3d", "otsu3d_roi"}:
        with Timer("2-stage 3D Otsu thresholding"):
            if thresholding_mode == "otsu3d_roi" and roi_mask is not None and roi_mask.any():
                values = volume[roi_mask]
                values_for_otsu = values
                if (values_for_otsu > 0).any():
                    values_for_otsu = values_for_otsu[values_for_otsu > 0]
                vmin = int(values.min())
                vmax = int(values.max())
                threshold1 = threshold_otsu(values_for_otsu)
                logger.info(f"Stage 1 Otsu threshold: {threshold1} (dtype: {dtype}, roi_range: {vmin}-{vmax})")

                above_threshold1 = values > threshold1
                foreground_voxels = values[above_threshold1]
            else:
                values_for_otsu = volume
                if (values_for_otsu > 0).any():
                    values_for_otsu = values_for_otsu[values_for_otsu > 0]
                threshold1 = threshold_otsu(values_for_otsu)
                logger.info(f"Stage 1 Otsu threshold: {threshold1} (dtype: {dtype}, range: {volume.min()}-{volume.max()})")

                above_threshold1 = volume > threshold1
                foreground_voxels = volume[above_threshold1]

            if len(foreground_voxels) == 0:
                logger.warning("No voxels above first threshold! Using single-stage Otsu")
                threshold2 = threshold1
            else:
                foreground_for_otsu = foreground_voxels
                if (foreground_for_otsu > 0).any():
                    foreground_for_otsu = foreground_for_otsu[foreground_for_otsu > 0]
                threshold2 = threshold_otsu(foreground_for_otsu)
                logger.info(
                    f"Stage 2 Otsu threshold: {threshold2} (on foreground range: {foreground_voxels.min()}-{foreground_voxels.max()})"
                )

            logger.info(f"Final threshold: {threshold2}")
    
    binary_volume = None
    if thresholding_mode == "sauvola2d_roi":
        if roi_mask is None or not roi_mask.any():
            roi_mask = volume > 0

        window = int(sauvola_window)
        if window < 3:
            window = 3
        if window % 2 == 0:
            window += 1

        binary_volume = np.zeros(volume.shape, dtype=bool)
        for z in range(volume.shape[0]):
            m = roi_mask[z]
            if not m.any():
                continue
            slice_u16 = volume[z]
            roi_vals = slice_u16[m].astype(np.float32)
            p_low = float(np.percentile(roi_vals, norm_p_low))
            p_high = float(np.percentile(roi_vals, norm_p_high))
            if p_high <= p_low:
                p_low = float(roi_vals.min())
                p_high = float(roi_vals.max())
            denom = (p_high - p_low) if (p_high - p_low) > 0 else 1.0
            slice_norm = ((slice_u16.astype(np.float32) - p_low) / denom).clip(0.0, 1.0)
            thr = threshold_sauvola(slice_norm, window_size=window, k=float(sauvola_k))

            requested_polarity = (polarity or "auto").lower()
            if requested_polarity == "dark":
                b = slice_norm <= thr
            else:
                b = slice_norm > thr

            b &= m
            binary_volume[z] = b

        polarity = "forced dark (foreground is darker/below threshold)" if (polarity or "auto").lower() == "dark" else "forced bright (foreground is brighter/above threshold)"
        logger.info(f"Using Sauvola 2D thresholding (window={window}, k={sauvola_k})")

    # Step 5: Polarity selection
    with Timer("Polarity selection"):
        if roi_mask is not None and roi_mask.any():
            below_threshold = roi_mask & (volume <= threshold2)
            above_threshold = roi_mask & (volume > threshold2)
        else:
            below_threshold = volume <= threshold2
            above_threshold = volume > threshold2

        mean_below = volume[below_threshold].mean() if below_threshold.any() else 0
        mean_above = volume[above_threshold].mean() if above_threshold.any() else 0

        count_below = below_threshold.sum()
        count_above = above_threshold.sum()

        logger.info(f"Below threshold: mean={mean_below:.1f}, count={count_below:,}")
        logger.info(f"Above threshold: mean={mean_above:.1f}, count={count_above:,}")

        requested_polarity = (polarity or "auto").lower()
        if requested_polarity not in {"auto", "bright", "dark"}:
            raise ValueError(f"Unsupported polarity: {polarity}. Use 'auto', 'bright', or 'dark'.")

        if binary_volume is not None:
            requested_polarity = (polarity or "auto").lower()
        elif requested_polarity == "bright":
            binary_volume = volume > threshold2
            if roi_mask is not None:
                binary_volume &= roi_mask
            polarity = "forced bright (foreground is brighter/above threshold)"
            logger.info("✓ Polarity forced: Foreground is ABOVE threshold (bright)")
        elif requested_polarity == "dark":
            binary_volume = volume <= threshold2
            if roi_mask is not None:
                binary_volume &= roi_mask
            polarity = "forced dark (foreground is darker/below threshold)"
            logger.info("✓ Polarity forced: Foreground is BELOW threshold (dark)")
        else:
            # Determine polarity based on which side has fewer voxels
            if count_below < count_above:
                binary_volume = volume <= threshold2
                if roi_mask is not None:
                    binary_volume &= roi_mask
                polarity = "auto inverted (foreground is darker/below threshold)"
                logger.info("✓ Detected polarity (auto): Foreground is BELOW threshold (inverted)")
                logger.info(f"   Minority phase: {count_below:,} voxels ({count_below/volume.size:.2%})")
            else:
                binary_volume = volume > threshold2
                if roi_mask is not None:
                    binary_volume &= roi_mask
                polarity = "auto normal (foreground is brighter/above threshold)"
                logger.info("✓ Detected polarity (auto): Foreground is ABOVE threshold (normal)")
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
        'threshold': float(threshold2),  # Final threshold after 2-stage Otsu
        'threshold_stage1': float(threshold1),  # First stage threshold
        'threshold_stage2': float(threshold2),  # Second stage threshold
        'polarity': polarity,
        'foreground_voxels': int(foreground_after),
        'foreground_ratio': float(foreground_ratio),
        'mean_below_threshold': float(mean_below),
        'mean_above_threshold': float(mean_above),
        'closing_radius': closing_radius,
        'min_object_size': min_object_size,
        'thresholding': thresholding_mode,
        'roi_mode': str(roi_mode),
        'roi_voxels': int(roi_mask.sum()) if roi_mask is not None else 0,
        'roi_ratio': float(roi_mask.sum() / roi_mask.size) if roi_mask is not None else 0.0,
        'sauvola_window': int(sauvola_window),
        'sauvola_k': float(sauvola_k),
        'norm_p_low': float(norm_p_low),
        'norm_p_high': float(norm_p_high)
    }
    
    if return_info:
        return binary_volume, info
    else:
        return binary_volume


# Method A (per-slice 2D mask processing) and related CLI-oriented helpers have been removed.
