"""Tests for classroom blackout dates functionality."""

from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from edusched.domain.resource import (
    Resource, ResourceStatus, RoomType, Equipment,
    BlackoutPeriod, MaintenanceWindow
)
from edusched.domain.building import Building, BuildingType
from edusched.constraints.blackout_constraints import BlackoutDateConstraint, BuildingBlackoutConstraint
from edusched.constraints.base import ConstraintContext, Violation
from edusched.domain.assignment import Assignment


def test_room_blackout_period():
    """Test room-specific blackout periods."""
    print("\n=== Test: Room Blackout Period ===")

    # Create a resource
    room = Resource(
        id="Eng101",
        resource_type="classroom",
        room_type=RoomType.CLASSROOM_STANDARD,
        building_id="engineering",
        capacity=50
    )

    # Add a blackout period for renovations
    blackout = BlackoutPeriod(
        start_date=date(2024, 8, 1),
        end_date=date(2024, 8, 15),
        reason="Room renovation - new flooring installation",
        affects_all_rooms=False,
        affected_resources=["Eng101"]
    )
    room.add_blackout_period(blackout)

    # Test availability during blackout
    during_blackout = datetime(2024, 8, 5, 10, 0, tzinfo=ZoneInfo("UTC"))
    available, reason = room.is_available(during_blackout, during_blackout + timedelta(hours=2))

    print(f"During blackout (Aug 5): Available = {available}")
    print(f"Reason: {reason}")
    assert not available
    assert "Room blackout" in reason

    # Test availability after blackout
    after_blackout = datetime(2024, 8, 20, 10, 0, tzinfo=ZoneInfo("UTC"))
    available, reason = room.is_available(after_blackout, after_blackout + timedelta(hours=2))

    print(f"After blackout (Aug 20): Available = {available}")
    assert available

    # Test the is_date_blacked_out method
    is_blacked, blackout_reason = room.is_date_blacked_out(date(2024, 8, 5))
    assert is_blacked
    assert blackout_reason == "Room renovation - new flooring installation"

    is_blacked, _ = room.is_date_blacked_out(date(2024, 8, 20))
    assert not is_blacked

    print("✓ Room blackout period test passed")


def test_building_wide_blackout():
    """Test building-wide blackout periods."""
    print("\n=== Test: Building-Wide Blackout ===")

    # Create building with blackout
    building = Building(
        id="engineering",
        name="Engineering Building",
        building_type=BuildingType.ACADEMIC,
        address="123 Campus Dr"
    )

    # Add building-wide blackout for HVAC replacement
    building_blackout = BlackoutPeriod(
        start_date=date(2024, 12, 20),
        end_date=date(2025, 1, 5),
        reason="HVAC system replacement - entire building",
        affects_all_rooms=True
    )
    building.add_blackout_period(building_blackout)

    # Create rooms in the building
    room1 = Resource(
        id="Eng101",
        resource_type="classroom",
        room_type=RoomType.CLASSROOM_STANDARD,
        building_id="engineering",
        capacity=50
    )

    room2 = Resource(
        id="Eng205",
        resource_type="classroom",
        room_type=RoomType.CLASSROOM_TIER1,
        building_id="engineering",
        capacity=30
    )

    # Inherit building blackouts
    room1.building_blackouts = building.blackout_periods
    room2.building_blackouts = building.blackout_periods

    # Test both rooms during blackout
    blackout_date = datetime(2024, 12, 28, 14, 0, tzinfo=ZoneInfo("UTC"))

    for room in [room1, room2]:
        available, reason = room.is_available(blackout_date, blackout_date + timedelta(hours=2))
        print(f"Room {room.id} during building blackout: Available = {available}")
        assert not available
        assert "Building blackout" in reason

    print("✓ Building-wide blackout test passed")


