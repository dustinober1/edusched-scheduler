"""Constraints for teacher availability and conflict prevention."""

from typing import TYPE_CHECKING, Optional

from edusched.constraints.base import Constraint, ConstraintContext, Violation

if TYPE_CHECKING:
    from edusched.domain.assignment import Assignment


class TeacherConflictConstraint(Constraint):
    """Prevents teachers from being assigned to overlapping sessions."""

    def __init__(self, teacher_id: str):
        """
        Initialize teacher conflict constraint.

        Args:
            teacher_id: The teacher ID this constraint applies to
        """
        self.teacher_id = teacher_id

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if teacher has overlapping assignments."""
        request = context.request_lookup.get(assignment.request_id)
        if not request:
            return None

        # Check primary teacher
        if request.teacher_id != self.teacher_id:
            # Also check additional teachers
            if (
                not request.additional_teachers
                or self.teacher_id not in request.additional_teachers
            ):
                return None

        # Check for conflicts with existing assignments
        for existing in solution:
            existing_request = context.request_lookup.get(existing.request_id)
            if not existing_request:
                continue

            # Skip if this is the same assignment
            if (
                existing.request_id == assignment.request_id
                and existing.occurrence_index == assignment.occurrence_index
            ):
                continue

            # Check if teacher is assigned to existing session
            teacher_in_existing = existing_request.teacher_id == self.teacher_id or (
                existing_request.additional_teachers
                and self.teacher_id in existing_request.additional_teachers
            )

            if not teacher_in_existing:
                continue

            # Check time overlap
            if self._times_overlap(assignment, existing):
                return Violation(
                    constraint_type=self.constraint_type,
                    affected_request_id=assignment.request_id,
                    message=(
                        f"Teacher {self.teacher_id} is double-booked: "
                        f"session {assignment.request_id} conflicts with session {existing.request_id} "
                        f"from {existing.start_time} to {existing.end_time}"
                    ),
                )

        return None

    def _times_overlap(self, assignment1: "Assignment", assignment2: "Assignment") -> bool:
        """Check if two assignments have overlapping times."""
        # Check same day first
        if assignment1.start_time.date() != assignment2.start_time.date():
            return False

        # Check time overlap
        return (
            assignment1.start_time < assignment2.end_time
            and assignment1.end_time > assignment2.start_time
        )

    def explain(self, violation: Violation) -> str:
        """Generate human-readable explanation."""
        return violation.message

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.teacher_conflict"


class TeacherAvailabilityConstraint(Constraint):
    """Ensures sessions are scheduled when the teacher is available."""

    def __init__(self, teacher_id: str):
        """
        Initialize teacher availability constraint.

        Args:
            teacher_id: The teacher ID this constraint applies to
        """
        self.teacher_id = teacher_id

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if assignment time is within teacher availability."""
        request = context.request_lookup.get(assignment.request_id)
        if not request:
            return None

        # Check primary teacher
        if request.teacher_id != self.teacher_id:
            # Also check additional teachers
            if (
                not request.additional_teachers
                or self.teacher_id not in request.additional_teachers
            ):
                return None

        teacher = context.teacher_lookup.get(self.teacher_id)
        if not teacher:
            return None  # Cannot validate without teacher info

        # Get day of week
        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        day_of_week = day_names[assignment.start_time.weekday()]

        # Check if teacher is available on this day
        if not teacher.is_available_day(day_of_week):
            return Violation(
                constraint_type=self.constraint_type,
                affected_request_id=assignment.request_id,
                message=(
                    f"Teacher {teacher.name} ({self.teacher_id}) "
                    f"is not available on {day_of_week.capitalize()} for session {assignment.request_id}"
                ),
            )

        # Check teacher's preferred times if specified
        if teacher.preferred_times:
            start_time_str = assignment.start_time.strftime("%H:%M")
            end_time_str = assignment.end_time.strftime("%H:%M")

            if not teacher.is_available_time(day_of_week, start_time_str, end_time_str):
                return Violation(
                    constraint_type=self.constraint_type,
                    affected_request_id=assignment.request_id,
                    message=(
                        f"Teacher {teacher.name} ({self.teacher_id}) "
                        f"is not available during {start_time_str}-{end_time_str} on {day_of_week.capitalize()} "
                        f"for session {assignment.request_id}"
                    ),
                )

        return None

    def explain(self, violation: Violation) -> str:
        """Generate human-readable explanation."""
        return violation.message

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.teacher_availability"


