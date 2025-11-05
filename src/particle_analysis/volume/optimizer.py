"""Main optimization orchestration functions.

This module provides the high-level optimization functions that coordinate
all aspects of radius optimization including volume processing, metric calculation,
and best radius determination.
"""

import logging
import time
from pathlib import Path
from typing import List, Optional, Callable

import numpy as np

from .data_structures import OptimizationResult, OptimizationSummary
from .core import split_particles
from .metrics.basic import calculate_largest_particle_ratio
from .optimization.algorithms import (
    determine_best_radius_advanced,
    determine_best_radius_pareto_distance,
)

logger = logging.getLogger(__name__)


def optimize_radius_advanced(
    vol_path: str,
    output_dir: str,
    radii: List[int],
    connectivity: int = 6,
    progress_callback: Optional[Callable[[OptimizationResult], None]] = None,
    complete_analysis: bool = True,
    early_stopping: bool = False,
    plateau_threshold: float = 0.01,
) -> OptimizationSummary:
    """Advanced radius optimization with comprehensive analysis.

    Args:
        vol_path: Path to 3D volume (.npy file)
        output_dir: Directory for temporary files
        radii: List of radii to evaluate (e.g., [1,2,3,4,5,6,7,8,9,10])
        connectivity: Connectivity for labeling (6 or 26)
        progress_callback: Function called after each radius evaluation
        complete_analysis: If True, calculate all metrics including contacts
        early_stopping: If True, stop at plateau detection
        plateau_threshold: Threshold for plateau detection

    Returns:
        OptimizationSummary with all results and best radius
    """
    from collections import OrderedDict

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = OptimizationSummary()
    start_time = time.time()
    prev_count: int | None = None

    logger.info(f"Starting advanced radius optimization for radii: {radii}")

    for i, r in enumerate(radii):
        step_start_time = time.time()

        # File paths
        label_path = output_dir / f"labels_r{r}.npy"
        
        # Check for cached results
        if label_path.exists():
            logger.debug(f"Re-using cached labels for radius {r}")
            labels = np.load(label_path)
            num_particles = int(labels.max())
        else:
            # Run particle splitting
            logger.info(f"Processing radius {r} ({i+1}/{len(radii)})...")
            num_particles = split_particles(
                vol_path=str(vol_path),
                out_labels=str(label_path),
                radius=r,
                connectivity=connectivity,
            )
        
        # Calculate additional metrics
        labels = np.load(label_path)
        largest_ratio, largest_vol, total_vol = calculate_largest_particle_ratio(labels)

        # Calculate mean contacts if requested
        mean_contacts = 0.0
        if complete_analysis and num_particles > 0:
            logger.info(f"Starting contact calculation for r={r} with {num_particles} particles using connectivity={connectivity}")
            try:
                # Import from contact package
                from ..contact import count_contacts
                logger.info(f"Successfully imported count_contacts function")
                
                # Use the connectivity parameter passed to optimize_radius_advanced
                contacts_dict = count_contacts(labels, connectivity=connectivity)
                
                if contacts_dict and len(contacts_dict) > 0:
                    contact_values = list(contacts_dict.values())
                    mean_contacts = np.mean(contact_values)
                    logger.info(f"✅ Contact calculation successful for r={r}: {mean_contacts:.1f} (from {len(contact_values)} particles)")
                else:
                    logger.warning(f"❌ No contacts returned for radius {r} (dict empty or None)")
                    mean_contacts = 0.0
                    
            except ImportError as e:
                logger.error(f"❌ Import error for contact calculation (r={r}): {e}")
                mean_contacts = 0.0
            except Exception as e:
                logger.error(f"❌ Contact calculation failed for radius {r}: {e}")
                import traceback
                traceback.print_exc()
                mean_contacts = 0.0
        else:
            if not complete_analysis:
                logger.info(f"Skipping contact analysis for r={r} (complete_analysis=False)")
            elif num_particles == 0:
                logger.info(f"Skipping contact analysis for r={r} (no particles detected)")
                
        logger.info(f"Final mean_contacts for r={r}: {mean_contacts:.1f}")

        processing_time = time.time() - step_start_time

        # Create result
        result = OptimizationResult(
            radius=r,
            particle_count=num_particles,
            mean_contacts=mean_contacts,
            largest_particle_ratio=largest_ratio,
            processing_time=processing_time,
            labels_path=str(label_path),
            total_volume=total_vol,
            largest_particle_volume=largest_vol
        )

        summary.add_result(result)

        # Call progress callback for real-time updates
        if progress_callback:
            try:
                progress_callback(result)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")

        logger.info(
            f"Radius {r}: {num_particles} particles, "
            f"{largest_ratio:.1%} largest, "
            f"{mean_contacts:.1f} avg contacts"
        )

        # Early stopping check
        if early_stopping and prev_count is not None and prev_count > 0:
            rel_change = abs(num_particles - prev_count) / prev_count
            if rel_change < plateau_threshold:
                logger.info(f"Early stopping at r={r} (plateau reached)")
                break
        
        prev_count = num_particles

    # Determine best radius using Pareto + distance selection (new default)
    best_radius, explanation = determine_best_radius_pareto_distance(summary)
    summary.best_radius = best_radius
    summary.optimization_method = "Pareto+distance (HHI, knee, VI)"
    summary.total_processing_time = time.time() - start_time

    logger.info(f"Optimization completed in {summary.total_processing_time:.1f}s")
    logger.info(explanation)

    return summary


# Legacy wrapper for backward compatibility
def optimize_radius(
    vol_path: str,
    output_dir: str,
    radii: List[int],
    connectivity: int = 6,
    plateau_threshold: float = 0.01,
    min_particles: int | None = None,
    max_particles: int | None = None,
) -> tuple[int, dict[int, int]]:
    """Legacy wrapper for backward compatibility.

    This maintains the old API while using the new advanced optimization internally.
    """
    summary = optimize_radius_advanced(
        vol_path=vol_path,
        output_dir=output_dir,
        radii=radii,
        connectivity=connectivity,
        complete_analysis=False,  # Skip contact analysis for speed
        early_stopping=True,
        plateau_threshold=plateau_threshold
    )

    # Convert to old format
    counts = {result.radius: result.particle_count for result in summary.results}

    return summary.best_radius, counts

__all__ = ["optimize_radius_advanced", "optimize_radius"] 