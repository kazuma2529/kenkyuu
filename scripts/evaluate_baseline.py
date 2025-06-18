#!/usr/bin/env python3
"""Evaluate baseline masks against ground truth."""

import argparse
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from particle_analysis.evaluation import evaluate_masks


def main():
    parser = argparse.ArgumentParser(description="Evaluate baseline masks against ground truth")
    parser.add_argument("--img_dir", default="data/images",
                       help="Directory containing original CT images")
    parser.add_argument("--mask_dir", default="data/masks_otsu",
                       help="Directory containing baseline masks")
    parser.add_argument("--gt_dir", required=True,
                       help="Directory containing ground truth masks")
    parser.add_argument("--out_csv", default="evaluation_results.csv",
                       help="Output CSV file for detailed results")
    
    args = parser.parse_args()
    
    mean_dice, mean_iou = evaluate_masks(
        args.img_dir,
        args.mask_dir,
        args.gt_dir,
        args.out_csv
    )
    
    print(f"\nEvaluation Results:")
    print(f"Mean Dice: {mean_dice:.4f}")
    print(f"Mean IoU: {mean_iou:.4f}")
    print(f"Detailed results saved to: {args.out_csv}")


if __name__ == "__main__":
    main() 