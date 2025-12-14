"""Optimization configuration and preferences domain models.

Handles solver settings, optimization objectives, and performance metrics.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from edusched.domain.base import BaseEntity


@dataclass
class OptimizationObjective(BaseEntity):
    """Represents an optimization objective."""

    name: str
    objective_type: str  # minimize, maximize, satisfy
    weight: float = 1.0  # Relative importance
    target_value: Optional[float] = None
    tolerance: float = 0.0  # Acceptable deviation from target
    enabled: bool = True
    description: str = ""

    # Objective-specific parameters
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SolverConfiguration(BaseEntity):
    """Configuration for a specific solver."""

    solver_name: str  # heuristic, ortools, cp, milp, etc.
    parameters: Dict[str, Any] = field(default_factory=dict)
    time_limit_seconds: int = 300
    solution_limit: Optional[int] = None
    gap_tolerance: float = 0.01
    random_seed: Optional[int] = None
    parallel_threads: int = 1
    enable_logging: bool = True
    log_level: str = "INFO"

    # Solver-specific settings
    heuristic_beam_width: int = 100
    ortools_solver_specific: str = "SAT"  # SAT, CP-SAT, GLOP, etc.
    local_search_enabled: bool = True
    tabu_tenure: int = 10


@dataclass
class OptimizationMetrics(BaseEntity):
    """Metrics for optimization performance."""

    solver_name: str
    problem_size: int  # Number of variables/constraints
    solve_time_seconds: float
    solution_quality: float  # 0-1 score
    objective_value: float
    iterations: int = 0
    backtracks: int = 0
    nodes_explored: int = 0

    # Quality indicators
    constraints_satisfied: int = 0
    constraints_violated: int = 0
    penalty_score: float = 0.0

    # Resource usage
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0

    # Solution diversity
    alternative_solutions: int = 0
    pareto_optimal: bool = False


@dataclass
class OptimizationProfile(BaseEntity):
    """Pre-configured optimization profile for different scenarios."""

    name: str
    description: str
    objectives: List[OptimizationObjective] = field(default_factory=list)
    solver_config: Optional[SolverConfiguration] = None

    # Profile characteristics
    scenario_type: str  # academic, conference, event, hybrid
    institution_size: str  # small, medium, large, enterprise
    priority_order: List[str] = field(default_factory=list)

    # Performance targets
    max_solve_time_seconds: int = 600
    min_solution_quality: float = 0.8

    # Special settings
    prefer_faster_solutions: bool = False
    allow_approximate: bool = False
    incremental_optimization: bool = True


class OptimizationManager:
    """Manages optimization settings and profiles."""

    def __init__(self):
        self.profiles: Dict[str, OptimizationProfile] = {}
        self.metrics_history: List[OptimizationMetrics] = []
        self.default_objectives: List[OptimizationObjective] = []

    def add_profile(self, profile: OptimizationProfile) -> None:
        """Add an optimization profile."""
        self.profiles[profile.id] = profile

    def get_profile(self, profile_id: str) -> Optional[OptimizationProfile]:
        """Get optimization profile by ID."""
        return self.profiles.get(profile_id)

    def create_default_profiles(self) -> None:
        """Create default optimization profiles."""
        # Fast profile for quick scheduling
        fast_profile = OptimizationProfile(
            id="fast",
            name="Fast Scheduling",
            description="Quick scheduling with basic constraints",
            scenario_type="academic",
            institution_size="small",
            prefer_faster_solutions=True,
            max_solve_time_seconds=60,
            objectives=[
                OptimizationObjective(
                    id="min_conflicts",
                    name="Minimize Conflicts",
                    objective_type="minimize",
                    weight=10.0,
                ),
                OptimizationObjective(
                    id="spread_sessions",
                    name="Even Distribution",
                    objective_type="satisfy",
                    weight=1.0,
                ),
            ],
        )

        # Balanced profile
        balanced_profile = OptimizationProfile(
            id="balanced",
            name="Balanced Optimization",
            description="Balanced solution with good quality and reasonable speed",
            scenario_type="academic",
            institution_size="medium",
            max_solve_time_seconds=300,
            min_solution_quality=0.7,
            objectives=[
                OptimizationObjective(
                    id="min_conflicts",
                    name="Minimize Conflicts",
                    objective_type="minimize",
                    weight=8.0,
                ),
                OptimizationObjective(
                    id="room_utilization",
                    name="Maximize Room Utilization",
                    objective_type="maximize",
                    weight=3.0,
                ),
                OptimizationObjective(
                    id="teacher_preferences",
                    name="Satisfy Teacher Preferences",
                    objective_type="satisfy",
                    weight=2.0,
                ),
                OptimizationObjective(
                    id="student_walking",
                    name="Minimize Walking Distance",
                    objective_type="minimize",
                    weight=1.5,
                ),
            ],
        )

        # Quality profile for optimal solutions
        quality_profile = OptimizationProfile(
            id="quality",
            name="Optimal Quality",
            description="Maximum quality optimization with time limit",
            scenario_type="academic",
            institution_size="large",
            max_solve_time_seconds=1800,
            min_solution_quality=0.95,
            prefer_faster_solutions=False,
            objectives=[
                OptimizationObjective(
                    id="min_conflicts",
                    name="Minimize Conflicts",
                    objective_type="minimize",
                    weight=10.0,
                ),
                OptimizationObjective(
                    id="room_utilization",
                    name="Maximize Room Utilization",
                    objective_type="maximize",
                    weight=5.0,
                ),
                OptimizationObjective(
                    id="teacher_preferences",
                    name="Satisfy Teacher Preferences",
                    objective_type="satisfy",
                    weight=4.0,
                ),
                OptimizationObjective(
                    id="student_walking",
                    name="Minimize Walking Distance",
                    objective_type="minimize",
                    weight=3.0,
                ),
                OptimizationObjective(
                    id="department_budgets",
                    name="Respect Department Budgets",
                    objective_type="satisfy",
                    weight=5.0,
                ),
                OptimizationObjective(
                    id="equipment_sharing",
                    name="Optimize Equipment Sharing",
                    objective_type="maximize",
                    weight=2.0,
                ),
            ],
        )

        self.profiles.update(
            {
                "fast": fast_profile,
                "balanced": balanced_profile,
                "quality": quality_profile,
            }
        )

    def record_metrics(self, metrics: OptimizationMetrics) -> None:
        """Record optimization metrics."""
        self.metrics_history.append(metrics)

    def get_solver_performance(self, solver_name: str, days: int = 30) -> Dict[str, float]:
        """Get performance statistics for a solver."""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_metrics = [
            m
            for m in self.metrics_history
            if m.solver_name == solver_name
            and hasattr(m, "timestamp")
            and getattr(m, "timestamp", datetime.now()) > cutoff_date
        ]

        if not recent_metrics:
            return {}

        return {
            "avg_solve_time": sum(m.solve_time_seconds for m in recent_metrics)
            / len(recent_metrics),
            "avg_solution_quality": sum(m.solution_quality for m in recent_metrics)
            / len(recent_metrics),
            "success_rate": sum(1 for m in recent_metrics if m.solution_quality > 0.5)
            / len(recent_metrics),
            "total_solves": len(recent_metrics),
        }

    def suggest_solver(self, problem_size: int, time_limit: int, quality_required: float) -> str:
        """Suggest best solver based on problem characteristics."""
        if problem_size < 100 and time_limit < 60:
            return "heuristic"
        elif problem_size < 1000 and time_limit < 300:
            return "ortools"
        elif quality_required > 0.9 and time_limit > 600:
            return "ortools"
        else:
            return "heuristic"


@dataclass
class OptimizationResult(BaseEntity):
    """Complete result of optimization including metrics and alternatives."""

    primary_solution: Dict[str, Any]  # The main solution
    alternative_solutions: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Optional[OptimizationMetrics] = None
    constraint_violations: List[Dict[str, Any]] = field(default_factory=list)
    optimization_stats: Dict[str, Any] = field(default_factory=dict)

    # Solution quality indicators
    feasibility_score: float = 1.0  # 0-1, 1 = fully feasible
    objective_score: float = 0.0  # Optimized objective value
    diversity_score: float = 0.0  # How different from alternatives

    # Confidence measures
    confidence_level: float = 1.0  # 0-1, solver confidence
    stability_score: float = 1.0  # 0-1, how stable solution is to changes


@dataclass
class SensitivityAnalysis(BaseEntity):
    """Sensitivity analysis of optimization parameters."""

    parameter_name: str
    base_value: float
    tested_values: List[float]
    solution_impacts: List[float]  # Impact on objective value
    feasibility_changes: List[bool]  # Whether solution remained feasible
    recommended_range: Tuple[float, float]
    critical_threshold: Optional[float] = None


@dataclass
class OptimizationExperiment(BaseEntity):
    """Experiment comparing different optimization approaches."""

    name: str
    description: str
    experiment_type: str  # solver_comparison, parameter_tuning, objective_pareto

    # Experiment parameters
    solvers_tested: List[str]
    parameter_variations: List[Dict[str, Any]]
    objective_weights_tested: List[Dict[str, float]]

    # Results
    results: List[OptimizationResult] = field(default_factory=list)
    best_result: Optional[OptimizationResult] = None
    statistical_summary: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    # Experiment metadata
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    success: bool = False
