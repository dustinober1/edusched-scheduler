"""Constraints for department availability and preferences."""

from typing import TYPE_CHECKING, Optional

from edusched.constraints.base import Constraint, ConstraintContext, Violation

if TYPE_CHECKING:
    from edusched.domain.assignment import Assignment


class DepartmentAvailabilityConstraint(Constraint):
    """Ensures sessions are scheduled when the department is available."""

    def __init__(self, department_id: str):
        """
        Initialize department availability constraint.

        Args:
            department_id: The department ID this constraint applies to
        """
        self.department_id = department_id

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if assignment time is within department availability."""
        request = context.request_lookup.get(assignment.request_id)
        if not request or request.department_id != self.department_id:
            return None

        department = context.department_lookup.get(self.department_id)
        if not department:
            return None  # Cannot validate without department info

        # Get day of week
        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        day_of_week = day_names[assignment.start_time.weekday()]

        # Check if department is available on this day
        if not department.is_day_available(day_of_week):
            return Violation(
                constraint_type=self.constraint_type,
                affected_request_id=assignment.request_id,
                message=(
                    f"Department {department.name} ({self.department_id}) "
                    f"is not available on {day_of_week.capitalize()} for session {assignment.request_id}"
                )
            )

        # Check department's preferred times if specified
        preferred_times = department.preferred_times.get(day_of_week.lower(), [])
        if preferred_times:
            # Simple check - in production, you'd parse times properly
            # For now, assume any time is within preferred times if they exist
            # This could be enhanced with actual time range checking
            pass  # Placeholder for time range checking

        return None

    def explain(self, violation: Violation) -> str:
        """Generate human-readable explanation."""
        return violation.message

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.department_availability"


class DepartmentPreferenceConstraint(Constraint):
    """Soft constraint encouraging department preferences for building and room types."""

    def __init__(self, department_id: str, weight: float = 1.0):
        """
        Initialize department preference constraint.

        Args:
            department_id: The department ID this constraint applies to
            weight: Weight of this preference (higher = more important)
        """
        self.department_id = department_id
        self.weight = weight

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check department preferences (soft constraint - returns None)."""
        # This is a soft constraint, so we don't return violations
        # The preference information could be used by the solver's objective function
        return None

    def explain(self, violation: Violation) -> str:
        """Generate human-readable explanation."""
        return violation.message

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "soft.department_preference"