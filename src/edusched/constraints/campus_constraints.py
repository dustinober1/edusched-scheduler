"""Campus-related constraints for multi-campus scheduling.

Ensures cross-campus considerations, transportation times,
campus-specific resources, and distance constraints.
"""

from dataclasses import dataclass
from datetime import time, timedelta
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from edusched.constraints.base import Constraint, ConstraintContext, Violation

if TYPE_CHECKING:
    from edusched.domain.assignment import Assignment
    from edusched.domain.campus import CampusManager


class CampusAvailabilityConstraint(Constraint):
    """Ensures sessions are scheduled within campus operating hours."""

    def __init__(
        self,
        campus_manager: "CampusManager",
        violation_penalty: float = 500.0,
    ):
        """
        Initialize campus availability constraint.

        Args:
            campus_manager: Campus management system
            violation_penalty: Penalty for operating hours violations
        """
        super().__init__("campus_availability", violation_penalty)
        self.campus_manager = campus_manager

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if session is within campus operating hours."""
        # Get session request
        request = context.request_lookup.get(assignment.request_id)
        if not request:
            return None

        # Get resource campus
        resource = context.resource_lookup.get(str(assignment.resource.id))
        if not resource or not hasattr(resource, "campus_id"):
            return None

        campus = self.campus_manager.campuses.get(resource.campus_id)
        if not campus:
            return None

        # Get session time
        session_start = assignment.start_time
        session_end = session_start + timedelta(minutes=float(request.duration))

        # Check campus operating hours
        if session_start.time() < campus.opening_time or session_end.time() > campus.closing_time:
            return Violation(
                constraint=self,
                assignment=assignment,
                message=(
                    f"Session scheduled outside campus {campus.name} operating hours: "
                    f"{campus.opening_time} - {campus.closing_time}"
                ),
                details={
                    "campus_id": campus.id,
                    "campus_name": campus.name,
                    "session_start": session_start.time().isoformat(),
                    "session_end": session_end.time().isoformat(),
                    "opening_time": campus.opening_time.isoformat(),
                    "closing_time": campus.closing_time.isoformat(),
                },
            )

        # Check building-specific hours if applicable
        if hasattr(resource, "building_id") and resource.building_id:
            building = self.campus_manager.buildings.get(resource.building_id)
            if building and building.opening_time and building.closing_time:
                if (
                    session_start.time() < building.opening_time
                    or session_end.time() > building.closing_time
                ):
                    return Violation(
                        constraint=self,
                        assignment=assignment,
                        message=(
                            f"Session scheduled outside building {building.name} operating hours: "
                            f"{building.opening_time} - {building.closing_time}"
                        ),
                        details={
                            "building_id": building.id,
                            "building_name": building.name,
                            "session_start": session_start.time().isoformat(),
                            "session_end": session_end.time().isoformat(),
                        },
                    )

        return None


class TransportationConstraint(Constraint):
    """Ensures sufficient time for transportation between campuses."""

    def __init__(
        self,
        campus_manager: "CampusManager",
        buffer_minutes: int = 15,
        violation_penalty: float = 800.0,
    ):
        """
        Initialize transportation constraint.

        Args:
            campus_manager: Campus management system
            buffer_minutes: Additional buffer time for transportation
            violation_penalty: Penalty for transportation violations
        """
        super().__init__("transportation", violation_penalty)
        self.campus_manager = campus_manager
        self.buffer_minutes = buffer_minutes

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if student/instructor has sufficient travel time between sessions."""
        # Get session request
        request = context.request_lookup.get(assignment.request_id)
        if not request:
            return None

        # Get current assignment campus
        resource = context.resource_lookup.get(str(assignment.resource.id))
        if not resource or not hasattr(resource, "campus_id"):
            return None

        current_campus_id = getattr(resource, "campus_id", None)
        if not current_campus_id:
            return None

        # Check against other assignments for same instructor/students
        conflicts = []

        for other_assignment in solution:
            if other_assignment.id == assignment.id:
                continue

            # Get other assignment campus
            other_resource = context.resource_lookup.get(str(other_assignment.resource.id))
            if not other_resource:
                continue

            other_campus_id = getattr(other_resource, "campus_id", None)
            if not other_campus_id or other_campus_id == current_campus_id:
                continue  # Same campus, no transportation needed

            # Check time overlap or insufficient gap
            other_request = context.request_lookup.get(other_assignment.request_id)
            if not other_request:
                continue

            # Calculate travel times
            travel_time_to = self.campus_manager.get_travel_time(other_campus_id, current_campus_id)
            travel_time_from = self.campus_manager.get_travel_time(
                current_campus_id, other_campus_id
            )

            current_end = assignment.start_time + timedelta(minutes=float(request.duration))
            other_end = other_assignment.start_time + timedelta(
                minutes=float(other_request.duration)
            )

            # Check if sessions are too close for transportation
            min_gap = max(travel_time_to, travel_time_from) + self.buffer_minutes

            # Case 1: Other session before current
            if other_assignment.start_time < assignment.start_time:
                gap = (assignment.start_time - other_end).total_seconds() / 60
                if gap < min_gap:
                    conflicts.append(
                        f"Insufficient time ({gap:.0f}m) between sessions at "
                        f"{other_campus_id} and {current_campus_id} (need {min_gap}m)"
                    )

            # Case 2: Other session after current
            elif other_assignment.start_time > assignment.start_time:
                gap = (other_assignment.start_time - current_end).total_seconds() / 60
                if gap < min_gap:
                    conflicts.append(
                        f"Insufficient time ({gap:.0f}m) between sessions at "
                        f"{current_campus_id} and {other_campus_id} (need {min_gap}m)"
                    )

        if conflicts:
            return Violation(
                constraint=self,
                assignment=assignment,
                message=f"Transportation scheduling conflicts: {'; '.join(conflicts)}",
                details={
                    "current_campus_id": current_campus_id,
                    "conflicts": conflicts,
                    "buffer_minutes": self.buffer_minutes,
                },
            )

        return None


