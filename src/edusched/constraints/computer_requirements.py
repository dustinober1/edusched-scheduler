"""Custom constraint for computer room requirements."""

from typing import TYPE_CHECKING, Any, List, Optional

from edusched.constraints.base import Constraint, ConstraintContext, Violation

if TYPE_CHECKING:
    from edusched.domain.assignment import Assignment


class ComputerRequirements(Constraint):
    """Ensures session requirements for computer facilities are met."""

    def __init__(self, request_id: str) -> None:
        self.request_id = request_id

    def check(
        self,
        assignment: "Assignment",
        solution: List["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if assigned room meets computer requirements."""
        if assignment.request_id != self.request_id:
            return None

        request = context.request_lookup.get(self.request_id)
        if not request:
            return None

        computer_req = request.required_attributes.get("computers")
        if computer_req is None:
            # No computer requirements
            return None

        # Check assigned rooms
        for _resource_type, resource_ids in assignment.assigned_resources.items():
            for resource_id in resource_ids:
                resource = context.resource_lookup.get(resource_id)
                if not resource:
                    continue

                resource_computers = resource.attributes.get("computers")

                # Handle different requirement patterns
                violation = self._check_requirement(computer_req, resource_computers, resource.id)
                if violation:
                    return violation

        return None

    def _check_requirement(
        self, requirement: Any, resource_computers: Any, resource_id: str
    ) -> Optional[Violation]:
        """Check if resource computers meet the requirement."""
        # Case 1: Explicitly no computers required
        if requirement is None:
            if resource_computers is not None and resource_computers.get("total", 0) > 0:
                return Violation(
                    constraint_type=self.constraint_type,
                    affected_request_id=self.request_id,
                    affected_resource_id=resource_id,
                    message=f"Room {resource_id} has computers but course requires no computers",
                )
            return None

        # Case 2: Min total computers
        if "min_total" in requirement:
            if resource_computers is None:
                return Violation(
                    constraint_type=self.constraint_type,
                    affected_request_id=self.request_id,
                    affected_resource_id=resource_id,
                    message=f"Room {resource_id} has no computers but course requires at least {requirement['min_total']}",
                )

            total_computers = resource_computers.get("total", 0)
            if total_computers < requirement["min_total"]:
                return Violation(
                    constraint_type=self.constraint_type,
                    affected_request_id=self.request_id,
                    affected_resource_id=resource_id,
                    message=f"Room {resource_id} has {total_computers} computers but course requires at least {requirement['min_total']}",
                )

        # Case 3: Specific type requirements (connected/standalone)
        for comp_type in ["connected", "standalone"]:
            if comp_type in requirement:
                required = requirement[comp_type]
                available = (
                    0 if resource_computers is None else resource_computers.get(comp_type, 0)
                )

                if isinstance(required, int):
                    if required > 0 and available < required:
                        return Violation(
                            constraint_type=self.constraint_type,
                            affected_request_id=self.request_id,
                            affected_resource_id=resource_id,
                            message=f"Room {resource_id} has {available} {comp_type} computers but course requires {required}",
                        )
                elif required == 0 and available > 0:
                    return Violation(
                        constraint_type=self.constraint_type,
                        affected_request_id=self.request_id,
                        affected_resource_id=resource_id,
                        message=f"Room {resource_id} has {available} {comp_type} computers but course requires no {comp_type} computers",
                    )

        # Case 4: Minimum total computers
        if "total" in requirement:
            if resource_computers is None:
                return Violation(
                    constraint_type=self.constraint_type,
                    affected_request_id=self.request_id,
                    affected_resource_id=resource_id,
                    message=f"Room {resource_id} has no computers but course requires {requirement['total']} total",
                )

            total_computers = resource_computers.get("total", 0)
            if total_computers < requirement["total"]:
                return Violation(
                    constraint_type=self.constraint_type,
                    affected_request_id=self.request_id,
                    affected_resource_id=resource_id,
                    message=f"Room {resource_id} has {total_computers} computers but course requires {requirement['total']}",
                )

        return None

    def explain(self, violation: Violation) -> str:
        """Generate human-readable explanation."""
        return violation.message

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.computer_requirements"


class AnyComputerAvailable(Constraint):
    """Constraint that ensures at least one room with computers is available in the solution."""

    def __init__(self, request_id: str, min_computers: int = 1) -> None:
        self.request_id = request_id
        self.min_computers = min_computers

    def check(
        self,
        assignment: "Assignment",
        solution: List["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if any computer-equipped room is available."""
        if assignment.request_id != self.request_id:
            return None

        # Check if this assignment is in a room with sufficient computers
        for _resource_type, resource_ids in assignment.assigned_resources.items():
            for resource_id in resource_ids:
                resource = context.resource_lookup.get(resource_id)
                if resource and resource.attributes.get("computers"):
                    total = resource.attributes["computers"].get("total", 0)
                    if total >= self.min_computers:
                        return None  # Found suitable room

        # No suitable room found
        return Violation(
            constraint_type=self.constraint_type,
            affected_request_id=self.request_id,
            message=f"No room with at least {self.min_computers} computers assigned",
        )

    def explain(self, violation: Violation) -> str:
        """Generate human-readable explanation."""
        return violation.message

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.any_computer_available"


class NoComputerRoom(Constraint):
    """Ensures session is scheduled in a room without computers."""

    def __init__(self, request_id: str) -> None:
        self.request_id = request_id

    def check(
        self,
        assignment: "Assignment",
        solution: List["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check that assigned room has no computers."""
        if assignment.request_id != self.request_id:
            return None

        for _resource_type, resource_ids in assignment.assigned_resources.items():
            for resource_id in resource_ids:
                resource = context.resource_lookup.get(resource_id)
                if resource and resource.attributes.get("computers"):
                    total = resource.attributes["computers"].get("total", 0)
                    if total > 0:
                        return Violation(
                            constraint_type=self.constraint_type,
                            affected_request_id=self.request_id,
                            affected_resource_id=resource_id,
                            message=f"Room {resource_id} has {total} computers but course requires no computers",
                        )

        return None

    def explain(self, violation: Violation) -> str:
        """Generate human-readable explanation."""
        return violation.message

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.no_computers"
