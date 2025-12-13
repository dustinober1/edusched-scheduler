"""Tests for instructor teaching constraints and course conflicts."""

from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from edusched.domain.teacher import Teacher
from edusched.domain.session_request import SessionRequest
from edusched.domain.assignment import Assignment
from edusched.constraints.instructor_constraints import (
    InstructorQualificationConstraint,
    ConcurrentTeachingConstraint,
    InstructorSetupBufferConstraint,
    CourseConflictConstraint
)
from edusched.constraints.base import ConstraintContext, Violation


def test_instructor_qualification():
    """Test instructor qualification constraints."""
    print("\n=== Test: Instructor Qualification ===")

    # Create instructor with qualified courses
    instructor = Teacher(
        id="prof_smith",
        name="Dr. Smith",
        department_id="cs",
        qualified_courses=["CS101", "CS201", "CS301"],
        excluded_courses=["CS401"],
        preferred_courses=["CS201", "CS301"]
    )

    # Test qualification check
    can_teach, reason = instructor.can_teach_course("CS201")
    print(f"Can teach CS201: {can_teach} - {reason}")
    assert can_teach
    assert instructor.prefers_teaching("CS201")

    can_teach, reason = instructor.can_teach_course("CS401")
    print(f"Can teach CS401: {can_teach} - {reason}")
    assert not can_teach
    assert reason == "Teacher has excluded this course"

    can_teach, reason = instructor.can_teach_course("MATH101")
    print(f"Can teach MATH101: {can_teach} - {reason}")
    assert not can_teach
    assert reason == "Teacher not qualified to teach this course"

    # Test constraint
    constraint = InstructorQualificationConstraint("prof_smith")

    # Create mock context
    request = SessionRequest(
        id="CS201",
        duration=timedelta(hours=1.5),
        number_of_occurrences=3,
        earliest_date=datetime(2024, 9, 1),
        latest_date=datetime(2024, 12, 15),
        enrollment_count=30
    )

    assignment = Assignment(
        request_id="CS201",
        occurrence_index=0,
        start_time=datetime(2024, 9, 10, 10, 0, tzinfo=ZoneInfo("UTC")),
        end_time=datetime(2024, 9, 10, 11, 30, tzinfo=ZoneInfo("UTC")),
        cohort_id="cs_fall24",
        assigned_resources={"instructor": ["prof_smith"]}
    )

    context = ConstraintContext(
        problem=None,
        resource_lookup={},
        calendar_lookup={},
        request_lookup={"CS201": request},
        teacher_lookup={"prof_smith": instructor}
    )

    # Should not violate for qualified course
    violation = constraint.check(assignment, [], context)
    assert violation is None

    # Should violate for unqualified course
    request.id = "MATH101"
    assignment.request_id = "MATH101"
    # Add MATH101 to context
    context.request_lookup["MATH101"] = request
    violation = constraint.check(assignment, [], context)
    print(f"Violation for MATH101: {violation}")
    assert violation is not None
    assert "not qualified" in violation.message

    print("✓ Instructor qualification test passed")


