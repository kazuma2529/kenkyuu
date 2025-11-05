"""Plot utilities for GUI histograms.

Centralizes small helpers to keep widget code concise and consistent.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np


def robust_upper_bound(values: Iterable[float], percentile: float, safety: float = 1.05) -> float:
    """Return a robust upper x-limit based on a high percentile with safety margin.

    Args:
        values: sequence of numeric values
        percentile: e.g. 99.0 or 99.5
        safety: multiplicative margin (default 1.05)
    """
    arr = np.asarray(list(values))
    if arr.size == 0:
        return 0.0
    if arr.size <= 10:
        upper = float(arr.max(initial=0))
    else:
        upper = float(np.percentile(arr, percentile))
    return upper * safety


def style_dark_axes(ax) -> None:
    ax.set_facecolor('#2c313a')
    for side in ('bottom', 'top', 'left', 'right'):
        ax.spines[side].set_color('white')
    ax.tick_params(colors='white')
    ax.grid(True, alpha=0.3, color='white')


def set_legend_white(legend) -> None:
    if legend is None:
        return
    for text in legend.get_texts():
        text.set_color('white')
    frame = legend.get_frame()
    if frame is not None:
        frame.set_edgecolor('white')
        frame.set_facecolor('#23272e')


__all__ = [
    'robust_upper_bound',
    'style_dark_axes',
    'set_legend_white',
]


