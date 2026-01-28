"""GPU backend utilities for volume processing (experimental, January-kenkyuu only).

現時点では、距離変換と侵食の CuPy 実装を用意しておき、
`split_particles_in_memory(..., backend="gpu")` から呼び出せるようにする。

note:
    - CuPy がインストールされていない環境では ImportError を出し、
      呼び出し側で CPU backend にフォールバックできるようにする。
"""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)

try:
    import cupy as cp
    from cupyx.scipy import ndimage as cndimage
except Exception:  # CuPy がない環境用
    cp = None  # type: ignore[assignment]
    cndimage = None  # type: ignore[assignment]


def _ensure_cupy_available() -> None:
    """CuPy が利用可能かチェックし、なければ明示的に例外を投げる。"""
    if cp is None or cndimage is None:
        raise ImportError(
            "CuPy / cupyx.scipy が見つかりません。"
            "GPU backend を使うには、Colab などで `pip install cupy-cudaXX` が必要です。"
        )


def binary_erosion_gpu(volume: np.ndarray, struct_elem: np.ndarray) -> np.ndarray:
    """GPU 上で 3D binary erosion を実行する."""
    _ensure_cupy_available()

    vol_gpu = cp.asarray(volume.astype(bool))
    se_gpu = cp.asarray(struct_elem.astype(bool))

    eroded_gpu = cndimage.binary_erosion(vol_gpu, structure=se_gpu)
    eroded = cp.asnumpy(eroded_gpu)

    logger.info("GPU binary_erosion completed")
    return eroded


def distance_transform_edt_gpu(volume: np.ndarray) -> np.ndarray:
    """GPU 上で距離変換を実行する."""
    _ensure_cupy_available()

    vol_gpu = cp.asarray(volume.astype(bool))
    dist_gpu = cndimage.distance_transform_edt(vol_gpu)
    dist = cp.asnumpy(dist_gpu)

    logger.info("GPU distance_transform_edt completed")
    return dist


__all__ = ["binary_erosion_gpu", "distance_transform_edt_gpu"]