class TeacherWorkloadConstraint(Constraint):
    """Ensures teacher's workload doesn't exceed specified limits."""

    def __init__(self, teacher_id: str):
        """
        Initialize teacher workload constraint.

        Args:
            teacher_id: The teacher ID this constraint applies to
        """
        self.teacher_id = teacher_id

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if assignment would exceed teacher's workload limits."""
        request = context.request_lookup.get(assignment.request_id)
        if not request:
            return None

        # Check primary teacher
        if request.teacher_id != self.teacher_id:
            # Also check additional teachers
            if (
                not request.additional_teachers
                or self.teacher_id not in request.additional_teachers
            ):
                return None

        teacher = context.teacher_lookup.get(self.teacher_id)
        if not teacher or not teacher.max_daily_hours and not teacher.max_weekly_hours:
            return None

        # Get all assignments for this teacher
        teacher_assignments = []
        for existing in solution:
            existing_request = context.request_lookup.get(existing.request_id)
            if not existing_request:
                continue

            teacher_in_existing = existing_request.teacher_id == self.teacher_id or (
                existing_request.additional_teachers
                and self.teacher_id in existing_request.additional_teachers
            )

            if teacher_in_existing:
                teacher_assignments.append(existing)

        # Include the current assignment for checking
        all_assignments = teacher_assignments + [assignment]

        # Calculate workload

        daily_hours = {}
        weekly_hours = {}

        for assign in all_assignments:
            duration = assign.end_time - assign.start_time
            hours = duration.total_seconds() / 3600

            # Daily tracking
            day = assign.start_time.date()
            daily_hours[day] = daily_hours.get(day, 0) + hours

            # Weekly tracking
            week = assign.start_time.isocalendar()[1]
            weekly_hours[week] = weekly_hours.get(week, 0) + hours

        # Check daily limit
        if teacher.max_daily_hours:
            for day, hours in daily_hours.items():
                if hours > teacher.max_daily_hours:
                    return Violation(
                        constraint_type=self.constraint_type,
                        affected_request_id=assignment.request_id,
                        message=(
                            f"Teacher {teacher.name} would exceed daily limit of {teacher.max_daily_hours} hours "
                            f"({hours:.1f} hours on {day}) with session {assignment.request_id}"
                        ),
                    )

        # Check weekly limit
        if teacher.max_weekly_hours:
            for week, hours in weekly_hours.items():
                if hours > teacher.max_weekly_hours:
                    return Violation(
                        constraint_type=self.constraint_type,
                        affected_request_id=assignment.request_id,
                        message=(
                            f"Teacher {teacher.name} would exceed weekly limit of {teacher.max_weekly_hours} hours "
                            f"({hours:.1f} hours in week {week}) with session {assignment.request_id}"
                        ),
                    )

        return None

    def explain(self, violation: Violation) -> str:
        """Generate human-readable explanation."""
        return violation.message

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.teacher_workload"


class TeacherTravelTimeConstraint(Constraint):
    """Ensures sufficient travel time between classes in different buildings."""

    def __init__(self, teacher_id: str):
        """
        Initialize teacher travel time constraint.

        Args:
            teacher_id: The teacher ID this constraint applies to
        """
        self.teacher_id = teacher_id

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if teacher has sufficient travel time between classes."""
        request = context.request_lookup.get(assignment.request_id)
        if not request:
            return None

        # Check if this teacher is assigned to this session
        teacher_in_session = request.teacher_id == self.teacher_id or (
            request.additional_teachers and self.teacher_id in request.additional_teachers
        )
        if not teacher_in_session:
            return None

        # Get teacher information
        teacher = context.teacher_lookup.get(self.teacher_id)
        if not teacher:
            return None

        # Get building for current assignment
        current_building_id = self._get_assignment_building_id(assignment, context)

        # Get teacher's other assignments on the same day
        other_assignments = [
            a
            for a in solution
            if a != assignment  # Not the same assignment
            and a.start_time.date() == assignment.start_time.date()  # Same day
            and self._teacher_assigned_to_session(a, context)  # Teacher assigned
        ]

        # Check travel time to/from other classes
        for other in other_assignments:
            other_building_id = self._get_assignment_building_id(other, context)

            # Skip if same building or no building info
            if (
                not current_building_id
                or not other_building_id
                or current_building_id == other_building_id
            ):
                continue

            # Check if classes are consecutive (other before current)
            if other.end_time <= assignment.start_time:
                gap_minutes = (assignment.start_time - other.end_time).total_seconds() / 60
                if gap_minutes < teacher.max_travel_time_between_classes:
                    return Violation(
                        constraint_type=self.constraint_type,
                        affected_request_id=assignment.request_id,
                        message=(
                            f"Insufficient travel time from {other_building_id} to {current_building_id}: "
                            f"{gap_minutes:.0f} < {teacher.max_travel_time_between_classes} minutes"
                        ),
                    )

            # Check if classes are consecutive (current before other)
            elif assignment.end_time <= other.start_time:
                gap_minutes = (other.start_time - assignment.end_time).total_seconds() / 60
                if gap_minutes < teacher.max_travel_time_between_classes:
                    return Violation(
                        constraint_type=self.constraint_type,
                        affected_request_id=assignment.request_id,
                        message=(
                            f"Insufficient travel time from {current_building_id} to {other_building_id}: "
                            f"{gap_minutes:.0f} < {teacher.max_travel_time_between_classes} minutes"
                        ),
                    )

        return None

    def _get_assignment_building_id(
        self, assignment: "Assignment", context: ConstraintContext
    ) -> Optional[str]:
        """Get building ID for an assignment."""
        if "classroom" in assignment.assigned_resources:
            room_id = assignment.assigned_resources["classroom"][0]
            room = context.resource_lookup.get(room_id)
            if room and hasattr(room, "building_id"):
                return room.building_id
        return None

    def _teacher_assigned_to_session(
        self, assignment: "Assignment", context: ConstraintContext
    ) -> bool:
        """Check if teacher is assigned to a session."""
        request = context.request_lookup.get(assignment.request_id)
        if not request:
            return False

        return request.teacher_id == self.teacher_id or (
            request.additional_teachers and self.teacher_id in request.additional_teachers
        )

    def explain(self, violation: Violation) -> str:
        """Generate human-readable explanation."""
        return violation.message

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.teacher_travel_time"
