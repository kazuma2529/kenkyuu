"""Contact Analysis Package

This package handles particle contact analysis including:
- Contact counting between particles
- Statistical analysis of contact distributions 
- Contact visualization and reporting
"""

from .core import count_contacts, save_contact_csv, analyze_contacts

__all__ = [
    "count_contacts",
    "save_contact_csv", 
    "analyze_contacts"
] 