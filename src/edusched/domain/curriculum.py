"""Curriculum domain model for programs, courses, and requirements."""

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Set, Tuple, Union
from enum import Enum

from edusched.errors import ValidationError


class RequirementType(Enum):
    """Types of academic requirements."""
    CREDIT = "credit"                    # Total credits needed
    COURSE = "course"                   # Specific course required
    ELECTIVE = "elective"               # Choice from list
    PREREQUISITE = "prerequisite"      # Must complete before
    COREQUISITE = "corequisite"        # Must take simultaneously
    GPA = "gpa"                        # Minimum GPA requirement
    CONCENTRATION = "concentration"     # Specific track/concentration


class CourseType(Enum):
    """Types of courses."""
    LECTURE = "lecture"
    LAB = "lab"
    SEMINAR = "seminar"
    STUDIO = "studio"
    CLINICAL = "clinical"
    RESEARCH = "research"
    THESIS = "thesis"
    DISSERTATION = "dissertation"
    INTERNSHIP = "internship"
    ONLINE = "online"
    HYBRID = "hybrid"


@dataclass
class CourseInfo:
    """Detailed course information for curriculum."""
    id: str
    title: str
    code: str  # e.g., CS401, MATH301
    department_id: str
    credits: float
    course_type: CourseType
    level: int  # 100-400 for undergrad, 500+ for grad

    # Prerequisites and corequisites
    prerequisites: List[str] = field(default_factory=list)
    corequisites: List[str] = field(default_factory=list)

    # Offerings information
    semesters_offered: List[str] = field(default_factory=list)  # ["fall", "spring"]
    years_offered: List[int] = field(default_factory=list)
    min_enrollment: int = 5
    max_enrollment: int = 100

    # Special requirements
    requires_lab: bool = False
    requires_computer: bool = False
    requires_special_equipment: List[str] = field(default_factory=list)
    has_final_exam: bool = True

    # Academic info
    writing_intensive: bool = False
    quantitative: bool = False
    diversity: bool = False
    cross_listed: List[str] = field(default_factory=list)  # Other department codes

    # Frequency and scheduling
    typically_offered: str = "annually"  # annually, biennially, occasional
    restricted_to_majors: List[str] = field(default_factory=list)
    open_to_majors: List[str] = field(default_factory=list)  # Empty means all

    def validate(self) -> List[ValidationError]:
        """Validate course information."""
        errors: List[ValidationError] = []

        if not self.id:
            errors.append(ValidationError(
                field="id",
                expected_format="non-empty string",
                actual_value=self.id
            ))

        if not self.title:
            errors.append(ValidationError(
                field="title",
                expected_format="non-empty string",
                actual_value=self.title
            ))

        if not self.code:
            errors.append(ValidationError(
                field="code",
                expected_format="course code (e.g., CS401)",
                actual_value=self.code
            ))

        if self.credits <= 0:
            errors.append(ValidationError(
                field="credits",
                expected_format="positive number",
                actual_value=self.credits
            ))

        return errors


@dataclass
class AcademicRequirement:
    """Represents an academic requirement for graduation."""
    id: str
    name: str
    requirement_type: RequirementType
    description: str

    # Requirement details (varies by type)
    credits_needed: Optional[float] = None  # For CREDIT type
    courses_needed: List[str] = field(default_factory=list)  # For COURSE type
    elective_options: List[str] = field(default_factory=list)  # For ELECTIVE type
    elective_count: int = 0  # Number of electives to choose
    minimum_gpa: Optional[float] = None  # For GPA type
    concentration_id: Optional[str] = None  # For CONCENTRATION type

    # Additional constraints
    minimum_grade: str = "D"  # Minimum grade for requirement satisfaction
    can_fulfill_with_transfer: bool = True
    can_fulfill_with_ap_ib: bool = True
    expire_date: Optional[date] = None  # Requirements that expire

    def is_satisfied_by(self, student_record: Dict) -> Tuple[bool, str]:
        """Check if requirement is satisfied by student record."""
        # This would integrate with the student's academic record
        # Implementation depends on record format
        return False, "Not implemented"


@dataclass
class Concentration:
    """A concentration or track within a major."""
    id: str
    name: str
    major_id: str
    description: str

    # Requirements specific to concentration
    required_courses: List[str] = field(default_factory=list)
    elective_courses: List[str] = field(default_factory=list)
    elective_count: int = 2  # Number of electives to choose

    # Faculty and resources
    faculty_advisors: List[str] = field(default_factory=list)
    dedicated_resources: List[str] = field(default_factory=list)

    # Special features
    has_thesis_option: bool = False
    has_internship_requirement: bool = False
    requires_portfolio: bool = False


