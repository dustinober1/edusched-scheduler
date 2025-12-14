"""Resource domain model."""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


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
    BREAKOUT_ROOM = "breakout_room"
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
class BlackoutPeriod:
    """Blackout period when a resource is completely unavailable."""

    start_date: date
    end_date: date
    reason: str
    affects_all_rooms: bool = False  # If True, applies to all rooms in building

    # Optional constraints
    affected_room_types: List[RoomType] = field(default_factory=list)
    affected_resources: List[str] = field(default_factory=list)  # Specific resource IDs
    exception_dates: List[date] = field(default_factory=list)  # Dates when blackout doesn't apply

    def affects_date(self, check_date: date) -> bool:
        """Check if a date is affected by this blackout period."""
        if check_date in self.exception_dates:
            return False
        return self.start_date <= check_date <= self.end_date

    def affects_resource(self, resource_id: str, room_type: Optional[RoomType] = None) -> bool:
        """Check if a specific resource is affected by this blackout."""
        if self.affects_all_rooms:
            return True

        if resource_id in self.affected_resources:
            return True

        if room_type and room_type in self.affected_room_types:
            return True

        return False


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
    floor_number: Optional[int] = None  # Floor within the building
    capacity: Optional[int] = None  # Physical capacity (seats, etc.)

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

    # Blackout periods (building-wide or room-specific)
    blackout_periods: List[BlackoutPeriod] = field(default_factory=list)
    building_blackouts: List[BlackoutPeriod] = field(
        default_factory=list
    )  # Inherited from building

    # Flexible room usage
    can_be_used_as: Set[RoomType] = field(
        default_factory=set
    )  # Alternative room types this room can serve as
    fallback_priority: Dict[RoomType, int] = field(
        default_factory=dict
    )  # Priority when used as fallback (1=highest)
    min_capacity_for_alt_use: Optional[Dict[RoomType, int]] = (
        None  # Min capacity needed for alternative use
    )
    requires_conversion: Set[RoomType] = field(
        default_factory=set
    )  # Room types that need setup changes
    conversion_time_minutes: Dict[RoomType, int] = field(
        default_factory=dict
    )  # Time needed to convert

    # Room usage tracking
    primary_usage_count: Dict[str, int] = field(
        default_factory=dict
    )  # Count of times used as primary type
    fallback_usage_count: Dict[str, int] = field(
        default_factory=dict
    )  # Count of times used as fallback

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

        # Check blackout periods first (they override everything)
        check_date = start_time.date()

        # Check room-specific blackouts
        for blackout in self.blackout_periods:
            if blackout.affects_date(check_date) and blackout.affects_resource(
                self.id, self.room_type
            ):
                return False, f"Room blackout: {blackout.reason}"

        # Check building-wide blackouts
        for blackout in self.building_blackouts:
            if blackout.affects_date(check_date) and blackout.affects_resource(
                self.id, self.room_type
            ):
                return False, f"Building blackout: {blackout.reason}"

        # Check maintenance windows
        for maintenance in self.maintenance_windows:
            if maintenance.affects_availability:
                if start_time < maintenance.end_time and end_time > maintenance.start_time:
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
            if course_type == "lab" and self.room_type not in [
                RoomType.COMPUTER_LAB,
                RoomType.SCIENCE_LAB,
                RoomType.ENGINEERING_LAB,
                RoomType.CLINICAL_ROOM,
            ]:
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
        # Check basic attributes first
        for key, required_value in requirements.items():
            # Special handling for dict-typed requirements in specific keys
            if key == "capacity" and isinstance(required_value, (int, float)):
                # Check capacity as a numeric comparison
                resource_capacity = (
                    self.capacity if self.capacity is not None else self.attributes.get("capacity")
                )
                if resource_capacity is None or resource_capacity < required_value:
                    return False
            elif key == "equipment" and isinstance(required_value, dict):
                # Check equipment as a dict of type: count
                for eq_type, count in required_value.items():
                    if isinstance(count, (int, float)) and self.get_equipment_count(eq_type) < count:
                        return False
            elif key == "accessibility" and isinstance(required_value, dict):
                # Check accessibility requirements
                if not self.meets_accessibility_requirements(required_value):
                    return False
            elif key == "technical_features" and isinstance(required_value, dict):
                # Check technical features
                for feature, required in required_value.items():
                    if required and not getattr(self, f"has_{feature}", False):
                        return False
            else:
                # Regular attribute matching
                if key not in self.attributes:
                    return False
                if self.attributes[key] != required_value:
                    return False

        return True

    def validate(self) -> List["ValidationError"]:  # type: ignore
        """
        Validate resource parameters.

        Returns:
            List of validation errors (empty if valid)
        """
        from edusched.errors import ValidationError

        errors: List[ValidationError] = []

        if not self.id:
            errors.append(
                ValidationError(
                    field="id", expected_format="non-empty string", actual_value=self.id
                )
            )

        valid_types = ["room", "instructor", "equipment", "campus", "online_slot"]
        if self.resource_type not in valid_types:
            errors.append(
                ValidationError(
                    field="resource_type",
                    expected_format=f"one of {valid_types}",
                    actual_value=self.resource_type,
                )
            )

        if self.capacity is not None and self.capacity < 0:
            errors.append(
                ValidationError(
                    field="capacity",
                    expected_format="non-negative integer",
                    actual_value=self.capacity,
                )
            )

        # Validate attribute types
        valid_attr_types = (str, int, list, dict, bool, type(None))
        # Note: float is intentionally excluded based on test requirements
        for key, value in self.attributes.items():
            if not isinstance(value, valid_attr_types):
                errors.append(
                    ValidationError(
                        field="attributes",
                        expected_format=f"valid types {valid_attr_types} for key '{key}'",
                        actual_value=type(value),
                    )
                )

        return errors

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

    def add_blackout_period(self, blackout: BlackoutPeriod) -> None:
        """Add a blackout period for this resource."""
        self.blackout_periods.append(blackout)
        # Sort blackout periods by start date
        self.blackout_periods.sort(key=lambda b: b.start_date)

    def remove_blackout_period(self, blackout_start: date) -> bool:
        """Remove a blackout period by start date."""
        for i, blackout in enumerate(self.blackout_periods):
            if blackout.start_date == blackout_start:
                del self.blackout_periods[i]
                return True
        return False

    def get_blackout_periods_in_range(
        self, start_date: date, end_date: date
    ) -> List[BlackoutPeriod]:
        """Get all blackout periods within a date range."""
        return [
            blackout
            for blackout in self.blackout_periods
            if blackout.start_date <= end_date and blackout.end_date >= start_date
        ]

    def is_date_blacked_out(self, check_date: date) -> Tuple[bool, Optional[str]]:
        """
        Check if a specific date is blacked out.

        Returns:
            Tuple of (is_blacked_out, reason)
        """
        # Check room-specific blackouts
        for blackout in self.blackout_periods:
            if blackout.affects_date(check_date) and blackout.affects_resource(
                self.id, self.room_type
            ):
                return True, blackout.reason

        # Check building-wide blackouts
        for blackout in self.building_blackouts:
            if blackout.affects_date(check_date) and blackout.affects_resource(
                self.id, self.room_type
            ):
                return True, blackout.reason

        return False, None

    def can_be_used_as_type(self, target_type: RoomType) -> bool:
        """
        Check if this room can be used as the specified room type.

        Args:
            target_type: The room type to check

        Returns:
            True if the room can serve as the target type
        """
        # If it's already the target type, it can be used
        if self.room_type == target_type:
            return True

        # Check if it's in the flexible usage list
        return target_type in self.can_be_used_as

    def get_fallback_priority(self, target_type: RoomType) -> int:
        """
        Get the priority when this room is used as a fallback for the target type.

        Args:
            target_type: The room type it's being used for

        Returns:
            Priority value (1=highest, higher numbers=lower priority)
        """
        return self.fallback_priority.get(target_type, 999)  # Default to very low priority

    def meets_capacity_for_type(self, target_type: RoomType, enrollment: int) -> bool:
        """
        Check if the room meets minimum capacity requirements for the target type.

        Args:
            target_type: The room type it would be used as
            enrollment: Number of students enrolled

        Returns:
            True if capacity is adequate
        """
        if not self.capacity:
            return True

        # Must meet enrollment requirement
        if self.capacity < enrollment:
            return False

        # If this is the primary room type, we're done
        if target_type == self.room_type:
            return True

        # If there's a minimum capacity for this alternative use, check it
        if self.min_capacity_for_alt_use and target_type in self.min_capacity_for_alt_use:
            min_capacity = self.min_capacity_for_alt_use[target_type]
            return enrollment >= min_capacity  # Enrollment must meet minimum requirement

        return True

    def needs_conversion_for_type(self, target_type: RoomType) -> bool:
        """
        Check if the room needs conversion to be used as the target type.

        Args:
            target_type: The room type it would be used as

        Returns:
            True if conversion/setup is needed
        """
        return target_type in self.requires_conversion

    def get_conversion_time(self, target_type: RoomType) -> int:
        """
        Get time needed to convert the room for the target type.

        Args:
            target_type: The room type it would be used as

        Returns:
            Time in minutes needed for conversion
        """
        return self.conversion_time_minutes.get(target_type, 0)

    def record_usage(
        self, used_as_type: Optional[RoomType] = None, is_fallback: bool = False
    ) -> None:
        """
        Record usage of the room for analytics.

        Args:
            used_as_type: The room type it was used as (None for primary type)
            is_fallback: Whether this was a fallback usage
        """
        if used_as_type is None:
            used_as_type = self.room_type

        type_name = used_as_type.value

        if is_fallback:
            self.fallback_usage_count[type_name] = self.fallback_usage_count.get(type_name, 0) + 1
        else:
            self.primary_usage_count[type_name] = self.primary_usage_count.get(type_name, 0) + 1

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics for this room.

        Returns:
            Dictionary with usage metrics
        """
        total_primary = sum(self.primary_usage_count.values())
        total_fallback = sum(self.fallback_usage_count.values())

        return {
            "total_uses": total_primary + total_fallback,
            "primary_uses": total_primary,
            "fallback_uses": total_fallback,
            "primary_by_type": self.primary_usage_count.copy(),
            "fallback_by_type": self.fallback_usage_count.copy(),
            "fallback_percentage": (total_fallback / max(total_primary + total_fallback, 1)) * 100,
        }

    def add_fallback_capability(
        self,
        fallback_type: RoomType,
        priority: int = 10,
        min_capacity: Optional[int] = None,
        conversion_time: Optional[int] = None,
        requires_conversion: bool = False,
    ) -> None:
        """
        Add capability for this room to be used as a fallback.

        Args:
            fallback_type: The room type it can serve as
            priority: Priority level (1=highest)
            min_capacity: Minimum capacity required for this use
            conversion_time: Time in minutes needed for conversion
            requires_conversion: Whether physical conversion is needed
        """
        self.can_be_used_as.add(fallback_type)
        self.fallback_priority[fallback_type] = priority

        if requires_conversion:
            self.requires_conversion.add(fallback_type)

        if conversion_time is not None:
            self.conversion_time_minutes[fallback_type] = conversion_time

        if min_capacity is not None:
            if self.min_capacity_for_alt_use is None:
                self.min_capacity_for_alt_use = {}
            self.min_capacity_for_alt_use[fallback_type] = min_capacity
