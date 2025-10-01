"""Stability metrics for label consistency analysis.

This module provides metrics to quantify the stability and consistency
of particle segmentation across different parameters:
- Variation of Information (VI) between labelings
- Dice coefficient for binary mask comparison
- Mean slice-wise Dice against ground truth
"""

import logging
from typing import Dict, List, Tuple

import numpy as np

logger = logging.getLogger(__name__)


def calculate_variation_of_information(
    labels_a: np.ndarray,
    labels_b: np.ndarray,
    ignore_background: bool = True,
) -> float:
    """Compute Variation of Information (VI) between two labelings.

    VI(X, Y) = H(X) + H(Y) - 2 I(X; Y), lower is better (0 if identical).

    Args:
        labels_a: 3D labeled volume A
        labels_b: 3D labeled volume B
        ignore_background: If True, restrict to voxels where A>0 or B>0

    Returns:
        float: VI value (>=0)
    """
    if labels_a.shape != labels_b.shape:
        raise ValueError("labels_a and labels_b must have the same shape")

    if ignore_background:
        mask = (labels_a > 0) | (labels_b > 0)
        if not np.any(mask):
            return 0.0
        a = labels_a[mask].ravel()
        b = labels_b[mask].ravel()
    else:
        a = labels_a.ravel()
        b = labels_b.ravel()

    # Map labels to consecutive integers for compact contingency
    def relabel(x: np.ndarray) -> Tuple[np.ndarray, int]:
        unique, inv = np.unique(x, return_inverse=True)
        return inv, unique.size

    a_inv, a_k = relabel(a)
    b_inv, b_k = relabel(b)

    # Build contingency table via 1D indexing
    joint_index = a_inv.astype(np.int64) * b_k + b_inv.astype(np.int64)
    counts = np.bincount(joint_index, minlength=a_k * b_k).astype(float)
    Pxy = counts.reshape((a_k, b_k))
    n = Pxy.sum()
    if n <= 0:
        return 0.0
    Pxy /= n

    Px = Pxy.sum(axis=1, keepdims=True)
    Py = Pxy.sum(axis=0, keepdims=True)

    # Entropies H(X), H(Y)
    def entropy(p: np.ndarray) -> float:
        p = p[p > 0]
        if p.size == 0:
            return 0.0
        return float(-np.sum(p * np.log2(p)))

    Hx = entropy(Px.flatten())
    Hy = entropy(Py.flatten())

    # Mutual information I(X;Y)
    # Only where Pxy>0 and Px*Py>0
    with np.errstate(divide='ignore', invalid='ignore'):
        ratio = np.where(Pxy > 0, Pxy / (Px @ Py), 1.0)
        log_term = np.where(Pxy > 0, np.log2(ratio), 0.0)
        Ixy = float(np.sum(Pxy * log_term))

    VI = Hx + Hy - 2.0 * Ixy
    # Numerical guard
    return float(max(0.0, VI))


def dice_coefficient_2d(mask_pred: np.ndarray, mask_gt: np.ndarray) -> float:
    """Compute Dice coefficient between two 2D binary masks.

    Args:
        mask_pred: 2D boolean/0-1 array (prediction)
        mask_gt: 2D boolean/0-1 array (ground truth)

    Returns:
        float: Dice in [0,1]
    """
    if mask_pred.shape != mask_gt.shape:
        raise ValueError("mask_pred and mask_gt must have the same shape")
    a = mask_pred.astype(bool)
    b = mask_gt.astype(bool)
    inter = np.logical_and(a, b).sum(dtype=float)
    s = a.sum(dtype=float) + b.sum(dtype=float)
    if s == 0.0:
        return 1.0
    return float(2.0 * inter / s)


def calculate_mean_slice_dice(
    labels: np.ndarray,
    gt_slices: Dict[int, np.ndarray],
    axis: int = 0,
) -> float:
    """Compute mean Dice over provided GT slices against labels>0 per slice.

    Args:
        labels: 3D labeled volume
        gt_slices: Mapping slice_index -> 2D GT binary mask
        axis: Slicing axis (0=z, 1=y, 2=x)

    Returns:
        float: Mean Dice over available slices (0 if none)
    """
    if not gt_slices:
        return 0.0
    dices: List[float] = []
    for idx, gt in gt_slices.items():
        if axis == 0:
            if idx < 0 or idx >= labels.shape[0]:
                continue
            pred2d = labels[idx] > 0
        elif axis == 1:
            if idx < 0 or idx >= labels.shape[1]:
                continue
            pred2d = labels[:, idx, :] > 0
        elif axis == 2:
            if idx < 0 or idx >= labels.shape[2]:
                continue
            pred2d = labels[:, :, idx] > 0
        else:
            raise ValueError("axis must be 0, 1, or 2")
        if pred2d.shape != gt.shape:
            # Skip mismatched slice sizes
            continue
        dices.append(dice_coefficient_2d(pred2d, gt))
    if not dices:
        return 0.0
    return float(np.mean(dices))


__all__ = [
    "calculate_variation_of_information",
    "dice_coefficient_2d",
    "calculate_mean_slice_dice",
]