def test_concurrent_teaching_constraint():
    """Test concurrent teaching prevention."""
    print("\n=== Test: Concurrent Teaching Constraint ===")

    instructor = Teacher(
        id="prof_jones",
        name="Dr. Jones",
        concurrent_teaching_limit=1
    )

    # Add mutual exclusivity for lab courses
    instructor.mutually_exclusive_courses = [
        ["CS201L", "CS301L"],  # Can't teach both lab sections
        ["MATH201", "MATH301"]  # Can't teach both math courses
    ]

    constraint = ConcurrentTeachingConstraint("prof_jones")

    # Create assignments with time overlap
    assignment1 = Assignment(
        request_id="CS201",
        occurrence_index=0,
        start_time=datetime(2024, 9, 10, 10, 0, tzinfo=ZoneInfo("UTC")),
        end_time=datetime(2024, 9, 10, 11, 30, tzinfo=ZoneInfo("UTC")),
        cohort_id="cs_fall24",
        assigned_resources={"instructor": ["prof_jones"]}
    )

    assignment2 = Assignment(
        request_id="CS301",
        occurrence_index=0,
        start_time=datetime(2024, 9, 10, 11, 0, tzinfo=ZoneInfo("UTC")),
        end_time=datetime(2024, 9, 10, 12, 30, tzinfo=ZoneInfo("UTC")),
        cohort_id="cs_fall24",
        assigned_resources={"instructor": ["prof_jones"]}
    )

    context = ConstraintContext(
        problem=None,
        resource_lookup={},
        calendar_lookup={},
        request_lookup={},
        teacher_lookup={"prof_jones": instructor}
    )

    # Add requests to context
    context.request_lookup.update({
        "CS201": SessionRequest(
            id="CS201",
            duration=timedelta(hours=1.5),
            number_of_occurrences=3,
            earliest_date=datetime(2024, 9, 1),
            latest_date=datetime(2024, 12, 15),
            enrollment_count=30
        ),
        "CS301": SessionRequest(
            id="CS301",
            duration=timedelta(hours=1.5),
            number_of_occurrences=3,
            earliest_date=datetime(2024, 9, 1),
            latest_date=datetime(2024, 12, 15),
            enrollment_count=25
        )
    })

    # Should detect concurrent teaching
    violation = constraint.check(assignment2, [assignment1], context)
    print(f"Concurrent teaching violation: {violation}")
    assert violation is not None
    assert "simultaneously" in violation.message

    # Test mutually exclusive courses
    assignment3 = Assignment(
        request_id="CS201L",
        occurrence_index=0,
        start_time=datetime(2024, 9, 11, 14, 0, tzinfo=ZoneInfo("UTC")),
        end_time=datetime(2024, 9, 11, 17, 0, tzinfo=ZoneInfo("UTC")),
        cohort_id="cs_fall24",
        assigned_resources={"instructor": ["prof_jones"]}
    )

    # Create mock request for CS201L
    request_cs201l = SessionRequest(
        id="CS201L",
        duration=timedelta(hours=3),
        number_of_occurrences=1,
        earliest_date=datetime(2024, 9, 1),
        latest_date=datetime(2024, 12, 15),
        enrollment_count=20
    )
    context.request_lookup["CS201L"] = request_cs201l

    # Test mutual exclusivity with CourseConflictConstraint
    course_conflict_constraint = CourseConflictConstraint("prof_jones")

    print(f"Checking CS201L against existing assignments")
    print(f"CS201L conflicts: {instructor.courses_conflict_with('CS201L')}")

    # Create an assignment for CS301L to show the conflict
    assignment_cs301l = Assignment(
        request_id="CS301L",
        occurrence_index=0,
        start_time=datetime(2024, 9, 13, 9, 0, tzinfo=ZoneInfo("UTC")),  # Different day
        end_time=datetime(2024, 9, 13, 12, 0, tzinfo=ZoneInfo("UTC")),
        cohort_id="cs_fall24",
        assigned_resources={"instructor": ["prof_jones"]}
    )
    context.request_lookup["CS301L"] = request_cs201l  # Reuse the request object

    violation = course_conflict_constraint.check(assignment_cs301l, [assignment3], context)
    print(f"Mutual exclusivity violation: {violation}")
    assert violation is not None

    print("✓ Concurrent teaching constraint test passed")


