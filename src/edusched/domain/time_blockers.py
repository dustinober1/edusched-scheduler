"""Time blockers for institutional scheduling constraints."""

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import List, Optional, Tuple


@dataclass
class TimeBlock:
    """Represents a blocked time period when no classes should be scheduled."""

    name: str  # e.g., "Lunch Break", "All-Hands Meeting", "Common Exam"
    start_time: time  # Start time of the block (HH:MM)
    end_time: time  # End time of the block (HH:MM)
    days_of_week: List[int]  # Days when block applies [0=Monday, ..., 6=Sunday]
    start_date: Optional[datetime] = None  # When block starts being active (None = always active)
    end_date: Optional[datetime] = None  # When block ends being active (None = always active)
    description: Optional[str] = None

    def is_active(self, check_date: datetime) -> bool:
        """Check if time block is active on the given date."""
        # Check date range
        if self.start_date and check_date < self.start_date:
            return False
        if self.end_date and check_date > self.end_date:
            return False

        # Check day of week
        return check_date.weekday() in self.days_of_week

    def blocks_time(self, check_time: datetime) -> bool:
        """Check if a specific datetime falls within this time block."""
        # First check if it's the right day and date range
        if not self.is_active(check_time):
            return False

        # Check if time falls within the block
        check_time_only = check_time.time()

        # Handle blocks that cross midnight (though rare for institutional blocks)
        if self.start_time <= self.end_time:
            # Normal case: start and end on same day
            return self.start_time <= check_time_only <= self.end_time
        else:
            # Edge case: block crosses midnight
            return check_time_only >= self.start_time or check_time_only <= self.end_time


@dataclass
class TimeBlocker:
    """Manages institutional time blockers for scheduling."""

    institution_id: str
    blocks: List[TimeBlock] = field(default_factory=list)

    def add_block(self, block: TimeBlock) -> None:
        """Add a time block."""
        self.blocks.append(block)

    def add_daily_block(
        self,
        name: str,
        start_time: str,  # "HH:MM"
        end_time: str,  # "HH:MM"
        days: List[int],  # [0, 1, 2, 3, 4] for Mon-Fri
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        description: Optional[str] = None,
    ) -> None:
        """Add a time block using string time format."""
        start = time.fromisoformat(start_time)
        end = time.fromisoformat(end_time)

        block = TimeBlock(
            name=name,
            start_time=start,
            end_time=end,
            days_of_week=days,
            start_date=start_date,
            end_date=end_date,
            description=description,
        )
        self.add_block(block)

    def is_time_blocked(self, check_time: datetime) -> Tuple[bool, Optional[str]]:
        """
        Check if a specific time is blocked.

        Returns:
            Tuple of (is_blocked, block_name)
        """
        for block in self.blocks:
            if block.blocks_time(check_time):
                return True, block.name
        return False, None

    def get_available_time_blocks(
        self,
        day_date: datetime,
        day_start: time = time(8, 0),  # 8:00 AM
        day_end: time = time(22, 0),  # 10:00 PM
    ) -> List[Tuple[time, time]]:
        """
        Get available time slots on a specific day, excluding blocked times.

        Returns:
            List of (start_time, end_time) tuples for available slots
        """
        # Get all blocks that apply to this day
        day_blocks = [b for b in self.blocks if b.is_active(day_date)]

        # Sort blocks by start time
        day_blocks.sort(key=lambda b: b.start_time)

        # Generate available slots
        available = []
        current_time = day_start

        for block in day_blocks:
            # Add time before this block if available
            if current_time < block.start_time:
                available.append((current_time, block.start_time))

            # Move current time past this block
            current_time = max(current_time, block.end_time)

        # Add time after last block
        if current_time < day_end:
            available.append((current_time, day_end))

        return available


