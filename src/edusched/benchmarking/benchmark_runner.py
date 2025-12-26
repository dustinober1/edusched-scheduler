"""Benchmarking infrastructure for EduSched solvers."""

import time
import statistics
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import json
import os

from edusched.domain.problem import Problem
from edusched.domain.result import Result
from edusched import solve


@dataclass
class BenchmarkResult:
    """Represents the result of a single benchmark run."""
    solver_name: str
    problem_size: int
    execution_time: float
    solution_quality: float
    memory_usage: Optional[float] = None
    success_rate: float = 1.0
    constraint_violations: int = 0
    run_timestamp: datetime = None
    
    def __post_init__(self):
        if self.run_timestamp is None:
            self.run_timestamp = datetime.now()


@dataclass
class BenchmarkSuiteResult:
    """Represents the aggregated results of a benchmark suite."""
    benchmark_name: str
    results: List[BenchmarkResult]
    summary_stats: Dict[str, Any]
    
    def __post_init__(self):
        self.calculate_summary_stats()
    
    def calculate_summary_stats(self):
        """Calculate summary statistics for the benchmark results."""
        if not self.results:
            self.summary_stats = {}
            return
        
        # Execution time statistics
        execution_times = [r.execution_time for r in self.results]
        self.summary_stats = {
            "execution_time": {
                "mean": statistics.mean(execution_times),
                "median": statistics.median(execution_times),
                "stdev": statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
                "min": min(execution_times),
                "max": max(execution_times),
            },
            "solution_quality": {
                "mean": statistics.mean([r.solution_quality for r in self.results]),
                "median": statistics.median([r.solution_quality for r in self.results]),
            },
            "success_rate": statistics.mean([r.success_rate for r in self.results]),
            "constraint_violations": {
                "total": sum(r.constraint_violations for r in self.results),
                "mean": statistics.mean([r.constraint_violations for r in self.results]),
            },
            "total_runs": len(self.results),
        }


class ProblemGenerator:
    """Generates standardized problems for benchmarking."""
    
    @staticmethod
    def generate_small_problem() -> Problem:
        """Generate a small benchmark problem."""
        from edusched.domain import SessionRequest, Resource, Calendar
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        
        # Create a simple calendar
        calendar = Calendar(
            id="benchmark-cal",
            timezone=ZoneInfo("UTC")
        )
        
        # Create resources
        resources = [
            Resource(id=f"room-{i}", resource_type="classroom", capacity=30)
            for i in range(5)
        ]
        
        # Create requests
        requests = [
            SessionRequest(
                id=f"req-{i}",
                duration=timedelta(hours=1),
                number_of_occurrences=10,
                earliest_date=datetime(2024, 1, 1, tzinfo=ZoneInfo("UTC")),
                latest_date=datetime(2024, 6, 1, tzinfo=ZoneInfo("UTC")),
                enrollment_count=25
            )
            for i in range(8)
        ]
        
        return Problem(
            requests=requests,
            resources=resources,
            calendars=[calendar],
            constraints=[]
        )
    
    @staticmethod
    def generate_medium_problem() -> Problem:
        """Generate a medium benchmark problem."""
        from edusched.domain import SessionRequest, Resource, Calendar
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        
        # Create a calendar
        calendar = Calendar(
            id="benchmark-cal",
            timezone=ZoneInfo("UTC")
        )
        
        # Create more resources
        resources = [
            Resource(id=f"room-{i}", resource_type="classroom", capacity=min(20 + i * 5, 100))
            for i in range(15)
        ]
        # Add some special resources
        resources.extend([
            Resource(id=f"lab-{i}", resource_type="lab", capacity=20, 
                    attributes={"computer_lab": True})
            for i in range(5)
        ])
        
        # Create more requests
        requests = [
            SessionRequest(
                id=f"req-{i}",
                duration=timedelta(hours=1, minutes=30),
                number_of_occurrences=14,
                earliest_date=datetime(2024, 1, 1, tzinfo=ZoneInfo("UTC")),
                latest_date=datetime(2024, 6, 1, tzinfo=ZoneInfo("UTC")),
                enrollment_count=min(15 + i * 2, 50),
                required_attributes={"computer_lab": True} if i % 5 == 0 else {}
            )
            for i in range(25)
        ]
        
        return Problem(
            requests=requests,
            resources=resources,
            calendars=[calendar],
            constraints=[]
        )
    
    @staticmethod
    def generate_large_problem() -> Problem:
        """Generate a large benchmark problem."""
        from edusched.domain import SessionRequest, Resource, Calendar
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        
        # Create calendars
        calendar = Calendar(
            id="benchmark-cal",
            timezone=ZoneInfo("UTC")
        )
        
        # Create many resources
        resources = []
        for i in range(50):
            resource_type = "classroom" if i < 30 else "lab" if i < 40 else "seminar"
            capacity = 20 + (i % 10) * 10
            attributes = {}
            if resource_type == "lab":
                attributes = {"computer_lab": True, "projector": True}
            elif resource_type == "seminar":
                attributes = {"conference": True}
                
            resources.append(
                Resource(id=f"res-{i}", resource_type=resource_type, 
                        capacity=capacity, attributes=attributes)
            )
        
        # Create many requests
        requests = []
        for i in range(100):
            duration = timedelta(hours=1) if i % 3 == 0 else timedelta(hours=1, minutes=30)
            enrollment = 10 + (i % 20) * 3
            required_attrs = {}
            if i % 4 == 0:
                required_attrs = {"computer_lab": True}
            elif i % 5 == 0:
                required_attrs = {"projector": True}
                
            requests.append(
                SessionRequest(
                    id=f"req-{i}",
                    duration=duration,
                    number_of_occurrences=20,
                    earliest_date=datetime(2024, 1, 1, tzinfo=ZoneInfo("UTC")),
                    latest_date=datetime(2024, 12, 1, tzinfo=ZoneInfo("UTC")),
                    enrollment_count=enrollment,
                    required_attributes=required_attrs
                )
            )
        
        return Problem(
            requests=requests,
            resources=resources,
            calendars=[calendar],
            constraints=[]
        )


