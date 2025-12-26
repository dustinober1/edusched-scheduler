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
from edusched.constraints.composite_constraints import (
    AndConstraint,
    OrConstraint,
    NotConstraint,
    XorConstraint,
    ConstraintBuilder,
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
from edusched.objectives.multi_objective import (
    MultiObjectiveOptimizer,
    EnhancedObjectiveScorer,
    AchievementScalarizingFunction,
    ObjectiveComparisonTool
)
from edusched.io.import_export import (
    ImportExportManager,
    JSONHandler,
    CSVHandler,
    ExcelHandler
)
from edusched.plugins.base import (
    PluginManager,
    plugin_manager,
    PluginInterface,
    ConstraintPlugin,
    SolverPlugin,
    ObjectivePlugin
)

# Solver backend imports
from edusched.solvers.base import SolverBackend
from edusched.solvers.heuristic import HeuristicSolver
from edusched.solvers.genetic_algorithm import GeneticAlgorithmSolver

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
    "AndConstraint",
    "OrConstraint",
    "NotConstraint",
    "XorConstraint",
    "ConstraintBuilder",
    # Objectives
    "Objective",
    "SpreadEvenlyAcrossTerm",
    "MinimizeEveningSessions",
    "BalanceInstructorLoad",
    # Multi-objective optimization
    "MultiObjectiveOptimizer",
    "EnhancedObjectiveScorer",
    "AchievementScalarizingFunction",
    "ObjectiveComparisonTool",
    # Import/Export
    "ImportExportManager",
    "JSONHandler",
    "CSVHandler",
    "ExcelHandler",
    # Plugins
    "PluginManager",
    "plugin_manager",
    "PluginInterface",
    "ConstraintPlugin",
    "SolverPlugin",
    "ObjectivePlugin",
    # Solvers
    "SolverBackend",
    "HeuristicSolver",
    "GeneticAlgorithmSolver",
    # API
    "solve",
    # Errors
    "ValidationError",
    "InfeasibilityError",
    "BackendError",
    "MissingOptionalDependency",
]
