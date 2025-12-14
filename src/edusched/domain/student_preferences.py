"""Student preference domain models for personalized scheduling.

Handles student preferences for:
- Time slot preferences
- Course sequence preferences
- Cohort scheduling requirements
- Walking distance minimization
- Campus building preferences
"""

from dataclasses import dataclass, field
from datetime import time
from typing import Dict, List, Optional, Set

from edusched.domain.base import BaseEntity


@dataclass
class TimePreference:
    """Time slot preference for a student."""

    day: str  # monday, tuesday, etc.
    start_time: time  # Preferred start time
    end_time: time  # Preferred end time
    priority: int  # 1=highest, 5=lowest
    flexible: bool = False  # Can be flexible with this preference


@dataclass
class CoursePreference:
    """Preference for specific courses."""

    course_id: str
    preferred_instructors: List[str] = field(default_factory=list)
    preferred_times: List[TimePreference] = field(default_factory=list)
    avoid_times: List[TimePreference] = field(default_factory=list)
    preferred_room_types: List[str] = field(default_factory=list)
    wants_online: Optional[bool] = None  # True/False/None for any


@dataclass
class CohortRequirement:
    """Cohort scheduling requirements."""

    cohort_id: str
    student_ids: Set[str] = field(default_factory=set)
    courses: List[str] = field(default_factory=list)  # Courses to take together
    same_time: bool = False  # All courses at same time
    same_day: bool = False  # All courses on same day
    consecutive: bool = False  # Back-to-back scheduling
    min_gap_minutes: int = 0  # Minimum gap between classes


@dataclass
class WalkingDistancePreference:
    """Preference for minimizing walking distance."""

    max_distance_meters: float = 500.0  # Maximum walking distance
    prioritize_campus_center: bool = True  # Prefer campus center
    avoid_hills: bool = True  # Avoid hilly routes
    accessible_route: bool = False  # Requires accessible route


@dataclass
class StudentPreferences(BaseEntity):
    """Comprehensive student preferences."""

    student_id: str
    time_preferences: List[TimePreference] = field(default_factory=list)
    course_preferences: Dict[str, CoursePreference] = field(default_factory=dict)
    cohort_requirements: List[CohortRequirement] = field(default_factory=list)
    walking_distance: WalkingDistancePreference = field(default_factory=WalkingDistancePreference)
    building_preferences: Dict[str, float] = field(
        default_factory=dict
    )  # building -> preference score
    preferred_campuses: List[str] = field(default_factory=list)
    avoid_campuses: List[str] = field(default_factory=list)

    # Additional preferences
    wants_morning_classes: Optional[bool] = None
    wants_afternoon_classes: Optional[bool] = None
    prefers_back_to_back: bool = False
    minimum_break_minutes: int = 15
    max_classes_per_day: int = 5
    prefers_same_building: bool = False
    dietary_restrictions: List[str] = field(default_factory=list)  # For dining hall proximity
    accessibility_needs: List[str] = field(default_factory=list)


@dataclass
class PreferenceConflict:
    """Conflict between student preferences."""

    student_id: str
    conflict_type: str  # time, course, cohort, location
    description: str
    severity: str  # low, medium, high
    affected_assignments: List[str] = field(default_factory=list)
    resolution_options: List[str] = field(default_factory=list)


