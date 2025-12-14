"""Heuristic solver backend implementation."""

import random
import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Dict, List, Optional, Set
from zoneinfo import ZoneInfo

from edusched.solvers.base import SolverBackend
from edusched.utils.scheduling_utils import OccurrenceSpreader

if TYPE_CHECKING:
    from edusched.constraints.base import ConstraintContext
    from edusched.domain.assignment import Assignment
    from edusched.domain.problem import Problem, ProblemIndices
    from edusched.domain.result import Result
    from edusched.domain.session_request import SessionRequest


class HeuristicSolver(SolverBackend):
    """Greedy heuristic solver backend."""

    def __init__(self, max_attempts: int = 1000):
        self.max_attempts = max_attempts
        self.spreader = None  # Will be initialized with holiday calendar

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
        from edusched.domain.result import Result

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

        # Initialize occurrence spreader with holiday calendar
        if problem.holiday_calendar:
            self.spreader = OccurrenceSpreader(problem.holiday_calendar)
        else:
            # Create default holiday calendar if none provided
            from edusched.domain.holiday_calendar import HolidayCalendar

            current_year = datetime.now().year
            default_calendar = HolidayCalendar(
                id="default_academic",
                name="Default Academic Calendar",
                year=current_year,
                excluded_weekdays={5, 6},  # Weekends
            )
            self.spreader = OccurrenceSpreader(default_calendar)

        # Create constraint context
        context = self._create_context(problem, indices)

        # Start with locked assignments
        solution = problem.locked_assignments.copy()

        # Try to schedule each request
        unscheduled = []
        scheduled_requests: Set[str] = {a.request_id for a in solution}

        # Sort requests by priority using new priority system (longer classes first)
        requests_to_schedule = [r for r in problem.requests if r.id not in scheduled_requests]
        requests_to_schedule = self.spreader.sort_requests_by_priority(requests_to_schedule)

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
                diagnostics = self._generate_infeasibility_report(unscheduled, problem, context)
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

    def _create_context(self, problem: "Problem", indices: "ProblemIndices") -> "ConstraintContext":
        """Create constraint context for checking constraints."""
        from edusched.constraints.base import ConstraintContext

        return ConstraintContext(
            problem=problem,
            resource_lookup=indices.resource_lookup,
            calendar_lookup=indices.calendar_lookup,
            request_lookup=indices.request_lookup,
            building_lookup=indices.building_lookup,
            department_lookup=indices.department_lookup,
            teacher_lookup=indices.teacher_lookup,
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
        Try to schedule a single occurrence of a request using pattern-based scheduling.
        """
        from edusched.domain.assignment import Assignment

        # Get calendar for granularity
        calendar = context.calendar_lookup.get(context.problem.institutional_calendar_id)
        if calendar:
            granularity = calendar.timeslot_granularity
        else:
            granularity = timedelta(minutes=15)  # Default

        # Generate spread-out occurrence dates if this is the first occurrence
        if occurrence_index == 0:
            schedule_dates = self.spreader.generate_occurrence_dates(
                request, calendar.timezone if hasattr(calendar, "timezone") else ZoneInfo("UTC")
            )
        else:
            # For subsequent occurrences, find the next available date
            schedule_dates = self._find_next_available_dates(
                request,
                solution,
                calendar.timezone if hasattr(calendar, "timezone") else ZoneInfo("UTC"),
            )

        # Try each date in the preferred order (try more dates to handle conflicts)
        for schedule_date in schedule_dates[:10]:  # Try up to 10 dates
            # Get available time slots for this date
            time_slots = self.spreader.generate_time_slots(
                schedule_date,
                request,
                granularity,
                calendar.timezone if hasattr(calendar, "timezone") else ZoneInfo("UTC"),
            )

            # Try each time slot
            for start_time, end_time in time_slots:
                # Create tentative assignment
                assignment = Assignment(
                    request_id=request.id,
                    occurrence_index=occurrence_index,
                    start_time=start_time,
                    end_time=end_time,
                    cohort_id=request.cohort_id,
                )

                # Try to assign resources
                if self._assign_resources(assignment, context, indices, solution):
                    # Check all constraints
                    if self._check_constraints(assignment, solution, context):
                        return assignment

        return None

    def _find_next_available_dates(
        self, request: "SessionRequest", solution: List["Assignment"], timezone: ZoneInfo
    ) -> List:
        """Find next available dates for additional occurrences."""

        # Get existing assignments for this request
        existing_dates = [a.start_time.date() for a in solution if a.request_id == request.id]

        # Generate all possible dates within range
        all_dates = self.spreader.holiday_calendar.get_available_days_in_range(
            request.earliest_date.date(), request.latest_date.date()
        )

        # Get allowed pattern days
        pattern = request.scheduling_pattern or "5days"
        pattern_days = self.spreader.holiday_calendar.get_weekly_pattern_days(pattern)

        # Filter to only pattern-matching dates that aren't already used
        available_dates = [
            d for d in all_dates if d not in existing_dates and d.weekday() in pattern_days
        ]

        # Sort to spread out from existing dates (prefer dates farther from already scheduled)
        if existing_dates:
            # Sort by maximum distance from any existing date (prefer spread-out dates)
            available_dates.sort(key=lambda d: -min(abs((d - ed).days) for ed in existing_dates))
        else:
            available_dates.sort()  # Just chronological if no existing dates

        return available_dates[:10]  # Return up to 10 candidate dates

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
        from edusched.utils.capacity_utils import check_capacity_fit

        request = context.request_lookup[assignment.request_id]

        # For each resource type needed, find suitable resource
        assigned_resources: Dict[str, List[str]] = {}

        # Group resources by type
        for resource_type, resources in indices.resources_by_type.items():
            # Find resources that satisfy requirements and are available
            suitable_resources = []
            for resource in resources:
                if resource.can_satisfy(request.required_attributes):
                    # Check capacity for classrooms
                    if resource_type == "classroom" and request.modality != "online":
                        # Skip if no capacity info
                        if resource.capacity is None:
                            continue

                        # Check if classroom can fit the enrollment
                        can_fit, _ = check_capacity_fit(
                            resource,
                            request.enrollment_count,
                            request.min_capacity or 0,
                            request.max_capacity,
                            buffer_percent=0.1,  # 10% buffer
                        )
                        if not can_fit:
                            continue

                    # Check availability if calendar specified
                    if resource.availability_calendar_id:
                        calendar = context.calendar_lookup[resource.availability_calendar_id]
                        if not calendar.is_available(assignment.start_time, assignment.end_time):
                            continue

                    # Check if not already booked
                    if self._is_resource_available(
                        resource.id, assignment, context, current_solution
                    ):
                        suitable_resources.append(resource)

            if suitable_resources:
                # Sort by efficiency for classrooms (closest fit to required capacity)
                if resource_type == "classroom" and request.modality != "online":
                    from edusched.utils.capacity_utils import calculate_efficiency_score

                    required_capacity = max(request.enrollment_count, request.min_capacity or 0)
                    required_with_buffer = int(required_capacity * 1.1)  # 10% buffer

                    suitable_resources.sort(
                        key=lambda r: calculate_efficiency_score(
                            context.resource_lookup[r.id].capacity or 0,
                            required_with_buffer,
                            request.max_capacity,
                        ),
                        reverse=True,
                    )

                # Assign the best resource
                assigned_resources[resource_type] = [suitable_resources[0].id]

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
        from datetime import timedelta

        # Get setup/cleanup time requirements
        setup_minutes = 15  # Default setup time
        cleanup_minutes = 10  # Default cleanup time

        # Check if teacher has specific setup requirements
        request = context.request_lookup.get(assignment.request_id)
        if request and request.teacher_id:
            teacher = context.teacher_lookup.get(request.teacher_id)
            if teacher:
                setup_minutes = teacher.setup_time_minutes
                cleanup_minutes = teacher.cleanup_time_minutes

        # Check against existing solution (including locked assignments)
        # Include setup/cleanup buffer times
        assignment_start = assignment.start_time - timedelta(minutes=setup_minutes)
        assignment_end = assignment.end_time + timedelta(minutes=cleanup_minutes)

        for existing in solution:
            for resource_ids in existing.assigned_resources.values():
                if resource_id in resource_ids:
                    # Also add buffer for existing assignment
                    existing_setup = 15
                    existing_cleanup = 10
                    if existing.request_id != assignment.request_id:
                        existing_request = context.request_lookup.get(existing.request_id)
                        if existing_request and existing_request.teacher_id:
                            existing_teacher = context.teacher_lookup.get(
                                existing_request.teacher_id
                            )
                            if existing_teacher:
                                existing_setup = existing_teacher.setup_time_minutes
                                existing_cleanup = existing_teacher.cleanup_time_minutes

                    existing_start = existing.start_time - timedelta(minutes=existing_setup)
                    existing_end = existing.end_time + timedelta(minutes=existing_cleanup)

                    if assignment_start < existing_end and assignment_end > existing_start:
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
            minutes_since_midnight = current.hour * 60 + current.minute + current.second / 60
            granularity_minutes = granularity.total_seconds() / 60

            # Find next aligned time
            next_minutes = (
                (minutes_since_midnight // granularity_minutes) + 1
            ) * granularity_minutes
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
                "Time window constraints too tight",
            ],
        )

    @property
    def backend_name(self) -> str:
        """Return backend identifier."""
        return "heuristic"
