"""Guard Volume functionality for edge effect exclusion.

This module provides functions to exclude particles at the boundaries of the
3D volume to avoid edge effects in contact analysis. Particles that touch the
boundary are excluded from statistics, but their contacts with interior particles
are still counted.
"""

import logging
from typing import Dict, Set, Tuple, Optional

import numpy as np

logger = logging.getLogger(__name__)


def calculate_max_particle_radius(labels: np.ndarray) -> float:
    """Calculate the maximum equivalent radius of particles.
    
    The equivalent radius is calculated assuming spherical particles:
    r = (3V / 4π)^(1/3)
    
    Args:
        labels: 3D labeled volume (particle IDs)
        
    Returns:
        Maximum equivalent radius in voxels (float)
    """
    if labels.max() == 0:
        logger.warning("No particles found in labels")
        return 0.0
    
    unique_labels = np.unique(labels)
    unique_labels = unique_labels[unique_labels > 0]  # Remove background
    
    if len(unique_labels) == 0:
        return 0.0
    
    max_radius = 0.0
    for label_id in unique_labels:
        volume = np.sum(labels == label_id)
        if volume > 0:
            # Equivalent radius: V = (4/3)πr³ => r = (3V/4π)^(1/3)
            equivalent_radius = np.power(3.0 * volume / (4.0 * np.pi), 1.0 / 3.0)
            max_radius = max(max_radius, equivalent_radius)
    
    logger.info(f"Maximum particle equivalent radius: {max_radius:.2f} voxels")
    return max_radius


def calculate_guard_margin(
    labels: np.ndarray,
    min_margin: int = 10,
    margin_multiplier: float = 0.3
) -> int:
    """Calculate guard margin based on maximum particle size.
    
    The margin is calculated as:
    margin = max(max_particle_radius × margin_multiplier, min_margin)
    
    However, the margin is limited to ensure at least 88% of the volume
    remains as interior region in each dimension (6% margin on each side).
    
    The goal is to keep approximately 60-70% of particles in the interior
    for statistically meaningful analysis while excluding edge effects.
    
    Args:
        labels: 3D labeled volume
        min_margin: Minimum margin in voxels (default: 10 = 140μm at 14μm/voxel)
        margin_multiplier: Multiplier for max particle radius (default: 0.3)
        
    Returns:
        Guard margin in voxels (int)
    """
    max_radius = calculate_max_particle_radius(labels)
    calculated_margin = int(np.ceil(max_radius * margin_multiplier))
    margin = max(calculated_margin, min_margin)
    
    # Limit margin to ensure at least 88% of each dimension remains as interior
    # (6% margin on each side)
    Z, H, W = labels.shape
    max_allowed_margin = min(
        int(Z * 0.06),  # At least 88% interior = 6% margin on each side
        int(H * 0.06),
        int(W * 0.06)
    )
    
    if margin > max_allowed_margin:
        logger.warning(
            f"Guard margin {margin} voxels exceeds maximum allowed {max_allowed_margin} voxels "
            f"(limited by volume size {labels.shape}). Using {max_allowed_margin} voxels instead."
        )
        margin = max_allowed_margin
    
    # Ensure margin is at least min_margin (but not larger than allowed)
    margin = max(min(margin, max_allowed_margin), min_margin)
    
    logger.info(
        f"Guard margin: {margin} voxels "
        f"(calculated: {calculated_margin}, min: {min_margin}, max_allowed: {max_allowed_margin})"
    )
    return margin


def create_guard_volume_mask(
    shape: Tuple[int, int, int],
    margin: int
) -> np.ndarray:
    """Create a boolean mask for the interior (guard) volume.
    
    The mask is True for voxels that are at least `margin` voxels away
    from any boundary.
    
    Args:
        shape: Shape of the 3D volume (Z, Y, X)
        margin: Margin size in voxels
        
    Returns:
        Boolean mask (True = interior, False = boundary region)
    """
    Z, H, W = shape
    
    # Create coordinate arrays
    z_coords = np.arange(Z)
    y_coords = np.arange(H)
    x_coords = np.arange(W)
    
    # Create meshgrid
    zz, yy, xx = np.meshgrid(z_coords, y_coords, x_coords, indexing='ij')
    
    # Check if coordinates are within interior region
    interior_mask = (
        (zz >= margin) & (zz < Z - margin) &
        (yy >= margin) & (yy < H - margin) &
        (xx >= margin) & (xx < W - margin)
    )
    
    logger.info(
        f"Guard volume mask created: {interior_mask.sum()} interior voxels "
        f"out of {interior_mask.size} total ({100.0 * interior_mask.sum() / interior_mask.size:.1f}%)"
    )
    
    return interior_mask


