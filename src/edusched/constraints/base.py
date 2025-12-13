"""Base constraint interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from edusched.domain.assignment import Assignment
    from edusched.domain.calendar import Calendar
    from edusched.domain.problem import Problem
    from edusched.domain.resource import Resource
    from edusched.domain.session_request import SessionRequest
    from edusched.domain.building import Building
    from edusched.domain.department import Department
    from edusched.domain.teacher import Teacher


@dataclass
class Violation:
    """Represents a constraint violation."""

    constraint_type: str
    affected_request_id: str
    affected_resource_id: Optional[str] = None
    message: str = ""


@dataclass
class ConstraintContext:
    """Context object providing access to problem data during constraint checking."""

    problem: "Problem"
    resource_lookup: Dict[str, "Resource"]
    calendar_lookup: Dict[str, "Calendar"]
    request_lookup: Dict[str, "SessionRequest"]
    building_lookup: Dict[str, "Building"] = None
    department_lookup: Dict[str, "Department"] = None
    teacher_lookup: Dict[str, "Teacher"] = None


class Constraint(ABC):
    """Base class for all constraints."""

    @abstractmethod
    def check(
        self,
        assignment: "Assignment",
        solution: List["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """
        Check if assignment violates this constraint.

        Args:
            assignment: The assignment to check
            solution: Current solution (all assignments so far)
            context: Context with problem data

        Returns:
            Violation object if constraint is violated, None otherwise
        """

    @abstractmethod
    def explain(self, violation: Violation) -> str:
        """
        Provide human-readable explanation of violation.

        Args:
            violation: The violation to explain

        Returns:
            Human-readable explanation string
        """

    @property
    @abstractmethod
    def constraint_type(self) -> str:
        """
        Unique identifier for constraint type.

        Returns:
            Constraint type identifier (e.g., 'hard.no_overlap')
        """
