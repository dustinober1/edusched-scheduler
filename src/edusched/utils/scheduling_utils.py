"""Utilities for scheduling with patterns and spreading occurrences."""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Set
from zoneinfo import ZoneInfo

from edusched.domain.holiday_calendar import HolidayCalendar
from edusched.domain.session_request import SessionRequest


class OccurrenceSpreader:
    """Utility class for spreading class occurrences throughout the academic year."""

    def __init__(self, holiday_calendar: HolidayCalendar):
        self.holiday_calendar = holiday_calendar

    def generate_occurrence_dates(
        self,
        request: SessionRequest,
        timezone: ZoneInfo = ZoneInfo("UTC")
    ) -> List[date]:
        """
        Generate optimal dates for class occurrences, spread throughout the term.

        Args:
            request: The session request to schedule
            timezone: Timezone for date calculations

        Returns:
            List of dates for scheduled occurrences
        """
        start_date = request.earliest_date.date()
        end_date = request.latest_date.date()

        # Get available weeks in the term
        academic_weeks = self.holiday_calendar.get_academic_weeks(start_date, end_date)

        # Determine scheduling pattern
        pattern = request.scheduling_pattern or self._determine_default_pattern(request)
        pattern_days = self.holiday_calendar.get_weekly_pattern_days(pattern)

        # Generate candidates dates
        candidate_dates = []
        for week_start, week_end in academic_weeks:
            week_dates = self._get_pattern_dates_in_week(
                week_start, week_end, pattern_days, request.avoid_holidays
            )
            candidate_dates.extend(week_dates)

        # Select optimal dates using spreading algorithm
        selected_dates = self._select_spread_dates(candidate_dates, request, academic_weeks)

        return selected_dates

    def _determine_default_pattern(self, request: SessionRequest) -> str:
        """Determine default scheduling pattern based on class characteristics."""
        # For now, default to 5 days (Mon-Fri)
        # In a more sophisticated system, this could consider:
        # - Course type (lecture, lab, seminar)
        # - Student level (undergrad, grad)
        # - Duration
        # - Enrollment size
        return "5days"

    def _get_pattern_dates_in_week(
        self,
        week_start: date,
        week_end: date,
        pattern_days: List[int],
        avoid_holidays: bool
    ) -> List[date]:
        """Get all valid dates in a week that match the pattern."""
        valid_dates = []

        current = week_start
        while current <= week_end:
            # Check if this day matches the pattern (0=Monday to 6=Sunday)
            if current.weekday() in pattern_days:
                # Check if we should avoid holidays
                if not avoid_holidays or not self.holiday_calendar.is_holiday(current):
                    valid_dates.append(current)
            current += timedelta(days=1)

        return valid_dates

    def _select_spread_dates(
        self,
        candidate_dates: List[date],
        request: SessionRequest,
        academic_weeks: List[Tuple[date, date]]
    ) -> List[date]:
        """
        Select dates that are spread throughout the term.

        Uses various strategies to avoid bunching:
        1. Even distribution across weeks
        2. Minimize consecutive days
        3. Respect minimum gap requirements
        """
        if not candidate_dates:
            return []

        occurrences_needed = request.number_of_occurrences

        # Calculate target dates per week
        total_weeks = len(academic_weeks)
        min_per_week = occurrences_needed // total_weeks
        extra_needed = occurrences_needed % total_weeks

        # Group candidate dates by week
        dates_by_week: Dict[int, List[date]] = {}
        for i, (week_start, week_end) in enumerate(academic_weeks):
            week_dates = [
                d for d in candidate_dates
                if week_start <= d <= week_end
            ]
            dates_by_week[i] = week_dates

        selected_dates = []
        used_weeks: Set[int] = set()
        consecutive_count = 0
        last_used_week = -1

        # First pass: distribute minimum occurrences
        for week_idx in range(total_weeks):
            if week_idx in dates_by_week and dates_by_week[week_idx]:
                # Select one date from this week
                selected_date = self._select_best_date_in_week(
                    dates_by_week[week_idx],
                    selected_dates,
                    request
                )
                if selected_date:
                    selected_dates.append(selected_date)
                    used_weeks.add(week_idx)

        # Second pass: add extra occurrences to remaining weeks
        extra_added = 0
        for week_idx in range(total_weeks):
            if extra_added >= extra_needed:
                break
            if week_idx not in used_weeks and week_idx in dates_by_week and dates_by_week[week_idx]:
                # Try to add an extra occurrence to this week
                selected_date = self._select_best_date_in_week(
                    dates_by_week[week_idx],
                    selected_dates,
                    request,
                    allow_consecutive=True
                )
                if selected_date:
                    selected_dates.append(selected_date)
                    extra_added += 1

        # Sort the final dates
        selected_dates.sort()

        # If we still don't have enough occurrences, fill from remaining candidates
        if len(selected_dates) < occurrences_needed:
            remaining_needed = occurrences_needed - len(selected_dates)
            for candidate_date in candidate_dates:
                if candidate_date not in selected_dates:
                    selected_dates.append(candidate_date)
                    if len(selected_dates) >= occurrences_needed:
                        break

        return selected_dates[:occurrences_needed]

    def _select_best_date_in_week(
        self,
        week_dates: List[date],
        selected_dates: List[date],
        request: SessionRequest,
        allow_consecutive: bool = False
    ) -> Optional[date]:
        """Select the best date in a week based on spreading criteria."""
        if not week_dates:
            return None

        # Scoring factors
        best_date = None
        best_score = -1

        for candidate_date in week_dates:
            score = 0

            # Prefer earlier days in the week for stability
            day_score = 5 - candidate_date.weekday()  # Monday=5, Tuesday=4, etc.
            score += day_score

            # Avoid consecutive weeks if not allowed
            if not allow_consecutive and selected_dates:
                last_date = selected_dates[-1]
                weeks_diff = (candidate_date - last_date).days // 7
                if weeks_diff < 1:
                    score -= 10  # Heavy penalty for consecutive weeks

            # Check minimum gap requirement
            if request.min_gap_between_occurrences:
                min_gap_days = request.min_gap_between_occurrences.days
                min_gap_ok = True
                for selected_date in selected_dates:
                    gap_days = abs((candidate_date - selected_date).days)
                    if gap_days < min_gap_days:
                        min_gap_ok = False
                        break
                if min_gap_ok:
                    score += 5
                else:
                    score -= 5

            # Respect max occurrences per week
            if request.max_occurrences_per_week:
                occurrences_this_week = sum(
                    1 for d in selected_dates
                    if self._get_week_number(d) == self._get_week_number(candidate_date)
                )
                if occurrences_this_week < request.max_occurrences_per_week:
                    score += 3
                else:
                    score -= 10

            # Update best date
            if score > best_score:
                best_score = score
                best_date = candidate_date

        return best_date

    def _get_week_number(self, date_to_check: date) -> int:
        """Get week number for a date (for comparison purposes)."""
        # Simple approximation - week number since start of year
        year_start = date(date_to_check.year, 1, 1)
        return (date_to_check - year_start).days // 7

    def generate_time_slots(
        self,
        schedule_date: date,
        request: SessionRequest,
        calendar_granularity: timedelta,
        timezone: ZoneInfo = ZoneInfo("UTC")
    ) -> List[Tuple[datetime, datetime]]:
        """
        Generate potential time slots for a given date.

        Args:
            schedule_date: The date to schedule on
            request: The session request
            calendar_granularity: Time slot granularity from calendar
            timezone: Timezone for time calculations

        Returns:
            List of (start_time, end_time) tuples
        """
        # Default time slots (9 AM to 5 PM)
        default_start_time = 9  # 9 AM
        default_end_time = 17   # 5 PM

        slots = []
        current_hour = default_start_time

        while current_hour + (request.duration.total_seconds() / 3600) <= default_end_time:
            start_time = datetime.combine(schedule_date, datetime.min.time(), tzinfo=timezone) + timedelta(hours=current_hour)
            end_time = start_time + request.duration

            # Check against preferred time slots
            if self._is_preferred_time_slot(start_time, end_time, request):
                slots.append((start_time, end_time))

            # Move to next possible time (accounting for duration)
            current_hour = current_hour + int(request.duration.total_seconds() / 3600) + 1  # Add duration hours + 1 hour gap

        return slots

    def _is_preferred_time_slot(
        self,
        start_time: datetime,
        end_time: datetime,
        request: SessionRequest
    ) -> bool:
        """Check if a time slot matches the request's preferences."""
        if not request.preferred_time_slots:
            return True  # No preference, any time slot works

        start_str = start_time.strftime("%H:%M")
        end_str = end_time.strftime("%H:%M")

        for preferred in request.preferred_time_slots:
            pref_start = preferred.get("start", "00:00")
            pref_end = preferred.get("end", "23:59")

            # Simple string comparison - in production, use proper time parsing
            if start_str >= pref_start and end_str <= pref_end:
                return True

        return False

    def calculate_priority_score(self, request: SessionRequest) -> int:
        """Calculate priority score for a request (longer classes = higher priority)."""
        duration_minutes = int(request.duration.total_seconds() / 60)

        if duration_minutes >= 180:  # 3+ hours
            return 4
        elif duration_minutes >= 120:  # 2+ hours
            return 3
        elif duration_minutes >= 90:   # 1.5+ hours
            return 2
        else:                          # < 1.5 hours
            return 1

    def sort_requests_by_priority(self, requests: List[SessionRequest]) -> List[SessionRequest]:
        """Sort requests by priority (longer classes first)."""
        return sorted(
            requests,
            key=lambda r: (self.calculate_priority_score(r), r.latest_date),
            reverse=True
        )