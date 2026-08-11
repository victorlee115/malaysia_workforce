"""Frappe-native casual staffing extensions.

The package plans availability and coverage only. Standard Frappe HR Shift
Assignments remain the published roster and attendance source of truth.
"""

from malaysia_workforce.staffing.allocator import ALLOCATOR_VERSION, allocate_staff

__all__ = ["ALLOCATOR_VERSION", "allocate_staff"]
