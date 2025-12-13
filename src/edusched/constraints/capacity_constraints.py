"""Constraints for managing classroom capacity requirements."""

from typing import TYPE_CHECKING, Optional

from edusched.constraints.base import Constraint, ConstraintContext, Violation

if TYPE_CHECKING:
    from edusched.domain.assignment import Assignment


class CapacityConstraint(Constraint):
    """Ensures assigned classroom can accommodate the class enrollment."""

    def __init__(self, request_id: str, buffer_percent: float = 0.1):
        """
        Initialize capacity constraint.

        Args:
            request_id: The session request ID this constraint applies to
            buffer_percent: Extra capacity buffer as percentage (default 10%)
        """
        self.request_id = request_id
        self.buffer_percent = buffer_percent

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if assigned classroom has sufficient capacity."""
        if assignment.request_id != self.request_id:
            return None

        request = context.request_lookup.get(self.request_id)
        if not request:
            return None

        # Skip capacity check for online classes
        if request.modality in ["online", "hybrid"]:
            return None

        # Check if any classroom resources are assigned
        classroom_resources = assignment.assigned_resources.get("classroom", [])
        if not classroom_resources:
            return None

        # Get the primary classroom (first in the list)
        classroom_id = classroom_resources[0]
        classroom = context.resource_lookup.get(classroom_id)

        if not classroom or classroom.capacity is None:
            # If no capacity info is available, we can't validate
            return None

        # Calculate required capacity with buffer
        required_capacity = max(request.enrollment_count, request.min_capacity)
        if required_capacity == 0:
            # No capacity requirement specified
            return None

        # Apply buffer (e.g., 10% extra space)
        required_capacity_with_buffer = int(required_capacity * (1 + self.buffer_percent))

        # Check capacity limits
        if classroom.capacity < required_capacity_with_buffer:
            return Violation(
                constraint_type=self.constraint_type,
                affected_request_id=self.request_id,
                affected_resource_id=classroom_id,
                message=(
                    f"Classroom {classroom_id} capacity ({classroom.capacity}) "
                    f"is insufficient for class {self.request_id} "
                    f"(required: {required_capacity_with_buffer} with {self.buffer_percent*100}% buffer, "
                    f"enrollment: {request.enrollment_count})"
                )
            )

        # Check if classroom is too large (if max_capacity is specified)
        if request.max_capacity is not None and classroom.capacity > request.max_capacity:
            return Violation(
                constraint_type=self.constraint_type,
                affected_request_id=self.request_id,
                affected_resource_id=classroom_id,
                message=(
                    f"Classroom {classroom_id} capacity ({classroom.capacity}) "
                    f"exceeds maximum allowed for class {self.request_id} "
                    f"(max: {request.max_capacity})"
                )
            )

        return None

    def explain(self, violation: Violation) -> str:
        """Generate human-readable explanation."""
        return violation.message

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.classroom_capacity"