"""Post-optimization analysis and CSV export.

This module provides pure-data functions for:
1. Analyzing the best-radius labels (contacts, volumes, guard volume filtering)
2. Building histogram/scatter data dicts consumed by GUI plotting widgets
3. Exporting per-particle CSV files for external tools (Excel, etc.)

All functions are free of Qt/GUI dependencies and can be tested independently.
"""

import csv
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data container
# ---------------------------------------------------------------------------

@dataclass
class InteriorAnalysis:
    """Core analysis results for Guard Volume interior particles.

    Attributes:
        interior_contacts: {particle_id: contact_count} for interior particles
        interior_volumes:  {particle_id: volume_voxels}  for interior particles
        guard_stats:       {'total_particles', 'interior_particles', 'excluded_particles'}
    """
    interior_contacts: Dict[int, int] = field(default_factory=dict)
    interior_volumes: Dict[int, int] = field(default_factory=dict)
    guard_stats: Dict[str, int] = field(default_factory=dict)

    @property
    def interior_ids(self) -> Set[int]:
        return set(self.interior_contacts.keys())

    @property
    def interior_count(self) -> int:
        return self.guard_stats.get('interior_particles', 0)

    @property
    def excluded_count(self) -> int:
        return self.guard_stats.get('excluded_particles', 0)


# ---------------------------------------------------------------------------
# 1. Analyse best-radius labels
# ---------------------------------------------------------------------------

def analyze_best_labels(
    labels_path: Path,
    connectivity: int = 6,
) -> InteriorAnalysis:
    """Load labels and compute contacts/volumes for interior particles.

    Args:
        labels_path: Path to ``labels_r{best}.npy``
        connectivity: Neighbourhood connectivity (6 or 26)

    Returns:
        InteriorAnalysis with contacts, volumes, and guard stats

    Raises:
        FileNotFoundError: if *labels_path* does not exist
        ValueError: if no particles are found
    """
    from ..volume.metrics.basic import calculate_particle_volumes
    from ..contact.guard_volume import count_contacts_with_guard

    if not labels_path.exists():
        raise FileNotFoundError(f"Labels not found: {labels_path}")

    labels = np.load(labels_path)
    logger.info(f"Loaded labels: {labels.shape}, {labels.max()} particles")

    # Volumes for ALL particles
    all_volumes = calculate_particle_volumes(labels)
    if not all_volumes:
        raise ValueError("No particles found in labels")

    # Contacts with guard-volume filtering
    _full, interior_contacts, guard_stats = count_contacts_with_guard(
        labels, connectivity=connectivity
    )

    interior_ids = set(interior_contacts.keys())
    interior_volumes = {pid: all_volumes[pid] for pid in interior_ids if pid in all_volumes}

    logger.info(
        f"Interior analysis complete: {len(interior_contacts)} interior, "
        f"{guard_stats['excluded_particles']} excluded"
    )

    return InteriorAnalysis(
        interior_contacts=interior_contacts,
        interior_volumes=interior_volumes,
        guard_stats=guard_stats,
    )


# ---------------------------------------------------------------------------
# 2. Build histogram / scatter dicts (consumed by HistogramPlotter)
# ---------------------------------------------------------------------------

def build_contact_histogram(analysis: InteriorAnalysis) -> Optional[Dict]:
    """Build contact-histogram dict expected by ``HistogramPlotter``."""
    values = list(analysis.interior_contacts.values())
    if not values:
        return None
    return {
        'values': values,
        'min': int(np.min(values)),
        'max': int(np.max(values)),
        'mean': float(np.mean(values)),
        'median': float(np.median(values)),
        'interior_count': analysis.interior_count,
        'excluded_count': analysis.excluded_count,
    }


def build_volume_histogram(analysis: InteriorAnalysis) -> Optional[Dict]:
    """Build volume-histogram dict expected by ``HistogramPlotter``."""
    values = list(analysis.interior_volumes.values())
    if not values:
        return None
    return {
        'values': values,
        'min': int(np.min(values)),
        'max': int(np.max(values)),
        'mean': float(np.mean(values)),
        'median': float(np.median(values)),
        'interior_count': analysis.interior_count,
        'excluded_count': analysis.excluded_count,
    }


