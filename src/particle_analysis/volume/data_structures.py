"""Data structures for volume optimization results.

This module defines the core data structures used throughout the
optimization process to store and manage results.
"""

import time
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np


@dataclass
class OptimizationResult:
    """Results from radius optimization for a single radius value."""
    radius: int
    particle_count: int
    mean_contacts: float = 0.0
    largest_particle_ratio: float = 0.0
    processing_time: float = 0.0
    labels_path: str = ""
    total_volume: int = 0
    largest_particle_volume: int = 0
    # Guard volume statistics
    interior_particle_count: int = 0
    excluded_particle_count: int = 0

    def __post_init__(self):
        """Calculate derived metrics after initialization."""
        if self.total_volume > 0 and self.largest_particle_volume > 0:
            self.largest_particle_ratio = self.largest_particle_volume / self.total_volume


@dataclass
class OptimizationSummary:
    """Complete summary of radius optimization process."""
    results: List[OptimizationResult] = field(default_factory=list)
    best_radius: int = 0
    optimization_method: str = ""
    total_processing_time: float = 0.0

    def add_result(self, result: OptimizationResult):
        """Add a new result to the summary."""
        self.results.append(result)

    def get_result_by_radius(self, radius: int) -> Optional[OptimizationResult]:
        """Get result for specific radius."""
        for result in self.results:
            if result.radius == radius:
                return result
        return None

    def to_dataframe(self):
        """Convert results to pandas DataFrame for easy analysis."""
        try:
            import pandas as pd
            data = []
            for result in self.results:
                data.append({
                    'radius': result.radius,
                    'particle_count': result.particle_count,
                    'mean_contacts': result.mean_contacts,
                    'largest_particle_ratio': result.largest_particle_ratio,
                    'processing_time': result.processing_time,
                    'total_volume': result.total_volume,
                    'largest_particle_volume': result.largest_particle_volume,
                    'interior_particle_count': result.interior_particle_count,
                    'excluded_particle_count': result.excluded_particle_count
                })
            return pd.DataFrame(data)
        except ImportError:
            import logging
            logging.getLogger(__name__).warning("pandas not available for DataFrame conversion")
            return None

__all__ = ["OptimizationResult", "OptimizationSummary"] 