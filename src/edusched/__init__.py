"""EduSched: A constraint-based scheduling package for educational institutions."""

__version__ = "0.1.0b1"

# Core domain model imports
# Constraint system imports
from edusched.constraints.base import Constraint, ConstraintContext, Violation
from edusched.constraints.hard_constraints import (
    AttributeMatch,
    BlackoutDates,
    MaxPerDay,
    MinGapBetweenOccurrences,
    NoOverlap,
    WithinDateRange,
)

# Main API
from edusched.core_api import solve
from edusched.domain.assignment import Assignment
from edusched.domain.calendar import Calendar
from edusched.domain.problem import Problem
from edusched.domain.resource import Resource
from edusched.domain.result import Result
from edusched.domain.session_request import SessionRequest

# Error types
from edusched.errors import (
    BackendError,
    InfeasibilityError,
    MissingOptionalDependency,
    ValidationError,
)

# Objective system imports
from edusched.objectives.base import Objective
from edusched.objectives.objectives import (
    BalanceInstructorLoad,
    MinimizeEveningSessions,
    SpreadEvenlyAcrossTerm,
)

# Solver backend imports
from edusched.solvers.base import SolverBackend
from edusched.solvers.heuristic import HeuristicSolver

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
