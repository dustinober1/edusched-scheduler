"""Constraints for department availability, preferences, and budget management."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional

from edusched.constraints.base import Constraint, ConstraintContext, Violation

if TYPE_CHECKING:
    from edusched.domain.assignment import Assignment


class DepartmentAvailabilityConstraint(Constraint):
    """Ensures sessions are scheduled when the department is available."""

    def __init__(self, department_id: str):
        """
        Initialize department availability constraint.

        Args:
            department_id: The department ID this constraint applies to
        """
        self.department_id = department_id

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if assignment time is within department availability."""
        request = context.request_lookup.get(assignment.request_id)
        if not request or request.department_id != self.department_id:
            return None

        department = context.department_lookup.get(self.department_id)
        if not department:
            return None  # Cannot validate without department info

        # Get day of week
        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        day_of_week = day_names[assignment.start_time.weekday()]

        # Check if department is available on this day
        if not department.is_day_available(day_of_week):
            return Violation(
                constraint_type=self.constraint_type,
                affected_request_id=assignment.request_id,
                message=(
                    f"Department {department.name} ({self.department_id}) "
                    f"is not available on {day_of_week.capitalize()} for session {assignment.request_id}"
                ),
            )

        # Check department's preferred times if specified
        preferred_times = department.preferred_times.get(day_of_week.lower(), [])
        if preferred_times:
            # Simple check - in production, you'd parse times properly
            # For now, assume any time is within preferred times if they exist
            # This could be enhanced with actual time range checking
            pass  # Placeholder for time range checking

        return None

    def explain(self, violation: Violation) -> str:
        """Generate human-readable explanation."""
        return violation.message

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.department_availability"


class DepartmentPreferenceConstraint(Constraint):
    """Soft constraint encouraging department preferences for building and room types."""

    def __init__(self, department_id: str, weight: float = 1.0):
        """
        Initialize department preference constraint.

        Args:
            department_id: The department ID this constraint applies to
            weight: Weight of this preference (higher = more important)
        """
        self.department_id = department_id
        self.weight = weight

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check department preferences (soft constraint - returns None)."""
        # This is a soft constraint, so we don't return violations
        # The preference information could be used by the solver's objective function
        return None

    def explain(self, violation: Violation) -> str:
        """Generate human-readable explanation."""
        return violation.message

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "soft.department_preference"


@dataclass
class ResourceCost:
    """Cost information for a resource."""

    hourly_rate: float
    setup_cost: float = 0.0
    cleaning_cost: float = 0.0
    maintenance_cost: float = 0.0


@dataclass
class DepartmentBudget:
    """Department budget allocation."""

    department_id: str
    total_budget: float
    allocated_budget: float = 0.0
    cost_centers: Dict[str, float] = None
    restrictions: Dict[str, any] = None

    def __post_init__(self):
        if self.cost_centers is None:
            self.cost_centers = {}
        if self.restrictions is None:
            self.restrictions = {}


class DepartmentBudgetConstraint(Constraint):
    """Ensures departments stay within their allocated budgets."""

    def __init__(
        self,
        department_budgets: List[DepartmentBudget],
        resource_costs: Dict[str, ResourceCost],
        violation_penalty: float = 1000.0,
    ):
        """Initialize department budget constraint.

        Args:
            department_budgets: List of department budget allocations
            resource_costs: Cost information for each resource
            violation_penalty: Penalty for budget violations
        """
        super().__init__("department_budget", violation_penalty)
        self.department_budgets = {db.department_id: db for db in department_budgets}
        self.resource_costs = resource_costs

    def check(
        self,
        assignment: "Assignment",
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if assignment violates department budget."""
        # Get department from request
        department_id = getattr(assignment.request, "department_id", None)
        if not department_id or department_id not in self.department_budgets:
            return None

        budget = self.department_budgets[department_id]
        resource_id = str(assignment.resource.id)

        # Get resource cost
        resource_cost = self.resource_costs.get(resource_id)
        if not resource_cost:
            return None

        # Calculate total cost for this assignment
        duration_hours = float(assignment.request.duration)
        total_cost = (
            resource_cost.hourly_rate * duration_hours
            + resource_cost.setup_cost
            + resource_cost.cleaning_cost
        )

        # Calculate current department usage
        current_usage = self._calculate_department_usage(
            department_id,
            context.current_assignments,
            assignment,
        )

        # Check budget violation
        if current_usage + total_cost > budget.total_budget:
            return Violation(
                constraint=self,
                assignment=assignment,
                message=(
                    f"Department {department_id} budget exceeded: "
                    f"${current_usage + total_cost:.2f} > ${budget.total_budget:.2f}"
                ),
                details={
                    "department_id": department_id,
                    "current_usage": current_usage,
                    "assignment_cost": total_cost,
                    "total_cost": current_usage + total_cost,
                    "budget_limit": budget.total_budget,
                    "over_budget": (current_usage + total_cost) - budget.total_budget,
                },
            )

        return None

    def _calculate_department_usage(
        self,
        department_id: str,
        existing_assignments: List["Assignment"],
        new_assignment: Optional["Assignment"] = None,
    ) -> float:
        """Calculate current department resource usage."""
        total_cost = 0.0

        # Calculate cost for existing assignments
        for assignment in existing_assignments:
            if getattr(assignment.request, "department_id", None) == department_id:
                resource_id = str(assignment.resource.id)
                resource_cost = self.resource_costs.get(resource_id)
                if resource_cost:
                    duration = float(assignment.request.duration)
                    total_cost += (
                        resource_cost.hourly_rate * duration
                        + resource_cost.setup_cost
                        + resource_cost.cleaning_cost
                    )

        # Add cost for new assignment
        if (
            new_assignment
            and getattr(new_assignment.request, "department_id", None) == department_id
        ):
            resource_id = str(new_assignment.resource.id)
            resource_cost = self.resource_costs.get(resource_id)
            if resource_cost:
                duration = float(new_assignment.request.duration)
                total_cost += (
                    resource_cost.hourly_rate * duration
                    + resource_cost.setup_cost
                    + resource_cost.cleaning_cost
                )

        return total_cost


class ResourceSharingConstraint(Constraint):
    """Manages cost allocation for shared resources between departments."""

    def __init__(
        self,
        sharing_rules: Dict[str, Dict[str, float]],
        cost_sharing_method: str = "proportional",
        violation_penalty: float = 500.0,
    ):
        """Initialize resource sharing constraint.

        Args:
            sharing_rules: Resource ID -> {department_id: share_percentage}
            cost_sharing_method: How to share costs
            violation_penalty: Penalty for sharing violations
        """
        super().__init__("resource_sharing", violation_penalty)
        self.sharing_rules = sharing_rules
        self.cost_sharing_method = cost_sharing_method

    def check(
        self,
        assignment: "Assignment",
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if resource sharing rules are followed."""
        resource_id = str(assignment.resource.id)
        department_id = getattr(assignment.request, "department_id", None)

        # Check if this is a shared resource
        if resource_id not in self.sharing_rules or not department_id:
            return None

        sharing_rule = self.sharing_rules[resource_id]
        if department_id not in sharing_rule:
            return Violation(
                constraint=self,
                assignment=assignment,
                message=(
                    f"Department {department_id} not authorized to use "
                    f"shared resource {resource_id}"
                ),
                details={
                    "resource_id": resource_id,
                    "department_id": department_id,
                    "authorized_departments": list(sharing_rule.keys()),
                },
            )

        return None
