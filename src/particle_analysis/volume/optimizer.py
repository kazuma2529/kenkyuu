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
import math
from dataclasses import asdict
try:
    import pandas as pd
except Exception:  # pandas は実行環境により未導入の場合があるため遅延依存
    pd = None  # type: ignore

from .data_structures import OptimizationResult, OptimizationSummary
from .core import split_particles_in_memory
from .metrics.basic import calculate_largest_particle_ratio
from .optimization.algorithms import (
    determine_best_radius_advanced,
    determine_best_radius_pareto_distance,
)

logger = logging.getLogger(__name__)


def optimize_radius_advanced(
    vol_path: str | None,
    output_dir: str,
    radii: List[int],
    connectivity: int = 6,
    progress_callback: Optional[Callable[[OptimizationResult], None]] = None,
    complete_analysis: bool = True,
    early_stopping: bool = False,
    plateau_threshold: float = 0.01,
    # New selector params (GUI-configurable)
    tau_ratio: float = 0.05,
    tau_gain_rel: float = 0.003,
    contacts_range: tuple[int, int] = (4, 10),
    smoothing_window: Optional[int] = None,
    *,
    volume: Optional[np.ndarray] = None,
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

    # Load volume if only vol_path was provided
    if volume is None:
        if vol_path is None:
            raise ValueError("Either `volume` or `vol_path` must be provided")
        volume = np.load(str(vol_path)).astype(bool)

    for i, r in enumerate(radii):
        step_start_time = time.time()

        # Run particle splitting in-memory
        logger.info(f"Processing radius {r} ({i+1}/{len(radii)})...")
        labels = split_particles_in_memory(volume, radius=r, connectivity=connectivity)
        num_particles = int(labels.max())

        # Calculate additional metrics
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

    # Determine best radius using new hard-constraint + marginal gain + contacts range
    try:
        selection = _select_radius_by_constraints_from_summary(
            summary,
            tau_ratio=tau_ratio,
            tau_gain_rel=tau_gain_rel,
            contacts_range=contacts_range,
            smoothing_window=smoothing_window,
        )
        best_radius = selection["selected_radius"]
        explanation = (
            f"Selected by constraints: r={best_radius} | reason={selection['reason']} | "
            f"r_star={selection.get('r_star')} | thresholds={selection.get('thresholds')}"
        )
        summary.optimization_method = "HardConstraint+MarginalGain+ContactsRange"
    except Exception as e:
        logger.error(f"Constraint-based selection failed, fallback to Pareto+distance: {e}")
        best_radius, explanation = determine_best_radius_pareto_distance(summary)
        summary.optimization_method = "Pareto+distance (fallback)"

    summary.best_radius = best_radius
    summary.total_processing_time = time.time() - start_time

    logger.info(f"Optimization completed in {summary.total_processing_time:.1f}s")
    logger.info(explanation)

    # Save optimization_results.csv
    try:
        if pd is None:
            logger.warning("pandas not available; skipping optimization_results.csv save")
        else:
            df = _summary_to_dataframe(summary)
            (output_dir / "").mkdir(parents=True, exist_ok=True)
            df.to_csv(output_dir / "optimization_results.csv", index=False)
            logger.info("Saved optimization_results.csv")
    except Exception as e:
        logger.warning(f"Failed to save optimization_results.csv: {e}")

    # Save only the selected labels to disk
    try:
        sel_r = int(summary.best_radius)
        logger.info(f"Saving labels for selected radius r={sel_r}")
        sel_labels = None
        # Recompute labels for selected radius to avoid keeping all in memory
        sel_labels = split_particles_in_memory(volume, radius=sel_r, connectivity=connectivity)
        np.save(output_dir / f"labels_r{sel_r}.npy", sel_labels.astype(np.int32))
        logger.info(f"Saved labels_r{sel_r}.npy")
    except Exception as e:
        logger.error(f"Failed to save selected labels: {e}")

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


# ---- New constraint-based selector (public helper) ---------------------------------------

def select_radius_by_constraints(
    results_df,
    *,
    tau_ratio: float = 0.05,
    tau_gain_rel: float = 0.003,
    contacts_range: tuple[int, int] = (4, 10),
    smoothing_window: Optional[int] = None,
):
    """Select radius by hard-constraint + marginal gain + contacts range.

    Args:
        results_df: pandas DataFrame like with columns [radius, particle_count, largest_particle_ratio, mean_contacts]
        tau_ratio: threshold for largest_particle_ratio
        tau_gain_rel: relative threshold (e.g., 0.003 == 0.3%) referenced to particle_count at r*
        contacts_range: acceptable range for mean_contacts (inclusive)
        smoothing_window: optional window size (1 or 2 recommended) for moving average smoothing

    Returns:
        dict with keys: selected_radius, r_star, reason, thresholds, fallback_path_index
    """
    if pd is None:
        raise RuntimeError("pandas is required for select_radius_by_constraints")

    required_cols = {"radius", "particle_count", "largest_particle_ratio", "mean_contacts"}
    missing = required_cols - set(results_df.columns)
    if missing:
        raise ValueError(f"results_df missing columns: {sorted(missing)}")

    df = results_df.copy().sort_values("radius").reset_index(drop=True)
    df = df.dropna(subset=list(required_cols))

    # Optional smoothing for stability (applied only to decision signals)
    def _ma(series):
        if smoothing_window is None or smoothing_window in (0, 1):
            return series
        w = int(smoothing_window)
        if w <= 1:
            return series
        return series.rolling(window=w, min_periods=1, center=True).mean()

    lpr = _ma(df["largest_particle_ratio"])  # largest particle ratio
    pc = _ma(df["particle_count"])  # particle count

    # 1) r* (first r s.t. lpr <= tau_ratio)
    mask_pass = lpr <= tau_ratio
    if mask_pass.any():
        idx_star = int(mask_pass.idxmax())  # first True index
        r_star = int(df.loc[idx_star, "radius"])
    else:
        # Not found -> define r* as minimum radius (for fallback path bookkeeping)
        r_star = int(df.loc[0, "radius"]) if len(df) else None

    # 2) simultaneous conditions from r >= r*
    if r_star is not None:
        df_after = df[df["radius"] >= r_star].copy()
        pc_after = pc[df_after.index]
        lpr_after = lpr[df_after.index]
    else:
        df_after = df.copy()
        pc_after = pc
        lpr_after = lpr

    # Base for marginal gain threshold
    if r_star is not None:
        base_count = float(df.loc[df["radius"] == r_star, "particle_count"].iloc[0])
    else:
        base_count = float(df["particle_count"].iloc[0]) if len(df) else 0.0

    th_gain = math.ceil(base_count * float(tau_gain_rel))

    # Compute Δcount = pc(r) - pc(r-1) in the sorted order
    # For the very first row, Δcount is undefined; we set a large value so it won't pass.
    dcount = pc.diff().fillna(np.inf)

    cmin, cmax = contacts_range

    def _first_index(iter_idx):
        try:
            return int(next(iter(iter_idx)))
        except StopIteration:
            return None

    # (A) both conditions (Δcount <= th_gain) AND (contacts in range)
    idx_both = _first_index(
        i for i in df_after.index
        if (dcount.loc[i] <= th_gain) and (cmin <= df.loc[i, "mean_contacts"] <= cmax)
    )
    if idx_both is not None:
        sel_r = int(df.loc[idx_both, "radius"])
        return {
            "selected_radius": sel_r,
            "r_star": r_star,
            "reason": "both",
            "thresholds": {"tau_ratio": tau_ratio, "tau_gain_rel": tau_gain_rel, "gain_abs": th_gain, "contacts_range": (cmin, cmax)},
            "fallback_path_index": 0,
        }

    # (B) contacts only
    idx_contacts = _first_index(
        i for i in df_after.index
        if (cmin <= df.loc[i, "mean_contacts"] <= cmax)
    )
    if idx_contacts is not None:
        sel_r = int(df.loc[idx_contacts, "radius"])
        return {
            "selected_radius": sel_r,
            "r_star": r_star,
            "reason": "contacts_only",
            "thresholds": {"tau_ratio": tau_ratio, "tau_gain_rel": tau_gain_rel, "gain_abs": th_gain, "contacts_range": (cmin, cmax)},
            "fallback_path_index": 1,
        }

    # (C) r*
    if r_star is not None:
        return {
            "selected_radius": int(r_star),
            "r_star": r_star,
            "reason": "r_star",
            "thresholds": {"tau_ratio": tau_ratio, "tau_gain_rel": tau_gain_rel, "gain_abs": th_gain, "contacts_range": (cmin, cmax)},
            "fallback_path_index": 2,
        }

    # (D) max r
    if len(df) == 0:
        raise ValueError("No results to select from")
    sel_r = int(df["radius"].max())
    return {
        "selected_radius": sel_r,
        "r_star": r_star,
        "reason": "max_r",
        "thresholds": {"tau_ratio": tau_ratio, "tau_gain_rel": tau_gain_rel, "gain_abs": th_gain, "contacts_range": (cmin, cmax)},
        "fallback_path_index": 3,
    }


def _summary_to_dataframe(summary: "OptimizationSummary"):
    if pd is None:
        raise RuntimeError("pandas is required for _summary_to_dataframe")
    rows = []
    for res in summary.results:
        rows.append({
            "radius": res.radius,
            "particle_count": res.particle_count,
            "largest_particle_ratio": res.largest_particle_ratio,
            "mean_contacts": res.mean_contacts,
        })
    return pd.DataFrame(rows)


def _select_radius_by_constraints_from_summary(
    summary: "OptimizationSummary",
    *,
    tau_ratio: float = 0.05,
    tau_gain_rel: float = 0.003,
    contacts_range: tuple[int, int] = (4, 10),
    smoothing_window: Optional[int] = None,
):
    df = _summary_to_dataframe(summary)
    return select_radius_by_constraints(
        df,
        tau_ratio=tau_ratio,
        tau_gain_rel=tau_gain_rel,
        contacts_range=contacts_range,
        smoothing_window=smoothing_window,
    )