#!/usr/bin/env python3
"""Demonstration of instructor teaching constraints and room flexibility features.

This script shows how the education scheduler can:
1. Track instructor qualifications and course conflicts
2. Manage room types and flexible room usage
3. Ensure adequate setup/buffer times
4. Optimize room assignments based on capacity and type
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from edusched.domain.teacher import Teacher
from edusched.domain.resource import Resource, RoomType
from edusched.domain.session_request import SessionRequest
from edusched.domain.assignment import Assignment
from edusched.constraints.base import ConstraintContext
from edusched.constraints.instructor_constraints import (
    InstructorQualificationConstraint,
    ConcurrentTeachingConstraint,
    CourseConflictConstraint
)
from edusched.constraints.room_flexibility_constraints import (
    RoomTypeFlexibilityConstraint,
    RoomConversionConstraint
)


def main():
    print("=" * 70)
    print("EDUSCHED - INSTRUCTOR CONSTRAINTS & ROOM FLEXIBILITY DEMO")
    print("=" * 70)

    # Create instructors with different qualifications
    prof_smith = Teacher(
        id="prof_smith",
        name="Dr. Smith",
        department_id="cs",
        qualified_courses=["CS101", "CS201", "CS301"],
        excluded_courses=["CS401"],
        preferred_courses=["CS201", "CS301"]
    )

    prof_jones = Teacher(
        id="prof_jones",
        name="Dr. Jones",
        department_id="cs",
        qualified_courses=["CS101", "CS201L", "CS301"],
        mutually_exclusive_courses=[
            ["CS201", "CS201L"],  # Can't teach both sections
            ["CS301", "CS401"]    # Advanced courses conflict
        ]
    )

    # Create flexible rooms
    conference_room = Resource(
        id="Conf301",
        resource_type="conference_room",
        room_type=RoomType.CONFERENCE_ROOM,
        building_id="engineering",
        capacity=40,
        has_projector=True,
        has_smart_board=True,
        has_video_conference=True
    )

    # Add fallback capabilities to conference room
    conference_room.add_fallback_capability(
        fallback_type=RoomType.CLASSROOM_STANDARD,
        priority=2,  # High priority
        min_capacity=30
    )
    conference_room.add_fallback_capability(
        fallback_type=RoomType.SEMINAR_ROOM,
        priority=3,
        min_capacity=20,
        conversion_time=15,
        requires_conversion=True
    )

    # Create a regular classroom
    classroom = Resource(
        id="Room205",
        resource_type="classroom",
        room_type=RoomType.CLASSROOM_STANDARD,
        building_id="arts",
        capacity=50
    )

    # Create session requests
    requests = {
        "CS201": SessionRequest(
            id="CS201",
            duration=timedelta(hours=1.5),
            number_of_occurrences=3,
            earliest_date=datetime(2024, 9, 1),
            latest_date=datetime(2024, 12, 15),
            enrollment_count=35
        ),
        "CS301": SessionRequest(
            id="CS301",
            duration=timedelta(hours=1.5),
            number_of_occurrences=3,
            earliest_date=datetime(2024, 9, 1),
            latest_date=datetime(2024, 12, 15),
            enrollment_count=25,
            required_attributes={"room_type": "seminar_room"}
        ),
        "SEMINAR": SessionRequest(
            id="SEMINAR",
            duration=timedelta(hours=2),
            number_of_occurrences=1,
            earliest_date=datetime(2024, 9, 10),
            latest_date=datetime(2024, 9, 10),
            enrollment_count=30
        )
    }

    # Create assignments
    assignments = [
        Assignment(
            request_id="CS201",
            occurrence_index=0,
            start_time=datetime(2024, 9, 10, 9, 0, tzinfo=ZoneInfo("UTC")),
            end_time=datetime(2024, 9, 10, 10, 30, tzinfo=ZoneInfo("UTC")),
            cohort_id="cs_fall24",
            assigned_resources={
                "instructor": [prof_smith.id],
                "room": [classroom.id]
            }
        ),
        Assignment(
            request_id="CS301",
            occurrence_index=0,
            start_time=datetime(2024, 9, 10, 14, 0, tzinfo=ZoneInfo("UTC")),
            end_time=datetime(2024, 9, 10, 15, 30, tzinfo=ZoneInfo("UTC")),
            cohort_id="cs_fall24",
            assigned_resources={
                "instructor": [prof_smith.id],
                "room": [conference_room.id]
            }
        )
    ]

    # Build constraint context
    context = ConstraintContext(
        problem=None,
        resource_lookup={
            classroom.id: classroom,
            conference_room.id: conference_room
        },
        calendar_lookup={},
        request_lookup=requests,
        teacher_lookup={
            prof_smith.id: prof_smith,
            prof_jones.id: prof_jones
        }
    )

    print("\n1. INSTRUCTOR QUALIFICATIONS")
    print("-" * 40)
    for course_id in ["CS201", "CS301", "CS401"]:
        can_teach, reason = prof_smith.can_teach_course(course_id)
        print(f"Dr. Smith can teach {course_id}: {can_teach} - {reason}")

    print("\n2. ROOM FLEXIBILITY")
    print("-" * 40)
    print(f"Conference room primary type: {conference_room.room_type.value}")
    print(f"Can be used as classroom: {conference_room.can_be_used_as_type(RoomType.CLASSROOM_STANDARD)}")
    print(f"Can be used as seminar room: {conference_room.can_be_used_as_type(RoomType.SEMINAR_ROOM)}")
    print(f"Conversion time for seminar: {conference_room.get_conversion_time(RoomType.SEMINAR_ROOM)} minutes")

    print("\n3. CONSTRAINT VALIDATIONS")
    print("-" * 40)

    # Check instructor qualification constraint
    qual_constraint = InstructorQualificationConstraint(prof_smith.id)
    violation = qual_constraint.check(assignments[0], [], context)
    print(f"CS201 qualification check: {'PASSED' if not violation else 'VIOLATION'}")

    # Check room type flexibility
    room_constraint = RoomTypeFlexibilityConstraint(conference_room.id)
    violation = room_constraint.check(assignments[1], [], context)
    print(f"CS301 room type check: {'PASSED' if not violation else 'VIOLATION'}")

    print("\n4. COURSE CONFLICTS")
    print("-" * 40)
    conflicts = prof_jones.courses_conflict_with("CS201")
    print(f"CS201 conflicts with: {conflicts}")

    print("\n5. ROOM USAGE TRACKING")
    print("-" * 40)
    # Record some usage
    conference_room.record_usage()  # Primary use
    conference_room.record_usage(RoomType.SEMINAR_ROOM, is_fallback=True)  # Fallback use
    stats = conference_room.get_usage_stats()
    print(f"Total uses: {stats['total_uses']}")
    print(f"Primary uses: {stats['primary_uses']}")
    print(f"Fallback uses: {stats['fallback_uses']}")
    print(f"Fallback percentage: {stats['fallback_percentage']:.1f}%")

    print("\n" + "=" * 70)
    print("DEMO COMPLETED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    main()