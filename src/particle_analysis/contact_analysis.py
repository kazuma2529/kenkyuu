"""Contact analysis for 3D particle structures.

This module provides a unified interface for particle contact analysis,
combining contact counting and statistical analysis functionality.
"""

# Re-export functions from specialized modules
from .contact_counting import count_contacts, save_contact_csv
from .contact_statistics import analyze_contacts

__all__ = [
    "count_contacts",
    "save_contact_csv", 
    "analyze_contacts"
] 