def test_instructor_setup_buffer():
    """Test instructor setup and break time requirements."""
    print("\n=== Test: Instructor Setup Buffer ===")

    instructor = Teacher(
        id="prof_davis",
        name="Dr. Davis",
        setup_time_minutes=15,
        cleanup_time_minutes=10,
        preferred_block_gap=30
    )

    # Add course-specific requirements
    instructor.add_course_requirement(
        "CHEM101",
        setup_minutes=30,  # Lab requires more setup
        cleanup_minutes=20
    )

    instructor.add_course_requirement(
        "ART101",
        buffer_days_before=1,  # Needs day before to prep
        buffer_days_after=1   # Needs day after for cleanup
    )

    constraint = InstructorSetupBufferConstraint("prof_davis")

    # Create assignments with insufficient buffer
    assignment1 = Assignment(
        request_id="CHEM101",
        occurrence_index=0,
        start_time=datetime(2024, 9, 10, 10, 0, tzinfo=ZoneInfo("UTC")),
        end_time=datetime(2024, 9, 10, 12, 0, tzinfo=ZoneInfo("UTC")),
        cohort_id="chem_fall24",
        assigned_resources={"instructor": ["prof_davis"]}
    )

    assignment2 = Assignment(
        request_id="PHYS101",
        occurrence_index=0,
        start_time=datetime(2024, 9, 10, 12, 10, tzinfo=ZoneInfo("UTC")),  # Only 10 min gap
        end_time=datetime(2024, 9, 10, 14, 10, tzinfo=ZoneInfo("UTC")),
        cohort_id="phys_fall24",
        assigned_resources={"instructor": ["prof_davis"]}
    )

    context = ConstraintContext(
        problem=None,
        resource_lookup={},
        calendar_lookup={},
        request_lookup={
            "CHEM101": SessionRequest(
                id="CHEM101",
                duration=timedelta(hours=2),
                number_of_occurrences=1,
                earliest_date=datetime(2024, 9, 1),
                latest_date=datetime(2024, 12, 15),
                enrollment_count=25
            ),
            "PHYS101": SessionRequest(
                id="PHYS101",
                duration=timedelta(hours=2),
                number_of_occurrences=1,
                earliest_date=datetime(2024, 9, 1),
                latest_date=datetime(2024, 12, 15),
                enrollment_count=25
            )
        },
        teacher_lookup={"prof_davis": instructor}
    )

    # Should detect insufficient buffer
    # CHEM101 needs 20 min cleanup + 15 min setup for PHYS101 = 35 min
    violation = constraint.check(assignment2, [assignment1], context)
    assert violation is not None
    assert "Insufficient buffer" in violation.message

    # Test with adequate buffer
    assignment2.start_time = datetime(2024, 9, 10, 12, 45, tzinfo=ZoneInfo("UTC"))
    violation = constraint.check(assignment2, [assignment1], context)
    assert violation is None

    print("✓ Instructor setup buffer test passed")


def test_course_conflicts():
    """Test course conflict prevention."""
    print("\n=== Test: Course Conflicts ===")

    instructor = Teacher(
        id="prof_wilson",
        name="Dr. Wilson"
    )

    # Define conflicting course pairs
    instructor.mutually_exclusive_courses = [
        ["CS101", "CS101L"],  # Lecture and lab of same course
        ["ADV301", "ADV302"],  # Advanced topics that conflict
        ["RESEARCH1", "RESEARCH2", "RESEARCH3"]  # Research seminars
    ]

    constraint = CourseConflictConstraint("prof_wilson")

    # Create assignments for conflicting courses
    assignment1 = Assignment(
        request_id="CS101",
        occurrence_index=0,
        start_time=datetime(2024, 9, 10, 9, 0, tzinfo=ZoneInfo("UTC")),
        end_time=datetime(2024, 9, 10, 10, 30, tzinfo=ZoneInfo("UTC")),
        cohort_id="cs_fall24",
        assigned_resources={"instructor": ["prof_wilson"]}
    )

    assignment2 = Assignment(
        request_id="CS101L",
        occurrence_index=0,
        start_time=datetime(2024, 9, 12, 14, 0, tzinfo=ZoneInfo("UTC")),  # Different day/time
        end_time=datetime(2024, 9, 12, 17, 0, tzinfo=ZoneInfo("UTC")),
        cohort_id="cs_fall24",
        assigned_resources={"instructor": ["prof_wilson"]}
    )

    context = ConstraintContext(
        problem=None,
        resource_lookup={},
        calendar_lookup={},
        request_lookup={
            "CS101": SessionRequest(
                id="CS101",
                duration=timedelta(hours=1.5),
                number_of_occurrences=1,
                earliest_date=datetime(2024, 9, 1),
                latest_date=datetime(2024, 12, 15),
                enrollment_count=100
            ),
            "CS101L": SessionRequest(
                id="CS101L",
                duration=timedelta(hours=3),
                number_of_occurrences=1,
                earliest_date=datetime(2024, 9, 1),
                latest_date=datetime(2024, 12, 15),
                enrollment_count=30
            )
        },
        teacher_lookup={"prof_wilson": instructor}
    )

    # Should detect conflict even on different days
    violation = constraint.check(assignment2, [assignment1], context)
    assert violation is not None
    assert "conflicts with CS101" in violation.message

    # Test non-conflicting courses
    assignment3 = Assignment(
        request_id="MATH101",
        occurrence_index=0,
        start_time=datetime(2024, 9, 15, 10, 0, tzinfo=ZoneInfo("UTC")),
        end_time=datetime(2024, 9, 15, 11, 30, tzinfo=ZoneInfo("UTC")),
        cohort_id="math_fall24",
        assigned_resources={"instructor": ["prof_wilson"]}
    )

    context.request_lookup["MATH101"] = SessionRequest(
        id="MATH101",
        duration=timedelta(hours=1.5),
        number_of_occurrences=1,
        earliest_date=datetime(2024, 9, 1),
        latest_date=datetime(2024, 12, 15),
        enrollment_count=50
    )

    violation = constraint.check(assignment3, [assignment1], context)
    assert violation is None

    print("✓ Course conflicts test passed")


