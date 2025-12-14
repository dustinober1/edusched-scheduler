"""Department domain model."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from edusched.errors import ValidationError


@dataclass
class Department:
    """Represents an academic department with availability constraints."""

    id: str
    name: str
    head: Optional[str] = None  # Department head name
    building_id: Optional[str] = None  # Primary building location
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None

    # Availability calendar for scheduling
    availability_calendar_id: Optional[str] = None

    # Department-specific requirements
    preferred_times: Dict[str, List[str]] = field(
        default_factory=dict
    )  # e.g., {"monday": ["09:00-12:00", "14:00-17:00"]}
    blacked_out_days: List[str] = field(default_factory=list)  # Days when department doesn't teach

    # Resource preferences
    preferred_room_types: List[str] = field(default_factory=list)  # Preferred classroom types
    required_amenities: List[str] = field(default_factory=list)  # Required amenities in rooms

    def validate(self) -> List[ValidationError]:
        """
        Validate department parameters.

        Returns:
            List of validation errors (empty if valid)
        """
        errors: List[ValidationError] = []

        # Validate ID
        if not self.id:
            errors.append(
                ValidationError(
                    field="id",
                    expected_format="non-empty string",
                    actual_value=self.id,
                )
            )

        # Validate name
        if not self.name:
            errors.append(
                ValidationError(
                    field="name",
                    expected_format="non-empty string",
                    actual_value=self.name,
                )
            )

        # Validate preferred_times format
        for day, time_slots in self.preferred_times.items():
            if not isinstance(time_slots, list):
                errors.append(
                    ValidationError(
                        field="preferred_times",
                        expected_format=f"list of time strings for {day}",
                        actual_value=time_slots,
                    )
                )
                continue

            for time_slot in time_slots:
                if not isinstance(time_slot, str):
                    errors.append(
                        ValidationError(
                            field="preferred_times",
                            expected_format="time string in HH:MM-HH:MM format",
                            actual_value=time_slot,
                        )
                    )

        return errors

    def is_day_available(self, day_of_week: str) -> bool:
        """
        Check if the department is available to teach on a specific day.

        Args:
            day_of_week: Day name (e.g., "monday", "tuesday")

        Returns:
            True if department is available on this day
        """
        # Check if day is explicitly blacked out
        if day_of_week.lower() in [d.lower() for d in self.blacked_out_days]:
            return False

        # If no preferred times specified, assume available all day
        if day_of_week.lower() not in self.preferred_times:
            return True

        # Available if preferred times exist for this day
        return len(self.preferred_times.get(day_of_week.lower(), [])) > 0

    def get_available_days(self) -> List[str]:
        """
        Get list of days when department is available to teach.

        Returns:
            List of available day names
        """
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        available_days = []

        for day in days:
            if self.is_day_available(day):
                available_days.append(day)

        return available_days
