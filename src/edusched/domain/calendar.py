"""Calendar domain model."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, NamedTuple
from zoneinfo import ZoneInfo


class TimeWindow(NamedTuple):
    """Represents a time window with start and end times."""

    start: datetime
    end: datetime


@dataclass
class Calendar:
    """Manages availability windows and blackout periods with timezone support."""

    id: str
    timezone: ZoneInfo = field(default_factory=lambda: ZoneInfo("UTC"))
    timeslot_granularity: timedelta = field(default_factory=lambda: timedelta(minutes=15))
    availability_windows: List[TimeWindow] = field(default_factory=list)
    blackout_periods: List[TimeWindow] = field(default_factory=list)

    def is_available(self, start: datetime, end: datetime) -> bool:
        """
        Check if time period is available.

        All datetimes must be timezone-aware.

        Args:
            start: Start time (timezone-aware)
            end: End time (timezone-aware)

        Returns:
            True if the period is available, False otherwise
        """
        # Check if period falls within any availability window
        if self.availability_windows:
            in_window = False
            for window in self.availability_windows:
                if start >= window.start and end <= window.end:
                    in_window = True
                    break
            if not in_window:
                return False

        # Check if period overlaps with any blackout period
        for blackout in self.blackout_periods:
            if start < blackout.end and end > blackout.start:
                return False

        return True
