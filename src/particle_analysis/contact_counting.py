"""Contact counting for 3D particle structures."""

import csv
import logging
from pathlib import Path
from typing import Dict

import numpy as np
from tqdm import tqdm

logger = logging.getLogger(__name__)


def count_contacts(labels: np.ndarray, connectivity: int = 26) -> Dict[int, int]:
    """Count contacts between particles in a 3D labeled volume.
    
    Args:
        labels: 3D labeled volume (particle IDs)
        connectivity: Neighborhood connectivity (6, 18, or 26)
    
    Returns:
        Dict mapping particle_id -> contact_count
    """
    if connectivity == 6:
        # Face-connected neighbors (6 directions)
        offsets = [(-1,0,0), (1,0,0), (0,-1,0), (0,1,0), (0,0,-1), (0,0,1)]
    elif connectivity == 18:
        # Face + edge connected (18 directions)
        offsets = []
        for dz in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if abs(dx) + abs(dy) + abs(dz) <= 2 and (dx, dy, dz) != (0, 0, 0):
                        offsets.append((dz, dy, dx))
    else:  # connectivity == 26
        # Full 26-connected neighborhood
        offsets = []
        for dz in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if (dx, dy, dz) != (0, 0, 0):
                        offsets.append((dz, dy, dx))
    
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