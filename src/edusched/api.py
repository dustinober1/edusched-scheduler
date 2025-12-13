"""Main API for EduSched scheduling."""

from typing import Optional

from edusched.domain.problem import Problem
from edusched.domain.result import Result


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
    # Placeholder implementation - will be completed in later tasks
    raise NotImplementedError("solve() will be implemented in task 9")
