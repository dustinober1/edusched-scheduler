"""Building domain model for managing physical locations."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class BuildingType(Enum):
    """Types of buildings on campus."""
    ACADEMIC = "academic"
    LIBRARY = "library"
    LAB = "lab"
    DORMITORY = "dormitory"
    ADMINISTRATIVE = "administrative"
    RECREATION = "recreation"
    DINING = "dining"
    OTHER = "other"


@dataclass
class Floor:
    """Represents a floor in a building with rooms."""
    number: int  # Floor number (0 for ground floor, -1 for basement, etc.)
    rooms: List[str] = field(default_factory=list)  # List of room IDs on this floor

    def add_room(self, room_id: str) -> None:
        """Add a room to this floor."""
        if room_id not in self.rooms:
            self.rooms.append(room_id)

    def remove_room(self, room_id: str) -> None:
        """Remove a room from this floor."""
        if room_id in self.rooms:
            self.rooms.remove(room_id)

    def get_room_count(self) -> int:
        """Get the number of rooms on this floor."""
        return len(self.rooms)


@dataclass
class Building:
    """Represents a physical building with floors and location information."""

    id: str
    name: str
    building_type: BuildingType
    address: str
    coordinates: Optional[Tuple[float, float]] = None  # (latitude, longitude)
    campus_area: Optional[str] = None  # e.g., "North Campus", "West Campus"
    floors: Dict[int, Floor] = field(default_factory=dict)
    amenities: List[str] = field(default_factory=list)  # e.g., ["elevator", "ramp", "parking"]

    def add_floor(self, floor_number: int) -> Floor:
        """Add a floor to the building."""
        if floor_number not in self.floors:
            self.floors[floor_number] = Floor(number=floor_number)
        return self.floors[floor_number]

    def add_room_to_floor(self, floor_number: int, room_id: str) -> None:
        """Add a room to a specific floor."""
        floor = self.add_floor(floor_number)
        floor.add_room(room_id)

    def get_rooms_on_floor(self, floor_number: int) -> List[str]:
        """Get all rooms on a specific floor."""
        if floor_number in self.floors:
            return self.floors[floor_number].rooms.copy()
        return []

    def get_all_rooms(self) -> List[str]:
        """Get all rooms in the building."""
        all_rooms = []
        for floor in self.floors.values():
            all_rooms.extend(floor.rooms)
        return all_rooms

    def get_room_floor(self, room_id: str) -> Optional[int]:
        """Get the floor number for a specific room."""
        for floor_number, floor in self.floors.items():
            if room_id in floor.rooms:
                return floor_number
        return None

    def calculate_distance_to(self, other_building: 'Building') -> Optional[float]:
        """Calculate distance to another building using coordinates."""
        if not self.coordinates or not other_building.coordinates:
            return None

        lat1, lon1 = self.coordinates
        lat2, lon2 = other_building.coordinates

        # Simple Euclidean distance (for demonstration)
        # In practice, you might use Haversine formula for Earth coordinates
        return ((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2) ** 0.5

    def is_same_building(self, other_building: 'Building') -> bool:
        """Check if this is the same building."""
        return self.id == other_building.id

    def get_floors_between(self, floor1: int, floor2: int) -> int:
        """Get the number of floors between two floors."""
        return abs(floor2 - floor1)

    def has_amenity(self, amenity: str) -> bool:
        """Check if the building has a specific amenity."""
        return amenity.lower() in [a.lower() for a in self.amenities]