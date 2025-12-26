"""Reporting and analytics for EduSched."""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from edusched.domain.assignment import Assignment
from edusched.domain.problem import Problem
from edusched.domain.result import Result


class ReportType(Enum):
    """Types of reports that can be generated."""
    RESOURCE_UTILIZATION = "resource_utilization"
    SCHEDULE_ANALYSIS = "schedule_analysis"
    CONFLICT_REPORT = "conflict_report"
    OPTIMIZATION_METRICS = "optimization_metrics"
    SUMMARY = "summary"


@dataclass
class ResourceUtilizationReport:
    """Report on resource utilization."""
    resource_id: str
    resource_type: str
    total_time_allocated: float  # in hours
    utilization_percentage: float
    capacity: Optional[int] = None
    average_occupancy: float = 0.0
    peak_usage: float = 0.0
    usage_by_day: Dict[str, float] = None  # hours per day


@dataclass
class ConflictReport:
    """Report on scheduling conflicts."""
    conflict_type: str
    affected_resources: List[str]
    affected_requests: List[str]
    severity: str  # 'high', 'medium', 'low'
    description: str
    count: int = 1


@dataclass
class ScheduleAnalysisReport:
    """Analysis of the schedule quality."""
    total_assignments: int
    total_requests: int
    scheduled_percentage: float
    average_session_duration: float  # in hours
    schedule_density: float  # assignments per time unit
    time_utilization: float  # percentage of available time used
    resource_balance_score: float  # how evenly resources are used


@dataclass
class OptimizationMetricsReport:
    """Metrics related to optimization objectives."""
    objective_satisfaction: Dict[str, float]  # objective name -> satisfaction score
    constraint_violation_count: int
    solution_quality_score: float
    improvement_over_baseline: float


@dataclass
class SummaryReport:
    """Overall summary of the scheduling result."""
    report_date: datetime
    solver_used: str
    solve_time_seconds: float
    result_status: str
    scheduled_requests: int
    total_requests: int
    resource_utilization: float
    conflict_count: int
    overall_score: float


