"""Contact Analysis Package

This package handles particle contact analysis including:
- Contact counting between particles
- Statistical analysis of contact distributions 
- Contact visualization and reporting
- Guard volume filtering for edge effect exclusion
"""

from .core import count_contacts, save_contact_csv, analyze_contacts
from .guard_volume import (
    calculate_max_particle_radius,
    calculate_guard_margin,
    create_guard_volume_mask,
    filter_interior_particles,
    count_contacts_with_guard,
)
from .visualization import (
    get_discrete_contact_colormap,
    create_contact_count_map,
)

__all__ = [
    "count_contacts",
    "save_contact_csv", 
    "analyze_contacts",
    "calculate_max_particle_radius",
    "calculate_guard_margin",
    "create_guard_volume_mask",
    "filter_interior_particles",
    "count_contacts_with_guard",
    "get_discrete_contact_colormap",
    "create_contact_count_map",
] 