"""Flexible room usage constraints."""

from typing import TYPE_CHECKING, Optional

from edusched.constraints.base import Constraint, ConstraintContext, Violation
from edusched.domain.resource import RoomType

if TYPE_CHECKING:
    from edusched.domain.assignment import Assignment


class RoomTypeFlexibilityConstraint(Constraint):
    """Enables flexible room usage based on room capabilities."""

    def __init__(self, room_id: str):
        """
        Initialize room type flexibility constraint.

        Args:
            room_id: The room ID this constraint applies to
        """
        self.room_id = room_id

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if room can be used for the requested type."""
        # Get the room
        room = context.resource_lookup.get(self.room_id)
        if not room or room.room_type is None:
            return None

        # Get the course/session type
        request = context.request_lookup.get(assignment.request_id)
        if not request:
            return None

        # Determine the required room type from the request
        required_type = self._get_required_room_type(request)
        if not required_type:
            return None  # No specific type requirement

        # Check if room can be used as the required type
        if not room.can_be_used_as_type(required_type):
            # Check if it's the last resort
            if not self._is_last_resort(request, context):
                return Violation(
                    constraint_type=self.constraint_type,
                    affected_request_id=assignment.request_id,
                    affected_resource_id=self.room_id,
                    message=f"Room {self.room_id} cannot be used as {required_type.value}",
                )

        # Check capacity requirements
        if hasattr(request, "enrollment_count"):
            if not room.meets_capacity_for_type(required_type, request.enrollment_count):
                return Violation(
                    constraint_type=self.constraint_type,
                    affected_request_id=assignment.request_id,
                    affected_resource_id=self.room_id,
                    message=f"Room {self.room_id} capacity insufficient for {required_type.value} with {request.enrollment_count} students",
                )

        return None

    def _get_required_room_type(self, request) -> Optional[RoomType]:
        """Extract required room type from request."""
        # Check required_attributes for room type hints
        if hasattr(request, "required_attributes"):
            attrs = request.required_attributes

            # Check for explicit room type requirement
            if "room_type" in attrs:
                try:
                    return RoomType(attrs["room_type"])
                except ValueError:
                    pass

            # Check for course type that implies room type
            if "course_type" in attrs:
                course_type = attrs["course_type"].lower()
                if course_type == "lecture":
                    return RoomType.LECTURE_HALL
                elif course_type == "lab":
                    return RoomType.COMPUTER_LAB
                elif course_type == "seminar":
                    return RoomType.SEMINAR_ROOM
                elif course_type == "conference":
                    return RoomType.CONFERENCE_ROOM
                elif course_type == "breakout":
                    return RoomType.BREAKOUT_ROOM

        # Check request pattern or other attributes
        if hasattr(request, "scheduling_pattern"):
            pattern = request.scheduling_pattern
            if "seminar" in str(pattern).lower():
                return RoomType.SEMINAR_ROOM
            elif "lecture" in str(pattern).lower():
                return RoomType.LECTURE_HALL

        return None

    def _is_last_resort(self, request, context: ConstraintContext) -> bool:
        """Check if this is a last resort booking."""
        # This would integrate with the solver to check if no other rooms are available
        # For now, return False - let the solver determine last resort
        return False

    def explain(self, violation: Violation) -> str:
        """Provide explanation for room type violation."""
        return f"Room type requirement not met: {violation.message}"

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.room_type_flexibility"


class RoomConversionConstraint(Constraint):
    """Ensures adequate time for room conversion when needed."""

    def __init__(self, room_id: str):
        """
        Initialize room conversion constraint.

        Args:
            room_id: The room ID this constraint applies to
        """
        self.room_id = room_id

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check for adequate conversion time between bookings."""
        room = context.resource_lookup.get(self.room_id)
        if not room or room.room_type is None:
            return None

        # Get the course/session type for current assignment
        request = context.request_lookup.get(assignment.request_id)
        if not request:
            return None

        current_type = self._get_required_room_type(request)
        if not current_type:
            # If no specific type required, assume primary room type
            current_type = room.room_type

        # Check previous and next assignments for adequate buffer
        for existing in solution:
            if existing.assigned_resources and self.room_id in [
                r for resources in existing.assigned_resources.values() for r in resources
            ]:
                # Get the room type for existing assignment
                existing_request = context.request_lookup.get(existing.request_id)
                if not existing_request:
                    continue

                existing_type = self._get_required_room_type(existing_request)
                if not existing_type:
                    existing_type = room.room_type

                # Check if conversion is needed (different room types)
                needs_conversion = False
                conversion_time = 0

                # If types are different, check if conversion is needed
                if existing_type != current_type:
                    # Check if converting from existing type to current type needs time
                    if room.needs_conversion_for_type(current_type):
                        needs_conversion = True
                        conversion_time = max(
                            conversion_time, room.get_conversion_time(current_type)
                        )

                    # Check if converting from current type to existing type needs time
                    if room.needs_conversion_for_type(existing_type):
                        needs_conversion = True
                        conversion_time = max(
                            conversion_time, room.get_conversion_time(existing_type)
                        )

                # Check time before this assignment (existing is before current)
                if existing.end_time <= assignment.start_time and needs_conversion:
                    buffer = (assignment.start_time - existing.end_time).total_seconds() / 60
                    if buffer < conversion_time:
                        return Violation(
                            constraint_type=self.constraint_type,
                            affected_request_id=assignment.request_id,
                            affected_resource_id=self.room_id,
                            message=f"Room {self.room_id} needs {conversion_time} minutes for conversion from {existing_type.value} to {current_type.value}, "
                            f"only {buffer:.0f} minutes available",
                        )

                # Check time after this assignment (existing is after current)
                elif assignment.end_time <= existing.start_time and needs_conversion:
                    buffer = (existing.start_time - assignment.end_time).total_seconds() / 60
                    if buffer < conversion_time:
                        return Violation(
                            constraint_type=self.constraint_type,
                            affected_request_id=assignment.request_id,
                            affected_resource_id=self.room_id,
                            message=f"Room {self.room_id} needs {conversion_time} minutes for conversion from {current_type.value} to {existing_type.value}, "
                            f"only {buffer:.0f} minutes available",
                        )

        return None

    def _get_required_room_type(self, request) -> Optional[RoomType]:
        """Extract required room type from request."""
        if hasattr(request, "required_attributes"):
            attrs = request.required_attributes
            if "room_type" in attrs:
                try:
                    return RoomType(attrs["room_type"])
                except ValueError:
                    pass

            if "course_type" in attrs:
                course_type = attrs["course_type"].lower()
                if course_type == "lecture":
                    return RoomType.LECTURE_HALL
                elif course_type == "lab":
                    return RoomType.COMPUTER_LAB
                elif course_type == "seminar":
                    return RoomType.SEMINAR_ROOM
                elif course_type == "conference":
                    return RoomType.CONFERENCE_ROOM
                elif course_type == "breakout":
                    return RoomType.BREAKOUT_ROOM

        return None

    def explain(self, violation: Violation) -> str:
        """Provide explanation for conversion time violation."""
        return f"Room conversion time requirement not met: {violation.message}"

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "hard.room_conversion_time"


