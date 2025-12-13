"""Solver backends for EduSched."""

from edusched.solvers.base import SolverBackend
from edusched.solvers.heuristic import HeuristicSolver

__all__ = [
    "SolverBackend",
    "HeuristicSolver",
]
