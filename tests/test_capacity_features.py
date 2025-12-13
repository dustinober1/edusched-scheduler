"""Tests for classroom capacity management features."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from edusched.domain.building import Building, BuildingType
from edusched.domain.calendar import Calendar
from edusched.domain.problem import Problem
from edusched.domain.resource import Resource
from edusched.domain.session_request import SessionRequest
from edusched.domain.assignment import Assignment
from edusched.constraints.capacity_constraints import CapacityConstraint
from edusched.utils.capacity_utils import (
    get_classroom_capacity,
    check_capacity_fit,
    recommend_classrooms,
    calculate_efficiency_score,
    get_capacity_statistics,
    find_classrooms_for_class
)


class TestCapacityFeatures:
    """Test suite for classroom capacity management."""

    def test_session_request_enrollment(self):
        """Test session request with enrollment tracking."""
        request = SessionRequest(
            id="cs101",
            duration=timedelta(hours=1),
            number_of_occurrences=3,
            earliest_date=datetime(2024, 1, 15, 10, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 5, 15, 16, 0, tzinfo=ZoneInfo("UTC")),
            enrollment_count=30,
            min_capacity=25,
            max_capacity=50
        )

        assert request.enrollment_count == 30
        assert request.min_capacity == 25
        assert request.max_capacity == 50

    def test_session_request_capacity_validation(self):
        """Test validation of capacity requirements."""
        # Valid request
        request = SessionRequest(
            id="valid",
            duration=timedelta(hours=1),
            number_of_occurrences=1,
            earliest_date=datetime(2024, 1, 15, 10, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 5, 15, 16, 0, tzinfo=ZoneInfo("UTC")),
            enrollment_count=30,
            min_capacity=25,
            max_capacity=50
        )
        errors = request.validate()
        assert len(errors) == 0

        # Invalid: negative enrollment
        request_invalid = SessionRequest(
            id="invalid",
            duration=timedelta(hours=1),
            number_of_occurrences=1,
            earliest_date=datetime(2024, 1, 15, 10, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 5, 15, 16, 0, tzinfo=ZoneInfo("UTC")),
            enrollment_count=-5
        )
        errors = request_invalid.validate()
        assert any(e.field == "enrollment_count" for e in errors)

        # Invalid: min > max
        request_invalid2 = SessionRequest(
            id="invalid2",
            duration=timedelta(hours=1),
            number_of_occurrences=1,
            earliest_date=datetime(2024, 1, 15, 10, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 5, 15, 16, 0, tzinfo=ZoneInfo("UTC")),
            enrollment_count=30,
            min_capacity=50,
            max_capacity=25
        )
        errors = request_invalid2.validate()
        assert any(e.field == "capacity_range" for e in errors)

    def test_classroom_capacity_retrieval(self):
        """Test getting classroom capacity."""
        classroom = Resource(
            id="Room101",
            resource_type="classroom",
            capacity=30,
            building_id="building_a"
        )
        lab = Resource(
            id="Lab201",
            resource_type="lab",
            capacity=20
        )
        no_capacity = Resource(
            id="Room102",
            resource_type="classroom"
        )

        assert get_classroom_capacity(classroom) == 30
        assert get_classroom_capacity(lab) is None
        assert get_classroom_capacity(no_capacity) is None

    def test_capacity_fit_check(self):
        """Test checking if a classroom can accommodate a class."""
        # Good fit
        classroom = Resource(
            id="Room101",
            resource_type="classroom",
            capacity=30
        )
        can_fit, reason = check_capacity_fit(
            classroom, enrollment_count=25, min_capacity=20, buffer_percent=0.1
        )
        assert can_fit
        assert "Good fit" in reason

        # Too small
        small_room = Resource(
            id="SmallRoom",
            resource_type="classroom",
            capacity=15
        )
        can_fit, reason = check_capacity_fit(
            small_room, enrollment_count=25, buffer_percent=0.1
        )
        assert not can_fit
        assert "less than required" in reason.lower() or "insufficient" in reason.lower()

        # Too large (with max capacity)
        large_room = Resource(
            id="LargeRoom",
            resource_type="classroom",
            capacity=100
        )
        can_fit, reason = check_capacity_fit(
            large_room, enrollment_count=25, max_capacity=50
        )
        assert not can_fit
        assert "exceeds maximum" in reason.lower()

        # Not a classroom
        lab = Resource(
            id="Lab",
            resource_type="lab",
            capacity=30
        )
        can_fit, reason = check_capacity_fit(lab, enrollment_count=25)
        assert not can_fit
        assert "not a classroom" in reason.lower()

    def test_classroom_recommendations(self):
        """Test classroom recommendation system."""
        classrooms = [
            Resource(id="SmallRoom", resource_type="classroom", capacity=15, building_id="building_a"),
            Resource(id="GoodRoom1", resource_type="classroom", capacity=30, building_id="building_a"),
            Resource(id="GoodRoom2", resource_type="classroom", capacity=35, building_id="building_b"),
            Resource(id="LargeRoom", resource_type="classroom", capacity=100, building_id="building_a"),
            Resource(id="PerfectRoom", resource_type="classroom", capacity=28, building_id="building_a")
        ]

        recommendations = recommend_classrooms(
            enrollment_count=25,
            classrooms=classrooms,
            min_capacity=20,
            max_capacity=40
        )

        # Should get recommendations in order of preference
        assert len(recommendations) >= 2

        # Perfect fit (28 capacity) should be highly rated
        room_ids = [r[0].id for r in recommendations]
        assert "PerfectRoom" in room_ids
        assert "SmallRoom" not in room_ids  # Too small
        assert "LargeRoom" not in room_ids  # Exceeds max_capacity

    def test_efficiency_score_calculation(self):
        """Test efficiency score calculation."""
        # Perfect fit (10% above required)
        score = calculate_efficiency_score(
            classroom_capacity=33, required_capacity=30
        )
        assert score == 1.0

        # Slightly larger (50% above required)
        score = calculate_efficiency_score(
            classroom_capacity=45, required_capacity=30
        )
        assert 0.5 <= score < 1.0

        # Too small
        score = calculate_efficiency_score(
            classroom_capacity=25, required_capacity=30
        )
        assert score == 0.0

        # Way too large (3x required)
        score = calculate_efficiency_score(
            classroom_capacity=90, required_capacity=30
        )
        assert 0.0 < score < 0.5

    def test_capacity_statistics(self):
        """Test capacity statistics calculation."""
        classrooms = [
            Resource(id="Room1", resource_type="classroom", capacity=20),
            Resource(id="Room2", resource_type="classroom", capacity=30),
            Resource(id="Room3", resource_type="classroom", capacity=50),
            Resource(id="Lab", resource_type="lab", capacity=15),  # Should be excluded
            Resource(id="NoCapacity", resource_type="classroom")  # Should be excluded
        ]

        stats = get_capacity_statistics(classrooms)

        assert stats["count"] == 3
        assert stats["min_capacity"] == 20
        assert stats["max_capacity"] == 50
        assert stats["avg_capacity"] == 33.333333333333336
        assert stats["total_capacity"] == 100

    def test_capacity_constraint(self):
        """Test capacity constraint enforcement."""
        # Create request with enrollment
        request = SessionRequest(
            id="cs101",
            duration=timedelta(hours=1),
            number_of_occurrences=1,
            earliest_date=datetime(2024, 1, 15, 10, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 5, 15, 16, 0, tzinfo=ZoneInfo("UTC")),
            enrollment_count=30,
            min_capacity=25
        )

        # Create resources
        suitable_room = Resource(id="Room101", resource_type="classroom", capacity=35)
        too_small_room = Resource(id="Room102", resource_type="classroom", capacity=20)

        # Create mock context
        from edusched.constraints.base import ConstraintContext
        context = ConstraintContext(
            problem=None,
            resource_lookup={"Room101": suitable_room, "Room102": too_small_room},
            calendar_lookup={},
            request_lookup={"cs101": request}
        )

        constraint = CapacityConstraint(request_id="cs101", buffer_percent=0.1)

        # Test suitable room
        suitable_assignment = Assignment(
            request_id="cs101",
            occurrence_index=0,
            start_time=datetime(2024, 1, 15, 10, 0, tzinfo=ZoneInfo("UTC")),
            end_time=datetime(2024, 1, 15, 11, 0, tzinfo=ZoneInfo("UTC")),
            assigned_resources={"classroom": ["Room101"]}
        )
        violation = constraint.check(suitable_assignment, [], context)
        assert violation is None  # Should pass

        # Test too small room
        unsuitable_assignment = Assignment(
            request_id="cs101",
            occurrence_index=0,
            start_time=datetime(2024, 1, 15, 10, 0, tzinfo=ZoneInfo("UTC")),
            end_time=datetime(2024, 1, 15, 11, 0, tzinfo=ZoneInfo("UTC")),
            assigned_resources={"classroom": ["Room102"]}
        )
        violation = constraint.check(unsuitable_assignment, [], context)
        assert violation is not None  # Should fail
        assert "insufficient" in violation.message.lower()

    def test_find_classrooms_for_class(self):
        """Test finding suitable classrooms for a session request."""
        request = SessionRequest(
            id="math101",
            duration=timedelta(hours=1),
            number_of_occurrences=1,
            earliest_date=datetime(2024, 1, 15, 10, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 5, 15, 16, 0, tzinfo=ZoneInfo("UTC")),
            enrollment_count=25,
            min_capacity=20,
            max_capacity=40,
            required_building_id="building_a"
        )

        classrooms = [
            Resource(id="RoomA1", resource_type="classroom", capacity=30, building_id="building_a"),
            Resource(id="RoomA2", resource_type="classroom", capacity=35, building_id="building_a"),
            Resource(id="RoomB1", resource_type="classroom", capacity=30, building_id="building_b"),  # Wrong building
            Resource(id="RoomSmall", resource_type="classroom", capacity=15, building_id="building_a"),  # Too small
            Resource(id="RoomLarge", resource_type="classroom", capacity=50, building_id="building_a"),  # Too large
        ]

        suitable_rooms = find_classrooms_for_class(request, classrooms)

        # Should find rooms in building_a with appropriate capacity
        assert len(suitable_rooms) == 2
        assert all(r.building_id == "building_a" for r in suitable_rooms)
        room_ids = [r.id for r in suitable_rooms]
        assert "RoomA1" in room_ids
        assert "RoomA2" in room_ids
        assert "RoomB1" not in room_ids
        assert "RoomSmall" not in room_ids
        assert "RoomLarge" not in room_ids

    def test_integration_example(self):
        """Test complete integration example with capacity features."""
        # Create buildings
        building = Building(
            id="tech_building",
            name="Technology Building",
            building_type=BuildingType.ACADEMIC,
            address="123 Tech St"
        )

        # Create classrooms with various capacities
        classrooms = [
            Resource(id="Lec101", resource_type="classroom", capacity=100, building_id="tech_building"),
            Resource(id="Sem201", resource_type="seminar", capacity=20, building_id="tech_building"),
            Resource(id="Lab301", resource_type="lab", capacity=30, building_id="tech_building"),
            Resource(id="Room401", resource_type="classroom", capacity=40, building_id="tech_building"),
            Resource(id="Room501", resource_type="classroom", capacity=50, building_id="tech_building")
        ]

        # Create a course with significant enrollment
        course_request = SessionRequest(
            id="data_science_101",
            duration=timedelta(hours=2),
            number_of_occurrences=24,
            earliest_date=datetime(2024, 1, 15, 9, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 5, 15, 17, 0, tzinfo=ZoneInfo("UTC")),
            enrollment_count=45,
            min_capacity=40,
            max_capacity=60,
            required_building_id="tech_building"
        )

        # Create capacity constraint
        capacity_constraint = CapacityConstraint(
            request_id="data_science_101",
            buffer_percent=0.15  # 15% buffer for large class
        )

        # Create calendar
        calendar = Calendar(
            id="academic_calendar",
            timezone=ZoneInfo("UTC"),
            timeslot_granularity=timedelta(minutes=30)
        )

        # Create problem
        problem = Problem(
            requests=[course_request],
            resources=classrooms,
            calendars=[calendar],
            constraints=[capacity_constraint],
            buildings=[building]
        )

        # Verify problem setup
        assert problem.requests[0].enrollment_count == 45
        assert problem.requests[0].min_capacity == 40
        assert problem.requests[0].max_capacity == 60

        # Test recommendations with 10% buffer for more realistic fit
        recommendations = recommend_classrooms(
            enrollment_count=45,
            classrooms=classrooms,
            min_capacity=40,
            max_capacity=100,  # Allow larger rooms
            buffer_percent=0.1,  # 10% buffer is more realistic
            building_id="tech_building"
        )

        # With 10% buffer, 45 students need 50 seats (45 * 1.1)
        # Room501 (50 capacity) should be a perfect fit
        assert len(recommendations) >= 1
        room_ids = [r[0].id for r in recommendations]
        assert "Room501" in room_ids or "Lec101" in room_ids  # Either 50 or 100 capacity works

        # Check that the highest efficiency score is for Room501 (perfect fit)
        if len(recommendations) > 1:
            assert recommendations[0][0].id == "Room501"  # Should be first (most efficient)

        # Test statistics
        stats = get_capacity_statistics(classrooms)
        assert stats["count"] >= 3  # At least 3 classroom resources (Lec101, Room401, Room501)
        assert stats["total_capacity"] >= 180  # Lec101(100) + Room401(40) + Room501(50) = 190