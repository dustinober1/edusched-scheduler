"""Advanced optimization objectives for EduSched.

Implements sophisticated objectives for schedule optimization
including gap minimization, time preferences, walking distance,
and various quality metrics.
"""

from datetime import time, timedelta
from typing import TYPE_CHECKING, Dict, List, Tuple

from edusched.objectives.base import Objective

if TYPE_CHECKING:
    from edusched.domain.assignment import Assignment
    from edusched.domain.problem import Problem


class MinimizeGapsBetweenClasses(Objective):
    """Minimize gaps between consecutive classes for students and teachers."""

    def __init__(self, weight: float = 1.0, max_gap_hours: float = 2.0):
        """
        Initialize gap minimization objective.

        Args:
            weight: Importance weight for this objective
            max_gap_hours: Maximum gap to consider (gaps larger than this are ignored)
        """
        super().__init__("minimize_gaps", weight)
        self.max_gap_hours = max_gap_hours

    def evaluate(self, problem: "Problem", solution: List["Assignment"]) -> float:
        """Calculate total gap time between consecutive classes."""
        total_gap_hours = 0.0
        gap_count = 0

        # Group assignments by entity (student/teacher)
        entity_assignments = self._group_assignments_by_entity(problem, solution)

        # Calculate gaps for each entity
        for entity_id, assignments in entity_assignments.items():
            # Sort by start time
            assignments.sort(key=lambda a: a.start_time)

            # Find gaps between consecutive assignments
            for i in range(len(assignments) - 1):
                current_end = assignments[i].start_time + timedelta(
                    minutes=float(problem.requests[assignments[i].request_id].duration)
                )
                next_start = assignments[i + 1].start_time
                gap = (next_start - current_end).total_seconds() / 3600

                # Only count gaps within the maximum threshold
                if 0 < gap <= self.max_gap_hours:
                    total_gap_hours += gap
                    gap_count += 1

        # Return normalized score (lower is better)
        return total_gap_hours / max(1, gap_count)

    def _group_assignments_by_entity(
        self,
        problem: "Problem",
        solution: List["Assignment"],
    ) -> Dict[str, List["Assignment"]]:
        """Group assignments by the entities affected."""
        entity_assignments = {}

        for assignment in solution:
            request = problem.requests[assignment.request_id]

            # Group by teacher
            if request.teacher_id:
                teacher_id = request.teacher_id
                if teacher_id not in entity_assignments:
                    entity_assignments[teacher_id] = []
                entity_assignments[teacher_id].append(assignment)

            # Group by enrolled students
            if hasattr(request, "enrolled_students"):
                for student_id in request.enrolled_students:
                    if student_id not in entity_assignments:
                        entity_assignments[student_id] = []
                    entity_assignments[student_id].append(assignment)

        return entity_assignments


