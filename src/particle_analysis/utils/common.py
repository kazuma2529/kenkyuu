"""Common utilities for the particle analysis pipeline."""

import logging
import os
import time
from pathlib import Path
from typing import Optional, Tuple, Union

import numpy as np


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Setup consistent logging configuration.
    
    Args:
        level: Logging level
        
    Returns:
        Configured logger
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def ensure_directory(path: Union[str, Path]) -> Path:
    """Ensure directory exists, create if necessary.
    
    Args:
        path: Directory path
        
    Returns:
        Path object
    """
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj


def load_volume(path: Union[str, Path], expected_dtype: Optional[type] = None) -> np.ndarray:
    """Load and validate volume data.
    
    Args:
        path: Path to .npy file
        expected_dtype: Expected data type for validation
        
    Returns:
        Loaded volume array
        
    Raises:
        ValueError: If volume has unexpected properties
    """
    volume = np.load(path)
    
    if volume.ndim != 3:
        raise ValueError(f"Expected 3D volume, got {volume.ndim}D array")
    
    if expected_dtype and volume.dtype != expected_dtype:
        logging.warning(f"Converting volume dtype from {volume.dtype} to {expected_dtype}")
        if expected_dtype == bool:
            volume = volume > 0
        else:
            volume = volume.astype(expected_dtype)
    
    return volume


def save_volume(volume: np.ndarray, path: Union[str, Path], dtype: Optional[type] = None) -> None:
    """Save volume with optional type conversion.
    
    Args:
        volume: Volume array to save
        path: Output path
        dtype: Optional target dtype
    """
    if dtype and volume.dtype != dtype:
        if dtype == np.uint8 and volume.dtype == bool:
            volume = volume.astype(np.uint8) * 255
        else:
            volume = volume.astype(dtype)
    
    path_obj = Path(path)
    ensure_directory(path_obj.parent)
    np.save(path_obj, volume)


def get_connectivity_structure(connectivity: int) -> np.ndarray:
    """Get 3D connectivity structure for ndimage operations.
    
    Args:
        connectivity: 6, 18, or 26
        
    Returns:
        3D structure array
        
    Raises:
        ValueError: If connectivity not supported
    """
    from scipy import ndimage
    
    connectivity_map = {6: 1, 18: 2, 26: 3}
    if connectivity not in connectivity_map:
        raise ValueError(f"Connectivity must be 6, 18, or 26, got {connectivity}")
    
    return ndimage.generate_binary_structure(3, connectivity_map[connectivity])


def validate_labels(labels: np.ndarray) -> Tuple[int, int]:
    """Validate and analyze label array.
    
    Args:
        labels: Label array
        
    Returns:
        Tuple of (max_label, num_unique_labels)
    """
    if labels.ndim != 3:
        raise ValueError(f"Expected 3D labels, got {labels.ndim}D array")
    
    unique_labels = np.unique(labels)
    max_label = unique_labels.max()
    
    # Check for gaps in labeling
    expected_labels = set(range(max_label + 1))
    actual_labels = set(unique_labels)
    missing_labels = expected_labels - actual_labels
    
    if missing_labels and len(missing_labels) > max_label * 0.1:  # > 10% missing
        logging.warning(f"Label array has {len(missing_labels)} missing labels")
    
    return int(max_label), len(unique_labels)


class Timer:
    """Simple context manager for timing operations."""
    
    def __init__(self, description: str):
        self.description = description
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        logging.info(f"Starting: {self.description}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        logging.info(f"Completed: {self.description} ({elapsed:.2f}s)")


 