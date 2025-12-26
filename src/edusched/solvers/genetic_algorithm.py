"""Genetic algorithm solver backend implementation."""

import random
import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Dict, List, Optional, Set
from edusched.solvers.base import SolverBackend

if TYPE_CHECKING:
    from edusched.constraints.base import ConstraintContext
    from edusched.domain.assignment import Assignment
    from edusched.domain.problem import Problem, ProblemIndices
    from edusched.domain.result import Result
    from edusched.domain.session_request import SessionRequest
    from edusched.objectives.base import Objective


class ScheduleIndividual:
    """Represents a complete schedule solution for genetic algorithm."""
    
    def __init__(self, assignments: List["Assignment"], problem: "Problem"):
        self.assignments = assignments
        self.problem = problem
        self.fitness = None  # Will be calculated when needed

    def calculate_fitness(self, context: "ConstraintContext") -> float:
        """Calculate fitness of this individual based on constraints and objectives."""
        if self.fitness is not None:
            return self.fitness
            
        constraint_violations = 0
        objective_score = 0.0
        
        # Check constraint violations
        for assignment in self.assignments:
            for constraint in self.problem.constraints:
                violation = constraint.check(assignment, self.assignments, context)
                if violation:
                    constraint_violations += 1
        
        # Calculate objective satisfaction
        if self.problem.objectives:
            total_weight = sum(obj.weight for obj in self.problem.objectives)
            if total_weight > 0:
                objective_score = sum(
                    obj.score(self.assignments) * obj.weight 
                    for obj in self.problem.objectives
                ) / total_weight
        
        # Fitness is higher for fewer violations and better objective scores
        # Negative penalty for violations, positive for objectives
        self.fitness = -constraint_violations * 100 + objective_score
        return self.fitness


