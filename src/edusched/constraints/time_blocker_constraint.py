"""Constraint for institutional time blockers."""

from typing import TYPE_CHECKING, Optional

from edusched.constraints.base import Constraint, ConstraintContext, Violation

if TYPE_CHECKING:
    from edusched.domain.assignment import Assignment
    from edusched.domain.time_blockers import TimeBlocker


class TimeBlockerConstraint(Constraint):
    """Prevents scheduling during blocked time periods."""

    def __init__(self, time_blocker: "TimeBlocker"):
        """
        Initialize time blocker constraint.

        Args:
            time_blocker: The TimeBlocker instance with blocked periods
        """
        self.time_blocker = time_blocker

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if assignment conflicts with any time blockers."""
        # Check both start and end times
        is_start_blocked, block_name = self.time_blocker.is_time_blocked(assignment.start_time)
        if is_start_blocked:
            return Violation(
                constraint_type=self.constraint_type,
                affected_request_id=assignment.request_id,
                message=f"Class start time conflicts with {block_name}"
            )

        is_end_blocked, block_name = self.time_blocker.is_time_blocked(assignment.end_time)
        if is_end_blocked:
            return Violation(
                constraint_type=self.constraint_type,
                affected_request_id=assignment.request_id,
                message=f"Class end time conflicts with {block_name}"
            )

        # Check if the class duration spans through a blocked period
        # We check the middle of the class to catch longer classes that span breaks
        class_duration = assignment.end_time - assignment.start_time
        middle_time = assignment.start_time + class_duration / 2

        is_middle_blocked, block_name = self.time_blocker.is_time_blocked(middle_time)
        if is_middle_blocked:
            return Violation(
                constraint_type=self.constraint_type,
                affected_request_id=assignment.request_id,
                message=f"Class spans through {block_name}"
            )

        return None

    def explain(self, violation: Violation) -> str:
        """Generate human-readable explanation."""
        return violation.message

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.time_blocker"