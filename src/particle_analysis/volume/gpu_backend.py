"""GPU backend utilities for volume processing (experimental, January-kenkyuu only).

現時点では、距離変換と侵食の PyTorch 実装を用意しておき、
`split_particles_in_memory(..., backend="gpu")` から呼び出せるようにする。

note:
    - PyTorch がインストールされていない環境では ImportError を出し、
      呼び出し側で CPU backend にフォールバックできるようにする。
    - CUDA が利用できない場合は CPU で実行される。
"""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    torch = None  # type: ignore[assignment]
    F = None  # type: ignore[assignment]
    TORCH_AVAILABLE = False


def _ensure_torch_available() -> None:
    """PyTorch が利用可能かチェックし、なければ明示的に例外を投げる。"""
    if not TORCH_AVAILABLE or torch is None:
        raise ImportError(
            "PyTorch が見つかりません。"
            "GPU backend を使うには、`pip install torch` が必要です。"
        )


def _get_device() -> torch.device:
    """利用可能なデバイス（GPU/CPU）を取得する。"""
    _ensure_torch_available()
    if torch.cuda.is_available():
        return torch.device("cuda")
    else:
        logger.warning("CUDA not available, using CPU for GPU backend")
        return torch.device("cpu")


def binary_erosion_gpu(volume: np.ndarray, struct_elem: np.ndarray) -> np.ndarray:
    """GPU 上で 3D binary erosion を実行する（PyTorch実装）。
    
    Args:
        volume: Binary 3D volume (Z, Y, X)
        struct_elem: Structuring element (3D array)
    
    Returns:
        Eroded volume as numpy array
    """
    _ensure_torch_available()
    device = _get_device()
    
    # Convert to torch tensors
    vol_torch = torch.from_numpy(volume.astype(bool)).to(device)
    se_torch = torch.from_numpy(struct_elem.astype(bool)).to(device)
    
    # Get structuring element size
    se_shape = se_torch.shape
    kernel_size = tuple(se_shape)
    
    # For binary erosion with a structuring element, we use max_pool3d
    # with inverted volume (erosion = dilation of complement)
    # However, for a general structuring element, we need to use convolution
    
    # Convert to float for convolution
    vol_float = vol_torch.float()
    
    # Create kernel from structuring element
    # Flip the kernel for correlation (erosion needs flipped kernel)
    kernel = se_torch.float().flip(dims=(0, 1, 2))
    
    # Add batch and channel dimensions: (1, 1, Z, Y, X)
    vol_4d = vol_float.unsqueeze(0).unsqueeze(0)
    kernel_5d = kernel.unsqueeze(0).unsqueeze(0)
    
    # Perform correlation (erosion)
    # For binary erosion: output = 1 if all neighbors in SE are 1
    # This is equivalent to: min(conv(input, flipped_SE)) == sum(SE)
    conv_result = F.conv3d(vol_4d, kernel_5d, padding='same')
    
    # Erosion: all neighbors must be 1, so sum must equal kernel sum
    kernel_sum = kernel.sum().item()
    eroded = (conv_result >= kernel_sum).squeeze(0).squeeze(0)
    
    # Convert back to numpy
    result = eroded.cpu().numpy().astype(bool)
    
    logger.info("GPU binary_erosion completed (PyTorch)")
    return result


def distance_transform_edt_gpu(volume: np.ndarray) -> np.ndarray:
    """GPU 上で距離変換を実行する（PyTorch実装）。
    
    Euclidean Distance Transform (EDT) を実装します。
    scipy.ndimage.distance_transform_edt と同等の結果を返します。
    
    Args:
        volume: Binary 3D volume (Z, Y, X)
    
    Returns:
        Distance transform as numpy array
    """
    _ensure_torch_available()
    device = _get_device()
    
    # Convert to torch tensor
    vol_torch = torch.from_numpy(volume.astype(bool)).to(device)
    
    # Distance transform: distance from each False voxel to nearest True voxel
    # Invert: we want distance from background (False) to foreground (True)
    vol_inv = ~vol_torch
    
    # Get coordinates of foreground (True) voxels
    foreground_coords = torch.nonzero(vol_inv, as_tuple=False).float()
    
    if foreground_coords.numel() == 0:
        # No foreground, return zeros
        dist = torch.zeros_like(vol_torch, dtype=torch.float32)
        return dist.cpu().numpy()
    
    # Get all voxel coordinates
    z, y, x = vol_torch.shape
    z_coords, y_coords, x_coords = torch.meshgrid(
        torch.arange(z, device=device, dtype=torch.float32),
        torch.arange(y, device=device, dtype=torch.float32),
        torch.arange(x, device=device, dtype=torch.float32),
        indexing='ij'
    )
    all_coords = torch.stack([z_coords.flatten(), y_coords.flatten(), x_coords.flatten()], dim=1)
    
    # Compute distances: for each voxel, find minimum distance to any foreground voxel
    # This is memory-intensive but works correctly
    # Use chunking to avoid OOM errors for large volumes
    chunk_size = 10000
    n_voxels = all_coords.shape[0]
    min_distances = torch.full((n_voxels,), float('inf'), device=device, dtype=torch.float32)
    
    for i in range(0, n_voxels, chunk_size):
        end_idx = min(i + chunk_size, n_voxels)
        chunk_coords = all_coords[i:end_idx]
        
        # Compute Euclidean distances: (n_chunk, 3) to (n_foreground, 3)
        # Shape: (n_chunk, n_foreground)
        distances = torch.cdist(chunk_coords, foreground_coords, p=2)
        
        # Minimum distance for each voxel in chunk
        chunk_min = distances.min(dim=1)[0]
        min_distances[i:end_idx] = chunk_min
    
    # Reshape back to original volume shape
    dist = min_distances.reshape(vol_torch.shape)
    
    # Set foreground voxels to 0 (they are at distance 0 from themselves)
    dist[vol_inv] = 0.0
    
    logger.info("GPU distance_transform_edt completed (PyTorch)")
    return dist.cpu().numpy()


__all__ = ["binary_erosion_gpu", "distance_transform_edt_gpu"]