def filter_interior_particles(
    labels: np.ndarray,
    guard_mask: np.ndarray
) -> Set[int]:
    """Identify particles that are completely within the guard volume.
    
    A particle is considered interior if ALL its voxels are within the
    guard volume (interior_mask == True).
    
    Args:
        labels: 3D labeled volume (particle IDs)
        guard_mask: Boolean mask (True = interior region)
        
    Returns:
        Set of particle IDs that are completely interior
    """
    if labels.shape != guard_mask.shape:
        raise ValueError(
            f"Shape mismatch: labels {labels.shape} vs guard_mask {guard_mask.shape}"
        )
    
    unique_labels = np.unique(labels)
    unique_labels = unique_labels[unique_labels > 0]  # Remove background
    
    interior_particles = set()
    
    for label_id in unique_labels:
        particle_mask = (labels == label_id)
        particle_voxels = particle_mask.sum()
        
        if particle_voxels == 0:
            continue
        
        # Check if all voxels are in interior
        interior_voxels = (particle_mask & guard_mask).sum()
        
        if interior_voxels == particle_voxels:
            interior_particles.add(label_id)
    
    total_particles = len(unique_labels)
    excluded_particles = total_particles - len(interior_particles)
    
    logger.info(
        f"Interior particle filtering: {len(interior_particles)} interior particles "
        f"out of {total_particles} total ({excluded_particles} excluded)"
    )
    
    return interior_particles


def count_contacts_with_guard(
    labels: np.ndarray,
    connectivity: int = 26,
    guard_mask: Optional[np.ndarray] = None,
    interior_particles: Optional[Set[int]] = None
) -> Tuple[Dict[int, int], Dict[int, int], Dict[str, int]]:
    """Count contacts with guard volume filtering.
    
    This function:
    1. Counts contacts for ALL particles (including boundary particles)
    2. Filters statistics to only interior particles
    3. Returns both full and filtered contact counts
    
    Args:
        labels: 3D labeled volume (particle IDs)
        connectivity: Neighborhood connectivity (6 or 26)
        guard_mask: Optional pre-computed guard mask (if None, will be created)
        interior_particles: Optional pre-computed interior particle set
        
    Returns:
        Tuple of:
        - full_contacts: Dict[particle_id -> contact_count] for all particles
        - interior_contacts: Dict[particle_id -> contact_count] for interior particles only
        - stats: Dict with statistics (total_particles, interior_particles, excluded_particles)
    """
    from .core import count_contacts
    
    # Count contacts for all particles
    logger.info(f"Counting contacts for all particles (connectivity={connectivity})...")
    full_contacts = count_contacts(labels, connectivity=connectivity)
    logger.info(f"Total particles with contacts: {len(full_contacts)}")
    
    # Always compute guard mask and interior particles (even if provided, we log the process)
    if guard_mask is None:
        logger.info("Computing guard volume mask...")
        margin = calculate_guard_margin(labels)
        guard_mask = create_guard_volume_mask(labels.shape, margin)
        logger.info(f"Guard mask created: {guard_mask.sum()} interior voxels out of {guard_mask.size} total")
    else:
        logger.info(f"Using provided guard mask: {guard_mask.sum()} interior voxels")
    
    if interior_particles is None:
        logger.info("Filtering interior particles...")
        interior_particles = filter_interior_particles(labels, guard_mask)
        logger.info(f"Interior particles identified: {len(interior_particles)} particles")
    else:
        logger.info(f"Using provided interior particles: {len(interior_particles)} particles")
    
    # Filter to interior particles only
    logger.info(f"Filtering contact counts to interior particles only...")
    interior_contacts = {
        pid: count for pid, count in full_contacts.items()
        if pid in interior_particles
    }
    
    stats = {
        'total_particles': len(full_contacts),
        'interior_particles': len(interior_contacts),
        'excluded_particles': len(full_contacts) - len(interior_contacts)
    }
    
    # Calculate statistics for comparison
    if len(full_contacts) > 0:
        full_mean = np.mean(list(full_contacts.values()))
    else:
        full_mean = 0.0
    
    if len(interior_contacts) > 0:
        interior_mean = np.mean(list(interior_contacts.values()))
    else:
        interior_mean = 0.0
    
    logger.info(
        f"✅ Guard volume filtering complete:\n"
        f"  - Total particles: {stats['total_particles']}\n"
        f"  - Interior particles: {stats['interior_particles']} ({100.0 * stats['interior_particles'] / stats['total_particles']:.1f}%)\n"
        f"  - Excluded particles: {stats['excluded_particles']} ({100.0 * stats['excluded_particles'] / stats['total_particles']:.1f}%)\n"
        f"  - Mean contacts (all): {full_mean:.2f}\n"
        f"  - Mean contacts (interior only): {interior_mean:.2f}\n"
        f"  - Difference: {full_mean - interior_mean:.2f}"
    )
    
    return full_contacts, interior_contacts, stats


__all__ = [
    "calculate_max_particle_radius",
    "calculate_guard_margin",
    "create_guard_volume_mask",
    "filter_interior_particles",
    "count_contacts_with_guard",
]

