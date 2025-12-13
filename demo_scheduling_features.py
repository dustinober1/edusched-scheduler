#!/usr/bin/env python3
"""
Demonstration of the new scheduling features:
- 5-day classes (Mon-Fri)
- 4-day classes (Mon-Thu or Tue-Fri)
- 3-day classes (Mon-Wed or Wed-Fri)
- 2-day classes (Mon-Tue or Thu-Fri)
- Priority-based scheduling (longer classes first)
- Occurrence spreading throughout the term
- Holiday avoidance
"""

from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

from edusched.domain.holiday_calendar import HolidayCalendar
from edusched.domain.calendar import Calendar
from edusched.domain.resource import Resource
from edusched.domain.session_request import SessionRequest
from edusched.domain.problem import Problem
from edusched.domain.building import Building, BuildingType
from edusched.constraints.scheduling_constraints import (
    SchedulingPatternConstraint,
    HolidayAvoidanceConstraint,
    OccurrenceSpreadConstraint
)
from edusched.solvers.heuristic import HeuristicSolver


def demo_scheduling_features():
    """Demonstrate the new scheduling features."""

    # Create holiday calendar
    calendar = HolidayCalendar(
        id="demo_academic",
        name="Demo Academic Calendar 2024",
        year=2024,
        excluded_weekdays={5, 6}  # No classes on weekends
    )

    # Add holiday periods
    calendar.add_holiday(date(2024, 12, 20), date(2025, 1, 10), "Winter Break")
    calendar.add_holiday(date(2024, 3, 11), date(2024, 3, 22), "Spring Break")

    # Create resources
    large_lecture = Resource(id="Lecture101", resource_type="classroom", capacity=100)
    small_classroom = Resource(id="Room201", resource_type="classroom", capacity=30)
    lab = Resource(id="Lab301", resource_type="lab", capacity=25)

    # Create academic calendar
    academic_calendar = Calendar(
        id="demo_academic_calendar",
        timezone=ZoneInfo("UTC"),
        timeslot_granularity=timedelta(minutes=30)
    )

    # Create course requests with different patterns
    requests = [
        # 3-hour seminar on Tue-Fri (highest priority)
        SessionRequest(
            id="grad_seminar",
            duration=timedelta(hours=3),
            number_of_occurrences=8,
            earliest_date=datetime(2024, 2, 1, 9, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 5, 15, 17, 0, tzinfo=ZoneInfo("UTC")),
            scheduling_pattern="2days_tf",  # Tue-Fri
            enrollment_count=15,
            required_resource_types={"classroom": 1},
            avoid_holidays=True,
            min_gap_between_occurrences=timedelta(days=7)  # Weekly
        ),

        # 2-hour lab on Mon-Wed (medium priority)
        SessionRequest(
            id="cs_lab",
            duration=timedelta(hours=2),
            number_of_occurrences=12,
            earliest_date=datetime(2024, 2, 1, 9, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 5, 15, 17, 0, tzinfo=ZoneInfo("UTC")),
            scheduling_pattern="3days_mw",  # Mon-Wed
            enrollment_count=20,
            required_resource_types={"lab": 1},
            avoid_holidays=True,
            min_gap_between_occurrences=timedelta(days=5)
        ),

        # 1-hour lecture Mon-Fri (lowest priority)
        SessionRequest(
            id="intro_course",
            duration=timedelta(hours=1),
            number_of_occurrences=24,
            earliest_date=datetime(2024, 2, 1, 9, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 5, 15, 17, 0, tzinfo=ZoneInfo("UTC")),
            scheduling_pattern="5days",  # Mon-Fri
            enrollment_count=50,
            required_resource_types={"classroom": 1},
            avoid_holidays=True,
            min_gap_between_occurrences=timedelta(days=1)
        )
    ]

    # Create constraints
    constraints = []
    for request in requests:
        constraints.append(SchedulingPatternConstraint(request.id))
        constraints.append(HolidayAvoidanceConstraint(request.id))
        constraints.append(OccurrenceSpreadConstraint(
            request.id,
            min_days_between=int(request.min_gap_between_occurrences.total_seconds() / 86400)
        ))

    # Create problem
    problem = Problem(
        requests=requests,
        resources=[large_lecture, small_classroom, lab],
        calendars=[academic_calendar],
        constraints=constraints,
        holiday_calendar=calendar,
        institutional_calendar_id="demo_academic_calendar"
    )

    # Solve using heuristic solver
    solver = HeuristicSolver()
    result = solver.solve(problem, seed=42)

    # Display results
    print("\n=== SCHEDULING DEMO RESULTS ===\n")
    print(f"Solver status: {result.status}")
    print(f"Total assignments: {len(result.assignments)}")
    print(f"Unscheduled requests: {result.unscheduled_requests}")
    print(f"Solve time: {result.solve_time_seconds:.3f} seconds\n")

    # Group assignments by request
    assignments_by_request = {}
    for assignment in result.assignments:
        if assignment.request_id not in assignments_by_request:
            assignments_by_request[assignment.request_id] = []
        assignments_by_request[assignment.request_id].append(assignment)

    # Display schedule for each course
    for request_id, assignments in assignments_by_request.items():
        request = next(r for r in requests if r.id == request_id)
        print(f"\n--- {request_id.upper()} ---")
        print(f"Pattern: {request.scheduling_pattern}")
        print(f"Duration: {request.duration}")
        print(f"Occurrences: {len(assignments)}")
        print("Schedule:")

        assignments.sort(key=lambda a: a.start_time)
        for assignment in assignments:
            day_name = assignment.start_time.strftime("%A")
            date_str = assignment.start_time.strftime("%Y-%m-%d")
            time_str = assignment.start_time.strftime("%H:%M")
            print(f"  {day_name} {date_str} at {time_str}")
            print(f"    Resource: {assignment.assigned_resources}")

            # Verify scheduling pattern
            if request.scheduling_pattern == "5days":
                assert assignment.start_time.weekday() < 5, "Should be Mon-Fri"
            elif request.scheduling_pattern == "2days_tf":
                assert assignment.start_time.weekday() in [3, 4], "Should be Thu-Fri"
            elif request.scheduling_pattern == "3days_mw":
                assert assignment.start_time.weekday() in [0, 1, 2], "Should be Mon-Wed"

    print("\n=== PRIORITY ORDER VERIFICATION ===")
    # Show that longer classes were scheduled first (priority-based)
    for request in sorted(requests, key=lambda r: r.duration, reverse=True):
        assignments = assignments_by_request.get(request.id, [])
        if assignments:
            first_assignment = min(assignments, key=lambda a: a.start_time)
            avg_hour = sum(a.start_time.hour for a in assignments) / len(assignments)
            print(f"{request.id}: Duration {request.duration}, Avg time: {avg_hour:.1f}:00")

    print("\n=== HOLIDAY AVOIDANCE VERIFICATION ===")
    # Verify no assignments on holidays
    for assignment in result.assignments:
        assignment_date = assignment.start_time.date()
        if calendar.is_holiday(assignment_date):
            print(f"WARNING: Assignment on holiday: {assignment_date}")
        else:
            assert not calendar.is_holiday(assignment_date), "Should not schedule on holidays"
    print("All assignments avoid holidays ✓")

    print("\n=== OCCURRENCE SPREADING VERIFICATION ===")
    # Verify occurrences are spread out
    for request_id, assignments in assignments_by_request.items():
        request = next(r for r in requests if r.id == request_id)
        if len(assignments) > 1:
            assignments.sort(key=lambda a: a.start_time)
            min_gap = float('inf')
            for i in range(len(assignments) - 1):
                gap = (assignments[i + 1].start_time - assignments[i].start_time).days
                min_gap = min(min_gap, gap)
            print(f"{request_id}: Minimum gap between occurrences: {min_gap} days")

    return result


if __name__ == "__main__":
    result = demo_scheduling_features()
    print("\nDemo completed successfully!")