"""Blackout period constraints for room unavailability."""

from typing import TYPE_CHECKING, Optional

from edusched.constraints.base import Constraint, ConstraintContext, Violation

if TYPE_CHECKING:
    from edusched.domain.assignment import Assignment


class BlackoutDateConstraint(Constraint):
    """Prevents scheduling during blackout periods."""

    def __init__(self, resource_id: str):
        """
        Initialize blackout date constraint.

        Args:
            resource_id: The resource ID this constraint applies to
        """
        self.resource_id = resource_id

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if assignment conflicts with blackout periods."""
        # Get the resource
        resource = context.resource_lookup.get(self.resource_id)
        if not resource:
            return None

        # Check if the resource is assigned to this assignment
        assigned_resources = assignment.assigned_resources
        resource_assigned = False
        for _resource_type, resource_ids in assigned_resources.items():
            if self.resource_id in resource_ids:
                resource_assigned = True
                break

        if not resource_assigned:
            return None

        # Check availability (this will include blackout checks)
        is_available, reason = resource.is_available(assignment.start_time, assignment.end_time)

        if not is_available and "blackout" in reason.lower():
            return Violation(
                constraint_type=self.constraint_type,
                affected_request_id=assignment.request_id,
                affected_resource_id=self.resource_id,
                message=reason,
            )

        return None

    def explain(self, violation: Violation) -> str:
        """Provide explanation for blackout violation."""
        return f"Cannot schedule during blackout period: {violation.message}"

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.blackout_date"


class BuildingBlackoutConstraint(Constraint):
    """Prevents scheduling during building-wide blackout periods."""

    def __init__(self, building_id: str):
        """
        Initialize building blackout constraint.

        Args:
            building_id: The building ID this constraint applies to
        """
        self.building_id = building_id

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if assignment conflicts with building blackout periods."""
        # Get all assigned resources
        assigned_resources = assignment.assigned_resources
        building_resources = []

        # Find resources in this building
        for resource in context.resource_lookup.values():
            if resource.building_id == self.building_id:
                # Check if this resource is assigned
                for resource_ids in assigned_resources.values():
                    if resource.id in resource_ids:
                        building_resources.append(resource)
                        break

        if not building_resources:
            return None

        # Check each resource for blackout
        for resource in building_resources:
            is_available, reason = resource.is_available(assignment.start_time, assignment.end_time)

            if not is_available and "building blackout" in reason.lower():
                return Violation(
                    constraint_type=self.constraint_type,
                    affected_request_id=assignment.request_id,
                    affected_resource_id=resource.id,
                    message=f"Building blackout: {reason}",
                )

        return None

    def explain(self, violation: Violation) -> str:
        """Provide explanation for building blackout violation."""
        return f"Cannot schedule during building blackout: {violation.message}"

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.building_blackout"
