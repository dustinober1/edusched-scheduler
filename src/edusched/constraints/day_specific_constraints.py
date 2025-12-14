"""Constraints for day-specific resource requirements."""

from typing import TYPE_CHECKING, List, Optional

from edusched.constraints.base import Constraint, ConstraintContext, Violation

if TYPE_CHECKING:
    from edusched.domain.assignment import Assignment


class DaySpecificResourceRequirement(Constraint):
    """Ensures resources are available only on specific days of the week."""

    def __init__(self, request_id: str):
        self.request_id = request_id

    def check(
        self,
        assignment: "Assignment",
        solution: List["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if resources are assigned on valid days for this request."""
        if assignment.request_id != self.request_id:
            return None

        request = context.request_lookup.get(self.request_id)
        if not request or not request.day_requirements:
            return None

        # Get day of week (0=Monday, 1=Tuesday, ..., 6=Sunday)
        day_of_week = assignment.start_time.weekday()

        # Check if any resources are assigned on an invalid day
        for resource_type, resource_ids in assignment.assigned_resources.items():
            # Get required resource types for this day
            required_types = request.day_requirements.get(day_of_week, [])
            if required_types and resource_type not in required_types:
                day_names = [
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                    "Saturday",
                    "Sunday",
                ]
                return Violation(
                    constraint_type=self.constraint_type,
                    affected_request_id=self.request_id,
                    affected_resource_id=resource_ids[0] if resource_ids else None,
                    message=f"Resource type '{resource_type}' not required on {day_names[day_of_week]} for session {self.request_id}",
                )

        return None

    def explain(self, violation: Violation) -> str:
        """Generate human-readable explanation."""
        return violation.message

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.day_specific_resource"
