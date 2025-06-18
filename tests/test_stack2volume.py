import os
import shutil
from pathlib import Path

import cv2
import numpy as np
import pytest

import sys
sys.path.append('src')
from stack2volume import stack_masks


@pytest.fixture
def test_dirs():
    """Create and clean up test directories."""
    # Setup test directories
    base_dir = "tests/test_data_stack"
    dirs = {
        "base": base_dir,
        "mask": f"{base_dir}/masks",
        "out": f"{base_dir}/output"
    }
    
    # Create directories
    for dir_path in dirs.values():
        os.makedirs(dir_path, exist_ok=True)
    
    # Create 3 checkerboard masks (10x10)
    for i in range(3):
        mask = np.zeros((10, 10), dtype=np.uint8)
        # Create alternating pattern
        mask[::2, ::2] = 255  # Even rows, even columns
        mask[1::2, 1::2] = 255  # Odd rows, odd columns
        # Add some variation per slice
        if i > 0:
            mask = np.roll(mask, i, axis=0)
        cv2.imwrite(f"{dirs['mask']}/CT{i+1:03d}.png", mask)
    
    yield dirs
    
    # Cleanup after tests
    shutil.rmtree(base_dir)


def test_volume_stacking(test_dirs):
    """Test that masks are correctly stacked into a volume."""
    out_vol = f"{test_dirs['out']}/volume.npy"
    
    # Stack masks
    stack_masks(test_dirs["mask"], out_vol)
    
    # Load and check volume
    volume = np.load(out_vol)
    
    # Check shape
    assert volume.shape == (3, 10, 10)
    
    # Check dtype
    assert volume.dtype == bool
    
    # Check that each slice has some True values
    assert volume.any(axis=(1, 2)).all()


def test_uint8_output(test_dirs):
    """Test uint8 output option."""
    out_vol = f"{test_dirs['out']}/volume_uint8.npy"
    
    # Stack masks with uint8 dtype
    stack_masks(test_dirs["mask"], out_vol, dtype="uint8")
    
    # Load and check volume
    volume = np.load(out_vol)
    
    # Check dtype
    assert volume.dtype == np.uint8
    
    # Check values are 0 or 255
    assert set(np.unique(volume)) <= {0, 255} 