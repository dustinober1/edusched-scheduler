"""Incremental scheduling solver for adding/removing courses without full reschedule."""

import bisect
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from edusched.constraints.base import ConstraintContext
from edusched.domain.problem import ProblemIndices
from edusched.solvers.base import SolverBackend

if TYPE_CHECKING:
    from edusched.domain.assignment import Assignment
    from edusched.domain.problem import Problem
    from edusched.domain.result import Result


class IncrementalSolver(SolverBackend):
    """Solver for incremental schedule modifications."""

    def __init__(self, max_attempts: int = 1000):
        self.max_attempts = max_attempts

    def add_course(
        self,
        existing_schedule: List["Assignment"],
        new_request,
        context: ConstraintContext,
        indices: ProblemIndices,
    ) -> Tuple[bool, List["Assignment"], List[str]]:
        """
        Add a new course to existing schedule.

        Args:
            existing_schedule: Current assignments
            new_request: New course request to add
            context: Constraint context
            indices: Problem indices

        Returns:
            Tuple of (success, updated_schedule, conflicts)
        """

        updated_schedule = existing_schedule.copy()
        conflicts = []

        # Try to schedule all occurrences of the new course
        for occurrence_index in range(new_request.number_of_occurrences):
            assignment = self._schedule_single_occurrence(
                new_request, occurrence_index, updated_schedule, context, indices
            )

            if assignment:
                updated_schedule.append(assignment)
            else:
                # Couldn't schedule this occurrence
                conflicts.append(f"Occurrence {occurrence_index + 1} of {new_request.id}")

        # If we couldn't schedule any occurrences, fail
        if all(a.request_id != new_request.id for a in updated_schedule):
            return False, existing_schedule, ["Could not schedule any occurrences"]

        # Verify all constraints still satisfied
        constraint_violations = self._check_all_constraints(updated_schedule, context)
        if constraint_violations:
            return False, existing_schedule, [v.message for v in constraint_violations]

        return True, updated_schedule, conflicts

    def remove_course(
        self, existing_schedule: List["Assignment"], course_id: str, context: ConstraintContext
    ) -> Tuple[bool, List["Assignment"], List[str]]:
        """
        Remove a course from existing schedule.

        Args:
            existing_schedule: Current assignments
            course_id: Course ID to remove
            context: Constraint context

        Returns:
            Tuple of (success, updated_schedule, removed_assignments)
        """
        # Find all assignments for this course
        to_remove = [a for a in existing_schedule if a.request_id == course_id]

        if not to_remove:
            return False, existing_schedule, []

        # Remove assignments
        updated_schedule = [a for a in existing_schedule if a.request_id != course_id]

        # Check if removing breaks any dependencies
        dependency_issues = self._check_dependencies_on_removal(course_id, context)

        if dependency_issues:
            # Roll back changes
            return False, existing_schedule, dependency_issues

        return True, updated_schedule, [f"Removed {len(to_remove)} assignments"]

    def move_assignment(
        self,
        existing_schedule: List["Assignment"],
        assignment_id: str,
        new_time: Tuple[datetime, datetime],
        context: ConstraintContext,
        indices: ProblemIndices,
    ) -> Tuple[bool, List["Assignment"], str]:
        """
        Move an existing assignment to a new time.

        Args:
            existing_schedule: Current assignments
            assignment_id: Assignment to move
            new_time: New (start_time, end_time)
            context: Constraint context
            indices: Problem indices

        Returns:
            Tuple of (success, updated_schedule, message)
        """
        # Find the assignment
        assignment_to_move = None
        for assignment in existing_schedule:
            if hasattr(assignment, "id") and assignment.id == assignment_id:
                assignment_to_move = assignment
                break
            elif hasattr(assignment, "occurrence_index"):
                # Match by request_id and occurrence_index
                # Would need more specific identification here
                pass

        if not assignment_to_move:
            return False, existing_schedule, "Assignment not found"

        # Create new assignment with new time
        new_assignment = Assignment(
            request_id=assignment_to_move.request_id,
            occurrence_index=assignment_to_move.occurrence_index,
            start_time=new_time[0],
            end_time=new_time[1],
            cohort_id=assignment_to_move.cohort_id,
            assigned_resources=assignment_to_move.assigned_resources.copy(),
        )

        # Remove old assignment
        updated_schedule = [a for a in existing_schedule if a != assignment_to_move]

        # Try to place new assignment
        # This would need to check constraints and resource availability
        updated_schedule.append(new_assignment)

        # Verify constraints
        violations = self._check_all_constraints(updated_schedule, context)
        if violations:
            return False, existing_schedule, f"Move violates constraints: {violations[0].message}"

        return True, updated_schedule, "Assignment moved successfully"

    def resolve_conflicts(
        self,
        existing_schedule: List["Assignment"],
        conflicts: List[str],
        context: ConstraintContext,
        indices: ProblemIndices,
    ) -> Tuple[bool, List["Assignment"], List[str]]:
        """
        Attempt to resolve scheduling conflicts.

        Args:
            existing_schedule: Current schedule with conflicts
            conflicts: List of conflict descriptions
            context: Constraint context
            indices: Problem indices

        Returns:
            Tuple of (success, resolved_schedule, remaining_conflicts)
        """
        resolved_schedule = existing_schedule.copy()
        remaining_conflicts = conflicts.copy()

        # Try different resolution strategies
        strategies = [
            self._try_resource_reallocation,
            self._try_time_adjustment,
            self._try_constraint_relaxation,
        ]

        for strategy in strategies:
            resolved_schedule, remaining_conflicts = strategy(
                resolved_schedule, remaining_conflicts, context, indices
            )

            if not remaining_conflicts:
                return True, resolved_schedule, []

        return False, resolved_schedule, remaining_conflicts

    def _schedule_single_occurrence(
        self,
        request,
        occurrence_index: int,
        current_schedule: List["Assignment"],
        context: ConstraintContext,
        indices: ProblemIndices,
    ) -> Optional["Assignment"]:
        """Attempt to schedule a single occurrence."""
        from edusched.domain.assignment import Assignment

        # Generate candidate time slots
        candidates = self._generate_time_candidates(request, occurrence_index, indices)

        for start_time, end_time in candidates:
            # Create tentative assignment
            assignment = Assignment(
                request_id=request.id,
                occurrence_index=occurrence_index,
                start_time=start_time,
                end_time=end_time,
                cohort_id=request.cohort_id,
                assigned_resources={},
            )

            # Try to assign resources
            if self._assign_resources(assignment, context, indices, current_schedule):
                # Check constraints
                if self._check_constraints(assignment, current_schedule, context):
                    return assignment

        return None

    def _generate_time_candidates(
        self, request, occurrence_index: int, indices: ProblemIndices
    ) -> List[Tuple[datetime, datetime]]:
        """Generate candidate time slots for scheduling."""
        candidates = []

        # Get calendar and availability
        calendar = indices.calendar_lookup.get(indices.problem.institutional_calendar_id)
        if not calendar:
            return candidates

        # Generate time slots within date range
        current_date = request.earliest_date.date()
        end_date = request.latest_date.date()
        granularity = calendar.timeslot_granularity

        # Simple implementation - generate daily slots
        while current_date <= end_date:
            # Generate slots from 8 AM to 6 PM
            current_time = datetime.combine(current_date, datetime.min.time().replace(hour=8))
            end_of_day = datetime.combine(current_date, datetime.min.time().replace(hour=18))

            while current_time + request.duration <= end_of_day:
                candidates.append((current_time, current_time + request.duration))
                current_time += granularity + timedelta(minutes=15)  # Buffer between classes

            current_date += timedelta(days=1)

        return candidates

    def _assign_resources(
        self,
        assignment,
        context: ConstraintContext,
        indices: ProblemIndices,
        current_schedule: List["Assignment"],
    ) -> bool:
        """Assign resources to assignment."""
        request = context.request_lookup[assignment.request_id]
        assigned_resources = {}

        # For each required resource type
        if request.required_resource_types:
            for resource_type, count in request.required_resource_types.items():
                available_resources = []

                # Find available resources of this type
                for resource in indices.resources_by_type.get(resource_type, []):
                    if self._is_resource_available(resource, assignment, current_schedule):
                        available_resources.append(resource)

                # Check if we have enough resources
                if len(available_resources) >= count:
                    # Assign the best resources
                    assigned_resources[resource_type] = [r.id for r in available_resources[:count]]
                else:
                    return False

        assignment.assigned_resources = assigned_resources
        return True

    def _is_resource_available(
        self, resource, assignment, current_schedule: List["Assignment"]
    ) -> bool:
        """Check if resource is available at assignment time."""
        # Check against existing assignments
        for existing in current_schedule:
            for resource_ids in existing.assigned_resources.values():
                if resource.id in resource_ids:
                    if (
                        assignment.start_time < existing.end_time
                        and assignment.end_time > existing.start_time
                    ):
                        return False
        return True

    def _check_constraints(self, assignment, current_schedule, context: ConstraintContext) -> bool:
        """Check all constraints for assignment."""
        for constraint in context.problem.constraints:
            violation = constraint.check(assignment, current_schedule, context)
            if violation:
                return False
        return True

    def _check_all_constraints(
        self, schedule: List["Assignment"], context: ConstraintContext
    ) -> List:
        """Check all assignments against all constraints."""
        violations = []
        for assignment in schedule:
            for constraint in context.problem.constraints:
                violation = constraint.check(assignment, schedule, context)
                if violation:
                    violations.append(violation)
        return violations

    def _check_dependencies_on_removal(
        self, course_id: str, context: ConstraintContext
    ) -> List[str]:
        """Check if removing course breaks any dependencies."""
        # Would check for:
        # - Courses that require this as prerequisite
        # - Student dependencies
        # - Teacher minimum load requirements
        return []

    def _try_resource_reallocation(
        self,
        schedule: List["Assignment"],
        conflicts: List[str],
        context: ConstraintContext,
        indices: ProblemIndices,
    ) -> Tuple[List["Assignment"], List[str]]:
        """Try to resolve conflicts by reallocating resources."""
        # Implementation for resource reallocation
        return schedule, conflicts

    def _try_time_adjustment(
        self,
        schedule: List["Assignment"],
        conflicts: List[str],
        context: ConstraintContext,
        indices: ProblemIndices,
    ) -> Tuple[List["Assignment"], List[str]]:
        """Try to resolve conflicts by adjusting times."""
        # Implementation for time adjustment
        return schedule, conflicts

    def _try_constraint_relaxation(
        self,
        schedule: List["Assignment"],
        conflicts: List[str],
        context: ConstraintContext,
        indices: ProblemIndices,
    ) -> Tuple[List["Assignment"], List[str]]:
        """Try to resolve conflicts by relaxing constraints."""
        # Implementation for constraint relaxation
        return schedule, conflicts

    def solve(self, problem: "Problem", **kwargs) -> "Result":
        """Standard solve method - delegates to incremental scheduling."""
        from edusched.domain.result import Result

        # For incremental solving, expect existing_schedule in kwargs
        existing_schedule = kwargs.get("existing_schedule", [])
        modifications = kwargs.get("modifications", [])

        updated_schedule = existing_schedule.copy()
        all_conflicts = []

        # Process modifications
        for mod in modifications:
            if mod["type"] == "add":
                success, new_schedule, conflicts = self.add_course(
                    updated_schedule, mod["request"], context, indices
                )
                if success:
                    updated_schedule = new_schedule
                all_conflicts.extend(conflicts)

            elif mod["type"] == "remove":
                success, new_schedule, conflicts = self.remove_course(
                    updated_schedule, mod["course_id"], context
                )
                if success:
                    updated_schedule = new_schedule
                all_conflicts.extend(conflicts)

            elif mod["type"] == "move":
                success, new_schedule, message = self.move_assignment(
                    updated_schedule, mod["assignment_id"], mod["new_time"], context, indices
                )
                if success:
                    updated_schedule = new_schedule
                else:
                    all_conflicts.append(message)

        # Try to resolve any conflicts
        if all_conflicts:
            success, final_schedule, remaining = self.resolve_conflicts(
                updated_schedule, all_conflicts, context, indices
            )
            if not success:
                status = "partial" if updated_schedule else "infeasible"
            else:
                status = "feasible"
                updated_schedule = final_schedule
                all_conflicts = remaining
        else:
            status = "feasible"

        return Result(
            status=status,
            assignments=updated_schedule,
            unscheduled_requests=[],  # Would calculate based on unscheduled modifications
            backend_used="incremental",
        )

    @property
    def backend_name(self) -> str:
        """Return backend identifier."""
        return "incremental"


