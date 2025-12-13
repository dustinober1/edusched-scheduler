"""Resource domain model."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from enum import Enum


class ResourceStatus(Enum):
    """Resource availability status."""
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"
    OUT_OF_SERVICE = "out_of_service"
    RESERVED = "reserved"


class RoomType(Enum):
    """Specific room types with special requirements."""
    CLASSROOM_STANDARD = "classroom_standard"
    CLASSROOM_TIER1 = "classroom_tier1"  # Tech-enabled
    CLASSROOM_TIER2 = "classroom_tier2"  # Basic tech
    LECTURE_HALL = "lecture_hall"
    SEMINAR_ROOM = "seminar_room"
    COMPUTER_LAB = "computer_lab"
    SCIENCE_LAB = "science_lab"
    ENGINEERING_LAB = "engineering_lab"
    ART_STUDIO = "art_studio"
    MUSIC_ROOM = "music_room"
    DANCE_STUDIO = "dance_studio"
    CLINICAL_ROOM = "clinical_room"
    SIMULATION_LAB = "simulation_lab"
    CONFERENCE_ROOM = "conference_room"
    STUDY_ROOM = "study_room"
    TESTING_CENTER = "testing_center"


@dataclass
class Equipment:
    """Equipment associated with a resource."""
    id: str
    name: str
    type: str  # projector, computer, lab_equipment, etc.
    quantity: int
    requires_setup: bool = False
    setup_time_minutes: int = 0
    maintenance_schedule: List[Dict[str, datetime]] = field(default_factory=list)


@dataclass
class MaintenanceWindow:
    """Scheduled maintenance window for a resource."""
    start_time: datetime
    end_time: datetime
    reason: str
    affects_availability: bool = True
    recurring: bool = False
    recurring_pattern: Optional[str] = None  # "weekly", "monthly"


@dataclass
class Resource:
    """Represents a bookable resource (instructor, room, campus, online slot, etc.)."""

    id: str
    resource_type: str
    room_type: Optional[RoomType] = None  # Specific room type if applicable
    concurrency_capacity: int = 1
    attributes: Dict[str, Any] = field(default_factory=dict)
    availability_calendar_id: Optional[str] = None
    building_id: Optional[str] = None  # Reference to building if applicable
    floor_number: Optional[int] = None   # Floor within the building
    capacity: Optional[int] = None        # Physical capacity (seats, etc.)

    # Advanced room features
    equipment: List[Equipment] = field(default_factory=list)
    compatible_course_types: Set[str] = field(default_factory=set)
    restricted_departments: Set[str] = field(default_factory=set)
    authorized_users: Set[str] = field(default_factory=set)

    # Accessibility features
    wheelchair_accessible: bool = False
    has_elevator_access: bool = False
    has_assistive_technology: bool = False
    has_adjustable_furniture: bool = False

    # Technical features
    has_internet: bool = True
    has_projector: bool = False
    has_smart_board: bool = False
    has_microphone: bool = False
    has_video_conference: bool = False
    has_recording_equipment: bool = False
    power_outlets_per_seat: int = 0

    # Environmental features
    has_windows: bool = True
    has_air_conditioning: bool = True
    has_natural_light: bool = False
    noise_level: str = "low"  # low, medium, high
    temperature_control: bool = True

    # Scheduling constraints
    minimum_booking_duration: int = 30  # minutes
    maximum_booking_duration: int = 480  # minutes (8 hours)
    requires_approval: bool = False
    booking_lead_time: int = 0  # days in advance

    # Maintenance and status
    status: ResourceStatus = ResourceStatus.AVAILABLE
    maintenance_windows: List[MaintenanceWindow] = field(default_factory=list)
    last_maintenance: Optional[datetime] = None
    next_inspection: Optional[datetime] = None

    # Cost and billing
    hourly_rate: Optional[float] = None
    requires_payment: bool = False
    billing_department: Optional[str] = None

    # Room configuration
    layout_configurable: bool = False
    max_table_capacity: Optional[int] = None
    has_moveable_furniture: bool = False
    has_podium: bool = False

    def is_available(self, start_time: datetime, end_time: datetime) -> Tuple[bool, str]:
        """
        Check if resource is available during the specified time.

        Returns:
            Tuple of (is_available, reason_if_not)
        """
        # Check resource status
        if self.status != ResourceStatus.AVAILABLE:
            return False, f"Resource status is {self.status.value}"

        # Check maintenance windows
        for maintenance in self.maintenance_windows:
            if maintenance.affects_availability:
                if (start_time < maintenance.end_time and end_time > maintenance.start_time):
                    return False, f"Maintenance scheduled: {maintenance.reason}"

        # Check booking duration constraints
        duration_minutes = (end_time - start_time).total_seconds() / 60
        if duration_minutes < self.minimum_booking_duration:
            return False, f"Minimum duration is {self.minimum_booking_duration} minutes"
        if duration_minutes > self.maximum_booking_duration:
            return False, f"Maximum duration is {self.maximum_booking_duration} minutes"

        return True, "Available"

    def is_compatible_with_course(self, course_type: str, department_id: str) -> bool:
        """
        Check if resource is compatible with a course type and department.

        Args:
            course_type: Type of course (lecture, lab, seminar, etc.)
            department_id: Department offering the course

        Returns:
            True if compatible, False otherwise
        """
        # Check department restrictions
        if self.restricted_departments and department_id not in self.restricted_departments:
            return False

        # Check course type compatibility
        if self.compatible_course_types and course_type not in self.compatible_course_types:
            return False

        # Check room type compatibility
        if self.room_type:
            if course_type == "lab" and self.room_type not in [RoomType.COMPUTER_LAB, RoomType.SCIENCE_LAB,
                                                           RoomType.ENGINEERING_LAB, RoomType.CLINICAL_ROOM]:
                return False
            if course_type == "lecture" and self.room_type == RoomType.STUDY_ROOM:
                return False

        return True

    def meets_accessibility_requirements(self, requirements: Dict[str, bool]) -> bool:
        """
        Check if resource meets accessibility requirements.

        Args:
            requirements: Dictionary of accessibility requirements

        Returns:
            True if all requirements met, False otherwise
        """
        for requirement, needed in requirements.items():
            if needed and not getattr(self, requirement, False):
                return False
        return True

    def has_equipment(self, equipment_type: str) -> bool:
        """Check if resource has specific equipment type."""
        return any(eq.type == equipment_type for eq in self.equipment)

    def get_equipment_count(self, equipment_type: str) -> int:
        """Get count of specific equipment type."""
        return sum(eq.quantity for eq in self.equipment if eq.type == equipment_type)

    def calculate_setup_time(self) -> int:
        """Calculate total setup time in minutes."""
        total_setup = sum(eq.setup_time_minutes for eq in self.equipment if eq.requires_setup)
        return total_setup

    def get_operating_cost(self, duration_minutes: int) -> Optional[float]:
        """Calculate operating cost for given duration."""
        if not self.hourly_rate or not self.requires_payment:
            return None
        return self.hourly_rate * (duration_minutes / 60)

    def requires_approval_for_booking(self, requester_id: str, duration_minutes: int) -> bool:
        """
        Check if booking requires approval.

        Args:
            requester_id: ID of person making booking
            duration_minutes: Duration of booking

        Returns:
            True if approval required
        """
        if self.requires_approval:
            return True

        if self.authorized_users and requester_id not in self.authorized_users:
            return True

        if duration_minutes > 240:  # More than 4 hours
            return True

        return False

    def can_satisfy(self, requirements: Dict[str, Any]) -> bool:
        """
        Check if resource attributes satisfy requirements.

        Args:
            requirements: Dictionary of required attributes

        Returns:
            True if all requirements are satisfied, False otherwise
        """
        # Check basic attributes
        for key, required_value in requirements.items():
            if key in self.attributes:
                if self.attributes[key] != required_value:
                    return False

        # Check capacity requirement
        if "capacity" in requirements:
            if self.capacity is None or self.capacity < requirements["capacity"]:
                return False

        # Check equipment requirements
        if "equipment" in requirements:
            for eq_type, count in requirements["equipment"].items():
                if self.get_equipment_count(eq_type) < count:
                    return False

        # Check accessibility requirements
        if "accessibility" in requirements:
            if not self.meets_accessibility_requirements(requirements["accessibility"]):
                return False

        # Check technical features
        if "technical_features" in requirements:
            for feature, required in requirements["technical_features"].items():
                if required and not getattr(self, f"has_{feature}", False):
                    return False

        return True

    def add_equipment(self, equipment: Equipment) -> None:
        """Add equipment to the resource."""
        # Check if equipment already exists and update quantity
        for existing in self.equipment:
            if existing.id == equipment.id:
                existing.quantity += equipment.quantity
                return
        self.equipment.append(equipment)

    def add_maintenance_window(self, window: MaintenanceWindow) -> None:
        """Add a maintenance window."""
        self.maintenance_windows.append(window)
        # Sort maintenance windows by start time
        self.maintenance_windows.sort(key=lambda w: w.start_time)
