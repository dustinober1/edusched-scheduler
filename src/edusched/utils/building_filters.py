"""Utility functions for filtering and finding resources by building criteria."""

from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from edusched.domain.building import Building
from edusched.domain.resource import Resource


def filter_resources_by_building(
    resources: List[Resource], building_id: str, resource_types: Optional[List[str]] = None
) -> List[Resource]:
    """
    Filter resources by building ID and optionally by resource types.

    Args:
        resources: List of all resources to filter
        building_id: Building ID to filter by
        resource_types: Optional list of resource types to include

    Returns:
        List of resources in the specified building
    """
    filtered = []
    for resource in resources:
        if resource.building_id == building_id:
            if resource_types is None or resource.resource_type in resource_types:
                filtered.append(resource)
    return filtered


def find_nearby_resources(
    resources: List[Resource],
    buildings: Dict[str, Building],
    reference_resource: Resource,
    max_floors: int = 2,
    include_same_floor: bool = True,
) -> List[Resource]:
    """
    Find resources near a reference resource within the same or nearby floors.

    Args:
        resources: List of all resources to search
        buildings: Dictionary of buildings by ID
        reference_resource: The resource to search near
        max_floors: Maximum floor difference
        include_same_floor: Whether to include resources on the same floor

    Returns:
        List of nearby resources
    """
    if not reference_resource.building_id:
        return []

    building = buildings.get(reference_resource.building_id)
    if not building:
        return []

    nearby = []
    reference_floor = reference_resource.floor_number or 0

    for resource in resources:
        # Skip the reference resource itself
        if resource.id == reference_resource.id:
            continue

        # Check if in same building
        if resource.building_id != reference_resource.building_id:
            continue

        # Check floor proximity
        resource_floor = resource.floor_number or 0
        floor_diff = abs(resource_floor - reference_floor)

        if include_same_floor and floor_diff == 0:
            nearby.append(resource)
        elif 0 < floor_diff <= max_floors:
            nearby.append(resource)

    return nearby


def find_resources_in_campus_area(
    resources: List[Resource],
    buildings: Dict[str, Building],
    campus_area: str,
    resource_types: Optional[List[str]] = None,
) -> List[Resource]:
    """
    Find resources in a specific campus area.

    Args:
        resources: List of all resources to search
        buildings: Dictionary of buildings by ID
        campus_area: Campus area to search in
        resource_types: Optional list of resource types to include

    Returns:
        List of resources in the campus area
    """
    area_resources = []

    # Get buildings in the campus area
    area_buildings = {
        building_id
        for building_id, building in buildings.items()
        if building.campus_area == campus_area
    }

    for resource in resources:
        if resource.building_id in area_buildings:
            if resource_types is None or resource.resource_type in resource_types:
                area_resources.append(resource)

    return area_resources


def group_resources_by_building(
    resources: List[Resource], buildings: Dict[str, Building]
) -> Dict[str, Tuple[Building, List[Resource]]]:
    """
    Group resources by their building.

    Returns:
        Dictionary mapping building ID to (Building, [Resources])
    """
    grouped = defaultdict(lambda: (None, []))

    for resource in resources:
        if resource.building_id:
            building = buildings.get(resource.building_id)
            if building:
                grouped[resource.building_id] = (building, grouped[resource.building_id][1])
                grouped[resource.building_id][1].append(resource)

    return dict(grouped)


def find_available_breakout_rooms(
    resources: List[Resource],
    building_id: str,
    classroom_resource_id: str,
    scheduled_resources: Dict[str, List[Tuple[datetime, datetime]]] = None,
    assignment_time: Optional[Tuple[datetime, datetime]] = None,
) -> List[Resource]:
    """
    Find available breakout rooms in the same building as a classroom.

    Args:
        resources: List of all resources
        building_id: Building ID to search in
        classroom_resource_id: The classroom resource ID
        scheduled_resources: Current resource schedules
        assignment_time: Time range for the assignment

    Returns:
        List of available breakout room resources
    """
    breakout_rooms = filter_resources_by_building(
        resources, building_id, resource_types=["breakout", "study_room"]
    )

    # Remove already scheduled rooms
    available = []
    for room in breakout_rooms:
        if room.id == classroom_resource_id:
            continue  # Skip the classroom itself

        # Check if room is available at the assignment time
        if assignment_time and scheduled_resources:
            room_schedule = scheduled_resources.get(room.id, [])
            is_available = True
            for scheduled_start, scheduled_end in room_schedule:
                if assignment_time[0] < scheduled_end and assignment_time[1] > scheduled_start:
                    is_available = False
                    break
            if is_available:
                available.append(room)
        else:
            available.append(room)

    return available


def calculate_building_utilization(
    resources: List[Resource],
    scheduled_resources: Dict[str, List[Tuple[datetime, datetime]]],
    buildings: Dict[str, Building],
) -> Dict[str, float]:
    """
    Calculate utilization percentage for each building.

    Args:
        resources: List of resources
        scheduled_resources: Resource schedules
        buildings: Building information

    Returns:
        Dictionary mapping building ID to utilization percentage
    """
    # Group resources by building
    building_resources = group_resources_by_building(resources, buildings)

    utilization = {}
    for building_id, (_building, bldg_resources) in building_resources.items():
        total_capacity = sum(r.capacity or 0 for r in bldg_resources)
        if total_capacity == 0:
            utilization[building_id] = 0.0
            continue

        # Calculate total scheduled time
        total_scheduled_time = 0
        for resource in bldg_resources:
            schedule = scheduled_resources.get(resource.id, [])
            for start, end in schedule:
                total_scheduled_time += (end - start).total_seconds() / 3600  # Convert to hours

        # Assume operating hours per day
        operating_hours_per_day = 10
        days_in_term = 100  # Approximate

        total_available_time = total_capacity * operating_hours_per_day * days_in_term

        if total_available_time > 0:
            utilization[building_id] = (total_scheduled_time / total_available_time) * 100
        else:
            utilization[building_id] = 0.0

    return utilization


def recommend_classroom(
    request_requirements: Dict[str, any],
    resources: List[Resource],
    buildings: Dict[str, Building],
    preferred_building_id: Optional[str] = None,
    required_building_id: Optional[str] = None,
) -> List[Resource]:
    """
    Recommend classrooms based on requirements and preferences.

    Args:
        request_requirements: Dictionary of requirements (capacity, amenities, etc.)
        resources: List of all available resources
        buildings: Building information
        preferred_building_id: Preferred building ID
        required_building_id: Required building ID (must be in this building)

    Returns:
        List of recommended classrooms, sorted by preference
    """
    candidates = []

    for resource in resources:
        # Skip if not a classroom
        if resource.resource_type != "classroom":
            continue

        # Check required building
        if required_building_id and resource.building_id != required_building_id:
            continue

        # Check capacity requirement
        if "capacity" in request_requirements:
            min_capacity = request_requirements["capacity"]
            if (resource.capacity or 0) < min_capacity:
                continue

        # Check computer requirements
        if "computers" in request_requirements:
            computers_required = request_requirements["computers"]
            if computers_required > 0:
                resource_computers = resource.attributes.get("computers", {})
                total_computers = resource_computers.get("total", 0)
                if total_computers < computers_required:
                    continue

        candidates.append(resource)

    # Sort by preference
    if preferred_building_id:
        # Put preferred building first
        preferred = [r for r in candidates if r.building_id == preferred_building_id]
        others = [r for r in candidates if r.building_id != preferred_building_id]
        candidates = preferred + others

    return candidates