class IncrementalState:
    """State tracking for incremental scheduling optimization."""

    def __init__(self, schedule: List["Assignment"]):
        self.schedule = schedule.copy()
        self.schedule_sorted = sorted(schedule, key=lambda a: a.start_time)
        self.resource_usage = self._build_resource_usage_map(schedule)
        self.constraint_cache = {}
        self.last_update = datetime.now()

    def _build_resource_usage_map(
        self, schedule: List["Assignment"]
    ) -> Dict[str, List[Tuple[datetime, datetime]]]:
        """Build resource usage map for efficient conflict checking."""
        usage_map = {}
        for assignment in schedule:
            for resource_ids in assignment.assigned_resources.values():
                for resource_id in resource_ids:
                    if resource_id not in usage_map:
                        usage_map[resource_id] = []
                    # Insert while maintaining sorted order
                    bisect.insort(
                        usage_map[resource_id], (assignment.start_time, assignment.end_time)
                    )
        return usage_map

    def has_resource_conflict(
        self, resource_id: str, start_time: datetime, end_time: datetime
    ) -> bool:
        """Efficiently check for resource conflicts using binary search."""
        if resource_id not in self.resource_usage:
            return False

        usage_times = self.resource_usage[resource_id]
        # Find insertion point using binary search
        i = bisect.bisect_left(usage_times, (start_time, end_time))

        # Check neighboring intervals for conflicts
        # Check previous interval
        if i > 0:
            prev_start, prev_end = usage_times[i - 1]
            if start_time < prev_end:
                return True

        # Check current interval
        if i < len(usage_times):
            curr_start, curr_end = usage_times[i]
            if end_time > curr_start:
                return True

        return False

    def add_assignment(self, assignment: "Assignment") -> None:
        """Add assignment and update state."""
        bisect.insort(self.schedule_sorted, assignment)
        self.schedule.append(assignment)

        # Update resource usage
        for resource_ids in assignment.assigned_resources.values():
            for resource_id in resource_ids:
                if resource_id not in self.resource_usage:
                    self.resource_usage[resource_id] = []
                bisect.insort(
                    self.resource_usage[resource_id], (assignment.start_time, assignment.end_time)
                )

        # Clear affected constraint cache
        self._invalidate_constraint_cache(assignment)

        self.last_update = datetime.now()

    def remove_assignment(self, assignment: "Assignment") -> None:
        """Remove assignment and update state."""
        # Remove from sorted schedule
        i = bisect.bisect_left(self.schedule_sorted, (assignment.start_time, assignment.end_time))
        while i < len(self.schedule_sorted):
            if (
                self.schedule_sorted[i].start_time == assignment.start_time
                and self.schedule_sorted[i].end_time == assignment.end_time
            ):
                del self.schedule_sorted[i]
                break
            i += 1

        # Remove from schedule
        if assignment in self.schedule:
            self.schedule.remove(assignment)

        # Update resource usage
        for resource_ids in assignment.assigned_resources.values():
            for resource_id in resource_ids:
                if resource_id in self.resource_usage:
                    # Find and remove the interval
                    i = bisect.bisect_left(
                        self.resource_usage[resource_id],
                        (assignment.start_time, assignment.end_time),
                    )
                    while i < len(self.resource_usage[resource_id]):
                        if (
                            self.resource_usage[resource_id][i][0] == assignment.start_time
                            and self.resource_usage[resource_id][i][1] == assignment.end_time
                        ):
                            del self.resource_usage[resource_id][i]
                            break
                        i += 1

        # Clear affected constraint cache
        self._invalidate_constraint_cache(assignment)

        self.last_update = datetime.now()

    def _invalidate_constraint_cache(self, assignment: "Assignment") -> None:
        """Invalidate constraint cache for affected resources."""
        affected_resources = set()
        for resource_ids in assignment.assigned_resources.values():
            affected_resources.update(resource_ids)

        # Remove cache entries for affected resources
        keys_to_remove = []
        for key in self.constraint_cache:
            if any(r in key for r in affected_resources):
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.constraint_cache[key]