@dataclass
class ComprehensiveReport:
    """A comprehensive report containing all types of analytics."""
    report_id: str
    generation_time: datetime
    problem_summary: Dict[str, Any]
    resource_utilization: List[ResourceUtilizationReport]
    schedule_analysis: ScheduleAnalysisReport
    conflict_report: List[ConflictReport]
    optimization_metrics: OptimizationMetricsReport
    summary: SummaryReport
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the report to a dictionary for serialization."""
        result = {
            "report_id": self.report_id,
            "generation_time": self.generation_time.isoformat(),
            "problem_summary": self.problem_summary,
            "resource_utilization": [asdict(r) for r in self.resource_utilization],
            "schedule_analysis": asdict(self.schedule_analysis),
            "conflict_report": [asdict(c) for c in self.conflict_report],
            "optimization_metrics": asdict(self.optimization_metrics),
            "summary": asdict(self.summary)
        }
        return result
    
    def to_json(self) -> str:
        """Convert the report to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class ReportGenerator:
    """Generates various types of reports from scheduling results."""
    
    def __init__(self):
        pass
    
    def generate_comprehensive_report(self, problem: Problem, result: Result) -> ComprehensiveReport:
        """Generate a comprehensive report from problem and result."""
        report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Generate individual reports
        resource_utilization = self._generate_resource_utilization_report(problem, result)
        schedule_analysis = self._generate_schedule_analysis_report(problem, result)
        conflict_report = self._generate_conflict_report(problem, result)
        optimization_metrics = self._generate_optimization_metrics_report(problem, result)
        summary = self._generate_summary_report(problem, result)
        
        # Create problem summary
        problem_summary = {
            "total_requests": len(problem.requests),
            "total_resources": len(problem.resources),
            "total_calendars": len(problem.calendars),
            "total_constraints": len(problem.constraints),
            "total_objectives": len(problem.objectives)
        }
        
        return ComprehensiveReport(
            report_id=report_id,
            generation_time=datetime.now(),
            problem_summary=problem_summary,
            resource_utilization=resource_utilization,
            schedule_analysis=schedule_analysis,
            conflict_report=conflict_report,
            optimization_metrics=optimization_metrics,
            summary=summary
        )
    
    def _generate_resource_utilization_report(self, problem: Problem, result: Result) -> List[ResourceUtilizationReport]:
        """Generate resource utilization report."""
        utilization_reports = []
        
        # Calculate total available time per resource (simplified)
        # In a real implementation, this would consider calendar availability
        for resource in problem.resources:
            # Calculate time allocated to this resource
            total_time = 0.0
            days_used = set()
            
            for assignment in result.assignments:
                if resource.id in [rid for rids in assignment.assigned_resources.values() for rid in rids]:
                    duration_hours = (assignment.end_time - assignment.start_time).total_seconds() / 3600
                    total_time += duration_hours
                    days_used.add(assignment.start_time.date().isoformat())
            
            # Calculate utilization percentage (simplified)
            # In a real implementation, this would consider the actual available time
            utilization_percentage = min((total_time / 40.0) * 100, 100) if total_time > 0 else 0  # Assuming 40h work week
            
            report = ResourceUtilizationReport(
                resource_id=resource.id,
                resource_type=resource.resource_type,
                total_time_allocated=total_time,
                utilization_percentage=utilization_percentage,
                capacity=resource.capacity,
                usage_by_day={day: total_time/len(days_used) if days_used else 0 for day in days_used}
            )
            utilization_reports.append(report)
        
        return utilization_reports
    
    def _generate_schedule_analysis_report(self, problem: Problem, result: Result) -> ScheduleAnalysisReport:
        """Generate schedule analysis report."""
        total_assignments = len(result.assignments)
        total_requests = len(problem.requests)
        
        scheduled_percentage = (total_assignments / max(total_requests, 1)) * 100
        
        # Calculate average session duration
        if result.assignments:
            total_duration = sum(
                (a.end_time - a.start_time).total_seconds() / 3600 
                for a in result.assignments
            )
            average_duration = total_duration / total_assignments
        else:
            average_duration = 0.0
        
        # Simplified metrics
        schedule_density = total_assignments / max(len(set(a.start_time.date() for a in result.assignments)), 1)
        time_utilization = scheduled_percentage / 100  # Simplified
        resource_balance_score = 0.8  # Placeholder - in real implementation this would be calculated
        
        return ScheduleAnalysisReport(
            total_assignments=total_assignments,
            total_requests=total_requests,
            scheduled_percentage=scheduled_percentage,
            average_session_duration=average_duration,
            schedule_density=schedule_density,
            time_utilization=time_utilization,
            resource_balance_score=resource_balance_score
        )
    
    def _generate_conflict_report(self, problem: Problem, result: Result) -> List[ConflictReport]:
        """Generate conflict report."""
        conflicts = []
        
        # Check for basic resource conflicts (double bookings)
        resource_assignments = {}
        for assignment in result.assignments:
            for resource_ids in assignment.assigned_resources.values():
                for resource_id in resource_ids:
                    if resource_id not in resource_assignments:
                        resource_assignments[resource_id] = []
                    resource_assignments[resource_id].append(assignment)
        
        for resource_id, assignments in resource_assignments.items():
            # Check for overlapping assignments
            for i, assign1 in enumerate(assignments):
                for j, assign2 in enumerate(assignments[i+1:], i+1):
                    if (assign1.start_time < assign2.end_time and 
                        assign1.end_time > assign2.start_time):
                        conflict = ConflictReport(
                            conflict_type="resource_overlap",
                            affected_resources=[resource_id],
                            affected_requests=[assign1.request_id, assign2.request_id],
                            severity="high",
                            description=f"Resource {resource_id} double-booked between "
                                      f"{assign1.start_time} and {assign2.start_time}"
                        )
                        conflicts.append(conflict)
        
        return conflicts
    
    def _generate_optimization_metrics_report(self, problem: Problem, result: Result) -> OptimizationMetricsReport:
        """Generate optimization metrics report."""
        # Calculate objective satisfaction
        objective_satisfaction = {}
        for obj in problem.objectives:
            satisfaction = obj.score(result.assignments)
            objective_satisfaction[obj.__class__.__name__] = satisfaction
        
        # Count constraint violations
        constraint_violations = 0  # This would be calculated by checking all constraints
        solution_quality = result.objective_score or 0.0  # Use the result's objective score
        
        return OptimizationMetricsReport(
            objective_satisfaction=objective_satisfaction,
            constraint_violation_count=constraint_violations,
            solution_quality_score=solution_quality,
            improvement_over_baseline=0.0  # Placeholder
        )
    
    def _generate_summary_report(self, problem: Problem, result: Result) -> SummaryReport:
        """Generate summary report."""
        # Calculate resource utilization
        if problem.resources and result.assignments:
            resource_util = len(set(
                rid for a in result.assignments 
                for rids in a.assigned_resources.values() 
                for rid in rids
            )) / len(problem.resources) * 100
        else:
            resource_util = 0.0
        
        # Count conflicts (simplified)
        conflicts = self._generate_conflict_report(problem, result)
        conflict_count = len(conflicts)
        
        return SummaryReport(
            report_date=datetime.now(),
            solver_used=result.backend_used,
            solve_time_seconds=result.solve_time_seconds,
            result_status=result.status,
            scheduled_requests=len(result.assignments),
            total_requests=len(problem.requests),
            resource_utilization=resource_util,
            conflict_count=conflict_count,
            overall_score=result.objective_score or 0.0
        )


class ReportExporter:
    """Exports reports in various formats."""
    
    def export_json(self, report: ComprehensiveReport, filename: str):
        """Export report as JSON."""
        with open(filename, 'w') as f:
            f.write(report.to_json())
    
    def export_text(self, report: ComprehensiveReport, filename: str):
        """Export report as text."""
        lines = [
            f"EduSched Report: {report.report_id}",
            f"Generated: {report.generation_time}",
            "",
            "Problem Summary:",
            f"  Total Requests: {report.problem_summary['total_requests']}",
            f"  Total Resources: {report.problem_summary['total_resources']}",
            f"  Total Constraints: {report.problem_summary['total_constraints']}",
            "",
            "Schedule Summary:",
            f"  Scheduled: {report.summary.scheduled_requests}/{report.summary.total_requests} ({report.summary.scheduled_requests/report.summary.total_requests*100:.1f}%)",
            f"  Solve Time: {report.summary.solve_time_seconds:.2f}s",
            f"  Solver: {report.summary.solver_used}",
            f"  Status: {report.summary.result_status}",
            "",
            "Resource Utilization:",
        ]
        
        for util in report.resource_utilization[:5]:  # Show first 5 resources
            lines.append(f"  {util.resource_id} ({util.resource_type}): {util.utilization_percentage:.1f}% utilization")
        
        if len(report.conflict_report) > 0:
            lines.append(f"\nConflicts Found: {len(report.conflict_report)}")
            for conflict in report.conflict_report[:3]:  # Show first 3 conflicts
                lines.append(f"  {conflict.conflict_type}: {conflict.description}")
        else:
            lines.append("\nConflicts Found: None")
        
        lines.append(f"\nOverall Score: {report.summary.overall_score:.2f}")
        
        with open(filename, 'w') as f:
            f.write('\n'.join(lines))