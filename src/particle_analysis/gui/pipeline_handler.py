"""Pipeline processing handler for GUI operations.

This module handles the image processing pipeline operations
that are called from the main GUI window.
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class PipelineHandler:
    """Handles pipeline processing operations for the GUI."""
    
    def __init__(self, output_dir: Path):
        """Initialize pipeline handler.
        
        Args:
            output_dir: Directory for output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def process_ct_images(self, ct_folder_path: str, progress_callback=None) -> int:
        """Process CT images through the complete pipeline.
        
        Args:
            ct_folder_path: Path to folder containing CT images
            progress_callback: Optional callback for progress updates
            
        Returns:
            int: Number of images processed
            
        Raises:
            ValueError: If no images found or processing fails
        """
        from ..processing import clean_mask
        from ..utils import get_image_files
        
        # Setup masks directory
        masks_pred_dir = self.output_dir / "masks_pred"
        masks_pred_dir.mkdir(parents=True, exist_ok=True)
        
        # Get all supported image files
        ct_files = get_image_files(Path(ct_folder_path))
        
        if len(ct_files) == 0:
            raise ValueError("No supported image files found in selected folder")
        
        processed_count = 0
        total_files = len(ct_files)
        
        for i, ct_file in enumerate(ct_files):
            # Update progress
            if progress_callback:
                progress_percent = (i + 1) / total_files * 100
                progress_callback(f"Processing CT images... ({progress_percent:.0f}%)")
            
            # Read CT image
            ct_img = cv2.imread(str(ct_file), cv2.IMREAD_GRAYSCALE)
            if ct_img is None:
                logger.warning(f"Failed to read CT image: {ct_file}")
                continue
            
            # Process through clean_mask (CLAHE → Gaussian → Otsu → morphology)
            processed_mask = clean_mask(ct_img)
            
            # Save processed mask
            dest_file = masks_pred_dir / ct_file.name
            cv2.imwrite(str(dest_file), processed_mask)
            processed_count += 1
        
        if processed_count == 0:
            raise ValueError("No CT images were processed successfully")
        
        logger.info(f"Processed {processed_count}/{total_files} CT images")
        return processed_count
    
    def create_volume_from_3d_binarization(
        self, 
        ct_folder_path: str, 
        progress_callback=None
    ) -> Tuple[Path, Dict]:
        """Create 3D volume using high-precision 3D Otsu binarization.
        
        This method implements M2 from APP_IMPLEMENTATION_PLAN.md:
        - 3D Otsu on uint16 data (no downscaling)
        - Automatic polarity detection
        - Morphological post-processing
        
        Args:
            ct_folder_path: Path to folder containing CT TIF images
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple[Path, Dict]: (volume_path, info_dict) with binarization info
            
        Raises:
            ValueError: If volume creation fails
        """
        from ..processing import load_and_binarize_3d_volume
        
        if progress_callback:
            progress_callback("Loading images and performing 3D Otsu binarization...")
        
        volume_path = self.output_dir / "volume.npy"
        
        try:
            # High-precision 3D binarization
            binary_volume, info = load_and_binarize_3d_volume(
                ct_folder_path,
                min_object_size=100,  # Remove small noise
                closing_radius=0,     # No closing by default (can be adjusted)
                return_info=True
            )
            
            # Save binary volume
            np.save(str(volume_path), binary_volume)
            
            logger.info(f"Created 3D volume: {volume_path}")
            logger.info(f"Volume shape: {binary_volume.shape}")
            logger.info(f"Foreground ratio: {info['foreground_ratio']:.2%}")
            logger.info(f"Polarity: {info['polarity']}")
            
            return volume_path, info
            
        except Exception as e:
            logger.error(f"Failed to create 3D volume: {e}")
            raise ValueError(f"Failed to create 3D volume: {e}")
    
    def create_volume(self, progress_callback=None) -> Path:
        """Create 3D volume from processed masks.
        
        DEPRECATED: Use create_volume_from_3d_binarization() for better quality.
        
        Args:
            progress_callback: Optional callback for progress updates
            
        Returns:
            Path: Path to created volume.npy file
            
        Raises:
            ValueError: If volume creation fails
        """
        from ..volume import stack_masks
        
        if progress_callback:
            progress_callback("Creating 3D volume...")
        
        masks_pred_dir = self.output_dir / "masks_pred"
        if not masks_pred_dir.exists():
            raise ValueError("Processed masks directory not found")
        
        volume_path = self.output_dir / "volume.npy"
        
        try:
            stack_masks(
                mask_dir=str(masks_pred_dir),
                out_vol=str(volume_path),
                dtype="bool"
            )
            
            logger.info(f"Created 3D volume: {volume_path}")
            return volume_path
            
        except Exception as e:
            raise ValueError(f"Failed to create 3D volume: {e}")
    
    def get_masks_directory(self) -> Path:
        """Get the processed masks directory."""
        return self.output_dir / "masks_pred"
    
    def get_volume_path(self) -> Path:
        """Get the volume file path."""
        return self.output_dir / "volume.npy"


__all__ = ["PipelineHandler"]
