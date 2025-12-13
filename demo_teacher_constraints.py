#!/usr/bin/env python3
"""
Demonstration of teacher scheduling constraints including:
- Vacation and personal time off
- Travel time between buildings
- Setup/teardown time requirements
- Institutional time blockers (lunch breaks, meetings)
- Teacher workload limits
"""

from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from edusched.domain.teacher import Teacher
from edusched.domain.calendar import Calendar
from edusched.domain.resource import Resource
from edusched.domain.session_request import SessionRequest
from edusched.domain.problem import Problem
from edusched.domain.building import Building, BuildingType
from edusched.domain.holiday_calendar import HolidayCalendar
from edusched.domain.time_blockers import TimeBlocker, create_standard_time_blocker
from edusched.constraints.teacher_constraints import (
    TeacherAvailabilityConstraint,
    TeacherWorkloadConstraint,
    TeacherTravelTimeConstraint
)
from edusched.constraints.time_blocker_constraint import TimeBlockerConstraint
from edusched.constraints.scheduling_constraints import (
    SchedulingPatternConstraint,
    HolidayAvoidanceConstraint
)
from edusched.solvers.heuristic import HeuristicSolver


def demo_teacher_constraints():
    """Demonstrate teacher constraints in action."""

    print("\n=== TEACHER CONSTRAINTS DEMONSTRATION ===\n")

    # Create teachers with various constraints
    professor_johnson = Teacher(
        id="prof_johnson",
        name="Dr. Sarah Johnson",
        title="Professor of Computer Science",
        department_id="cs",
        email="sjohnson@university.edu",

        # Availability preferences
        preferred_days=["monday", "wednesday", "friday"],
        preferred_times={
            "monday": ["09:00-12:00", "14:00-16:00"],
            "wednesday": ["09:00-12:00", "14:00-16:00"],
            "friday": ["09:00-12:00"]
        },

        # Time off
        vacation_periods=[
            (date(2024, 3, 10), date(2024, 3, 17), "Spring Break"),
            (date(2024, 6, 1), date(2024, 8, 15), "Summer Research")
        ],
        conference_dates=[
            (date(2024, 4, 15), date(2024, 4, 18), "ACM Conference")
        ],
        personal_days=[date(2024, 2, 14)],  # Taking Valentine's Day off

        # Teaching constraints
        max_consecutive_hours=3,
        max_daily_hours=6,
        max_weekly_hours=18,

        # Building preferences
        preferred_buildings=["engineering", "science"],
        max_class_size=50,

        # Setup and travel
        max_travel_time_between_classes=25,
        requires_setup_time=True,
        setup_time_minutes=20,
        cleanup_time_minutes=15,
        preferred_block_gap=45
    )

    professor_chen = Teacher(
        id="prof_chen",
        name="Dr. Michael Chen",
        title="Associate Professor of Mathematics",
        department_id="math",

        # Part-time availability
        preferred_days=["tuesday", "thursday"],
        preferred_times={
            "tuesday": ["10:00-14:00"],
            "thursday": ["10:00-14:00"]
        },

        # Limited workload
        max_consecutive_hours=2,
        max_daily_hours=4,
        max_weekly_hours=8,

        # Setup requirements (minimal for math lectures)
        setup_time_minutes=5,
        cleanup_time_minutes=5,
        max_travel_time_between_classes=30
    )

    # Create buildings
    engineering = Building(
        id="engineering",
        name="Engineering Building",
        building_type=BuildingType.ACADEMIC,
        address="123 Engineering Drive"
    )
    science = Building(
        id="science",
        name="Science Building",
        building_type=BuildingType.ACADEMIC,
        address="456 Science Avenue"
    )
    humanities = Building(
        id="humanities",
        name="Humanities Hall",
        building_type=BuildingType.ACADEMIC,
        address="789 Humanities Boulevard"
    )

    # Create resources in different buildings
    resources = [
        # Engineering Building
        Resource(
            id="Eng101",
            resource_type="classroom",
            capacity=60,
            building_id="engineering",
            floor_number=1,
            attributes={"has_computers": True, "projector": True}
        ),
        Resource(
            id="EngLab201",
            resource_type="lab",
            capacity=30,
            building_id="engineering",
            floor_number=2,
            attributes={"computers": 30, "specialized_software": True}
        ),

        # Science Building
        Resource(
            id="Sci301",
            resource_type="classroom",
            capacity=40,
            building_id="science",
            floor_number=3,
            attributes={"projector": True}
        ),

        # Humanities Hall
        Resource(
            id="Hum105",
            resource_type="classroom",
            capacity=50,
            building_id="humanities",
            floor_number=1,
            attributes={"blackboards": True}
        )
    ]

    # Create holiday calendar
    holiday_calendar = HolidayCalendar(
        id="academic_2024",
        name="2024 Academic Calendar",
        year=2024,
        excluded_weekdays={5, 6}  # No weekend classes
    )
    holiday_calendar.add_holiday(date(2024, 3, 10), date(2024, 3, 17), "Spring Break")

    # Create time blocker for institutional constraints
    time_blocker = TimeBlocker(institution_id="university")
    time_blocker.add_daily_block(
        name="Common Lunch",
        start_time="11:30",
        end_time="13:00",
        days=[0, 1, 2, 3, 4],  # Mon-Fri
        description="Common lunch period"
    )
    time_blocker.add_daily_block(
        name="Department Meetings",
        start_time="15:00",
        end_time="16:30",
        days=[2],  # Wednesday
        description="Weekly department meetings"
    )

    # Create academic calendar
    calendar = Calendar(
        id="academic",
        timezone=ZoneInfo("UTC"),
        timeslot_granularity=timedelta(minutes=15)
    )

    # Create session requests
    requests = [
        # CS course that needs lab setup
        SessionRequest(
            id="cs401",
            duration=timedelta(hours=2),
            number_of_occurrences=15,  # Weekly for spring semester
            earliest_date=datetime(2024, 2, 5, 9, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 5, 10, 17, 0, tzinfo=ZoneInfo("UTC")),
            scheduling_pattern="3days_wf",  # Wed-Fri
            teacher_id="prof_johnson",
            enrollment_count=45,
            required_resource_types={"lab": 1},
            avoid_holidays=True
        ),

        # Math course with simple setup
        SessionRequest(
            id="math301",
            duration=timedelta(hours=1.5),
            number_of_occurrences=14,  # Weekly
            earliest_date=datetime(2024, 2, 6, 10, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 5, 9, 15, 0, tzinfo=ZoneInfo("UTC")),
            scheduling_pattern="2days_tf",  # Tue-Thu
            teacher_id="prof_chen",
            enrollment_count=35,
            required_resource_types={"classroom": 1},
            avoid_holidays=True
        ),

        # Another CS course for Prof Johnson
        SessionRequest(
            id="cs101",
            duration=timedelta(hours=1),
            number_of_occurrences=14,  # Weekly
            earliest_date=datetime(2024, 2, 5, 9, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 5, 10, 17, 0, tzinfo=ZoneInfo("UTC")),
            scheduling_pattern="3days_mw",  # Mon-Wed
            teacher_id="prof_johnson",
            enrollment_count=50,
            required_resource_types={"classroom": 1},
            avoid_holidays=True
        )
    ]

    # Create constraints
    constraints = []

    # Teacher-specific constraints
    for teacher in [professor_johnson, professor_chen]:
        constraints.append(TeacherAvailabilityConstraint(teacher.id))
        constraints.append(TeacherWorkloadConstraint(teacher.id))
        constraints.append(TeacherTravelTimeConstraint(teacher.id))

    # Course-specific constraints
    for request in requests:
        constraints.append(SchedulingPatternConstraint(request.id))
        constraints.append(HolidayAvoidanceConstraint(request.id))

    # Institutional constraints
    constraints.append(TimeBlockerConstraint(time_blocker))

    # Create problem
    problem = Problem(
        requests=requests,
        resources=resources,
        calendars=[calendar],
        constraints=constraints,
        teachers=[professor_johnson, professor_chen],
        buildings=[engineering, science, humanities],
        holiday_calendar=holiday_calendar,
        institutional_calendar_id="academic"
    )

    # Solve
    solver = HeuristicSolver()
    result = solver.solve(problem, seed=42, fallback=True)

    # Display results
    print(f"Solver status: {result.status}")
    print(f"Total assignments: {len(result.assignments)}")
    print(f"Unscheduled requests: {result.unscheduled_requests}")
    print(f"Solve time: {result.solve_time_seconds:.3f} seconds\n")

    # Group assignments by teacher and course
    assignments_by_teacher = {}
    for assignment in result.assignments:
        request = next(r for r in requests if r.id == assignment.request_id)
        teacher_id = request.teacher_id
        if teacher_id not in assignments_by_teacher:
            assignments_by_teacher[teacher_id] = {}
        if assignment.request_id not in assignments_by_teacher[teacher_id]:
            assignments_by_teacher[teacher_id][assignment.request_id] = []
        assignments_by_teacher[teacher_id][assignment.request_id].append(assignment)

    # Display schedule for each teacher
    for teacher_id, courses in assignments_by_teacher.items():
        teacher = professor_johnson if teacher_id == "prof_johnson" else professor_chen
        print(f"\n--- {teacher.name}'s Schedule ---")
        print(f"Max daily hours: {teacher.max_daily_hours}")
        print(f"Max weekly hours: {teacher.max_weekly_hours}")
        print(f"Setup time: {teacher.setup_time_minutes} min")

        total_hours = 0
        daily_hours = {}

        for course_id, assignments in courses.items():
            assignments.sort(key=lambda a: a.start_time)
            print(f"\n{course_id.upper()}:")

            for assignment in assignments:
                duration = (assignment.end_time - assignment.start_time).total_seconds() / 3600
                total_hours += duration

                day_name = assignment.start_time.strftime("%A")
                date_str = assignment.start_time.strftime("%Y-%m-%d")
                time_str = assignment.start_time.strftime("%H:%M")

                print(f"  {day_name} {date_str}: {time_str} ({duration:.1f}h)")

                # Show room and building
                if "classroom" in assignment.assigned_resources:
                    room_id = assignment.assigned_resources["classroom"][0]
                    room = next(r for r in resources if r.id == room_id)
                    building = next(b for b in [engineering, science, humanities] if b.id == room.building_id)
                    print(f"    Location: {building.name} - Room {room_id}")

                # Track daily hours
                day_key = assignment.start_time.date()
                daily_hours[day_key] = daily_hours.get(day_key, 0) + duration

        print(f"\nSummary:")
        print(f"  Total teaching hours: {total_hours:.1f}")
        print(f"  Maximum daily hours: {max(daily_hours.values()) if daily_hours else 0:.1f}")
        print(f"  Average daily hours: {total_hours/len(daily_hours):.1f}" if daily_hours else "N/A")

    # Verify constraints were respected
    print("\n=== CONSTRAINT VERIFICATION ===")

    # Check no classes during lunch
    lunch_conflicts = 0
    for assignment in result.assignments:
        lunch_start = assignment.start_time.replace(hour=11, minute=30)
        lunch_end = assignment.start_time.replace(hour=13, minute=0)
        if lunch_start <= assignment.start_time <= lunch_end or lunch_start <= assignment.end_time <= lunch_end:
            lunch_conflicts += 1

    print(f"Lunch break violations: {lunch_conflicts} (should be 0)")

    # Check teacher workload limits
    for teacher_id, teacher in [("prof_johnson", professor_johnson), ("prof_chen", professor_chen)]:
        teacher_assignments = [a for a in result.assignments
                            if next((r for r in requests if r.id == a.request_id and r.teacher_id == teacher_id), None)]
        workload = teacher.get_teaching_load(teacher_assignments)

        print(f"\n{teacher.name} workload:")
        print(f"  Total hours: {workload['total_hours']:.1f} (limit: {teacher.max_weekly_hours})")
        print(f"  Max daily: {workload['max_daily']:.1f} (limit: {teacher.max_daily_hours})")

        if workload['total_hours'] > teacher.max_weekly_hours:
            print(f"  WARNING: Exceeds weekly limit!")
        if workload['max_daily'] > teacher.max_daily_hours:
            print(f"  WARNING: Exceeds daily limit!")

    print("\n=== DEMO COMPLETED ===")

    return result


if __name__ == "__main__":
    result = demo_teacher_constraints()