class CampusResourceConstraint(Constraint):
    """Ensures resources are only used at their designated campuses."""

    def __init__(
        self,
        campus_manager: "CampusManager",
        violation_penalty: float = 1000.0,
    ):
        """
        Initialize campus resource constraint.

        Args:
            campus_manager: Campus management system
            violation_penalty: Penalty for campus resource violations
        """
        super().__init__("campus_resource", violation_penalty)
        self.campus_manager = campus_manager

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if resource is being used at its designated campus."""
        # Get session request
        request = context.request_lookup.get(assignment.request_id)
        if not request:
            return None

        # Check for campus-specific resources in requirements
        if hasattr(request, "required_campus_id") and request.required_campus_id:
            resource = context.resource_lookup.get(str(assignment.resource.id))
            if not resource:
                return None

            resource_campus = getattr(resource, "campus_id", None)
            if resource_campus != request.required_campus_id:
                return Violation(
                    constraint=self,
                    assignment=assignment,
                    message=(
                        f"Resource must be at campus {request.required_campus_id}, "
                        f"but is at campus {resource_campus}"
                    ),
                    details={
                        "required_campus_id": request.required_campus_id,
                        "resource_campus_id": resource_campus,
                        "resource_id": str(resource.id),
                    },
                )

        # Check for department campus allocations
        if hasattr(request, "department_id") and request.department_id:
            resource = context.resource_lookup.get(str(assignment.resource.id))
            if not resource:
                return None

            resource_campus = getattr(resource, "campus_id", None)
            if not resource_campus:
                return None

            # Get campus schedule for this campus
            campus_schedule = self.campus_manager.schedules.get(resource_campus)
            if campus_schedule:
                department_rooms = campus_schedule.department_room_allocations.get(
                    request.department_id, []
                )
                if department_rooms and str(resource.id) not in department_rooms:
                    return Violation(
                        constraint=self,
                        assignment=assignment,
                        message=(
                            f"Resource {resource.id} not allocated to department {request.department_id} "
                            f"at campus {resource_campus}"
                        ),
                        details={
                            "department_id": request.department_id,
                            "resource_id": str(resource.id),
                            "allocated_resources": department_rooms,
                            "campus_id": resource_campus,
                        },
                    )

        return None


class CrossCampusSchedulingConstraint(Constraint):
    """Manages constraints for courses spanning multiple campuses."""

    def __init__(
        self,
        campus_manager: "CampusManager",
        violation_penalty: float = 1200.0,
    ):
        """
        Initialize cross-campus scheduling constraint.

        Args:
            campus_manager: Campus management system
            violation_penalty: Penalty for cross-campus violations
        """
        super().__init__("cross_campus_scheduling", violation_penalty)
        self.campus_manager = campus_manager

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check cross-campus scheduling constraints."""
        # Get session request
        request = context.request_lookup.get(assignment.request_id)
        if not request:
            return None

        # Check if this is a cross-campus course
        cross_campus_courses = self.campus_manager.courses
        cross_course = None
        for course in cross_campus_courses.values():
            if course.course_id == getattr(request, "course_id", None):
                cross_course = course
                break

        if not cross_course:
            return None  # Not a cross-campus course

        # Get current assignment campus
        resource = context.resource_lookup.get(str(assignment.resource.id))
        if not resource:
            return None

        current_campus_id = getattr(resource, "campus_id", None)
        if not current_campus_id:
            return None

        # Validate cross-campus schedule
        session_start = assignment.start_time
        duration = timedelta(minutes=float(request.duration))

        issues = self.campus_manager.validate_cross_campus_schedule(
            cross_course,
            session_start,
            duration,
        )

        if issues:
            return Violation(
                constraint=self,
                assignment=assignment,
                message=(f"Cross-campus course scheduling violation: {'; '.join(issues)}"),
                details={
                    "course_id": cross_course.course_id,
                    "primary_campus": cross_course.primary_campus_id,
                    "current_campus": current_campus_id,
                    "issues": issues,
                },
            )

        return None