class FastIncrementalSolver(IncrementalSolver):
    """Enhanced incremental solver with fast delta updates."""

    def __init__(self, max_attempts: int = 1000, enable_caching: bool = True):
        super().__init__(max_attempts)
        self.enable_caching = enable_caching
        self.state_cache: Dict[str, IncrementalState] = {}

    def add_course_fast(
        self,
        existing_schedule: List["Assignment"],
        new_request,
        context: ConstraintContext,
        indices: ProblemIndices,
    ) -> Tuple[bool, List["Assignment"], List[str]]:
        """
        Fast addition using delta updates and cached state.
        """
        # Get or create cached state
        cache_key = self._generate_cache_key(existing_schedule)
        if cache_key not in self.state_cache:
            self.state_cache[cache_key] = IncrementalState(existing_schedule)

        state = self.state_cache[cache_key]

        # Try to schedule using fast path
        assignments = []
        conflicts = []

        for occurrence_index in range(new_request.number_of_occurrences):
            assignment = self._schedule_single_occurrence_fast(
                new_request, occurrence_index, state, context, indices
            )

            if assignment:
                assignments.append(assignment)
                state.add_assignment(assignment)
            else:
                conflicts.append(f"Occurrence {occurrence_index + 1} of {new_request.id}")

        # Update schedule if successful
        if assignments:
            updated_schedule = existing_schedule + assignments
            self.state_cache[cache_key] = state
            return True, updated_schedule, conflicts

        return False, existing_schedule, conflicts

    def _schedule_single_occurrence_fast(
        self,
        request,
        occurrence_index: int,
        state: IncrementalState,
        context: ConstraintContext,
        indices: ProblemIndices,
    ) -> Optional["Assignment"]:
        """Fast single occurrence scheduling using cached state."""
        from edusched.domain.assignment import Assignment

        # Generate prioritized candidates
        candidates = self._generate_prioritized_candidates(
            request, occurrence_index, indices, context
        )

        for start_time, end_time, _priority_score in candidates:
            # Create tentative assignment
            assignment = Assignment(
                request_id=request.id,
                occurrence_index=occurrence_index,
                start_time=start_time,
                end_time=end_time,
                cohort_id=request.cohort_id,
                assigned_resources={},
            )

            # Fast resource assignment using state
            if self._assign_resources_fast(assignment, context, indices, state):
                # Fast constraint check using cache
                if self._check_constraints_fast(assignment, context, state):
                    return assignment

        return None

    def _generate_prioritized_candidates(
        self, request, occurrence_index: int, indices: ProblemIndices, context: ConstraintContext
    ) -> List[Tuple[datetime, datetime, float]]:
        """Generate time slot candidates with priority scores."""
        candidates = []
        calendar = indices.calendar_lookup.get(indices.problem.institutional_calendar_id)

        if not calendar:
            return candidates

        # Consider preferred times first
        preferred_times = getattr(request, "preferred_time_slots", [])
        preferred_set = set()

        if preferred_times:
            for pref in preferred_times:
                # Convert to datetime objects
                # This is simplified - would need proper date/time handling
                preferred_set.add((pref.get("start"), pref.get("end")))

        # Generate candidates
        current_date = request.earliest_date.date()
        end_date = request.latest_date.date()

        while current_date <= end_date:
            # Generate slots from 8 AM to 6 PM
            current_time = datetime.combine(current_date, datetime.min.time().replace(hour=8))
            end_of_day = datetime.combine(current_date, datetime.min.time().replace(hour=18))

            while current_time + request.duration <= end_of_day:
                start_time = current_time
                end_time = current_time + request.duration

                # Calculate priority score
                score = 1.0  # Base score
                if (start_time.time(), end_time.time()) in preferred_set:
                    score += 2.0  # Bonus for preferred times

                # Add bonus for less busy times (using state)
                # This would check resource usage patterns
                score += self._calculate_time_slot_score(start_time, end_time, context)

                candidates.append((start_time, end_time, score))

                current_time += calendar.timeslot_granularity + timedelta(minutes=15)

            current_date += timedelta(days=1)

        # Sort by priority score (descending)
        candidates.sort(key=lambda x: x[2], reverse=True)

        # Return top candidates (limit for performance)
        return candidates[:50]

    def _assign_resources_fast(
        self,
        assignment,
        context: ConstraintContext,
        indices: ProblemIndices,
        state: IncrementalState,
    ) -> bool:
        """Fast resource assignment using cached state."""
        request = context.request_lookup[assignment.request_id]
        assigned_resources = {}

        if request.required_resource_types:
            for resource_type, count in request.required_resource_types.items():
                # Get available resources with fast conflict checking
                available_resources = []
                for resource in indices.resources_by_type.get(resource_type, []):
                    if not state.has_resource_conflict(
                        resource.id, assignment.start_time, assignment.end_time
                    ):
                        available_resources.append(resource)

                if len(available_resources) >= count:
                    assigned_resources[resource_type] = [r.id for r in available_resources[:count]]
                else:
                    return False

        assignment.assigned_resources = assigned_resources
        return True

    def _check_constraints_fast(
        self, assignment, context: ConstraintContext, state: IncrementalState
    ) -> bool:
        """Fast constraint checking using cache."""
        # Create cache key
        cache_key = f"{assignment.start_time}_{assignment.end_time}"
        for resource_ids in assignment.assigned_resources.values():
            cache_key += f"_{','.join(resource_ids)}"

        # Check cache first
        if self.enable_caching and cache_key in state.constraint_cache:
            cached_result = state.constraint_cache[cache_key]
            # Check if cache is still valid (based on last update)
            if cached_result["valid_until"] > datetime.now():
                return cached_result["result"]

        # Check constraints
        result = True
        for constraint in context.problem.constraints:
            violation = constraint.check(assignment, state.schedule, context)
            if violation:
                result = False
                break

        # Cache result
        if self.enable_caching:
            state.constraint_cache[cache_key] = {
                "result": result,
                "valid_until": datetime.now() + timedelta(minutes=5),
            }

        return result

    def _calculate_time_slot_score(
        self, start_time: datetime, end_time: datetime, context: ConstraintContext
    ) -> float:
        """Calculate score for time slot based on current usage."""
        # This would analyze resource usage patterns
        # For now, return a simple score based on time of day
        hour = start_time.hour

        # Preferred hours (10 AM - 2 PM)
        if 10 <= hour <= 14:
            return 1.0
        # Morning hours
        elif 8 <= hour < 10:
            return 0.7
        # Late afternoon
        elif 14 < hour <= 17:
            return 0.5
        # Other times
        else:
            return 0.2

    def _generate_cache_key(self, schedule: List["Assignment"]) -> str:
        """Generate cache key for schedule state."""
        # Simple hash based on assignment count and times
        return f"schedule_{len(schedule)}_{hash(tuple(a.start_time for a in schedule))}"