class GeneticAlgorithmSolver(SolverBackend):
    """Genetic algorithm solver backend for complex optimization problems."""

    def __init__(self, 
                 population_size: int = 50,
                 mutation_rate: float = 0.1,
                 crossover_rate: float = 0.8,
                 max_generations: int = 100,
                 elite_size: int = 5):
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.max_generations = max_generations
        self.elite_size = elite_size

    def solve(
        self,
        problem: "Problem",
        seed: Optional[int] = None,
        fallback: bool = False,
    ) -> "Result":
        """
        Solve scheduling problem using genetic algorithm.

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

        # Create constraint context
        context = self._create_context(problem, indices)

        # Initialize population
        population = self._initialize_population(problem, context)
        
        best_solution = None
        best_fitness = float('-inf')
        
        # Evolve population
        for generation in range(self.max_generations):
            # Evaluate fitness of all individuals
            for individual in population:
                fitness = individual.calculate_fitness(context)
                if fitness > best_fitness:
                    best_fitness = fitness
                    best_solution = individual
            
            # Check if we found a perfect solution (no violations)
            if best_fitness >= 0 and self._is_valid_solution(best_solution.assignments, problem, context):
                break
            
            # Create new generation
            population = self._create_new_generation(population, problem, context)

        # Return the best solution found
        if best_solution is not None:
            objective_score = self._calculate_objectives(problem.objectives, best_solution.assignments)
            
            return Result(
                status="feasible" if best_fitness >= 0 else "partial",
                assignments=best_solution.assignments,
                unscheduled_requests=self._get_unscheduled_requests(problem, best_solution.assignments),
                objective_score=objective_score,
                backend_used=self.backend_name,
                seed_used=seed,
                solve_time_seconds=time.time() - start_time,
            )
        else:
            # If no solution found, return empty result
            return Result(
                status="infeasible",
                assignments=[],
                unscheduled_requests=[req.id for req in problem.requests],
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

    def _initialize_population(self, problem: "Problem", context: "ConstraintContext") -> List[ScheduleIndividual]:
        """Initialize population with random valid solutions."""
        population = []
        
        for _ in range(self.population_size):
            # Create random assignment for each request
            assignments = self._create_random_solution(problem, context)
            individual = ScheduleIndividual(assignments, problem)
            population.append(individual)
        
        return population

    def _create_random_solution(self, problem: "Problem", context: "ConstraintContext") -> List["Assignment"]:
        """Create a random solution for the problem."""
        from edusched.domain.assignment import Assignment
        from edusched.utils.scheduling_utils import OccurrenceSpreader
        from zoneinfo import ZoneInfo
        
        assignments = []
        
        # Use occurrence spreader to generate valid dates
        spreader = OccurrenceSpreader(problem.holiday_calendar) if problem.holiday_calendar else \
                   OccurrenceSpreader(None)  # Default holiday calendar
        
        # Get calendar for timezone
        calendar = context.calendar_lookup.get(context.problem.institutional_calendar_id)
        timezone = calendar.timezone if calendar and hasattr(calendar, "timezone") else ZoneInfo("UTC")
        
        # Create assignments for each request
        for request in problem.requests:
            # Generate occurrence dates
            schedule_dates = spreader.generate_occurrence_dates(request, timezone)
            
            for occurrence_index in range(min(request.number_of_occurrences, len(schedule_dates))):
                if occurrence_index < len(schedule_dates):
                    # Get available time slots for this date
                    time_slots = spreader.generate_time_slots(
                        schedule_dates[occurrence_index],
                        request,
                        timedelta(minutes=15),  # Default granularity
                        timezone
                    )
                    
                    # Pick a random time slot
                    if time_slots:
                        start_time, end_time = random.choice(time_slots)
                        
                        # Create assignment with random resource
                        assignment = Assignment(
                            request_id=request.id,
                            occurrence_index=occurrence_index,
                            start_time=start_time,
                            end_time=end_time,
                            cohort_id=request.cohort_id,
                        )
                        
                        # Assign resources
                        if self._assign_resources(assignment, context, problem.build_indices(), assignments):
                            assignments.append(assignment)
        
        return assignments

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
                # Assign a random suitable resource
                assigned_resources[resource_type] = [random.choice(suitable_resources).id]

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

    def _create_new_generation(self, population: List[ScheduleIndividual], 
                              problem: "Problem", context: "ConstraintContext") -> List[ScheduleIndividual]:
        """Create a new generation using selection, crossover, and mutation."""
        new_population = []
        
        # Keep elite individuals
        sorted_population = sorted(population, key=lambda x: x.calculate_fitness(context), reverse=True)
        new_population.extend(sorted_population[:self.elite_size])
        
        # Fill the rest of the population
        while len(new_population) < self.population_size:
            # Selection
            parent1 = self._tournament_selection(population, context)
            parent2 = self._tournament_selection(population, context)
            
            # Crossover
            if random.random() < self.crossover_rate:
                child1, child2 = self._crossover(parent1, parent2, problem, context)
            else:
                child1 = ScheduleIndividual(parent1.assignments[:], problem)
                child2 = ScheduleIndividual(parent2.assignments[:], problem)
            
            # Mutation
            self._mutate(child1, problem, context)
            self._mutate(child2, problem, context)
            
            new_population.extend([child1, child2])
        
        # Ensure population size is correct (might be slightly over due to pairs)
        return new_population[:self.population_size]

    def _tournament_selection(self, population: List[ScheduleIndividual], 
                            context: "ConstraintContext", tournament_size: int = 3) -> ScheduleIndividual:
        """Select an individual using tournament selection."""
        tournament = random.sample(population, min(tournament_size, len(population)))
        return max(tournament, key=lambda x: x.calculate_fitness(context))

    def _crossover(self, parent1: ScheduleIndividual, parent2: ScheduleIndividual,
                  problem: "Problem", context: "ConstraintContext") -> tuple:
        """Perform crossover between two parents to create two children."""
        # Simple crossover: mix assignments from both parents
        # This is a basic implementation - more sophisticated approaches could be used
        
        # Create new assignments list by combining parts of both parents
        child_assignments1 = []
        child_assignments2 = []
        
        # Group assignments by request ID
        parent1_by_request = {}
        parent2_by_request = {}
        
        for assignment in parent1.assignments:
            if assignment.request_id not in parent1_by_request:
                parent1_by_request[assignment.request_id] = []
            parent1_by_request[assignment.request_id].append(assignment)
        
        for assignment in parent2.assignments:
            if assignment.request_id not in parent2_by_request:
                parent2_by_request[assignment.request_id] = []
            parent2_by_request[assignment.request_id].append(assignment)
        
        # Alternate taking assignments from each parent for each request
        all_request_ids = set(parent1_by_request.keys()) | set(parent2_by_request.keys())
        
        for request_id in all_request_ids:
            parent1_assignments = parent1_by_request.get(request_id, [])
            parent2_assignments = parent2_by_request.get(request_id, [])
            
            # For simplicity, take all assignments from one parent or the other
            if random.random() < 0.5:
                child_assignments1.extend(parent1_assignments)
                child_assignments2.extend(parent2_assignments)
            else:
                child_assignments1.extend(parent2_assignments)
                child_assignments2.extend(parent1_assignments)
        
        child1 = ScheduleIndividual(child_assignments1, problem)
        child2 = ScheduleIndividual(child_assignments2, problem)
        
        return child1, child2

    def _mutate(self, individual: ScheduleIndividual, problem: "Problem", context: "ConstraintContext"):
        """Apply mutation to an individual."""
        if random.random() > self.mutation_rate:
            return  # No mutation this time
        
        # Simple mutation: randomly change time or resource for some assignments
        if not individual.assignments:
            return
            
        # Pick a random assignment to mutate
        assignment_idx = random.randint(0, len(individual.assignments) - 1)
        assignment = individual.assignments[assignment_idx]
        
        # Mutate either the time or the resources
        if random.random() < 0.5:
            # Mutate time - change to a different valid time slot
            request = context.request_lookup[assignment.request_id]
            if request:
                from edusched.utils.scheduling_utils import OccurrenceSpreader
                from zoneinfo import ZoneInfo
                
                spreader = OccurrenceSpreader(problem.holiday_calendar) if problem.holiday_calendar else \
                           OccurrenceSpreader(None)
                
                calendar = context.calendar_lookup.get(context.problem.institutional_calendar_id)
                timezone = calendar.timezone if calendar and hasattr(calendar, "timezone") else ZoneInfo("UTC")
                
                # Find a new valid time slot
                schedule_dates = spreader.generate_occurrence_dates(request, timezone)
                if schedule_dates:
                    new_date = random.choice(schedule_dates)
                    time_slots = spreader.generate_time_slots(
                        new_date,
                        request,
                        timedelta(minutes=15),
                        timezone
                    )
                    
                    if time_slots:
                        new_start, new_end = random.choice(time_slots)
                        assignment.start_time = new_start
                        assignment.end_time = new_end
        else:
            # Mutate resources - assign different resources if available
            indices = problem.build_indices()
            self._assign_resources(assignment, context, indices, 
                                 [a for i, a in enumerate(individual.assignments) if i != assignment_idx])

    def _is_valid_solution(self, assignments: List["Assignment"], 
                          problem: "Problem", context: "ConstraintContext") -> bool:
        """Check if a solution satisfies all constraints."""
        for assignment in assignments:
            for constraint in problem.constraints:
                violation = constraint.check(assignment, assignments, context)
                if violation:
                    return False
        return True

    def _get_unscheduled_requests(self, problem: "Problem", assignments: List["Assignment"]) -> List[str]:
        """Get list of request IDs that weren't scheduled."""
        scheduled_request_ids = {a.request_id for a in assignments}
        return [req.id for req in problem.requests if req.id not in scheduled_request_ids]

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

    @property
    def backend_name(self) -> str:
        """Return backend identifier."""
        return "genetic_algorithm"