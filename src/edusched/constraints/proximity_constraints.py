"""Constraints for managing resource proximity and building relationships."""

from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from edusched.constraints.base import Constraint, ConstraintContext, Violation

if TYPE_CHECKING:
    from edusched.domain.assignment import Assignment


class ProximityType(Enum):
    """Types of proximity requirements."""

    SAME_BUILDING = "same_building"
    SAME_FLOOR = "same_floor"
    NEARBY_FLOOR = "nearby_floor"  # Within X floors
    ADJACENT_BUILDING = "adjacent_building"
    CAMPUS_AREA = "campus_area"  # Same campus area
    MAX_DISTANCE = "max_distance"


class ProximityConstraint(Constraint):
    """Ensures related resources are within specified proximity."""

    def __init__(
        self,
        request_id: str,
        primary_resource_type: str,
        related_resource_types: List[str],
        proximity_type: ProximityType,
        max_floors: int = 1,  # Used with NEARBY_FLOOR
        max_distance: float = 0.5,  # Used with MAX_DISTANCE (in coordinate units)
        campus_area: Optional[str] = None,  # Used with CAMPUS_AREA
    ):
        self.request_id = request_id
        self.primary_resource_type = primary_resource_type
        self.related_resource_types = related_resource_types
        self.proximity_type = proximity_type
        self.max_floors = max_floors
        self.max_distance = max_distance
        self.campus_area = campus_area

    def check(
        self,
        assignment: "Assignment",
        solution: List["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if related resources meet proximity requirements."""
        if assignment.request_id != self.request_id:
            return None

        # Get the primary resource for this assignment
        primary_resources = self._get_resources_by_type(
            assignment.assigned_resources, self.primary_resource_type
        )
        if not primary_resources:
            return None

        primary_resource_id = primary_resources[0]
        primary_resource = context.resource_lookup.get(primary_resource_id)
        if not primary_resource:
            return None

        # Check all related assignments for the same request
        related_assignments = [
            a
            for a in solution
            if a.request_id == self.request_id and a.occurrence_index == assignment.occurrence_index
        ]

        for related_assignment in related_assignments:
            for related_type in self.related_resource_types:
                related_resources = self._get_resources_by_type(
                    related_assignment.assigned_resources, related_type
                )
                for related_resource_id in related_resources:
                    related_resource = context.resource_lookup.get(related_resource_id)
                    if related_resource:
                        violation = self._check_proximity(
                            primary_resource, related_resource, context.building_lookup
                        )
                        if violation:
                            return violation

        return None

    def _get_resources_by_type(self, assigned_resources: dict, resource_type: str) -> List[str]:
        """Get resource IDs of a specific type from assigned resources."""
        resources = []
        for rtype, resource_ids in assigned_resources.items():
            if rtype == resource_type:
                resources.extend(resource_ids)
        return resources

    def _check_proximity(
        self, primary_resource, related_resource, building_lookup: dict
    ) -> Optional[Violation]:
        """Check proximity between two resources."""
        # If either resource doesn't have a building, no proximity check needed
        if not primary_resource.building_id or not related_resource.building_id:
            return None

        # Get buildings
        primary_building = building_lookup.get(primary_resource.building_id)
        related_building = building_lookup.get(related_resource.building_id)

        if not primary_building or not related_building:
            return None

        # Check based on proximity type
        if self.proximity_type == ProximityType.SAME_BUILDING:
            if primary_building.id != related_building.id:
                return Violation(
                    constraint_type=self.constraint_type,
                    affected_request_id=self.request_id,
                    affected_resource_id=related_resource.id,
                    message=f"Resource {related_resource.id} must be in same building as {primary_resource.id}",
                )

        elif self.proximity_type == ProximityType.SAME_FLOOR:
            if (
                primary_building.id != related_building.id
                or primary_resource.floor_number != related_resource.floor_number
            ):
                return Violation(
                    constraint_type=self.constraint_type,
                    affected_request_id=self.request_id,
                    affected_resource_id=related_resource.id,
                    message=f"Resource {related_resource.id} must be on same floor as {primary_resource.id}",
                )

        elif self.proximity_type == ProximityType.NEARBY_FLOOR:
            floors_between = primary_building.get_floors_between(
                primary_resource.floor_number or 0, related_resource.floor_number or 0
            )
            if floors_between > self.max_floors:
                return Violation(
                    constraint_type=self.constraint_type,
                    affected_request_id=self.request_id,
                    affected_resource_id=related_resource.id,
                    message=f"Resource {related_resource.id} must be within {self.max_floors} floors of {primary_resource.id}",
                )

        elif self.proximity_type == ProximityType.MAX_DISTANCE:
            distance = primary_building.calculate_distance_to(related_building)
            if distance and distance > self.max_distance:
                return Violation(
                    constraint_type=self.constraint_type,
                    affected_request_id=self.request_id,
                    affected_resource_id=related_resource.id,
                    message=f"Resource {related_resource.id} is too far from {primary_resource.id} ({distance:.2f} > {self.max_distance})",
                )

        elif self.proximity_type == ProximityType.CAMPUS_AREA:
            if (
                primary_building.campus_area != related_building.campus_area
                or primary_building.campus_area != self.campus_area
            ):
                return Violation(
                    constraint_type=self.constraint_type,
                    affected_request_id=self.request_id,
                    affected_resource_id=related_resource.id,
                    message=f"Resource {related_resource.id} must be in {self.campus_area or 'same campus area'} as {primary_resource.id}",
                )

        return None

    def explain(self, violation: Violation) -> str:
        """Generate human-readable explanation."""
        return violation.message

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return f"hard.proximity.{self.proximity_type.value}"


class MultiRoomCoordination(Constraint):
    """Ensures multiple rooms for the same session are compatible."""

    def __init__(
        self,
        request_id: str,
        required_rooms: Dict[str, List[str]],  # e.g., {"classroom": 1, "breakout": 2}
        proximity_requirements: Optional[
            List[Tuple[str, str, ProximityType]]
        ] = None,  # [("classroom", "breakout", ProximityType.SAME_FLOOR)]
    ):
        self.request_id = request_id
        self.required_rooms = required_rooms
        self.proximity_requirements = proximity_requirements or []

    def check(
        self,
        assignment: "Assignment",
        solution: List["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if multi-room assignment is valid."""
        if assignment.request_id != self.request_id:
            return None

        # Collect all room assignments for this request occurrence
        all_room_assignments = [
            a
            for a in solution
            if a.request_id == self.request_id and a.occurrence_index == assignment.occurrence_index
        ]

        # Check we have the right number of each room type
        room_counts = {}
        for room_assignment in all_room_assignments:
            for room_type, room_ids in room_assignment.assigned_resources.items():
                if room_type in self.required_rooms:
                    room_counts[room_type] = room_counts.get(room_type, 0) + len(room_ids)

        for room_type, required_count in self.required_rooms.items():
            actual_count = room_counts.get(room_type, 0)
            if actual_count < required_count:
                return Violation(
                    constraint_type=self.constraint_type,
                    affected_request_id=self.request_id,
                    message=f"Need {required_count} {room_type}(s), only have {actual_count}",
                )

        # Check proximity requirements between room types
        for room_type1, room_type2, proximity_type in self.proximity_requirements:
            rooms1 = self._get_rooms_of_type(all_room_assignments, room_type1)
            rooms2 = self._get_rooms_of_type(all_room_assignments, room_type2)

            for room1_id in rooms1:
                for room2_id in rooms2:
                    room1 = context.resource_lookup.get(room1_id)
                    room2 = context.resource_lookup.get(room2_id)
                    if room1 and room2:
                        # Create a temporary proximity constraint to check
                        temp_constraint = ProximityConstraint(
                            self.request_id, room_type1, [room_type2], proximity_type
                        )
                        violation = temp_constraint._check_proximity(
                            room1, room2, context.building_lookup
                        )
                        if violation:
                            violation.message = f"Multi-room: {violation.message}"
                            return violation

        return None

    def _get_rooms_of_type(self, assignments: List["Assignment"], room_type: str) -> List[str]:
        """Get all room IDs of a specific type from assignments."""
        rooms = []
        for assignment in assignments:
            for rtype, room_ids in assignment.assigned_resources.items():
                if rtype == room_type:
                    rooms.extend(room_ids)
        return rooms

    def explain(self, violation: Violation) -> str:
        """Generate human-readable explanation."""
        return violation.message

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.multi_room_coordination"
