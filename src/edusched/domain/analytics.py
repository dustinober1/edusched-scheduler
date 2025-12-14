"""Analytics and reporting domain models.

Handles schedule analysis, metrics collection, and reporting capabilities.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from edusched.domain.base import BaseEntity


@dataclass
class ScheduleMetrics(BaseEntity):
    """Metrics calculated for a schedule."""

    schedule_id: str
    calculation_date: datetime = field(default_factory=datetime.now)

    # Session metrics
    total_sessions: int = 0
    scheduled_sessions: int = 0
    unscheduled_sessions: int = 0
    conflict_sessions: int = 0

    # Resource utilization
    room_utilization_percent: float = 0.0
    teacher_utilization_percent: float = 0.0
    equipment_utilization_percent: float = 0.0
    average_room_capacity_used: float = 0.0

    # Time distribution
    morning_sessions: int = 0  # 6AM - 12PM
    afternoon_sessions: int = 0  # 12PM - 6PM
    evening_sessions: int = 0  # 6PM - 12AM
    weekend_sessions: int = 0

    # Quality metrics
    preference_satisfaction_score: float = 0.0  # 0-1
    constraint_violation_score: float = 0.0  # 0-1, lower is better
    schedule_efficiency_score: float = 0.0  # 0-1

    # Student metrics
    average_class_size: float = 0.0
    average_students_per_teacher: float = 0.0
    total_student_hours: float = 0.0

    # Cost metrics
    total_room_cost: float = 0.0
    total_equipment_cost: float = 0.0
    total_transportation_cost: float = 0.0
    cost_per_student_hour: float = 0.0

    # Campus metrics (if multi-campus)
    campuses_used: int = 0
    cross_campus_sessions: int = 0
    inter_campus_travel_time: float = 0.0  # Total hours

    # Additional custom metrics
    custom_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class TimeSlotAnalysis(BaseEntity):
    """Analysis of time slot usage patterns."""

    time_slot: str  # e.g., "Monday 09:00-10:30"
    day_of_week: int  # 0=Monday, 6=Sunday
    start_time: str  # HH:MM format
    end_time: str  # HH:MM format

    # Usage statistics
    total_capacity: int = 0  # Sum of all room capacities
    scheduled_capacity: int = 0  # Capacity of scheduled sessions
    utilization_percent: float = 0.0
    rooms_available: int = 0
    rooms_in_use: int = 0

    # Quality metrics
    average_preference_score: float = 0.0
    conflict_count: int = 0
    overcapacity_sessions: int = 0  # Sessions exceeding room capacity

    # Department distribution
    department_usage: Dict[str, int] = field(default_factory=dict)
    course_level_distribution: Dict[str, int] = field(default_factory=dict)


@dataclass
class ResourceUtilizationReport(BaseEntity):
    """Detailed utilization report for resources."""

    resource_type: str  # room, teacher, equipment, etc.
    resource_id: str
    resource_name: str

    # Usage statistics
    total_available_hours: float = 0.0
    scheduled_hours: float = 0.0
    utilization_percent: float = 0.0

    # Booking patterns
    bookings_count: int = 0
    average_booking_duration: float = 0.0
    peak_utilization_hour: int = 0  # Hour of day (0-23)
    peak_utilization_day: int = 0  # Day of week (0-6)

    # Capacity metrics
    capacity_utilization_percent: float = 0.0  # For rooms
    overcapacity_instances: int = 0
    undercapacity_instances: int = 0

    # Preference satisfaction
    preference_satisfaction_score: float = 0.0
    preferred_time_percentage: float = 0.0  # % of time in preferred slots

    # Constraints and issues
    constraint_violations: List[Dict[str, Any]] = field(default_factory=list)
    maintenance_downtime: float = 0.0  # Hours unavailable

    # Historical trends
    utilization_trend: List[Tuple[datetime, float]] = field(default_factory=list)
    booking_frequency_trend: List[Tuple[datetime, int]] = field(default_factory=list)


@dataclass
class DepartmentAnalysis(BaseEntity):
    """Analysis of department scheduling patterns."""

    department_id: str
    department_name: str

    # Course and session metrics
    total_courses: int = 0
    total_sessions: int = 0
    total_student_enrollment: int = 0
    average_class_size: float = 0.0

    # Resource allocation
    rooms_allocated: List[str] = field(default_factory=list)
    total_room_hours: float = 0.0
    budget_utilization_percent: float = 0.0

    # Time preferences
    preferred_time_slots: List[str] = field(default_factory=list)
    preferred_time_satisfaction: float = 0.0
    teaching_load_distribution: Dict[str, int] = field(default_factory=dict)

    # Cross-department metrics
    shared_resources: List[str] = field(default_factory=list)
    conflicts_with_departments: List[str] = field(default_factory=list)

    # Quality metrics
    schedule_efficiency_score: float = 0.0
    student_satisfaction_estimate: float = 0.0

    # Historical performance
    semester_comparison: Dict[str, float] = field(default_factory=dict)


@dataclass
class StudentExperienceMetrics(BaseEntity):
    """Metrics related to student experience."""

    student_id: Optional[str] = None  # None for aggregate metrics
    program_id: Optional[str] = None

    # Schedule density
    classes_per_week: int = 0
    class_hours_per_week: float = 0.0
    average_daily_class_hours: float = 0.0
    longest_continuous_hours: float = 0.0
    breaks_between_classes: List[float] = field(default_factory=list)  # In minutes

    # Travel and logistics
    average_walking_distance_meters: float = 0.0
    max_walking_distance_meters: float = 0.0
    campus_changes_per_week: int = 0
    travel_time_per_week: float = 0.0  # Minutes

    # Time preferences
    morning_classes: int = 0
    afternoon_classes: int = 0
    evening_classes: int = 0
    preferred_time_satisfaction: float = 0.0

    # Quality of experience
    schedule_stability_score: float = 0.0  # How consistent schedule is
    breaks_satisfaction_score: float = 0.0  # Adequate breaks
    cohort_scheduling_score: float = 0.0  # Classes with cohort

    # Access issues
    conflicts_resolved: int = 0
    waitlisted_sessions: int = 0
    accommodation_needs_met: bool = True


@dataclass
class ScheduleComparison(BaseEntity):
    """Comparison between two or more schedule versions."""

    name: str
    description: str
    schedule_ids: List[str]
    comparison_date: datetime = field(default_factory=datetime.now)

    # Metrics comparison
    metrics_comparison: Dict[str, Dict[str, float]] = field(default_factory=dict)
    improvement_areas: List[str] = field(default_factory=list)
    regression_areas: List[str] = field(default_factory=list)

    # Resource changes
    resource_allocation_changes: Dict[str, Tuple[List[str], List[str]]] = field(
        default_factory=dict
    )
    utilization_changes: Dict[str, float] = field(default_factory=dict)

    # Impact analysis
    affected_students: int = 0
    affected_teachers: int = 0
    affected_departments: List[str] = field(default_factory=list)

    # Recommendations
    selected_schedule_id: Optional[str] = None
    selection_reasons: List[str] = field(default_factory=list)
    implementation_risks: List[str] = field(default_factory=list)


class AnalyticsEngine:
    """Engine for calculating schedule analytics and generating reports."""

    def __init__(self):
        self.schedule_metrics: Dict[str, ScheduleMetrics] = {}
        self.time_slot_analyses: Dict[str, TimeSlotAnalysis] = {}
        self.resource_reports: Dict[str, ResourceUtilizationReport] = {}
        self.department_analyses: Dict[str, DepartmentAnalysis] = {}
        self.student_metrics: Dict[str, StudentExperienceMetrics] = {}

    def calculate_schedule_metrics(
        self,
        schedule_id: str,
        assignments: List[Any],
        requests: List[Any],
        resources: List[Any],
        custom_metrics: Dict[str, float] = None,
    ) -> ScheduleMetrics:
        """Calculate comprehensive metrics for a schedule."""
        metrics = ScheduleMetrics(schedule_id=schedule_id)

        # Basic session counts
        metrics.total_sessions = len(requests)
        metrics.scheduled_sessions = len(assignments)
        metrics.unscheduled_sessions = metrics.total_sessions - metrics.scheduled_sessions

        # Time distribution
        for assignment in assignments:
            hour = assignment.start_time.hour
            day_of_week = assignment.start_time.weekday()

            if 6 <= hour < 12:
                metrics.morning_sessions += 1
            elif 12 <= hour < 18:
                metrics.afternoon_sessions += 1
            elif 18 <= hour < 24:
                metrics.evening_sessions += 1

            if day_of_week >= 5:  # Saturday, Sunday
                metrics.weekend_sessions += 1

        # Resource utilization calculations would go here
        # This is a placeholder - actual implementation would depend on data structures

        # Add custom metrics if provided
        if custom_metrics:
            metrics.custom_metrics.update(custom_metrics)

        self.schedule_metrics[schedule_id] = metrics
        return metrics

    def analyze_time_slots(
        self,
        schedule_id: str,
        assignments: List[Any],
        resources: List[Any],
    ) -> List[TimeSlotAnalysis]:
        """Analyze utilization by time slots."""
        analyses = []

        # Generate time slots (e.g., hourly from 7AM to 10PM)
        for day in range(7):  # Monday to Sunday
            for hour in range(7, 23):  # 7AM to 10PM
                slot_id = f"{day}_{hour:02d}:00-{hour + 1:02d}:00"

                analysis = TimeSlotAnalysis(
                    time_slot=f"{['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][day]} {hour:02d}:00-{hour + 1:02d}:00",
                    day_of_week=day,
                    start_time=f"{hour:02d}:00",
                    end_time=f"{hour + 1:02d}:00",
                )

                # Count sessions in this time slot
                slot_assignments = [
                    a
                    for a in assignments
                    if a.start_time.weekday() == day and a.start_time.hour == hour
                ]

                analysis.rooms_in_use = len(slot_assignments)
                analysis.utilization_percent = min(
                    100.0, (len(slot_assignments) / len(resources)) * 100
                )

                analyses.append(analysis)
                self.time_slot_analyses[slot_id] = analysis

        return analyses

    def generate_resource_report(
        self,
        resource_id: str,
        resource_name: str,
        resource_type: str,
        assignments: List[Any],
        time_period: Tuple[datetime, datetime],
    ) -> ResourceUtilizationReport:
        """Generate utilization report for a specific resource."""
        report = ResourceUtilizationReport(
            resource_id=resource_id,
            resource_name=resource_name,
            resource_type=resource_type,
        )

        # Calculate total available hours in time period
        start_date, end_date = time_period
        total_days = (end_date - start_date).days
        hours_per_day = 12  # Assume 12-hour operating day
        report.total_available_hours = total_days * hours_per_day

        # Sum up scheduled hours for this resource
        for assignment in assignments:
            if str(assignment.resource.id) == resource_id:
                # Calculate duration of this assignment
                duration_hours = len(assignment.request_id) * 0.1  # Placeholder calculation
                report.scheduled_hours += duration_hours
                report.bookings_count += 1

        # Calculate utilization
        if report.total_available_hours > 0:
            report.utilization_percent = (
                report.scheduled_hours / report.total_available_hours
            ) * 100

        if report.bookings_count > 0:
            report.average_booking_duration = report.scheduled_hours / report.bookings_count

        self.resource_reports[resource_id] = report
        return report

    def create_schedule_comparison(
        self,
        name: str,
        schedule_ids: List[str],
        comparison_metrics: List[str] = None,
    ) -> ScheduleComparison:
        """Create comparison between multiple schedules."""
        comparison = ScheduleComparison(
            name=name,
            schedule_ids=schedule_ids,
        )

        if not comparison_metrics:
            comparison_metrics = [
                "room_utilization_percent",
                "preference_satisfaction_score",
                "constraint_violation_score",
                "total_room_cost",
            ]

        # Compare metrics across schedules
        for metric in comparison_metrics:
            comparison.metrics_comparison[metric] = {}
            for schedule_id in schedule_ids:
                metrics = self.schedule_metrics.get(schedule_id)
                if metrics:
                    value = getattr(metrics, metric, None)
                    if value is not None:
                        comparison.metrics_comparison[metric][schedule_id] = value

        # Analyze improvements and regressions
        for metric, values in comparison.metrics_comparison.items():
            if len(values) > 1:
                value_list = list(values.values())
                if metric.endswith("score") or metric.endswith("percent"):
                    # Higher is better
                    best = max(value_list)
                    worst = min(value_list)
                else:
                    # Lower is better (e.g., cost, violations)
                    best = min(value_list)
                    worst = max(value_list)

                if best != worst:
                    # Identify schedules with best values
                    best_schedules = [sid for sid, val in values.items() if val == best]
                    worst_schedules = [sid for sid, val in values.items() if val == worst]

                    if len(best_schedules) < len(worst_schedules):
                        comparison.improvement_areas.append(
                            f"{metric}: {best_schedules} perform best"
                        )
                    else:
                        comparison.regression_areas.append(
                            f"{metric}: {worst_schedules} could improve"
                        )

        return comparison

    def get_analytics_summary(self, schedule_id: str) -> Dict[str, Any]:
        """Get comprehensive analytics summary for a schedule."""
        summary = {
            "schedule_id": schedule_id,
            "calculated_at": datetime.now().isoformat(),
        }

        # Include metrics if available
        metrics = self.schedule_metrics.get(schedule_id)
        if metrics:
            summary["schedule_metrics"] = {
                "total_sessions": metrics.total_sessions,
                "scheduled_sessions": metrics.scheduled_sessions,
                "utilization": {
                    "rooms": metrics.room_utilization_percent,
                    "teachers": metrics.teacher_utilization_percent,
                    "equipment": metrics.equipment_utilization_percent,
                },
                "quality_scores": {
                    "preference_satisfaction": metrics.preference_satisfaction_score,
                    "constraint_violation": metrics.constraint_violation_score,
                    "efficiency": metrics.schedule_efficiency_score,
                },
                "costs": {
                    "total": metrics.total_room_cost + metrics.total_equipment_cost,
                    "per_student_hour": metrics.cost_per_student_hour,
                },
            }

        # Include time slot analyses
        time_analyses = list(self.time_slot_analyses.values())
        if time_analyses:
            summary["time_slot_analysis"] = {
                "total_slots": len(time_analyses),
                "average_utilization": sum(a.utilization_percent for a in time_analyses)
                / len(time_analyses),
                "peak_slot": max(time_analyses, key=lambda x: x.utilization_percent).time_slot,
                "lowest_slot": min(time_analyses, key=lambda x: x.utilization_percent).time_slot,
            }

        return summary
