"""Constraint system for EduSched."""

from edusched.constraints.base import Constraint, ConstraintContext, Violation
from edusched.constraints.hard_constraints import (
    AttributeMatch,
    BlackoutDates,
    MaxPerDay,
    MinGapBetweenOccurrences,
    NoOverlap,
    WithinDateRange,
)

__all__ = [
    "Constraint",
    "ConstraintContext",
    "Violation",
    "NoOverlap",
    "BlackoutDates",
    "MaxPerDay",
    "MinGapBetweenOccurrences",
    "WithinDateRange",
    "AttributeMatch",
]
