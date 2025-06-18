import numpy as np
import pytest
import sys
sys.path.append('src')
from eval_baseline import compute_dice, compute_iou


def test_perfect_match():
    """Test that identical masks give Dice=1 and IoU=1."""
    # Create a random binary mask
    rng = np.random.default_rng(42)
    mask = (rng.random((100, 100)) > 0.5).astype(np.uint8) * 255
    
    # Compare with itself
    dice = compute_dice(mask, mask)
    iou = compute_iou(mask, mask)
    
    assert dice == pytest.approx(1.0)
    assert iou == pytest.approx(1.0)


def test_complete_mismatch():
    """Test that completely different masks give Dice=0 and IoU=0."""
    # Create black and white masks
    black = np.zeros((100, 100), dtype=np.uint8)
    white = np.full((100, 100), 255, dtype=np.uint8)
    
    # Compare black vs white
    dice = compute_dice(black, white)
    iou = compute_iou(black, white)
    
    assert dice == pytest.approx(0.0)
    assert iou == pytest.approx(0.0)


def test_empty_masks():
    """Test edge case where both masks are empty (all black)."""
    empty = np.zeros((100, 100), dtype=np.uint8)
    
    dice = compute_dice(empty, empty)
    iou = compute_iou(empty, empty)
    
    assert dice == pytest.approx(1.0)  # Empty masks are considered perfect match
    assert iou == pytest.approx(1.0) 