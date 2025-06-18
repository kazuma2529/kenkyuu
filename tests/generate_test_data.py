import cv2
import numpy as np
from pathlib import Path

# Create test images
size = (256, 256)
test_images = {
    "CT001.png": np.random.randint(0, 256, size, dtype=np.uint8),
    "CT002.png": np.random.randint(0, 256, size, dtype=np.uint8),
    "CT003.png": np.random.randint(0, 256, size, dtype=np.uint8)
}

# Create corresponding masks (simple circles)
for i, filename in enumerate(test_images.keys(), 1):
    # Original image
    cv2.imwrite(f"data/images/{filename}", test_images[filename])
    
    # Create mask with a circle
    mask = np.zeros(size, dtype=np.uint8)
    center = (128, 128)
    radius = 50 + i * 10  # Different size for each image
    cv2.circle(mask, center, radius, 255, -1)
    
    # Save both Otsu and GT masks (identical for testing)
    cv2.imwrite(f"data/masks_otsu/{filename}", mask)
    cv2.imwrite(f"data/masks_gt/{filename}", mask)

print("Test data generated successfully!") 