class PreferredTimeSlots(Objective):
    """Maximize assignment to preferred time slots."""

    def __init__(self, weight: float = 1.0, penalty_function: str = "linear"):
        """
        Initialize preferred time slots objective.

        Args:
            weight: Importance weight for this objective
            penalty_function: How to calculate penalty for non-preferred times
        """
        super().__init__("preferred_time_slots", weight)
        self.penalty_function = penalty_function
        self.preferred_slots_cache = {}

    def evaluate(self, problem: "Problem", solution: List["Assignment"]) -> float:
        """Calculate preference satisfaction score."""
        total_preference_score = 0.0
        total_assignments = 0

        for assignment in solution:
            request = problem.requests[assignment.request_id]

            # Get preferred time slots for this request
            preferred_slots = self._get_preferred_slots(problem, request)

            if preferred_slots:
                # Check if assignment time matches any preferred slot
                assignment_time = assignment.start_time.time()
                day_of_week = assignment.start_time.weekday()

                preference_score = 0.0
                for slot in preferred_slots:
                    if self._time_in_slot(assignment_time, day_of_week, slot):
                        # Perfect match
                        preference_score = 1.0
                        break
                    else:
                        # Calculate partial score based on distance from preferred
                        distance = self._calculate_time_distance(assignment_time, slot)
                        preference_score = max(preference_score, 1.0 - distance)

                total_preference_score += preference_score
                total_assignments += 1

        # Return average preference satisfaction (higher is better)
        return total_preference_score / max(1, total_assignments)

    def _get_preferred_slots(self, problem: "Problem", request) -> List[Dict]:
        """Get preferred time slots for a request."""
        # Check cache first
        cache_key = str(request.id)
        if cache_key in self.preferred_slots_cache:
            return self.preferred_slots_cache[cache_key]

        slots = []

        # Check teacher preferences
        if hasattr(problem, "teacher_preferences") and request.teacher_id:
            teacher_prefs = problem.teacher_preferences.get(request.teacher_id)
            if teacher_prefs and hasattr(teacher_prefs, "preferred_times"):
                for pref in teacher_prefs.preferred_times:
                    slots.append(
                        {
                            "start": pref.start_time,
                            "end": pref.end_time,
                            "days": [pref.day.lower()] if hasattr(pref, "day") else None,
                            "priority": getattr(pref, "priority", 1),
                        }
                    )

        # Check department preferences
        if hasattr(problem, "department_preferences") and request.department_id:
            dept_prefs = problem.department_preferences.get(request.department_id)
            if dept_prefs and hasattr(dept_prefs, "preferred_times"):
                slots.extend(dept_prefs.preferred_times)

        # Check request-specific preferences
        if hasattr(request, "preferred_time_slots"):
            slots.extend(request.preferred_time_slots)

        self.preferred_slots_cache[cache_key] = slots
        return slots

    def _time_in_slot(self, current_time: time, day_of_week: int, slot: Dict) -> bool:
        """Check if current time is within the preferred slot."""
        if "days" in slot and slot["days"]:
            days_map = {
                "monday": 0,
                "tuesday": 1,
                "wednesday": 2,
                "thursday": 3,
                "friday": 4,
                "saturday": 5,
                "sunday": 6,
            }
            if day_of_week not in [days_map[d.lower()] for d in slot["days"] if d in days_map]:
                return False

        # Check time range
        if "start" in slot and "end" in slot:
            return slot["start"] <= current_time <= slot["end"]

        return False

    def _calculate_time_distance(self, current_time: time, slot: Dict) -> float:
        """Calculate distance from preferred time slot."""
        if not ("start" in slot and "end" in slot):
            return 1.0

        # Convert times to minutes for easier calculation
        current_minutes = current_time.hour * 60 + current_time.minute
        slot_start = slot["start"].hour * 60 + slot["start"].minute
        slot_end = slot["end"].hour * 60 + slot["end"].minute

        if slot_start <= current_minutes <= slot_end:
            return 0.0

        # Calculate distance to nearest slot boundary
        distance = min(abs(current_minutes - slot_start), abs(current_minutes - slot_end))

        # Normalize to 0-1 range (max 12 hours = 720 minutes)
        return min(1.0, distance / 720.0)


class BreakTimeRequirements(Objective):
    """Ensure adequate breaks between classes."""

    def __init__(self, weight: float = 1.0, min_break_minutes: int = 15):
        """
        Initialize break time requirements objective.

        Args:
            weight: Importance weight for this objective
            min_break_minutes: Minimum break time between classes
        """
        super().__init__("break_time_requirements", weight)
        self.min_break_minutes = min_break_minutes

    def evaluate(self, problem: "Problem", solution: List["Assignment"]) -> float:
        """Calculate break time violation score."""
        total_violations = 0.0
        total_gaps = 0

        # Group assignments by entity
        entity_assignments = self._group_assignments_by_entity(problem, solution)

        for entity_id, assignments in entity_assignments.items():
            # Sort by start time
            assignments.sort(key=lambda a: a.start_time)

            # Check gaps between consecutive assignments
            for i in range(len(assignments) - 1):
                current_end = assignments[i].start_time + timedelta(
                    minutes=float(problem.requests[assignments[i].request_id].duration)
                )
                next_start = assignments[i + 1].start_time
                gap_minutes = (next_start - current_end).total_seconds() / 60

                total_gaps += 1

                # Calculate violation (if gap is too small)
                if gap_minutes < self.min_break_minutes:
                    violation = self.min_break_minutes - gap_minutes
                    total_violations += violation

        # Return average violation per gap (lower is better)
        return total_violations / max(1, total_gaps)

    def _group_assignments_by_entity(
        self,
        problem: "Problem",
        solution: List["Assignment"],
    ) -> Dict[str, List["Assignment"]]:
        """Group assignments by the entities affected."""
        # Same implementation as MinimizeGapsBetweenClasses
        entity_assignments = {}

        for assignment in solution:
            request = problem.requests[assignment.request_id]

            if request.teacher_id:
                teacher_id = request.teacher_id
                if teacher_id not in entity_assignments:
                    entity_assignments[teacher_id] = []
                entity_assignments[teacher_id].append(assignment)

            if hasattr(request, "enrolled_students"):
                for student_id in request.enrolled_students:
                    if student_id not in entity_assignments:
                        entity_assignments[student_id] = []
                    entity_assignments[student_id].append(assignment)

        return entity_assignments


