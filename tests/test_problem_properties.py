"""Property-based tests for Problem validation and canonicalization."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import hypothesis.strategies as st
from hypothesis import given, settings

from edusched.domain.calendar import Calendar
from edusched.domain.problem import Problem
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
def calendars(draw):
    """Generate Calendar instances."""
    return Calendar(
        id=draw(st.text(min_size=1, max_size=10)),
        timezone=ZoneInfo("UTC"),
        timeslot_granularity=draw(st.timedeltas(min_value=timedelta(minutes=15), max_value=timedelta(hours=1))),
    )


@st.composite
def resources(draw):
    """Generate Resource instances."""
    calendar_list = draw(st.lists(calendars(), min_size=0, max_size=1))
    calendar_id = calendar_list[0].id if calendar_list else None

    return Resource(
        id=draw(st.text(min_size=1, max_size=10)),
        resource_type=draw(st.sampled_from(["room", "instructor", "campus", "online_slot"])),
        concurrency_capacity=draw(st.integers(min_value=1, max_value=100)),
        attributes=draw(st.dictionaries(
            keys=st.text(min_size=1, max_size=10),
            values=st.one_of(st.text(min_size=1, max_size=10), st.integers()),
            max_size=3
        )),
        availability_calendar_id=calendar_id,
    )


class TestProblemProperties:
    """Property-based tests for Problem validation and canonicalization."""

    @given(
        st.lists(valid_session_requests(), min_size=0, max_size=5),
        st.lists(resources(), min_size=0, max_size=5),
        st.lists(calendars(), min_size=0, max_size=5),
        st.text(min_size=1, max_size=10)
    )
    def test_validation_error_completeness(self, requests, resources, calendars, invalid_calendar_id):
        """
        **Feature: edusched-scheduler, Property 21: Validation Error Completeness**

        For any Problem with invalid references, the validate() method should
        identify all validation errors, including missing calendar references
        and invalid date ranges.

        **Validates: Requirements 10.1**
        """
        # Create a problem with potentially invalid references
        problem = Problem(
            requests=requests,
            resources=resources,
            calendars=calendars,
            constraints=[],
            objectives=[],
            institutional_calendar_id=invalid_calendar_id  # Might be invalid
        )

        errors = problem.validate()

        # Errors should contain all issues
        calendar_ids = {cal.id for cal in calendars}

        # Check for institutional calendar error
        if invalid_calendar_id not in calendar_ids:
            assert any(f"institutional_calendar_id '{invalid_calendar_id}'" in e for e in errors), \
                "Should report missing institutional calendar"

        # Check for resource calendar errors
        for resource in resources:
            if resource.availability_calendar_id and resource.availability_calendar_id not in calendar_ids:
                assert any(f"Resource '{resource.id}'" in e and "unknown calendar" in e for e in errors), \
                    f"Should report missing calendar for resource {resource.id}"

        # Check for request validation errors (already covered by SessionRequest tests)
        # All error messages should be informative
        for error in errors:
            assert len(error) > 10, f"Error message should be descriptive: {error}"

    @given(
        st.lists(valid_session_requests(), min_size=3, max_size=10),
        st.lists(resources(), min_size=3, max_size=10),
        st.lists(calendars(), min_size=3, max_size=10)
    )
    def test_input_canonicalization(self, requests, resources, calendars):
        """
        **Feature: edusched-scheduler, Property 24: Input Canonicalization**

        For any Problem, the canonicalize() method should sort all collections
        by ID to ensure deterministic processing.

        **Validates: Requirements 11.6**
        """
        # Create problem with unsorted inputs
        problem = Problem(
            requests=requests,
            resources=resources,
            calendars=calendars,
            constraints=[],
            objectives=[]
        )

        # Store original order
        original_request_ids = [r.id for r in problem.requests]
        original_resource_ids = [r.id for r in problem.resources]
        original_calendar_ids = [c.id for c in problem.calendars]

        # Canonicalize
        problem.canonicalize()

        # Check that all lists are sorted by ID
        assert problem.requests == sorted(problem.requests, key=lambda r: r.id), \
            "Requests should be sorted by ID"
        assert problem.resources == sorted(problem.resources, key=lambda r: r.id), \
            "Resources should be sorted by ID"
        assert problem.calendars == sorted(problem.calendars, key=lambda c: c.id), \
            "Calendars should be sorted by ID"

        # Check that sorted order is different from original (unless already sorted)
        sorted_request_ids = sorted(original_request_ids)
        sorted_resource_ids = sorted(original_resource_ids)
        sorted_calendar_ids = sorted(original_calendar_ids)

        assert [r.id for r in problem.requests] == sorted_request_ids, \
            "Requests should be in sorted order by ID"
        assert [r.id for r in problem.resources] == sorted_resource_ids, \
            "Resources should be in sorted order by ID"
        assert [c.id for c in problem.calendars] == sorted_calendar_ids, \
            "Calendars should be in sorted order by ID"

    @given(
        valid_session_requests(),
        st.lists(timezone_aware_datetimes(), min_size=0, max_size=5),
        st.integers(min_value=1, max_value=10)
    )
    def test_canonicalize_with_locked_assignments(self, request, start_times, count):
        """
        Locked assignments should be sorted by (request_id, occurrence_index).
        """
        from edusched.domain.assignment import Assignment

        # Create locked assignments
        locked_assignments = []
        for i in range(count):
            if start_times:
                start = start_times[i % len(start_times)]
            else:
                start = request.earliest_date + timedelta(days=i)

            assignment = Assignment(
                request_id=request.id,
                occurrence_index=count - i - 1,  # Reverse order
                start_time=start,
                end_time=start + request.duration,
                cohort_id=request.cohort_id,
                assigned_resources={}
            )
            locked_assignments.append(assignment)

        # Create problem
        problem = Problem(
            requests=[request],
            resources=[],
            calendars=[],
            constraints=[],
            locked_assignments=locked_assignments
        )

        # Store original order
        original_order = [(a.request_id, a.occurrence_index) for a in problem.locked_assignments]

        # Canonicalize
        problem.canonicalize()

        # Check sorting
        expected_order = sorted(original_order, key=lambda x: (x[0], x[1]))
        actual_order = [(a.request_id, a.occurrence_index) for a in problem.locked_assignments]

        assert actual_order == expected_order, \
            f"Locked assignments should be sorted by (request_id, occurrence_index), got {actual_order}"

    @given(
        st.lists(valid_session_requests(), min_size=1, max_size=5),
        st.lists(resources(), min_size=1, max_size=5),
        st.lists(calendars(), min_size=1, max_size=5),
        st.text(min_size=1, max_size=10)
    )
    def test_build_indices_completeness(self, requests, resources, calendars, institution_calendar_id):
        """
        build_indices() should create all necessary lookup structures.
        """
        # Create a valid problem
        calendar_ids = [c.id for c in calendars]
        if institution_calendar_id not in calendar_ids:
            institution_calendar_id = calendar_ids[0] if calendar_ids else None

        problem = Problem(
            requests=requests,
            resources=resources,
            calendars=calendars,
            constraints=[],
            objectives=[],
            institutional_calendar_id=institution_calendar_id
        )

        # Ensure all resource calendar references are valid
        for resource in resources:
            if resource.availability_calendar_id not in calendar_ids:
                resource.availability_calendar_id = calendar_ids[0] if calendar_ids else None

        # Build indices
        indices = problem.build_indices()

        # Check all lookups exist
        assert indices.resource_lookup is not None, "resource_lookup should be created"
        assert indices.calendar_lookup is not None, "calendar_lookup should be created"
        assert indices.request_lookup is not None, "request_lookup should be created"
        assert indices.resources_by_type is not None, "resources_by_type should be created"
        assert indices.qualified_resources is not None, "qualified_resources should be created"
        assert indices.time_occupancy_maps is not None, "time_occupancy_maps should be created"
        assert indices.locked_intervals is not None, "locked_intervals should be created"

        # Check lookups contain all items
        for request in requests:
            assert request.id in indices.request_lookup, f"Request {request.id} should be in lookup"
            assert request.id in indices.qualified_resources, f"Request {request.id} should have qualified resources"

        for resource in resources:
            assert resource.id in indices.resource_lookup, f"Resource {resource.id} should be in lookup"
            assert resource.id in indices.time_occupancy_maps, f"Resource {resource.id} should have occupancy map"
            assert resource.id in indices.locked_intervals, f"Resource {resource.id} should have locked intervals"

        for calendar in calendars:
            assert calendar.id in indices.calendar_lookup, f"Calendar {calendar.id} should be in lookup"

        # Check resources_by_type grouping
        for resource in resources:
            assert resource.resource_type in indices.resources_by_type, \
                f"Resource type {resource.resource_type} should be grouped"
            assert resource in indices.resources_by_type[resource.resource_type], \
                f"Resource {resource.id} should be in its type group"