"""Campus domain models for multi-campus scheduling.

Handles multiple campus locations, transportation between campuses,
campus-specific resources, and cross-campus course scheduling.
"""

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Set, Tuple

from edusched.domain.base import BaseEntity


@dataclass
class Campus(BaseEntity):
    """Represents a campus location."""

    name: str
    address: str
    city: str
    state: str
    country: str
    postal_code: str
    timezone: str  # IANA timezone identifier

    # Campus characteristics
    total_area_sqft: float = 0.0
    student_capacity: int = 0
    faculty_count: int = 0
    is_primary_campus: bool = False
    is_active: bool = True

    # Operating hours
    opening_time: time = time(7, 0)  # 7:00 AM
    closing_time: time = time(23, 0)  # 11:00 PM

    # Special facilities
    has_library: bool = True
    has_dining: bool = True
    has_parking: bool = True
    has_dormitories: bool = False

    # Campus contacts
    campus_director: str = ""
    main_phone: str = ""
    emergency_contact: str = ""

    # Coordinates for distance calculations
    latitude: Optional[float] = None
    longitude: Optional[float] = None


@dataclass
class Building(BaseEntity):
    """Represents a building on a campus."""

    campus_id: str
    name: str
    building_code: str  # e.g., "SCI" for Science Building
    building_type: str  # academic, administrative, athletic, residential, etc.

    # Physical characteristics
    floor_count: int = 1
    total_square_feet: float = 0.0
    year_built: int = 2024
    accessibility_features: List[str] = field(default_factory=list)

    # Operating constraints
    opening_time: Optional[time] = None  # None = use campus hours
    closing_time: Optional[time] = None
    restricted_access: bool = False
    access_requirements: List[str] = field(default_factory=list)

    # Special features
    has_elevators: bool = False
    has_loading_dock: bool = False
    has_parking: bool = False
    parking_spaces: int = 0

    # Emergency and maintenance
    evacuation_plan: str = ""
    last_inspection: Optional[datetime] = None
    next_inspection_due: Optional[datetime] = None


@dataclass
class TransportationRoute(BaseEntity):
    """Transportation connection between campuses."""

    from_campus_id: str
    to_campus_id: str
    transport_type: str  # shuttle, bus, train, walking, driving

    # Schedule information
    departure_schedule: List[time] = field(default_factory=list)  # Regular departure times
    return_schedule: List[time] = field(default_factory=list)
    operating_days: List[int] = field(default_factory=list)  # 0=Monday, 6=Sunday
    frequency_minutes: int = 60  # Minutes between departures

    # Duration and capacity
    travel_duration_minutes: int = 30
    capacity_per_trip: int = 50
    advance_booking_minutes: int = 0  # How far in advance to book

    # Cost and constraints
    cost_per_trip: float = 0.0
    requires_booking: bool = False
    weather_sensitive: bool = False

    # Physical route
    route_name: str = ""
    route_description: str = ""
    stops: List[str] = field(default_factory=list)  # Intermediate stops


@dataclass
class CampusResource(BaseEntity):
    """Resource available at a specific campus."""

    campus_id: str
    building_id: Optional[str] = None
    resource_type: str  # classroom, lab, library, gym, etc.
    name: str
    capacity: int = 0

    # Resource characteristics
    area_square_feet: float = 0.0
    has_projector: bool = False
    has_computers: bool = False
    has_internet: bool = True
    has_air_conditioning: bool = True

    # Availability constraints
    campus_only: bool = True  # Only available to campus-affiliated groups
    booking_priority: List[str] = field(default_factory=list)  # Dept priority order
    shared_departments: Set[str] = field(default_factory=set)

    # Special equipment
    equipment_ids: List[str] = field(default_factory=list)
    special_features: List[str] = field(default_factory=list)


@dataclass
class CrossCampusCourse(BaseEntity):
    """Course that spans multiple campuses."""

    course_id: str
    primary_campus_id: str
    secondary_campus_ids: List[str] = field(default_factory=list)

    # Scheduling pattern
    rotation_pattern: str = "alternating"  # alternating, simultaneous, primary_secondary
    rotation_frequency: str = "weekly"  # weekly, monthly, by_topic

    # Transportation requirements
    requires_transportation: bool = True
    transportation_cost_per_student: float = 0.0
    travel_time_buffer_minutes: int = 30

    # Live streaming setup
    requires_streaming: bool = False
    streaming_equipment_ids: List[str] = field(default_factory=list)
    backup_recording: bool = True

    # Faculty requirements
    instructor_travels: bool = True
    remote_instruction_available: bool = False

    # Student preferences
    max_travel_distance_km: float = 50.0
    accommodation_provided: bool = False


