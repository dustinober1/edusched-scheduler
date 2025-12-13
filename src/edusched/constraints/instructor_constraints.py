"""Instructor-specific constraints for course assignment and teaching."""

from typing import TYPE_CHECKING, Optional, List
from datetime import datetime, timedelta

from edusched.constraints.base import Constraint, ConstraintContext, Violation

if TYPE_CHECKING:
    from edusched.domain.assignment import Assignment
    from edusched.domain.teacher import Teacher


class InstructorQualificationConstraint(Constraint):
    """Ensures instructor is qualified to teach assigned courses."""

    def __init__(self, instructor_id: str):
        """
        Initialize instructor qualification constraint.

        Args:
            instructor_id: The instructor ID this constraint applies to
        """
        self.instructor_id = instructor_id

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if instructor is qualified for the course."""
        # Get the instructor
        instructor = context.teacher_lookup.get(self.instructor_id)
        if not instructor:
            return None

        # Get the course code from request ID
        request = context.request_lookup.get(assignment.request_id)
        if not request:
            return None

        # Check if instructor is qualified
        can_teach, reason = instructor.can_teach_course(request.id)
        if not can_teach:
            return Violation(
                constraint_type=self.constraint_type,
                affected_request_id=assignment.request_id,
                message=f"Instructor {self.instructor_id} not qualified for {request.id}: {reason}"
            )

        return None

    def explain(self, violation: Violation) -> str:
        """Provide explanation for qualification violation."""
        return f"Instructor qualification requirement not met: {violation.message}"

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.instructor_qualification"


class ConcurrentTeachingConstraint(Constraint):
    """Prevents instructors from teaching conflicting courses simultaneously."""

    def __init__(self, instructor_id: str):
        """
        Initialize concurrent teaching constraint.

        Args:
            instructor_id: The instructor ID this constraint applies to
        """
        self.instructor_id = instructor_id

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check for concurrent teaching conflicts."""
        instructor = context.teacher_lookup.get(self.instructor_id)
        if not instructor:
            return None

        # Check if this assignment is for this instructor
        if not self._is_instructor_assigned(assignment, self.instructor_id):
            return None

        # Get all assignments for this instructor
        instructor_assignments = [
            a for a in solution if self._is_instructor_assigned(a, self.instructor_id)
        ]

        # Check for time overlaps
        for existing in instructor_assignments:
            if existing.request_id == assignment.request_id:
                continue  # Skip self

            if self._times_overlap(assignment, existing):
                # Get course IDs for conflict message
                existing_course = existing.request_id
                new_course = assignment.request_id

                # Check if courses can be taught concurrently
                other_courses = [e.request_id for e in instructor_assignments if e != assignment]
                if not instructor.can_teach_concurrently_with(new_course, other_courses):
                    return Violation(
                        constraint_type=self.constraint_type,
                        affected_request_id=assignment.request_id,
                        message=f"Instructor {self.instructor_id} scheduled to teach {existing_course} and {new_course} simultaneously"
                    )

        return None

    def _is_instructor_assigned(self, assignment: "Assignment", instructor_id: str) -> bool:
        """Check if instructor is assigned to this assignment."""
        # This would need proper assignment tracking
        # For now, check if instructor_id is in assigned_resources
        for resource_type, resource_ids in assignment.assigned_resources.items():
            if resource_type == "instructor" and instructor_id in resource_ids:
                return True
        return False

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
        """Provide explanation for concurrent teaching violation."""
        return f"Instructor cannot teach multiple courses simultaneously: {violation.message}"

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.concurrent_teaching"


class InstructorSetupBufferConstraint(Constraint):
    """Ensures instructors have adequate setup/break time between classes."""

    def __init__(self, instructor_id: str):
        """
        Initialize instructor setup buffer constraint.

        Args:
            instructor_id: The instructor ID this constraint applies to
        """
        self.instructor_id = instructor_id

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check for adequate setup and break time."""
        instructor = context.teacher_lookup.get(self.instructor_id)
        if not instructor:
            return None

        request = context.request_lookup.get(assignment.request_id)
        if not request:
            return None

        # Get course-specific requirements
        setup_time = instructor.get_course_setup_time(request.id)
        cleanup_time = instructor.get_course_cleanup_time(request.id)

        # Get all assignments for this instructor on the same day
        instructor_assignments = [
            a for a in solution
            if self._is_instructor_assigned(a, self.instructor_id) and
            a.start_time.date() == assignment.start_time.date()
        ]

        # Check buffer requirements with other assignments
        for existing in instructor_assignments:
            if existing.request_id == assignment.request_id:
                continue

            # Calculate time gap considering setup/cleanup
            if assignment.start_time > existing.end_time:
                # New assignment is after existing
                gap = (assignment.start_time - existing.end_time).total_seconds() / 60
                required_gap = instructor.get_course_cleanup_time(existing.request_id) + setup_time

                if gap < required_gap:
                    return Violation(
                        constraint_type=self.constraint_type,
                        affected_request_id=assignment.request_id,
                        message=f"Insufficient buffer between {existing.request_id} and {assignment.request_id}: "
                               f"need {required_gap} minutes, have {gap:.0f} minutes"
                    )

            elif assignment.end_time < existing.start_time:
                # New assignment is before existing
                gap = (existing.start_time - assignment.end_time).total_seconds() / 60
                required_gap = cleanup_time + instructor.get_course_setup_time(existing.request_id)

                if gap < required_gap:
                    return Violation(
                        constraint_type=self.constraint_type,
                        affected_request_id=assignment.request_id,
                        message=f"Insufficient buffer between {assignment.request_id} and {existing.request_id}: "
                               f"need {required_gap} minutes, have {gap:.0f} minutes"
                    )

        return None

    def _is_instructor_assigned(self, assignment: "Assignment", instructor_id: str) -> bool:
        """Check if instructor is assigned to this assignment."""
        for resource_type, resource_ids in assignment.assigned_resources.items():
            if resource_type == "instructor" and instructor_id in resource_ids:
                return True
        return False

    def explain(self, violation: Violation) -> str:
        """Provide explanation for setup buffer violation."""
        return f"Instructor setup/break time requirement not met: {violation.message}"

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.instructor_setup_buffer"


class CourseConflictConstraint(Constraint):
    """Prevents conflicting courses from running in the same term."""

    def __init__(self, instructor_id: str):
        """
        Initialize course conflict constraint.

        Args:
            instructor_id: The instructor ID this constraint applies to
        """
        self.instructor_id = instructor_id

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check for course conflicts."""
        instructor = context.teacher_lookup.get(self.instructor_id)
        if not instructor:
            return None

        # Get all course IDs instructor is teaching
        teaching_courses = [
            a.request_id for a in solution
            if self._is_instructor_assigned(a, self.instructor_id)
        ]

        # Check for conflicts with new assignment
        conflicts = instructor.courses_conflict_with(assignment.request_id)
        for conflict_course in conflicts:
            if conflict_course in teaching_courses:
                return Violation(
                    constraint_type=self.constraint_type,
                    affected_request_id=assignment.request_id,
                    message=f"Course {assignment.request_id} conflicts with {conflict_course} for instructor {self.instructor_id}"
                )

        return None

    def _is_instructor_assigned(self, assignment: "Assignment", instructor_id: str) -> bool:
        """Check if instructor is assigned to this assignment."""
        for resource_type, resource_ids in assignment.assigned_resources.items():
            if resource_type == "instructor" and instructor_id in resource_ids:
                return True
        return False

    def explain(self, violation: Violation) -> str:
        """Provide explanation for course conflict violation."""
        return f"Course conflict detected: {violation.message}"

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.course_conflict"