class BenchmarkRunner:
    """Runs benchmarks on different solvers."""
    
    def __init__(self):
        self.problem_generator = ProblemGenerator()
    
    def run_single_benchmark(self, problem: Problem, solver_backend: str = "auto") -> BenchmarkResult:
        """Run a single benchmark on a problem with a specific solver."""
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        try:
            result = solve(problem, backend=solver_backend)
            
            execution_time = time.time() - start_time
            memory_used = self._get_memory_usage() - start_memory
            
            # Calculate solution quality (higher is better, with 0 being perfect)
            solution_quality = self._calculate_solution_quality(result, problem)
            
            # Count constraint violations
            constraint_violations = len(result.assignments) if result.status == "infeasible" else 0
            
            return BenchmarkResult(
                solver_name=solver_backend,
                problem_size=len(problem.requests) + len(problem.resources),
                execution_time=execution_time,
                solution_quality=solution_quality,
                memory_usage=memory_used,
                success_rate=1.0 if result.status in ["feasible", "partial"] else 0.0,
                constraint_violations=constraint_violations
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return BenchmarkResult(
                solver_name=solver_backend,
                problem_size=len(problem.requests) + len(problem.resources),
                execution_time=execution_time,
                solution_quality=float('-inf'),  # Worst possible score
                success_rate=0.0,
                constraint_violations=float('inf')
            )
    
    def run_benchmark_suite(self, 
                          solver_backends: List[str],
                          problems: List[Problem],
                          runs_per_problem: int = 3) -> BenchmarkSuiteResult:
        """Run a comprehensive benchmark suite."""
        all_results = []
        
        for solver in solver_backends:
            for problem in problems:
                for run in range(runs_per_problem):
                    result = self.run_single_benchmark(problem, solver)
                    all_results.append(result)
        
        return BenchmarkSuiteResult(
            benchmark_name=f"comprehensive_suite_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            results=all_results,
            summary_stats={}
        )
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB. This is a simplified version."""
        # In a real implementation, we'd use psutil or similar
        # For now, return 0 to indicate that memory tracking is not implemented
        return 0.0
    
    def _calculate_solution_quality(self, result: Result, problem: Problem) -> float:
        """Calculate a quality score for the solution."""
        if result.status == "infeasible":
            return float('-inf')
        
        # Calculate based on number of scheduled requests vs total requests
        scheduled_ratio = len(result.assignments) / max(len(problem.requests), 1)
        
        # Calculate resource utilization
        if result.assignments:
            # Simple utilization calculation
            total_resource_hours = sum(
                (a.end_time - a.start_time).total_seconds() / 3600 
                for a in result.assignments
            )
            # This is a simplified calculation
            utilization_score = min(total_resource_hours / 100.0, 1.0)  # Normalize
            return scheduled_ratio + utilization_score
        else:
            return 0.0


class BenchmarkReporter:
    """Generates reports from benchmark results."""
    
    def generate_text_report(self, suite_result: BenchmarkSuiteResult) -> str:
        """Generate a text-based report."""
        report = f"Benchmark Report: {suite_result.benchmark_name}\n"
        report += "=" * 50 + "\n\n"
        
        report += "Summary Statistics:\n"
        for category, stats in suite_result.summary_stats.items():
            if isinstance(stats, dict):
                report += f"  {category}:\n"
                for stat_name, stat_value in stats.items():
                    report += f"    {stat_name}: {stat_value:.4f}\n"
            else:
                report += f"  {category}: {stats:.4f}\n"
        
        report += "\nDetailed Results:\n"
        for result in suite_result.results[:10]:  # Show first 10 results
            report += f"  {result.solver_name} (size={result.problem_size}): "
            report += f"time={result.execution_time:.4f}s, quality={result.solution_quality:.4f}\n"
        
        return report
    
    def generate_json_report(self, suite_result: BenchmarkSuiteResult) -> str:
        """Generate a JSON report."""
        data = {
            "benchmark_name": suite_result.benchmark_name,
            "timestamp": datetime.now().isoformat(),
            "summary_stats": suite_result.summary_stats,
            "results": [
                {
                    "solver_name": r.solver_name,
                    "problem_size": r.problem_size,
                    "execution_time": r.execution_time,
                    "solution_quality": r.solution_quality,
                    "memory_usage": r.memory_usage,
                    "success_rate": r.success_rate,
                    "constraint_violations": r.constraint_violations,
                    "timestamp": r.run_timestamp.isoformat()
                }
                for r in suite_result.results
            ]
        }
        return json.dumps(data, indent=2)
    
    def save_report(self, suite_result: BenchmarkSuiteResult, filename: str, format: str = "json"):
        """Save benchmark report to file."""
        if format == "json":
            content = self.generate_json_report(suite_result)
        elif format == "text":
            content = self.generate_text_report(suite_result)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else ".", exist_ok=True)
        with open(filename, 'w') as f:
            f.write(content)