@dataclass
class Major:
    """Academic major/degree program."""
    id: str
    name: str
    department_id: str
    degree_type: str  # BA, BS, MS, PhD, etc.

    # Credit requirements
    total_credits_required: float
    major_credits_required: float
    elective_credits_required: float

    # Grade requirements
    minimum_major_gpa: float = 2.0
    minimum_cumulative_gpa: float = 2.0

    # Curriculum structure
    required_courses: List[str] = field(default_factory=list)
    requirements: List[AcademicRequirement] = field(default_factory=list)
    concentrations: List[Concentration] = field(default_factory=list)

    # Program features
    has_thesis: bool = False
    has_comprehensive_exam: bool = False
    has_internship: bool = False
    has_study_abroad: bool = False

    # Time limits
    maximum_years_to_complete: int = 6
    minimum_gpa_for_good_standing: float = 2.0

    def validate(self) -> List[ValidationError]:
        """Validate major information."""
        errors: List[ValidationError] = []

        if not self.id:
            errors.append(ValidationError(
                field="id",
                expected_format="non-empty string",
                actual_value=self.id
            ))

        if self.major_credits_required > self.total_credits_required:
            errors.append(ValidationError(
                field="credits",
                expected_format="major_credits <= total_credits",
                actual_value=f"{self.major_credits_required} > {self.total_credits_required}"
            ))

        return errors

    def get_concentration(self, concentration_id: str) -> Optional[Concentration]:
        """Get concentration by ID."""
        for concentration in self.concentrations:
            if concentration.id == concentration_id:
                return concentration
        return None


@dataclass
class Curriculum:
    """Complete curriculum catalog for an institution."""
    institution_id: str
    academic_year: int

    # Catalog data
    courses: Dict[str, CourseInfo] = field(default_factory=dict)
    majors: Dict[str, Major] = field(default_factory=dict)
    minors: Dict[str, Major] = field(default_factory=dict)  # Minors can use Major structure
    certificates: Dict[str, Major] = field(default_factory=dict)  # Certificates too

    # Prerequisite graph (for quick lookups)
    prerequisite_graph: Dict[str, List[str]] = field(default_factory=dict)

    def add_course(self, course: CourseInfo) -> None:
        """Add a course to the curriculum."""
        self.courses[course.id] = course
        self.prerequisite_graph[course.id] = course.prerequisites

    def add_major(self, major: Major) -> None:
        """Add a major to the curriculum."""
        self.majors[major.id] = major

    def get_course(self, course_id: str) -> Optional[CourseInfo]:
        """Get course by ID."""
        return self.courses.get(course_id)

    def get_major(self, major_id: str) -> Optional[Major]:
        """Get major by ID."""
        return self.majors.get(major_id)

    def check_prerequisites(self, student_id: str, course_id: str,
                           completed_courses: Set[str]) -> Tuple[bool, List[str]]:
        """Check if student meets prerequisites for a course."""
        course = self.get_course(course_id)
        if not course:
            return False, ["Course not found"]

        missing_prereqs = []
        for prereq in course.prerequisites:
            if prereq not in completed_courses:
                missing_prereqs.append(prereq)

        return len(missing_prereqs) == 0, missing_prereqs

    def get_course_sequence(self, course_id: str) -> List[str]:
        """Get complete prerequisite chain for a course."""
        sequence = []
        visited = set()

        def dfs(course: str):
            if course in visited or course not in self.prerequisite_graph:
                return
            visited.add(course)
            for prereq in self.prerequisite_graph[course]:
                dfs(prereq)
            sequence.append(course)

        dfs(course_id)
        return sequence

    def validate_student_progress(self, student_id: str, major_id: str,
                               completed_courses: Dict[str, str],
                               current_gpa: float) -> Dict:
        """Validate student's progress toward major requirements."""
        major = self.get_major(major_id)
        if not major:
            return {"error": "Major not found"}

        report = {
            "major": major.name,
            "gpa": current_gpa,
            "gpa_status": "passing" if current_gpa >= major.minimum_cumulative_gpa else "failing",
            "completed_courses": len(completed_courses),
            "requirements": []
        }

        # Check each requirement
        for requirement in major.requirements:
            status = requirement.is_satisfied_by({
                "completed_courses": completed_courses,
                "gpa": current_gpa
            })
            report["requirements"].append({
                "requirement": requirement.name,
                "satisfied": status[0],
                "details": status[1]
            })

        return report

    def get_available_courses(self, student_id: str,
                             completed_courses: Set[str],
                             major_id: Optional[str] = None,
                             semester: str = "fall") -> List[CourseInfo]:
        """Get courses student can register for based on prerequisites."""
        available = []

        for course in self.courses.values():
            # Skip if already completed
            if course.id in completed_courses:
                continue

            # Check semester offered
            if semester not in course.semesers_offered:
                continue

            # Check prerequisites
            prereq_met, _ = self.check_prerequisites(student_id, course.id, completed_courses)
            if not prereq_met:
                continue

            # Check major restrictions if specified
            if major_id and course.restricted_to_majors:
                if major_id not in course.restricted_to_majors:
                    continue

            available.append(course)

        return available