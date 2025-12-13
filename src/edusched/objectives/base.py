"""Base objective interface."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from edusched.domain.assignment import Assignment


class Objective(ABC):
    """Base class for all objectives."""

    def __init__(self, weight: float = 1.0) -> None:
        self.weight = weight

    @abstractmethod
    def score(self, solution: List["Assignment"]) -> float:
        """
        Calculate normalized score [0,1] using penalty-based normalization.

        Normalization strategy: penalty-based with fixed bounds
        - Calculate total penalty from objective-specific violations
        - Normalize using: score = max(0, 1 - (total_penalty / max_penalty_bound))
        - max_penalty_bound is objective-specific and configurable

        Args:
            solution: List of assignments in the current solution

        Returns:
            Normalized score between 0 and 1
        """

    @property
    @abstractmethod
    def objective_type(self) -> str:
        """
        Unique identifier for objective type.

        Returns:
            Objective type identifier
        """
