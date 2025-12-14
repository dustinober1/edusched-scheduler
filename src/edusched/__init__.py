"""EduSched: A constraint-based scheduling package for educational institutions."""

__version__ = "0.1.0b1"

# Core domain model imports
from edusched.domain.session_request import SessionRequest
from edusched.domain.resource import Resource
from edusched.domain.calendar import Calendar
from edusched.domain.assignment import Assignment
from edusched.domain.problem import Problem
from edusched.domain.result import Result

# Constraint system imports
from edusched.constraints.base import Constraint, ConstraintContext, Violation
from edusched.constraints.hard_constraints import (
    NoOverlap,
    BlackoutDates,
    MaxPerDay,
    MinGapBetweenOccurrences,
    WithinDateRange,
    AttributeMatch,
)

# Objective system imports
from edusched.objectives.base import Objective
from edusched.objectives.objectives import (
    SpreadEvenlyAcrossTerm,
    MinimizeEveningSessions,
    BalanceInstructorLoad,
)

# Solver backend imports
from edusched.solvers.base import SolverBackend
from edusched.solvers.heuristic import HeuristicSolver

# Main API
from edusched.core_api import solve

# Error types
from edusched.errors import (
    ValidationError,
    InfeasibilityError,
    BackendError,
    MissingOptionalDependency,
)

__all__ = [
    # Version
    "__version__",
    # Domain model
    "SessionRequest",
    "Resource",
    "Calendar",
    "Assignment",
    "Problem",
    "Result",
    # Constraints
    "Constraint",
    "ConstraintContext",
    "Violation",
    "NoOverlap",
    "BlackoutDates",
    "MaxPerDay",
    "MinGapBetweenOccurrences",
    "WithinDateRange",
    "AttributeMatch",
    # Objectives
    "Objective",
    "SpreadEvenlyAcrossTerm",
    "MinimizeEveningSessions",
    "BalanceInstructorLoad",
    # Solvers
    "SolverBackend",
    "HeuristicSolver",
    # API
    "solve",
    # Errors
    "ValidationError",
    "InfeasibilityError",
    "BackendError",
    "MissingOptionalDependency",
]