class WalkingDistanceMinimizer(Objective):
    """Minimize walking distance between consecutive classes."""

    def __init__(self, weight: float = 1.0, building_distances: Dict[str, Dict[str, float]] = None):
        """
        Initialize walking distance minimizer.

        Args:
            weight: Importance weight for this objective
            building_distances: Pre-computed distances between buildings
        """
        super().__init__("walking_distance_minimizer", weight)
        self.building_distances = building_distances or {}

    def evaluate(self, problem: "Problem", solution: List["Assignment"]) -> float:
        """Calculate total walking distance."""
        total_distance = 0.0
        total_transitions = 0

        # Group assignments by student
        student_assignments = self._group_by_students(problem, solution)

        for student_id, assignments in student_assignments.items():
            # Sort by start time
            assignments.sort(key=lambda a: a.start_time)

            # Calculate distance between consecutive classes
            for i in range(len(assignments) - 1):
                current_building = self._get_building_id(problem, assignments[i])
                next_building = self._get_building_id(problem, assignments[i + 1])

                if current_building != next_building:
                    distance = self._get_distance(current_building, next_building)
                    total_distance += distance
                    total_transitions += 1

        # Return average distance per transition (lower is better)
        return total_distance / max(1, total_transitions)

    def _group_by_students(
        self,
        problem: "Problem",
        solution: List["Assignment"],
    ) -> Dict[str, List["Assignment"]]:
        """Group assignments by student ID."""
        student_assignments = {}

        for assignment in solution:
            request = problem.requests[assignment.request_id]

            if hasattr(request, "enrolled_students"):
                for student_id in request.enrolled_students:
                    if student_id not in student_assignments:
                        student_assignments[student_id] = []
                    student_assignments[student_id].append(assignment)

        return student_assignments

    def _get_building_id(self, problem: "Problem", assignment: "Assignment") -> str:
        """Get building ID for an assignment."""
        resource = problem.resources.get(assignment.resource.id)
        if resource:
            return getattr(resource, "building_id", str(resource.id))
        return str(assignment.resource.id)

    def _get_distance(self, building1: str, building2: str) -> float:
        """Get walking distance between two buildings."""
        if building1 == building2:
            return 0.0

        # Check pre-computed distances
        if building1 in self.building_distances:
            if building2 in self.building_distances[building1]:
                return self.building_distances[building1][building2]

        if building2 in self.building_distances:
            if building1 in self.building_distances[building2]:
                return self.building_distances[building2][building1]

        # Default estimation (can be improved with actual coordinates)
        return 500.0  # 500 meters default


