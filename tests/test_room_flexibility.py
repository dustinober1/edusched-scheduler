"""Tests for room type labeling and flexible room usage."""

from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from edusched.domain.resource import (
    Resource, ResourceStatus, RoomType, Equipment
)
from edusched.domain.session_request import SessionRequest
from edusched.constraints.room_flexibility_constraints import (
    RoomTypeFlexibilityConstraint,
    RoomConversionConstraint,
    RoomCapacityOptimizationConstraint
)
from edusched.constraints.base import ConstraintContext, Violation
from edusched.domain.assignment import Assignment


def test_room_type_labeling():
    """Test basic room type labeling and classification."""
    print("\n=== Test: Room Type Labeling ===")

    # Create different types of rooms
    rooms = {
        "classroom": Resource(
            id="Eng101",
            resource_type="classroom",
            room_type=RoomType.CLASSROOM_STANDARD,
            building_id="engineering",
            capacity=50
        ),
        "breakout": Resource(
            id="BreakoutA",
            resource_type="breakout_room",
            room_type=RoomType.BREAKOUT_ROOM,
            building_id="engineering",
            capacity=10
        ),
        "conference": Resource(
            id="Conf203",
            resource_type="conference_room",
            room_type=RoomType.CONFERENCE_ROOM,
            building_id="admin",
            capacity=20,
            has_projector=True,
            has_video_conference=True
        ),
        "lecture": Resource(
            id="Auditorium",
            resource_type="lecture_hall",
            room_type=RoomType.LECTURE_HALL,
            building_id="main",
            capacity=200,
            has_microphone=True
        ),
        "computer_lab": Resource(
            id="Lab201",
            resource_type="lab",
            room_type=RoomType.COMPUTER_LAB,
            building_id="science",
            capacity=30,
            power_outlets_per_seat=2
        )
    }

    # Verify room types
    assert rooms["classroom"].room_type == RoomType.CLASSROOM_STANDARD
    assert rooms["breakout"].room_type == RoomType.BREAKOUT_ROOM
    assert rooms["conference"].room_type == RoomType.CONFERENCE_ROOM
    assert rooms["lecture"].room_type == RoomType.LECTURE_HALL
    assert rooms["computer_lab"].room_type == RoomType.COMPUTER_LAB

    # Verify capacities
    assert rooms["classroom"].capacity == 50
    assert rooms["breakout"].capacity == 10
    assert rooms["conference"].capacity == 20
    assert rooms["lecture"].capacity == 200
    assert rooms["computer_lab"].capacity == 30

    # Verify special features
    assert rooms["conference"].has_video_conference
    assert rooms["lecture"].has_microphone
    assert rooms["computer_lab"].power_outlets_per_seat == 2

    print(f"Created {len(rooms)} rooms with proper labeling")
    print("✓ Room type labeling test passed")


def test_flexible_room_usage():
    """Test flexible room usage capabilities."""
    print("\n=== Test: Flexible Room Usage ===")

    # Create a conference room that can be used as other room types
    conference_room = Resource(
        id="Conf301",
        resource_type="conference_room",
        room_type=RoomType.CONFERENCE_ROOM,
        building_id="business",
        capacity=40,
        has_projector=True,
        has_smart_board=True,
        has_video_conference=True
    )

    # Add fallback capabilities
    conference_room.add_fallback_capability(
        fallback_type=RoomType.CLASSROOM_STANDARD,
        priority=2,  # High priority
        min_capacity=30
    )
    conference_room.add_fallback_capability(
        fallback_type=RoomType.BREAKOUT_ROOM,
        priority=5,  # Lower priority
        min_capacity=5
    )
    conference_room.add_fallback_capability(
        fallback_type=RoomType.SEMINAR_ROOM,
        priority=3,
        min_capacity=20,
        conversion_time=15,  # 15 minutes to rearrange
        requires_conversion=True
    )

    # Test flexibility checks
    print(f"Can be used as classroom: {conference_room.can_be_used_as_type(RoomType.CLASSROOM_STANDARD)}")
    print(f"Can be used as breakout room: {conference_room.can_be_used_as_type(RoomType.BREAKOUT_ROOM)}")
    print(f"Can be used as seminar room: {conference_room.can_be_used_as_type(RoomType.SEMINAR_ROOM)}")
    print(f"Can be used as lecture hall: {conference_room.can_be_used_as_type(RoomType.LECTURE_HALL)}")

    assert conference_room.can_be_used_as_type(RoomType.CLASSROOM_STANDARD)
    assert conference_room.can_be_used_as_type(RoomType.BREAKOUT_ROOM)
    assert conference_room.can_be_used_as_type(RoomType.SEMINAR_ROOM)
    assert not conference_room.can_be_used_as_type(RoomType.LECTURE_HALL)  # Not listed as fallback

    # Test priority levels
    assert conference_room.get_fallback_priority(RoomType.CLASSROOM_STANDARD) == 2
    assert conference_room.get_fallback_priority(RoomType.BREAKOUT_ROOM) == 5
    assert conference_room.get_fallback_priority(RoomType.SEMINAR_ROOM) == 3

    # Test capacity requirements
    assert conference_room.meets_capacity_for_type(RoomType.CLASSROOM_STANDARD, 35)
    assert not conference_room.meets_capacity_for_type(RoomType.CLASSROOM_STANDARD, 25)  # Below min 30
    assert conference_room.meets_capacity_for_type(RoomType.BREAKOUT_ROOM, 8)
    assert not conference_room.meets_capacity_for_type(RoomType.BREAKOUT_ROOM, 3)  # Below min 5

    # Test conversion requirements
    assert not conference_room.needs_conversion_for_type(RoomType.CLASSROOM_STANDARD)
    assert not conference_room.needs_conversion_for_type(RoomType.BREAKOUT_ROOM)
    assert conference_room.needs_conversion_for_type(RoomType.SEMINAR_ROOM)
    assert conference_room.get_conversion_time(RoomType.SEMINAR_ROOM) == 15

    print("✓ Flexible room usage test passed")


