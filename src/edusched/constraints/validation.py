"""Constraint validation framework.

Provides comprehensive validation, dependency checking,
constraint composition, and validation reporting.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from edusched.constraints.base import Constraint, ConstraintContext, Violation


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ConstraintCategory(Enum):
    """Categories of constraints for organization."""

    HARD = "hard"  # Must be satisfied
    SOFT = "soft"  # Preference, can be violated with penalty
    DOMAIN = "domain"  # Domain-specific constraints
    TEMPORAL = "temporal"  # Time-related constraints
    RESOURCE = "resource"  # Resource allocation constraints
    CAPACITY = "capacity"  # Capacity and sizing constraints


@dataclass
class ValidationResult:
    """Result of constraint validation."""

    constraint_id: str
    constraint_name: str
    constraint_category: ConstraintCategory
    severity: ValidationSeverity
    is_valid: bool
    violations: List[Violation] = field(default_factory=list)
    execution_time_ms: float = 0.0
    message: str = ""
    suggestions: List[str] = field(default_factory=list)

    # Performance metrics
    checks_performed: int = 0
    cache_hits: int = 0

    # Context information
    affected_entities: Set[str] = field(default_factory=set)
    dependency_chain: List[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    """Comprehensive validation report for a problem or solution."""

    problem_id: Optional[str] = None
    validation_date: datetime = field(default_factory=datetime.now)
    total_constraints_checked: int = 0

    # Results by category
    results: List[ValidationResult] = field(default_factory=list)
    results_by_category: Dict[ConstraintCategory, List[ValidationResult]] = field(
        default_factory=dict
    )
    results_by_severity: Dict[ValidationSeverity, List[ValidationResult]] = field(
        default_factory=dict
    )

    # Summary statistics
    total_violations: int = 0
    critical_violations: int = 0
    error_violations: int = 0
    warning_count: int = 0

    # Performance metrics
    total_validation_time_ms: float = 0.0
    average_constraint_time_ms: float = 0.0

    # Recommendations
    top_issues: List[Tuple[int, str]] = field(default_factory=list)  # (severity_score, description)
    suggestions: List[str] = field(default_factory=list)
    fix_recommendations: Dict[str, List[str]] = field(default_factory=dict)


class ConstraintValidator:
    """Main constraint validation engine."""

    def __init__(self, enable_caching: bool = True, enable_parallel: bool = False):
        self.enable_caching = enable_caching
        self.enable_parallel = enable_parallel

        # Constraint registry
        self.constraints: Dict[str, Constraint] = {}
        self.constraint_dependencies: Dict[str, Set[str]] = field(default_factory=dict)
        self.constraint_categories: Dict[str, ConstraintCategory] = field(default_factory=dict)

        # Validation cache
        self.validation_cache: Dict[str, ValidationResult] = {}
        self.cache_ttl_minutes: int = 30
        self.last_cache_cleanup = datetime.now()

        # Performance tracking
        self.validation_history: List[ValidationReport] = []
        self.performance_stats: Dict[str, List[float]] = field(default_factory=dict)

    def register_constraint(
        self,
        constraint: Constraint,
        category: ConstraintCategory = ConstraintCategory.HARD,
        dependencies: List[str] = None,
    ) -> None:
        """Register a constraint for validation."""
        constraint_id = f"{category.value}_{constraint.constraint_type}"
        self.constraints[constraint_id] = constraint
        self.constraint_categories[constraint_id] = category

        if dependencies:
            self.constraint_dependencies[constraint_id] = set(dependencies)

    def unregister_constraint(self, constraint_id: str) -> None:
        """Remove a constraint from validation."""
        if constraint_id in self.constraints:
            del self.constraints[constraint_id]
            self.constraint_categories.pop(constraint_id, None)
            self.constraint_dependencies.pop(constraint_id, None)

    def validate_problem(
        self,
        problem: Any,
        context: ConstraintContext = None,
        constraint_filter: List[str] = None,
    ) -> ValidationReport:
        """Validate a problem (before solving)."""
        if context is None:
            context = ConstraintContext(
                problem=problem,
                request_lookup={r.id: r for r in problem.requests},
                resource_lookup={r.id: r for r in problem.resources},
            )

        start_time = datetime.now()
        report = ValidationReport(problem_id=getattr(problem, "id", None))

        # Get constraints to check
        constraints_to_check = self._get_constraints_to_check(constraint_filter)

        # Sort constraints by dependencies
        sorted_constraints = self._sort_constraints_by_dependencies(constraints_to_check)

        # Validate each constraint
        for constraint_id in sorted_constraints:
            constraint = self.constraints[constraint_id]
            category = self.constraint_categories[constraint_id]

            result = self._validate_constraint(
                constraint_id,
                constraint,
                category,
                context,
                is_problem_validation=True,
            )

            report.results.append(result)

            # Update category mapping
            if category not in report.results_by_category:
                report.results_by_category[category] = []
            report.results_by_category[category].append(result)

        # Calculate summary statistics
        report.total_constraints_checked = len(report.results)
        report.total_validation_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        report.average_constraint_time_ms = (
            report.total_validation_time_ms / report.total_constraints_checked
            if report.total_constraints_checked > 0
            else 0
        )

        # Categorize results by severity
        for result in report.results:
            if result.severity not in report.results_by_severity:
                report.results_by_severity[result.severity] = []
            report.results_by_severity[result.severity].append(result)

            report.total_violations += len(result.violations)
            if result.severity == ValidationSeverity.CRITICAL:
                report.critical_violations += len(result.violations)
            elif result.severity == ValidationSeverity.ERROR:
                report.error_violations += len(result.violations)
            elif result.severity == ValidationSeverity.WARNING:
                report.warning_count += 1

        # Generate recommendations
        report.top_issues = self._identify_top_issues(report.results)
        report.suggestions = self._generate_suggestions(report.results)
        report.fix_recommendations = self._generate_fix_recommendations(report.results)

        self.validation_history.append(report)
        return report

    def validate_solution(
        self,
        solution: List[Any],
        problem: Any,
        context: ConstraintContext = None,
        constraint_filter: List[str] = None,
    ) -> ValidationReport:
        """Validate a complete solution."""
        if context is None:
            context = ConstraintContext(
                problem=problem,
                request_lookup={r.id: r for r in problem.requests},
                resource_lookup={r.id: r for r in problem.resources},
                current_assignments=solution,
            )

        start_time = datetime.now()
        report = ValidationReport(problem_id=getattr(problem, "id", None))

        # Get constraints to check
        constraints_to_check = self._get_constraints_to_check(constraint_filter)

        # Sort constraints by dependencies
        sorted_constraints = self._sort_constraints_by_dependencies(constraints_to_check)

        # Validate each assignment against each constraint
        constraint_results = {cid: [] for cid in sorted_constraints}

        for assignment in solution:
            for constraint_id in sorted_constraints:
                constraint = self.constraints[constraint_id]
                category = self.constraint_categories[constraint_id]

                # Check if constraint applies to this assignment
                if self._constraint_applies(constraint, assignment, context):
                    result = self._validate_constraint(
                        constraint_id,
                        constraint,
                        category,
                        context,
                        assignment,
                    )

                    if result:
                        constraint_results[constraint_id].append(result)

        # Aggregate results by constraint
        for constraint_id, results in constraint_results.items():
            if results:
                # Combine results for the same constraint
                combined_result = self._combine_constraint_results(constraint_id, results)
                report.results.append(combined_result)

                category = self.constraint_categories[constraint_id]
                if category not in report.results_by_category:
                    report.results_by_category[category] = []
                report.results_by_category[category].append(combined_result)

        # Calculate summary statistics (similar to validate_problem)
        report.total_constraints_checked = len(constraint_results)
        report.total_validation_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        # Categorize results and count violations
        for result in report.results:
            if result.severity not in report.results_by_severity:
                report.results_by_severity[result.severity] = []
            report.results_by_severity[result.severity].append(result)

            report.total_violations += len(result.violations)
            if result.severity == ValidationSeverity.CRITICAL:
                report.critical_violations += len(result.violations)
            elif result.severity == ValidationSeverity.ERROR:
                report.error_violations += len(result.violations)
            elif result.severity == ValidationSeverity.WARNING:
                report.warning_count += 1

        # Generate recommendations
        report.top_issues = self._identify_top_issues(report.results)
        report.suggestions = self._generate_suggestions(report.results)
        report.fix_recommendations = self._generate_fix_recommendations(report.results)

        return report

    def _get_constraints_to_check(self, constraint_filter: List[str] = None) -> List[str]:
        """Get list of constraint IDs to check."""
        if constraint_filter:
            return [cid for cid in constraint_filter if cid in self.constraints]
        else:
            return list(self.constraints.keys())

    def _sort_constraints_by_dependencies(self, constraint_ids: List[str]) -> List[str]:
        """Sort constraints by their dependencies using topological sort."""
        # Build dependency graph
        graph = {cid: self.constraint_dependencies.get(cid, set()) for cid in constraint_ids}

        # Topological sort
        visited = set()
        temp_visited = set()
        sorted_constraints = []

        def visit(constraint_id: str):
            if constraint_id in temp_visited:
                raise ValueError(f"Circular dependency detected involving {constraint_id}")
            if constraint_id in visited:
                return

            temp_visited.add(constraint_id)
            for dep in graph[constraint_id]:
                if dep in constraint_ids:
                    visit(dep)
            temp_visited.remove(constraint_id)
            visited.add(constraint_id)
            sorted_constraints.append(constraint_id)

        for constraint_id in constraint_ids:
            if constraint_id not in visited:
                visit(constraint_id)

        return sorted_constraints

    def _validate_constraint(
        self,
        constraint_id: str,
        constraint: Constraint,
        category: ConstraintCategory,
        context: ConstraintContext,
        assignment: Any = None,
        is_problem_validation: bool = False,
    ) -> Optional[ValidationResult]:
        """Validate a single constraint."""
        # Check cache first
        cache_key = self._get_cache_key(constraint_id, context, assignment)
        if self.enable_caching and cache_key in self.validation_cache:
            cached_result = self.validation_cache[cache_key]
            # Check if cache is still valid
            if (
                datetime.now() - cached_result.execution_time_ms
            ).seconds < self.cache_ttl_minutes * 60:
                cached_result.cache_hits += 1
                return cached_result

        start_time = datetime.now()

        try:
            # Run constraint check
            if is_problem_validation:
                # Problem-level validation (check constraint parameters)
                violation = None  # Most constraints don't have problem-level checks
            else:
                # Solution-level validation (check against assignments)
                violation = constraint.check(assignment, context.current_assignments, context)

            # Create validation result
            if violation:
                severity = self._determine_severity(violation, category)
                result = ValidationResult(
                    constraint_id=constraint_id,
                    constraint_name=constraint.constraint_type,
                    constraint_category=category,
                    severity=severity,
                    is_valid=False,
                    violations=[violation],
                    execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                    message=f"Constraint violated: {violation.message}",
                    affected_entities={str(violation.assignment.resource.id)}
                    if violation.assignment
                    else set(),
                )
            else:
                result = ValidationResult(
                    constraint_id=constraint_id,
                    constraint_name=constraint.constraint_type,
                    constraint_category=category,
                    severity=ValidationSeverity.INFO,
                    is_valid=True,
                    execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                    message="Constraint satisfied",
                )

            # Cache result
            if self.enable_caching:
                self.validation_cache[cache_key] = result

            # Track performance
            if constraint_id not in self.performance_stats:
                self.performance_stats[constraint_id] = []
            self.performance_stats[constraint_id].append(result.execution_time_ms)

            return result

        except Exception as e:
            # Handle validation errors gracefully
            return ValidationResult(
                constraint_id=constraint_id,
                constraint_name=constraint.constraint_type,
                constraint_category=category,
                severity=ValidationSeverity.ERROR,
                is_valid=False,
                execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                message=f"Validation error: {str(e)}",
                suggestions=["Check constraint implementation", "Verify input data"],
            )

    def _get_cache_key(
        self, constraint_id: str, context: ConstraintContext, assignment: Any = None
    ) -> str:
        """Generate cache key for validation result."""
        # Simple hash-based key - in production, use more sophisticated hashing
        key_parts = [constraint_id, str(len(context.current_assignments))]
        if assignment:
            key_parts.append(str(assignment.id))
        return hash("_".join(key_parts))

    def _constraint_applies(
        self, constraint: Constraint, assignment: Any, context: ConstraintContext
    ) -> bool:
        """Check if constraint applies to this assignment."""
        # Most constraints apply to all assignments
        # Override in subclasses for specific filtering
        return True

    def _combine_constraint_results(
        self, constraint_id: str, results: List[ValidationResult]
    ) -> ValidationResult:
        """Combine multiple validation results for the same constraint."""
        if not results:
            return None

        # Use the most severe result as the primary
        severity_order = {
            ValidationSeverity.CRITICAL: 4,
            ValidationSeverity.ERROR: 3,
            ValidationSeverity.WARNING: 2,
            ValidationSeverity.INFO: 1,
        }

        primary_result = max(results, key=lambda r: severity_order.get(r.severity, 0))

        # Combine violations
        all_violations = []
        affected_entities = set()
        all_suggestions = set()

        for result in results:
            all_violations.extend(result.violations)
            affected_entities.update(result.affected_entities)
            all_suggestions.update(result.suggestions)

        # Create combined result
        combined = ValidationResult(
            constraint_id=constraint_id,
            constraint_name=primary_result.constraint_name,
            constraint_category=primary_result.constraint_category,
            severity=primary_result.severity,
            is_valid=primary_result.is_valid,
            violations=all_violations,
            execution_time_ms=sum(r.execution_time_ms for r in results),
            message=f"{len(all_violations)} violation(s) found for {constraint_id}",
            suggestions=list(all_suggestions),
            checks_performed=len(results),
            affected_entities=affected_entities,
        )

        return combined

    def _determine_severity(
        self, violation: Violation, category: ConstraintCategory
    ) -> ValidationSeverity:
        """Determine validation severity based on violation and category."""
        # Hard constraints are critical or errors
        if category == ConstraintCategory.HARD:
            return ValidationSeverity.CRITICAL
        # Soft constraints are warnings or info
        elif category == ConstraintCategory.SOFT:
            return ValidationSeverity.WARNING
        # Domain constraints are errors
        elif category == ConstraintCategory.DOMAIN:
            return ValidationSeverity.ERROR
        # Others default to error
        else:
            return ValidationSeverity.ERROR

    def _identify_top_issues(self, results: List[ValidationResult]) -> List[Tuple[int, str]]:
        """Identify top issues from validation results."""
        issues = []

        for result in results:
            if not result.is_valid:
                # Score based on severity and number of violations
                severity_score = {
                    ValidationSeverity.CRITICAL: 10,
                    ValidationSeverity.ERROR: 5,
                    ValidationSeverity.WARNING: 2,
                    ValidationSeverity.INFO: 1,
                }.get(result.severity, 1)

                total_score = severity_score * len(result.violations)
                description = f"{result.constraint_name}: {len(result.violations)} violation(s)"

                issues.append((total_score, description))

        # Sort by score (descending) and return top 10
        issues.sort(key=lambda x: x[0], reverse=True)
        return issues[:10]

    def _generate_suggestions(self, results: List[ValidationResult]) -> List[str]:
        """Generate general suggestions from validation results."""
        suggestions = []

        # Count issues by category
        category_issues = {}
        for result in results:
            if not result.is_valid:
                category = result.constraint_category.value
                category_issues[category] = category_issues.get(category, 0) + len(
                    result.violations
                )

        # Generate category-specific suggestions
        if category_issues.get("hard", 0) > 0:
            suggestions.append("Review hard constraints - these must be satisfied")
        if category_issues.get("capacity", 0) > 0:
            suggestions.append("Consider increasing resource capacity or reducing enrollment")
        if category_issues.get("temporal", 0) > 0:
            suggestions.append("Adjust time windows or extend scheduling period")

        return suggestions

    def _generate_fix_recommendations(
        self, results: List[ValidationResult]
    ) -> Dict[str, List[str]]:
        """Generate specific fix recommendations for constraint violations."""
        recommendations = {}

        for result in results:
            if not result.is_valid and result.violations:
                constraint_recommendations = []

                for violation in result.violations:
                    # Generate recommendations based on violation type
                    if "capacity" in violation.message.lower():
                        constraint_recommendations.append("Use larger room or reduce class size")
                    elif "overlap" in violation.message.lower():
                        constraint_recommendations.append(
                            "Check for double bookings or adjust time slots"
                        )
                    elif "availability" in violation.message.lower():
                        constraint_recommendations.append(
                            "Verify resource availability or reschedule"
                        )
                    elif "preference" in violation.message.lower():
                        constraint_recommendations.append(
                            "Consider relaxing preferences or finding alternatives"
                        )

                recommendations[result.constraint_id] = constraint_recommendations

        return recommendations


class ConstraintComposer:
    """Helps compose complex constraints from simpler ones."""

    @staticmethod
    def create_composite_constraint(
        constraints: List[Constraint],
        operator: str = "AND",  # AND, OR, XOR
        weights: List[float] = None,
    ) -> Constraint:
        """Create a composite constraint from multiple constraints."""
        # This would return a new constraint class that combines the given ones
        # Implementation would depend on specific constraint composition requirements
        pass

    @staticmethod
    def create_conditional_constraint(
        condition: callable,
        true_constraint: Constraint,
        false_constraint: Optional[Constraint] = None,
    ) -> Constraint:
        """Create a constraint that applies conditionally."""
        # Returns a constraint that checks the condition and applies the appropriate constraint
        pass


# Predefined constraint sets for common scenarios
class ConstraintPresets:
    """Predefined constraint configurations for common scheduling scenarios."""

    @staticmethod
    def get_academic_constraints() -> List[Tuple[str, ConstraintCategory]]:
        """Get standard constraints for academic scheduling."""
        # Would return a list of (constraint_name, category) tuples
        # Implementation would instantiate the appropriate constraint classes
        pass

    @staticmethod
    def get_conference_constraints() -> List[Tuple[str, ConstraintCategory]]:
        """Get constraints for conference scheduling."""
        pass

    @staticmethod
    def get_exam_constraints() -> List[Tuple[str, ConstraintCategory]]:
        """Get constraints for exam scheduling."""
        pass
