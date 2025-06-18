import os
import shutil
from pathlib import Path

import numpy as np
import pytest

import sys
sys.path.append('src')
from label3d import label_volume


@pytest.fixture
def test_dirs():
    """Create and clean up test directories."""
    base_dir = "tests/test_data_label"
    dirs = {
        "base": base_dir,
        "out": f"{base_dir}/output"
    }
    
    # Create directories
    for dir_path in dirs.values():
        os.makedirs(dir_path, exist_ok=True)
    
    yield dirs
    
    # Cleanup after tests
    shutil.rmtree(base_dir)


@pytest.fixture
def test_volume(test_dirs):
    """Create a test volume with two separate particles."""
    # Create 3x4x4 volume
    volume = np.zeros((3, 4, 4), dtype=bool)
    
    # First particle in z=0
    volume[0, 0:2, 0:2] = True
    
    # Second particle in z=2
    volume[2, 2:4, 2:4] = True
    
    # Save volume
    vol_path = f"{test_dirs['base']}/volume.npy"
    np.save(vol_path, volume)
    
    return vol_path


def test_separate_particles(test_dirs, test_volume):
    """Test that two separate particles are correctly labeled."""
    out_labels = f"{test_dirs['out']}/labels.npy"
    
    # Run labeling
    num_particles = label_volume(test_volume, out_labels)
    
    # Check number of particles
    assert num_particles == 2
    
    # Load and check labels
    labels = np.load(out_labels)
    assert labels.dtype == np.uint32
    assert labels.shape == (3, 4, 4)
    assert len(np.unique(labels)) == 3  # 0 (background) + 2 particles


def test_connectivity_difference(test_dirs):
    """Test that connectivity affects the number of particles."""
    # Create volume with diagonal connection
    volume = np.zeros((2, 2, 2), dtype=bool)
    volume[0, 0, 0] = True
    volume[1, 1, 1] = True
    
    vol_path = f"{test_dirs['base']}/volume_diag.npy"
    np.save(vol_path, volume)
    
    # Test with 6-connectivity
    out_labels_6 = f"{test_dirs['out']}/labels_6.npy"
    num_6 = label_volume(vol_path, out_labels_6, connectivity=6)
    
    # Test with 26-connectivity
    out_labels_26 = f"{test_dirs['out']}/labels_26.npy"
    num_26 = label_volume(vol_path, out_labels_26, connectivity=26)
    
    # 6-connectivity should see them as separate
    assert num_6 == 2
    # 26-connectivity should see them as connected
    assert num_26 == 1


def test_empty_volume(test_dirs):
    """Test handling of volume with no particles."""
    # Create empty volume
    volume = np.zeros((2, 2, 2), dtype=bool)
    vol_path = f"{test_dirs['base']}/volume_empty.npy"
    np.save(vol_path, volume)
    
    # Run labeling
    out_labels = f"{test_dirs['out']}/labels_empty.npy"
    num_particles = label_volume(vol_path, out_labels)
    
    assert num_particles == 0 