def build_scatter_data(analysis: InteriorAnalysis) -> Optional[Dict]:
    """Build scatter dict expected by ``HistogramPlotter``."""
    ids, vols, conts = [], [], []
    for pid in analysis.interior_ids:
        if pid in analysis.interior_volumes and pid in analysis.interior_contacts:
            ids.append(pid)
            vols.append(analysis.interior_volumes[pid])
            conts.append(analysis.interior_contacts[pid])

    if not ids:
        return None
    return {
        'volumes': vols,
        'contacts': conts,
        'particle_ids': ids,
        'interior_count': analysis.interior_count,
        'excluded_count': analysis.excluded_count,
    }


# ---------------------------------------------------------------------------
# 3. CSV export
# ---------------------------------------------------------------------------

def _write_csv(path: Path, comment_lines: list[str], header: list[str], rows):
    """Write a CSV with ``#``-prefixed comment lines, a header row, and data rows."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        for line in comment_lines:
            f.write(f"# {line}\n")
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def save_analysis_csvs(output_dir: Path, analysis: InteriorAnalysis) -> None:
    """Save 3 CSV files for external graph generation (Excel, etc.).

    Files created:
        - ``contact_distribution.csv``  (particle_id, contact_count)
        - ``volume_distribution.csv``   (particle_id, volume_voxels)
        - ``volume_vs_contacts.csv``    (particle_id, volume_voxels, contact_count)
    """
    ic = analysis.interior_count
    ec = analysis.excluded_count

    # --- contact_distribution.csv ---
    try:
        vals = list(analysis.interior_contacts.values())
        mean_c = float(np.mean(vals)) if vals else 0.0
        median_c = float(np.median(vals)) if vals else 0.0
        _write_csv(
            output_dir / "contact_distribution.csv",
            [
                "Contact Number Distribution (Guard Volume Interior)",
                f"interior_particles={ic}, excluded_boundary={ec}",
                f"mean={mean_c:.4f}, median={median_c:.1f}",
            ],
            ["particle_id", "contact_count"],
            [[pid, analysis.interior_contacts[pid]]
             for pid in sorted(analysis.interior_contacts)],
        )
        logger.info(f"Saved contact_distribution.csv ({len(vals)} rows)")
    except Exception as e:
        logger.error(f"Failed to save contact_distribution.csv: {e}")

    # --- volume_distribution.csv ---
    try:
        vals = list(analysis.interior_volumes.values())
        mean_v = float(np.mean(vals)) if vals else 0.0
        median_v = float(np.median(vals)) if vals else 0.0
        _write_csv(
            output_dir / "volume_distribution.csv",
            [
                "Particle Volume Distribution (Guard Volume Interior)",
                f"interior_particles={ic}, excluded_boundary={ec}",
                f"mean={mean_v:.2f}, median={median_v:.1f} (voxels)",
            ],
            ["particle_id", "volume_voxels"],
            [[pid, analysis.interior_volumes[pid]]
             for pid in sorted(analysis.interior_volumes)],
        )
        logger.info(f"Saved volume_distribution.csv ({len(vals)} rows)")
    except Exception as e:
        logger.error(f"Failed to save volume_distribution.csv: {e}")

    # --- volume_vs_contacts.csv ---
    try:
        scatter = build_scatter_data(analysis)
        if scatter and scatter['particle_ids']:
            vols = np.array(scatter['volumes'])
            conts = np.array(scatter['contacts'])
            ids = scatter['particle_ids']

            slope, corr = 0.0, 0.0
            if len(vols) > 2:
                coeffs = np.polyfit(vols, conts, 1)
                slope = float(coeffs[0])
                corr = float(np.corrcoef(vols, conts)[0, 1])

            _write_csv(
                output_dir / "volume_vs_contacts.csv",
                [
                    "Particle Volume vs Contact Number (Guard Volume Interior)",
                    f"interior_particles={ic}, excluded_boundary={ec}",
                    f"linear_fit_slope={slope:.6f}, correlation_R={corr:.4f}",
                ],
                ["particle_id", "volume_voxels", "contact_count"],
                sorted(zip(ids, [int(v) for v in vols], [int(c) for c in conts])),
            )
            logger.info(f"Saved volume_vs_contacts.csv ({len(ids)} rows)")
        else:
            logger.warning("No scatter data; skipping volume_vs_contacts.csv")
    except Exception as e:
        logger.error(f"Failed to save volume_vs_contacts.csv: {e}")


__all__ = [
    "InteriorAnalysis",
    "analyze_best_labels",
    "build_contact_histogram",
    "build_volume_histogram",
    "build_scatter_data",
    "save_analysis_csvs",
]
