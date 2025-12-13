"""Objective system for EduSched."""

from edusched.objectives.base import Objective
from edusched.objectives.objectives import (
    BalanceInstructorLoad,
    MinimizeEveningSessions,
    SpreadEvenlyAcrossTerm,
)

__all__ = [
    "Objective",
    "SpreadEvenlyAcrossTerm",
    "MinimizeEveningSessions",
    "BalanceInstructorLoad",
]
