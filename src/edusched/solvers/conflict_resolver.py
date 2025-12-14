"""Conflict resolution system for EduSched.

Provides priority-based conflict resolution, constraint ranking,
suggestion generation, and automated conflict mitigation strategies.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from edusched.constraints.base import Constraint, Violation


class ConflictType(Enum):
    """Types of scheduling conflicts."""

    RESOURCE_DOUBLE_BOOKING = "resource_double_booking"
    TEACHER_OVERLOAD = "teacher_overload"
    CAPACITY_EXCEEDED = "capacity_exceeded"
    TIME_SLOT_UNAVAILABLE = "time_slot_unavailable"
    EQUIPMENT_UNAVAILABLE = "equipment_unavailable"
    ROOM_UNAVAILABLE = "room_unavailable"
    STUDENT_CONFLICT = "student_conflict"
    PREREQUISITE_VIOLATION = "prerequisite_violation"
    BLACKOUT_DATE = "blackout_date"
    PREFERENCE_VIOLATION = "preference_violation"


class ResolutionStrategy(Enum):
    """Conflict resolution strategies."""

    REMOVE_VIOLATION = "remove_violation"  # Remove the conflicting assignment
    RESCHEDULE = "reschedule"  # Move to different time/resource
    REASSIGN = "reassign"  # Assign to different resource
    RELAX_CONSTRAINT = "relax_constraint"  # Temporarily relax constraint
    PARTIAL_SCHEDULE = "partial_schedule"  # Schedule only part of request
    ALTERNATE_RESOURCE = "alternate_resource"  # Use alternative resource
    ADJUST_DURATION = "adjust_duration"  # Change session duration


@dataclass
class Conflict:
    """Represents a scheduling conflict."""

    conflict_id: str
    conflict_type: ConflictType
    severity: float  # 0-1, higher is more severe
    description: str

    # Affected entities
    assignment_ids: List[str] = field(default_factory=list)
    resource_ids: List[str] = field(default_factory=list)
    teacher_ids: List[str] = field(default_factory=list)
    student_ids: List[str] = field(default_factory=list)

    # Related constraints
    violated_constraints: List[str] = field(default_factory=list)
    constraint_violations: List[Violation] = field(default_factory=list)

    # Resolution options
    suggested_strategies: List[ResolutionStrategy] = field(default_factory=list)
    alternative_assignments: List[Dict[str, Any]] = field(default_factory=list)

    # Metadata
    detection_time: datetime = field(default_factory=datetime.now)
    resolver: Optional[str] = None  # What/who detected the conflict
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConstraintRanking:
    """Ranking configuration for constraints."""

    constraint_id: str
    priority: int  # 1=highest, 10=lowest
    weight: float  # Relative importance in optimization
    category: str
    is_hard: bool = True  # False for soft constraints
    can_relax: bool = False
    relax_penalty: float = 0.0


@dataclass
class ResolutionResult:
    """Result of conflict resolution attempt."""

    success: bool
    resolved_conflicts: List[str] = field(default_factory=list)
    remaining_conflicts: List[str] = field(default_factory=list)
    resolution_strategy: Optional[ResolutionStrategy] = None
    resolution_details: Dict[str, Any] = field(default_factory=dict)
    new_conflicts: List[Conflict] = field(default_factory=list)
    quality_impact: float = 0.0  # -1 to 1, negative = lower quality


class ConflictDetector:
    """Detects various types of scheduling conflicts."""

    def __init__(self):
        self.conflict_patterns = {
            ConflictType.RESOURCE_DOUBLE_BOOKING: self._detect_resource_conflicts,
            ConflictType.TEACHER_OVERLOAD: self._detect_teacher_overload,
            ConflictType.CAPACITY_EXCEEDED: self._detect_capacity_issues,
            ConflictType.TIME_SLOT_UNAVAILABLE: self._detect_time_slot_conflicts,
            ConflictType.STUDENT_CONFLICT: self._detect_student_conflicts,
        }

    def detect_all_conflicts(
        self,
        assignments: List[Any],
        context: Any,
    ) -> List[Conflict]:
        """Detect all conflicts in the schedule."""
        conflicts = []

        # Run all detection patterns
        for conflict_type, detector in self.conflict_patterns.items():
            detected = detector(assignments, context)
            conflicts.extend(detected)

        # Detect constraint violations
        constraint_conflicts = self._detect_constraint_violations(assignments, context)
        conflicts.extend(constraint_conflicts)

        return conflicts

    def _detect_resource_conflicts(
        self,
        assignments: List[Any],
        context: Any,
    ) -> List[Conflict]:
        """Detect resource double-booking conflicts."""
        conflicts = []
        resource_usage = {}

        # Build resource usage map
        for assignment in assignments:
            for resource in assignment.assigned_resources:
                for resource_id in resource:
                    if resource_id not in resource_usage:
                        resource_usage[resource_id] = []
                    resource_usage[resource_id].append(assignment)

        # Check for conflicts
        for resource_id, usage in resource_usage.items():
            for i in range(len(usage)):
                for j in range(i + 1, len(usage)):
                    if self._assignments_overlap(usage[i], usage[j]):
                        conflict = Conflict(
                            conflict_id=f"resource_conflict_{resource_id}_{i}_{j}",
                            conflict_type=ConflictType.RESOURCE_DOUBLE_BOOKING,
                            severity=0.9,  # High severity
                            description=f"Resource {resource_id} double-booked",
                            assignment_ids=[usage[i].id, usage[j].id],
                            resource_ids=[resource_id],
                            suggested_strategies=[
                                ResolutionStrategy.RESCHEDULE,
                                ResolutionStrategy.REASSIGN,
                            ],
                        )
                        conflicts.append(conflict)

        return conflicts

    def _detect_teacher_overload(
        self,
        assignments: List[Any],
        context: Any,
    ) -> List[Conflict]:
        """Detect teacher overload conflicts."""
        conflicts = []
        teacher_assignments = {}

        # Group by teacher
        for assignment in assignments:
            request = context.request_lookup.get(assignment.request_id)
            if request and request.teacher_id:
                teacher_id = request.teacher_id
                if teacher_id not in teacher_assignments:
                    teacher_assignments[teacher_id] = []
                teacher_assignments[teacher_id].append(assignment)

        # Check for overlaps
        for teacher_id, assignments_list in teacher_assignments.items():
            for i in range(len(assignments_list)):
                for j in range(i + 1, len(assignments_list)):
                    if self._assignments_overlap(assignments_list[i], assignments_list[j]):
                        conflict = Conflict(
                            conflict_id=f"teacher_overload_{teacher_id}_{i}_{j}",
                            conflict_type=ConflictType.TEACHER_OVERLOAD,
                            severity=0.8,
                            description=f"Teacher {teacher_id} has overlapping assignments",
                            assignment_ids=[assignments_list[i].id, assignments_list[j].id],
                            teacher_ids=[teacher_id],
                            suggested_strategies=[
                                ResolutionStrategy.RESCHEDULE,
                                ResolutionStrategy.ADJUST_DURATION,
                            ],
                        )
                        conflicts.append(conflict)

        return conflicts

    def _detect_capacity_issues(
        self,
        assignments: List[Any],
        context: Any,
    ) -> List[Conflict]:
        """Detect capacity exceeded conflicts."""
        conflicts = []

        for assignment in assignments:
            request = context.request_lookup.get(assignment.request_id)
            resource = context.resource_lookup.get(assignment.resource.id)

            if request and resource and hasattr(resource, "capacity"):
                enrollment = getattr(request, "enrollment_count", 0)
                if enrollment > resource.capacity:
                    conflict = Conflict(
                        conflict_id=f"capacity_exceeded_{assignment.id}",
                        conflict_type=ConflictType.CAPACITY_EXCEEDED,
                        severity=0.7,
                        description=f"Room capacity exceeded: {enrollment} > {resource.capacity}",
                        assignment_ids=[assignment.id],
                        resource_ids=[resource.id],
                        suggested_strategies=[
                            ResolutionStrategy.REASSIGN,
                            ResolutionStrategy.ALTERNATE_RESOURCE,
                        ],
                    )
                    conflicts.append(conflict)

        return conflicts

    def _detect_time_slot_conflicts(
        self,
        assignments: List[Any],
        context: Any,
    ) -> List[Conflict]:
        """Detect time slot availability conflicts."""
        conflicts = []

        for assignment in assignments:
            request = context.request_lookup.get(assignment.request_id)
            if request and hasattr(request, "blackout_dates"):
                # Check against blackout dates
                for start_date, end_date in request.blackout_dates:
                    if start_date <= assignment.start_time.date() <= end_date:
                        conflict = Conflict(
                            conflict_id=f"blackout_date_{assignment.id}",
                            conflict_type=ConflictType.BLACKOUT_DATE,
                            severity=1.0,  # Critical
                            description="Assignment during blackout date",
                            assignment_ids=[assignment.id],
                            suggested_strategies=[
                                ResolutionStrategy.RESCHEDULE,
                            ],
                        )
                        conflicts.append(conflict)

        return conflicts

    def _detect_student_conflicts(
        self,
        assignments: List[Any],
        context: Any,
    ) -> List[Conflict]:
        """Detect student scheduling conflicts."""
        conflicts = []
        student_assignments = {}

        # Group by student
        for assignment in assignments:
            request = context.request_lookup.get(assignment.request_id)
            if request and hasattr(request, "enrolled_students"):
                for student_id in request.enrolled_students:
                    if student_id not in student_assignments:
                        student_assignments[student_id] = []
                    student_assignments[student_id].append(assignment)

        # Check for overlaps
        for student_id, assignments_list in student_assignments.items():
            for i in range(len(assignments_list)):
                for j in range(i + 1, len(assignments_list)):
                    if self._assignments_overlap(assignments_list[i], assignments_list[j]):
                        conflict = Conflict(
                            conflict_id=f"student_conflict_{student_id}_{i}_{j}",
                            conflict_type=ConflictType.STUDENT_CONFLICT,
                            severity=0.6,  # Medium severity
                            description=f"Student {student_id} has overlapping classes",
                            assignment_ids=[assignments_list[i].id, assignments_list[j].id],
                            student_ids=[student_id],
                            suggested_strategies=[
                                ResolutionStrategy.RESCHEDULE,
                            ],
                        )
                        conflicts.append(conflict)

        return conflicts

    def _detect_constraint_violations(
        self,
        assignments: List[Any],
        context: Any,
    ) -> List[Conflict]:
        """Detect general constraint violations."""
        conflicts = []

        for assignment in assignments:
            for constraint in context.constraints:
                violation = constraint.check(assignment, assignments, context)
                if violation:
                    conflict = Conflict(
                        conflict_id=f"constraint_violation_{constraint.constraint_type}_{assignment.id}",
                        conflict_type=ConflictType.PREFERENCE_VIOLATION,
                        severity=0.5,  # Default severity
                        description=f"Constraint violation: {violation.message}",
                        assignment_ids=[assignment.id],
                        violated_constraints=[constraint.constraint_type],
                        constraint_violations=[violation],
                        suggested_strategies=[
                            ResolutionStrategy.RESCHEDULE,
                            ResolutionStrategy.RELAX_CONSTRAINT,
                        ],
                    )
                    conflicts.append(conflict)

        return conflicts

    def _assignments_overlap(self, assignment1: Any, assignment2: Any) -> bool:
        """Check if two assignments overlap in time."""
        end1 = assignment1.start_time + assignment1.duration
        end2 = assignment2.start_time + assignment2.duration
        return assignment1.start_time < end2 and assignment2.start_time < end1


class ConflictResolver:
    """Resolves scheduling conflicts using various strategies."""

    def __init__(self):
        self.detector = ConflictDetector()
        self.constraint_rankings = {}
        self.resolution_strategies = {
            ResolutionStrategy.REMOVE_VIOLATION: self._resolve_by_removal,
            ResolutionStrategy.RESCHEDULE: self._resolve_by_rescheduling,
            ResolutionStrategy.REASSIGN: self._resolve_by_reassignment,
            ResolutionStrategy.ALTERNATIVE_RESOURCE: self._resolve_with_alternative,
        }

    def resolve_conflicts(
        self,
        conflicts: List[Conflict],
        assignments: List[Any],
        context: Any,
        strategy_order: Optional[List[ResolutionStrategy]] = None,
    ) -> ResolutionResult:
        """
        Attempt to resolve a list of conflicts.

        Args:
            conflicts: List of conflicts to resolve
            assignments: Current assignments
            context: Scheduling context
            strategy_order: Preferred order of resolution strategies

        Returns:
            ResolutionResult with outcome details
        """
        if not strategy_order:
            strategy_order = [
                ResolutionStrategy.ALTERNATIVE_RESOURCE,
                ResolutionStrategy.RESCHEDULE,
                ResolutionStrategy.REASSIGN,
                ResolutionStrategy.REMOVE_VIOLATION,
            ]

        result = ResolutionResult(success=False)
        remaining_conflicts = conflicts.copy()

        # Sort conflicts by severity (highest first)
        remaining_conflicts.sort(key=lambda c: c.severity, reverse=True)

        # Try to resolve each conflict
        for conflict in remaining_conflicts:
            for strategy in strategy_order:
                if strategy not in conflict.suggested_strategies:
                    continue

                strategy_result = self._apply_resolution_strategy(
                    conflict, strategy, assignments, context
                )

                if strategy_result.success:
                    result.success = True
                    result.resolved_conflicts.append(conflict.conflict_id)
                    result.resolution_strategy = strategy
                    result.resolution_details.update(strategy_result.resolution_details)

                    # Check for new conflicts
                    new_conflicts = self.detector.detect_all_conflicts(assignments, context)
                    result.new_conflicts = new_conflicts

                    break  # Move to next conflict
                else:
                    # Try next strategy
                    continue

            # If no strategy worked, add to remaining conflicts
            if conflict.conflict_id not in result.resolved_conflicts:
                result.remaining_conflicts.append(conflict.conflict_id)

        return result

    def generate_suggestions(
        self,
        conflicts: List[Conflict],
        context: Any,
    ) -> Dict[str, List[str]]:
        """
        Generate suggestions for resolving conflicts.

        Args:
            conflicts: List of conflicts
            context: Scheduling context

        Returns:
            Dictionary mapping conflict_id to list of suggestions
        """
        suggestions = {}

        for conflict in conflicts:
            conflict_suggestions = []

            # Add general suggestions based on conflict type
            if conflict.conflict_type == ConflictType.RESOURCE_DOUBLE_BOOKING:
                conflict_suggestions.extend(
                    [
                        "Use a different room",
                        "Change the time of one session",
                        "Check for alternative resources",
                    ]
                )
            elif conflict.conflict_type == ConflictType.TEACHER_OVERLOAD:
                conflict_suggestions.extend(
                    [
                        "Reschedule one session to a different day",
                        "Find an alternative instructor",
                        "Split the session into smaller parts",
                    ]
                )
            elif conflict.conflict_type == ConflictType.CAPACITY_EXCEEDED:
                conflict_suggestions.extend(
                    [
                        "Move to a larger room",
                        "Split the class into multiple sections",
                        "Offer online participation for some students",
                    ]
                )
            elif conflict.conflict_type == ConflictType.STUDENT_CONFLICT:
                conflict_suggestions.extend(
                    [
                        "Offer recorded sessions",
                        "Provide alternative time slots",
                        "Consider hybrid attendance options",
                    ]
                )

            # Add specific alternative assignments
            if conflict.alternative_assignments:
                for alt in conflict.alternative_assignments[:3]:  # Top 3 alternatives
                    if "time" in alt and "resource" in alt:
                        conflict_suggestions.append(f"Move to {alt['time']} in {alt['resource']}")

            suggestions[conflict.conflict_id] = conflict_suggestions

        return suggestions

    def rank_constraints(
        self,
        constraints: List[Constraint],
        context: Any,
    ) -> List[ConstraintRanking]:
        """
        Rank constraints by priority and importance.

        Args:
            constraints: List of constraints to rank
            context: Scheduling context

        Returns:
            List of constraint rankings
        """
        rankings = []

        for constraint in constraints:
            # Determine category and priority
            if "hard" in constraint.constraint_type:
                priority = 1  # Highest
                weight = 10.0
                is_hard = True
            elif "soft" in constraint.constraint_type:
                priority = 5  # Medium
                weight = 5.0
                is_hard = False
                can_relax = True
            else:
                priority = 3  # Default medium-high
                weight = 7.0
                is_hard = True

            ranking = ConstraintRanking(
                constraint_id=constraint.constraint_type,
                priority=priority,
                weight=weight,
                category=self._determine_constraint_category(constraint),
                is_hard=is_hard,
                can_relax=not is_hard,
            )

            rankings.append(ranking)

        # Sort by priority (1 first)
        rankings.sort(key=lambda r: r.priority)
        return rankings

    def _apply_resolution_strategy(
        self,
        conflict: Conflict,
        strategy: ResolutionStrategy,
        assignments: List[Any],
        context: Any,
    ) -> ResolutionResult:
        """Apply a specific resolution strategy."""
        if strategy in self.resolution_strategies:
            return self.resolution_strategies[strategy](conflict, assignments, context)

        # Default: failure
        return ResolutionResult(success=False)

    def _resolve_by_removal(
        self,
        conflict: Conflict,
        assignments: List[Any],
        context: Any,
    ) -> ResolutionResult:
        """Resolve by removing violating assignment."""
        # Find lowest priority assignment to remove
        assignment_to_remove = None
        min_priority = float("inf")

        for assignment_id in conflict.assignment_ids:
            assignment = next((a for a in assignments if a.id == assignment_id), None)
            if assignment:
                request = context.request_lookup.get(assignment.request_id)
                priority = getattr(request, "priority", 5)
                if priority < min_priority:
                    min_priority = priority
                    assignment_to_remove = assignment

        if assignment_to_remove:
            assignments.remove(assignment_to_remove)
            return ResolutionResult(
                success=True,
                resolution_details={
                    "action": "removed",
                    "assignment_id": assignment_to_remove.id,
                    "priority": min_priority,
                },
                quality_impact=-0.2,  # Slightly lower quality
            )

        return ResolutionResult(success=False)

    def _resolve_by_rescheduling(
        self,
        conflict: Conflict,
        assignments: List[Any],
        context: Any,
    ) -> ResolutionResult:
        """Resolve by rescheduling to different time."""
        # This is a simplified implementation
        # In practice, would use the solver to find new time slots

        return ResolutionResult(
            success=False, resolution_details={"reason": "Rescheduling not implemented"}
        )

    def _resolve_by_reassignment(
        self,
        conflict: Conflict,
        assignments: List[Any],
        context: Any,
    ) -> ResolutionResult:
        """Resolve by assigning to different resource."""
        # This is a simplified implementation
        # In practice, would check for alternative resources

        return ResolutionResult(
            success=False, resolution_details={"reason": "Reassignment not implemented"}
        )

    def _resolve_with_alternative(
        self,
        conflict: Conflict,
        assignments: List[Any],
        context: Any,
    ) -> ResolutionResult:
        """Resolve using alternative resources."""
        # This is a simplified implementation
        # In practice, would find and assign alternative resources

        return ResolutionResult(
            success=False, resolution_details={"reason": "Alternative resources not found"}
        )

    def _determine_constraint_category(self, constraint: Constraint) -> str:
        """Determine category of a constraint."""
        constraint_type = constraint.constraint_type.lower()

        if "resource" in constraint_type:
            return "resource"
        elif "time" in constraint_type:
            return "temporal"
        elif "capacity" in constraint_type:
            return "capacity"
        elif "teacher" in constraint_type:
            return "personnel"
        else:
            return "general"


class AutomatedResolver:
    """Automated conflict resolution with learning capabilities."""

    def __init__(self):
        self.resolver = ConflictResolver()
        self.resolution_history = []
        self.success_patterns = {}
        self.failure_patterns = {}

    def auto_resolve(
        self,
        conflicts: List[Conflict],
        assignments: List[Any],
        context: Any,
        max_attempts: int = 3,
    ) -> ResolutionResult:
        """
        Automatically resolve conflicts with learning from past resolutions.

        Args:
            conflicts: Conflicts to resolve
            assignments: Current assignments
            context: Scheduling context
            max_attempts: Maximum resolution attempts per conflict

        Returns:
            ResolutionResult with automated resolution outcome
        """
        result = ResolutionResult(success=False)

        # Sort conflicts by severity
        sorted_conflicts = sorted(conflicts, key=lambda c: c.severity, reverse=True)

        for conflict in sorted_conflicts:
            # Check for successful patterns
            pattern_key = self._get_pattern_key(conflict)
            if pattern_key in self.success_patterns:
                # Use previously successful strategy
                successful_strategy = self.success_patterns[pattern_key]
                attempt_result = self.resolver.resolve_conflicts(
                    [conflict], assignments, context, [successful_strategy]
                )
            else:
                # Try default strategies
                attempt_result = self.resolver.resolve_conflicts([conflict], assignments, context)

            # Record result
            if attempt_result.success:
                if attempt_result.resolution_strategy:
                    self.success_patterns[pattern_key] = attempt_result.resolution_strategy
                result.resolved_conflicts.append(conflict.conflict_id)
            else:
                result.remaining_conflicts.append(conflict.conflict_id)

        # Determine overall success
        result.success = len(result.resolved_conflicts) > 0

        # Record in history
        self.resolution_history.append(
            {
                "timestamp": datetime.now(),
                "conflicts_count": len(conflicts),
                "resolved_count": len(result.resolved_conflicts),
                "success_rate": len(result.resolved_conflicts) / len(conflicts) if conflicts else 0,
            }
        )

        return result

    def _get_pattern_key(self, conflict: Conflict) -> str:
        """Generate pattern key for conflict type recognition."""
        return f"{conflict.conflict_type.value}_{len(conflict.assignment_ids)}"
