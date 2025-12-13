"""Base solver backend interface."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from edusched.domain.problem import Problem
    from edusched.domain.result import Result


class SolverBackend(ABC):
    """Base class for solver backends."""

    @abstractmethod
    def solve(
        self,
        problem: "Problem",
        seed: Optional[int] = None,
        fallback: bool = False,
    ) -> "Result":
        """
        Solve scheduling problem and return result.

        Args:
            problem: The scheduling problem to solve
            seed: Random seed for deterministic results
            fallback: Whether to fall back on failure

        Returns:
            Result object with scheduling solution
        """

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """
        Backend identifier for reproducibility.

        Returns:
            Name of the backend
        """
