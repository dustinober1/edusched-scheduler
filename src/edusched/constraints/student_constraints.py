"""Constraints for student registration and scheduling conflicts."""

from typing import TYPE_CHECKING, Optional, Dict, List, Tuple
from datetime import datetime, timedelta

from edusched.constraints.base import Constraint, ConstraintContext, Violation

if TYPE_CHECKING:
    from edusched.domain.assignment import Assignment
    from edusched.domain.student import Student
    from edusched.domain.curriculum import Curriculum


class StudentConflictConstraint(Constraint):
    """Prevents students from being registered for conflicting courses."""

    def __init__(self, student_id: str):
        """
        Initialize student conflict constraint.

        Args:
            student_id: The student ID this constraint applies to
        """
        self.student_id = student_id

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if assignment conflicts with student's existing schedule."""
        # Get all assignments for this student
        student_assignments = []
        for existing in solution:
            # This would need to track student enrollment per assignment
            # For now, we'll check if the same student is in both
            if hasattr(existing, 'student_ids') and self.student_id in existing.student_ids:
                student_assignments.append(existing)

        # Check time conflicts
        for existing in student_assignments:
            if self._times_overlap(assignment, existing):
                return Violation(
                    constraint_type=self.constraint_type,
                    affected_request_id=assignment.request_id,
                    message=(
                        f"Student {self.student_id} has time conflict: "
                        f"{assignment.request_id} overlaps with {existing.request_id}"
                    )
                )

        return None

    def _times_overlap(self, assignment1: "Assignment", assignment2: "Assignment") -> bool:
        """Check if two assignments have overlapping times."""
        # Check same day first
        if assignment1.start_time.date() != assignment2.start_time.date():
            return False

        # Check time overlap
        return (
            assignment1.start_time < assignment2.end_time and
            assignment1.end_time > assignment2.start_time
        )

    def explain(self, violation: Violation) -> str:
        """Provide explanation for student conflict violation."""
        return f"Student {self.student_id} has a scheduling conflict: {violation.message}"

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.student_conflict"


class PrerequisiteConstraint(Constraint):
    """Ensures students have completed prerequisites for courses."""

    def __init__(self, student_id: str, curriculum: "Curriculum"):
        """
        Initialize prerequisite constraint.

        Args:
            student_id: The student ID to check
            curriculum: The curriculum containing prerequisite information
        """
        self.student_id = student_id
        self.curriculum = curriculum

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if student meets prerequisites for the course."""
        # Get the course information
        request = context.request_lookup.get(assignment.request_id)
        if not request:
            return None

        # Get course from curriculum
        course = self.curriculum.get_course(request.id)
        if not course or not course.prerequisites:
            return None  # No prerequisites to check

        # Get student's completed courses (this would come from student record)
        # For now, we'll simulate this check
        completed_courses = self._get_student_completed_courses()

        # Check prerequisites
        prereq_met, missing_prereqs = self.curriculum.check_prerequisites(
            self.student_id, course.id, completed_courses
        )

        if not prereq_met:
            return Violation(
                constraint_type=self.constraint_type,
                affected_request_id=assignment.request_id,
                message=(
                    f"Student {self.student_id} missing prerequisites: {', '.join(missing_prereqs)}"
                )
            )

        return None

    def explain(self, violation: Violation) -> str:
        """Provide explanation for prerequisite violation."""
        return f"Prerequisite requirement not met: {violation.message}"

    def _get_student_completed_courses(self) -> set:
        """
        Get set of completed courses for student.
        This would integrate with student information system.
        """
        # Simulated implementation
        # In production, fetch from student records
        return set()

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.prerequisite"


class StudentCapacityConstraint(Constraint):
    """Ensures room capacity meets enrollment and student accessibility needs."""

    def __init__(self, student_ids: List[str]):
        """
        Initialize student capacity constraint.

        Args:
            student_ids: List of student IDs registered for the course
        """
        self.student_ids = student_ids

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if room meets student needs."""
        request = context.request_lookup.get(assignment.request_id)
        if not request:
            return None

        # Get the assigned room
        room_id = None
        if "classroom" in assignment.assigned_resources:
            room_id = assignment.assigned_resources["classroom"][0]
        elif "lab" in assignment.assigned_resources:
            room_id = assignment.assigned_resources["lab"][0]

        if not room_id:
            return None

        room = context.resource_lookup.get(room_id)
        if not room:
            return None

        # Check capacity
        total_students = len(self.student_ids)
        if room.capacity and total_students > room.capacity:
            return Violation(
                constraint_type=self.constraint_type,
                affected_request_id=assignment.request_id,
                message=(
                    f"Room capacity ({room.capacity}) exceeded by enrollment ({total_students})"
                )
            )

        # Check accessibility requirements
        accessibility_needs = self._get_accessibility_requirements()
        if accessibility_needs:
            if not room.meets_accessibility_requirements(accessibility_needs):
                missing_features = [
                    feat for feat, req in accessibility_needs.items()
                    if req and not getattr(room, feat, False)
                ]
                return Violation(
                    constraint_type=self.constraint_type,
                    affected_request_id=assignment.request_id,
                    message=(
                        f"Room lacks accessibility features: {', '.join(missing_features)}"
                    )
                )

        return None

    def explain(self, violation: Violation) -> str:
        """Provide explanation for capacity violation."""
        return f"Room capacity or accessibility requirement not met: {violation.message}"

    def _get_accessibility_requirements(self) -> Dict[str, bool]:
        """
        Get accessibility requirements for enrolled students.
        This would aggregate needs from all registered students.
        """
        # In production, fetch from student records
        return {}

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.student_capacity"