def test_classroom_as_breakout_fallback():
    """Test using empty classroom as breakout room."""
    print("\n=== Test: Classroom as Breakout Fallback ===")

    # Create an empty classroom
    empty_classroom = Resource(
        id="Room205",
        resource_type="classroom",
        room_type=RoomType.CLASSROOM_STANDARD,
        building_id="arts",
        capacity=40
    )

    # Add breakout room as fallback capability
    empty_classroom.add_fallback_capability(
        fallback_type=RoomType.BREAKOUT_ROOM,
        priority=10,  # Last resort
        min_capacity=5
    )

    # Test that it can serve as breakout room
    assert empty_classroom.can_be_used_as_type(RoomType.BREAKOUT_ROOM)
    assert empty_classroom.get_fallback_priority(RoomType.BREAKOUT_ROOM) == 10

    # Create a large classroom that won't be used as breakout
    large_lecture = Resource(
        id="HallA",
        resource_type="lecture_hall",
        room_type=RoomType.LECTURE_HALL,
        building_id="main",
        capacity=300
    )

    # Large halls typically don't become breakout rooms
    # (would be impractical to convert)
    assert not large_lecture.can_be_used_as_type(RoomType.BREAKOUT_ROOM)

    print(f"Empty classroom can be used as breakout: {empty_classroom.can_be_used_as_type(RoomType.BREAKOUT_ROOM)}")
    print(f"Large lecture hall can be used as breakout: {large_lecture.can_be_used_as_type(RoomType.BREAKOUT_ROOM)}")
    print("✓ Classroom as breakout fallback test passed")


def test_room_flexibility_constraints():
    """Test room flexibility constraints."""
    print("\n=== Test: Room Flexibility Constraints ===")

    # Create a conference room with fallback capabilities
    conf_room = Resource(
        id="Conf401",
        resource_type="conference_room",
        room_type=RoomType.CONFERENCE_ROOM,
        building_id="library",
        capacity=25
    )
    conf_room.add_fallback_capability(
        RoomType.BREAKOUT_ROOM,
        priority=5,
        min_capacity=5
    )

    # Create a request for breakout room
    breakout_request = SessionRequest(
        id="GROUP_DISCUSSION",
        duration=timedelta(hours=2),
        number_of_occurrences=1,
        earliest_date=datetime(2024, 9, 10),
        latest_date=datetime(2024, 9, 10),
        enrollment_count=8
    )
    breakout_request.required_attributes = {"room_type": "breakout_room"}

    assignment = Assignment(
        request_id="GROUP_DISCUSSION",
        occurrence_index=0,
        start_time=datetime(2024, 9, 10, 14, 0, tzinfo=ZoneInfo("UTC")),
        end_time=datetime(2024, 9, 10, 16, 0, tzinfo=ZoneInfo("UTC")),
        cohort_id="fall24",
        assigned_resources={"room": [conf_room.id]}
    )

    context = ConstraintContext(
        problem=None,
        resource_lookup={conf_room.id: conf_room},
        calendar_lookup={},
        request_lookup={"GROUP_DISCUSSION": breakout_request},
        teacher_lookup={}
    )

    # Test constraint
    constraint = RoomTypeFlexibilityConstraint(conf_room.id)
    violation = constraint.check(assignment, [], context)
    print(f"Constraint violation: {violation is not None}")
    assert violation is None  # Should pass as it can be used as breakout room

    # Test with a room that cannot be used as breakout
    lab_room = Resource(
        id="Lab301",
        resource_type="lab",
        room_type=RoomType.COMPUTER_LAB,
        building_id="science",
        capacity=25
    )

    lab_assignment = Assignment(
        request_id="GROUP_DISCUSSION",
        occurrence_index=0,
        start_time=datetime(2024, 9, 10, 14, 0, tzinfo=ZoneInfo("UTC")),
        end_time=datetime(2024, 9, 10, 16, 0, tzinfo=ZoneInfo("UTC")),
        cohort_id="fall24",
        assigned_resources={"room": [lab_room.id]}
    )

    context.resource_lookup[lab_room.id] = lab_room
    lab_constraint = RoomTypeFlexibilityConstraint(lab_room.id)
    violation = lab_constraint.check(lab_assignment, [], context)
    print(f"Lab constraint violation: {violation is not None}")
    assert violation is not None  # Should fail - lab can't be breakout room

    print("✓ Room flexibility constraints test passed")


