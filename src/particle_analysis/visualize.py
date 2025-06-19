"""Interactive 3-D visualization helpers (napari).

All functions in this module are optional and require
`napari` (and its Qt backend) to be installed.
"""

from pathlib import Path
from typing import Optional, Union

import numpy as np

try:
    import napari  # type: ignore
except ImportError as e:  # pragma: no cover
    napari = None  # type: ignore


class NapariUnavailable(RuntimeError):
    """Raised when a napari-dependent call is invoked without napari present."""


def _ensure_napari() -> None:
    if napari is None:
        raise NapariUnavailable(
            "napari is not installed.\n"
            "Install with:  pip install \"napari[all]\"  (recommended)"
        )


def view_volume(
    volume: Union[str, Path, np.ndarray],
    labels: Optional[Union[str, Path, np.ndarray]] = None,
    *,
    rendering: str = "mip",
    title: str = "3D Volume",
) -> None:
    """Launch an interactive napari viewer for a 3-D volume (and labels).

    Parameters
    ----------
    volume
        Path to ``.npy`` file  **or** a 3-D ``numpy.ndarray`` of bool/uint8.
    labels
        Optional path/array of same shape containing integer labels.
    rendering
        napari 3-D rendering mode.  One of ``"mip" | "attenuated_mip" | "iso"``.
    title
        Window title.
    """
    _ensure_napari()

    # ---------- Load data ----------
    if isinstance(volume, (str, Path)):
        volume_arr = np.load(volume)  # type: ignore[arg-type]
    else:
        volume_arr = volume

    if labels is not None:
        if isinstance(labels, (str, Path)):
            labels_arr: Optional[np.ndarray] = np.load(labels)  # type: ignore[arg-type]
        else:
            labels_arr = labels
    else:
        labels_arr = None

    # Napari expects bool/uint8 for image and int for labels.
    if volume_arr.dtype != np.uint8 and volume_arr.dtype != bool:
        volume_arr = volume_arr.astype(np.uint8)
    if volume_arr.dtype == bool:
        volume_arr = volume_arr.astype(np.uint8) * 255

    viewer = napari.Viewer(title=title)
    viewer.add_image(volume_arr, name="volume", rendering=rendering, contrast_limits=(0, 255))

    if labels_arr is not None:
        labels_layer = viewer.add_labels(labels_arr.astype(np.int32), name="labels", blending="translucent")

        # --------------------------------------------------
        # Click callback: show particle ID in viewer status bar
        # --------------------------------------------------

        def _show_label_id(layer, event):  # type: ignore[override]
            # event.position gives (z, y, x) in data coordinates
            pos = tuple(int(round(c)) for c in event.position)
            if any(p < 0 for p in pos):
                return  # outside data
            if any(p >= s for p, s in zip(pos, labels_arr.shape)):
                return
            label_val = int(labels_arr[pos])
            viewer.status = f"Clicked Label ID: {label_val}"

        # 左クリック（ドラッグ開始）で取得
        labels_layer.mouse_drag_callbacks.append(_show_label_id)

    napari.run()


__all__ = ["view_volume", "NapariUnavailable"] 