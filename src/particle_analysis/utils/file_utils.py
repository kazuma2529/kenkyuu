"""File handling utilities for image processing.

This module provides utility functions for handling file operations
with proper sorting and format support.
"""

import re
from pathlib import Path
from typing import List


def natural_sort_key(path: Path) -> tuple:
    """Generate a sort key for natural ordering of filenames.
    
    This function handles filenames with numbers properly:
    CT1.png, CT2.png, ..., CT10.png, CT11.png
    instead of alphabetical: CT1.png, CT10.png, CT11.png, CT2.png
    
    Args:
        path: Path object to generate sort key for
        
    Returns:
        Tuple that can be used for sorting
    """
    def convert_part(text):
        return int(text) if text.isdigit() else text.lower()
    
    # Split filename into parts (numbers and text)
    parts = re.split(r'(\d+)', path.stem)
    return tuple(convert_part(part) for part in parts)


def get_image_files(directory: Path, supported_formats: List[str] = None) -> List[Path]:
    """Get all supported image files from a directory with natural sorting.
    
    Args:
        directory: Directory to search for images
        supported_formats: List of glob patterns (default: common image formats)
        
    Returns:
        List of Path objects sorted naturally (duplicates removed)
    """
    if supported_formats is None:
        supported_formats = ["*.png", "*.jpg", "*.jpeg", "*.tif", "*.tiff", "*.bmp"]
    
    # Use set to avoid duplicates (important on Windows where case is ignored)
    image_files_set = set()
    for pattern in supported_formats:
        image_files_set.update(directory.glob(pattern))
    
    # Convert back to list and sort using natural ordering
    image_files = sorted(list(image_files_set), key=natural_sort_key)
    
    return image_files

__all__ = ["natural_sort_key", "get_image_files"] 