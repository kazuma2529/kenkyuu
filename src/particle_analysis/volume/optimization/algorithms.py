"""Radius selection algorithms.

This module provides different algorithms for selecting the optimal radius
based on various optimization criteria:
- Advanced weighted composite method (legacy)
- Pareto + normalized distance method (new)
"""

import logging
from typing import Dict, List, Tuple

import numpy as np

from ..data_structures import OptimizationResult, OptimizationSummary
from ..metrics import (
    calculate_variation_of_information,
    calculate_hhi,
)
from .utils import (
    detect_knee_point,
    calculate_composite_score,
    calculate_coordination_score,
)

logger = logging.getLogger(__name__)


def determine_best_radius_advanced(summary: OptimizationSummary) -> Tuple[int, str]:
    """Determine best radius using advanced multi-criteria analysis.

    This is the legacy weighted composite method for backward compatibility.

    Args:
        summary: Optimization summary with all results

    Returns:
        tuple: (best_radius, explanation)
    """
    if not summary.results:
        return 0, "No results available"

    # Calculate composite scores for all results
    scored_results = []
    for result in summary.results:
        score = calculate_composite_score(result, summary.results)
        scored_results.append((result.radius, score, result))

    # Sort by score (descending)
    scored_results.sort(key=lambda x: x[1], reverse=True)

    best_radius, best_score, best_result = scored_results[0]

    # Generate explanation
    explanation_parts = []

    # Particle count analysis
    particle_counts = [r.particle_count for r in summary.results]
    radii = [r.radius for r in summary.results]
    if len(particle_counts) >= 3:
        knee_idx = detect_knee_point(radii, particle_counts)
        knee_radius = summary.results[knee_idx].radius
        explanation_parts.append(f"Knee point detected at r={knee_radius}")

    # Largest particle analysis
    if best_result.largest_particle_ratio <= 0.05:
        explanation_parts.append(f"Excellent particle separation ({best_result.largest_particle_ratio:.1%} largest)")
    elif best_result.largest_particle_ratio <= 0.20:
        explanation_parts.append(f"Good particle separation ({best_result.largest_particle_ratio:.1%} largest)")
    else:
        explanation_parts.append(f"Moderate separation ({best_result.largest_particle_ratio:.1%} largest)")

    # Coordination number analysis
    coord_score = calculate_coordination_score(best_result.mean_contacts)
    if coord_score >= 0.8:
        explanation_parts.append(f"Physically reasonable contacts ({best_result.mean_contacts:.1f})")
    elif coord_score >= 0.5:
        explanation_parts.append(f"Acceptable contacts ({best_result.mean_contacts:.1f})")
    else:
        explanation_parts.append(f"Suboptimal contacts ({best_result.mean_contacts:.1f})")

    explanation = f"Best radius r={best_radius} (score: {best_score:.3f}). " + "; ".join(explanation_parts)

    return best_radius, explanation


def determine_best_radius_pareto_distance(
    summary: OptimizationSummary,
    target_contacts: float = 6.0,
) -> Tuple[int, str]:
    """Determine best radius using Pareto + normalized distance + tie-breaks.

    Objectives to minimize (per radius):
      - Dominance (HHI over particle volume shares)
      - Knee distance (|index - knee_idx|)
      - Instability (mean VI to neighbors)

    Tie-break order: smaller r, lower HHI, |contacts - target_contacts|.

    Args:
        summary: Optimization summary with results (labels_path required)
        target_contacts: Reference contact value for tie-break proximity

    Returns:
        tuple: (best_radius, explanation)
    """
    results = summary.results
    if not results:
        return 0, "No results available"

    # Knee index from particle counts
    particle_counts = [r.particle_count for r in results]
    radii = [r.radius for r in results]
    knee_idx = detect_knee_point(radii, particle_counts) if len(results) >= 3 else 0

    # Cache labels to avoid reloading
    labels_cache: Dict[str, np.ndarray] = {}

    def load_labels(path: str) -> np.ndarray:
        if path not in labels_cache:
            labels_cache[path] = np.load(path)
        return labels_cache[path]

    # Compute objectives per result
    hhis: List[float] = []
    knee_dists: List[float] = []
    instabilities: List[float] = []  # mean VI to neighbors

    for idx, r in enumerate(results):
        # HHI dominance
        try:
            labels = load_labels(r.labels_path) if r.labels_path else None
            hhi = calculate_hhi(labels) if labels is not None else 1.0
        except Exception:
            hhi = 1.0
        hhis.append(float(hhi))

        # Knee distance (index distance)
        knee_dists.append(float(abs(idx - knee_idx)))

        # Instability: mean VI to neighbors (where available)
        vi_vals: List[float] = []
        if idx - 1 >= 0:
            try:
                if results[idx - 1].labels_path and r.labels_path:
                    a = load_labels(results[idx - 1].labels_path)
                    b = load_labels(r.labels_path)
                    vi_vals.append(calculate_variation_of_information(a, b))
            except Exception:
                pass
        if idx + 1 < len(results):
            try:
                if r.labels_path and results[idx + 1].labels_path:
                    a = load_labels(r.labels_path)
                    b = load_labels(results[idx + 1].labels_path)
                    vi_vals.append(calculate_variation_of_information(a, b))
            except Exception:
                pass
        instabilities.append(float(np.mean(vi_vals)) if vi_vals else 0.0)

    # Normalize objectives to [0,1]
    def normalize(values: List[float]) -> List[float]:
        v = np.array(values, dtype=float)
        v_min = float(np.min(v))
        v_max = float(np.max(v))
        if v_max <= v_min:
            return [0.0 for _ in values]
        return list((v - v_min) / (v_max - v_min))

    hhi_n = normalize(hhis)
    knee_n = normalize(knee_dists)
    instab_n = normalize(instabilities)

    objs = [
        (hhi_n[i], knee_n[i], instab_n[i])
        for i in range(len(results))
    ]

    # Pareto non-dominated set (minimization)
    indices = list(range(len(results)))
    def dominates(a: int, b: int) -> bool:
        A = objs[a]; B = objs[b]
        return all(A[i] <= B[i] for i in range(3)) and any(A[i] < B[i] for i in range(3))

    non_dominated = []
    for i in indices:
        if not any(dominates(j, i) for j in indices if j != i):
            non_dominated.append(i)

    # Distance to ideal (0,0,0)
    def distance(i: int) -> float:
        a, b, c = objs[i]
        return float(np.sqrt(a * a + b * b + c * c))

    # Candidate set
    candidates = non_dominated if non_dominated else indices

    # Sort by distance, then tie-breaks
    def tie_key(i: int):
        r = results[i]
        # smaller r, then lower raw HHI, then contacts proximity
        return (
            distance(i),
            r.radius,
            hhis[i],
            abs((r.mean_contacts or 0.0) - target_contacts),
        )

    best_idx = min(candidates, key=tie_key)
    best_r = results[best_idx].radius

    explanation = (
        f"Pareto+distance selection: r={best_r}; "
        f"knee@r={results[knee_idx].radius if results else 'n/a'}, "
        f"HHI={hhis[best_idx]:.3f}, knee_dist={knee_dists[best_idx]:.0f}, "
        f"instabVI={instabilities[best_idx]:.3f}"
    )

    return best_r, explanation


__all__ = [
    "determine_best_radius_advanced",
    "determine_best_radius_pareto_distance",
]
