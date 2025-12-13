"""Assignment domain model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Assignment:
    """Represents the placement of a SessionRequest occurrence into a specific timeslot."""

    request_id: str
    occurrence_index: int
    start_time: datetime
    end_time: datetime
    assigned_resources: Dict[str, List[str]] = field(default_factory=dict)
    cohort_id: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate that datetimes are timezone-aware."""
        if self.start_time.tzinfo is None:
            raise ValueError("start_time must be timezone-aware")
        if self.end_time.tzinfo is None:
            raise ValueError("end_time must be timezone-aware")
