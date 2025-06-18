import numpy as np
import pytest
import sys
sys.path.append('src')
from core.processing import clean_mask


def test_output_values_are_binary():
    """Test that output mask contains only 0 and 255 values."""
    # Create random noise image
    rng = np.random.default_rng(42)
    noise_img = rng.integers(0, 256, size=(100, 100), dtype=np.uint8)
    
    # Process the image
    result = clean_mask(noise_img)
    
    # Check output type and values
    assert result.dtype == np.uint8
    assert set(np.unique(result)) <= {0, 255}


def test_small_noise_removal():
    """Test that small objects (radius < 2px) are removed."""
    # Create black image with small white dots
    img = np.zeros((100, 100), dtype=np.uint8)
    
    # Add small noise dots (2x2 pixels)
    noise_positions = [(25, 25), (50, 50), (75, 75)]
    for y, x in noise_positions:
        img[y:y+2, x:x+2] = 255
    
    # Process the image
    result = clean_mask(img)
    
    # Check that all noise dots are removed
    assert np.sum(result) == 0  # Should be completely black 