"""
Rapid testing script for binarization methods.
Usage: python scripts/test_binarization.py <path_to_tif_folder>
"""

import sys
import argparse
from pathlib import Path
import cv2
import numpy as np
from skimage.filters import threshold_otsu, threshold_triangle, threshold_multiotsu
from skimage.exposure import equalize_adapthist
from skimage.util import img_as_ubyte

def load_middle_slice(folder_path: Path) -> np.ndarray:
    """Load the middle slice from a folder of TIF images."""
    if not folder_path.exists():
        raise ValueError(f"Folder not found: {folder_path}")
        
    image_files = sorted(list(folder_path.glob("*.tif")) + list(folder_path.glob("*.tiff")))
    if not image_files:
        raise ValueError(f"No TIF images found in {folder_path}")
        
    mid_idx = len(image_files) // 2
    img_path = image_files[mid_idx]
    print(f"Loading middle slice ({mid_idx + 1}/{len(image_files)}): {img_path.name}")
    
    img = cv2.imread(str(img_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"Failed to load image: {img_path}")
        
    print(f"Image stats: shape={img.shape}, dtype={img.dtype}, min={img.min()}, max={img.max()}, mean={img.mean():.2f}")
    return img

def apply_clahe(image: np.ndarray) -> np.ndarray:
    """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)."""
    # normalize to 0-1 for skimage
    if image.dtype == np.uint16:
        img_norm = image / 65535.0
    elif image.dtype == np.uint8:
        img_norm = image / 255.0
    else:
        img_norm = (image - image.min()) / (image.max() - image.min())
        
    # Apply CLAHE
    img_clahe = equalize_adapthist(img_norm, kernel_size=None, clip_limit=0.01, nbins=256)
    
    # Return as float 0-1
    return img_clahe

def normalize_for_display(img: np.ndarray) -> np.ndarray:
    """Normalize image to 8-bit for display."""
    if img.dtype == bool:
        return (img.astype(np.uint8) * 255)
    
    img = img.astype(float)
    img_min, img_max = img.min(), img.max()
    if img_max == img_min:
        return np.zeros_like(img, dtype=np.uint8)
        
    img = (img - img_min) / (img_max - img_min)
    return (img * 255).astype(np.uint8)

def to_bgr(img, title):
    norm = normalize_for_display(img)
    bgr = cv2.cvtColor(norm, cv2.COLOR_GRAY2BGR)
    cv2.putText(bgr, title, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    return bgr

def main():
    parser = argparse.ArgumentParser(description="Test binarization methods on TIF images.")
    parser.add_argument("folder_path", type=str, help="Path to folder containing TIF images")
    args = parser.parse_args()
    
    folder = Path(args.folder_path)
    try:
        original = load_middle_slice(folder)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
        
    # --- Analysis of Histogram ---
    # Check if we have a huge background peak
    hist, bins = np.histogram(original.ravel(), bins=256)
    print(f"Histogram peak at bin {np.argmax(hist)} (count={hist.max()})")
    
    # --- Method 1: Global Otsu (Current Fail) ---
    thresh_otsu = threshold_otsu(original)
    binary_otsu = original > thresh_otsu
    print(f"Global Otsu Threshold: {thresh_otsu}")

    # --- Method 2: Masked Otsu (Hierarchical) ---
    # Step 1: Separate Object from Background (0)
    # If background is 0, we can just use > 0.
    # If background is noisy, use a low threshold (e.g. Otsu on full image)
    
    # Let's assume the first Otsu (thresh_otsu) successfully separates Background (0) from Object (Gray)
    # The user result showed T=0.0. This implies everything > 0 is Object.
    
    # Mask of the object (ROI)
    roi_mask = original > thresh_otsu
    roi_pixels = original[roi_mask]
    
    if len(roi_pixels) == 0:
        print("Warning: ROI mask is empty!")
        binary_masked_otsu = np.zeros_like(original, dtype=bool)
        thresh_masked = 0
    else:
        # Step 2: Apply Otsu on ROI pixels only
        thresh_masked = threshold_otsu(roi_pixels)
        print(f"Masked Otsu Threshold (on ROI): {thresh_masked}")
        binary_masked_otsu = np.zeros_like(original, dtype=bool)
        # Apply threshold only inside ROI
        binary_masked_otsu[roi_mask] = original[roi_mask] > thresh_masked

    # --- Method 3: CLAHE + Masked Otsu ---
    clahe_img = apply_clahe(original) # Float 0-1
    
    # Determine ROI for CLAHE image
    # We can use the same spatial mask from original, or re-calculate
    # Let's re-calculate to be safe
    t_clahe_global = threshold_otsu(clahe_img)
    roi_mask_clahe = clahe_img > t_clahe_global
    roi_pixels_clahe = clahe_img[roi_mask_clahe]
    
    if len(roi_pixels_clahe) == 0:
         binary_clahe_masked = np.zeros_like(original, dtype=bool)
         t_clahe_local = 0
    else:
        t_clahe_local = threshold_otsu(roi_pixels_clahe)
        print(f"CLAHE Masked Otsu Threshold: {t_clahe_local:.4f}")
        binary_clahe_masked = np.zeros_like(original, dtype=bool)
        binary_clahe_masked[roi_mask_clahe] = clahe_img[roi_mask_clahe] > t_clahe_local

    # --- Method 4: Triangle on ROI ---
    if len(roi_pixels) > 0:
        try:
            t_tri = threshold_triangle(roi_pixels)
            print(f"Masked Triangle Threshold: {t_tri}")
            binary_masked_tri = np.zeros_like(original, dtype=bool)
            binary_masked_tri[roi_mask] = original[roi_mask] > t_tri
        except:
            binary_masked_tri = np.zeros_like(original, dtype=bool)
            t_tri = 0
    else:
        binary_masked_tri = np.zeros_like(original, dtype=bool)
        t_tri = 0

    # --- Polarity Check (Simple heuristic) ---
    # If > 50% pixels are True, invert.
    def check_polarity(mask):
        if mask.mean() > 0.5:
            return ~mask
        return mask

    # Apply polarity check to all *final* masks
    # Note: ROI mask should NOT be inverted usually, it defines the container.
    # But the internal segmentation (Sand vs Gap) might need inversion.
    
    # Logic: Sand is solid (High val?). Gap is Air (Low val?).
    # If Threshold separates Low (Gap) from High (Sand).
    # Mask = > Threshold -> Sand.
    # If Sand is majority, we might want to keep it as True?
    # Usually "Particles" are foreground (True).
    # If Sand > 50% of volume, keep as True?
    # The previous code flipped it if > 50%.
    # Let's just visualize "as is" and "inverted" if needed, but for now stick to the logic:
    # "White = Foreground".
    
    binary_masked_otsu = check_polarity(binary_masked_otsu)
    binary_clahe_masked = check_polarity(binary_clahe_masked)
    binary_masked_tri = check_polarity(binary_masked_tri)

    # Prepare visualization
    vis_original = to_bgr(original, "Original")
    vis_roi = to_bgr(roi_mask, f"ROI (Global T={thresh_otsu:.1f})")
    
    vis_masked_otsu = to_bgr(binary_masked_otsu, f"Masked Otsu (T={thresh_masked:.1f})")
    vis_masked_tri = to_bgr(binary_masked_tri, f"Masked Triangle (T={t_tri:.1f})")
    
    vis_clahe_masked = to_bgr(binary_clahe_masked, f"CLAHE + Masked Otsu")
    vis_clahe_raw = to_bgr(clahe_img, "CLAHE Raw")

    # Stack grid
    def resize(img):
        scale = 500 / img.shape[1]
        return cv2.resize(img, (500, int(img.shape[0] * scale)))

    imgs = [vis_original, vis_roi, vis_masked_otsu, vis_masked_tri, vis_clahe_raw, vis_clahe_masked]
    imgs = [resize(img) for img in imgs]
    
    row1 = np.hstack([imgs[0], imgs[1]])
    row2 = np.hstack([imgs[2], imgs[3]])
    row3 = np.hstack([imgs[4], imgs[5]])
    grid = np.vstack([row1, row2, row3])
    
    out_path = "binarization_test_v2.png"
    cv2.imwrite(out_path, grid)
    print(f"Result saved to {out_path}")

if __name__ == "__main__":
    main()
