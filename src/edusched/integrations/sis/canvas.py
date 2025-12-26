"""Canvas LMS integration for EduSched SIS framework.

Implements Canvas API integration for course, student, and enrollment data.
"""

from datetime import datetime
import logging
from typing import Any, Dict, List, Optional

from .base import Course, CourseSection, Enrollment, Instructor, SISProvider, Student

logger = logging.getLogger(__name__)


class CanvasProvider(SISProvider):
    """Canvas LMS provider implementation."""

    def __init__(self):
        self.base_url = None
        self.access_token = None
        self.headers = None

    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Authenticate with Canvas API."""
        try:
            # Check for required libraries
            try:
                import requests
            except ImportError:
                logger.error("requests library required for Canvas integration")
                return False

            self.base_url = credentials.get("base_url")
            self.access_token = credentials.get("access_token")

            if not self.base_url or not self.access_token:
                return False

            # Set up headers
            self.headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }

            # Test authentication
            test_url = f"{self.base_url}/api/v1/users/self"
            response = requests.get(test_url, headers=self.headers)

            return response.status_code == 200

        except Exception:
            logger.exception("Canvas authentication error")
            return False

    def test_connection(self) -> bool:
        """Test the connection to Canvas."""
        try:
            import requests

            url = f"{self.base_url}/api/v1/accounts/self"
            response = requests.get(url, headers=self.headers)
            return response.status_code == 200

        except Exception:
            logger.exception("Canvas connection test failed")
            return False

    def _make_request(
        self, endpoint: str, method: str = "GET", data: Dict = None
    ) -> Optional[Dict]:
        """Make a request to Canvas API."""
        try:
            import requests

            url = f"{self.base_url}/api/v1/{endpoint}"

            if method == "GET":
                response = requests.get(url, headers=self.headers)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method == "PUT":
                response = requests.put(url, headers=self.headers, json=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers)
            else:
                return None

            if response.status_code < 400:
                return response.json()
            else:
                logger.error(
                    "Canvas API error: %s - %s",
                    response.status_code,
                    response.text,
                )
                return None

        except Exception:
            logger.exception("Canvas API request error")
            return None

    def get_students(self, filters: Dict[str, Any] = None, limit: int = 1000) -> List[Student]:
        """Get students from Canvas."""
        students = []
        filters = filters or {}
        account_id = filters.get("account_id", "1")

        # Get enrollments with student role
        endpoint = f"accounts/{account_id}/enrollments?type[]=StudentEnrollment"
        if "term_id" in filters:
            endpoint += f"&enrollment_term_id={filters['term_id']}"

        response = self._make_request(endpoint)

        if response and "enrollments" in response:
            for enrollment in response["enrollments"]:
                user = enrollment.get("user", {})
                course = enrollment.get("course", {})

                student = Student(
                    student_id=str(user.get("id", "")),
                    first_name=user.get("name", "").split()[0],
                    last_name=" ".join(user.get("name", "").split()[1:]),
                    email=user.get("email", ""),
                    student_type=self._determine_student_type(enrollment),
                    program=course.get("name", ""),
                    department="",
                    year=1,
                    status="active"
                    if enrollment.get("enrollment_state") == "active"
                    else "inactive",
                    enrollment_date=self._parse_date(enrollment.get("created_at")),
                    sis_id=str(user.get("sis_user_id", "")),
                )

                students.append(student)

        return students[:limit]

    def get_student(self, student_id: str) -> Optional[Student]:
        """Get a specific student from Canvas."""
        endpoint = f"users/{student_id}"
        response = self._make_request(endpoint)

        if response:
            user = response
            return Student(
                student_id=str(user.get("id", "")),
                first_name=user.get("name", "").split()[0],
                last_name=" ".join(user.get("name", "").split()[1:]),
                email=user.get("email", ""),
                sis_id=str(user.get("sis_user_id", "")),
            )

        return None

    def get_student_enrollments(
        self, student_id: str, term: Optional[str] = None
    ) -> List[Enrollment]:
        """Get student enrollments from Canvas."""
        enrollments = []
        endpoint = f"users/{student_id}/enrollments"

        response = self._make_request(endpoint)

        if response:
            for enrollment_data in response:
                enrollment = Enrollment(
                    enrollment_id=str(enrollment_data.get("id", "")),
                    student_id=student_id,
                    section_id=str(enrollment_data.get("course_section_id", "")),
                    term=term or "unknown",
                    status=enrollment_data.get("enrollment_state", "unknown"),
                    enrollment_date=self._parse_date(enrollment_data.get("created_at")),
                    sis_id=str(enrollment_data.get("sis_user_id", "")),
                )
                enrollments.append(enrollment)

        return enrollments

    def get_courses(self, filters: Dict[str, Any] = None, limit: int = 1000) -> List[Course]:
        """Get courses from Canvas."""
        courses = []
        filters = filters or {}
        account_id = filters.get("account_id", "1")

        endpoint = f"accounts/{account_id}/courses"
        if "term_id" in filters:
            endpoint += f"?enrollment_term_id={filters['term_id']}"

        response = self._make_request(endpoint)

        if response:
            for course_data in response:
                course = Course(
                    course_code=course_data.get("course_code", ""),
                    title=course_data.get("name", ""),
                    description=course_data.get("public_description", ""),
                    credits=self._extract_credits(course_data),
                    department=self._extract_department(course_data),
                    level="undergraduate",  # Canvas doesn't specify level clearly
                    prerequisites=[],
                    max_enrollment=course_data.get("course_section", {}).get("max_enrollment", 30),
                    duration_hours=3.0,  # Default, would need configuration
                    room_type="classroom",
                    sis_id=str(course_data.get("sis_course_id", "")),
                )
                courses.append(course)

        return courses[:limit]

    def get_course(self, course_code: str) -> Optional[Course]:
        """Get a specific course from Canvas."""
        # Search by course code
        endpoint = f"courses?search_term={course_code}"
        response = self._make_request(endpoint)

        if response:
            for course_data in response:
                if course_data.get("course_code") == course_code:
                    return Course(
                        course_code=course_data.get("course_code", ""),
                        title=course_data.get("name", ""),
                        description=course_data.get("public_description", ""),
                        credits=self._extract_credits(course_data),
                        department=self._extract_department(course_data),
                        sis_id=str(course_data.get("sis_course_id", "")),
                    )

        return None

    def get_course_sections(
        self, course_code: str, term: Optional[str] = None
    ) -> List[CourseSection]:
        """Get course sections from Canvas."""
        sections = []

        # First find the course
        course = self.get_course(course_code)
        if not course:
            return sections

        # Get sections for the course
        endpoint = f"courses/{course.sis_id or course_code}/sections"
        response = self._make_request(endpoint)

        if response:
            for section_data in response:
                section = CourseSection(
                    section_id=str(section_data.get("id", "")),
                    course_code=course_code,
                    term=term or "unknown",
                    section_number=section_data.get("name", "").split()[-1],
                    instructor_id=None,  # Would need separate lookup
                    instructor_name="",
                    schedule_type="lecture",
                    current_enrollment=section_data.get("students_count", 0),
                    max_enrollment=section_data.get("max_enrollment", 30),
                    status="active"
                    if section_data.get("restrict_enrollments_to_section_dates")
                    else "active",
                    location="",
                    start_date=self._parse_date(section_data.get("start_at")),
                    end_date=self._parse_date(section_data.get("end_at")),
                    sis_id=str(section_data.get("sis_section_id", "")),
                )
                sections.append(section)

        return sections

    def get_instructors(
        self, filters: Dict[str, Any] = None, limit: int = 1000
    ) -> List[Instructor]:
        """Get instructors from Canvas."""
        instructors = []
        filters = filters or {}
        account_id = filters.get("account_id", "1")

        # Get all enrollments with teacher/TA roles
        endpoint = f"accounts/{account_id}/enrollments?type[]=TeacherEnrollment&type[]=TaEnrollment"
        response = self._make_request(endpoint)

        processed_users = set()

        if response and "enrollments" in response:
            for enrollment in response["enrollments"]:
                user = enrollment.get("user", {})
                user_id = str(user.get("id", ""))

                if user_id not in processed_users:
                    instructor = Instructor(
                        instructor_id=user_id,
                        first_name=user.get("name", "").split()[0],
                        last_name=" ".join(user.get("name", "").split()[1:]),
                        email=user.get("email", ""),
                        title="Instructor",
                        department="",
                        rank="Teacher" if enrollment.get("type") == "TeacherEnrollment" else "TA",
                        status="active",
                        max_courses_per_term=5,
                        sis_id=str(user.get("sis_user_id", "")),
                    )
                    instructors.append(instructor)
                    processed_users.add(user_id)

        return instructors[:limit]

    def get_instructor(self, instructor_id: str) -> Optional[Instructor]:
        """Get a specific instructor from Canvas."""
        endpoint = f"users/{instructor_id}"
        response = self._make_request(endpoint)

        if response:
            user = response
            return Instructor(
                instructor_id=instructor_id,
                first_name=user.get("name", "").split()[0],
                last_name=" ".join(user.get("name", "").split()[1:]),
                email=user.get("email", ""),
                title="Instructor",
                sis_id=str(user.get("sis_user_id", "")),
            )

        return None

    def get_enrollments(
        self, filters: Dict[str, Any] = None, limit: int = 1000
    ) -> List[Enrollment]:
        """Get enrollments from Canvas."""
        enrollments = []
        filters = filters or {}

        # Build query
        endpoint = "enrollments"
        params = []
        if "course_id" in filters:
            params.append(f"course_id[]={filters['course_id']}")
        if "user_id" in filters:
            params.append(f"user_id[]={filters['user_id']}")
        if "type" in filters:
            params.append(f"type[]={filters['type']}")
        if "term_id" in filters:
            params.append(f"enrollment_term_id={filters['term_id']}")

        if params:
            endpoint += "?" + "&".join(params)

        response = self._make_request(endpoint)

        if response:
            for enrollment_data in response:
                enrollment = Enrollment(
                    enrollment_id=str(enrollment_data.get("id", "")),
                    student_id=str(enrollment_data.get("user_id", "")),
                    section_id=str(enrollment_data.get("course_section_id", "")),
                    term=str(enrollment_data.get("enrollment_term_id", "")),
                    status=enrollment_data.get("enrollment_state", "unknown"),
                    enrollment_date=self._parse_date(enrollment_data.get("created_at")),
                    sis_id=str(enrollment_data.get("sis_user_id", "")),
                )
                enrollments.append(enrollment)

        return enrollments[:limit]

    def update_enrollment(self, enrollment_id: str, updates: Dict[str, Any]) -> bool:
        """Update enrollment record."""
        endpoint = f"enrollments/{enrollment_id}"
        response = self._make_request(endpoint, "PUT", updates)
        return response is not None

    def get_term_schedule(self, term: str, filters: Dict[str, Any] = None) -> List[CourseSection]:
        """Get schedule for a term from Canvas."""
        # Get courses for the term
        courses = self.get_courses({"term_id": term})

        sections = []
        for course in courses:
            course_sections = self.get_course_sections(course.course_code, term)
            sections.extend(course_sections)

        return sections

    def push_schedule(self, sections: List[CourseSection], term: str) -> Dict[str, bool]:
        """Push schedule to Canvas."""
        results = {}

        for section in sections:
            # Canvas doesn't have a direct way to push schedules
            # Would need to update course section details
            results[section.section_id] = False

        return results

    def _determine_student_type(self, enrollment: Dict[str, Any]) -> str:
        """Determine student type from enrollment data."""
        # This is simplified - would need actual logic based on enrollment attributes
        return "undergraduate"

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse Canvas date string."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return None

    def _extract_credits(self, course_data: Dict[str, Any]) -> int:
        """Extract credits from Canvas course data."""
        # Canvas doesn't store credits directly
        # Would need to check custom fields or SIS integration
        return 3

    def _extract_department(self, course_data: Dict[str, Any]) -> str:
        """Extract department from Canvas course data."""
        # Check account/sub-account info for department
        account = course_data.get("account", {})
        return account.get("name", "")