class RoomUtilizationOptimizer(Objective):
    """Optimize room utilization to minimize waste."""

    def __init__(self, weight: float = 1.0, target_utilization: float = 0.8):
        """
        Initialize room utilization optimizer.

        Args:
            weight: Importance weight for this objective
            target_utilization: Target utilization percentage (0-1)
        """
        super().__init__("room_utilization_optimizer", weight)
        self.target_utilization = target_utilization

    def evaluate(self, problem: "Problem", solution: List["Assignment"]) -> float:
        """Calculate room utilization efficiency."""
        room_utilizations = {}

        # Calculate utilization for each room
        for assignment in solution:
            resource = problem.resources[assignment.resource.id]
            room_id = str(resource.id)
            request = problem.requests[assignment.request_id]

            if room_id not in room_utilizations:
                room_utilizations[room_id] = {
                    "capacity": getattr(resource, "capacity", 0),
                    "assigned_students": 0,
                    "time_slots": 0,
                }

            # Add enrolled students
            enrollment = getattr(request, "enrollment_count", 0)
            room_utilizations[room_id]["assigned_students"] += enrollment
            room_utilizations[room_id]["time_slots"] += 1

        # Calculate utilization efficiency
        efficiency_scores = []

        for room_id, data in room_utilizations.items():
            if data["capacity"] > 0 and data["time_slots"] > 0:
                avg_students = data["assigned_students"] / data["time_slots"]
                utilization = avg_students / data["capacity"]

                # Score based on how close to target utilization
                deviation = abs(utilization - self.target_utilization)
                efficiency = max(0.0, 1.0 - deviation)
                efficiency_scores.append(efficiency)

        # Return average efficiency (higher is better)
        return sum(efficiency_scores) / max(1, len(efficiency_scores))


class TeacherWorkloadBalancer(Objective):
    """Balance teacher workload evenly across time periods."""

    def __init__(self, weight: float = 1.0):
        """
        Initialize teacher workload balancer.

        Args:
            weight: Importance weight for this objective
        """
        super().__init__("teacher_workload_balancer", weight)

    def evaluate(self, problem: "Problem", solution: List["Assignment"]) -> float:
        """Calculate teacher workload balance."""
        teacher_workloads = {}

        # Calculate workload for each teacher
        for assignment in solution:
            request = problem.requests[assignment.request_id]
            teacher_id = request.teacher_id

            if teacher_id:
                if teacher_id not in teacher_workloads:
                    teacher_workloads[teacher_id] = {
                        "total_hours": 0,
                        "daily_hours": {},
                        "courses": set(),
                    }

                # Add hours
                duration_hours = float(request.duration) / 60
                teacher_workloads[teacher_id]["total_hours"] += duration_hours
                teacher_workloads[teacher_id]["courses"].add(assignment.request_id)

                # Track daily hours
                day_key = assignment.start_time.date()
                teacher_workloads[teacher_id]["daily_hours"][day_key] = (
                    teacher_workloads[teacher_id]["daily_hours"].get(day_key, 0) + duration_hours
                )

        # Calculate balance metric
        if len(teacher_workloads) < 2:
            return 1.0  # Perfect balance if only one teacher

        # Calculate standard deviation of workloads
        workloads = [data["total_hours"] for data in teacher_workloads.values()]
        avg_workload = sum(workloads) / len(workloads)

        variance = sum((w - avg_workload) ** 2 for w in workloads) / len(workloads)
        std_dev = variance**0.5

        # Convert to balance score (lower std_dev = higher balance)
        balance_score = max(0.0, 1.0 - (std_dev / max(1.0, avg_workload)))
        return balance_score


class CampusDistributionOptimizer(Objective):
    """Optimize distribution of classes across campuses for multi-campus institutions."""

    def __init__(self, weight: float = 1.0, balance_factor: float = 0.5):
        """
        Initialize campus distribution optimizer.

        Args:
            weight: Importance weight for this objective
            balance_factor: How much to prioritize even distribution (0-1)
        """
        super().__init__("campus_distribution_optimizer", weight)
        self.balance_factor = balance_factor

    def evaluate(self, problem: "Problem", solution: List["Assignment"]) -> float:
        """Calculate campus distribution efficiency."""
        campus_assignments = {}
        campus_capacities = {}

        # Count assignments per campus
        for assignment in solution:
            resource = problem.resources[assignment.resource.id]
            campus_id = getattr(resource, "campus_id", "default")

            if campus_id not in campus_assignments:
                campus_assignments[campus_id] = 0
                campus_capacities[campus_id] = getattr(resource, "campus_capacity", 0)

            campus_assignments[campus_id] += 1

        if not campus_assignments:
            return 1.0

        # Calculate distribution balance
        total_assignments = sum(campus_assignments.values())
        expected_per_campus = total_assignments / len(campus_assignments)

        # Calculate balance score
        balance_score = 1.0
        for assignments in campus_assignments.values():
            deviation = abs(assignments - expected_per_campus)
            balance_score -= deviation / total_assignments
        balance_score = max(0.0, balance_score)

        # Consider campus capacities
        capacity_score = 1.0
        for campus_id, assignments in campus_assignments.items():
            capacity = campus_capacities.get(campus_id, float("inf"))
            if capacity > 0:
                utilization = assignments / capacity
                if utilization > 1.0:
                    capacity_score -= (utilization - 1.0) * 0.5

        capacity_score = max(0.0, capacity_score)

        # Combine scores
        final_score = (
            self.balance_factor * balance_score + (1 - self.balance_factor) * capacity_score
        )

        return max(0.0, min(1.0, final_score))


