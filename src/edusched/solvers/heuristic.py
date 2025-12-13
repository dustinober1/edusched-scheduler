"""Heuristic solver backend implementation."""

from typing import TYPE_CHECKING, Optional

from edusched.solvers.base import SolverBackend

if TYPE_CHECKING:
    from edusched.domain.problem import Problem
    from edusched.domain.result import Result


class HeuristicSolver(SolverBackend):
    """Greedy heuristic solver backend."""

    def solve(
        self,
        problem: "Problem",
        seed: Optional[int] = None,
        fallback: bool = False,
    ) -> "Result":
        """
        Solve scheduling problem using greedy heuristic.

        Args:
            problem: The scheduling problem to solve
            seed: Random seed for deterministic results
            fallback: Whether to fall back on failure

        Returns:
            Result object with scheduling solution
        """
        # Placeholder implementation - will be completed in task 7
        raise NotImplementedError("HeuristicSolver.solve() will be implemented in task 7")

    @property
    def backend_name(self) -> str:
        """Return backend identifier."""
        return "heuristic"
