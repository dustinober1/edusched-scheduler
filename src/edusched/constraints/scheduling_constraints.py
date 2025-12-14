"""Constraints for scheduling patterns and time preferences."""

from typing import TYPE_CHECKING, Optional

from edusched.constraints.base import Constraint, ConstraintContext, Violation

if TYPE_CHECKING:
    from edusched.domain.assignment import Assignment


class SchedulingPatternConstraint(Constraint):
    """Ensures assignments follow the specified scheduling pattern."""

    def __init__(self, request_id: str):
        """
        Initialize scheduling pattern constraint.

        Args:
            request_id: The request ID this constraint applies to
        """
        self.request_id = request_id

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if assignment follows the scheduling pattern."""
        request = context.request_lookup.get(assignment.request_id)
        if not request or assignment.request_id != self.request_id:
            return None

        # If no pattern specified, allow any days (default to 5-day Mon-Fri)
        if not request.scheduling_pattern:
            # Default: Allow Monday-Friday (0-4)
            if assignment.start_time.weekday() > 4:  # Saturday or Sunday
                return Violation(
                    constraint_type=self.constraint_type,
                    affected_request_id=assignment.request_id,
                    message=(
                        f"Assignment {assignment.request_id} scheduled on weekend "
                        f"(no pattern specified, defaulting to Monday-Friday)"
                    ),
                )
            return None

        # Get the allowed days for this pattern
        pattern_days = self._get_pattern_days(request.scheduling_pattern)
        day_of_week = assignment.start_time.weekday()

        if day_of_week not in pattern_days:
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
                affected_request_id=assignment.request_id,
                message=(
                    f"Assignment {assignment.request_id} scheduled on {day_names[day_of_week]} "
                    f"which doesn't match pattern {request.scheduling_pattern}"
                ),
            )

        return None

    def _get_pattern_days(self, pattern: str) -> list[int]:
        """Get allowed weekday numbers for a pattern."""
        patterns = {
            "5days": [0, 1, 2, 3, 4],  # Mon-Fri
            "4days_mt": [0, 1, 2, 3],  # Mon-Thu
            "4days_tf": [1, 2, 3, 4],  # Tue-Fri
            "3days_mw": [0, 1, 2],  # Mon-Wed
            "3days_wf": [2, 3, 4],  # Wed-Fri
            "2days_mt": [0, 1],  # Mon-Tue
            "2days_tf": [3, 4],  # Thu-Fri
        }
        return patterns.get(pattern, [0, 1, 2, 3, 4])  # Default to Mon-Fri

    def explain(self, violation: Violation) -> str:
        """Generate human-readable explanation."""
        return violation.message

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.scheduling_pattern"


class HolidayAvoidanceConstraint(Constraint):
    """Ensures assignments are not scheduled during holidays."""

    def __init__(self, request_id: str):
        """
        Initialize holiday avoidance constraint.

        Args:
            request_id: The request ID this constraint applies to
        """
        self.request_id = request_id

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if assignment falls on a holiday."""
        request = context.request_lookup.get(assignment.request_id)
        if not request or assignment.request_id != self.request_id:
            return None

        # If holiday avoidance is disabled, skip check
        if not request.avoid_holidays:
            return None

        # Get the holiday calendar from institutional calendar
        calendar_id = context.problem.institutional_calendar_id
        if not calendar_id:
            return None  # No holiday calendar available

        calendar = context.calendar_lookup.get(calendar_id)
        if not calendar:
            return None

        # This is a simplified check - in a real implementation,
        # we'd need to integrate with HolidayCalendar
        assignment_date = assignment.start_time.date()

        # For now, check common holidays (would use HolidayCalendar in production)
        common_holidays = self._get_common_holidays(assignment_date.year)
        for holiday_start, holiday_end, holiday_name in common_holidays:
            if holiday_start <= assignment_date <= holiday_end:
                return Violation(
                    constraint_type=self.constraint_type,
                    affected_request_id=assignment.request_id,
                    message=(
                        f"Assignment {assignment.request_id} scheduled during "
                        f"{holiday_name} ({holiday_start} to {holiday_end})"
                    ),
                )

        return None

    def _get_common_holidays(self, year: int) -> list[tuple]:
        """Get common holidays for a year (simplified)."""
        from datetime import date

        # This is just an example - in production, use HolidayCalendar
        holidays = [
            # Winter Break
            (date(year, 12, 20), date(year + 1, 1, 10), "Winter Break"),
            # Spring Break (mid-March)
            (date(year, 3, 10), date(year, 3, 20), "Spring Break"),
            # Summer Break
            (date(year, 5, 15), date(year, 8, 20), "Summer Break"),
            # Thanksgiving (US - fourth Thursday of November)
            (date(year, 11, 25), date(year, 11, 29), "Thanksgiving Break"),
        ]

        return holidays

    def explain(self, violation: Violation) -> str:
        """Generate human-readable explanation."""
        return violation.message

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.holiday_avoidance"


class TimeSlotPreferenceConstraint(Constraint):
    """Soft constraint encouraging preferred time slots."""

    def __init__(self, request_id: str, weight: float = 1.0):
        """
        Initialize time slot preference constraint.

        Args:
            request_id: The request ID this constraint applies to
            weight: Weight for this preference (higher = more important)
        """
        self.request_id = request_id
        self.weight = weight

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if assignment uses preferred time slots (soft constraint)."""
        # This is a soft constraint, so we don't return violations
        # The preference information could be used by the solver's objective function
        return None

    def explain(self, violation: Violation) -> str:
        """Generate human-readable explanation."""
        return violation.message

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "soft.time_slot_preference"


class OccurrenceSpreadConstraint(Constraint):
    """Ensures class occurrences are spread throughout the term."""

    def __init__(self, request_id: str, min_days_between: int = 7):
        """
        Initialize occurrence spread constraint.

        Args:
            request_id: The request ID this constraint applies to
            min_days_between: Minimum days between occurrences
        """
        self.request_id = request_id
        self.min_days_between = min_days_between

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if occurrences are properly spread out."""
        # Filter assignments for this request
        request_assignments = [a for a in solution if a.request_id == self.request_id]

        if len(request_assignments) < 2:
            return None  # No spreading needed for single occurrence

        # Sort by date
        request_assignments.sort(key=lambda a: a.start_time.date())

        # Check consecutive assignments
        for i in range(len(request_assignments) - 1):
            current = request_assignments[i]
            next_one = request_assignments[i + 1]

            days_gap = (next_one.start_time.date() - current.start_time.date()).days

            if days_gap < self.min_days_between:
                return Violation(
                    constraint_type=self.constraint_type,
                    affected_request_id=self.request_id,
                    message=(
                        f"Occurrences of {self.request_id} are too close together: "
                        f"{days_gap} days between classes (minimum: {self.min_days_between})"
                    ),
                )

        return None

    def explain(self, violation: Violation) -> str:
        """Generate human-readable explanation."""
        return violation.message

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "soft.occurrence_spread"
