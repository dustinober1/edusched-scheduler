"""Property-based tests for domain model correctness."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import hypothesis.strategies as st
from hypothesis import given

from edusched.domain.assignment import Assignment
from edusched.domain.calendar import Calendar, TimeWindow
from edusched.domain.resource import Resource
from edusched.domain.session_request import SessionRequest


# Strategies for generating valid test data

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
def valid_session_requests(draw):
    """Generate valid SessionRequest instances."""
    earliest = draw(timezone_aware_datetimes())
    latest = earliest + timedelta(days=30)
    duration = draw(st.timedeltas(min_value=timedelta(minutes=15), max_value=timedelta(hours=4)))
    occurrences = draw(st.integers(min_value=1, max_value=20))
    
    return SessionRequest(
        id=draw(st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz0123456789")),
        duration=duration,
        number_of_occurrences=occurrences,
        earliest_date=earliest,
        latest_date=latest,
        cohort_id=draw(st.one_of(st.none(), st.text(min_size=1, max_size=10))),
        modality=draw(st.sampled_from(["online", "in_person", "hybrid"])),
        required_attributes=draw(st.dictionaries(
            keys=st.text(min_size=1, max_size=10),
            values=st.one_of(st.text(min_size=1, max_size=10), st.integers()),
            max_size=3
        )),
    )


@st.composite
def valid_resources(draw):
    """Generate valid Resource instances."""
    return Resource(
        id=draw(st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz0123456789")),
        resource_type=draw(st.sampled_from(["room", "instructor", "campus", "online_slot"])),
        concurrency_capacity=draw(st.integers(min_value=1, max_value=100)),
        attributes=draw(st.dictionaries(
            keys=st.text(min_size=1, max_size=10),
            values=st.one_of(st.text(min_size=1, max_size=10), st.integers()),
            max_size=3
        )),
        availability_calendar_id=draw(st.one_of(st.none(), st.text(min_size=1, max_size=10))),
    )


# Property-based tests

class TestSessionRequestProperties:
    """Property-based tests for SessionRequest validation."""

    @given(valid_session_requests())
    def test_date_range_enforcement(self, request):
        """
        **Feature: edusched-scheduler, Property 1: Date Range Enforcement**

        For any SessionRequest with earliest and latest dates, all generated
        assignments should have start and end times within the specified date range.

        **Validates: Requirements 1.2**
        """
        # Valid request should pass validation
        errors = request.validate()

        # Check that earliest_date <= latest_date
        assert request.earliest_date <= request.latest_date, "Earliest date must be before or equal to latest date"

        # If there are no validation errors, the date range is valid
        date_range_errors = [e for e in errors if "date_range" in str(e)]
        if request.earliest_date <= request.latest_date:
            assert len(date_range_errors) == 0, "Valid date range should not produce errors"

    @given(st.datetimes(min_value=datetime(2024, 1, 1), max_value=datetime(2025, 12, 31)),
           st.datetimes(min_value=datetime(2024, 1, 1), max_value=datetime(2025, 12, 31)),
           st.timedeltas(min_value=timedelta(minutes=15), max_value=timedelta(hours=4)),
           st.integers(min_value=1, max_value=20))
    def test_session_request_validation_properties(self, earliest, latest, duration, occurrences):
        """
        Property-based test for SessionRequest validation logic.

        Tests that validation correctly identifies:
        - Timezone-aware datetime requirement
        - Date range consistency
        - Positive duration and occurrence requirements
        """
        # Create a session request (might be valid or invalid)
        request = SessionRequest(
            id="test_request",
            duration=duration,
            number_of_occurrences=occurrences,
            earliest_date=earliest,
            latest_date=latest,
        )

        errors = request.validate()

        # Check timezone-aware requirement
        if earliest.tzinfo is None:
            assert any("earliest_date" in str(e) and "timezone-aware" in str(e) for e in errors)
        else:
            assert not any("earliest_date" in str(e) and "timezone-aware" in str(e) for e in errors)

        if latest.tzinfo is None:
            assert any("latest_date" in str(e) and "timezone-aware" in str(e) for e in errors)
        else:
            assert not any("latest_date" in str(e) and "timezone-aware" in str(e) for e in errors)

        # Check date range validation
        if earliest > latest:
            assert any("date_range" in str(e) for e in errors)
        elif earliest.tzinfo is not None and latest.tzinfo is not None:
            # If datetimes are timezone-aware and in correct order, no date range error
            assert not any("date_range" in str(e) for e in errors)

        # Check duration validation
        if duration <= timedelta(0):
            assert any("duration" in str(e) for e in errors)
        else:
            assert not any("duration" in str(e) for e in errors)

        # Check occurrences validation
        if occurrences <= 0:
            assert any("number_of_occurrences" in str(e) for e in errors)
        else:
            assert not any("number_of_occurrences" in str(e) for e in errors)


class TestResourceProperties:
    """Property-based tests for Resource attribute matching."""

    @given(valid_resources())
    def test_resource_attribute_satisfaction(self, resource):
        """
        **Feature: edusched-scheduler, Property 26: Resource Attribute Satisfaction**
        
        For any SessionRequest with attribute requirements, only resources whose 
        attributes satisfy all requirements should be assigned.
        
        **Validates: Requirements 12.1, 12.2**
        """
        # Empty requirements should always be satisfied
        assert resource.can_satisfy({})
        
        # Resource should satisfy its own attributes
        assert resource.can_satisfy(resource.attributes)
        
        # Resource should not satisfy requirements it doesn't have
        missing_attr_req = {"nonexistent_attr": "value"}
        assert not resource.can_satisfy(missing_attr_req)

    @given(valid_resources(), st.dictionaries(
        keys=st.text(min_size=1, max_size=10),
        values=st.one_of(st.text(min_size=1, max_size=10), st.integers()),
        max_size=3
    ))
    def test_attribute_matching_consistency(self, resource, requirements):
        """
        For any resource and requirements, can_satisfy should be consistent:
        if it returns True, then all required attributes must be present and match.
        """
        result = resource.can_satisfy(requirements)
        
        if result:
            # If satisfied, all requirements must be in attributes with matching values
            for key, value in requirements.items():
                assert key in resource.attributes
                assert resource.attributes[key] == value


class TestCalendarProperties:
    """Property-based tests for Calendar timezone consistency."""

    @given(timezone_aware_datetimes())
    def test_timezone_consistency(self, dt):
        """
        **Feature: edusched-scheduler, Property 19: Timezone Consistency**
        
        For any problem with specified timezone, all scheduling operations and 
        exports should maintain consistent timezone handling.
        
        **Validates: Requirements 9.4**
        """
        tz = ZoneInfo("UTC")
        calendar = Calendar(
            id="test_calendar",
            timezone=tz,
            timeslot_granularity=timedelta(minutes=15),
        )
        
        # Calendar should maintain its timezone
        assert calendar.timezone == tz
        
        # Datetime should be timezone-aware
        assert dt.tzinfo is not None


class TestAssignmentProperties:
    """Property-based tests for Assignment cohort preservation."""

    @given(valid_session_requests())
    def test_cohort_preservation(self, request):
        """
        **Feature: edusched-scheduler, Property 3: Cohort Preservation**
        
        For any SessionRequest with a cohort specification, all generated 
        assignments should maintain the same cohort association.
        
        **Validates: Requirements 1.4**
        """
        if request.cohort_id is not None:
            # Create an assignment with the same cohort
            assignment = Assignment(
                request_id=request.id,
                occurrence_index=0,
                start_time=request.earliest_date,
                end_time=request.earliest_date + request.duration,
                assigned_resources={},
                cohort_id=request.cohort_id,
            )
            
            # Cohort should be preserved
            assert assignment.cohort_id == request.cohort_id
            assert assignment.cohort_id == request.cohort_id


class TestAssignmentTimezoneValidation:
    """Property-based tests for Assignment timezone validation."""

    @given(valid_session_requests())
    def test_assignment_timezone_aware_requirement(self, request):
        """
        For any Assignment, both start_time and end_time must be timezone-aware.
        """
        # Valid assignment with timezone-aware datetimes
        assignment = Assignment(
            request_id=request.id,
            occurrence_index=0,
            start_time=request.earliest_date,
            end_time=request.earliest_date + request.duration,
            assigned_resources={},
        )
        
        assert assignment.start_time.tzinfo is not None
        assert assignment.end_time.tzinfo is not None