@dataclass
class CampusSchedule(BaseEntity):
    """Campus-specific scheduling constraints and preferences."""

    campus_id: str

    # Academic calendar differences
    semester_start: Optional[datetime] = None
    semester_end: Optional[datetime] = None
    spring_break_dates: List[Tuple[datetime, datetime]] = field(default_factory=list)
    reading_days: List[datetime] = field(default_factory=list)

    # Class scheduling preferences
    preferred_class_days: List[int] = field(default_factory=list)  # Days of week
    preferred_time_blocks: List[Tuple[time, time]] = field(default_factory=list)
    break_times: List[Tuple[time, time]] = field(default_factory=list)  # Campus-wide breaks

    # Resource allocation
    department_room_allocations: Dict[str, List[str]] = field(default_factory=dict)
    shared_time_slots: Set[str] = field(
        default_factory=set
    )  # Times when multiple campuses can schedule

    # Special events
    blackout_dates: List[Tuple[datetime, datetime]] = field(default_factory=list)
    special_events: List[Tuple[datetime, str]] = field(default_factory=list)

    # Transportation schedules
    peak_transportation_times: List[Tuple[time, time]] = field(default_factory=list)
    exam_period_transportation: bool = True  # Enhanced during exams


class CampusManager:
    """Manages multiple campus operations and interactions."""

    def __init__(self):
        self.campuses: Dict[str, Campus] = {}
        self.buildings: Dict[str, Building] = {}
        self.routes: Dict[str, TransportationRoute] = {}
        self.resources: Dict[str, CampusResource] = {}
        self.courses: Dict[str, CrossCampusCourse] = {}
        self.schedules: Dict[str, CampusSchedule] = {}

    def add_campus(self, campus: Campus) -> None:
        """Add a campus."""
        self.campuses[campus.id] = campus

    def add_building(self, building: Building) -> None:
        """Add a building."""
        self.buildings[building.id] = building

    def add_transportation_route(self, route: TransportationRoute) -> None:
        """Add a transportation route."""
        self.routes[route.id] = route
        # Store in both directions for easier lookup
        reverse_key = f"{route.to_campus_id}_to_{route.from_campus_id}"
        if reverse_key not in self.routes:
            # Create reverse route entry with same ID
            reverse_route = TransportationRoute(
                id=f"{route.id}_reverse",
                from_campus_id=route.to_campus_id,
                to_campus_id=route.from_campus_id,
                transport_type=route.transport_type,
                travel_duration_minutes=route.travel_duration_minutes,
                capacity_per_trip=route.capacity_per_trip,
                cost_per_trip=route.cost_per_trip,
            )
            self.routes[reverse_key] = reverse_route

    def get_travel_time(self, from_campus_id: str, to_campus_id: str) -> int:
        """Get travel time between two campuses in minutes."""
        route_key = f"{from_campus_id}_to_{to_campus_id}"
        route = self.routes.get(route_key)
        return route.travel_duration_minutes if route else 0

    def get_transportation_options(
        self,
        from_campus_id: str,
        to_campus_id: str,
        departure_time: time,
        day_of_week: int,
    ) -> List[Tuple[time, time, float]]:
        """Get available transportation options (departure, arrival, cost)."""
        route_key = f"{from_campus_id}_to_{to_campus_id}"
        route = self.routes.get(route_key)

        if not route or day_of_week not in route.operating_days:
            return []

        options = []
        for departure in route.departure_schedule:
            if departure >= departure_time:
                arrival = (
                    datetime.combine(datetime.min.date(), departure)
                    + timedelta(minutes=route.travel_duration_minutes)
                ).time()
                options.append((departure, arrival, route.cost_per_trip))

        return options

    def get_campus_buildings(self, campus_id: str) -> List[Building]:
        """Get all buildings on a campus."""
        return [building for building in self.buildings.values() if building.campus_id == campus_id]

    def get_campus_resources(self, campus_id: str) -> List[CampusResource]:
        """Get all resources on a campus."""
        return [resource for resource in self.resources.values() if resource.campus_id == campus_id]

    def find_nearest_campus(
        self,
        latitude: float,
        longitude: float,
        max_distance_km: float = 100.0,
    ) -> Optional[Tuple[str, float]]:
        """Find nearest campus to given coordinates."""
        from math import atan2, cos, radians, sin, sqrt

        nearest_campus = None
        min_distance = float("inf")

        for campus in self.campuses.values():
            if not campus.latitude or not campus.longitude:
                continue

            # Calculate distance using Haversine formula
            lat1, lon1 = radians(campus.latitude), radians(campus.longitude)
            lat2, lon2 = radians(latitude), radians(longitude)

            dlat = lat2 - lat1
            dlon = lon2 - lon1

            a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
            c = 2 * atan2(sqrt(a), sqrt(1 - a))

            distance_km = 6371 * c  # Earth's radius in kilometers

            if distance_km < min_distance and distance_km <= max_distance_km:
                min_distance = distance_km
                nearest_campus = (campus.id, distance_km)

        return nearest_campus

    def calculate_commuting_distance(
        self,
        student_lat: float,
        student_lon: float,
        campus_id: str,
    ) -> float:
        """Calculate commuting distance for a student to a campus."""
        from math import atan2, cos, radians, sin, sqrt

        campus = self.campuses.get(campus_id)
        if not campus or not campus.latitude or not campus.longitude:
            return float("inf")

        # Haversine formula
        lat1, lon1 = radians(student_lat), radians(student_lon)
        lat2, lon2 = radians(campus.latitude), radians(campus.longitude)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return 6371 * c  # Distance in kilometers

    def get_campus_timezones(self) -> Set[str]:
        """Get all unique timezones across campuses."""
        return set(campus.timezone for campus in self.campuses.values())

    def validate_cross_campus_schedule(
        self,
        course: CrossCampusCourse,
        start_time: datetime,
        duration: timedelta,
    ) -> List[str]:
        """Validate if cross-campus course can be scheduled."""
        issues = []

        # Check transportation availability
        if course.requires_transportation:
            for secondary_campus in course.secondary_campus_ids:
                travel_time = self.get_travel_time(course.primary_campus_id, secondary_campus)
                if travel_time == 0:
                    issues.append(
                        f"No transportation available from {course.primary_campus_id} to {secondary_campus}"
                    )

                # Check if travel time fits in schedule
                total_time = duration + timedelta(
                    minutes=travel_time * 2 + course.travel_time_buffer_minutes
                )
                if total_time > timedelta(hours=8):  # Assume 8-hour max day
                    issues.append(
                        f"Insufficient time for cross-campus session to {secondary_campus}"
                    )

        # Check streaming requirements
        if course.requires_streaming:
            primary_campus = self.campuses.get(course.primary_campus_id)
            if primary_campus and not primary_campus.has_internet:
                issues.append("Primary campus lacks internet for streaming")

        # Check instructor travel
        if course.instructor_travels:
            # Would need to check instructor's schedule and constraints
            pass

        return issues

    def suggest_optimal_campus(
        self,
        student_locations: List[Tuple[float, float]],
        department_id: str,
        course_capacity: int,
    ) -> Optional[str]:
        """Suggest optimal campus for a course based on student locations."""
        if not student_locations:
            return None

        campus_scores = {}

        for campus in self.campuses.values():
            if not campus.is_active:
                continue

            # Calculate total travel distance for all students
            total_distance = 0.0
            for lat, lon in student_locations:
                distance = self.calculate_commuting_distance(lat, lon, campus.id)
                total_distance += distance

            # Get campus resources that match capacity
            suitable_resources = [
                r for r in self.get_campus_resources(campus.id) if r.capacity >= course_capacity
            ]

            # Score based on distance and availability
            if suitable_resources:
                avg_distance = total_distance / len(student_locations)
                campus_scores[campus.id] = avg_distance

        if not campus_scores:
            return None

        # Return campus with minimum average distance
        return min(campus_scores, key=campus_scores.get)
