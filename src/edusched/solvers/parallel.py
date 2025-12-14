"""Parallel solving capabilities for EduSched.

Implements multi-threaded constraint checking, parallel assignment
generation, and result merging for improved performance.
"""

import concurrent.futures
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, List, Optional, Tuple

from edusched.solvers.heuristic import HeuristicSolver


class ParallelContext:
    """Thread-safe context for parallel solving."""

    def __init__(self, problem: Any):
        self.problem = problem
        self.lock = threading.RLock()
        self.best_solution = []
        self.best_score = float("-inf")
        self.iterations_completed = 0
        self.start_time = datetime.now()
        self.should_stop = threading.Event()

    def update_best_solution(self, solution: List[Any], score: float) -> bool:
        """Thread-safe update of best solution."""
        with self.lock:
            if score > self.best_score:
                self.best_solution = solution.copy()
                self.best_score = score
                return True
            return False

    def increment_iterations(self) -> int:
        """Thread-safe iteration counter."""
        with self.lock:
            self.iterations_completed += 1
            return self.iterations_completed

    def get_elapsed_time(self) -> float:
        """Get elapsed solving time in seconds."""
        with self.lock:
            return (datetime.now() - self.start_time).total_seconds()


@dataclass
class ParallelConfiguration:
    """Configuration for parallel solving."""

    num_workers: int = 4
    chunk_size: int = 10
    enable_load_balancing: bool = True
    dynamic_work_distribution: bool = True
    sync_interval: int = 100  # Iterations between sync
    timeout_seconds: Optional[float] = None
    max_iterations: Optional[int] = None


