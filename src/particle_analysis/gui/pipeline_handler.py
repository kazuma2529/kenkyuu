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
    
    # Method A (per-slice processing) removed; GUI uses 3D binarization directly.
    
    def create_volume_from_3d_binarization(
        self,
        ct_folder_path: str,
        progress_callback=None
    ) -> Tuple[np.ndarray, Dict]:
        """Create 3D volume using high-precision 3D Otsu binarization (in-memory).

        Returns the binary volume and info dict without saving to disk.
        """
        from ..processing import load_and_binarize_3d_volume
        
        if progress_callback:
            progress_callback("Loading images and performing 3D Otsu binarization...")

        try:
            # High-precision 3D binarization
            binary_volume, info = load_and_binarize_3d_volume(
                ct_folder_path,
                min_object_size=100,  # Remove small noise
                closing_radius=0,     # No closing by default (can be adjusted)
                return_info=True
            )
            
            logger.info("Created 3D volume in memory (not saved to disk)")
            logger.info(f"Volume shape: {binary_volume.shape}")
            logger.info(f"Foreground ratio: {info['foreground_ratio']:.2%}")
            logger.info(f"Polarity: {info['polarity']}")
            
            return binary_volume, info
            
        except Exception as e:
            logger.error(f"Failed to create 3D volume: {e}")
            raise ValueError(f"Failed to create 3D volume: {e}")
    
__all__ = ["PipelineHandler"]
