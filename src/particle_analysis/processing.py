"""Core image processing functions for particle analysis."""

import logging
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
from skimage.filters import threshold_otsu
from skimage.morphology import (
    binary_closing, 
    disk, 
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
    return_info: bool = False
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
    with Timer("2-stage 3D Otsu thresholding"):
        # Stage 1: First Otsu on entire volume (separates background from potential foreground)
        threshold1 = threshold_otsu(volume)
        logger.info(f"Stage 1 Otsu threshold: {threshold1} (dtype: {dtype}, range: {volume.min()}-{volume.max()})")
        
        # Extract voxels above first threshold
        above_threshold1 = volume > threshold1
        foreground_voxels = volume[above_threshold1]
        
        if len(foreground_voxels) == 0:
            logger.warning("No voxels above first threshold! Using single-stage Otsu")
            threshold2 = threshold1
        else:
            # Stage 2: Second Otsu on extracted foreground region (refines particle separation)
            threshold2 = threshold_otsu(foreground_voxels)
            logger.info(f"Stage 2 Otsu threshold: {threshold2} (on foreground range: {foreground_voxels.min()}-{foreground_voxels.max()})")
        
        logger.info(f"Final threshold: {threshold2}")
    
    # Step 5: Automatic polarity detection
    with Timer("Automatic polarity detection"):
        # Calculate statistics on each side of final threshold
        below_threshold = volume <= threshold2
        above_threshold = volume > threshold2
        
        mean_below = volume[below_threshold].mean() if below_threshold.any() else 0
        mean_above = volume[above_threshold].mean() if above_threshold.any() else 0
        
        count_below = below_threshold.sum()
        count_above = above_threshold.sum()
        
        logger.info(f"Below threshold: mean={mean_below:.1f}, count={count_below:,}")
        logger.info(f"Above threshold: mean={mean_above:.1f}, count={count_above:,}")
        
        # Determine polarity based on which side has fewer voxels
        # Particles are typically the minority phase in CT scans
        # The side with FEWER voxels is likely the foreground (particles)
        if count_below < count_above:
            # Fewer voxels below threshold → particles are below threshold
            binary_volume = volume <= threshold2
            polarity = "inverted (foreground is darker/below threshold)"
            logger.info(f"✓ Detected polarity: Foreground is BELOW threshold (inverted)")
            logger.info(f"   Minority phase: {count_below:,} voxels ({count_below/volume.size:.2%})")
        else:
            # Fewer voxels above threshold → particles are above threshold
            binary_volume = volume > threshold2
            polarity = "normal (foreground is brighter/above threshold)"
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
        'threshold': float(threshold2),  # Final threshold after 2-stage Otsu
        'threshold_stage1': float(threshold1),  # First stage threshold
        'threshold_stage2': float(threshold2),  # Second stage threshold
        'polarity': polarity,
        'foreground_voxels': int(foreground_after),
        'foreground_ratio': float(foreground_ratio),
        'mean_below_threshold': float(mean_below),
        'mean_above_threshold': float(mean_above),
        'closing_radius': closing_radius,
        'min_object_size': min_object_size
    }
    
    if return_info:
        return binary_volume, info
    else:
        return binary_volume


def clean_mask(
    gray_img: np.ndarray, 
    config: Optional[PostprocessConfig] = None,
    invert: Optional[bool] = None
) -> np.ndarray:
    """Clean and binarize a grayscale CT slice image.

    Args:
        gray_img: Input grayscale image (uint8 or uint16)
        config: Processing configuration
        invert: Override inversion setting

    Returns:
        Binary mask (uint8) with values 0 or 255
    """
    if config is None:
        config = DEFAULT_CONFIG.postprocess
    
    if invert is None:
        invert = config.invert_default
    
    # Convert to uint8 if needed
    if gray_img.dtype == np.uint16:
        gray_img = (gray_img / 256).astype(np.uint8)
    
    with Timer("CLAHE contrast enhancement"):
        clahe = cv2.createCLAHE(
            clipLimit=config.clahe_clip_limit, 
            tileGridSize=config.clahe_tile_size
        )
        equalized = clahe.apply(gray_img)
    
    with Timer("Gaussian blur"):
        blurred = cv2.GaussianBlur(equalized, config.gaussian_kernel, 0)
    
    with Timer("Otsu thresholding"):
        _, binary = cv2.threshold(
            blurred, 0, 255, 
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
    
    # Binary closing (optional)
    binary_bool = binary > 0
    if config.closing_radius > 0:
        with Timer(f"Binary closing (radius={config.closing_radius})"):
            selem = disk(config.closing_radius)
            binary_bool = binary_closing(binary_bool, selem)
    
    # Small object removal
    if config.min_object_size > 0:
        with Timer("Small object removal"):
            binary_bool = remove_small_objects(
                binary_bool, 
                min_size=config.min_object_size,
                connectivity=2  # Use 2-connectivity for 2D images
            )
    
    # Invert if requested
    if invert:
        binary_bool = ~binary_bool
    
    # Convert back to uint8
    result = binary_bool.astype(np.uint8) * 255
    return result


def process_masks(img_dir: str, mask_dir: str, out_dir: str, force: bool = False) -> int:
    """Process masks through clean_mask and save to output directory.
    
    Args:
        img_dir: Directory containing original CT images
        mask_dir: Directory containing input masks
        out_dir: Base output directory
        force: Whether to overwrite existing files
    
    Returns:
        int: Number of masks processed
    """
    from datetime import datetime
    from pathlib import Path
    
    # Setup output directory with timestamp if not forced
    if not force:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        out_dir = str(Path(out_dir) / f"run_{timestamp}")
    
    # Create output directories
    masks_pred_dir = Path(out_dir) / "masks_pred"
    masks_pred_dir.mkdir(parents=True, exist_ok=True)
    
    # Get list of mask files
    mask_files = list(Path(mask_dir).glob("*.png"))
    if not mask_files:
        logger.warning(f"No PNG files found in {mask_dir}")
        return 0
    
    processed_count = 0
    for mask_path in mask_files:
        # Read mask
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if mask is None:
            logger.warning(f"Failed to read mask: {mask_path}")
            continue
        
        # Process through clean_mask
        cleaned_mask = clean_mask(mask)
        
        # Save to output directory
        out_path = masks_pred_dir / mask_path.name
        cv2.imwrite(str(out_path), cleaned_mask)
        processed_count += 1
        
        if processed_count % 10 == 0:  # Progress indicator
            logger.info(f"Processed {processed_count}/{len(mask_files)} masks...")
    
    return processed_count
