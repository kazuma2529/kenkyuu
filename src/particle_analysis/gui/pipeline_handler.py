"""Pipeline processing handler for GUI operations.

This module handles the image processing pipeline operations
that are called from the main GUI window.
"""

import logging
from pathlib import Path
from typing import List, Optional

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
    
    def create_volume(self, progress_callback=None) -> Path:
        """Create 3D volume from processed masks.
        
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