def test_room_conversion_time():
    """Test room conversion time requirements."""
    print("\n=== Test: Room Conversion Time ===")

    # Create a conference room that needs setup for seminars
    conf_room = Resource(
        id="Conf501",
        resource_type="conference_room",
        room_type=RoomType.CONFERENCE_ROOM,
        building_id="business",
        capacity=30
    )

    conf_room.add_fallback_capability(
        RoomType.SEMINAR_ROOM,
        conversion_time=30,  # 30 minutes to rearrange tables
        requires_conversion=True
    )

    # Create assignments with insufficient buffer
    assignment1 = Assignment(
        request_id="MEETING_A",
        occurrence_index=0,
        start_time=datetime(2024, 9, 10, 9, 0, tzinfo=ZoneInfo("UTC")),
        end_time=datetime(2024, 9, 10, 10, 0, tzinfo=ZoneInfo("UTC")),
        cohort_id="fall24",
        assigned_resources={"room": [conf_room.id]}
    )

    assignment2 = Assignment(
        request_id="SEMINAR_B",
        occurrence_index=0,
        start_time=datetime(2024, 9, 10, 10, 20, tzinfo=ZoneInfo("UTC")),  # Only 20 min gap
        end_time=datetime(2024, 9, 10, 12, 0, tzinfo=ZoneInfo("UTC")),
        cohort_id="fall24",
        assigned_resources={"room": [conf_room.id]}
    )

    # Create requests
    meeting_request = SessionRequest(
        id="MEETING_A",
        duration=timedelta(hours=1),
        number_of_occurrences=1,
        earliest_date=datetime(2024, 9, 1),
        latest_date=datetime(2024, 9, 30),
        enrollment_count=10,
        required_attributes={"room_type": "conference_room"}
    )

    seminar_request = SessionRequest(
        id="SEMINAR_B",
        duration=timedelta(hours=1.5),
        number_of_occurrences=1,
        earliest_date=datetime(2024, 9, 1),
        latest_date=datetime(2024, 9, 30),
        enrollment_count=15,
        required_attributes={"room_type": "seminar_room"}
    )

    context = ConstraintContext(
        problem=None,
        resource_lookup={conf_room.id: conf_room},
        calendar_lookup={},
        request_lookup={
            "MEETING_A": meeting_request,
            "SEMINAR_B": seminar_request
        },
        teacher_lookup={}
    )

    # Test conversion constraint
    conversion_constraint = RoomConversionConstraint(conf_room.id)
    violation = conversion_constraint.check(assignment2, [assignment1], context)
    print(f"Conversion constraint violation: {violation is not None}")
    assert violation is not None  # Should fail - not enough time for conversion
    assert "30 minutes for conversion" in violation.message

    print("✓ Room conversion time test passed")


def test_room_usage_tracking():
    """Test room usage tracking and statistics."""
    print("\n=== Test: Room Usage Tracking ===")

    # Create a flexible room
    room = Resource(
        id="Multi101",
        resource_type="classroom",
        room_type=RoomType.CLASSROOM_STANDARD,
        building_id="arts",
        capacity=50
    )

    room.add_fallback_capability(
        RoomType.BREAKOUT_ROOM,
        priority=5,
        min_capacity=10
    )

    # Record usage
    room.record_usage()  # Primary use as classroom
    room.record_usage(RoomType.BREAKOUT_ROOM, is_fallback=True)  # Fallback use
    room.record_usage()  # Another primary use
    room.record_usage(RoomType.BREAKOUT_ROOM, is_fallback=True)  # Another fallback

    # Get statistics
    stats = room.get_usage_stats()
    print(f"Total uses: {stats['total_uses']}")
    print(f"Primary uses: {stats['primary_uses']}")
    print(f"Fallback uses: {stats['fallback_uses']}")
    print(f"Fallback percentage: {stats['fallback_percentage']:.1f}%")
    print(f"Primary by type: {stats['primary_by_type']}")
    print(f"Fallback by type: {stats['fallback_by_type']}")

    assert stats['total_uses'] == 4
    assert stats['primary_uses'] == 2
    assert stats['fallback_uses'] == 2
    assert stats['fallback_percentage'] == 50.0
    assert stats['primary_by_type']['classroom_standard'] == 2
    assert stats['fallback_by_type']['breakout_room'] == 2

    print("✓ Room usage tracking test passed")


def run_all_tests():
    """Run all room flexibility tests."""
    print("=" * 60)
    print("ROOM TYPE LABELING & FLEXIBLE USAGE - COMPREHENSIVE TESTS")
    print("=" * 60)

    test_room_type_labeling()
    test_flexible_room_usage()
    test_classroom_as_breakout_fallback()
    test_room_flexibility_constraints()
    test_room_conversion_time()
    test_room_usage_tracking()

    print("\n" + "=" * 60)
    print("ALL ROOM FLEXIBILITY TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()