class CampusTimezoneConstraint(Constraint):
    """Ensures sessions respect timezone differences between campuses."""

    def __init__(
        self,
        campus_manager: "CampusManager",
        violation_penalty: float = 600.0,
    ):
        """
        Initialize campus timezone constraint.

        Args:
            campus_manager: Campus management system
            violation_penalty: Penalty for timezone violations
        """
        super().__init__("campus_timezone", violation_penalty)
        self.campus_manager = campus_manager

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if session respects timezone constraints."""
        # Get session request
        request = context.request_lookup.get(assignment.request_id)
        if not request:
            return None

        # Get resource campus
        resource = context.resource_lookup.get(str(assignment.resource.id))
        if not resource:
            return None

        campus_id = getattr(resource, "campus_id", None)
        if not campus_id:
            return None

        campus = self.campus_manager.campuses.get(campus_id)
        if not campus:
            return None

        # Check if session time is appropriate for campus timezone
        session_time_local = assignment.start_time.astimezone(assignment.start_time.tzinfo)

        # Early morning/late evening checks for campus local time
        if session_time_local.hour < 6 or session_time_local.hour > 22:
            return Violation(
                constraint=self,
                assignment=assignment,
                message=(
                    f"Session scheduled at inappropriate local time for campus {campus.name}: "
                    f"{session_time_local.hour:02d}:{session_time_local.minute:02d}"
                ),
                details={
                    "campus_id": campus_id,
                    "campus_timezone": campus.timezone,
                    "local_time": session_time_local.isoformat(),
                },
            )

        return None


class CampusDistanceConstraint(Constraint):
    """Ensures students can reasonably commute to campus locations."""

    def __init__(
        self,
        campus_manager: "CampusManager",
        student_locations: Dict[str, Tuple[float, float]],  # student_id -> (lat, lon)
        max_distance_km: float = 50.0,
        violation_penalty: float = 400.0,
    ):
        """
        Initialize campus distance constraint.

        Args:
            campus_manager: Campus management system
            student_locations: Student home coordinates
            max_distance_km: Maximum reasonable commuting distance
            violation_penalty: Penalty for distance violations
        """
        super().__init__("campus_distance", violation_penalty)
        self.campus_manager = campus_manager
        self.student_locations = student_locations
        self.max_distance_km = max_distance_km

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if campus location is reasonable for enrolled students."""
        # Get session request
        request = context.request_lookup.get(assignment.request_id)
        if not request:
            return None

        # Get enrolled students
        if not hasattr(request, "enrolled_students") or not request.enrolled_students:
            return None

        # Get resource campus
        resource = context.resource_lookup.get(str(assignment.resource.id))
        if not resource:
            return None

        campus_id = getattr(resource, "campus_id", None)
        if not campus_id:
            return None

        # Check commuting distances
        distant_students = []
        for student_id in request.enrolled_students:
            if student_id not in self.student_locations:
                continue

            lat, lon = self.student_locations[student_id]
            distance = self.campus_manager.calculate_commuting_distance(lat, lon, campus_id)

            if distance > self.max_distance_km:
                distant_students.append(
                    {
                        "student_id": student_id,
                        "distance_km": distance,
                    }
                )

        # Allow some exceptions (e.g., graduate students, online options)
        max_distant = max(1, len(request.enrolled_students) * 0.05)  # 5% tolerance

        if len(distant_students) > max_distant:
            return Violation(
                constraint=self,
                assignment=assignment,
                message=(
                    f"Too many students ({len(distant_students)}) have excessive commuting "
                    f"distance to campus {campus_id}"
                ),
                details={
                    "campus_id": campus_id,
                    "distant_students": distant_students[:5],  # Limit to 5 in details
                    "max_distance_km": self.max_distance_km,
                    "total_distant": len(distant_students),
                },
            )

        return None


