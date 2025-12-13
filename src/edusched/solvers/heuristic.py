"""Heuristic solver backend implementation."""

import random
import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Dict, List, Optional, Set

from edusched.solvers.base import SolverBackend

if TYPE_CHECKING:
    from edusched.constraints.base import Constraint, ConstraintContext
    from edusched.domain.assignment import Assignment
    from edusched.domain.calendar import Calendar
    from edusched.domain.problem import Problem, ProblemIndices
    from edusched.domain.resource import Resource
    from edusched.domain.result import Result
    from edusched.domain.session_request import SessionRequest
    from edusched.errors import BackendError


class HeuristicSolver(SolverBackend):
    """Greedy heuristic solver backend."""

    def __init__(self, max_attempts: int = 1000):
        self.max_attempts = max_attempts

    def solve(
        self,
        problem: "Problem",
        seed: Optional[int] = None,
        fallback: bool = False,
    ) -> "Result":
        """
        Solve scheduling problem using greedy heuristic.

        Args:
            problem: The scheduling problem to solve
            seed: Random seed for deterministic results
            fallback: Whether to fall back on failure

        Returns:
            Result object with scheduling solution
        """
        from edusched.domain.assignment import Assignment
        from edusched.domain.result import Result, InfeasibilityReport

        start_time = time.time()

        # Set seed for determinism
        if seed is not None:
            random.seed(seed)

        # Validate problem
        errors = problem.validate()
        if errors:
            from edusched.errors import ValidationError
            raise ValidationError(f"Problem validation failed: {'; '.join(errors)}")

        # Canonicalize and build indices
        problem.canonicalize()
        indices = problem.build_indices()

        # Create constraint context
        context = self._create_context(problem, indices)

        # Start with locked assignments
        solution = problem.locked_assignments.copy()

        # Try to schedule each request
        unscheduled = []
        scheduled_requests: Set[str] = set(a.request_id for a in solution)

        # Sort requests by priority (earliest latest_date first for more constrained)
        requests_to_schedule = [
            r for r in problem.requests if r.id not in scheduled_requests
        ]
        requests_to_schedule.sort(key=lambda r: r.latest_date)

        for request in requests_to_schedule:
            scheduled_occurrences = 0

            # Try to schedule each occurrence
            for occurrence_index in range(request.number_of_occurrences):
                assignment = self._schedule_occurrence(
                    request, occurrence_index, solution, context, indices
                )

                if assignment:
                    solution.append(assignment)
                    scheduled_occurrences += 1
                else:
                    # Couldn't schedule this occurrence
                    break

            if scheduled_occurrences == 0:
                unscheduled.append(request.id)

        # Check if all requests were scheduled
        if unscheduled:
            if not fallback:
                # Generate infeasibility report
                diagnostics = self._generate_infeasibility_report(
                    unscheduled, problem, context
                )
                return Result(
                    status="infeasible" if len(unscheduled) == len(problem.requests) else "partial",
                    assignments=solution,
                    unscheduled_requests=unscheduled,
                    backend_used=self.backend_name,
                    seed_used=seed,
                    solve_time_seconds=time.time() - start_time,
                    diagnostics=diagnostics,
                )
            else:
                # With fallback, return partial solution
                return Result(
                    status="partial",
                    assignments=solution,
                    unscheduled_requests=unscheduled,
                    backend_used=self.backend_name,
                    seed_used=seed,
                    solve_time_seconds=time.time() - start_time,
                )

        # Calculate objective scores
        objective_score = self._calculate_objectives(problem.objectives, solution)

        return Result(
            status="feasible",
            assignments=solution,
            unscheduled_requests=[],
            objective_score=objective_score,
            backend_used=self.backend_name,
            seed_used=seed,
            solve_time_seconds=time.time() - start_time,
        )

    def _create_context(
        self, problem: "Problem", indices: "ProblemIndices"
    ) -> "ConstraintContext":
        """Create constraint context for checking constraints."""
        from edusched.constraints.base import ConstraintContext

        return ConstraintContext(
            problem=problem,
            resource_lookup=indices.resource_lookup,
            calendar_lookup=indices.calendar_lookup,
            request_lookup=indices.request_lookup,
            building_lookup=indices.building_lookup,
        )

    def _schedule_occurrence(
        self,
        request: "SessionRequest",
        occurrence_index: int,
        solution: List["Assignment"],
        context: "ConstraintContext",
        indices: "ProblemIndices",
    ) -> Optional["Assignment"]:
        """
        Try to schedule a single occurrence of a request.

        Uses greedy approach with backtracking support.
        """
        from edusched.domain.assignment import Assignment

        # Generate candidate timeslots aligned with calendar granularity
        calendar = context.calendar_lookup.get(context.problem.institutional_calendar_id)
        if calendar:
            granularity = calendar.timeslot_granularity
        else:
            granularity = timedelta(minutes=15)  # Default

        # Start from earliest_date, try timeslots aligned to granularity
        current = request.earliest_date
        attempts = 0

        while current <= request.latest_date and attempts < self.max_attempts:
            # Check if this timeslot is available
            end_time = current + request.duration

            # Create tentative assignment
            assignment = Assignment(
                request_id=request.id,
                occurrence_index=occurrence_index,
                start_time=current,
                end_time=end_time,
                cohort_id=request.cohort_id,
            )

            # Try to assign resources
            if self._assign_resources(assignment, context, indices, solution):
                # Check all constraints
                if self._check_constraints(assignment, solution, context):
                    return assignment

            # Move to next aligned timeslot
            current = self._next_aligned_timeslot(current, granularity, request.latest_date)
            attempts += 1

        return None

    def _assign_resources(
        self,
        assignment: "Assignment",
        context: "ConstraintContext",
        indices: "ProblemIndices",
        current_solution: List["Assignment"],
    ) -> bool:
        """
        Assign appropriate resources to an assignment.

        Returns True if successful assignment found, False otherwise.
        """
        request = context.request_lookup[assignment.request_id]

        # For each resource type needed, find suitable resource
        assigned_resources: Dict[str, List[str]] = {}

        # Group resources by type
        for resource_type, resources in indices.resources_by_type.items():
            # Find resources that satisfy requirements and are available
            suitable_resources = []
            for resource in resources:
                if resource.can_satisfy(request.required_attributes):
                    # Check availability if calendar specified
                    if resource.availability_calendar_id:
                        calendar = context.calendar_lookup[resource.availability_calendar_id]
                        if not calendar.is_available(assignment.start_time, assignment.end_time):
                            continue

                    # Check if not already booked
                    if self._is_resource_available(resource.id, assignment, context, current_solution):
                        suitable_resources.append(resource.id)

            if suitable_resources:
                # For simplicity, just take the first available
                # In a more sophisticated implementation, we might balance load
                assigned_resources[resource_type] = [suitable_resources[0]]

        if assigned_resources:
            assignment.assigned_resources = assigned_resources
            return True

        return False

    def _is_resource_available(
        self,
        resource_id: str,
        assignment: "Assignment",
        context: "ConstraintContext",
        solution: List["Assignment"],
    ) -> bool:
        """Check if resource is available during the assignment period."""
        # Check against existing solution (including locked assignments)
        for existing in solution:
            for resource_ids in existing.assigned_resources.values():
                if resource_id in resource_ids:
                    if assignment.start_time < existing.end_time and assignment.end_time > existing.start_time:
                        return False
        return True

    def _check_constraints(
        self,
        assignment: "Assignment",
        solution: List["Assignment"],
        context: "ConstraintContext",
    ) -> bool:
        """Check all constraints against the assignment."""
        for constraint in context.problem.constraints:
            violation = constraint.check(assignment, solution, context)
            if violation:
                return False
        return True

    def _next_aligned_timeslot(
        self, current: datetime, granularity: timedelta, max_date: datetime
    ) -> datetime:
        """Get next timeslot aligned to granularity."""
        # Round up to next granularity boundary
        if granularity.total_seconds() > 0:
            # Calculate minutes since midnight
            minutes_since_midnight = (
                current.hour * 60 + current.minute + current.second / 60
            )
            granularity_minutes = granularity.total_seconds() / 60

            # Find next aligned time
            next_minutes = ((minutes_since_midnight // granularity_minutes) + 1) * granularity_minutes
            next_hour = int(next_minutes // 60)
            next_minute = int(next_minutes % 60)

            next_time = current.replace(
                hour=next_hour % 24, minute=next_minute, second=0, microsecond=0
            )

            # If we've passed midnight, move to next day
            if next_hour >= 24:
                days_to_add = int(next_hour // 24)
                next_time += timedelta(days=days_to_add)

            return next_time

        return current + timedelta(minutes=15)

    def _calculate_objectives(
        self, objectives: List["Objective"], solution: List["Assignment"]
    ) -> float:
        """Calculate weighted objective score."""
        if not objectives:
            return None

        total_score = 0.0
        total_weight = 0.0

        for objective in objectives:
            score = objective.score(solution)
            total_score += score * objective.weight
            total_weight += objective.weight

        return total_score / total_weight if total_weight > 0 else None

    def _generate_infeasibility_report(
        self,
        unscheduled: List[str],
        problem: "Problem",
        context: "ConstraintContext",
    ) -> "InfeasibilityReport":
        """Generate a report explaining why scheduling failed."""
        from edusched.domain.result import InfeasibilityReport

        # Simple report - could be enhanced with specific constraint violations
        return InfeasibilityReport(
            unscheduled_requests=unscheduled,
            violated_constraints_summary={
                "resource_availability": len(unscheduled),
                "time_constraints": len(unscheduled),
            },
            top_conflicts=[
                f"Insufficient resources for {len(unscheduled)} requests",
                f"Time window constraints too tight",
            ],
        )

    @property
    def backend_name(self) -> str:
        """Return backend identifier."""
        return "heuristic"
