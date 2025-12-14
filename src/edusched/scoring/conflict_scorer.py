"""Conflict scoring and priority system for scheduling constraints."""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

from edusched.constraints.base import Violation


class ConstraintPriority(Enum):
    """Priority levels for constraints."""

    CRITICAL = 5  # Cannot violate (e.g., room double-booking)
    HIGH = 4  # Very important to satisfy
    MEDIUM = 3  # Important but flexible
    LOW = 2  # Nice to have
    INFORMATIONAL = 1  # For reporting only


class ConflictType(Enum):
    """Types of scheduling conflicts."""

    ROOM_DOUBLE_BOOKING = "room_double_booking"
    TEACHER_DOUBLE_BOOKING = "teacher_double_booking"
    STUDENT_CONFLICT = "student_conflict"
    CAPACITY_EXCEEDED = "capacity_exceeded"
    EQUIPMENT_MISSING = "equipment_missing"
    PREREQUISITE_MISSING = "prerequisite_missing"
    PATTERN_VIOLATION = "pattern_violation"
    HOLIDAY_VIOLATION = "holiday_violation"
    ACCESSIBILITY_VIOLATION = "accessibility_violation"
    PREFERENCE_VIOLATION = "preference_violation"


@dataclass
class ConflictScore:
    """Represents a scored conflict with weight and impact."""

    violation: Violation
    priority: ConstraintPriority
    impact_score: float  # 0.0 to 1.0, how severe the conflict is
    affected_parties: List[str]  # Student/teacher/room IDs affected
    suggested_resolution: Optional[str] = None


