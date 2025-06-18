import os
import shutil
from pathlib import Path

import cv2
import numpy as np
import pytest

import sys
sys.path.append('src')
from infer import process_masks


@pytest.fixture
def test_dirs():
    """Create and clean up test directories."""
    # Setup test directories
    base_dir = "tests/test_data"
    dirs = {
        "base": base_dir,
        "img": f"{base_dir}/images",
        "mask": f"{base_dir}/masks",
        "out": f"{base_dir}/output"
    }
    
    # Create directories
    for dir_path in dirs.values():
        os.makedirs(dir_path, exist_ok=True)
    
    # Create test masks
    for i in range(3):
        # Create a simple circle mask
        mask = np.zeros((100, 100), dtype=np.uint8)
        cv2.circle(mask, (50, 50), 30, 255, -1)
        cv2.imwrite(f"{dirs['mask']}/CT{i+1:03d}.png", mask)
    
    yield dirs
    
    # Cleanup after tests
    shutil.rmtree(base_dir)


def test_mask_processing(test_dirs):
    """Test that masks are processed and saved correctly."""
    # Process masks
    processed_count = process_masks(
        test_dirs["img"],
        test_dirs["mask"],
        test_dirs["out"],
        force=True
    )
    
    # Check number of processed files
    assert processed_count == 3
    
    # Check output files exist
    output_dir = Path(test_dirs["out"]) / "masks_pred"
    output_files = list(output_dir.glob("*.png"))
    assert len(output_files) == 3
    
    # Verify output mask properties
    for mask_path in output_files:
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        # Check that mask is binary (0 or 255)
        assert set(np.unique(mask)) <= {0, 255} 