class StudentSchedulePreferenceConstraint(Constraint):
    """Soft constraint to respect student scheduling preferences."""

    def __init__(self, student_ids: List[str], weight: float = 1.0):
        """
        Initialize student preference constraint.

        Args:
            student_ids: List of student IDs in the course
            weight: Weight for this preference (higher = more important)
        """
        self.student_ids = student_ids
        self.weight = weight

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """This is a soft constraint - used for scoring, not blocking."""
        # Would calculate preference satisfaction score here
        # Return None to allow scheduling
        return None

    def explain(self, violation: Violation) -> str:
        """Provide explanation for preference violation."""
        return f"Student scheduling preference not met: {violation.message}"

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "soft.student_preference"


class StudentCreditLoadConstraint(Constraint):
    """Ensures students don't exceed credit limits per semester."""

    def __init__(self, student_ids: List[str], max_credits: float = 18):
        """
        Initialize student credit load constraint.

        Args:
            student_ids: List of student IDs
            max_credits: Maximum credits allowed per semester
        """
        self.student_ids = student_ids
        self.max_credits = max_credits

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if adding this course would exceed student's credit limit."""
        request = context.request_lookup.get(assignment.request_id)
        if not request:
            return None

        # Get course credits (would fetch from curriculum)
        course_credits = self._get_course_credits(request.id)

        # Check each student's current credit load
        for student_id in self.student_ids:
            current_credits = self._get_student_current_credits(student_id)
            if current_credits + course_credits > self.max_credits:
                return Violation(
                    constraint_type=self.constraint_type,
                    affected_request_id=assignment.request_id,
                    message=(
                        f"Student {student_id} would exceed credit limit: "
                        f"{current_credits + course_credits} > {self.max_credits}"
                    )
                )

        return None

    def _get_course_credits(self, course_id: str) -> float:
        """Get credits for a course."""
        # Would fetch from curriculum database
        return 3.0  # Default assumption

    def explain(self, violation: Violation) -> str:
        """Provide explanation for credit load violation."""
        return f"Student credit limit exceeded: {violation.message}"

    def _get_course_credits(self, course_id: str) -> float:
        """Get credits for a course."""
        # Would fetch from curriculum database
        return 3.0  # Default assumption

    def _get_student_current_credits(self, student_id: str) -> float:
        """Get student's current credit load."""
        # Would fetch from student registration system
        return 12.0  # Simulated

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.student_credit_load"