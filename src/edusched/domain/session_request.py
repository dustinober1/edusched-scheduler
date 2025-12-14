"""SessionRequest domain model."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

from edusched.errors import ValidationError

if TYPE_CHECKING:
    from edusched.domain.equipment import EquipmentRequirement


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

    # Enrollment and capacity requirements
    enrollment_count: int = 0  # Number of students enrolled in the class
    min_capacity: int = 0  # Minimum classroom capacity required
    max_capacity: Optional[int] = None  # Maximum acceptable classroom capacity (None for no limit)

    # Department and teacher information
    department_id: Optional[str] = None  # Department offering this course
    teacher_id: Optional[str] = None  # Primary instructor
    additional_teachers: Optional[List[str]] = None  # TAs, co-instructors, etc.

    # Building and room preferences
    preferred_building_id: Optional[str] = None
    required_building_id: Optional[str] = None  # Must be in this building
    required_resource_types: Optional[Dict[str, int]] = (
        None  # e.g., {"classroom": 1, "breakout": 2}
    )

    # Day-specific requirements (days of week when resources are needed)
    day_requirements: Optional[Dict[int, List[str]]] = (
        None  # {0: ["classroom", "breakout"], 2: ["classroom"]}
    )
    # Where 0=Monday, 1=Tuesday, ..., 6=Sunday

    # Scheduling pattern and preferences
    scheduling_pattern: Optional[str] = (
        None  # "5days", "4days_mt", "4days_tf", "3days_mw", "3days_wf", "2days_mt", "2days_tf"
    )
    preferred_time_slots: Optional[List[Dict[str, str]]] = (
        None  # [{ "start": "09:00", "end": "11:00" }]
    )
    avoid_holidays: bool = True  # Default to avoiding holidays
    min_gap_between_occurrences: Optional[timedelta] = None  # Minimum gap between class occurrences
    max_occurrences_per_week: Optional[int] = None  # Maximum occurrences in a single week

    # Equipment requirements
    equipment_requirements: Optional[List["EquipmentRequirement"]] = (
        None  # List of required equipment
    )
    setup_time_minutes: int = 0  # Additional setup time needed before session
    teardown_time_minutes: int = 0  # Time needed after session for cleanup

    # User tracking for equipment certification
    user_id: Optional[str] = None  # User requesting this session

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

        # Validate enrollment count
        if self.enrollment_count < 0:
            errors.append(
                ValidationError(
                    field="enrollment_count",
                    expected_format="non-negative integer",
                    actual_value=self.enrollment_count,
                )
            )

        # Validate capacity requirements
        if self.min_capacity < 0:
            errors.append(
                ValidationError(
                    field="min_capacity",
                    expected_format="non-negative integer",
                    actual_value=self.min_capacity,
                )
            )

        if self.max_capacity is not None and self.max_capacity < 0:
            errors.append(
                ValidationError(
                    field="max_capacity",
                    expected_format="non-negative integer or None",
                    actual_value=self.max_capacity,
                )
            )

        if (
            self.min_capacity > 0
            and self.max_capacity is not None
            and self.min_capacity > self.max_capacity
        ):
            errors.append(
                ValidationError(
                    field="capacity_range",
                    expected_format="min_capacity <= max_capacity",
                    actual_value=f"{self.min_capacity} > {self.max_capacity}",
                )
            )

        # Validate modality
        valid_modalities = {"online", "in_person", "hybrid"}
        if self.modality not in valid_modalities:
            errors.append(
                ValidationError(
                    field="modality",
                    expected_format=f"one of {valid_modalities}",
                    actual_value=self.modality,
                )
            )

        # Validate setup/teardown times
        if self.setup_time_minutes < 0:
            errors.append(
                ValidationError(
                    field="setup_time_minutes",
                    expected_format="non-negative integer",
                    actual_value=self.setup_time_minutes,
                )
            )

        if self.teardown_time_minutes < 0:
            errors.append(
                ValidationError(
                    field="teardown_time_minutes",
                    expected_format="non-negative integer",
                    actual_value=self.teardown_time_minutes,
                )
            )

        # Validate equipment requirements if present
        if self.equipment_requirements:
            for req in self.equipment_requirements:
                if req.quantity <= 0:
                    errors.append(
                        ValidationError(
                            field="equipment_requirements.quantity",
                            expected_format="positive integer",
                            actual_value=req.quantity,
                        )
                    )
                if not req.equipment_type_id:
                    errors.append(
                        ValidationError(
                            field="equipment_requirements.equipment_type_id",
                            expected_format="non-empty string",
                            actual_value=req.equipment_type_id,
                        )
                    )

        return errors