def test_selective_room_type_blackout():
    """Test blackout affecting specific room types."""
    print("\n=== Test: Selective Room Type Blackout ===")

    # Create blackout for all computer labs
    blackout = BlackoutPeriod(
        start_date=date(2024, 7, 10),
        end_date=date(2024, 7, 12),
        reason="Network upgrade - all computer labs affected",
        affects_all_rooms=False,
        affected_room_types=[RoomType.COMPUTER_LAB]
    )

    # Create different types of rooms
    lab = Resource(
        id="Lab201",
        resource_type="lab",
        room_type=RoomType.COMPUTER_LAB,
        building_id="engineering",
        capacity=25
    )

    classroom = Resource(
        id="Eng101",
        resource_type="classroom",
        room_type=RoomType.CLASSROOM_STANDARD,
        building_id="engineering",
        capacity=50
    )

    # Add blackout only to the lab
    lab.blackout_periods.append(blackout)

    # Test during blackout
    test_date = datetime(2024, 7, 11, 10, 0, tzinfo=ZoneInfo("UTC"))

    # Lab should be unavailable
    lab_available, _ = lab.is_available(test_date, test_date + timedelta(hours=2))
    print(f"Computer lab during selective blackout: Available = {lab_available}")
    assert not lab_available

    # Regular classroom should be available
    class_available, _ = classroom.is_available(test_date, test_date + timedelta(hours=2))
    print(f"Regular classroom during selective blackout: Available = {class_available}")
    assert class_available

    print("✓ Selective room type blackout test passed")


def test_blackout_with_exceptions():
    """Test blackout periods with exception dates."""
    print("\n=== Test: Blackout with Exception Dates ===")

    # Create blackout for summer break with exceptions for special sessions
    blackout = BlackoutPeriod(
        start_date=date(2024, 6, 1),
        end_date=date(2024, 8, 31),
        reason="Summer break - building closed",
        affects_all_rooms=True,
        exception_dates=[
            date(2024, 6, 15),  # Special summer session starts
            date(2024, 6, 16),
            date(2024, 7, 20),  # Summer workshop
            date(2024, 7, 21)
        ]
    )

    room = Resource(
        id="Eng101",
        resource_type="classroom",
        room_type=RoomType.CLASSROOM_STANDARD,
        building_id="engineering",
        capacity=50
    )
    room.building_blackouts.append(blackout)

    # Test regular blackout date (should be unavailable)
    regular_date = datetime(2024, 6, 10, 10, 0, tzinfo=ZoneInfo("UTC"))
    available, reason = room.is_available(regular_date, regular_date + timedelta(hours=2))
    print(f"Regular blackout date (June 10): Available = {available}")
    assert not available

    # Test exception date (should be available)
    exception_date = datetime(2024, 6, 15, 10, 0, tzinfo=ZoneInfo("UTC"))
    available, reason = room.is_available(exception_date, exception_date + timedelta(hours=2))
    print(f"Exception date (June 15): Available = {available}")
    assert available

    print("✓ Blackout with exceptions test passed")


def test_blackout_constraint_integration():
    """Test blackout constraints in the scheduling system."""
    print("\n=== Test: Blackout Constraint Integration ===")

    # Create resource with blackout
    room = Resource(
        id="Sci101",
        resource_type="classroom",
        room_type=RoomType.LECTURE_HALL,
        building_id="science",
        capacity=100
    )

    blackout = BlackoutPeriod(
        start_date=date(2024, 9, 1),
        end_date=date(2024, 9, 7),
        reason="Annual maintenance week",
        affects_all_rooms=False,
        affected_resources=["Sci101"]
    )
    room.add_blackout_period(blackout)

    # Create assignment during blackout
    assignment = Assignment(
        request_id="PHYS101",
        occurrence_index=0,
        start_time=datetime(2024, 9, 3, 9, 0, tzinfo=ZoneInfo("UTC")),
        end_time=datetime(2024, 9, 3, 10, 30, tzinfo=ZoneInfo("UTC")),
        cohort_id="cohort1",
        assigned_resources={"classroom": ["Sci101"]}
    )

    # Create constraint
    constraint = BlackoutDateConstraint("Sci101")

    # Create mock context
    context = ConstraintContext(
        problem=None,
        resource_lookup={"Sci101": room},
        calendar_lookup={},
        request_lookup={}
    )

    # Check constraint
    violation = constraint.check(assignment, [], context)

    print(f"Assignment during blackout detected: {violation is not None}")
    assert violation is not None
    assert "blackout" in violation.message.lower()

    # Test assignment outside blackout
    assignment_outside = Assignment(
        request_id="PHYS101",
        occurrence_index=0,
        start_time=datetime(2024, 9, 10, 9, 0, tzinfo=ZoneInfo("UTC")),
        end_time=datetime(2024, 9, 10, 10, 30, tzinfo=ZoneInfo("UTC")),
        cohort_id="cohort1",
        assigned_resources={"classroom": ["Sci101"]}
    )

    violation = constraint.check(assignment_outside, [], context)
    print(f"Assignment outside blackout detected: {violation is not None}")
    assert violation is None

    print("✓ Blackout constraint integration test passed")


