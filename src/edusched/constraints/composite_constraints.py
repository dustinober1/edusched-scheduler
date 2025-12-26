"""Composite constraint implementations."""

from typing import TYPE_CHECKING, List, Optional
from edusched.constraints.base import Constraint, ConstraintContext, Violation

if TYPE_CHECKING:
    from edusched.domain.assignment import Assignment


class CompositeConstraint(Constraint):
    """Base class for composite constraints that combine multiple constraints."""
    
    def __init__(self, child_constraints: List[Constraint]):
        self.child_constraints = child_constraints

    def check(
        self,
        assignment: "Assignment",
        solution: List["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """
        Base implementation - should be overridden by subclasses.
        """
        raise NotImplementedError("CompositeConstraint is an abstract class")

    def explain(self, violation: Violation) -> str:
        """Explain the composite constraint violation."""
        return f"Composite constraint violated: {violation.message}"

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "composite.base"


class AndConstraint(CompositeConstraint):
    """All child constraints must be satisfied."""

    def check(
        self,
        assignment: "Assignment",
        solution: List["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if all child constraints are satisfied."""
        for constraint in self.child_constraints:
            violation = constraint.check(assignment, solution, context)
            if violation:
                return Violation(
                    constraint_type=self.constraint_type,
                    affected_request_id=assignment.request_id,
                    message=f"AND constraint failed: {violation.message}",
                )
        
        return None

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "composite.and"


class OrConstraint(CompositeConstraint):
    """At least one child constraint must be satisfied."""

    def check(
        self,
        assignment: "Assignment",
        solution: List["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if at least one child constraint is satisfied."""
        violations = []
        
        for constraint in self.child_constraints:
            violation = constraint.check(assignment, solution, context)
            if violation:
                violations.append(violation)
        
        # If all constraints were violated, the OR constraint is violated
        if len(violations) == len(self.child_constraints):
            return Violation(
                constraint_type=self.constraint_type,
                affected_request_id=assignment.request_id,
                message=f"OR constraint failed: all {len(violations)} child constraints violated",
            )
        
        return None

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "composite.or"


class NotConstraint(CompositeConstraint):
    """Negation of a constraint - the child constraint must be violated."""

    def check(
        self,
        assignment: "Assignment",
        solution: List["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if the negated constraint is satisfied (meaning this constraint is violated)."""
        if len(self.child_constraints) != 1:
            raise ValueError("NotConstraint must have exactly one child constraint")
        
        constraint = self.child_constraints[0]
        violation = constraint.check(assignment, solution, context)
        
        # If the child constraint is satisfied, then the NOT constraint is violated
        # If the child constraint is violated, then the NOT constraint is satisfied
        if violation is None:
            return Violation(
                constraint_type=self.constraint_type,
                affected_request_id=assignment.request_id,
                message=f"NOT constraint failed: child constraint was satisfied",
            )
        
        return None

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "composite.not"


class XorConstraint(CompositeConstraint):
    """Exactly one child constraint must be satisfied."""

    def check(
        self,
        assignment: "Assignment",
        solution: List["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if exactly one child constraint is satisfied."""
        satisfied_count = 0
        
        for constraint in self.child_constraints:
            violation = constraint.check(assignment, solution, context)
            if violation is None:  # Constraint is satisfied
                satisfied_count += 1
        
        if satisfied_count != 1:
            return Violation(
                constraint_type=self.constraint_type,
                affected_request_id=assignment.request_id,
                message=f"XOR constraint failed: {satisfied_count} constraints satisfied (exactly 1 required)",
            )
        
        return None

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "composite.xor"


class ConstraintBuilder:
    """Helper class to build complex composite constraints."""
    
    def __init__(self):
        self.constraints = []
    
    def add_constraint(self, constraint: Constraint) -> "ConstraintBuilder":
        """Add a constraint to the builder."""
        self.constraints.append(constraint)
        return self
    
    def and_constraint(self) -> "AndConstraint":
        """Create an AND constraint from the collected constraints."""
        return AndConstraint(self.constraints)
    
    def or_constraint(self) -> "OrConstraint":
        """Create an OR constraint from the collected constraints."""
        return OrConstraint(self.constraints)
    
    def xor_constraint(self) -> "XorConstraint":
        """Create an XOR constraint from the collected constraints."""
        return XorConstraint(self.constraints)
    
    def not_constraint(self) -> "NotConstraint":
        """Create a NOT constraint from the first collected constraint."""
        if len(self.constraints) != 1:
            raise ValueError("NOT constraint builder must have exactly one constraint")
        return NotConstraint(self.constraints)