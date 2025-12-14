"""Base SIS integration framework for EduSched.

Provides abstract interfaces and common functionality for
Student Information System (SIS) integrations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


@dataclass
class Student:
    """Student record from SIS."""

    student_id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    student_type: str = "undergraduate"  # undergraduate, graduate, etc.
    program: str = ""
    department: str = ""
    year: int = 1
    gpa: float = 0.0
    credits: int = 0
    status: str = "active"  # active, inactive, graduated
    enrollment_date: Optional[datetime] = None
    expected_graduation: Optional[datetime] = None

    # Academic info
    advisor_id: Optional[str] = None
    concentration: str = ""
    minor: str = ""

    # Preferences
    preferred_campus: Optional[str] = None
    preferred_schedule_times: List[str] = field(default_factory=list)
    disabilities: List[str] = field(default_factory=list)
    accommodations: List[str] = field(default_factory=list)

    # Sync metadata
    sis_id: Optional[str] = None  # ID in external SIS
    last_sync: Optional[datetime] = None
    sync_status: str = "pending"  # pending, synced, error


@dataclass
class Course:
    """Course record from SIS."""

    course_code: str
    title: str
    description: str = ""
    credits: int = 3
    department: str = ""
    level: str = "undergraduate"  # undergraduate, graduate
    prerequisites: List[str] = field(default_factory=list)
    corequisites: List[str] = field(default_factory=list)
    antirequisites: List[str] = field(default_factory=list)

    # Scheduling info
    duration_hours: float = 3.0
    contact_hours: float = 3.0
    lab_hours: float = 0.0
    requires_lab: bool = False
    max_enrollment: int = 30
    min_enrollment: int = 5

    # Resource requirements
    room_type: str = "classroom"  # classroom, lab, lecture_hall, etc.
    special_equipment: List[str] = field(default_factory=list)
    tech_requirements: List[str] = field(default_factory=list)

    # Sync metadata
    sis_id: Optional[str] = None
    last_sync: Optional[datetime] = None
    sync_status: str = "pending"


@dataclass
class CourseSection:
    """Course section/offering from SIS."""

    section_id: str
    course_code: str
    term: str  # e.g., "Fall2024", "Spring2025"
    section_number: str  # e.g., "001", "A01"
    instructor_id: Optional[str] = None
    instructor_name: str = ""
    schedule_type: str = "lecture"  # lecture, lab, seminar, etc.

    # Enrollment
    current_enrollment: int = 0
    max_enrollment: int = 30
    waitlist_count: int = 0
    status: str = "active"  # active, cancelled, full

    # Meeting pattern
    meeting_days: List[int] = field(default_factory=list)  # 0=Monday, 6=Sunday
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: str = ""
    campus: str = ""

    # Dates
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # Special instructions
    notes: str = ""
    special_requirements: List[str] = field(default_factory=list)

    # Sync metadata
    sis_id: Optional[str] = None
    last_sync: Optional[datetime] = None
    sync_status: str = "pending"


@dataclass
class Instructor:
    """Instructor/Faculty record from SIS."""

    instructor_id: str
    first_name: str
    last_name: str
    email: str
    title: str = ""  # Professor, Lecturer, etc.
    department: str = ""
    rank: str = ""  # Assistant, Associate, Full Professor
    status: str = "active"  # active, inactive, emeritus

    # Contact info
    office: str = ""
    phone: Optional[str] = None

    # Teaching preferences
    max_courses_per_term: int = 4
    preferred_times: List[str] = field(default_factory=list)
    preferred_room_types: List[str] = field(default_factory=list)
    research_days: List[int] = field(default_factory=list)

    # Certifications
    certifications: List[str] = field(default_factory=list)
    specializations: List[str] = field(default_factory=list)

    # Sync metadata
    sis_id: Optional[str] = None
    last_sync: Optional[datetime] = None
    sync_status: str = "pending"


@dataclass
class Enrollment:
    """Student enrollment record from SIS."""

    enrollment_id: str
    student_id: str
    section_id: str
    term: str
    status: str = "enrolled"  # enrolled, waitlisted, dropped, completed
    enrollment_date: Optional[datetime] = None
    grade: Optional[str] = None
    credits_attempted: int = 0
    credits_earned: int = 0

    # Financial info
    tuition_paid: bool = False
    financial_aid: bool = False
    payment_plan: bool = False

    # Sync metadata
    sis_id: Optional[str] = None
    last_sync: Optional[datetime] = None
    sync_status: str = "pending"


@dataclass
class SISConnection:
    """Connection details for an SIS."""

    sis_name: str
    sis_type: str  # canvas, banner, blackboard, custom
    base_url: str
    credentials: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True

    # Sync settings
    auto_sync: bool = True
    sync_frequency_minutes: int = 60
    last_sync: Optional[datetime] = None
    sync_endpoints: Dict[str, str] = field(default_factory=dict)

    # Data mapping
    field_mappings: Dict[str, str] = field(default_factory=dict)
    custom_attributes: Dict[str, Any] = field(default_factory=dict)

    # Permissions
    can_read_students: bool = True
    can_read_courses: bool = True
    can_read_enrollments: bool = True
    can_write_enrollments: bool = False
    can_write_schedules: bool = False


class SISProvider(ABC):
    """Abstract base class for SIS providers."""

    @abstractmethod
    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Authenticate with the SIS."""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Test the connection to the SIS."""
        pass

    # Student operations
    @abstractmethod
    def get_students(self, filters: Dict[str, Any] = None, limit: int = 1000) -> List[Student]:
        """Get students from SIS."""
        pass

    @abstractmethod
    def get_student(self, student_id: str) -> Optional[Student]:
        """Get a specific student from SIS."""
        pass

    @abstractmethod
    def get_student_enrollments(
        self, student_id: str, term: Optional[str] = None
    ) -> List[Enrollment]:
        """Get student enrollments."""
        pass

    # Course operations
    @abstractmethod
    def get_courses(self, filters: Dict[str, Any] = None, limit: int = 1000) -> List[Course]:
        """Get courses from SIS."""
        pass

    @abstractmethod
    def get_course(self, course_code: str) -> Optional[Course]:
        """Get a specific course from SIS."""
        pass

    @abstractmethod
    def get_course_sections(
        self, course_code: str, term: Optional[str] = None
    ) -> List[CourseSection]:
        """Get course sections."""
        pass

    # Instructor operations
    @abstractmethod
    def get_instructors(
        self, filters: Dict[str, Any] = None, limit: int = 1000
    ) -> List[Instructor]:
        """Get instructors from SIS."""
        pass

    @abstractmethod
    def get_instructor(self, instructor_id: str) -> Optional[Instructor]:
        """Get a specific instructor from SIS."""
        pass

    # Enrollment operations
    @abstractmethod
    def get_enrollments(
        self, filters: Dict[str, Any] = None, limit: int = 1000
    ) -> List[Enrollment]:
        """Get enrollments from SIS."""
        pass

    @abstractmethod
    def update_enrollment(self, enrollment_id: str, updates: Dict[str, Any]) -> bool:
        """Update enrollment record."""
        pass

    # Schedule operations
    @abstractmethod
    def get_term_schedule(self, term: str, filters: Dict[str, Any] = None) -> List[CourseSection]:
        """Get schedule for a term."""
        pass

    @abstractmethod
    def push_schedule(self, sections: List[CourseSection], term: str) -> Dict[str, bool]:
        """Push schedule to SIS."""
        pass


class SISManager:
    """Manages SIS integrations and data synchronization."""

    def __init__(self):
        self.providers: Dict[str, SISProvider] = {}
        self.connections: Dict[str, SISConnection] = {}
        self.data_cache = {
            "students": {},
            "courses": {},
            "instructors": {},
            "enrollments": {},
        }
        self.sync_history: List[Dict[str, Any]] = []

    def add_connection(self, connection: SISConnection) -> bool:
        """Add an SIS connection."""
        provider = self._create_provider(connection.sis_type)
        if not provider:
            return False

        # Authenticate
        if not provider.authenticate(connection.credentials):
            return False

        # Test connection
        if not provider.test_connection():
            return False

        self.providers[connection.sis_name] = provider
        self.connections[connection.sis_name] = connection
        return True

    def sync_all_data(self, connection_name: str, term: Optional[str] = None) -> Dict[str, Any]:
        """Sync all data from an SIS."""
        connection = self.connections.get(connection_name)
        if not connection or not connection.is_active:
            return {"success": False, "error": "Connection not active"}

        provider = self.providers[connection_name]
        results = {}

        # Sync students
        if connection.can_read_students:
            students = provider.get_students(limit=5000)
            results["students"] = len(students)
            self.data_cache["students"][connection_name] = students

        # Sync courses
        if connection.can_read_courses:
            courses = provider.get_courses(limit=5000)
            results["courses"] = len(courses)
            self.data_cache["courses"][connection_name] = courses

        # Sync instructors
        instructors = provider.get_instructors(limit=1000)
        results["instructors"] = len(instructors)
        self.data_cache["instructors"][connection_name] = instructors

        # Sync enrollments for term
        if term and connection.can_read_enrollments:
            enrollments = provider.get_enrollments({"term": term})
            results["enrollments"] = len(enrollments)
            self.data_cache["enrollments"][connection_name] = enrollments

        # Update last sync time
        connection.last_sync = datetime.now()

        # Record sync
        sync_record = {
            "timestamp": datetime.now(),
            "connection": connection_name,
            "term": term,
            "results": results,
        }
        self.sync_history.append(sync_record)

        return {"success": True, "results": results}

    def get_term_schedule(self, connection_name: str, term: str) -> List[CourseSection]:
        """Get schedule for a specific term."""
        provider = self.providers.get(connection_name)
        if not provider:
            return []

        return provider.get_term_schedule(term)

    def push_schedule_to_sis(
        self, connection_name: str, sections: List[CourseSection], term: str
    ) -> Dict[str, Any]:
        """Push generated schedule to SIS."""
        connection = self.connections.get(connection_name)
        if not connection or not connection.can_write_schedules:
            return {"success": False, "error": "SIS does not support writing schedules"}

        provider = self.providers[connection_name]
        results = provider.push_schedule(sections, term)

        return {
            "success": True,
            "pushed": sum(1 for success in results.values() if success),
            "failed": sum(1 for success in results.values() if not success),
            "details": results,
        }

    def get_student_schedule(
        self, connection_name: str, student_id: str, term: str
    ) -> List[Dict[str, Any]]:
        """Get a student's schedule from SIS."""
        provider = self.providers.get(connection_name)
        if not provider:
            return []

        enrollments = provider.get_student_enrollments(student_id, term)
        schedule = []

        for enrollment in enrollments:
            # Get section details
            sections = provider.get_course_sections(enrollment.course_code, term)
            for section in sections:
                if section.section_id == enrollment.section_id:
                    schedule.append(
                        {
                            "course_code": section.course_code,
                            "section": section.section_number,
                            "title": section.course_code,  # Would need course lookup
                            "instructor": section.instructor_name,
                            "days": section.meeting_days,
                            "time": f"{section.start_time} - {section.end_time}",
                            "location": section.location,
                            "credits": 3,  # Would need course lookup
                            "status": enrollment.status,
                        }
                    )

        return schedule

    def find_course_conflicts(
        self, connection_name: str, student_id: str, new_section: CourseSection
    ) -> List[Dict[str, Any]]:
        """Find conflicts for a student adding a new course."""
        current_schedule = self.get_student_schedule(connection_name, student_id, new_section.term)
        conflicts = []

        for existing in current_schedule:
            # Check time conflicts
            if self._sections_conflict(existing, new_section):
                conflicts.append(
                    {
                        "type": "time_conflict",
                        "existing_course": existing["course_code"],
                        "new_course": new_section.course_code,
                        "time": f"{existing['time']} overlaps with {new_section.start_time}-{new_section.end_time}",
                    }
                )

            # Check prerequisite conflicts
            # This would need more complex logic with prerequisite checking

        return conflicts

    def _create_provider(self, sis_type: str) -> Optional[SISProvider]:
        """Create a provider instance based on type."""
        if sis_type == "canvas":
            from .canvas import CanvasProvider

            return CanvasProvider()
        elif sis_type == "banner":
            from .banner import BannerProvider

            return BannerProvider()
        elif sis_type == "blackboard":
            from .blackboard import BlackboardProvider

            return BlackboardProvider()
        elif sis_type == "custom":
            from .custom import CustomProvider

            return CustomProvider()
        else:
            return None

    def _sections_conflict(self, existing: Dict[str, Any], new_section: CourseSection) -> bool:
        """Check if two sections have time conflicts."""
        if not existing["days"] or not new_section.meeting_days:
            return False

        # Check day overlap
        day_overlap = set(existing["days"]) & set(new_section.meeting_days)
        if not day_overlap:
            return False

        # Parse times and check overlap
        # This is simplified - would need proper time parsing
        return True

    def export_to_edusched(self, connection_name: str, term: str) -> Dict[str, Any]:
        """Export SIS data in EduSched format."""
        provider = self.providers.get(connection_name)
        if not provider:
            return {"success": False, "error": "Provider not found"}

        # Get all data
        students = provider.get_students({"term": term})
        courses = provider.get_courses({"term": term})
        sections = provider.get_term_schedule(term)
        provider.get_instructors()
        enrollments = provider.get_enrollments({"term": term})

        # Convert to EduSched format
        edu_requests = []

        # Convert sections to requests
        for section in sections:
            # Find matching course
            course = next((c for c in courses if c.course_code == section.course_code), None)
            if not course:
                continue

            # Create request
            request = {
                "id": section.section_id,
                "course_code": section.course_code,
                "title": course.title,
                "duration": timedelta(hours=course.duration_hours),
                "number_of_occurrences": 1,  # Simplified
                "department_id": course.department,
                "instructor_id": section.instructor_id,
                "enrollment_count": section.current_enrollment,
                "min_capacity": course.min_enrollment,
                "max_capacity": course.max_enrollment,
                "required_resource_types": {"classroom": 1},
                "preferred_building_id": None,
                "requires_lab": course.requires_lab,
            }
            edu_requests.append(request)

        return {
            "success": True,
            "requests": edu_requests,
            "students": [
                {
                    "id": s.student_id,
                    "name": f"{s.first_name} {s.last_name}",
                    "email": s.email,
                    "enrollments": [
                        e.section_id for e in enrollments if e.student_id == s.student_id
                    ],
                }
                for s in students
            ],
            "resources": [],  # Would need room mapping
            "constraints": [],  # Would need constraint mapping
            "metadata": {
                "sis_name": connection_name,
                "term": term,
                "export_time": datetime.now().isoformat(),
            },
        }
