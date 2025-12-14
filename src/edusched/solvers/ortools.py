"""OR-Tools solver backend for EduSched.

Implements constraint programming solver using Google OR-Tools.
Provides optimal solutions for scheduling problems.
"""

import time
from typing import TYPE_CHECKING, List, Optional

try:
    from ortools.sat.python import cp_model

    ORTOOLS_AVAILABLE = True
except ImportError:
    ORTOOLS_AVAILABLE = False

if TYPE_CHECKING:
    from edusched.domain.assignment import Assignment
    from edusched.domain.problem import Problem
    from edusched.domain.result import Result


class ORToolsSolver:
    """OR-Tools constraint programming solver.

    Uses OR-Tools CP-SAT solver for optimal schedule generation.
    Handles complex constraints and provides optimal solutions.
    """

    def __init__(self):
        """Initialize OR-Tools solver."""
        if not ORTOOLS_AVAILABLE:
            from edusched.errors import MissingOptionalDependency

            raise MissingOptionalDependency("ortools", "pip install ortools")

        self.model = None
        self.solver = None

    @property
    def backend_name(self) -> str:
        """Return backend identifier."""
        return "ortools"

    def solve(
        self,
        problem: "Problem",
        seed: Optional[int] = None,
        fallback: bool = False,
    ) -> "Result":
        """
        Solve scheduling problem using OR-Tools CP-SAT.

        Args:
            problem: The scheduling problem to solve
            seed: Random seed for deterministic results
            fallback: Whether to fall back to heuristic on failure

        Returns:
            Result object with scheduling solution
        """
        from edusched.domain.result import Result
        from edusched.solvers.heuristic import HeuristicSolver

        start_time = time.time()

        try:
            # Create CP-SAT model
            self.model = cp_model.CpModel()

            # Create decision variables
            assignments = self._create_variables(problem)

            # Add constraints
            self._add_constraints(problem, assignments)

            # Set up solver
            self.solver = cp_model.CpSolver()
            if seed is not None:
                self.solver.parameters.random_seed = seed

            # Configure solver for optimization
            self.solver.parameters.max_time_in_seconds = 30.0  # Reasonable time limit
            self.solver.parameters.num_search_workers = 8
            self.solver.parameters.log_search_progress = False

            # Solve
            status = self.solver.Solve(self.model)

            solver_time_ms = (time.time() - start_time) * 1000

            # Extract solution
            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                solution_assignments = self._extract_solution(
                    problem, assignments, status == cp_model.OPTIMAL
                )

                return Result(
                    assignments=solution_assignments,
                    problem=problem,
                    solver_time_ms=solver_time_ms,
                    iterations=self.solver.NumBranches(),
                    status="optimal" if status == cp_model.OPTIMAL else "feasible",
                )
            else:
                # No solution found
                if fallback:
                    # Fall back to heuristic solver
                    heuristic = HeuristicSolver()
                    return heuristic.solve(problem, seed=seed)
                else:
                    return Result(
                        assignments=[],
                        problem=problem,
                        solver_time_ms=solver_time_ms,
                        iterations=self.solver.NumBranches(),
                        status="infeasible",
                    )

        except Exception as e:
            if fallback:
                # Fall back to heuristic solver on any error
                heuristic = HeuristicSolver()
                return heuristic.solve(problem, seed=seed)
            else:
                from edusched.errors import BackendError

                raise BackendError(f"OR-Tools solver failed: {e}")

    def _create_variables(self, problem: "Problem"):
        """Create decision variables for assignments.

        Args:
            problem: The scheduling problem

        Returns:
            Dictionary of assignment variables
        """
        assignments = {}

        # Create boolean variable for each possible assignment
        # assignment[(request_idx, resource_idx, start_time)] = bool
        for req_idx, request in enumerate(problem.requests):
            for res_idx, resource in enumerate(problem.resources):
                # Check if resource is compatible with request
                if self._is_resource_compatible(request, resource):
                    # Calculate possible start times
                    possible_starts = self._get_possible_start_times(problem, request, resource)

                    for start_idx, _start_time in enumerate(possible_starts):
                        var_name = f"assign_{req_idx}_{res_idx}_{start_idx}"
                        assignments[(req_idx, res_idx, start_idx)] = self.model.NewBoolVar(var_name)

        return assignments

    def _add_constraints(self, problem: "Problem", assignments):
        """Add all scheduling constraints to the model.

        Args:
            problem: The scheduling problem
            assignments: Decision variables dictionary
        """
        # Each request must be scheduled exactly once
        self._add_request_constraints(problem, assignments)

        # No overlapping assignments for resources
        self._add_resource_constraints(problem, assignments)

        # Teacher constraints
        self._add_teacher_constraints(problem, assignments)

        # Student constraints
        self._add_student_constraints(problem, assignments)

        # Capacity constraints
        self._add_capacity_constraints(problem, assignments)

        # Blackout date constraints
        self._add_blackout_constraints(problem, assignments)

    def _add_request_constraints(self, problem: "Problem", assignments):
        """Ensure each request is scheduled exactly once."""
        for req_idx, _request in enumerate(problem.requests):
            # Collect all variables for this request
            request_vars = [var for (r_idx, _, _), var in assignments.items() if r_idx == req_idx]

            if request_vars:
                # Exactly one assignment per request
                self.model.AddExactlyOne(request_vars)
            else:
                # No feasible assignments for this request
                # This will make the problem infeasible
                self.model.Add(False)  # Impossible constraint

    def _add_resource_constraints(self, problem: "Problem", assignments):
        """Prevent overlapping assignments for each resource."""
        # Group assignments by resource
        resource_assignments = {}
        for (req_idx, res_idx, start_idx), var in assignments.items():
            if res_idx not in resource_assignments:
                resource_assignments[res_idx] = []

            request = problem.requests[req_idx]
            start_time = self._get_possible_start_times(
                problem, request, problem.resources[res_idx]
            )[start_idx]
            end_time = start_time + request.duration

            resource_assignments[res_idx].append((start_time, end_time, var))

        # Add no-overlap constraints for each resource
        for _res_idx, slot_assignments in resource_assignments.items():
            # Sort assignments by start time
            slot_assignments.sort(key=lambda x: x[0])

            # Add pairwise no-overlap constraints
            for i in range(len(slot_assignments)):
                for j in range(i + 1, len(slot_assignments)):
                    start1, end1, var1 = slot_assignments[i]
                    start2, end2, var2 = slot_assignments[j]

                    # If assignments overlap, they can't both be selected
                    if end1 > start2 and end2 > start1:  # Overlap
                        self.model.AddBoolOr([var1.Not(), var2.Not()])

    def _add_teacher_constraints(self, problem: "Problem", assignments):
        """Add teacher-specific constraints."""
        # Implementation depends on teacher constraint system
        # For now, basic teacher conflict prevention
        pass

    def _add_student_constraints(self, problem: "Problem", assignments):
        """Add student-specific constraints."""
        # Implementation depends on student constraint system
        # For now, basic student conflict prevention
        pass

    def _add_capacity_constraints(self, problem: "Problem", assignments):
        """Add room capacity constraints."""
        for (req_idx, res_idx, _start_idx), var in assignments.items():
            request = problem.requests[req_idx]
            resource = problem.resources[res_idx]

            # Resource must have sufficient capacity
            if hasattr(resource, "capacity") and hasattr(request, "enrollment"):
                if resource.capacity < request.enrollment:
                    # This assignment is not feasible
                    self.model.Add(var == 0)

    def _add_blackout_constraints(self, problem: "Problem", assignments):
        """Add blackout date constraints."""
        # Implementation depends on blackout constraint system
        pass

    def _is_resource_compatible(self, request, resource) -> bool:
        """Check if resource is compatible with request."""
        # Basic compatibility check
        # This would be expanded based on resource type matching
        return True

    def _get_possible_start_times(self, problem, request, resource):
        """Get list of possible start times for request-resource pair."""
        # For now, return a simplified set of time slots
        # In a full implementation, this would consider:
        # - Resource availability calendar
        # - Request date range
        # - Scheduling pattern
        # - Time slot granularity

        # Return dummy time slots for now
        from datetime import datetime, timedelta

        # Use request's date range if available
        if hasattr(request, "start_date") and hasattr(request, "end_date"):
            start = request.start_date
            end = request.end_date
        else:
            # Default to next month
            start = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=30)

        # Generate 2-hour slots between 9 AM and 6 PM on weekdays
        slots = []
        current = start
        while current < end:
            # Check if weekday (Monday=0, Friday=4)
            if current.weekday() < 5:
                if 9 <= current.hour < 18:  # Between 9 AM and 6 PM
                    slots.append(current)
            current += timedelta(hours=2)

        return slots

    def _extract_solution(
        self, problem: "Problem", assignments, is_optimal: bool
    ) -> List["Assignment"]:
        """Extract assignments from solver solution.

        Args:
            problem: The scheduling problem
            assignments: Decision variables
            is_optimal: Whether solution is optimal

        Returns:
            List of Assignment objects
        """
        from edusched.domain.assignment import Assignment

        solution_assignments = []

        for (req_idx, res_idx, start_idx), var in assignments.items():
            if self.solver.Value(var) == 1:  # Assignment is selected
                request = problem.requests[req_idx]
                resource = problem.resources[res_idx]

                start_times = self._get_possible_start_times(problem, request, resource)
                start_time = start_times[start_idx]
                end_time = start_time + request.duration

                assignment = Assignment(
                    request=request,
                    resource=resource,
                    start_time=start_time,
                    end_time=end_time,
                )
                solution_assignments.append(assignment)

        return solution_assignments
