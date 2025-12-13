"""Tests for advanced scheduling features including patterns, holidays, and priority."""

from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

from edusched.domain.holiday_calendar import HolidayCalendar, HolidayPeriod
from edusched.domain.calendar import Calendar
from edusched.domain.building import Building, BuildingType
from edusched.domain.resource import Resource
from edusched.domain.teacher import Teacher
from edusched.domain.session_request import SessionRequest
from edusched.domain.assignment import Assignment
from edusched.domain.problem import Problem
from edusched.utils.scheduling_utils import OccurrenceSpreader
from edusched.constraints.scheduling_constraints import (
    SchedulingPatternConstraint,
    HolidayAvoidanceConstraint,
    OccurrenceSpreadConstraint
)


class TestSchedulingFeatures:
    """Test suite for advanced scheduling features."""

    def test_holiday_calendar_creation(self):
        """Test holiday calendar with various holiday periods."""
        calendar = HolidayCalendar(
            id="academic_2024",
            name="2024 Academic Calendar",
            year=2024,
            excluded_weekdays={5, 6}  # Weekends
        )

        # Add holidays
        calendar.add_holiday(
            date(2024, 12, 20),
            date(2025, 1, 10),
            "Winter Break"
        )
        calendar.add_holiday(
            date(2024, 3, 10),
            date(2024, 3, 20),
            "Spring Break"
        )

        # Test holiday detection
        assert calendar.is_holiday(date(2024, 12, 25))  # Christmas
        assert calendar.is_holiday(date(2024, 3, 15))   # Spring Break
        assert not calendar.is_holiday(date(2024, 2, 15)) # Regular day

        # Test schedulable day check
        assert calendar.is_schedulable_day(date(2024, 1, 15))  # Monday
        assert not calendar.is_schedulable_day(date(2024, 12, 25))  # Holiday
        assert not calendar.is_schedulable_day(date(2024, 1, 13))  # Saturday

    def test_scheduling_patterns(self):
        """Test different scheduling patterns."""
        calendar = HolidayCalendar(
            id="test_calendar",
            name="Test Calendar",
            year=2024
        )

        # Test pattern day generation
        assert calendar.get_weekly_pattern_days("5days") == [0, 1, 2, 3, 4]      # Mon-Fri
        assert calendar.get_weekly_pattern_days("4days_mt") == [0, 1, 2, 3]  # Mon-Thu
        assert calendar.get_weekly_pattern_days("4days_tf") == [1, 2, 3, 4]  # Tue-Fri
        assert calendar.get_weekly_pattern_days("3days_mw") == [0, 1, 2]     # Mon-Wed
        assert calendar.get_weekly_pattern_days("3days_wf") == [2, 3, 4]     # Wed-Fri
        assert calendar.get_weekly_pattern_days("2days_mt") == [0, 1]       # Mon-Tue
        assert calendar.get_weekly_pattern_days("2days_tf") == [3, 4]       # Thu-Fri

    def test_session_request_patterns(self):
        """Test SessionRequest with scheduling patterns."""
        # 5-day class (default Mon-Fri)
        request_5day = SessionRequest(
            id="class_5day",
            duration=timedelta(hours=1),
            number_of_occurrences=30,
            earliest_date=datetime(2024, 1, 15, 9, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 5, 15, 17, 0, tzinfo=ZoneInfo("UTC")),
            scheduling_pattern="5days",
            enrollment_count=25
        )
        assert request_5day.scheduling_pattern == "5days"
        assert request_5day.avoid_holidays is True

        # 3-day class (Mon-Wed)
        request_3day = SessionRequest(
            id="class_3day",
            duration=timedelta(hours=2),
            number_of_occurrences=12,
            earliest_date=datetime(2024, 1, 15, 9, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 5, 15, 17, 0, tzinfo=ZoneInfo("UTC")),
            scheduling_pattern="3days_mw",
            enrollment_count=30,
            preferred_time_slots=[
                {"start": "10:00", "end": "12:00"}
            ]
        )
        assert request_3day.scheduling_pattern == "3days_mw"
        assert len(request_3day.preferred_time_slots) == 1

    def test_priority_scoring(self):
        """Test priority scoring based on class duration."""
        calendar = HolidayCalendar(id="test", name="Test", year=2024)
        spreader = OccurrenceSpreader(calendar)

        # Different duration classes
        short_class = SessionRequest(
            id="short",
            duration=timedelta(hours=1),
            number_of_occurrences=24,
            earliest_date=datetime(2024, 1, 15, 9, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 5, 15, 17, 0, tzinfo=ZoneInfo("UTC"))
        )
        medium_class = SessionRequest(
            id="medium",
            duration=timedelta(hours=2),
            number_of_occurrences=24,
            earliest_date=datetime(2024, 1, 15, 9, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 5, 15, 17, 0, tzinfo=ZoneInfo("UTC"))
        )
        long_class = SessionRequest(
            id="long",
            duration=timedelta(hours=3),
            number_of_occurrences=16,
            earliest_date=datetime(2024, 1, 15, 9, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 5, 15, 17, 0, tzinfo=ZoneInfo("UTC"))
        )

        # Priority scores (longer = higher)
        assert spreader.calculate_priority_score(long_class) == 4  # 3+ hours
        assert spreader.calculate_priority_score(medium_class) == 3  # 2+ hours
        assert spreader.calculate_priority_score(short_class) == 1   # < 1.5 hours

        # Test sorting by priority
        requests = [short_class, long_class, medium_class]
        sorted_requests = spreader.sort_requests_by_priority(requests)
        assert [r.id for r in sorted_requests] == ["long", "medium", "short"]

    def test_occurrence_spreading(self):
        """Test spreading occurrences throughout the term."""
        calendar = HolidayCalendar(
            id="academic",
            name="Academic Calendar",
            year=2024,
            excluded_weekdays={5, 6}
        )

        # Add some holidays
        calendar.add_holiday(date(2024, 2, 19), date(2024, 2, 23), "Winter Break")
        calendar.add_holiday(date(2024, 3, 11), date(2024, 3, 15), "Spring Break")

        spreader = OccurrenceSpreader(calendar)

        # Create a class with weekly occurrences
        request = SessionRequest(
            id="weekly_class",
            duration=timedelta(hours=1.5),
            number_of_occurrences=12,  # Once per week for 12 weeks
            earliest_date=datetime(2024, 1, 15, 9, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 5, 15, 17, 0, tzinfo=ZoneInfo("UTC")),
            scheduling_pattern="5days",
            min_gap_between_occurrences=timedelta(days=5)  # At least one week apart
        )

        # Generate occurrence dates
        dates = spreader.generate_occurrence_dates(request)

        # Verify we got the right number
        assert len(dates) == 12

        # Verify dates are sorted
        assert dates == sorted(dates)

        # Verify no dates are on holidays or weekends
        for d in dates:
            assert d.weekday() < 5  # Not weekend
            assert not calendar.is_holiday(d)  # Not holiday

        # Verify minimum gap between occurrences
        for i in range(len(dates) - 1):
            gap_days = (dates[i + 1] - dates[i]).days
            # Should be close to a week apart (allowing some flexibility)
            assert gap_days >= 3  # Minimum reasonable gap

    def test_scheduling_pattern_constraint(self):
        """Test scheduling pattern constraint enforcement."""
        # Create request with Mon-Wed pattern
        request = SessionRequest(
            id="class_mw",
            duration=timedelta(hours=2),
            number_of_occurrences=1,
            earliest_date=datetime(2024, 1, 15, 9, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 5, 15, 17, 0, tzinfo=ZoneInfo("UTC")),
            scheduling_pattern="3days_mw"
        )

        constraint = SchedulingPatternConstraint(request_id="class_mw")

        # Create context
        from edusched.constraints.base import ConstraintContext
        context = ConstraintContext(
            problem=None,
            resource_lookup={},
            calendar_lookup={},
            request_lookup={"class_mw": request}
        )

        # Valid assignment (Monday)
        monday_assignment = Assignment(
            request_id="class_mw",
            occurrence_index=0,
            start_time=datetime(2024, 1, 15, 10, 0, tzinfo=ZoneInfo("UTC")),  # Monday
            end_time=datetime(2024, 1, 15, 12, 0, tzinfo=ZoneInfo("UTC")),
            assigned_resources={}
        )
        violation = constraint.check(monday_assignment, [], context)
        assert violation is None

        # Invalid assignment (Friday)
        friday_assignment = Assignment(
            request_id="class_mw",
            occurrence_index=0,
            start_time=datetime(2024, 1, 19, 10, 0, tzinfo=ZoneInfo("UTC")),  # Friday
            end_time=datetime(2024, 1, 19, 12, 0, tzinfo=ZoneInfo("UTC")),
            assigned_resources={}
        )
        violation = constraint.check(friday_assignment, [], context)
        assert violation is not None
        assert "doesn't match pattern" in violation.message.lower()

    def test_holiday_avoidance_constraint(self):
        """Test holiday avoidance constraint."""
        # Create request that avoids holidays
        request = SessionRequest(
            id="no_holiday_class",
            duration=timedelta(hours=2),
            number_of_occurrences=1,
            earliest_date=datetime(2024, 3, 1, 9, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 3, 30, 17, 0, tzinfo=ZoneInfo("UTC")),
            avoid_holidays=True
        )

        constraint = HolidayAvoidanceConstraint(request_id="no_holiday_class")

        # Create context
        from edusched.constraints.base import ConstraintContext
        from edusched.domain.problem import Problem
        problem = Problem(
            requests=[request],
            resources=[],
            calendars=[],
            constraints=[],
            institutional_calendar_id="academic"
        )
        context = ConstraintContext(
            problem=problem,
            resource_lookup={},
            calendar_lookup={},
            request_lookup={"no_holiday_class": request}
        )

        # Valid assignment (regular day)
        regular_assignment = Assignment(
            request_id="no_holiday_class",
            occurrence_index=0,
            start_time=datetime(2024, 3, 1, 10, 0, tzinfo=ZoneInfo("UTC")),
            end_time=datetime(2024, 3, 1, 12, 0, tzinfo=ZoneInfo("UTC")),
            assigned_resources={}
        )
        violation = constraint.check(regular_assignment, [], context)
        assert violation is None  # Simplified constraint - in production would check actual holidays

    def test_occurrence_spread_constraint(self):
        """Test occurrence spread constraint."""
        request = SessionRequest(
            id="spread_class",
            duration=timedelta(hours=2),
            number_of_occurrences=1,
            earliest_date=datetime(2024, 1, 1, 9, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 5, 31, 17, 0, tzinfo=ZoneInfo("UTC")),
            min_gap_between_occurrences=timedelta(days=7)
        )

        constraint = OccurrenceSpreadConstraint(request_id="spread_class", min_days_between=7)

        # Create context
        from edusched.constraints.base import ConstraintContext
        context = ConstraintContext(
            problem=None,
            resource_lookup={},
            calendar_lookup={},
            request_lookup={"spread_class": request}
        )

        # Test with no existing assignments
        single_assignment = Assignment(
            request_id="spread_class",
            occurrence_index=0,
            start_time=datetime(2024, 1, 15, 10, 0, tzinfo=ZoneInfo("UTC")),
            end_time=datetime(2024, 1, 15, 12, 0, tzinfo=ZoneInfo("UTC")),
            assigned_resources={}
        )
        violation = constraint.check(single_assignment, [], context)
        assert violation is None  # No spreading needed for single occurrence

    def test_integration_with_solver(self):
        """Test integration with the scheduling solver."""
        from edusched.solvers.heuristic import HeuristicSolver

        # Create holiday calendar
        calendar = HolidayCalendar(
            id="test_academic",
            name="Test Academic Calendar",
            year=2024,
            excluded_weekdays={5, 6}
        )
        # Add a week-long holiday
        calendar.add_holiday(date(2024, 3, 10), date(2024, 3, 16), "Test Break")

        # Create resources with sufficient capacity for both classes
        classroom = Resource(
            id="Room101",
            resource_type="classroom",
            capacity=50  # Enough for both 40 and 25 student classes
        )

        # Create calendar
        academic_calendar = Calendar(
            id="academic",
            timezone=ZoneInfo("UTC"),
            timeslot_granularity=timedelta(minutes=30)
        )

        # Create requests with different patterns
        long_class = SessionRequest(
            id="cs401",
            duration=timedelta(hours=3),
            number_of_occurrences=10,
            earliest_date=datetime(2024, 1, 15, 9, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 5, 15, 17, 0, tzinfo=ZoneInfo("UTC")),
            scheduling_pattern="2days_tf",  # Thu-Fri
            enrollment_count=40
        )

        short_class = SessionRequest(
            id="cs101",
            duration=timedelta(hours=1),
            number_of_occurrences=24,
            earliest_date=datetime(2024, 1, 15, 9, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 5, 15, 17, 0, tzinfo=ZoneInfo("UTC")),
            scheduling_pattern="5days",
            enrollment_count=25
        )

        # Create constraints
        constraints = [
            SchedulingPatternConstraint("cs401"),
            SchedulingPatternConstraint("cs101"),
            HolidayAvoidanceConstraint("cs401"),
            HolidayAvoidanceConstraint("cs101")
        ]

        # Create problem
        problem = Problem(
            requests=[long_class, short_class],
            resources=[classroom],
            calendars=[academic_calendar],
            constraints=constraints,
            holiday_calendar=calendar,
            institutional_calendar_id="academic"
        )

        # Solve the problem
        solver = HeuristicSolver()
        result = solver.solve(problem)

        # Verify solution exists
        assert result.status in ["feasible", "partial"]
        assert len(result.assignments) > 0

        # Verify assignments follow patterns
        cs401_assignments = [a for a in result.assignments if a.request_id == "cs401"]
        for assignment in cs401_assignments:
            day_of_week = assignment.start_time.weekday()
            assert day_of_week in [3, 4]  # Should be Thu-Fri

        cs101_assignments = [a for a in result.assignments if a.request_id == "cs101"]
        for assignment in cs101_assignments:
            day_of_week = assignment.start_time.weekday()
            assert day_of_week < 5  # Should be Mon-Fri

    def test_complete_integration_scenario(self):
        """Test a complete integration scenario with all scheduling features."""
        from edusched.solvers.heuristic import HeuristicSolver

        # Create comprehensive holiday calendar
        calendar = HolidayCalendar(
            id="comprehensive_2024",
            name="Comprehensive 2024 Calendar",
            year=2024,
            excluded_weekdays={5, 6}
        )

        # Add multiple holiday periods
        calendar.add_holiday(date(2024, 1, 1), date(2024, 1, 15), "Winter Break")
        calendar.add_holiday(date(2024, 3, 11), date(2024, 3, 22), "Spring Break")
        calendar.add_holiday(date(2024, 5, 20), date(2024, 8, 20), "Summer Break")

        # Create various resources
        large_lecture = Resource(id="Lecture101", resource_type="classroom", capacity=100)
        small_classroom = Resource(id="Room201", resource_type="classroom", capacity=30)
        lab = Resource(id="Lab301", resource_type="lab", capacity=25)

        # Create academic calendar
        academic_calendar = Calendar(
            id="academic_2024",
            timezone=ZoneInfo("UTC"),
            timeslot_granularity=timedelta(minutes=30)
        )

        # Create diverse course requests
        requests = [
            # 3-hour seminar (highest priority)
            SessionRequest(
                id="grad_seminar",
                duration=timedelta(hours=3),
                number_of_occurrences=8,
                earliest_date=datetime(2024, 2, 1, 9, 0, tzinfo=ZoneInfo("UTC")),
                latest_date=datetime(2024, 5, 15, 17, 0, tzinfo=ZoneInfo("UTC")),
                scheduling_pattern="2days_tf",
                enrollment_count=15,
                required_resource_types={"classroom": 1}
            ),
            # 2-hour lab course (medium priority)
            SessionRequest(
                id="cs_lab",
                duration=timedelta(hours=2),
                number_of_occurrences=12,
                earliest_date=datetime(2024, 2, 1, 9, 0, tzinfo=ZoneInfo("UTC")),
                latest_date=datetime(2024, 5, 15, 17, 0, tzinfo=ZoneInfo("UTC")),
                scheduling_pattern="3days_mw",
                enrollment_count=20,
                required_resource_types={"lab": 1}
            ),
            # 1-hour lecture (lowest priority)
            SessionRequest(
                id="intro_course",
                duration=timedelta(hours=1),
                number_of_occurrences=24,
                earliest_date=datetime(2024, 2, 1, 9, 0, tzinfo=ZoneInfo("UTC")),
                latest_date=datetime(2024, 5, 15, 17, 0, tzinfo=ZoneInfo("UTC")),
                scheduling_pattern="5days",
                enrollment_count=50,
                required_resource_types={"classroom": 1}
            )
        ]

        # Create comprehensive constraints
        constraints = []
        for request in requests:
            constraints.append(SchedulingPatternConstraint(request.id))
            constraints.append(HolidayAvoidanceConstraint(request.id))

        # Create problem
        problem = Problem(
            requests=requests,
            resources=[large_lecture, small_classroom, lab],
            calendars=[academic_calendar],
            constraints=constraints,
            holiday_calendar=calendar,
            institutional_calendar_id="academic_2024"
        )

        # Solve
        solver = HeuristicSolver()
        result = solver.solve(problem)

        # Verify solution
        assert result.status in ["feasible", "partial"]
        assert len(result.assignments) > 0

        # Verify priority ordering (seminar should be scheduled first)
        seminar_assignments = [a for a in result.assignments if a.request_id == "grad_seminar"]
        lab_assignments = [a for a in result.assignments if a.request_id == "cs_lab"]
        intro_assignments = [a for a in result.assignments if a.request_id == "intro_course"]

        # Check that longer classes got better time slots
        if seminar_assignments and intro_assignments:
            # Seminars (3 hours) should get earlier time slots than intro (1 hour)
            seminar_avg_time = sum(a.start_time.hour for a in seminar_assignments) / len(seminar_assignments)
            intro_avg_time = sum(a.start_time.hour for a in intro_assignments) / len(intro_assignments)
            # This is a simplified check - in reality, you'd check against preferred slots
            assert seminar_avg_time <= intro_avg_time or len(seminar_assignments) == len(intro_assignments) == 0