class ConflictScorer:
    """Scores and prioritizes scheduling conflicts."""

    def __init__(self):
        # Default constraint priorities
        self.constraint_priorities = {
            "hard": ConstraintPriority.CRITICAL,
            "soft": ConstraintPriority.MEDIUM,
        }

        # Default impact scores for different conflict types
        self.impact_scores = {
            ConflictType.ROOM_DOUBLE_BOOKING: 1.0,
            ConflictType.TEACHER_DOUBLE_BOOKING: 1.0,
            ConflictType.STUDENT_CONFLICT: 0.9,
            ConflictType.CAPACITY_EXCEEDED: 0.8,
            ConflictType.EQUIPMENT_MISSING: 0.7,
            ConflictType.PREREQUISITE_MISSING: 0.9,
            ConflictType.PATTERN_VIOLATION: 0.6,
            ConflictType.HOLIDAY_VIOLATION: 0.8,
            ConflictType.ACCESSIBILITY_VIOLATION: 1.0,
            ConflictType.PREFERENCE_VIOLATION: 0.3,
        }

    def score_conflicts(
        self, violations: List[Violation], context=None
    ) -> Tuple[float, List[ConflictScore]]:
        """
        Score a list of violations.

        Args:
            violations: List of constraint violations
            context: Scheduling context for additional info

        Returns:
            Tuple of (total_score, detailed_scores)
        """
        detailed_scores = []

        for violation in violations:
            score = self._score_single_violation(violation, context)
            detailed_scores.append(score)

        # Calculate total weighted score
        total_score = sum(score.priority.value * score.impact_score for score in detailed_scores)

        return total_score, detailed_scores

    def _score_single_violation(self, violation: Violation, context=None) -> ConflictScore:
        """Score a single violation."""
        # Determine constraint type and priority
        priority = self._get_constraint_priority(violation)
        impact_score = self._calculate_impact_score(violation)

        # Extract affected parties from message
        affected_parties = self._extract_affected_parties(violation)

        # Generate suggested resolution
        suggested_resolution = self._suggest_resolution(violation)

        return ConflictScore(
            violation=violation,
            priority=priority,
            impact_score=impact_score,
            affected_parties=affected_parties,
            suggested_resolution=suggested_resolution,
        )

    def _get_constraint_priority(self, violation: Violation) -> ConstraintPriority:
        """Get the priority level for a constraint violation."""
        # Extract priority from constraint type
        constraint_type = violation.constraint_type.lower()

        if "critical" in constraint_type or "double_book" in constraint_type:
            return ConstraintPriority.CRITICAL
        elif "capacity" in constraint_type or "prerequisite" in constraint_type:
            return ConstraintPriority.HIGH
        elif "pattern" in constraint_type or "holiday" in constraint_type:
            return ConstraintPriority.MEDIUM
        elif "preference" in constraint_type or "soft" in constraint_type:
            return ConstraintPriority.LOW
        else:
            return ConstraintPriority.MEDIUM

    def _calculate_impact_score(self, violation: Violation) -> float:
        """Calculate impact score based on violation details."""
        # Base score from conflict type
        constraint_type = violation.constraint_type.lower()

        # Identify conflict type
        conflict_type = self._identify_conflict_type(constraint_type, violation.message)
        base_score = self.impact_scores.get(conflict_type, 0.5)

        # Adjust based on number of affected entities
        affected_count = len(self._extract_affected_parties(violation))
        if affected_count > 1:
            # Multiple entities affected increases impact
            adjustment = min(0.3, 0.1 * (affected_count - 1))
            base_score = min(1.0, base_score + adjustment)

        # Adjust based on severity indicators in message
        if "exceeds" in violation.message.lower():
            base_score = min(1.0, base_score + 0.2)

        return base_score

    def _identify_conflict_type(self, constraint_type: str, message: str) -> ConflictType:
        """Identify the specific type of conflict."""
        message_lower = message.lower()

        if "double" in message_lower and "room" in message_lower:
            return ConflictType.ROOM_DOUBLE_BOOKING
        elif "double" in message_lower and "teacher" in message_lower:
            return ConflictType.TEACHER_DOUBLE_BOOKING
        elif "student" in message_lower and "conflict" in message_lower:
            return ConflictType.STUDENT_CONFLICT
        elif "capacity" in message_lower or "exceeds" in message_lower:
            return ConflictType.CAPACITY_EXCEEDED
        elif "equipment" in message_lower or "missing" in message_lower:
            return ConflictType.EQUIPMENT_MISSING
        elif "prerequisite" in message_lower:
            return ConflictType.PREREQUISITE_MISSING
        elif "pattern" in message_lower:
            return ConflictType.PATTERN_VIOLATION
        elif "holiday" in message_lower:
            return ConflictType.HOLIDAY_VIOLATION
        elif "accessibility" in message_lower or "wheelchair" in message_lower:
            return ConflictType.ACCESSIBILITY_VIOLATION
        elif "preference" in message_lower:
            return ConflictType.PREFERENCE_VIOLATION

        return ConflictType.PATTERN_VIOLATION

    def _extract_affected_parties(self, violation: Violation) -> List[str]:
        """Extract IDs of affected entities from violation message."""
        affected = []

        # Look for IDs in the message
        import re

        # Extract various ID patterns
        id_patterns = [
            r"\b[A-Z]{2,4}\d{2,4}\b",  # Course IDs like CS401
            r"\bprof_[a-z_]+",  # Teacher IDs
            r"\bRoom\d+[A-Z]*",  # Room IDs
            r"\b\d{5,10}\b",  # Student IDs
        ]

        for pattern in id_patterns:
            matches = re.findall(pattern, violation.message)
            affected.extend(matches)

        # Also include the request_id
        if violation.affected_request_id:
            affected.append(violation.affected_request_id)

        # Remove duplicates
        return list(set(affected))

    def _suggest_resolution(self, violation: Violation) -> Optional[str]:
        """Suggest a resolution for the violation."""
        constraint_type = violation.constraint_type.lower()
        message = violation.message.lower()

        if "double" in message and ("room" in message or "teacher" in message):
            return "Reschedule one of the conflicting classes"

        elif "capacity" in message or "exceeds" in message:
            return "Use a larger room or split into multiple sections"

        elif "prerequisite" in message:
            return "Ensure prerequisites are completed or take prerequisite course first"

        elif "pattern" in message:
            return "Adjust scheduling pattern or move to different day"

        elif "holiday" in message:
            return "Schedule on different date outside holiday period"

        elif "equipment" in message:
            return "Choose room with required equipment or add equipment"

        elif "accessibility" in message:
            return "Select wheelchair-accessible room with required features"

        elif "preference" in message:
            return "Consider alternative time if preference cannot be met"

        return "Review constraint and adjust scheduling accordingly"

    def rank_violations(
        self, violations: List[Violation], max_to_resolve: int = None
    ) -> List[ConflictScore]:
        """Rank violations by priority and impact."""
        _, detailed_scores = self.score_conflicts(violations)

        # Sort by priority (descending) then impact (descending)
        detailed_scores.sort(key=lambda s: (s.priority.value, s.impact_score), reverse=True)

        if max_to_resolve:
            return detailed_scores[:max_to_resolve]

        return detailed_scores

    def get_conflict_summary(self, detailed_scores: List[ConflictScore]) -> Dict[str, any]:
        """Generate a summary of conflicts."""
        summary = {
            "total_violations": len(detailed_scores),
            "critical_violations": 0,
            "high_violations": 0,
            "medium_violations": 0,
            "low_violations": 0,
            "most_common_types": {},
            "total_impacted_parties": set(),
            "resolutions": [],
        }

        for score in detailed_scores:
            # Count by priority
            if score.priority == ConstraintPriority.CRITICAL:
                summary["critical_violations"] += 1
            elif score.priority == ConstraintPriority.HIGH:
                summary["high_violations"] += 1
            elif score.priority == ConstraintPriority.MEDIUM:
                summary["medium_violations"] += 1
            else:
                summary["low_violations"] += 1

            # Track affected parties
            summary["total_impacted_parties"].update(score.affected_parties)

            # Collect resolutions
            if score.suggested_resolution:
                summary["resolutions"].append(
                    {"conflict": score.violation.message, "resolution": score.suggested_resolution}
                )

        summary["total_impacted_parties"] = len(summary["total_impacted_parties"])

        return summary

    def calculate_schedule_quality(
        self, violations: List[Violation], total_assignments: int
    ) -> float:
        """
        Calculate overall schedule quality score (0.0 to 1.0).

        Args:
            violations: List of violations in the schedule
            total_assignments: Total number of assignments

        Returns:
            Quality score (higher is better)
        """
        if total_assignments == 0:
            return 1.0

        total_score, _ = self.score_conflicts(violations)

        # Normalize by number of assignments
        normalized_score = total_score / total_assignments

        # Convert to quality score (inverted)
        quality_score = max(0.0, 1.0 - normalized_score / 10.0)

        return quality_score
