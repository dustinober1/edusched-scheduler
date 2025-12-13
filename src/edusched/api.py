"""Main API for EduSched scheduling."""

import random
from typing import Optional

from edusched.domain.problem import Problem
from edusched.domain.result import Result
from edusched.errors import BackendError, ValidationError

# Import solver backends
from edusched.solvers.heuristic import HeuristicSolver


def solve(
    problem: Problem,
    backend: str = "auto",
    seed: Optional[int] = None,
    fallback: bool = False,
) -> Result:
    """
    Solve a scheduling problem.

    Args:
        problem: The scheduling problem to solve
        backend: Solver backend to use ("auto", "heuristic", "ortools")
        seed: Random seed for deterministic results
        fallback: Whether to fall back to heuristic if primary backend fails

    Returns:
        Result object with scheduling solution

    Raises:
        ValidationError: If problem is invalid
        BackendError: If solver backend fails
        MissingOptionalDependency: If required optional dependencies are missing
    """
    # Validate problem first
    errors = problem.validate()
    if errors:
        raise ValidationError(f"Problem validation failed: {'; '.join(errors)}")

    # Generate seed if not provided for reproducibility tracking
    if seed is None:
        seed = random.randint(0, 2**31 - 1)

    # Determine which backend to use
    if backend == "auto":
        # Try OR-Tools if available, otherwise fall back to heuristic
        try:
            from edusched.solvers.ortools_solver import ORToolsSolver
            solver = ORToolsSolver()
        except (ImportError, MissingOptionalDependency):
            solver = HeuristicSolver()
    elif backend == "heuristic":
        solver = HeuristicSolver()
    elif backend == "ortools":
        try:
            from edusched.solvers.ortools_solver import ORToolsSolver
            solver = ORToolsSolver()
        except ImportError:
            raise BackendError(
                "OR-Tools backend not available. Install with: pip install edusched[ortools]"
            )
    else:
        raise BackendError(f"Unknown backend: {backend}")

    # Try to solve with selected backend
    try:
        result = solver.solve(problem, seed=seed, fallback=fallback)
    except Exception as e:
        if fallback and backend != "heuristic":
            # Fall back to heuristic solver
            fallback_solver = HeuristicSolver()
            result = fallback_solver.solve(problem, seed=seed, fallback=False)
        else:
            raise BackendError(f"Solver failed: {str(e)}") from e

    return result