class EnergyEfficiencyOptimizer(Objective):
    """Optimize schedule for energy efficiency (e.g., consolidate buildings)."""

    def __init__(self, weight: float = 1.0):
        """
        Initialize energy efficiency optimizer.

        Args:
            weight: Importance weight for this objective
        """
        super().__init__("energy_efficiency_optimizer", weight)

    def evaluate(self, problem: "Problem", solution: List["Assignment"]) -> float:
        """Calculate energy efficiency score."""
        building_usage = {}

        # Track building usage by time blocks
        for assignment in solution:
            resource = problem.resources[assignment.resource.id]
            building_id = getattr(resource, "building_id", str(resource.id))

            # Get time block (hourly)
            hour = assignment.start_time.hour
            time_block = f"{assignment.start_time.date()}_{hour:02d}"

            if building_id not in building_usage:
                building_usage[building_id] = set()
            building_usage[building_id].add(time_block)

        # Calculate efficiency based on building consolidation
        if not building_usage:
            return 1.0

        # Fewer active buildings = better efficiency
        total_time_blocks = len(set(tb for blocks in building_usage.values() for tb in blocks))
        avg_blocks_per_building = sum(len(blocks) for blocks in building_usage.values()) / len(
            building_usage
        )

        # Efficiency score (consolidation bonus)
        consolidation_bonus = 1.0 - (len(building_usage) - 1) / max(1, total_time_blocks)
        consolidation_bonus = max(0.0, consolidation_bonus)

        # Also consider full utilization of active buildings
        utilization_bonus = min(1.0, avg_blocks_per_building / 10.0)  # Assume 10 blocks is full day

        final_score = (consolidation_bonus + utilization_bonus) / 2
        return max(0.0, min(1.0, final_score))


class PreferenceWeightedAggregator(Objective):
    """Aggregates multiple objectives with dynamic weight adjustment."""

    def __init__(self, objectives: List[Tuple[Objective, float]], adaptive_weights: bool = True):
        """
        Initialize weighted aggregator.

        Args:
            objectives: List of (objective, weight) tuples
            adaptive_weights: Whether to adaptively adjust weights based on performance
        """
        super().__init__("preference_weighted_aggregator", 1.0)
        self.objectives = objectives
        self.adaptive_weights = adaptive_weights
        self.performance_history = {obj.name: [] for obj, _ in objectives}

    def evaluate(self, problem: "Problem", solution: List["Assignment"]) -> float:
        """Calculate weighted aggregate score."""
        total_score = 0.0
        total_weight = 0.0

        for objective, base_weight in self.objectives:
            # Get objective score
            score = objective.evaluate(problem, solution)

            # Adjust weight if adaptive
            if self.adaptive_weights and objective.name in self.performance_history:
                # Reduce weight for consistently high-performing objectives
                # to focus on problem areas
                history = self.performance_history[objective.name]
                if len(history) >= 5:  # Need enough history
                    avg_performance = sum(history[-5:]) / 5
                    if avg_performance > 0.8:  # Consistently high
                        adjusted_weight = base_weight * 0.5
                    elif avg_performance < 0.3:  # Consistently low
                        adjusted_weight = base_weight * 1.5
                    else:
                        adjusted_weight = base_weight
                else:
                    adjusted_weight = base_weight
            else:
                adjusted_weight = base_weight

            total_score += score * adjusted_weight
            total_weight += adjusted_weight

            # Track performance
            self.performance_history[objective.name].append(score)
            if len(self.performance_history[objective.name]) > 100:
                self.performance_history[objective.name] = self.performance_history[objective.name][
                    -100:
                ]

        return total_score / max(1.0, total_weight)
