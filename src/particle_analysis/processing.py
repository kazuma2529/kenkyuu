"""Core image processing functions for particle analysis."""

import logging
from typing import Optional

import cv2
import numpy as np
from skimage.morphology import binary_closing, disk, remove_small_objects

from .config import PostprocessConfig, DEFAULT_CONFIG
from .utils.common import Timer

logger = logging.getLogger(__name__)


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