"""Holiday calendar domain model for managing academic holidays and breaks."""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Set, Tuple

from edusched.errors import ValidationError


@dataclass
class HolidayPeriod:
    """Represents a holiday or break period."""

    start_date: date
    end_date: date
    name: str
    holiday_type: str = "holiday"  # holiday, break, exam_period, etc.

    def contains_date(self, check_date: date) -> bool:
        """Check if a date falls within this holiday period."""
        return self.start_date <= check_date <= self.end_date

    def get_weekdays(self) -> Set[int]:
        """Get the weekdays (0=Monday to 6=Sunday) covered by this holiday."""
        weekdays = set()
        current = self.start_date
        while current <= self.end_date:
            weekdays.add(current.weekday())
            current += timedelta(days=1)
        return weekdays


@dataclass
class HolidayCalendar:
    """Manages holidays and academic breaks for scheduling."""

    id: str
    name: str
    year: int
    holidays: List[HolidayPeriod] = field(default_factory=list)
    excluded_weekdays: Set[int] = field(
        default_factory=set
    )  # Weekdays with no classes (e.g., weekends)

    def add_holiday(
        self, start_date: date, end_date: date, name: str, holiday_type: str = "holiday"
    ):
        """Add a holiday period."""
        holiday = HolidayPeriod(start_date, end_date, name, holiday_type)
        self.holidays.append(holiday)

    def is_holiday(self, check_date: date) -> bool:
        """Check if a date is during a holiday or break."""
        return any(holiday.contains_date(check_date) for holiday in self.holidays)

    def is_schedulable_day(self, check_date: date) -> bool:
        """Check if classes can be scheduled on this date."""
        # Check if it's a weekend
        if check_date.weekday() in self.excluded_weekdays:
            return False

        # Check if it's a holiday
        if self.is_holiday(check_date):
            return False

        return True

    def get_academic_weeks(self, start_date: date, end_date: date) -> List[Tuple[date, date]]:
        """
        Split date range into academic weeks, skipping holidays.
        Returns list of (week_start, week_end) tuples.
        """
        weeks = []
        current_week_start = self.find_next_monday(start_date)

        while current_week_start <= end_date:
            current_week_end = current_week_start + timedelta(days=4)  # Mon-Fri

            # Skip holiday weeks entirely
            if self.is_holiday_week(current_week_start, current_week_end):
                current_week_start += timedelta(days=7)
                continue

            # Adjust week bounds if they extend beyond the range
            if current_week_start < start_date:
                current_week_start = start_date
            if current_week_end > end_date:
                current_week_end = end_date

            if current_week_start <= current_week_end:
                weeks.append((current_week_start, current_week_end))

            current_week_start += timedelta(days=7)

        return weeks

    def is_holiday_week(self, week_start: date, week_end: date) -> bool:
        """Check if an entire week is a holiday/break."""
        for check_date in range((week_end - week_start).days + 1):
            current_date = week_start + timedelta(days=check_date)
            if not self.is_holiday(current_date) and current_date.weekday() < 5:
                return False  # Found at least one regular weekday
        return True  # All weekdays are holidays

    def get_available_days_in_range(self, start_date: date, end_date: date) -> List[date]:
        """Get all available (non-holiday) weekdays in a date range."""
        available_days = []
        current = start_date

        while current <= end_date:
            if self.is_schedulable_day(current):
                available_days.append(current)
            current += timedelta(days=1)

        return available_days

    def find_next_monday(self, from_date: date) -> date:
        """Find the next Monday on or after the given date."""
        days_until_monday = (0 - from_date.weekday()) % 7
        return from_date + timedelta(days=days_until_monday)

    def get_weekly_pattern_days(self, pattern: str) -> List[int]:
        """
        Convert a pattern string to weekday numbers.
        Patterns: "5days", "4days", "3days", "2days"
        """
        patterns = {
            "5days": [0, 1, 2, 3, 4],  # Mon-Fri
            "4days_mt": [0, 1, 2, 3],  # Mon-Thu
            "4days_tf": [1, 2, 3, 4],  # Tue-Fri
            "3days_mw": [0, 1, 2],  # Mon-Wed
            "3days_wf": [2, 3, 4],  # Wed-Fri
            "2days_mt": [0, 1],  # Mon-Tue
            "2days_tf": [3, 4],  # Thu-Fri
        }

        return patterns.get(pattern, [0, 1, 2, 3, 4])  # Default to Mon-Fri

    def calculate_priority_score(self, duration: timedelta) -> int:
        """Calculate priority score based on class duration (longer = higher priority)."""
        # Convert duration to minutes for scoring
        duration_minutes = int(duration.total_seconds() / 60)

        # Longer classes get higher priority
        if duration_minutes >= 180:  # 3+ hours
            return 4
        elif duration_minutes >= 120:  # 2+ hours
            return 3
        elif duration_minutes >= 90:  # 1.5+ hours
            return 2
        else:  # < 1.5 hours
            return 1

    def validate(self) -> List[ValidationError]:
        """Validate the holiday calendar."""
        errors = []

        # Validate ID
        if not self.id:
            errors.append(
                ValidationError(
                    field="id", expected_format="non-empty string", actual_value=self.id
                )
            )

        # Validate year
        if self.year < 2000 or self.year > 2100:
            errors.append(
                ValidationError(
                    field="year",
                    expected_format="year between 2000 and 2100",
                    actual_value=self.year,
                )
            )

        # Validate holidays
        for holiday in self.holidays:
            if holiday.start_date > holiday.end_date:
                errors.append(
                    ValidationError(
                        field=f"holiday_{holiday.name}",
                        expected_format="start_date <= end_date",
                        actual_value=f"{holiday.start_date} > {holiday.end_date}",
                    )
                )

        return errors
