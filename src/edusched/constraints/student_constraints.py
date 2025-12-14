"""Constraints for student registration, scheduling conflicts, and preferences."""

from typing import TYPE_CHECKING, Dict, List, Optional

from edusched.constraints.base import Constraint, ConstraintContext, Violation

if TYPE_CHECKING:
    from edusched.domain.assignment import Assignment
    from edusched.domain.curriculum import Curriculum
    from edusched.domain.student_preferences import StudentPreferences


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
            if hasattr(existing, "student_ids") and self.student_id in existing.student_ids:
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
                ),
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
                ),
            )

        # Check accessibility requirements
        accessibility_needs = self._get_accessibility_requirements()
        if accessibility_needs:
            if not room.meets_accessibility_requirements(accessibility_needs):
                missing_features = [
                    feat
                    for feat, req in accessibility_needs.items()
                    if req and not getattr(room, feat, False)
                ]
                return Violation(
                    constraint_type=self.constraint_type,
                    affected_request_id=assignment.request_id,
                    message=(f"Room lacks accessibility features: {', '.join(missing_features)}"),
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
                    ),
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


class StudentTimePreferenceConstraint(Constraint):
    """Ensures student time slot preferences are respected."""

    def __init__(
        self,
        student_preferences: "List[StudentPreferences]",
        weight: float = 100.0,
        violation_penalty: float = 200.0,
    ):
        """Initialize time preference constraint.

        Args:
            student_preferences: List of student preference objects
            weight: Importance weight for this constraint
            violation_penalty: Penalty for violations
        """
        super().__init__("student_time_preference", violation_penalty)
        self.student_preferences = {sp.student_id: sp for sp in student_preferences}
        # Import here to avoid circular dependency
        from edusched.domain.student_preferences import PreferenceScorer

        self.scorer = PreferenceScorer()
        self.weight = weight

    def check(
        self,
        assignment: "Assignment",
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if assignment respects student time preferences."""
        # Get student IDs for this assignment
        student_ids = getattr(assignment.request, "student_ids", [])
        if not student_ids:
            return None

        day = assignment.start_time.strftime("%A").lower()
        start_time = assignment.start_time.time()

        # Check each student's preference
        violated_students = []
        for student_id in student_ids:
            if student_id in self.student_preferences:
                preferences = self.student_preferences[student_id]
                score = self.scorer.calculate_time_score(preferences, day, start_time)

                # If score is very low, consider it a violation
                if score < 0.2:  # Very low preference match
                    violated_students.append(student_id)

        if violated_students:
            return Violation(
                constraint=self,
                assignment=assignment,
                message=(f"Time preference violation for students: {', '.join(violated_students)}"),
                details={
                    "violated_students": violated_students,
                    "day": day,
                    "time": str(start_time),
                    "preference_scores": [
                        self.scorer.calculate_time_score(
                            self.student_preferences[sid], day, start_time
                        )
                        for sid in violated_students
                        if sid in self.student_preferences
                    ],
                },
            )

        return None


class CohortSchedulingConstraint(Constraint):
    """Ensures cohort scheduling requirements are met."""

    def __init__(
        self,
        student_preferences: "List[StudentPreferences]",
        violation_penalty: float = 500.0,
    ):
        """Initialize cohort scheduling constraint.

        Args:
            student_preferences: List of student preference objects
            violation_penalty: Penalty for violations
        """
        super().__init__("cohort_scheduling", violation_penalty)
        self.student_preferences = {sp.student_id: sp for sp in student_preferences}

    def check(
        self,
        assignment: "Assignment",
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if assignment meets cohort requirements."""
        request = context.request_lookup.get(assignment.request_id)
        if not request:
            return None

        # Check each student's cohort requirements
        for student_id in getattr(request, "student_ids", []):
            if student_id in self.student_preferences:
                preferences = self.student_preferences[student_id]
                for cohort in preferences.cohort_requirements:
                    if request.id in cohort.courses:
                        # Check if other courses in this cohort are scheduled
                        violations = self._check_cohort_scheduling(
                            cohort,
                            request.id,
                            assignment,
                            context.current_assignments,
                        )
                        if violations:
                            return Violation(
                                constraint=self,
                                assignment=assignment,
                                message=f"Cohort scheduling violation: {', '.join(violations)}",
                                details={
                                    "cohort_id": cohort.cohort_id,
                                    "course_id": request.id,
                                    "violations": violations,
                                    "student_id": student_id,
                                },
                            )

        return None

    def _check_cohort_scheduling(
        self,
        cohort,
        course_id: str,
        assignment: "Assignment",
        existing_assignments,
    ) -> List[str]:
        """Check if cohort requirements are satisfied."""
        violations = []

        # Find assignments for other courses in this cohort
        cohort_assignments = []
        for existing in existing_assignments:
            existing_request = existing.request
            if existing_request and existing_request.id in cohort.courses:
                cohort_assignments.append(existing)

        # Check same day requirement
        if cohort.same_day:
            this_day = assignment.start_time.date()
            for other in cohort_assignments:
                other_day = other.start_time.date()
                if this_day != other_day:
                    violations.append(f"{course_id} and {other.request.id} not on same day")

        # Check same time requirement
        if cohort.same_time:
            this_time = assignment.start_time.time()
            for other in cohort_assignments:
                other_time = other.start_time.time()
                if this_time != other_time:
                    violations.append(f"{course_id} and {other.request.id} not at same time")

        # Check consecutive requirement
        if cohort.consecutive:
            # Sort assignments by start time
            all_assignments = [assignment] + cohort_assignments
            all_assignments.sort(key=lambda a: a.start_time)

            for i in range(len(all_assignments) - 1):
                gap = (
                    all_assignments[i + 1].start_time - all_assignments[i].end_time
                ).total_seconds() / 60

                if gap > cohort.min_gap_minutes:
                    violations.append(
                        f"Gap of {gap} minutes between courses exceeds minimum {cohort.min_gap_minutes}"
                    )

        return violations


class WalkingDistanceConstraint(Constraint):
    """Minimizes walking distance between consecutive classes."""

    def __init__(
        self,
        student_preferences: "List[StudentPreferences]",
        violation_penalty: float = 100.0,
    ):
        """Initialize walking distance constraint.

        Args:
            student_preferences: List of student preference objects
            violation_penalty: Penalty for violations
        """
        super().__init__("walking_distance", violation_penalty)
        self.student_preferences = {sp.student_id: sp for sp in student_preferences}
        # Import here to avoid circular dependency
        from edusched.domain.student_preferences import PreferenceScorer

        self.scorer = PreferenceScorer()

    def check(
        self,
        assignment: "Assignment",
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if walking distance between classes is acceptable."""
        request = context.request_lookup.get(assignment.request_id)
        if not request:
            return None

        student_ids = getattr(request, "student_ids", [])
        if not student_ids:
            return None

        # Get building ID for this assignment
        building_id = getattr(assignment.resource, "building_id", None)
        if not building_id:
            return None

        # Check each student's previous/next class
        for student_id in student_ids:
            if student_id in self.student_preferences:
                preferences = self.student_preferences[student_id]

                # Find student's other assignments on the same day
                other_assignments = self._find_student_assignments_same_day(
                    student_id,
                    assignment,
                    context.current_assignments,
                )

                for other in other_assignments:
                    other_building_id = getattr(other.resource, "building_id", None)
                    if other_building_id:
                        # Calculate walking distance (would use actual distance calculation)
                        distance = self._calculate_walking_distance(building_id, other_building_id)
                        score = self.scorer.calculate_walking_distance_score(preferences, distance)

                        # If score is too low, it's a violation
                        if score < 0.3:  # 30% satisfaction threshold
                            return Violation(
                                constraint=self,
                                assignment=assignment,
                                message=(
                                    f"Walking distance too large for student {student_id}: "
                                    f"{distance:.0f}m between {building_id} and {other_building_id}"
                                ),
                                details={
                                    "student_id": student_id,
                                    "from_building": building_id,
                                    "to_building": other_building_id,
                                    "distance": distance,
                                    "max_allowed": preferences.walking_distance.max_distance_meters,
                                },
                            )

        return None

    def _find_student_assignments_same_day(
        self,
        student_id: str,
        assignment: "Assignment",
        all_assignments: List["Assignment"],
    ) -> List["Assignment"]:
        """Find student's other assignments on the same day."""
        same_day_assignments = []
        assignment_day = assignment.start_time.date()

        for existing in all_assignments:
            if existing.start_time.date() == assignment_day:
                existing_request = existing.request
                if existing_request and student_id in getattr(existing_request, "student_ids", []):
                    same_day_assignments.append(existing)

        return same_day_assignments

    def _calculate_walking_distance(self, building1_id: str, building2_id: str) -> float:
        """Calculate walking distance between two buildings."""
        # In production, this would use actual campus map data
        # For now, simulate with a simple distance matrix
        distance_map = {
            ("A", "B"): 150.0,
            ("B", "A"): 150.0,
            ("A", "C"): 300.0,
            ("C", "A"): 300.0,
            ("B", "C"): 200.0,
            ("C", "B"): 200.0,
        }

        return distance_map.get((building1_id, building2_id), 100.0)
