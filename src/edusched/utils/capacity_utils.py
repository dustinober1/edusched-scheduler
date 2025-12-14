"""Utility functions for classroom capacity management and recommendations."""

from typing import Dict, List, Optional, Tuple

from edusched.domain.resource import Resource
from edusched.domain.session_request import SessionRequest


def get_classroom_capacity(resource: Resource) -> Optional[int]:
    """
    Get the capacity of a classroom resource.

    Args:
        resource: The classroom resource

    Returns:
        Capacity if available, None otherwise
    """
    if resource.resource_type != "classroom":
        return None

    return resource.capacity


def check_capacity_fit(
    classroom: Resource,
    enrollment_count: int,
    min_capacity: int = 0,
    max_capacity: Optional[int] = None,
    buffer_percent: float = 0.1,
) -> Tuple[bool, str]:
    """
    Check if a classroom can accommodate a class.

    Args:
        classroom: The classroom resource to check
        enrollment_count: Number of students in the class
        min_capacity: Minimum required capacity (default 0)
        max_capacity: Maximum acceptable capacity (None for no limit)
        buffer_percent: Extra capacity buffer as percentage (default 10%)

    Returns:
        Tuple of (can_fit: bool, reason: str)
    """
    if classroom.resource_type != "classroom":
        return False, "Resource is not a classroom"

    if classroom.capacity is None:
        return False, "Classroom capacity is unknown"

    required_capacity = max(enrollment_count, min_capacity)
    if required_capacity == 0:
        return True, "No capacity requirement specified"

    # Apply buffer
    required_with_buffer = int(required_capacity * (1 + buffer_percent))

    # Check minimum capacity
    if classroom.capacity < required_with_buffer:
        return False, (
            f"Classroom capacity ({classroom.capacity}) is less than required "
            f"({required_with_buffer} including {buffer_percent * 100}% buffer)"
        )

    # Check maximum capacity
    if max_capacity is not None and classroom.capacity > max_capacity:
        return False, (
            f"Classroom capacity ({classroom.capacity}) exceeds maximum allowed ({max_capacity})"
        )

    # Check if classroom is too large (more than 2x required with buffer)
    if classroom.capacity > required_with_buffer * 2:
        return True, f"Classroom may be too large (capacity: {classroom.capacity})"

    return True, f"Good fit (capacity: {classroom.capacity}, required: {required_with_buffer})"


def recommend_classrooms(
    enrollment_count: int,
    classrooms: List[Resource],
    min_capacity: int = 0,
    max_capacity: Optional[int] = None,
    buffer_percent: float = 0.1,
    building_id: Optional[str] = None,
    max_recommendations: int = 5,
) -> List[Tuple[Resource, str, float]]:
    """
    Recommend suitable classrooms for a class.

    Args:
        enrollment_count: Number of students in the class
        classrooms: List of classroom resources to consider
        min_capacity: Minimum required capacity (default 0)
        max_capacity: Maximum acceptable capacity (None for no limit)
        buffer_percent: Extra capacity buffer as percentage (default 10%)
        building_id: Filter by specific building (optional)
        max_recommendations: Maximum number of recommendations to return

    Returns:
        List of tuples: (classroom, reason, efficiency_score)
        Efficiency score is between 0 and 1, higher is better
    """
    recommendations = []
    required_capacity = max(enrollment_count, min_capacity)
    required_with_buffer = int(required_capacity * (1 + buffer_percent))

    for classroom in classrooms:
        # Filter by building if specified
        if building_id and classroom.building_id != building_id:
            continue

        # Skip non-classroom resources
        if classroom.resource_type != "classroom" or classroom.capacity is None:
            continue

        can_fit, reason = check_capacity_fit(
            classroom, enrollment_count, min_capacity, max_capacity, buffer_percent
        )

        if can_fit:
            # Calculate efficiency score (how well-sized the room is)
            efficiency = calculate_efficiency_score(
                classroom.capacity, required_with_buffer, max_capacity
            )
            recommendations.append((classroom, reason, efficiency))

    # Sort by efficiency score (descending)
    recommendations.sort(key=lambda x: x[2], reverse=True)
    return recommendations[:max_recommendations]


def calculate_efficiency_score(
    classroom_capacity: int, required_capacity: int, max_capacity: Optional[int] = None
) -> float:
    """
    Calculate how efficiently a classroom fits a requirement.

    Args:
        classroom_capacity: The classroom's capacity
        required_capacity: The required capacity (including buffer)
        max_capacity: Maximum acceptable capacity (optional)

    Returns:
        Efficiency score between 0 and 1
    """
    if classroom_capacity < required_capacity:
        return 0.0  # Can't fit

    # Perfect fit is when capacity is just above required
    ideal_ratio = 1.1  # 10% above required
    actual_ratio = classroom_capacity / required_capacity

    if max_capacity is not None and classroom_capacity > max_capacity:
        return 0.0  # Exceeds maximum

    # Score based on how close to ideal ratio
    if actual_ratio <= ideal_ratio:
        # Under or at ideal ratio - good score
        score = 1.0 - (ideal_ratio - actual_ratio) * 0.5
    else:
        # Over ideal ratio - decreasing score
        # Penalty grows exponentially for very large rooms
        excess_ratio = actual_ratio - ideal_ratio
        score = 1.0 / (1.0 + excess_ratio * excess_ratio)

    return max(0.0, min(1.0, score))


def get_capacity_statistics(classrooms: List[Resource]) -> Dict[str, any]:
    """
    Get statistics about classroom capacities.

    Args:
        classrooms: List of classroom resources

    Returns:
        Dictionary with capacity statistics
    """
    capacities = [
        c.capacity for c in classrooms if c.resource_type == "classroom" and c.capacity is not None
    ]

    if not capacities:
        return {
            "count": 0,
            "min_capacity": 0,
            "max_capacity": 0,
            "avg_capacity": 0,
            "total_capacity": 0,
        }

    return {
        "count": len(capacities),
        "min_capacity": min(capacities),
        "max_capacity": max(capacities),
        "avg_capacity": sum(capacities) / len(capacities),
        "total_capacity": sum(capacities),
    }


def find_classrooms_for_class(
    session_request: SessionRequest,
    available_classrooms: List[Resource],
    buffer_percent: float = 0.1,
) -> List[Resource]:
    """
    Find suitable classrooms for a session request.

    Args:
        session_request: The class session request
        available_classrooms: List of available classroom resources
        buffer_percent: Extra capacity buffer as percentage

    Returns:
        List of suitable classrooms, sorted by preference
    """
    recommendations = recommend_classrooms(
        enrollment_count=session_request.enrollment_count,
        classrooms=available_classrooms,
        min_capacity=session_request.min_capacity,
        max_capacity=session_request.max_capacity,
        buffer_percent=buffer_percent,
        building_id=session_request.required_building_id or session_request.preferred_building_id,
    )

    return [r for r, _, _ in recommendations]
