"""Hard constraint implementations."""

from typing import TYPE_CHECKING, List, Optional

from edusched.constraints.base import Constraint, ConstraintContext, Violation

if TYPE_CHECKING:
    from edusched.domain.assignment import Assignment


class NoOverlap(Constraint):
    """Prevents resource double-booking."""

    def __init__(self, resource_id: str) -> None:
        self.resource_id = resource_id

    def check(
        self,
        assignment: "Assignment",
        solution: List["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if assignment overlaps with existing assignments for this resource."""
        # Check if resource is assigned in this assignment
        for resource_ids in assignment.assigned_resources.values():
            if self.resource_id not in resource_ids:
                continue

            # Check for overlaps with existing assignments
            for existing in solution:
                for existing_resource_ids in existing.assigned_resources.values():
                    if self.resource_id not in existing_resource_ids:
                        continue

                    # Check for time overlap
                    if (
                        assignment.start_time < existing.end_time
                        and assignment.end_time > existing.start_time
                    ):
                        return Violation(
                            constraint_type=self.constraint_type,
                            affected_request_id=assignment.request_id,
                            affected_resource_id=self.resource_id,
                            message=f"Resource {self.resource_id} is double-booked",
                        )

        return None

    def explain(self, violation: Violation) -> str:
        """Explain the overlap violation."""
        return f"Resource '{violation.affected_resource_id}' is assigned to overlapping time slots"

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.no_overlap"


class BlackoutDates(Constraint):
    """Respects calendar blackout periods."""

    def __init__(self, calendar_id: str) -> None:
        self.calendar_id = calendar_id

    def check(
        self,
        assignment: "Assignment",
        solution: List["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if assignment falls within blackout periods."""
        calendar = context.calendar_lookup.get(self.calendar_id)
        if not calendar:
            return None

        if not calendar.is_available(assignment.start_time, assignment.end_time):
            return Violation(
                constraint_type=self.constraint_type,
                affected_request_id=assignment.request_id,
                message=f"Assignment falls within blackout period for calendar {self.calendar_id}",
            )

        return None

    def explain(self, violation: Violation) -> str:
        """Explain the blackout violation."""
        return "Assignment falls within a blackout period"

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.blackout_dates"


class MaxPerDay(Constraint):
    """Limits daily resource usage."""

    def __init__(self, resource_id: str, max_per_day: int) -> None:
        self.resource_id = resource_id
        self.max_per_day = max_per_day

    def check(
        self,
        assignment: "Assignment",
        solution: List["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if adding this assignment exceeds daily limit."""
        # Count assignments for this resource on the same day

        assignment_date = assignment.start_time.date()
        count = 0

        for existing in solution:
            if existing.start_time.date() == assignment_date:
                for resource_ids in existing.assigned_resources.values():
                    if self.resource_id in resource_ids:
                        count += 1

        # Check if this assignment would exceed the limit
        for resource_ids in assignment.assigned_resources.values():
            if self.resource_id in resource_ids:
                count += 1

        if count > self.max_per_day:
            return Violation(
                constraint_type=self.constraint_type,
                affected_request_id=assignment.request_id,
                affected_resource_id=self.resource_id,
                message=f"Resource {self.resource_id} exceeds daily limit of {self.max_per_day}",
            )

        return None

    def explain(self, violation: Violation) -> str:
        """Explain the daily limit violation."""
        return f"Resource exceeds daily limit of {self.max_per_day} assignments"

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.max_per_day"


class MinGapBetweenOccurrences(Constraint):
    """Enforces spacing between session occurrences."""

    def __init__(self, request_id: str, min_gap: "timedelta") -> None:  # noqa: F821
        self.request_id = request_id
        self.min_gap = min_gap

    def check(
        self,
        assignment: "Assignment",
        solution: List["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if gap between occurrences meets minimum requirement."""
        if assignment.request_id != self.request_id:
            return None

        # Find other occurrences of this request
        for existing in solution:
            if existing.request_id != self.request_id:
                continue

            # Calculate gap between assignments
            if existing.end_time <= assignment.start_time:
                gap = assignment.start_time - existing.end_time
            elif assignment.end_time <= existing.start_time:
                gap = existing.start_time - assignment.end_time
            else:
                # Overlapping assignments
                continue

            if gap < self.min_gap:
                return Violation(
                    constraint_type=self.constraint_type,
                    affected_request_id=self.request_id,
                    message=f"Gap between occurrences is {gap}, minimum required is {self.min_gap}",
                )

        return None

    def explain(self, violation: Violation) -> str:
        """Explain the gap violation."""
        return "Minimum gap between occurrences not maintained"

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.min_gap_between_occurrences"


class WithinDateRange(Constraint):
    """Enforces session date boundaries."""

    def __init__(self, request_id: str) -> None:
        self.request_id = request_id

    def check(
        self,
        assignment: "Assignment",
        solution: List["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if assignment is within date range."""
        if assignment.request_id != self.request_id:
            return None

        request = context.request_lookup.get(self.request_id)
        if not request:
            return None

        if (
            assignment.start_time < request.earliest_date
            or assignment.end_time > request.latest_date
        ):
            return Violation(
                constraint_type=self.constraint_type,
                affected_request_id=self.request_id,
                message=f"Assignment outside date range [{request.earliest_date}, {request.latest_date}]",
            )

        return None

    def explain(self, violation: Violation) -> str:
        """Explain the date range violation."""
        return "Assignment falls outside the specified date range"

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.within_date_range"


class AttributeMatch(Constraint):
    """Ensures resource attributes satisfy requirements."""

    def __init__(self, request_id: str) -> None:
        self.request_id = request_id

    def check(
        self,
        assignment: "Assignment",
        solution: List["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if assigned resources satisfy attribute requirements."""
        if assignment.request_id != self.request_id:
            return None

        request = context.request_lookup.get(self.request_id)
        if not request or not request.required_attributes:
            return None

        # Check each assigned resource
        for resource_ids in assignment.assigned_resources.values():
            for resource_id in resource_ids:
                resource = context.resource_lookup.get(resource_id)
                if not resource:
                    continue

                if not resource.can_satisfy(request.required_attributes):
                    return Violation(
                        constraint_type=self.constraint_type,
                        affected_request_id=self.request_id,
                        affected_resource_id=resource_id,
                        message=f"Resource {resource_id} does not satisfy attribute requirements",
                    )

        return None

    def explain(self, violation: Violation) -> str:
        """Explain the attribute mismatch."""
        return "Resource does not satisfy required attributes"

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.attribute_match"
