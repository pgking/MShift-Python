"""
Cell Authority - Single source of truth for cell appearance logic.

This module provides a unified way to determine how cells should be rendered
across both the UI and Excel export, ensuring consistency.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CellAppearance:
    """Represents the visual appearance of a cell."""
    type: str  # "service", "holiday", "weekend", "empty"
    service: Optional[object] = None  # Service object if type is "service"


def resolve_cell_appearance(service_id, is_holiday: bool, is_weekend: bool, services: list):
    """
    Single source of truth for cell appearance.
    
    Authority hierarchy:
    1. If service exists -> service owns the cell
    2. Else if holiday -> holiday shading
    3. Else if weekend -> weekend shading
    4. Else -> empty cell
    
    Args:
        service_id: ID of the service assigned to this cell (or None)
        is_holiday: Whether this day is marked as a holiday
        is_weekend: Whether this day is a weekend
        services: List of all available services
        
    Returns:
        CellAppearance object describing how the cell should be rendered
    """
    if service_id is not None:
        service = next((s for s in services if s.id == service_id), None)
        return CellAppearance(type="service", service=service)
    elif is_holiday:
        return CellAppearance(type="holiday")
    elif is_weekend:
        return CellAppearance(type="weekend")
    else:
        return CellAppearance(type="empty")