class StudentPreferenceValidator:
    """Validates student preferences for consistency and feasibility."""

    def validate(self, preferences: StudentPreferences) -> List[PreferenceConflict]:
        """Validate student preferences.

        Args:
            preferences: Student preferences to validate

        Returns:
            List of preference conflicts
        """
        conflicts = []

        # Validate time preferences
        conflicts.extend(self._validate_time_preferences(preferences))

        # Validate course preferences
        conflicts.extend(self._validate_course_preferences(preferences))

        # Validate cohort requirements
        conflicts.extend(self._validate_cohort_requirements(preferences))

        # Validate campus preferences
        conflicts.extend(self._validate_campus_preferences(preferences))

        return conflicts

    def _validate_time_preferences(
        self, preferences: StudentPreferences
    ) -> List[PreferenceConflict]:
        """Validate time slot preferences."""
        conflicts = []

        for pref in preferences.time_preferences:
            # Check if end time is after start time
            if pref.end_time <= pref.start_time:
                conflicts.append(
                    PreferenceConflict(
                        student_id=preferences.student_id,
                        conflict_type="time",
                        description=f"End time {pref.end_time} is before start time {pref.start_time}",
                        severity="high",
                    )
                )

            # Check if priority is valid
            if pref.priority < 1 or pref.priority > 5:
                conflicts.append(
                    PreferenceConflict(
                        student_id=preferences.student_id,
                        conflict_type="time",
                        description=f"Invalid priority {pref.priority} (must be 1-5)",
                        severity="low",
                    )
                )

        return conflicts

    def _validate_course_preferences(
        self, preferences: StudentPreferences
    ) -> List[PreferenceConflict]:
        """Validate course preferences."""
        conflicts = []

        for course_id, course_pref in preferences.course_preferences.items():
            # Check if preferred times are valid
            for time_pref in course_pref.preferred_times:
                if time_pref.end_time <= time_pref.start_time:
                    conflicts.append(
                        PreferenceConflict(
                            student_id=preferences.student_id,
                            conflict_type="course",
                            description=f"Invalid time preference for course {course_id}",
                            severity="medium",
                        )
                    )

        return conflicts

    def _validate_cohort_requirements(
        self, preferences: StudentPreferences
    ) -> List[PreferenceConflict]:
        """Validate cohort requirements."""
        conflicts = []

        for cohort in preferences.cohort_requirements:
            # Check if cohort has students
            if not cohort.student_ids:
                conflicts.append(
                    PreferenceConflict(
                        student_id=preferences.student_id,
                        conflict_type="cohort",
                        description=f"Cohort {cohort.cohort_id} has no students",
                        severity="medium",
                    )
                )

            # Check if consecutive requirement makes sense with min gap
            if cohort.consecutive and cohort.min_gap_minutes > 0:
                conflicts.append(
                    PreferenceConflict(
                        student_id=preferences.student_id,
                        conflict_type="cohort",
                        description=f"Cohort {cohort.cohort_id} cannot be both consecutive and have gaps",
                        severity="medium",
                    )
                )

        return conflicts

    def _validate_campus_preferences(
        self, preferences: StudentPreferences
    ) -> List[PreferenceConflict]:
        """Validate campus preferences."""
        conflicts = []

        # Check if preferred and avoided campuses overlap
        overlap = set(preferences.preferred_campuses) & set(preferences.avoid_campuses)
        if overlap:
            conflicts.append(
                PreferenceConflict(
                    student_id=preferences.student_id,
                    conflict_type="location",
                    description=f"Campus both preferred and avoided: {', '.join(overlap)}",
                    severity="high",
                )
            )

        return conflicts


class PreferenceScorer:
    """Calculates preference scores for potential assignments."""

    def calculate_time_score(
        self,
        preferences: StudentPreferences,
        day: str,
        start_time: time,
    ) -> float:
        """Calculate time preference score (0-1, higher is better)."""
        if not preferences.time_preferences:
            return 0.5  # Neutral score

        best_score = 0.0
        for pref in preferences.time_preferences:
            if pref.day.lower() == day.lower():
                # Check if time is within preference window
                if pref.start_time <= start_time <= pref.end_time:
                    # Score based on priority (1=highest)
                    score = (6 - pref.priority) / 5.0
                    best_score = max(best_score, score)

        return best_score

    def calculate_building_score(
        self,
        preferences: StudentPreferences,
        building_id: str,
    ) -> float:
        """Calculate building preference score."""
        if not preferences.building_preferences:
            return 0.5  # Neutral score

        # Return preference score (0-1)
        return preferences.building_preferences.get(building_id, 0.0)

    def calculate_walking_distance_score(
        self,
        preferences: StudentPreferences,
        distance_meters: float,
    ) -> float:
        """Calculate walking distance preference score."""
        max_distance = preferences.walking_distance.max_distance_meters

        if distance_meters <= max_distance:
            # Linear decay: 1.0 at 0m, 0.0 at max_distance
            return 1.0 - (distance_meters / max_distance)
        else:
            # Penalty for exceeding max distance
            return max(0.0, 1.0 - (distance_meters - max_distance) / max_distance)
