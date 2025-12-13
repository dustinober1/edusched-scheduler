"""SessionRequest domain model."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional

from edusched.errors import ValidationError


@dataclass
class SessionRequest:
    """Represents a request to schedule one or more session occurrences."""

    id: str
    duration: timedelta
    number_of_occurrences: int
    earliest_date: datetime
    latest_date: datetime
    cohort_id: Optional[str] = None
    modality: Literal["online", "in_person", "hybrid"] = "in_person"
    required_attributes: Dict[str, Any] = field(default_factory=dict)

    # Building and room preferences
    preferred_building_id: Optional[str] = None
    required_building_id: Optional[str] = None  # Must be in this building
    required_resource_types: Optional[Dict[str, int]] = None  # e.g., {"classroom": 1, "breakout": 2}

    # Day-specific requirements (days of week when resources are needed)
    day_requirements: Optional[Dict[int, List[str]]] = None  # {0: ["classroom", "breakout"], 2: ["classroom"]}
    # Where 0=Monday, 1=Tuesday, ..., 6=Sunday

    def validate(self) -> List[ValidationError]:
        """
        Validate request parameters including timezone-aware datetime requirement.

        Returns:
            List of validation errors (empty if valid)
        """
        errors: List[ValidationError] = []

        # Validate timezone-aware datetimes
        if self.earliest_date.tzinfo is None:
            errors.append(
                ValidationError(
                    field="earliest_date",
                    expected_format="timezone-aware datetime (e.g., datetime.now(ZoneInfo('UTC')))",
                    actual_value=self.earliest_date,
                )
            )

        if self.latest_date.tzinfo is None:
            errors.append(
                ValidationError(
                    field="latest_date",
                    expected_format="timezone-aware datetime (e.g., datetime.now(ZoneInfo('UTC')))",
                    actual_value=self.latest_date,
                )
            )

        # Validate date range
        if self.earliest_date > self.latest_date:
            errors.append(
                ValidationError(
                    field="date_range",
                    expected_format="earliest_date <= latest_date",
                    actual_value=f"{self.earliest_date} > {self.latest_date}",
                )
            )

        # Validate duration
        if self.duration <= timedelta(0):
            errors.append(
                ValidationError(
                    field="duration",
                    expected_format="positive timedelta",
                    actual_value=self.duration,
                )
            )

        # Validate number of occurrences
        if self.number_of_occurrences <= 0:
            errors.append(
                ValidationError(
                    field="number_of_occurrences",
                    expected_format="positive integer",
                    actual_value=self.number_of_occurrences,
                )
            )

        return errors
