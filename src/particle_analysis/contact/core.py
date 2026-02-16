"""Core contact analysis functionality.

This module provides the essential functions for particle contact analysis,
combining counting algorithms with statistical analysis capabilities.
"""

import csv
import logging
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from tqdm import tqdm

logger = logging.getLogger(__name__)


def count_contacts(
    labels: np.ndarray,
    connectivity: int = 26,
    use_guard_volume: bool = False
) -> Dict[int, int]:
    """Count contacts between particles in a 3D labeled volume.
    
    Args:
        labels: 3D labeled volume (particle IDs)
        connectivity: Neighborhood connectivity (6 or 26)
        use_guard_volume: If True, exclude boundary particles from returned results
                         (contacts are still counted for all particles, but only
                         interior particles are included in the returned dict)
    
    Returns:
        Dict mapping particle_id -> contact_count
        If use_guard_volume=True, only interior particles are included.
    """
    if connectivity == 6:
        # Face-connected neighbors (6 directions)
        offsets = [(-1,0,0), (1,0,0), (0,-1,0), (0,1,0), (0,0,-1), (0,0,1)]
    elif connectivity == 26:
        # Full 26-connected neighborhood
        offsets = []
        for dz in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if (dx, dy, dz) != (0, 0, 0):
                        offsets.append((dz, dy, dx))
    else:
        raise ValueError(f"Unsupported connectivity: {connectivity}. Use 6 or 26.")
    
    Z, H, W = labels.shape
    max_label = labels.max()
    
    logger.info(f"Max label id: {max_label}")
    
    # Initialize contact sets for each particle
    contacts = {pid: set() for pid in range(1, max_label + 1)}
    
    # Scan all neighbor directions
    for dz, dy, dx in tqdm(offsets, desc="Scanning neighbors"):
        # Create shifted versions of the labels
        if dz == 0 and dy == 0 and dx == 0:
            continue
            
        # Calculate valid slice ranges
        z_start = max(0, -dz)
        z_end = min(Z, Z - dz)
        y_start = max(0, -dy)
        y_end = min(H, H - dy)
        x_start = max(0, -dx)
        x_end = min(W, W - dx)
        
        if z_start >= z_end or y_start >= y_end or x_start >= x_end:
            continue
        
        # Get current and neighbor slices
        current_slice = labels[z_start:z_end, y_start:y_end, x_start:x_end]
        neighbor_slice = labels[z_start+dz:z_end+dz, y_start+dy:y_end+dy, x_start+dx:x_end+dx]
        
        # Find contacts (different non-zero labels)
        contact_mask = (current_slice > 0) & (neighbor_slice > 0) & (current_slice != neighbor_slice)
        
        if contact_mask.any():
            current_contacts = current_slice[contact_mask]
            neighbor_contacts = neighbor_slice[contact_mask]
            
            # Add contacts to sets (bidirectional)
            for curr, neigh in zip(current_contacts, neighbor_contacts):
                contacts[curr].add(neigh)
                contacts[neigh].add(curr)
    
    # Convert sets to counts
    contact_counts = {pid: len(contact_set) for pid, contact_set in contacts.items()}
    
    # Apply guard volume filtering if requested
    if use_guard_volume:
        from .guard_volume import (
            calculate_guard_margin,
            create_guard_volume_mask,
            filter_interior_particles
        )
        
        margin = calculate_guard_margin(labels)
        guard_mask = create_guard_volume_mask(labels.shape, margin)
        interior_particles = filter_interior_particles(labels, guard_mask)
        
        # Filter to interior particles only
        contact_counts = {
            pid: count for pid, count in contact_counts.items()
            if pid in interior_particles
        }
        
        logger.info(
            f"Guard volume filtering applied: {len(contact_counts)} interior particles "
            f"out of {len(contacts)} total"
        )
    
    return contact_counts


def save_contact_csv(contacts: Dict[int, int], out_csv: str) -> None:
    """Save contact counts to CSV file.
    
    Args:
        contacts: Dictionary mapping particle_id -> contact_count
        out_csv: Output CSV file path
    """
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    
    with open(out_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["particle_id", "contacts"])
        for pid, cnt in sorted(contacts.items()):
            writer.writerow([pid, cnt])
    
    logger.info("Saved CSV to %s", out_csv)


def analyze_contacts(
    csv_path: str,
    out_summary: str,
    exclude_ids: Optional[List[int]] = None,
    auto_exclude_threshold: int = 200
) -> Dict[str, float]:
    """Analyze particle contact distribution and generate summary statistics.
    
    Args:
        csv_path: Path to contact_counts.csv
        out_summary: Output path for summary CSV
        exclude_ids: List of particle IDs to exclude
        auto_exclude_threshold: Automatically exclude particles with contacts > threshold
    
    Returns:
        Dict: Summary statistics
    """
    # Load data
    df = pd.read_csv(csv_path)
    logger.info("Loaded %d particles from %s", len(df), csv_path)
    
    # Check if data is empty
    if len(df) == 0:
        logger.warning("No particles found in CSV file")
        stats = _get_empty_stats()
        _save_summary_csv(stats, out_summary)
        return stats
    
    # Apply manual exclusions
    if exclude_ids:
        excluded_manual = df[df['particle_id'].isin(exclude_ids)]
        df = df[~df['particle_id'].isin(exclude_ids)]
        logger.info("Manually excluded %d particles: %s", 
                   len(excluded_manual), exclude_ids)
    
    # Apply automatic exclusion for outliers
    outliers = df[df['contacts'] > auto_exclude_threshold]
    if len(outliers) > 0:
        logger.warning("Auto-excluding %d particles with contacts > %d:", 
                      len(outliers), auto_exclude_threshold)
        for _, row in outliers.iterrows():
            logger.warning("  Particle ID %d: %d contacts", 
                          row['particle_id'], row['contacts'])
        df = df[df['contacts'] <= auto_exclude_threshold]
    
    # Check if data is empty after exclusions
    if len(df) == 0:
        logger.warning("No particles remaining after exclusions")
        stats = _get_empty_stats()
        _save_summary_csv(stats, out_summary)
        return stats
    
    # Calculate statistics
    contacts = df['contacts'].values
    stats = {
        'total_particles': len(df),
        'mean_contacts': float(np.mean(contacts)),
        'median_contacts': float(np.median(contacts)),
        'std_contacts': float(np.std(contacts)),
        'min_contacts': int(np.min(contacts)),
        'max_contacts': int(np.max(contacts)),
        'q25_contacts': float(np.percentile(contacts, 25)),
        'q75_contacts': float(np.percentile(contacts, 75))
    }
    
    logger.info("Final statistics - particles: %d, mean: %.2f, median: %.1f, max: %d",
               stats['total_particles'], stats['mean_contacts'], 
               stats['median_contacts'], stats['max_contacts'])
    
    # Save summary only (histogram output is abolished)
    _save_summary_csv(stats, out_summary)

    return stats


def _get_empty_stats() -> Dict[str, float]:
    """Get empty statistics dictionary."""
    return {
        'total_particles': 0,
        'mean_contacts': 0.0,
        'median_contacts': 0.0,
        'std_contacts': 0.0,
        'min_contacts': 0,
        'max_contacts': 0,
        'q25_contacts': 0.0,
        'q75_contacts': 0.0
    }


def _save_summary_csv(stats: Dict[str, float], out_summary: str) -> None:
    """Save summary statistics to CSV."""
    Path(out_summary).parent.mkdir(parents=True, exist_ok=True)
    
    summary_df = pd.DataFrame([stats])
    summary_df.to_csv(out_summary, index=False)
    logger.info("Saved summary to %s", out_summary)