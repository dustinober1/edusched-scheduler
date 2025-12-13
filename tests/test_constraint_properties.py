"""Property-based tests for constraint correctness."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import hypothesis.strategies as st
from hypothesis import given, settings

from edusched.constraints.base import ConstraintContext
from edusched.constraints.hard_constraints import NoOverlap, BlackoutDates, MaxPerDay, MinGapBetweenOccurrences, WithinDateRange, AttributeMatch
from edusched.domain.assignment import Assignment
from edusched.domain.calendar import Calendar, TimeWindow
from edusched.domain.problem import Problem, ProblemIndices
from edusched.domain.resource import Resource
from edusched.domain.session_request import SessionRequest


# Strategies for generating test data
@st.composite
def timezone_aware_datetimes(draw, min_year=2024, max_year=2025):
    """Generate timezone-aware datetimes."""
    year = draw(st.integers(min_value=min_year, max_value=max_year))
    month = draw(st.integers(min_value=1, max_value=12))
    day = draw(st.integers(min_value=1, max_value=28))
    hour = draw(st.integers(min_value=0, max_value=23))
    minute = draw(st.integers(min_value=0, max_value=59))

    tz = ZoneInfo("UTC")
    return datetime(year, month, day, hour, minute, tzinfo=tz)


@st.composite
def valid_assignments(draw):
    """Generate valid Assignment instances."""
    start = draw(timezone_aware_datetimes())
    duration = draw(st.timedeltas(min_value=timedelta(minutes=15), max_value=timedelta(hours=4)))

    return Assignment(
        request_id=draw(st.text(min_size=1, max_size=10, alphabet="abcdefghijklmnopqrstuvwxyz0123456789")),
        occurrence_index=draw(st.integers(min_value=0, max_value=10)),
        start_time=start,
        end_time=start + duration,
        assigned_resources=draw(st.dictionaries(
            keys=st.text(min_size=1, max_size=10),
            values=st.lists(st.text(min_size=1, max_size=10)),
            max_size=3
        )),
    )


class TestNoOverlapProperties:
    """Property-based tests for NoOverlap constraint."""

    @given(timezone_aware_datetimes(), st.text(min_size=1, max_size=20))
    def test_no_resource_double_booking(self, start_time, resource_id):
        """
        **Feature: edusched-scheduler, Property 8: No Resource Double-Booking**

        For any two assignments that use the same resource, the NoOverlap constraint
        should prevent scheduling them in overlapping time periods.

        **Validates: Requirements 3.1**
        """
        duration = timedelta(hours=1)

        # Create a constraint for the specific resource
        constraint = NoOverlap(resource_id)

        # Create mock context with resource lookup
        resource = Resource(id=resource_id, resource_type="test")
        context = ConstraintContext(
            problem=Problem(
                requests=[],
                resources=[resource],
                calendars=[],
                constraints=[]
            ),
            resource_lookup={resource_id: resource},
            calendar_lookup={},
            request_lookup={}
        )

        # Create first assignment with the resource
        assignment1 = Assignment(
            request_id="test1",
            occurrence_index=0,
            start_time=start_time,
            end_time=start_time + duration,
            assigned_resources={"test_type": [resource_id]}
        )

        # Case 1: Non-overlapping assignments should be valid
        non_overlapping = Assignment(
            request_id="test2",
            occurrence_index=0,
            start_time=assignment1.end_time,
            end_time=assignment1.end_time + duration,
            assigned_resources={"test_type": [resource_id]}
        )

        # Check non-overlapping case
        violation = constraint.check(non_overlapping, [assignment1], context)
        assert violation is None, "Non-overlapping assignments should not violate NoOverlap constraint"

        # Case 2: Overlapping assignments should be invalid
        overlapping = Assignment(
            request_id="test3",
            occurrence_index=0,
            start_time=assignment1.start_time + timedelta(minutes=15),  # Overlaps
            end_time=assignment1.start_time + timedelta(minutes=15) + duration,
            assigned_resources={"test_type": [resource_id]}
        )

        # Check overlapping case
        violation = constraint.check(overlapping, [assignment1], context)
        assert violation is not None, "Overlapping assignments should violate NoOverlap constraint"
        assert resource_id in str(violation) or violation.affected_resource_id == resource_id


class TestBlackoutDatesProperties:
    """Property-based tests for BlackoutDates constraint."""

    @given(timezone_aware_datetimes(), timezone_aware_datetimes(), st.text(min_size=1, max_size=10))
    def test_blackout_date_enforcement(self, start, end, calendar_id):
        """
        **Feature: edusched-scheduler, Property 9: Blackout Date Enforcement**

        For any assignment that falls within a blackout period, the BlackoutDates
        constraint should reject it. Assignments outside blackout periods should be accepted.

        **Validates: Requirements 3.2**
        """
        # Ensure start is before end
        if start >= end:
            start, end = end, start + timedelta(hours=1)

        # Create assignment
        assignment = Assignment(
            request_id="test_request",
            occurrence_index=0,
            start_time=start,
            end_time=end,
            assigned_resources={}
        )

        # Create calendar with blackout period
        blackout_start = start - timedelta(hours=1)
        blackout_end = end + timedelta(hours=1)

        calendar = Calendar(
            id=calendar_id,
            timezone=ZoneInfo("UTC"),
            blackout_periods=[TimeWindow(blackout_start, blackout_end)]
        )

        # Create mock context
        context = ConstraintContext(
            problem=Problem(
                requests=[],
                resources=[],
                calendars=[calendar],
                constraints=[]
            ),
            resource_lookup={},
            calendar_lookup={calendar_id: calendar},
            request_lookup={}
        )

        # Create constraint
        constraint = BlackoutDates(calendar_id)

        # Check that assignment in blackout period is rejected
        violation = constraint.check(assignment, [], context)
        assert violation is not None, "Assignment in blackout period should violate BlackoutDates constraint"
        assert "blackout" in str(violation).lower()

        # Now test with assignment outside blackout period
        later_assignment = Assignment(
            request_id="test_request2",
            occurrence_index=0,
            start_time=blackout_end + timedelta(hours=1),
            end_time=blackout_end + timedelta(hours=2),
            assigned_resources={}
        )

        violation = constraint.check(later_assignment, [], context)
        assert violation is None, "Assignment outside blackout period should not violate BlackoutDates constraint"


class TestMaxPerDayProperties:
    """Property-based tests for MaxPerDay constraint."""

    @given(valid_assignments(), st.integers(min_value=1, max_value=5), st.text(min_size=1, max_size=10))
    def test_daily_resource_limits(self, base_assignment, max_per_day, resource_id):
        """
        **Feature: edusched-scheduler, Property 10: Daily Resource Limits**

        For any resource with a daily limit, the MaxPerDay constraint should reject
        assignments that would exceed the limit for a given day.

        **Validates: Requirements 3.3**
        """
        # Create constraint
        constraint = MaxPerDay(resource_id, max_per_day)

        # Create mock context
        resource = Resource(id=resource_id, resource_type="test")
        context = ConstraintContext(
            problem=Problem(
                requests=[],
                resources=[resource],
                calendars=[],
                constraints=[]
            ),
            resource_lookup={resource_id: resource},
            calendar_lookup={},
            request_lookup={}
        )

        # Create existing assignments for the same day (max_per_day - 1)
        existing_assignments = []
        for i in range(max_per_day - 1):
            existing = Assignment(
                request_id=f"existing_{i}",
                occurrence_index=0,
                start_time=base_assignment.start_time.replace(hour=i),  # Same day, different hour
                end_time=base_assignment.start_time.replace(hour=i) + timedelta(hours=1),
                assigned_resources={"test_type": [resource_id]}
            )
            existing_assignments.append(existing)

        # New assignment should be accepted (at limit but not exceeding)
        new_assignment = Assignment(
            request_id="new_request",
            occurrence_index=0,
            start_time=base_assignment.start_time.replace(hour=max_per_day),
            end_time=base_assignment.start_time.replace(hour=max_per_day) + timedelta(hours=1),
            assigned_resources={"test_type": [resource_id]}
        )

        violation = constraint.check(new_assignment, existing_assignments, context)
        assert violation is None, f"Assignment at limit ({max_per_day}) should not violate MaxPerDay constraint"

        # One more assignment should be rejected
        extra_assignment = Assignment(
            request_id="extra_request",
            occurrence_index=0,
            start_time=base_assignment.start_time.replace(hour=max_per_day + 1),
            end_time=base_assignment.start_time.replace(hour=max_per_day + 1) + timedelta(hours=1),
            assigned_resources={"test_type": [resource_id]}
        )

        violation = constraint.check(extra_assignment, existing_assignments + [new_assignment], context)
        assert violation is not None, "Assignment exceeding daily limit should violate MaxPerDay constraint"
        assert str(max_per_day) in str(violation)


class TestMinGapBetweenOccurrencesProperties:
    """Property-based tests for MinGapBetweenOccurrences constraint."""

    @given(timezone_aware_datetimes(), st.timedeltas(min_value=timedelta(minutes=15), max_value=timedelta(days=7)), st.text(min_size=1, max_size=10))
    def test_minimum_gap_maintenance(self, base_time, min_gap, request_id):
        """
        **Feature: edusched-scheduler, Property 11: Minimum Gap Maintenance**

        For any request with a minimum gap requirement, occurrences must be spaced
        at least the specified amount apart.

        **Validates: Requirements 3.4**
        """
        # Create constraint
        constraint = MinGapBetweenOccurrences(request_id, min_gap)

        # Create mock context
        request = SessionRequest(
            id=request_id,
            duration=timedelta(hours=1),
            number_of_occurrences=2,
            earliest_date=base_time,
            latest_date=base_time + timedelta(days=7)
        )
        context = ConstraintContext(
            problem=Problem(
                requests=[request],
                resources=[],
                calendars=[],
                constraints=[]
            ),
            resource_lookup={},
            calendar_lookup={},
            request_lookup={request_id: request}
        )

        # Existing assignment
        existing = Assignment(
            request_id=request_id,
            occurrence_index=0,
            start_time=base_time,
            end_time=base_time + timedelta(hours=1),
            assigned_resources={}
        )

        # New assignment with sufficient gap should be accepted
        new_assignment = Assignment(
            request_id=request_id,
            occurrence_index=1,
            start_time=existing.end_time + min_gap,
            end_time=existing.end_time + min_gap + timedelta(hours=1),
            assigned_resources={}
        )

        violation = constraint.check(new_assignment, [existing], context)
        assert violation is None, "Assignment with sufficient gap should not violate MinGapBetweenOccurrences constraint"

        # Assignment with insufficient gap should be rejected
        close_assignment = Assignment(
            request_id=request_id,
            occurrence_index=1,
            start_time=existing.end_time + min_gap - timedelta(minutes=1),  # Too close
            end_time=existing.end_time + min_gap - timedelta(minutes=1) + timedelta(hours=1),
            assigned_resources={}
        )

        violation = constraint.check(close_assignment, [existing], context)
        assert violation is not None, "Assignment with insufficient gap should violate MinGapBetweenOccurrences constraint"


class TestWithinDateRangeProperties:
    """Property-based tests for WithinDateRange constraint."""

    @given(timezone_aware_datetimes(), st.text(min_size=1, max_size=10))
    def test_date_boundary_compliance(self, earliest, request_id):
        """
        **Feature: edusched-scheduler, Property 12: Date Boundary Compliance**

        For any request with date boundaries, all assignments must fall within
        the specified earliest and latest dates.

        **Validates: Requirements 3.5**
        """
        # Create a date range that's at least a week long
        latest = earliest + timedelta(days=7)
        duration = timedelta(hours=1)

        # Create request
        request = SessionRequest(
            id=request_id,
            duration=duration,
            number_of_occurrences=1,
            earliest_date=earliest,
            latest_date=latest
        )

        # Create constraint
        constraint = WithinDateRange(request_id)

        # Create mock context
        context = ConstraintContext(
            problem=Problem(
                requests=[request],
                resources=[],
                calendars=[],
                constraints=[]
            ),
            resource_lookup={},
            calendar_lookup={},
            request_lookup={request_id: request}
        )

        # Assignment within range should be accepted
        valid_start = earliest + timedelta(days=3)  # Well within range
        valid_assignment = Assignment(
            request_id=request_id,
            occurrence_index=0,
            start_time=valid_start,
            end_time=valid_start + duration,
            assigned_resources={}
        )

        violation = constraint.check(valid_assignment, [], context)
        assert violation is None, "Assignment within date range should not violate WithinDateRange constraint"

        # Assignment before earliest should be rejected
        early_assignment = Assignment(
            request_id=request_id,
            occurrence_index=0,
            start_time=earliest - duration,
            end_time=earliest,
            assigned_resources={}
        )

        violation = constraint.check(early_assignment, [], context)
        assert violation is not None, "Assignment before earliest date should violate WithinDateRange constraint"

        # Assignment after latest should be rejected
        late_assignment = Assignment(
            request_id=request_id,
            occurrence_index=0,
            start_time=latest + timedelta(hours=1),
            end_time=latest + timedelta(hours=2),
            assigned_resources={}
        )

        violation = constraint.check(late_assignment, [], context)
        assert violation is not None, "Assignment after latest date should violate WithinDateRange constraint"


class TestAttributeMatchProperties:
    """Property-based tests for AttributeMatch constraint."""

    @given(st.dictionaries(
        keys=st.text(min_size=1, max_size=10),
        values=st.one_of(st.text(min_size=1, max_size=10), st.integers(min_value=1, max_value=100)),
        min_size=1,
        max_size=3
    ), st.text(min_size=1, max_size=10))
    def test_resource_attribute_satisfaction(self, required_attributes, request_id):
        """
        **Feature: edusched-scheduler, Property 26: Resource Attribute Satisfaction**

        For any request with attribute requirements, only resources whose attributes
        satisfy all requirements should be assigned.

        **Validates: Requirements 12.1, 12.2**
        """
        # Create request with attributes
        request = SessionRequest(
            id=request_id,
            duration=timedelta(hours=1),
            number_of_occurrences=1,
            earliest_date=datetime(2024, 1, 1, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 12, 31, tzinfo=ZoneInfo("UTC")),
            required_attributes=required_attributes
        )

        # Create constraint
        constraint = AttributeMatch(request_id)

        # Create mock context with matching and non-matching resources
        matching_resource = Resource(
            id="matching",
            resource_type="test",
            attributes=required_attributes.copy()  # Exact match
        )

        # Non-matching resource (missing or different attributes)
        non_matching_resource = Resource(
            id="non_matching",
            resource_type="test",
            attributes={"different": "attributes"}
        )

        context = ConstraintContext(
            problem=Problem(
                requests=[request],
                resources=[matching_resource, non_matching_resource],
                calendars=[],
                constraints=[]
            ),
            resource_lookup={
                "matching": matching_resource,
                "non_matching": non_matching_resource
            },
            calendar_lookup={},
            request_lookup={request_id: request}
        )

        # Assignment with matching resource should be accepted
        valid_assignment = Assignment(
            request_id=request_id,
            occurrence_index=0,
            start_time=datetime(2024, 6, 1, 10, 0, tzinfo=ZoneInfo("UTC")),
            end_time=datetime(2024, 6, 1, 11, 0, tzinfo=ZoneInfo("UTC")),
            assigned_resources={"test_type": ["matching"]}
        )

        violation = constraint.check(valid_assignment, [], context)
        assert violation is None, "Assignment with matching resource should not violate AttributeMatch constraint"

        # Assignment with non-matching resource should be rejected
        invalid_assignment = Assignment(
            request_id=request_id,
            occurrence_index=0,
            start_time=datetime(2024, 6, 2, 10, 0, tzinfo=ZoneInfo("UTC")),
            end_time=datetime(2024, 6, 2, 11, 0, tzinfo=ZoneInfo("UTC")),
            assigned_resources={"test_type": ["non_matching"]}
        )

        violation = constraint.check(invalid_assignment, [], context)
        assert violation is not None, "Assignment with non-matching resource should violate AttributeMatch constraint"
        assert "attribute" in str(violation).lower()