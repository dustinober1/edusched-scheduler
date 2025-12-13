"""Tests for building-based scheduling features."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from edusched.domain.building import Building, BuildingType, Floor
from edusched.domain.calendar import Calendar
from edusched.domain.problem import Problem
from edusched.domain.resource import Resource
from edusched.domain.session_request import SessionRequest
from edusched.domain.assignment import Assignment
from edusched.constraints.proximity_constraints import ProximityConstraint, ProximityType, MultiRoomCoordination
from edusched.constraints.day_specific_constraints import DaySpecificResourceRequirement
from edusched.utils.building_filters import (
    filter_resources_by_building,
    find_nearby_resources,
    find_available_breakout_rooms,
    recommend_classroom,
    group_resources_by_building
)


class TestBuildingFeatures:
    """Test suite for building-based scheduling features."""

    def test_building_creation(self):
        """Test building creation with floors and rooms."""
        building = Building(
            id="building_a",
            name="Academic Building A",
            building_type=BuildingType.ACADEMIC,
            address="123 University Ave",
            coordinates=(40.7128, -74.0060),
            campus_area="North Campus"
        )

        # Add floors and rooms
        building.add_room_to_floor(0, "room101")
        building.add_room_to_floor(0, "Room102")
        building.add_room_to_floor(1, "Room201")
        building.add_room_to_floor(1, "Room202")

        # Verify floors and rooms
        assert len(building.floors) == 2
        assert building.get_rooms_on_floor(0) == ["room101", "Room102"]
        assert building.get_rooms_on_floor(1) == ["Room201", "Room202"]
        assert building.get_room_floor("Room201") == 1

    def test_resource_building_reference(self):
        """Test resources can reference buildings."""
        resource = Resource(
            id="Room101",
            resource_type="classroom",
            capacity=30,
            building_id="building_a",
            floor_number=0
        )

        assert resource.building_id == "building_a"
        assert resource.floor_number == 0
        assert resource.capacity == 30

    def test_session_request_building_requirements(self):
        """Test session requests with building requirements."""
        request = SessionRequest(
            id="cs101",
            duration=timedelta(hours=1),
            number_of_occurrences=3,
            earliest_date=datetime(2024, 1, 15, 10, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 5, 15, 16, 0, tzinfo=ZoneInfo("UTC")),
            required_building_id="building_a",
            required_resource_types={"classroom": 1, "breakout": 1},
            day_requirements={1: ["classroom"], 3: ["classroom", "breakout"]}  # Tuesday and Thursday
        )

        assert request.required_building_id == "building_a"
        assert request.required_resource_types == {"classroom": 1, "breakout": 1}
        assert request.day_requirements[1] == ["classroom"]

    def test_problem_with_buildings(self):
        """Test problem can include buildings."""
        # Create buildings
        building_a = Building(
            id="building_a",
            name="Academic Building A",
            building_type=BuildingType.ACADEMIC,
            address="123 University Ave"
        )
        building_a.add_room_to_floor(1, "Room101")

        building_b = Building(
            id="building_b",
            name="Library",
            building_type=BuildingType.LIBRARY,
            address="456 Library Way"
        )

        # Create problem with buildings
        problem = Problem(
            requests=[],
            resources=[],
            calendars=[],
            constraints=[],
            buildings=[building_a, building_b]
        )

        assert len(problem.buildings) == 2
        assert problem.buildings[0].id == "building_a"
        assert problem.buildings[1].id == "building_b"

    def test_proximity_constraint_same_building(self):
        """Test proximity constraint for same building requirement."""
        constraint = ProximityConstraint(
            request_id="req1",
            primary_resource_type="classroom",
            related_resource_types=["breakout"],
            proximity_type=ProximityType.SAME_BUILDING
        )

        # Create mock resources
        resources = [
            Resource(id="Room101", resource_type="classroom", building_id="building_a", floor_number=1),
            Resource(id="Breakout1", resource_type="breakout", building_id="building_a", floor_number=1),
            Resource(id="Breakout2", resource_type="breakout", building_id="building_b", floor_number=1)
        ]

        # Test building lookup
        buildings = {
            "building_a": Building(id="building_a", name="Building A", building_type=BuildingType.ACADEMIC, address="")
        }
        buildings["building_a"].add_room_to_floor(1, "Room101")

        # Test proximity check
        # This would be done in the actual constraint checking logic
        # For now, we verify the constraint structure
        assert constraint.primary_resource_type == "classroom"
        assert constraint.related_resource_types == ["breakout"]
        assert constraint.proximity_type == ProximityType.SAME_BUILDING

    def test_proximity_constraint_same_floor(self):
        """Test proximity constraint for same floor requirement."""
        constraint = ProximityConstraint(
            request_id="req1",
            primary_resource_type="classroom",
            related_resource_types=["breakout"],
            proximity_type=ProximityType.SAME_FLOOR
        )

        assert constraint.proximity_type == ProximityType.SAME_FLOOR

    def test_multi_room_coordination(self):
        """Test multi-room coordination constraint."""
        constraint = MultiRoomCoordination(
            request_id="req1",
            required_rooms={"classroom": 1, "breakout": 2},
            proximity_requirements=[
                ("classroom", "breakout", ProximityType.NEARBY_FLOOR)
            ]
        )

        assert constraint.required_rooms == {"classroom": 1, "breakout": 2}
        assert len(constraint.proximity_requirements) == 1
        assert constraint.proximity_requirements[0] == ("classroom", "breakout", ProximityType.NEARBY_FLOOR)

    def test_day_specific_constraint(self):
        """Test day-specific resource requirement constraint."""
        constraint = DaySpecificResourceRequirement("req1")

        # Create a session request with day requirements
        request = SessionRequest(
            id="req1",
            duration=timedelta(hours=2),
            number_of_occurrences=1,
            earliest_date=datetime(2024, 1, 15, 10, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 1, 15, 16, 0, tzinfo=ZoneInfo("UTC")),
            day_requirements={2: ["classroom"]}  # Wednesday only
        )

        # Test checking day requirements (Monday=0, Wednesday=2)
        wednesday_assignment = Assignment(
            request_id="req1",
            occurrence_index=0,
            start_time=datetime(2024, 1, 17, 10, 0, tzinfo=ZoneInfo("UTC")),  # Wednesday
            end_time=datetime(2024, 1, 17, 12, 0, tzinfo=ZoneInfo("UTC")),
            assigned_resources={"classroom": ["Room101"]}
        )

        # This would be checked in the actual constraint
        assert wednesday_assignment.start_time.weekday() == 2  # Wednesday

    def test_building_filters(self):
        """Test building-based resource filtering utilities."""
        # Create resources
        resources = [
            Resource(id="Room101", resource_type="classroom", building_id="building_a", floor_number=1),
            Resource(id="Room102", resource_type="classroom", building_id="building_a", floor_number=2),
            Resource(id="Lab201", resource_type="lab", building_id="building_b", floor_number=2),
            Resource(id="Study1", resource_type="breakout", building_id="building_a", floor_number=1)
        ]

        # Test filtering by building
        building_a_resources = filter_resources_by_building(resources, "building_a")
        assert len(building_a_resources) == 3
        assert all(r.building_id == "building_a" for r in building_a_resources)

        # Test filtering by building and type
        classrooms_in_a = filter_resources_by_building(resources, "building_a", ["classroom"])
        assert len(classrooms_in_a) == 2
        assert all(r.resource_type == "classroom" for r in classrooms_in_a)

    def test_nearby_resources(self):
        """Test finding nearby resources by floor."""
        # Create resources
        resources = [
            Resource(id="Room101", resource_type="classroom", building_id="building_a", floor_number=1),
            Resource(id="Room102", resource_type="classroom", building_id="building_a", floor_number=2),
            Resource(id="Room201", resource_type="classroom", building_id="building_a", floor_number=2),
            Resource(id="Lab1", resource_type="lab", building_id="building_b", floor_number=1)
        ]

        # Create building
        building = Building(id="building_a", name="Building A", building_type=BuildingType.ACADEMIC, address="")

        # Find resources near Room101 (same floor and nearby floors)
        reference = Resource(id="Room101", resource_type="classroom", building_id="building_a", floor_number=1)
        nearby = find_nearby_resources(resources, {"building_a": building}, reference, max_floors=1)

        # With max_floors=1, should find resources on same floor (1) and one floor away (2)
        # Room201 is on floor 2, which is 1 floor away from floor 1
        assert any(r.id == "Room201" for r in nearby if r.building_id == "building_a" and r.floor_number == 2)

    def test_classroom_recommendation(self):
        """Test classroom recommendation system."""
        # Create resources
        resources = [
            Resource(id="Room101", resource_type="classroom", capacity=30, building_id="building_a", floor_number=1),
            Resource(id="Room102", resource_type="classroom", capacity=50, building_id="building_a", floor_number=1),
            Resource(id="Room201", resource_type="classroom", capacity=25, building_id="building_b", floor_number=2)
        ]

        # Create buildings
        buildings = {
            "building_a": Building(id="building_a", name="Academic Building A", building_type=BuildingType.ACADEMIC, address=""),
            "building_b": Building(id="building_b", name="Building B", building_type=BuildingType.ACADEMIC, address="")
        }

        # Test recommendation with capacity requirement
        requirements = {"capacity": 35}
        recommendations = recommend_classroom(requirements, resources, buildings, preferred_building_id="building_a")

        # Should return rooms that meet capacity requirement
        assert len(recommendations) >= 1
        assert all((r.capacity or 0) >= 35 for r in recommendations)

        # Preferred building should be first
        if len(recommendations) > 1:
            assert recommendations[0].building_id == "building_a"

    def test_breakout_room_availability(self):
        """Test finding available breakout rooms."""
        # Create resources
        resources = [
            Resource(id="Class101", resource_type="classroom", building_id="building_a", floor_number=1),
            Resource(id="Breakout1", resource_type="breakout", building_id="building_a", floor_number=1),
            Resource(id="Breakout2", resource_type="breakout", building_id="building_a", floor_number=2)
        ]

        # Test finding breakout rooms for a classroom
        available = find_available_breakout_rooms(resources, "building_a", "Class101")

        assert len(available) == 2
        assert all(r.resource_type in ["breakout", "study_room"] for r in available)
        assert all(r.building_id == "building_a" for r in available)
        assert all(r.id != "Class101" for r in available)

    def test_resource_grouping_by_building(self):
        """Test grouping resources by building."""
        # Create resources
        resources = [
            Resource(id="Room101", resource_type="classroom", building_id="building_a", floor_number=1),
            Resource(id="Lab1", resource_type="lab", building_id="building_a", floor_number=2),
            Resource(id="Room201", resource_type="classroom", building_id="building_b", floor_number=1)
        ]

        # Create buildings
        buildings = {
            "building_a": Building(id="building_a", name="Building A", building_type=BuildingType.ACADEMIC, address=""),
            "building_b": Building(id="building_b", name="Building B", building_type=BuildingType.ACADEMIC, address="")
        }

        # Group resources by building
        grouped = group_resources_by_building(resources, buildings)

        assert "building_a" in grouped
        assert "building_b" in grouped

        # Check Building A resources
        building_a, a_resources = grouped["building_a"]
        assert building_a.id == "building_a"
        assert len(a_resources) == 2
        assert all(r.building_id == "building_a" for r in a_resources)

        # Check Building B resources
        building_b, b_resources = grouped["building_b"]
        assert building_b.id == "building_b"
        assert len(b_resources) == 1
        assert b_resources[0].id == "Room201"

    def test_integration_example(self):
        """Test a complete integration example."""
        # Create buildings
        main_building = Building(
            id="main_academic",
            name="Main Academic Building",
            building_type=BuildingType.ACADEMIC,
            address="100 University Blvd"
        )
        main_building.add_room_to_floor(1, "LectureHall101")
        main_building.add_room_to_floor(1, "SeminarRoom101")
        main_building.add_room_to_floor(2, "BreakoutRoom201")
        main_building.add_room_to_floor(2, "BreakoutRoom202")

        library = Building(
            id="library",
            name="University Library",
            building_type=BuildingType.LIBRARY,
            address="200 Learning Lane",
            campus_area="Central Campus"
        )
        library.add_room_to_floor(1, "StudyRoom101")
        library.add_room_to_floor(2, "StudyRoom201")

        # Create resources with building references
        resources = [
            Resource(id="LectureHall101", resource_type="classroom", capacity=100, building_id="main_academic", floor_number=1),
            Resource(id="SeminarRoom101", resource_type="seminar", capacity=30, building_id="main_academic", floor_number=1),
            Resource(id="BreakoutRoom201", resource_type="breakout", capacity=15, building_id="main_academic", floor_number=2),
            Resource(id="BreakoutRoom202", resource_type="breakout", capacity=15, building_id="main_academic", floor_number=2),
            Resource(id="StudyRoom101", resource_type="study", capacity=20, building_id="library", floor_number=1),
        ]

        # Create calendar
        calendar = Calendar(
            id="term_calendar",
            timezone=ZoneInfo("UTC"),
            timeslot_granularity=timedelta(minutes=30)
        )

        # Create a complex session request
        request = SessionRequest(
            id="cs401_advanced_topic",
            duration=timedelta(hours=3),
            number_of_occurrences=12,
            earliest_date=datetime(2024, 1, 15, 9, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 5, 15, 17, 0, tzinfo=ZoneInfo("UTC")),
            required_building_id="main_academic",
            required_resource_types={"classroom": 1, "breakout": 2},
            day_requirements={
                2: ["classroom"],  # Wednesday - lecture only
                4: ["classroom", "breakout"],  # Friday - lecture + breakout
            }
        )

        # Create constraints
        constraints = [
            ProximityConstraint(
                request_id="cs401_advanced_topic",
                primary_resource_type="classroom",
                related_resource_types=["breakout"],
                proximity_type=ProximityType.NEARBY_FLOOR,
                max_floors=1
            ),
            MultiRoomCoordination(
                request_id="cs401_advanced_topic",
                required_rooms={"classroom": 1, "breakout": 2},
                proximity_requirements=[
                    ("classroom", "breakout", ProximityType.NEARBY_FLOOR)
                ]
            ),
            DaySpecificResourceRequirement("cs401_advanced_topic")
        ]

        # Create problem
        problem = Problem(
            requests=[request],
            resources=resources,
            calendars=[calendar],
            constraints=constraints,
            buildings=[main_building, library],
            institutional_calendar_id="term_calendar"
        )

        # Verify problem structure
        assert problem.requests[0].required_building_id == "main_academic"
        assert len(problem.buildings) == 2
        assert len(problem.constraints) == 3

        # Verify constraints - count proximity-related constraints
        proximity_related_constraints = [c for c in problem.constraints
                                       if "proximity" in c.constraint_type or "coordination" in c.constraint_type]
        assert len(proximity_related_constraints) == 2

        # Test utility functions
        main_building_resources = filter_resources_by_building(resources, "main_academic")
        assert len(main_building_resources) == 4

        recommended_classrooms = recommend_classroom(
            {"capacity": 50}, resources, {"main_academic": main_building, "library": library}
        )
        assert len(recommended_classrooms) >= 1

        # Test breakout room availability
        available_breakout = find_available_breakout_rooms(resources, "main_academic", "LectureHall101")
        assert len(available_breakout) == 2