"""Resource domain model."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Resource:
    """Represents a bookable resource (instructor, room, campus, online slot, etc.)."""

    id: str
    resource_type: str
    concurrency_capacity: int = 1
    attributes: Dict[str, Any] = field(default_factory=dict)
    availability_calendar_id: Optional[str] = None

    def can_satisfy(self, requirements: Dict[str, Any]) -> bool:
        """
        Check if resource attributes satisfy requirements.

        Args:
            requirements: Dictionary of required attributes

        Returns:
            True if all requirements are satisfied, False otherwise
        """
        for key, required_value in requirements.items():
            if key not in self.attributes:
                return False
            if self.attributes[key] != required_value:
                return False
        return True