class RoomCapacityOptimizationConstraint(Constraint):
    """Optimizes room usage by preferring appropriately sized rooms."""

    def __init__(self, room_id: str):
        """
        Initialize room capacity optimization constraint.

        Args:
            room_id: The room ID this constraint applies to
        """
        self.room_id = room_id

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check for optimal room capacity usage."""
        room = context.resource_lookup.get(self.room_id)
        if not room or not room.capacity:
            return None

        request = context.request_lookup.get(assignment.request_id)
        if not request or not hasattr(request, "enrollment_count"):
            return None

        enrollment = request.enrollment_count

        # This is a soft constraint that scores room efficiency
        # For now, just pass (the scorer will handle the optimization)
        return None

    def get_efficiency_score(self, enrollment: int) -> float:
        """
        Calculate how efficiently the room is being used.

        Args:
            enrollment: Number of students

        Returns:
            Efficiency score (0.0 to 1.0, higher is better)
        """
        if not self.capacity or enrollment == 0:
            return 0.0

        # Ideal utilization is 70-90% of capacity
        utilization = enrollment / self.capacity

        if utilization < 0.3:
            return utilization  # Very underutilized
        elif 0.3 <= utilization <= 0.7:
            return 0.3 + (utilization - 0.3) * 2  # Ramp up
        elif 0.7 < utilization <= 0.9:
            return 1.0  # Optimal range
        else:
            return max(0, 1.0 - (utilization - 0.9) * 2)  # Overcrowded

    def explain(self, violation: Violation) -> str:
        """Provide explanation for capacity optimization violation."""
        return f"Room capacity optimization: {violation.message}"

    @property
    def constraint_type(self) -> str:
        """Return constraint type identifier."""
        return "soft.room_capacity_optimization"