@dataclass
class CampusPreference:
    """Preference for campus scheduling."""

    campus_id: str
    preference_score: float  # 0-1, higher is better
    max_distance_km: float = 50.0
    transportation_available: bool = True
    preferred_time_blocks: List[Tuple[time, time]] = None


class CampusScorer:
    """Calculates campus preference scores for assignments."""

    def __init__(self, campus_manager: "CampusManager"):
        self.campus_manager = campus_manager

    def calculate_campus_score(
        self,
        campus_id: str,
        student_locations: List[Tuple[float, float]],
        department_id: str = None,
        course_capacity: int = 0,
    ) -> float:
        """Calculate preference score for a campus."""
        campus = self.campus_manager.campuses.get(campus_id)
        if not campus or not campus.is_active:
            return 0.0

        score = 0.5  # Base score

        # Factor in commuting distances
        if student_locations:
            total_distance = 0.0
            count = 0
            for lat, lon in student_locations:
                distance = self.campus_manager.calculate_commuting_distance(lat, lon, campus_id)
                if distance < float("inf"):
                    total_distance += distance
                    count += 1

            if count > 0:
                avg_distance = total_distance / count
                # Penalize long distances
                distance_penalty = min(0.4, avg_distance / 50.0)  # Max penalty for 50km
                score -= distance_penalty

        # Factor in resource availability
        if course_capacity > 0:
            suitable_resources = [
                r
                for r in self.campus_manager.get_campus_resources(campus_id)
                if r.capacity >= course_capacity
            ]
            resource_bonus = min(
                0.3, len(suitable_resources) / 10.0
            )  # Max bonus for many resources
            score += resource_bonus

        # Factor in primary campus bonus
        if campus.is_primary_campus:
            score += 0.1

        return max(0.0, min(1.0, score))

    def suggest_alternative_campuses(
        self,
        preferred_campus_id: str,
        student_locations: List[Tuple[float, float]],
        department_id: str = None,
        course_capacity: int = 0,
        top_n: int = 3,
    ) -> List[Tuple[str, float]]:
        """Suggest alternative campuses with scores."""
        scores = []

        for campus_id in self.campus_manager.campuses:
            if campus_id == preferred_campus_id:
                continue

            score = self.calculate_campus_score(
                campus_id,
                student_locations,
                department_id,
                course_capacity,
            )
            scores.append((campus_id, score))

        # Sort by score (descending) and return top N
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_n]
