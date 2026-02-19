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
try:
    import pandas as pd
except Exception:  # pandas は実行環境により未導入の場合があるため遅延依存
    pd = None  # type: ignore

from .data_structures import OptimizationResult, OptimizationSummary
from .core import split_particles_in_memory
from .metrics.basic import calculate_largest_particle_ratio
from .optimization.algorithms import determine_best_radius_pareto_distance

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
    tau_ratio: float = 0.03,
    contacts_range: tuple[int, int] = (5, 9),
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

        # Calculate mean contacts if requested (with guard volume filtering)
        mean_contacts = 0.0
        interior_particle_count = 0
        excluded_particle_count = 0
        
        if complete_analysis and num_particles > 0:
            logger.info(f"Starting contact calculation for r={r} with {num_particles} particles using connectivity={connectivity}")
            try:
                # Import guard volume functions
                from ..contact.guard_volume import count_contacts_with_guard
                logger.info(f"Successfully imported count_contacts_with_guard function")
                
                # Count contacts with guard volume filtering
                # This counts contacts for ALL particles, but filters statistics to interior only
                full_contacts, interior_contacts, guard_stats = count_contacts_with_guard(
                    labels,
                    connectivity=connectivity
                )
                
                # Use interior particles for mean contacts (primary metric)
                if interior_contacts and len(interior_contacts) > 0:
                    interior_contact_values = list(interior_contacts.values())
                    mean_contacts = np.mean(interior_contact_values)
                    
                    interior_particle_count = guard_stats['interior_particles']
                    excluded_particle_count = guard_stats['excluded_particles']
                    
                    logger.info(
                        f"✅ Contact calculation successful for r={r}: "
                        f"mean={mean_contacts:.1f} (interior particles only, "
                        f"{interior_particle_count} interior / {guard_stats['total_particles']} total)"
                    )
                else:
                    logger.warning(f"❌ No interior contacts returned for radius {r} (dict empty or None)")
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

        # Create result (labels_path is empty since we don't save intermediate files)
        result = OptimizationResult(
            radius=r,
            particle_count=num_particles,
            mean_contacts=mean_contacts,
            largest_particle_ratio=largest_ratio,
            processing_time=processing_time,
            labels_path="",  # Empty for in-memory processing (only selected radius is saved)
            total_volume=total_vol,
            largest_particle_volume=largest_vol,
            interior_particle_count=interior_particle_count,
            excluded_particle_count=excluded_particle_count
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

    # Determine best radius using hard-constraint + peak particle count + contacts range
    try:
        selection = _select_radius_by_constraints_from_summary(
            summary,
            tau_ratio=tau_ratio,
            contacts_range=contacts_range,
            smoothing_window=smoothing_window,
        )
        best_radius = selection["selected_radius"]
        explanation = (
            f"Selected by constraints: r={best_radius} | reason={selection['reason']} | "
            f"r_star={selection.get('r_star')} | r_peak={selection.get('r_peak')} | thresholds={selection.get('thresholds')}"
        )
        summary.optimization_method = "HardConstraint+PeakCount+ContactsRange"
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
    tau_ratio: float = 0.03,
    contacts_range: tuple[int, int] = (5, 9),
    smoothing_window: Optional[int] = None,
):
    """Select radius by hard-constraint + peak particle count + contacts range.

    Selection logic:
      1) r* = first R where largest_particle_ratio <= tau_ratio
      2) R_peak = R with maximum particle_count among {R >= r* AND lpr <= tau_ratio}
      3) Priority:
         (A) R_peak if mean_contacts in contacts_range
         (B) First R >= r* where mean_contacts in contacts_range
         (C) R_peak (without contacts constraint)
         (D) r*
         (E) max R (last resort)

    Args:
        results_df: pandas DataFrame with columns [radius, particle_count, largest_particle_ratio, mean_contacts]
        tau_ratio: threshold for largest_particle_ratio (default 0.03 = 3%)
        contacts_range: acceptable range for mean_contacts (default (5, 9), inclusive)
        smoothing_window: optional window size (1 or 2 recommended) for moving average smoothing

    Returns:
        dict with keys: selected_radius, r_star, r_peak, reason, thresholds, fallback_path_index
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

    cmin, cmax = contacts_range
    thresholds = {"tau_ratio": tau_ratio, "contacts_range": (cmin, cmax)}

    # 1) r* (first r s.t. lpr <= tau_ratio)
    mask_pass = lpr <= tau_ratio
    if mask_pass.any():
        idx_star = int(mask_pass.idxmax())  # first True index
        r_star = int(df.loc[idx_star, "radius"])
    else:
        # Not found -> define r* as minimum radius (for fallback path bookkeeping)
        r_star = int(df.loc[0, "radius"]) if len(df) else None

    # 2) R_peak: among {R >= r* AND lpr <= tau_ratio}, find R with max particle_count
    r_peak = None
    idx_peak = None
    if r_star is not None:
        valid_mask = (df["radius"] >= r_star) & (lpr <= tau_ratio)
        df_valid = df[valid_mask]
        if len(df_valid) > 0:
            pc_valid = pc[df_valid.index]
            idx_peak = int(pc_valid.idxmax())
            r_peak = int(df.loc[idx_peak, "radius"])

    # 3) Selection priority

    # (A) R_peak AND mean_contacts in range
    if r_peak is not None and idx_peak is not None:
        mc_at_peak = float(df.loc[idx_peak, "mean_contacts"])
        if cmin <= mc_at_peak <= cmax:
            return {
                "selected_radius": r_peak,
                "r_star": r_star,
                "r_peak": r_peak,
                "reason": "peak_and_contacts",
                "thresholds": thresholds,
                "fallback_path_index": 0,
            }

    # (B) First R >= r* where mean_contacts in range
    if r_star is not None:
        df_after = df[df["radius"] >= r_star]
        for i in df_after.index:
            if cmin <= df.loc[i, "mean_contacts"] <= cmax:
                sel_r = int(df.loc[i, "radius"])
                return {
                    "selected_radius": sel_r,
                    "r_star": r_star,
                    "r_peak": r_peak,
                    "reason": "contacts_only",
                    "thresholds": thresholds,
                    "fallback_path_index": 1,
                }

    # (C) R_peak (without contacts constraint)
    if r_peak is not None:
        return {
            "selected_radius": r_peak,
            "r_star": r_star,
            "r_peak": r_peak,
            "reason": "r_peak",
            "thresholds": thresholds,
            "fallback_path_index": 2,
        }

    # (D) r*
    if r_star is not None:
        return {
            "selected_radius": int(r_star),
            "r_star": r_star,
            "r_peak": r_peak,
            "reason": "r_star",
            "thresholds": thresholds,
            "fallback_path_index": 3,
        }

    # (E) max r
    if len(df) == 0:
        raise ValueError("No results to select from")
    sel_r = int(df["radius"].max())
    return {
        "selected_radius": sel_r,
        "r_star": r_star,
        "r_peak": r_peak,
        "reason": "max_r",
        "thresholds": thresholds,
        "fallback_path_index": 4,
    }


def _select_radius_by_constraints_from_summary(
    summary: "OptimizationSummary",
    *,
    tau_ratio: float = 0.03,
    contacts_range: tuple[int, int] = (5, 9),
    smoothing_window: Optional[int] = None,
):
    df = _summary_to_dataframe(summary)
    return select_radius_by_constraints(
        df,
        tau_ratio=tau_ratio,
        contacts_range=contacts_range,
        smoothing_window=smoothing_window,
    )


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
            "interior_particle_count": res.interior_particle_count,
            "excluded_particle_count": res.excluded_particle_count,
        })
    return pd.DataFrame(rows)