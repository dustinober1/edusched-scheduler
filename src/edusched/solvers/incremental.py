"""Incremental scheduling solver for adding/removing courses without full reschedule."""

from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from copy import deepcopy

from edusched.solvers.base import SolverBackend
from edusched.constraints.base import ConstraintContext

from edusched.domain.problem import ProblemIndices

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
        indices: ProblemIndices
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
        from edusched.domain.assignment import Assignment

        updated_schedule = existing_schedule.copy()
        conflicts = []

        # Try to schedule all occurrences of the new course
        for occurrence_index in range(new_request.number_of_occurrences):
            assignment = self._schedule_single_occurrence(
                new_request,
                occurrence_index,
                updated_schedule,
                context,
                indices
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
        self,
        existing_schedule: List["Assignment"],
        course_id: str,
        context: ConstraintContext
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
        indices: ProblemIndices
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
            if hasattr(assignment, 'id') and assignment.id == assignment_id:
                assignment_to_move = assignment
                break
            elif hasattr(assignment, 'occurrence_index'):
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
            assigned_resources=assignment_to_move.assigned_resources.copy()
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
        indices: ProblemIndices
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
            self._try_constraint_relaxation
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
        indices: ProblemIndices
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
                assigned_resources={}
            )

            # Try to assign resources
            if self._assign_resources(assignment, context, indices, current_schedule):
                # Check constraints
                if self._check_constraints(assignment, current_schedule, context):
                    return assignment

        return None

    def _generate_time_candidates(
        self,
        request,
        occurrence_index: int,
        indices: ProblemIndices
    ) -> List[Tuple[datetime, datetime]]:
        """Generate candidate time slots for scheduling."""
        candidates = []

        # Get calendar and availability
        calendar = indices.calendar_lookup.get(
            indices.problem.institutional_calendar_id
        )
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
        current_schedule: List["Assignment"]
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
                    if self._is_resource_available(
                        resource, assignment, current_schedule
                    ):
                        available_resources.append(resource)

                # Check if we have enough resources
                if len(available_resources) >= count:
                    # Assign the best resources
                    assigned_resources[resource_type] = [
                        r.id for r in available_resources[:count]
                    ]
                else:
                    return False

        assignment.assigned_resources = assigned_resources
        return True

    def _is_resource_available(
        self,
        resource,
        assignment,
        current_schedule: List["Assignment"]
    ) -> bool:
        """Check if resource is available at assignment time."""
        # Check against existing assignments
        for existing in current_schedule:
            for resource_ids in existing.assigned_resources.values():
                if resource.id in resource_ids:
                    if assignment.start_time < existing.end_time and assignment.end_time > existing.start_time:
                        return False
        return True

    def _check_constraints(
        self,
        assignment,
        current_schedule,
        context: ConstraintContext
    ) -> bool:
        """Check all constraints for assignment."""
        for constraint in context.problem.constraints:
            violation = constraint.check(assignment, current_schedule, context)
            if violation:
                return False
        return True

    def _check_all_constraints(
        self,
        schedule: List["Assignment"],
        context: ConstraintContext
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
        self,
        course_id: str,
        context: ConstraintContext
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
        indices: ProblemIndices
    ) -> Tuple[List["Assignment"], List[str]]:
        """Try to resolve conflicts by reallocating resources."""
        # Implementation for resource reallocation
        return schedule, conflicts

    def _try_time_adjustment(
        self,
        schedule: List["Assignment"],
        conflicts: List[str],
        context: ConstraintContext,
        indices: ProblemIndices
    ) -> Tuple[List["Assignment"], List[str]]:
        """Try to resolve conflicts by adjusting times."""
        # Implementation for time adjustment
        return schedule, conflicts

    def _try_constraint_relaxation(
        self,
        schedule: List["Assignment"],
        conflicts: List[str],
        context: ConstraintContext,
        indices: ProblemIndices
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
                    updated_schedule, mod["assignment_id"],
                    mod["new_time"], context, indices
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
            backend_used="incremental"
        )

    @property
    def backend_name(self) -> str:
        """Return backend identifier."""
        return "incremental"