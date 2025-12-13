"""Tests for department availability and teacher conflict constraints."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from edusched.domain.building import Building, BuildingType
from edusched.domain.calendar import Calendar
from edusched.domain.department import Department
from edusched.domain.teacher import Teacher
from edusched.domain.problem import Problem
from edusched.domain.resource import Resource
from edusched.domain.session_request import SessionRequest
from edusched.domain.assignment import Assignment
from edusched.constraints.department_constraints import DepartmentAvailabilityConstraint
from edusched.constraints.teacher_constraints import (
    TeacherConflictConstraint,
    TeacherAvailabilityConstraint,
    TeacherWorkloadConstraint
)


class TestDepartmentTeacherConstraints:
    """Test suite for department and teacher constraints."""

    def test_department_availability(self):
        """Test department with blocked teaching days."""
        # Create department that doesn't teach on Fridays
        cs_department = Department(
            id="cs_dept",
            name="Computer Science Department",
            blacked_out_days=["friday", "saturday", "sunday"]
        )

        # Create session request for CS department
        request = SessionRequest(
            id="cs101",
            duration=timedelta(hours=2),
            number_of_occurrences=1,
            earliest_date=datetime(2024, 1, 15, 10, 0, tzinfo=ZoneInfo("UTC")),  # Monday
            latest_date=datetime(2024, 1, 19, 17, 0, tzinfo=ZoneInfo("UTC")),   # Friday
            department_id="cs_dept"
        )

        # Test constraint
        constraint = DepartmentAvailabilityConstraint(department_id="cs_dept")

        # Create context
        from edusched.constraints.base import ConstraintContext
        context = ConstraintContext(
            problem=None,
            resource_lookup={},
            calendar_lookup={},
            request_lookup={"cs101": request},
            department_lookup={"cs_dept": cs_department}
        )

        # Monday assignment - should pass
        monday_assignment = Assignment(
            request_id="cs101",
            occurrence_index=0,
            start_time=datetime(2024, 1, 15, 10, 0, tzinfo=ZoneInfo("UTC")),  # Monday
            end_time=datetime(2024, 1, 15, 12, 0, tzinfo=ZoneInfo("UTC")),
            assigned_resources={}
        )
        violation = constraint.check(monday_assignment, [], context)
        assert violation is None

        # Friday assignment - should fail
        friday_assignment = Assignment(
            request_id="cs101",
            occurrence_index=0,
            start_time=datetime(2024, 1, 19, 10, 0, tzinfo=ZoneInfo("UTC")),  # Friday
            end_time=datetime(2024, 1, 19, 12, 0, tzinfo=ZoneInfo("UTC")),
            assigned_resources={}
        )
        violation = constraint.check(friday_assignment, [], context)
        assert violation is not None
        assert "not available" in violation.message.lower()
        assert "friday" in violation.message.lower()

    def test_teacher_conflict_prevention(self):
        """Test preventing teacher double-booking."""
        # Create teacher
        professor = Teacher(
            id="prof_smith",
            name="Professor Smith",
            email="smith@university.edu"
        )

        # Create two session requests with the same teacher
        cs101_request = SessionRequest(
            id="cs101",
            duration=timedelta(hours=1),
            number_of_occurrences=1,
            earliest_date=datetime(2024, 1, 15, 10, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 1, 15, 16, 0, tzinfo=ZoneInfo("UTC")),
            teacher_id="prof_smith"
        )

        cs102_request = SessionRequest(
            id="cs102",
            duration=timedelta(hours=1),
            number_of_occurrences=1,
            earliest_date=datetime(2024, 1, 15, 10, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 1, 15, 16, 0, tzinfo=ZoneInfo("UTC")),
            teacher_id="prof_smith"
        )

        # Test constraint
        constraint = TeacherConflictConstraint(teacher_id="prof_smith")

        # Create context
        from edusched.constraints.base import ConstraintContext
        context = ConstraintContext(
            problem=None,
            resource_lookup={},
            calendar_lookup={},
            request_lookup={
                "cs101": cs101_request,
                "cs102": cs102_request
            },
            teacher_lookup={"prof_smith": professor}
        )

        # Existing assignment at 10:00
        existing_assignment = Assignment(
            request_id="cs101",
            occurrence_index=0,
            start_time=datetime(2024, 1, 15, 10, 0, tzinfo=ZoneInfo("UTC")),
            end_time=datetime(2024, 1, 15, 11, 0, tzinfo=ZoneInfo("UTC")),
            assigned_resources={}
        )

        # Try to assign conflicting session at 10:30
        conflicting_assignment = Assignment(
            request_id="cs102",
            occurrence_index=0,
            start_time=datetime(2024, 1, 15, 10, 30, tzinfo=ZoneInfo("UTC")),
            end_time=datetime(2024, 1, 15, 11, 30, tzinfo=ZoneInfo("UTC")),
            assigned_resources={}
        )
        violation = constraint.check(conflicting_assignment, [existing_assignment], context)
        assert violation is not None
        assert "double-booked" in violation.message.lower()
        assert "conflicts" in violation.message.lower()

        # Try to assign non-conflicting session at 11:00
        non_conflicting_assignment = Assignment(
            request_id="cs102",
            occurrence_index=0,
            start_time=datetime(2024, 1, 15, 11, 0, tzinfo=ZoneInfo("UTC")),
            end_time=datetime(2024, 1, 15, 12, 0, tzinfo=ZoneInfo("UTC")),
            assigned_resources={}
        )
        violation = constraint.check(non_conflicting_assignment, [existing_assignment], context)
        assert violation is None

    def test_teacher_availability_days(self):
        """Test teacher availability on specific days."""
        # Create teacher who only teaches Mon-Wed
        professor = Teacher(
            id="prof_jones",
            name="Professor Jones",
            preferred_days=["monday", "tuesday", "wednesday"]
        )

        # Create session request
        request = SessionRequest(
            id="math101",
            duration=timedelta(hours=1),
            number_of_occurrences=1,
            earliest_date=datetime(2024, 1, 15, 10, 0, tzinfo=ZoneInfo("UTC")),  # Monday
            latest_date=datetime(2024, 1, 19, 16, 0, tzinfo=ZoneInfo("UTC")),   # Friday
            teacher_id="prof_jones"
        )

        # Test constraint
        constraint = TeacherAvailabilityConstraint(teacher_id="prof_jones")

        # Create context
        from edusched.constraints.base import ConstraintContext
        context = ConstraintContext(
            problem=None,
            resource_lookup={},
            calendar_lookup={},
            request_lookup={"math101": request},
            teacher_lookup={"prof_jones": professor}
        )

        # Monday assignment - should pass
        monday_assignment = Assignment(
            request_id="math101",
            occurrence_index=0,
            start_time=datetime(2024, 1, 15, 10, 0, tzinfo=ZoneInfo("UTC")),  # Monday
            end_time=datetime(2024, 1, 15, 11, 0, tzinfo=ZoneInfo("UTC")),
            assigned_resources={}
        )
        violation = constraint.check(monday_assignment, [], context)
        assert violation is None

        # Friday assignment - should fail
        friday_assignment = Assignment(
            request_id="math101",
            occurrence_index=0,
            start_time=datetime(2024, 1, 19, 10, 0, tzinfo=ZoneInfo("UTC")),  # Friday
            end_time=datetime(2024, 1, 19, 11, 0, tzinfo=ZoneInfo("UTC")),
            assigned_resources={}
        )
        violation = constraint.check(friday_assignment, [], context)
        assert violation is not None
        assert "not available" in violation.message.lower()
        assert "friday" in violation.message.lower()

    def test_teacher_workload_limits(self):
        """Test teacher workload constraints."""
        # Create teacher with daily limit
        professor = Teacher(
            id="prof_brown",
            name="Professor Brown",
            max_daily_hours=4
        )

        # Create session request
        request = SessionRequest(
            id="physics101",
            duration=timedelta(hours=2),
            number_of_occurrences=1,
            earliest_date=datetime(2024, 1, 15, 9, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 1, 19, 17, 0, tzinfo=ZoneInfo("UTC")),
            teacher_id="prof_brown"
        )

        # Test constraint
        constraint = TeacherWorkloadConstraint(teacher_id="prof_brown")

        # Create additional requests for existing assignments
        physics201_request = SessionRequest(
            id="physics201",
            duration=timedelta(hours=2),
            number_of_occurrences=1,
            earliest_date=datetime(2024, 1, 15, 9, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 1, 19, 17, 0, tzinfo=ZoneInfo("UTC")),
            teacher_id="prof_brown"
        )
        physics301_request = SessionRequest(
            id="physics301",
            duration=timedelta(hours=1),
            number_of_occurrences=1,
            earliest_date=datetime(2024, 1, 15, 9, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 1, 19, 17, 0, tzinfo=ZoneInfo("UTC")),
            teacher_id="prof_brown"
        )

        # Create context
        from edusched.constraints.base import ConstraintContext
        context = ConstraintContext(
            problem=None,
            resource_lookup={},
            calendar_lookup={},
            request_lookup={
                "physics101": request,
                "physics201": physics201_request,
                "physics301": physics301_request
            },
            teacher_lookup={"prof_brown": professor}
        )

        # Existing assignments totaling 3 hours on Monday
        existing_assignments = [
            Assignment(
                request_id="physics201",
                occurrence_index=0,
                start_time=datetime(2024, 1, 15, 9, 0, tzinfo=ZoneInfo("UTC")),
                end_time=datetime(2024, 1, 15, 11, 0, tzinfo=ZoneInfo("UTC")),  # 2 hours
                assigned_resources={}
            ),
            Assignment(
                request_id="physics301",
                occurrence_index=0,
                start_time=datetime(2024, 1, 15, 13, 0, tzinfo=ZoneInfo("UTC")),
                end_time=datetime(2024, 1, 15, 14, 0, tzinfo=ZoneInfo("UTC")),  # 1 hour
                assigned_resources={}
            )
        ]

        # Try to add 2-hour class (would exceed 4-hour daily limit)
        new_assignment = Assignment(
            request_id="physics101",
            occurrence_index=0,
            start_time=datetime(2024, 1, 15, 15, 0, tzinfo=ZoneInfo("UTC")),
            end_time=datetime(2024, 1, 15, 17, 0, tzinfo=ZoneInfo("UTC")),  # 2 hours
            assigned_resources={}
        )
        violation = constraint.check(new_assignment, existing_assignments, context)
        assert violation is not None
        assert "exceed daily limit" in violation.message.lower()
        assert "4 hours" in violation.message

        # Try to add 1-hour class (within limit)
        new_assignment_1hr = Assignment(
            request_id="physics101",
            occurrence_index=0,
            start_time=datetime(2024, 1, 15, 15, 0, tzinfo=ZoneInfo("UTC")),
            end_time=datetime(2024, 1, 15, 16, 0, tzinfo=ZoneInfo("UTC")),  # 1 hour
            assigned_resources={}
        )
        violation = constraint.check(new_assignment_1hr, existing_assignments, context)
        assert violation is None  # 3 + 1 = 4 hours, within limit

    def test_multiple_teachers_per_session(self):
        """Test sessions with multiple teachers (professor + TAs)."""
        # Create teachers
        professor = Teacher(id="prof_main", name="Main Professor")
        ta1 = Teacher(id="ta1", name="Teaching Assistant 1")
        ta2 = Teacher(id="ta2", name="Teaching Assistant 2")

        # Create session with multiple teachers
        request = SessionRequest(
            id="lab_course",
            duration=timedelta(hours=3),
            number_of_occurrences=1,
            earliest_date=datetime(2024, 1, 15, 9, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 1, 19, 17, 0, tzinfo=ZoneInfo("UTC")),
            teacher_id="prof_main",
            additional_teachers=["ta1", "ta2"]
        )

        # Test constraint for TA
        constraint = TeacherConflictConstraint(teacher_id="ta1")

        # Create additional request for existing assignment
        other_request = SessionRequest(
            id="other_course",
            duration=timedelta(hours=2),
            number_of_occurrences=1,
            earliest_date=datetime(2024, 1, 15, 9, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 1, 19, 17, 0, tzinfo=ZoneInfo("UTC")),
            teacher_id="ta1"
        )

        # Create context
        from edusched.constraints.base import ConstraintContext
        context = ConstraintContext(
            problem=None,
            resource_lookup={},
            calendar_lookup={},
            request_lookup={
                "lab_course": request,
                "other_course": other_request
            },
            teacher_lookup={
                "prof_main": professor,
                "ta1": ta1,
                "ta2": ta2
            }
        )

        # Existing assignment for TA1 at same time
        existing_assignment = Assignment(
            request_id="other_course",
            occurrence_index=0,
            start_time=datetime(2024, 1, 15, 10, 0, tzinfo=ZoneInfo("UTC")),
            end_time=datetime(2024, 1, 15, 12, 0, tzinfo=ZoneInfo("UTC")),
            assigned_resources={}
        )

        # Try to assign lab course conflicting with TA1
        lab_assignment = Assignment(
            request_id="lab_course",
            occurrence_index=0,
            start_time=datetime(2024, 1, 15, 11, 0, tzinfo=ZoneInfo("UTC")),
            end_time=datetime(2024, 1, 15, 14, 0, tzinfo=ZoneInfo("UTC")),
            assigned_resources={}
        )

        violation = constraint.check(lab_assignment, [existing_assignment], context)
        assert violation is not None
        assert "double-booked" in violation.message.lower()

    def test_integration_example(self):
        """Test complete integration with departments and teachers."""
        # Create department (CS doesn't teach Friday)
        cs_dept = Department(
            id="cs",
            name="Computer Science",
            blacked_out_days=["friday"]
        )

        # Create teachers
        prof_alice = Teacher(
            id="alice",
            name="Alice Professor",
            preferred_days=["monday", "wednesday"],
            max_daily_hours=4
        )
        prof_bob = Teacher(
            id="bob",
            name="Bob Professor",
            preferred_days=["tuesday", "thursday"]
        )

        # Create buildings and resources
        building = Building(
            id="tech",
            name="Tech Building",
            building_type=BuildingType.ACADEMIC,
            address="123 Tech Street"
        )
        classroom = Resource(
            id="Room101",
            resource_type="classroom",
            capacity=30,
            building_id="tech"
        )

        # Create calendar
        calendar = Calendar(
            id="academic",
            timezone=ZoneInfo("UTC"),
            timeslot_granularity=timedelta(minutes=30)
        )

        # Create session requests
        alice_course = SessionRequest(
            id="alice_course",
            duration=timedelta(hours=2),
            number_of_occurrences=2,
            earliest_date=datetime(2024, 1, 15, 9, 0, tzinfo=ZoneInfo("UTC")),  # Monday
            latest_date=datetime(2024, 1, 19, 17, 0, tzinfo=ZoneInfo("UTC")),   # Friday
            department_id="cs",
            teacher_id="alice",
            enrollment_count=25
        )

        bob_course = SessionRequest(
            id="bob_course",
            duration=timedelta(hours=2),
            number_of_occurrences=2,
            earliest_date=datetime(2024, 1, 15, 9, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 1, 19, 17, 0, tzinfo=ZoneInfo("UTC")),
            department_id="cs",
            teacher_id="bob",
            enrollment_count=20
        )

        # Create constraints
        constraints = [
            DepartmentAvailabilityConstraint(department_id="cs"),
            TeacherConflictConstraint(teacher_id="alice"),
            TeacherConflictConstraint(teacher_id="bob"),
            TeacherAvailabilityConstraint(teacher_id="alice"),
            TeacherAvailabilityConstraint(teacher_id="bob"),
            TeacherWorkloadConstraint(teacher_id="alice"),
            TeacherWorkloadConstraint(teacher_id="bob")
        ]

        # Create problem
        problem = Problem(
            requests=[alice_course, bob_course],
            resources=[classroom],
            calendars=[calendar],
            constraints=constraints,
            buildings=[building],
            departments=[cs_dept],
            teachers=[prof_alice, prof_bob],
            institutional_calendar_id="academic"
        )

        # Verify problem structure
        assert len(problem.requests) == 2
        assert len(problem.departments) == 1
        assert len(problem.teachers) == 2
        assert len(problem.constraints) == 7

        # Test department availability
        assert cs_dept.is_day_available("monday")
        assert not cs_dept.is_day_available("friday")

        # Test teacher availability
        assert prof_alice.is_available_day("monday")
        assert not prof_alice.is_available_day("tuesday")
        assert prof_bob.is_available_day("tuesday")
        assert not prof_bob.is_available_day("monday")