def create_standard_time_blocker(institution_id: str) -> TimeBlocker:
    """
    Create a standard time blocker with common institutional blocks.

    Args:
        institution_id: ID of the institution

    Returns:
        TimeBlocker with standard blocks configured
    """
    blocker = TimeBlocker(institution_id=institution_id)

    # Common lunch break (11:30 AM - 1:30 PM, Mon-Fri)
    blocker.add_daily_block(
        name="Lunch Break",
        start_time="11:30",
        end_time="13:30",
        days=[0, 1, 2, 3, 4],  # Monday-Friday
        description="Common lunch period - no classes scheduled",
    )

    # Department meetings (Wednesday 3:00-4:30 PM)
    blocker.add_daily_block(
        name="Department Meetings",
        start_time="15:00",
        end_time="16:30",
        days=[2],  # Wednesday
        description="Weekly department meetings",
    )

    # All-hands meetings (First Monday of month 2:00-3:00 PM)
    # Note: This would need more sophisticated date filtering for "first Monday"
    blocker.add_daily_block(
        name="All-Hands Meeting",
        start_time="14:00",
        end_time="15:00",
        days=[0],  # Monday
        description="Monthly all-hands meeting",
    )

    # Common exam periods (Finals week - 9 AM to 5 PM blocks)
    # These would be activated during specific date ranges
    blocker.add_block(
        TimeBlock(
            name="Final Exam Period - Morning",
            start_time=time(9, 0),
            end_time=time(12, 0),
            days_of_week=[0, 1, 2, 3, 4],  # Mon-Fri
            # start_date and end_date would be set when creating academic calendar
            description="Final exam morning slots",
        )
    )

    blocker.add_block(
        TimeBlock(
            name="Final Exam Period - Afternoon",
            start_time=time(13, 0),
            end_time=time(17, 0),
            days_of_week=[0, 1, 2, 3, 4],  # Mon-Fri
            # start_date and end_date would be set when creating academic calendar
            description="Final exam afternoon slots",
        )
    )

    # Break between classes (common 10-minute passing periods)
    # Note: This would be implemented differently - as a constraint rather than a blocker
    # since it affects the start/end times of classes rather than blocking entire periods

    return blocker


def create_research_university_blocker(institution_id: str) -> TimeBlocker:
    """
    Create time blocker for a research university with research seminars.

    Args:
        institution_id: ID of the institution

    Returns:
        TimeBlocker configured for research university
    """
    blocker = create_standard_time_blocker(institution_id)

    # Research seminar time (Thursday 4:00-5:30 PM)
    blocker.add_daily_block(
        name="Research Seminar",
        start_time="16:00",
        end_time="17:30",
        days=[3],  # Thursday
        description="Weekly research seminar series",
    )

    # Faculty research time (Tuesday afternoons)
    blocker.add_daily_block(
        name="Research Time",
        start_time="13:00",
        end_time="17:00",
        days=[1],  # Tuesday
        description="Protected faculty research time",
    )

    # Graduate student defenses (Friday 10 AM-12 PM)
    blocker.add_daily_block(
        name="Thesis Defenses",
        start_time="10:00",
        end_time="12:00",
        days=[4],  # Friday
        description="Thesis and dissertation defense times",
    )

    return blocker


def create_community_college_blocker(institution_id: str) -> TimeBlocker:
    """
    Create time blocker for a community college with different scheduling needs.

    Args:
        institution_id: ID of the institution

    Returns:
        TimeBlocker configured for community college
    """
    blocker = TimeBlocker(institution_id=institution_id)

    # Community colleges often have more evening classes, so lunch break is shorter
    blocker.add_daily_block(
        name="Lunch Break",
        start_time="12:00",
        end_time="13:00",
        days=[0, 1, 2, 3, 4],  # Monday-Friday
        description="One-hour lunch break",
    )

    # Registration periods (first week of semester)
    blocker.add_block(
        TimeBlock(
            name="Registration Period",
            start_time=time(9, 0),
            end_time=time(17, 0),
            days_of_week=[0, 1, 2, 3, 4],  # Mon-Fri
            description="Student registration and advising",
        )
    )

    # Evening adult education setup time (5:00-6:00 PM)
    blocker.add_daily_block(
        name="Evening Setup",
        start_time="17:00",
        end_time="18:00",
        days=[0, 1, 2, 3, 4],  # Monday-Friday
        description="Setup time for evening classes",
    )

    return blocker
