"""Student domain model for registration and course planning."""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from edusched.errors import ValidationError


class StudentStatus(Enum):
    """Student academic status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_LEAVE = "on_leave"
    GRADUATED = "graduated"
    WITHDRAWN = "withdrawn"


class AcademicLevel(Enum):
    """Student academic level."""

    FRESHMAN = "freshman"
    SOPHOMORE = "sophomore"
    JUNIOR = "junior"
    SENIOR = "senior"
    GRADUATE = "graduate"
    POSTDOCTORAL = "postdoctoral"


@dataclass
class Registration:
    """Represents a student's course registration."""

    student_id: str
    course_id: str
    section_id: Optional[str] = None  # For multi-section courses
    registration_date: Optional[datetime] = None
    status: str = "registered"  # registered, waitlisted, dropped
    waitlist_position: Optional[int] = None


@dataclass
class EnrollmentRecord:
    """Tracks student's academic progress."""

    student_id: str
    semester: str
    year: int
    gpa: Optional[float] = None
    credits_attempted: int = 0
    credits_earned: int = 0
    on_academic_probation: bool = False
    honors_list: bool = False


@dataclass
class Student:
    """Represents a student with registration and scheduling needs."""

    id: str
    first_name: str
    last_name: str
    email: Optional[str] = None
    student_number: Optional[str] = None
    status: StudentStatus = StudentStatus.ACTIVE
    academic_level: AcademicLevel = AcademicLevel.FRESHMAN
    major_ids: List[str] = field(default_factory=list)
    minor_ids: List[str] = field(default_factory=list)
    concentration: Optional[str] = None

    # Registration preferences
    preferred_sections: Dict[str, int] = field(
        default_factory=dict
    )  # course_id -> section preference
    avoid_times: List[Dict[str, str]] = field(
        default_factory=list
    )  # [{"start": "08:00", "end": "09:00"}]
    max_credits_per_semester: int = 18
    min_credits_per_semester: int = 12

    # Physical constraints
    mobility_needs: bool = False
    requires_wheelchair_access: bool = False
    elevator_required: bool = False

    # Work/schedule constraints
    has_job: bool = False
    work_hours: List[Dict[str, str]] = field(
        default_factory=list
    )  # [{"day": "monday", "start": "17:00", "end": "22:00"}]
    preferred_class_blocks: List[str] = field(
        default_factory=list
    )  # ["morning", "afternoon", "evening"]

    # Academic information
    cumulative_gpa: Optional[float] = None
    credits_completed: int = 0
    honors_student: bool = False
    athlete: bool = False
    international_student: bool = False

    # Special programs
    tutoring_assignments: List[str] = field(default_factory=list)
    research_assistances: List[str] = field(default_factory=list)
    teaching_assistances: List[str] = field(default_factory=list)

    # Registration tracking
    registrations: List[Registration] = field(default_factory=list)
    enrollment_history: List[EnrollmentRecord] = field(default_factory=list)
    holds: List[Dict[str, str]] = field(
        default_factory=list
    )  # [{"type": "financial", "reason": ""}]

    # Course history for prerequisite checking
    completed_courses: Dict[str, Tuple[date, str]] = field(
        default_factory=dict
    )  # course_id -> (date, grade)
    in_progress_courses: Set[str] = field(default_factory=set)

    def validate(self) -> List[ValidationError]:
        """Validate student data."""
        errors: List[ValidationError] = []

        if not self.id:
            errors.append(
                ValidationError(
                    field="id", expected_format="non-empty string", actual_value=self.id
                )
            )

        if not self.first_name or not self.last_name:
            errors.append(
                ValidationError(
                    field="name",
                    expected_format="first and last name required",
                    actual_value=f"{self.first_name} {self.last_name}",
                )
            )

        # Validate credit limits
        if self.min_credits_per_semester > self.max_credits_per_semester:
            errors.append(
                ValidationError(
                    field="credits",
                    expected_format="min_credits <= max_credits",
                    actual_value=f"{self.min_credits_per_semester} > {self.max_credits_per_semester}",
                )
            )

        # Validate GPA if provided
        if self.cumulative_gpa is not None:
            if not (0.0 <= self.cumulative_gpa <= 4.0):
                errors.append(
                    ValidationError(
                        field="cumulative_gpa",
                        expected_format="0.0 to 4.0",
                        actual_value=self.cumulative_gpa,
                    )
                )

        return errors

    def get_full_name(self) -> str:
        """Get student's full name."""
        return f"{self.first_name} {self.last_name}"

    def has_hold(self, hold_type: str) -> bool:
        """Check if student has a specific type of hold."""
        return any(hold["type"] == hold_type for hold in self.holds)

    def can_register(self, check_date: Optional[datetime] = None) -> Tuple[bool, str]:
        """Check if student can register for courses."""
        # Check status
        if self.status != StudentStatus.ACTIVE:
            return False, f"Student status is {self.status.value}"

        # Check holds
        if self.has_hold("registration"):
            return False, "Registration hold on account"

        if self.has_hold("financial"):
            return False, "Financial hold on account"

        if self.has_hold("academic"):
            return False, "Academic hold on account"

        return True, "Can register"

    def has_completed_prerequisite(self, prerequisite_course: str) -> bool:
        """Check if student has completed a prerequisite course."""
        return prerequisite_course in self.completed_courses

    def meets_prerequisites(self, prerequisites: List[str]) -> Tuple[bool, List[str]]:
        """Check if student meets all prerequisites for a course."""
        missing = []
        for prereq in prerequisites:
            if not self.has_completed_prerequisite(prereq):
                missing.append(prereq)
        return len(missing) == 0, missing

    def has_time_conflict(
        self,
        new_course_time: Tuple[datetime, datetime],
        existing_courses: List[Tuple[datetime, datetime]],
    ) -> bool:
        """Check if new course time conflicts with existing courses."""
        for existing_start, existing_end in existing_courses:
            # Check for overlap
            if new_course_time[0] < existing_end and new_course_time[1] > existing_start:
                return True
        return False

    def prefers_time_block(self, time_block: str) -> bool:
        """Check if student prefers this time block."""
        if not self.preferred_class_blocks:
            return True  # No preference
        return time_block in self.preferred_class_blocks

    def is_available_at_time(self, check_time: datetime) -> bool:
        """Check if student is available at a specific time."""
        # Check work schedule
        day_name = check_time.strftime("%A").lower()
        time_str = check_time.strftime("%H:%M")

        for work_shift in self.work_hours:
            if work_shift.get("day", "").lower() == day_name:
                work_start = work_shift.get("start", "")
                work_end = work_shift.get("end", "")
                if work_start <= time_str <= work_end:
                    return False

        # Check avoid times
        for avoid_time in self.avoid_times:
            if avoid_time.get("start", "") <= time_str <= avoid_time.get("end", ""):
                return False

        return True

    def get_semester_schedule(self, semester: str, year: int) -> List[Registration]:
        """Get student's schedule for a specific semester."""
        return [
            reg
            for reg in self.registrations
            if reg.status == "registered"
            and self._get_semester_from_date(reg.registration_date or datetime.now()) == semester
            and (reg.registration_date or datetime.now()).year == year
        ]

    def _get_semester_from_date(self, date: datetime) -> str:
        """Determine semester from date."""
        month = date.month
        if month in [1, 2, 3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "fall"

    def get_current_credits(self) -> int:
        """Calculate current semester credits."""
        current_semester = self._get_semester_from_date(datetime.now())
        current_year = datetime.now().year

        current_registrations = self.get_semester_schedule(current_semester, current_year)
        # This would typically fetch course credits from database
        return len(current_registrations) * 3  # Assuming 3 credits per course

    def add_registration(self, course_id: str, section_id: Optional[str] = None) -> Registration:
        """Add a new registration."""
        registration = Registration(
            student_id=self.id,
            course_id=course_id,
            section_id=section_id,
            registration_date=datetime.now(),
        )
        self.registrations.append(registration)
        return registration

    def drop_course(self, course_id: str) -> bool:
        """Drop a course."""
        for reg in self.registrations:
            if reg.course_id == course_id and reg.status == "registered":
                reg.status = "dropped"
                return True
        return False