def test_multiple_overlapping_blackouts():
    """Test handling of multiple overlapping blackouts."""
    print("\n=== Test: Multiple Overlapping Blackouts ===")

    room = Resource(
        id="Art105",
        resource_type="classroom",
        room_type=RoomType.ART_STUDIO,
        building_id="arts",
        capacity=20
    )

    # Room-specific blackout
    room_blackout = BlackoutPeriod(
        start_date=date(2024, 10, 1),
        end_date=date(2024, 10, 10),
        reason="Art studio renovation",
        affects_all_rooms=False,
        affected_resources=["Art105"]
    )
    room.add_blackout_period(room_blackout)

    # Building-wide blackout overlapping partially
    building_blackout = BlackoutPeriod(
        start_date=date(2024, 10, 5),
        end_date=date(2024, 10, 15),
        reason="Building inspection",
        affects_all_rooms=True
    )
    room.building_blackouts.append(building_blackout)

    # Test different dates
    test_cases = [
        (date(2024, 10, 3), "Oct 3 - Only room blackout"),
        (date(2024, 10, 8), "Oct 8 - Both blackouts"),
        (date(2024, 10, 12), "Oct 12 - Only building blackout"),
        (date(2024, 10, 16), "Oct 16 - No blackout")
    ]

    for test_date, description in test_cases:
        test_datetime = datetime.combine(test_date, datetime.min.time().replace(hour=10))
        is_blacked, reason = room.is_date_blacked_out(test_date)
        print(f"{description}: Blacked out = {is_blacked}")

        if test_date in [date(2024, 10, 3), date(2024, 10, 8), date(2024, 10, 12)]:
            assert is_blacked
        else:
            assert not is_blacked

    print("✓ Multiple overlapping blackouts test passed")


def test_blackout_period_management():
    """Test adding, removing, and querying blackout periods."""
    print("\n=== Test: Blackout Period Management ===")

    room = Resource(
        id="Music201",
        resource_type="classroom",
        room_type=RoomType.MUSIC_ROOM,
        building_id="arts",
        capacity=15
    )

    # Add multiple blackout periods
    blackouts = [
        BlackoutPeriod(
            start_date=date(2024, 3, 1),
            end_date=date(2024, 3, 7),
            reason="Spring break"
        ),
        BlackoutPeriod(
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 30),
            reason="Summer maintenance"
        ),
        BlackoutPeriod(
            start_date=date(2024, 11, 20),
            end_date=date(2024, 11, 25),
            reason="Thanksgiving break"
        )
    ]

    for blackout in blackouts:
        room.add_blackout_period(blackout)

    print(f"Added {len(room.blackout_periods)} blackout periods")
    assert len(room.blackout_periods) == 3

    # Query blackouts in a specific range
    march_blackouts = room.get_blackout_periods_in_range(date(2024, 3, 1), date(2024, 3, 31))
    print(f"Blackouts in March: {len(march_blackouts)}")
    assert len(march_blackouts) == 1

    summer_blackouts = room.get_blackout_periods_in_range(date(2024, 5, 1), date(2024, 7, 31))
    print(f"Blackouts in Summer: {len(summer_blackouts)}")
    assert len(summer_blackouts) == 1

    # Remove a blackout
    removed = room.remove_blackout_period(date(2024, 6, 1))
    print(f"Removed June blackout: {removed}")
    assert removed
    assert len(room.blackout_periods) == 2

    # Try to remove non-existent blackout
    removed = room.remove_blackout_period(date(2024, 5, 1))
    print(f"Removed non-existent May blackout: {removed}")
    assert not removed

    print("✓ Blackout period management test passed")


def run_all_tests():
    """Run all blackout dates tests."""
    print("=" * 60)
    print("CLASSROOM BLACKOUT DATES - COMPREHENSIVE TESTS")
    print("=" * 60)

    test_room_blackout_period()
    test_building_wide_blackout()
    test_selective_room_type_blackout()
    test_blackout_with_exceptions()
    test_blackout_constraint_integration()
    test_multiple_overlapping_blackouts()
    test_blackout_period_management()

    print("\n" + "=" * 60)
    print("ALL BLACKOUT DATES TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()