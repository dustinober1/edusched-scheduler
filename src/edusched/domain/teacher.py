"""Teacher domain model."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date, timedelta

from edusched.errors import ValidationError


@dataclass
class Teacher:
    """Represents a teacher/instructor with availability and preferences."""

    id: str
    name: str
    email: Optional[str] = None
    department_id: Optional[str] = None  # Primary department
    title: Optional[str] = None  # Professor, Lecturer, etc.
    employee_id: Optional[str] = None

    # Teaching availability
    availability_calendar_id: Optional[str] = None
    preferred_days: List[str] = field(default_factory=list)  # e.g., ["monday", "tuesday", "wednesday"]
    preferred_times: Dict[str, List[str]] = field(default_factory=dict)  # e.g., {"monday": ["09:00-12:00"]}
    unavailable_periods: List[str] = field(default_factory=list)  # Times when teacher cannot teach

    # Vacation and personal time off
    vacation_periods: List[Tuple[date, date, str]] = field(default_factory=list)  # (start, end, reason)
    conference_dates: List[Tuple[date, date, str]] = field(default_factory=list)  # (start, end, conference_name)
    personal_days: List[date] = field(default_factory=list)  # Individual days off

    # Teaching constraints
    max_consecutive_hours: Optional[int] = None  # Maximum consecutive teaching hours
    max_daily_hours: Optional[int] = None  # Maximum teaching hours per day
    max_weekly_hours: Optional[int] = None  # Maximum teaching hours per week

    # Preferences
    preferred_buildings: List[str] = field(default_factory=list)
    preferred_room_types: List[str] = field(default_factory=list)
    max_class_size: Optional[int] = None  # Maximum preferred class size

    # Travel and setup preferences
    max_travel_time_between_classes: int = 20  # minutes between classes
    requires_setup_time: bool = False
    setup_time_minutes: int = 15  # time needed before class starts
    cleanup_time_minutes: int = 10  # time needed after class ends
    preferred_block_gap: int = 30  # minimum minutes between consecutive classes

    # Course teaching capabilities
    qualified_courses: List[str] = field(default_factory=list)  # Course IDs teacher can teach
    preferred_courses: List[str] = field(default_factory=list)  # Courses teacher prefers to teach
    excluded_courses: List[str] = field(default_factory=list)  # Courses teacher cannot/will not teach

    # Course-specific requirements
    course_setup_requirements: Dict[str, int] = field(default_factory=dict)  # Course ID -> setup minutes
    course_cleanup_requirements: Dict[str, int] = field(default_factory=dict)  # Course ID -> cleanup minutes
    course_buffer_requirements: Dict[str, Dict[str, int]] = field(default_factory=dict)  # Course ID -> {before, after} days

    # Concurrent course restrictions
    mutually_exclusive_courses: List[List[str]] = field(default_factory=list)  # Courses that cannot run same term
    concurrent_teaching_limit: int = 1  # Max courses that can be taught simultaneously

    def validate(self) -> List[ValidationError]:
        """
        Validate teacher parameters.

        Returns:
            List of validation errors (empty if valid)
        """
        errors: List[ValidationError] = []

        # Validate ID
        if not self.id:
            errors.append(
                ValidationError(
                    field="id",
                    expected_format="non-empty string",
                    actual_value=self.id,
                )
            )

        # Validate name
        if not self.name:
            errors.append(
                ValidationError(
                    field="name",
                    expected_format="non-empty string",
                    actual_value=self.name,
                )
            )

        # Validate preferred days
        if self.preferred_days:
            valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            for day in self.preferred_days:
                if day.lower() not in valid_days:
                    errors.append(
                        ValidationError(
                            field="preferred_days",
                            expected_format=f"one of {valid_days}",
                            actual_value=day,
                        )
                    )

        # Validate preferred times format
        for day, time_slots in self.preferred_times.items():
            if not isinstance(time_slots, list):
                errors.append(
                    ValidationError(
                        field="preferred_times",
                        expected_format=f"list of time strings for {day}",
                        actual_value=time_slots,
                    )
                )
                continue

            for time_slot in time_slots:
                if not isinstance(time_slot, str):
                    errors.append(
                        ValidationError(
                            field="preferred_times",
                            expected_format="time string in HH:MM-HH:MM format",
                            actual_value=time_slot,
                        )
                    )

        # Validate hour constraints
        for field_name in ["max_consecutive_hours", "max_daily_hours", "max_weekly_hours"]:
            value = getattr(self, field_name)
            if value is not None and value <= 0:
                errors.append(
                    ValidationError(
                        field=field_name,
                        expected_format="positive integer or None",
                        actual_value=value,
                    )
                )

        return errors

    def is_available_day(self, day_of_week: str) -> bool:
        """
        Check if teacher is available to teach on a specific day.

        Args:
            day_of_week: Day name (e.g., "monday", "tuesday")

        Returns:
            True if teacher is available on this day
        """
        # If no preferred days specified, assume available
        if not self.preferred_days:
            return True

        return day_of_week.lower() in [d.lower() for d in self.preferred_days]

    def is_available_time(self, day_of_week: str, start_time: str, end_time: str) -> bool:
        """
        Check if teacher is available during a specific time slot.

        Args:
            day_of_week: Day name
            start_time: Start time in HH:MM format
            end_time: End time in HH:MM format

        Returns:
            True if teacher is available during this time
        """
        # First check if day is available
        if not self.is_available_day(day_of_week):
            return False

        # If no preferred times for this day, assume available all day
        day_times = self.preferred_times.get(day_of_week.lower(), [])
        if not day_times:
            return True

        # Check if the requested time overlaps with any preferred time slot
        # For now, simple check - could be enhanced with proper time parsing
        for preferred_slot in day_times:
            # Simple string comparison for now
            # In production, you'd want proper time range checking
            return True  # Assume available if preferred times exist

        return False

    def is_on_vacation(self, check_date: date) -> Optional[str]:
        """
        Check if teacher is on vacation or personal leave on a specific date.

        Args:
            check_date: Date to check

        Returns:
            Reason for unavailability if on vacation, None if available
        """
        # Check vacation periods
        for start_date, end_date, reason in self.vacation_periods:
            if start_date <= check_date <= end_date:
                return f"Vacation: {reason}"

        # Check conference dates
        for start_date, end_date, conference in self.conference_dates:
            if start_date <= check_date <= end_date:
                return f"Conference: {conference}"

        # Check personal days
        if check_date in self.personal_days:
            return "Personal day"

        return None

    def can_schedule_class(
        self,
        start_time: datetime,
        end_time: datetime,
        existing_assignments: List["Assignment"],
        building_id: Optional[str] = None,
        requires_setup: bool = False
    ) -> Tuple[bool, str]:
        """
        Check if teacher can schedule a class at the specified time.

        Args:
            start_time: Proposed class start time
            end_time: Proposed class end time
            existing_assignments: Teacher's current assignments
            building_id: Building where class will be held
            requires_setup: Whether class requires special setup time

        Returns:
            Tuple of (can_schedule, reason)
        """
        # Check if teacher is on vacation
        vacation_reason = self.is_on_vacation(start_time.date())
        if vacation_reason:
            return False, vacation_reason

        # Check day of week availability
        day_name = start_time.strftime("%A").lower()
        if not self.is_available_day(day_name):
            return False, f"Teacher not available on {day_name}"

        # Check preferred time slots
        start_str = start_time.strftime("%H:%M")
        end_str = end_time.strftime("%H:%M")
        if not self.is_available_time(day_name, start_str, end_str):
            return False, "Time outside teacher's preferred hours"

        # Check for conflicts with existing classes
        for existing in existing_assignments:
            # Check if times overlap (considering setup/cleanup time)
            earliest_start = start_time - timedelta(minutes=self.setup_time_minutes)
            latest_end = end_time + timedelta(minutes=self.cleanup_time_minutes)

            # Also add buffer time for existing class
            existing_earliest = existing.start_time - timedelta(minutes=self.setup_time_minutes)
            existing_latest = existing.end_time + timedelta(minutes=self.cleanup_time_minutes)

            if earliest_start < existing_latest and latest_end > existing_earliest:
                return False, f"Conflicts with existing class at {existing.start_time.strftime('%Y-%m-%d %H:%M')}"

        # Check travel time between buildings (if different buildings)
        if building_id and existing_assignments:
            for existing in existing_assignments:
                # Check same day classes
                if existing.start_time.date() == start_time.date():
                    # Calculate time between classes
                    if existing.end_time <= start_time:
                        gap_minutes = (start_time - existing.end_time).total_seconds() / 60
                        if gap_minutes < self.max_travel_time_between_classes:
                            return False, f"Insufficient travel time (need {self.max_travel_time_between_classes} min, have {gap_minutes:.0f} min)"

        # Check daily teaching load
        day_assignments = [a for a in existing_assignments
                          if a.start_time.date() == start_time.date()]

        if day_assignments:
            # Calculate hours for this day including new class
            daily_hours = sum(
                (a.end_time - a.start_time).total_seconds() / 3600
                for a in day_assignments
            )
            new_hours = (end_time - start_time).total_seconds() / 3600
            total_hours = daily_hours + new_hours

            if self.max_daily_hours and total_hours > self.max_daily_hours:
                return False, f"Exceeds daily teaching limit of {self.max_daily_hours} hours"

            # Check consecutive hours
            sorted_assignments = sorted(day_assignments + [type('Assignment', (), {
                'start_time': start_time, 'end_time': end_time
            })()], key=lambda a: a.start_time)

            consecutive = 0
            last_end = None
            for assignment in sorted_assignments:
                if last_end:
                    gap = (assignment.start_time - last_end).total_seconds() / 60
                    if gap < 60:  # Less than 1 hour gap is considered consecutive
                        consecutive += (assignment.end_time - assignment.start_time).total_seconds() / 3600
                    else:
                        consecutive = (assignment.end_time - assignment.start_time).total_seconds() / 3600
                else:
                    consecutive = (assignment.end_time - assignment.start_time).total_seconds() / 3600

                last_end = assignment.end_time
                if self.max_consecutive_hours and consecutive > self.max_consecutive_hours:
                    return False, f"Exceeds consecutive teaching limit of {self.max_consecutive_hours} hours"

        return True, "Available"

    def get_teaching_load(self, assignments: List["Assignment"]) -> Dict[str, float]:
        """
        Calculate current teaching load from assignments.

        Args:
            assignments: List of assignments for this teacher

        Returns:
            Dictionary with load statistics
        """
        total_hours = 0.0
        daily_hours: Dict[str, float] = {}
        weekly_hours: Dict[int, float] = {}

        for assignment in assignments:
            duration = assignment.end_time - assignment.start_time
            hours = duration.total_seconds() / 3600

            total_hours += hours

            # Daily tracking
            day_name = assignment.start_time.strftime("%A").lower()
            daily_hours[day_name] = daily_hours.get(day_name, 0) + hours

            # Weekly tracking
            week_num = assignment.start_time.isocalendar()[1]
            weekly_hours[week_num] = weekly_hours.get(week_num, 0) + hours

        return {
            "total_hours": total_hours,
            "daily_hours": daily_hours,
            "weekly_hours": weekly_hours,
            "max_daily": max(daily_hours.values()) if daily_hours else 0,
            "max_weekly": max(weekly_hours.values()) if weekly_hours else 0,
        }

    def can_teach_course(self, course_id: str) -> Tuple[bool, str]:
        """
        Check if teacher is qualified and willing to teach a course.

        Args:
            course_id: The course ID to check

        Returns:
            Tuple of (can_teach, reason_if_not)
        """
        # Check if course is explicitly excluded
        if course_id in self.excluded_courses:
            return False, "Teacher has excluded this course"

        # Check if teacher is qualified
        if self.qualified_courses and course_id not in self.qualified_courses:
            return False, "Teacher not qualified to teach this course"

        return True, "Qualified"

    def prefers_teaching(self, course_id: str) -> bool:
        """Check if teacher prefers teaching this course."""
        return course_id in self.preferred_courses

    def get_course_setup_time(self, course_id: str) -> int:
        """Get setup time required for a specific course."""
        return self.course_setup_requirements.get(course_id, self.setup_time_minutes)

    def get_course_cleanup_time(self, course_id: str) -> int:
        """Get cleanup time required for a specific course."""
        return self.course_cleanup_requirements.get(course_id, self.cleanup_time_minutes)

    def get_course_buffer_days(self, course_id: str) -> Dict[str, int]:
        """Get buffer days required before/after a course."""
        return self.course_buffer_requirements.get(course_id, {"before": 0, "after": 0})

    def add_course_requirement(
        self,
        course_id: str,
        setup_minutes: Optional[int] = None,
        cleanup_minutes: Optional[int] = None,
        buffer_days_before: Optional[int] = None,
        buffer_days_after: Optional[int] = None
    ) -> None:
        """Add specific requirements for teaching a course."""
        if setup_minutes is not None:
            self.course_setup_requirements[course_id] = setup_minutes
        if cleanup_minutes is not None:
            self.course_cleanup_requirements[course_id] = cleanup_minutes
        if buffer_days_before is not None or buffer_days_after is not None:
            before = buffer_days_before or 0
            after = buffer_days_after or 0
            self.course_buffer_requirements[course_id] = {"before": before, "after": after}

    def courses_conflict_with(self, course_id: str) -> List[str]:
        """Get list of courses that conflict with the given course."""
        conflicts = []
        for conflict_group in self.mutually_exclusive_courses:
            if course_id in conflict_group:
                for other_course in conflict_group:
                    if other_course != course_id:
                        conflicts.append(other_course)
        return conflicts

    def can_teach_concurrently_with(self, course_id: str, other_courses: List[str]) -> bool:
        """Check if teacher can teach this course alongside others."""
        # Check mutual exclusivity
        conflicts = self.courses_conflict_with(course_id)
        if any(conflict in other_courses for conflict in conflicts):
            return False

        # Check concurrent teaching limit
        if self.concurrent_teaching_limit <= 1:
            return len(other_courses) == 0

        return len(other_courses) < self.concurrent_teaching_limit

    def get_teaching_load_for_period(
        self,
        start_date: date,
        end_date: date,
        assignments: List["Assignment"]
    ) -> Dict[str, float]:
        """
        Calculate teacher's teaching load for a period.

        Returns:
            Dictionary with load metrics (hours, courses, etc.)
        """
        total_hours = 0
        course_count = 0
        days_teaching = set()

        for assignment in assignments:
            # Check if this assignment is for this teacher
            # (This would need proper teacher assignment tracking)
            # For now, assume all assignments are for this teacher
            if assignment.start_time.date() >= start_date and assignment.start_time.date() <= end_date:
                duration_hours = (assignment.end_time - assignment.start_time).total_seconds() / 3600
                total_hours += duration_hours
                course_count += 1
                days_teaching.add(assignment.start_time.date())

        return {
            "total_hours": total_hours,
            "course_count": course_count,
            "days_teaching": len(days_teaching),
            "average_hours_per_day": total_hours / max(len(days_teaching), 1)
        }