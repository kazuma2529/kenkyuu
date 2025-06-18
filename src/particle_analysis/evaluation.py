"""Evaluation metrics for particle analysis."""

import csv
import logging
import os
from pathlib import Path
from typing import Tuple

import cv2
import numpy as np

from .processing import clean_mask

logger = logging.getLogger(__name__)


def compute_dice(pred: np.ndarray, gt: np.ndarray) -> float:
    """Compute Dice coefficient between prediction and ground truth masks.
    
    Args:
        pred: Binary prediction mask (0 or 255)
        gt: Binary ground truth mask (0 or 255)
    
    Returns:
        float: Dice coefficient in range [0, 1]
    """
    pred = pred > 0  # Convert to boolean
    gt = gt > 0
    
    intersection = np.logical_and(pred, gt).sum()
    total = pred.sum() + gt.sum()
    
    if total == 0:
        return 1.0 if pred.sum() == gt.sum() else 0.0
        
    return 2.0 * intersection / total


def compute_iou(pred: np.ndarray, gt: np.ndarray) -> float:
    """Compute Intersection over Union (IoU) between prediction and ground truth masks.
    
    Args:
        pred: Binary prediction mask (0 or 255)
        gt: Binary ground truth mask (0 or 255)
    
    Returns:
        float: IoU coefficient in range [0, 1]
    """
    pred = pred > 0  # Convert to boolean
    gt = gt > 0
    
    intersection = np.logical_and(pred, gt).sum()
    union = np.logical_or(pred, gt).sum()
    
    if union == 0:
        return 1.0 if intersection == 0 else 0.0
        
    return intersection / union


def evaluate_masks(img_dir: str, mask_dir: str, gt_dir: str, out_csv: str = None) -> Tuple[float, float]:
    """Evaluate Otsu masks against ground truth using Dice and IoU metrics.
    
    Args:
        img_dir: Directory containing original CT images
        mask_dir: Directory containing Otsu masks
        gt_dir: Directory containing ground truth masks
        out_csv: Output CSV file path, if None no CSV is written
    
    Returns:
        Tuple[float, float]: Mean Dice and IoU scores
    """
    gt_files = list(Path(gt_dir).glob("*.png"))
    metrics = []
    
    if out_csv:
        os.makedirs(os.path.dirname(out_csv), exist_ok=True)
        f = open(out_csv, "w", newline="")
        writer = csv.writer(f)
        writer.writerow(["filename", "dice", "iou"])
    else:
        f = None
        writer = None
    
    for gt_path in gt_files:
        # Load ground truth
        gt = cv2.imread(str(gt_path), cv2.IMREAD_GRAYSCALE)
        if gt is None:
            logger.warning(f"Failed to read GT: {gt_path}")
            continue
        
        # Find corresponding Otsu mask
        mask_path = Path(mask_dir) / gt_path.name
        if not mask_path.exists():
            logger.warning(f"Otsu mask not found: {mask_path}")
            continue
        
        # Load Otsu mask
        otsu_mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if otsu_mask is None:
            logger.warning(f"Failed to read Otsu mask: {mask_path}")
            continue
        
        # Find corresponding original image for clean_mask
        img_path = Path(img_dir) / gt_path.name
        if img_path.exists():
            # Process through clean_mask pipeline
            img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                pred = clean_mask(img)
            else:
                pred = otsu_mask
        else:
            # Use Otsu mask directly
            pred = otsu_mask
        
        # Compute metrics
        dice = compute_dice(pred, gt)
        iou = compute_iou(pred, gt)
        
        metrics.append((dice, iou))
        
        if writer:
            writer.writerow([gt_path.name, f"{dice:.4f}", f"{iou:.4f}"])
        
        logger.debug(f"{gt_path.name}: Dice={dice:.4f}, IoU={iou:.4f}")
    
    if f:
        f.close()
    
    if not metrics:
        logger.error("No valid image pairs found for evaluation")
        return 0.0, 0.0
    
    # Calculate mean metrics
    dice_scores, iou_scores = zip(*metrics)
    mean_dice = np.mean(dice_scores)
    mean_iou = np.mean(iou_scores)
    
    logger.info(f"Evaluation complete: {len(metrics)} images")
    logger.info(f"Mean Dice: {mean_dice:.4f}")
    logger.info(f"Mean IoU: {mean_iou:.4f}")
    
    return mean_dice, mean_iou 