class BatchIncrementalSolver(FastIncrementalSolver):
    """Batch processing for multiple incremental changes."""

    def __init__(self, max_attempts: int = 1000, enable_caching: bool = True, batch_size: int = 10):
        super().__init__(max_attempts, enable_caching)
        self.batch_size = batch_size

    def process_changes_batch(
        self,
        existing_schedule: List["Assignment"],
        changes: List[Dict],
        context: ConstraintContext,
        indices: ProblemIndices,
    ) -> Tuple[bool, List["Assignment"], List[str]]:
        """
        Process multiple changes in batch for better efficiency.
        """
        updated_schedule = existing_schedule.copy()
        all_conflicts = []

        # Group changes by type for batch processing
        additions = [c for c in changes if c["type"] == "add"]
        removals = [c for c in changes if c["type"] == "remove"]
        moves = [c for c in changes if c["type"] == "move"]

        # Process removals first (frees up resources)
        for change in removals:
            success, new_schedule, conflicts = self.remove_course(
                updated_schedule, change["course_id"], context
            )
            if success:
                updated_schedule = new_schedule
            all_conflicts.extend(conflicts)

        # Process additions in batches
        for i in range(0, len(additions), self.batch_size):
            batch = additions[i : i + self.batch_size]
            for change in batch:
                success, new_schedule, conflicts = self.add_course_fast(
                    updated_schedule, change["request"], context, indices
                )
                if success:
                    updated_schedule = new_schedule
                all_conflicts.extend(conflicts)

            # Resolve conflicts after each batch
            if all_conflicts:
                success, resolved_schedule, remaining = self.resolve_conflicts(
                    updated_schedule, all_conflicts, context, indices
                )
                if success:
                    updated_schedule = resolved_schedule
                    all_conflicts = remaining
                else:
                    # Continue with partial success
                    break

        # Process moves
        for change in moves:
            success, new_schedule, message = self.move_assignment(
                updated_schedule, change["assignment_id"], change["new_time"], context, indices
            )
            if success:
                updated_schedule = new_schedule
            else:
                all_conflicts.append(message)

        return (updated_schedule != existing_schedule, updated_schedule, all_conflicts)