def test_instructor_with_buffer_days():
    """Test instructor buffer day requirements."""
    print("\n=== Test: Instructor Buffer Days ===")

    instructor = Teacher(
        id="prof_miller",
        name="Dr. Miller"
    )

    # Add course with buffer day requirements
    instructor.add_course_requirement(
        "CONF101",
        buffer_days_before=2,  # Needs 2 days before to prepare
        buffer_days_after=1     # Needs 1 day after for follow-up
    )

    # Test buffer day retrieval
    buffer = instructor.get_course_buffer_days("CONF101")
    print(f"Buffer days for CONF101: Before = {buffer['before']}, After = {buffer['after']}")
    assert buffer['before'] == 2
    assert buffer['after'] == 1

    # Test default buffer for courses without specific requirements
    default_buffer = instructor.get_course_buffer_days("GEN101")
    print(f"Default buffer days for GEN101: Before = {default_buffer['before']}, After = {default_buffer['after']}")
    assert default_buffer['before'] == 0
    assert default_buffer['after'] == 0

    # Test course-specific setup/cleanup times
    assert instructor.get_course_setup_time("CONF101") == instructor.setup_time_minutes
    assert instructor.get_course_cleanup_time("CONF101") == instructor.cleanup_time_minutes

    print("✓ Instructor buffer days test passed")


def test_instructor_workload_limits():
    """Test instructor workload and teaching limits."""
    print("\n=== Test: Instructor Workload Limits ===")

    instructor = Teacher(
        id="prof_anderson",
        name="Dr. Anderson",
        max_daily_hours=6,
        max_weekly_hours=20,
        max_consecutive_hours=3
    )

    # Create assignments approaching limits
    assignments = []

    # Day 1: 5 hours
    assignments.append(Assignment(
        request_id="COURSE1",
        occurrence_index=0,
        start_time=datetime(2024, 9, 10, 9, 0, tzinfo=ZoneInfo("UTC")),
        end_time=datetime(2024, 9, 10, 14, 0, tzinfo=ZoneInfo("UTC")),
        cohort_id="fall24",
        assigned_resources={"instructor": ["prof_anderson"]}
    ))

    # Day 2: 4 hours (total weekly would be 9)
    assignments.append(Assignment(
        request_id="COURSE2",
        occurrence_index=0,
        start_time=datetime(2024, 9, 11, 10, 0, tzinfo=ZoneInfo("UTC")),
        end_time=datetime(2024, 9, 11, 14, 0, tzinfo=ZoneInfo("UTC")),
        cohort_id="fall24",
        assigned_resources={"instructor": ["prof_anderson"]}
    ))

    # Calculate workload
    workload = instructor.get_teaching_load_for_period(
        date(2024, 9, 9),  # Start of week
        date(2024, 9, 15), # End of week
        assignments
    )

    print(f"Total hours: {workload['total_hours']}")
    print(f"Course count: {workload['course_count']}")
    print(f"Days teaching: {workload['days_teaching']}")
    print(f"Average hours per day: {workload['average_hours_per_day']:.1f}")

    assert workload['total_hours'] == 9.0
    assert workload['course_count'] == 2
    assert workload['days_teaching'] == 2

    print("✓ Instructor workload limits test passed")


def run_all_tests():
    """Run all instructor constraint tests."""
    print("=" * 60)
    print("INSTRUCTOR TEACHING CONSTRAINTS - COMPREHENSIVE TESTS")
    print("=" * 60)

    test_instructor_qualification()
    test_concurrent_teaching_constraint()
    test_instructor_setup_buffer()
    test_course_conflicts()
    test_instructor_with_buffer_days()
    test_instructor_workload_limits()

    print("\n" + "=" * 60)
    print("ALL INSTRUCTOR CONSTRAINT TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()