class ParallelConstraintChecker:
    """Parallel constraint checking for improved performance."""

    def __init__(self, num_workers: int = 4):
        self.num_workers = num_workers

    def check_constraints_parallel(
        self,
        constraints: List[Any],
        assignments: List[Any],
        context: Any,
    ) -> List[Any]:
        """Check constraints in parallel."""
        # Create chunks of assignments for each worker
        chunks = self._create_chunks(assignments, self.num_workers)

        # Execute constraint checking in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = [
                executor.submit(self._check_constraints_chunk, constraints, chunk, context)
                for chunk in chunks
            ]

            # Collect results
            all_violations = []
            for future in concurrent.futures.as_completed(futures):
                violations = future.result()
                all_violations.extend(violations)

        return all_violations

    def _create_chunks(self, items: List[Any], num_chunks: int) -> List[List[Any]]:
        """Split items into chunks for parallel processing."""
        chunk_size = max(1, len(items) // num_chunks)
        chunks = []

        for i in range(0, len(items), chunk_size):
            chunk = items[i : i + chunk_size]
            if chunk:
                chunks.append(chunk)

        # Ensure we don't have more chunks than items
        while len(chunks) < num_chunks and chunks:
            chunks.append([])

        return chunks[:num_chunks]

    def _check_constraints_chunk(
        self,
        constraints: List[Any],
        assignments: List[Any],
        context: Any,
    ) -> List[Any]:
        """Check constraints for a chunk of assignments."""
        violations = []

        for assignment in assignments:
            for constraint in constraints:
                violation = constraint.check(assignment, context.current_assignments, context)
                if violation:
                    violations.append(violation)

        return violations


class ParallelAssignmentGenerator:
    """Generates potential assignments in parallel."""

    def __init__(self, base_solver: HeuristicSolver, num_workers: int = 4):
        self.base_solver = base_solver
        self.num_workers = num_workers

    def generate_assignments_parallel(
        self,
        request: Any,
        resources: List[Any],
        time_slots: List[Tuple[datetime, datetime]],
        context: Any,
    ) -> List[Tuple[Any, float]]:
        """Generate potential assignments in parallel."""
        # Create work items
        work_items = []
        for resource in resources:
            for time_slot in time_slots:
                work_items.append((resource, time_slot))

        # Split work among workers
        chunks = self._create_work_chunks(work_items, self.num_workers)

        # Generate assignments in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = [
                executor.submit(self._generate_assignments_chunk, request, chunk, context)
                for chunk in chunks
            ]

            # Collect and rank assignments
            all_assignments = []
            for future in concurrent.futures.as_completed(futures):
                assignments = future.result()
                all_assignments.extend(assignments)

        # Sort by score
        all_assignments.sort(key=lambda x: x[1], reverse=True)
        return all_assignments

    def _create_work_chunks(self, work_items: List[Tuple], num_chunks: int) -> List[List[Tuple]]:
        """Split work items into chunks."""
        chunk_size = max(1, len(work_items) // num_chunks)
        chunks = []

        for i in range(0, len(work_items), chunk_size):
            chunk = work_items[i : i + chunk_size]
            if chunk:
                chunks.append(chunk)

        return chunks[:num_chunks]

    def _generate_assignments_chunk(
        self,
        request: Any,
        work_chunk: List[Tuple[Any, Tuple[datetime, datetime]]],
        context: Any,
    ) -> List[Tuple[Any, float]]:
        """Generate assignments for a chunk of work."""
        assignments = []

        for resource, time_slot in work_chunk:
            # Create temporary assignment
            temp_assignment = self.base_solver._create_assignment(request, resource, time_slot[0])

            # Check if valid
            if self.base_solver._is_assignment_valid(temp_assignment, context):
                # Calculate score
                score = self.base_solver._calculate_assignment_score(temp_assignment, context)
                assignments.append((temp_assignment, score))

        return assignments


class ParallelHeuristicSolver(HeuristicSolver):
    """Parallel version of the heuristic solver."""

    def __init__(self, config: ParallelConfiguration = None):
        super().__init__()
        self.config = config or ParallelConfiguration()
        self.constraint_checker = ParallelConstraintChecker(self.config.num_workers)
        self.assignment_generator = ParallelAssignmentGenerator(self, self.config.num_workers)

    def solve(self, problem: Any, seed: Optional[int] = None, fallback: bool = False) -> Any:
        """Solve using parallel heuristic algorithm."""
        if seed is not None:
            import random

            random.seed(seed)

        # Create parallel context
        parallel_context = ParallelContext(problem)

        # Sort requests (same as base solver)
        sorted_requests = sorted(
            problem.requests,
            key=lambda r: (-r.priority, -float(r.duration), r.number_of_occurrences),
        )

        # Generate time slots
        all_time_slots = self._generate_all_time_slots(problem)

        # Initialize solution
        solution = []

        # Process requests in parallel batches
        batch_size = self.config.chunk_size
        for i in range(0, len(sorted_requests), batch_size):
            batch = sorted_requests[i : i + batch_size]

            # Process batch
            batch_solution = self._solve_batch_parallel(
                batch, problem, all_time_slots, parallel_context
            )

            # Add to solution
            solution.extend(batch_solution)

            # Check stop conditions
            if parallel_context.should_stop.is_set():
                break

            if (
                self.config.max_iterations
                and parallel_context.iterations_completed >= self.config.max_iterations
            ):
                break

            if (
                self.config.timeout_seconds
                and parallel_context.get_elapsed_time() > self.config.timeout_seconds
            ):
                break

        # Return best solution found
        best_solution = parallel_context.best_solution or solution

        # Create result
        from edusched.domain.result import Result

        return Result(
            assignments=best_solution,
            solver_name="parallel_heuristic",
            solve_time_seconds=parallel_context.get_elapsed_time(),
            iterations=parallel_context.iterations_completed,
            is_optimal=False,
        )

    def _solve_batch_parallel(
        self,
        requests: List[Any],
        problem: Any,
        time_slots: List[Tuple[datetime, datetime]],
        parallel_context: ParallelContext,
    ) -> List[Any]:
        """Solve a batch of requests in parallel."""
        batch_solution = []

        for request in requests:
            # Generate potential assignments in parallel
            assignments = self.assignment_generator.generate_assignments_parallel(
                request, problem.resources, time_slots, problem
            )

            # Check constraints in parallel
            if assignments:
                # Test top candidates
                num_candidates = min(10, len(assignments))
                candidates = assignments[:num_candidates]

                # Check constraints for candidates
                valid_assignments = []
                for assignment, score in candidates:
                    # Quick constraint check
                    if self._quick_constraint_check(assignment, problem):
                        valid_assignments.append((assignment, score))

                # Select best assignment
                if valid_assignments:
                    best_assignment, _ = max(valid_assignments, key=lambda x: x[1])
                    batch_solution.append(best_assignment)

                    # Update context
                    problem.current_assignments.append(best_assignment)

                    # Update best solution if needed
                    current_score = self._calculate_solution_score(batch_solution, problem)
                    parallel_context.update_best_solution(batch_solution, current_score)

            parallel_context.increment_iterations()

        return batch_solution

    def _quick_constraint_check(self, assignment: Any, context: Any) -> bool:
        """Quick constraint check to filter assignments."""
        # Implement fast constraint checks for obvious violations
        # This is a simplified version - in production, implement specific fast checks

        # Check resource availability
        for existing in context.current_assignments:
            if existing.resource.id == assignment.resource.id and self._times_overlap(
                existing, assignment
            ):
                return False

        return True

    def _times_overlap(self, assignment1: Any, assignment2: Any) -> bool:
        """Check if two assignments overlap in time."""
        duration1 = float(assignment1.request.duration) / 60
        duration2 = float(assignment2.request.duration) / 60

        end1 = assignment1.start_time + timedelta(hours=duration1)
        end2 = assignment2.start_time + timedelta(hours=duration2)

        return assignment1.start_time < end2 and assignment2.start_time < end1

    def _calculate_solution_score(self, solution: List[Any], context: Any) -> float:
        """Calculate overall solution score."""
        if not solution or not context.objectives:
            return 0.0

        total_score = 0.0
        for objective in context.objectives:
            score = objective.evaluate(context, solution)
            weight = getattr(objective, "weight", 1.0)
            total_score += score * weight

        return total_score


class ParallelSolutionMerger:
    """Merges solutions from parallel workers."""

    def __init__(self):
        self.conflict_resolver = ConflictResolver()

    def merge_solutions(
        self,
        solutions: List[List[Any]],
        problem: Any,
        merge_strategy: str = "best_conflict_free",
    ) -> List[Any]:
        """Merge multiple solutions into one."""
        if not solutions:
            return []

        if len(solutions) == 1:
            return solutions[0]

        if merge_strategy == "best":
            # Return the best solution by score
            return max(solutions, key=lambda s: self._calculate_score(s, problem))

        elif merge_strategy == "union":
            # Union of all assignments, then resolve conflicts
            all_assignments = []
            for solution in solutions:
                all_assignments.extend(solution)
            return self.conflict_resolver.resolve_conflicts(all_assignments, problem)

        elif merge_strategy == "best_conflict_free":
            # Start with best solution, add compatible assignments from others
            best_solution = max(solutions, key=lambda s: self._calculate_score(s, problem))
            merged = best_solution.copy()

            for solution in solutions:
                if solution is best_solution:
                    continue

                for assignment in solution:
                    if self._is_compatible(assignment, merged, problem):
                        merged.append(assignment)

            return merged

        else:
            raise ValueError(f"Unknown merge strategy: {merge_strategy}")

    def _calculate_score(self, solution: List[Any], context: Any) -> float:
        """Calculate solution score."""
        if not solution or not context.objectives:
            return 0.0

        total_score = 0.0
        for objective in context.objectives:
            score = objective.evaluate(context, solution)
            weight = getattr(objective, "weight", 1.0)
            total_score += score * weight

        return total_score

    def _is_compatible(self, assignment: Any, solution: List[Any], context: Any) -> bool:
        """Check if assignment is compatible with solution."""
        # Check resource conflicts
        for existing in solution:
            if existing.resource.id == assignment.resource.id:
                if self._times_overlap(existing, assignment):
                    return False

        # Check other constraints
        temp_context = context.__class__()
        temp_context.current_assignments = solution + [assignment]

        for constraint in context.constraints:
            if constraint.check(assignment, temp_context.current_assignments, temp_context):
                return False

        return True

    def _times_overlap(self, assignment1: Any, assignment2: Any) -> bool:
        """Check if two assignments overlap."""
        duration1 = float(assignment1.request.duration) / 60
        duration2 = float(assignment2.request.duration) / 60

        end1 = assignment1.start_time + timedelta(hours=duration1)
        end2 = assignment2.start_time + timedelta(hours=duration2)

        return assignment1.start_time < end2 and assignment2.start_time < end1


class ConflictResolver:
    """Resolves conflicts in merged solutions."""

    def resolve_conflicts(self, assignments: List[Any], context: Any) -> List[Any]:
        """Resolve conflicts in a list of assignments."""
        # Sort assignments by priority and score
        sorted_assignments = sorted(
            assignments,
            key=lambda a: (
                -getattr(a.request, "priority", 1),
                -self._calculate_assignment_score(a, context),
            ),
        )

        resolved = []
        for assignment in sorted_assignments:
            if self._has_no_conflicts(assignment, resolved, context):
                resolved.append(assignment)

        return resolved

    def _has_no_conflicts(
        self,
        assignment: Any,
        existing_assignments: List[Any],
        context: Any,
    ) -> bool:
        """Check if assignment has no conflicts with existing ones."""
        # Create temporary context with existing assignments
        temp_context = context.__class__()
        temp_context.current_assignments = existing_assignments

        # Check all constraints
        for constraint in context.constraints:
            if constraint.check(assignment, existing_assignments, temp_context):
                return False

        return True

    def _calculate_assignment_score(self, assignment: Any, context: Any) -> float:
        """Calculate score for a single assignment."""
        score = 0.0

        # Resource efficiency score
        resource = context.resources.get(assignment.resource.id)
        if resource and hasattr(resource, "capacity"):
            request = assignment.request
            enrollment = getattr(request, "enrollment_count", 0)
            if resource.capacity > 0:
                efficiency = min(1.0, enrollment / resource.capacity)
                score += efficiency

        return score
