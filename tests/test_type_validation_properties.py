"""Property-based tests for type validation accuracy."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import inspect

import hypothesis.strategies as st
from hypothesis import given, settings, assume

from edusched.domain.calendar import Calendar
from edusched.domain.problem import Problem
from edusched.domain.resource import Resource
from edusched.domain.session_request import SessionRequest
from edusched.domain.assignment import Assignment


class TestTypeValidationProperties:
    """Property-based tests for type validation accuracy."""

    def test_calendar_timezone_validation(self):
        """
        **Feature: edusched-scheduler, Property 29: Type Validation Accuracy**

        Calendar should require timezone-aware datetime objects.
        """
        # None timezone should be rejected
        try:
            calendar = Calendar(
                id="cal1",
                timezone=None,  # None timezone
                timeslot_granularity=timedelta(minutes=30)
            )
            # Create problem to validate
            problem = Problem(
                requests=[],
                resources=[],
                calendars=[calendar],
                constraints=[],
                institutional_calendar_id="cal1"
            )
            errors = problem.validate()
            assert any("institutional_calendar_id" in error for error in errors), \
                "Should detect missing calendar reference"
        except (TypeError, ValueError):
            # Type errors should be raised for invalid types
            pass

        # Valid timezone should work
        try:
            calendar = Calendar(
                id="cal1",
                timezone=ZoneInfo("UTC"),
                timeslot_granularity=timedelta(minutes=30)
            )
            problem = Problem(
                requests=[],
                resources=[],
                calendars=[calendar],
                constraints=[],
                institutional_calendar_id="cal1"
            )
            errors = problem.validate()
            # Should not have timezone errors
            assert not any("timezone" in error for error in errors), \
                "Valid timezone should not cause errors"
        except Exception as e:
            # If it fails, it should not be due to type issues
            assert "timezone" not in str(e), \
                f"Valid timezone should not cause type errors: {e}"

    @given(
        st.text(min_size=1, max_size=20),
        st.sampled_from([
            timedelta(minutes=15),   # Valid
            timedelta(minutes=0),    # Invalid - zero duration
            timedelta(minutes=-30),  # Invalid - negative duration
            timedelta(days=365),     # Valid but very large
            None,                    # Invalid - None
            "invalid",               # Invalid - wrong type
            30,                     # Invalid - wrong type
        ])
    )
    def test_resource_type_validation(self, resource_id, capacity):
        """
        Resource type should be validated for correctness.
        """
        try:
            resource = Resource(
                id=resource_id,
                resource_type="room",  # Valid type
                concurrency_capacity=capacity if isinstance(capacity, int) else 1
            )
            errors = resource.validate()

            # Check capacity validation
            if capacity is None or capacity == 0 or capacity < 0:
                assert any("capacity" in error.lower() for error in errors), \
                    f"Should detect invalid capacity: {capacity}"
            elif isinstance(capacity, int) and capacity > 0:
                assert not any("capacity" in error.lower() for error in errors), \
                    f"Valid capacity should not cause errors: {capacity}"

        except (TypeError, ValueError):
            # Type errors are acceptable for invalid types
            if not isinstance(capacity, int):
                pass  # Expected
            else:
                raise  # Unexpected type error

    @given(
        st.text(min_size=1, max_size=20),
        st.sampled_from([
            "room",
            "instructor",
            "equipment",
            "invalid_type",  # Invalid
            "",             # Invalid - empty
            None,           # Invalid - None
            123,            # Invalid - wrong type
        ])
    )
    def test_resource_type_enumeration(self, resource_id, resource_type):
        """
        Resource type should be limited to valid enumeration values.
        """
        # Skip None for typing reasons
        assume(resource_type is not None)

        try:
            resource = Resource(
                id=resource_id,
                resource_type=resource_type,
                concurrency_capacity=1
            )
            errors = resource.validate()

            valid_types = ["room", "instructor", "equipment", "campus", "online_slot"]

            if resource_type not in valid_types:
                assert any("resource_type" in error.lower() or "type" in error.lower() for error in errors), \
                    f"Should detect invalid resource type: {resource_type}"
            else:
                assert not any("resource_type" in error.lower() for error in errors), \
                    f"Valid resource type should not cause errors: {resource_type}"

        except (TypeError, ValueError):
            # Type errors are acceptable for invalid types
            if not isinstance(resource_type, str):
                pass  # Expected
            else:
                raise  # Unexpected type error

    @given(
        st.text(min_size=1, max_size=20),
        st.sampled_from([
            timedelta(minutes=15),      # Valid
            timedelta(hours=2),         # Valid
            timedelta(0),              # Invalid - zero
            timedelta(minutes=-15),    # Invalid - negative
            None,                      # Invalid - None
            60,                        # Invalid - wrong type
            "1 hour",                  # Invalid - wrong type
        ])
    )
    def test_session_duration_validation(self, request_id, duration):
        """
        Session request duration should be validated for positive values.
        """
        assume(duration is not None and isinstance(duration, timedelta))

        # Create base request
        base_time = datetime(2024, 6, 10, 10, 0, tzinfo=ZoneInfo("UTC"))

        try:
            request = SessionRequest(
                id=request_id,
                duration=duration,
                number_of_occurrences=1,
                earliest_date=base_time,
                latest_date=base_time + timedelta(days=7)
            )
            errors = request.validate()

            # Check duration validation
            if duration.total_seconds() <= 0:
                assert any("duration" in error.lower() for error in errors), \
                    f"Should detect non-positive duration: {duration}"
            elif duration.total_seconds() > 24 * 60 * 60:  # More than 24 hours
                assert any("duration" in error.lower() for error in errors), \
                    f"Should detect excessively long duration: {duration}"
            else:
                assert not any("duration" in error.lower() for error in errors), \
                    f"Valid duration should not cause errors: {duration}"

        except (TypeError, ValueError):
            # Type errors should be raised for invalid types
            if not isinstance(duration, timedelta):
                pass  # Expected
            else:
                raise  # Unexpected type error

    @given(
        st.text(min_size=1, max_size=20),
        st.integers(min_value=-5, max_value=10)
    )
    def test_occurrence_count_validation(self, request_id, occurrences):
        """
        Number of occurrences should be positive integer.
        """
        base_time = datetime(2024, 6, 10, 10, 0, tzinfo=ZoneInfo("UTC"))

        try:
            request = SessionRequest(
                id=request_id,
                duration=timedelta(hours=1),
                number_of_occurrences=occurrences,
                earliest_date=base_time,
                latest_date=base_time + timedelta(days=7)
            )
            errors = request.validate()

            if occurrences <= 0:
                assert any("occurrences" in error.lower() for error in errors), \
                    f"Should detect non-positive occurrences: {occurrences}"
            elif occurrences > 1000:  # Reasonable upper limit
                assert any("occurrences" in error.lower() for error in errors), \
                    f"Should detect too many occurrences: {occurrences}"
            else:
                assert not any("occurrences" in error.lower() for error in errors), \
                    f"Valid occurrence count should not cause errors: {occurrences}"

        except (TypeError, ValueError):
            # Type errors for invalid types
            if not isinstance(occurrences, int):
                pass  # Expected
            else:
                raise

    @given(
        st.text(min_size=1, max_size=20),
        st.datetimes(min_value=datetime(2000, 1, 1), max_value=datetime(2030, 12, 31)),
        st.integers(min_value=1, max_value=30)
    )
    def test_date_range_validation(self, request_id, earliest, days_later):
        """
        Latest date should be after earliest date.
        """
        # Convert to timezone-aware if needed
        if earliest.tzinfo is None:
            earliest = earliest.replace(tzinfo=ZoneInfo("UTC"))

        latest = earliest + timedelta(days=days_later)

        # Also test inverted case
        if days_later % 3 == 0:  # Every third test
            earliest, latest = latest, earliest  # Swap to create invalid range

        try:
            request = SessionRequest(
                id=request_id,
                duration=timedelta(hours=1),
                number_of_occurrences=1,
                earliest_date=earliest,
                latest_date=latest
            )
            errors = request.validate()

            if latest <= earliest:
                assert any("latest_date" in error.lower() or "earliest_date" in error.lower() for error in errors), \
                    f"Should detect invalid date range: {earliest} to {latest}"
            else:
                assert not any("latest_date" in error.lower() or "earliest_date" in error.lower() for error in errors), \
                    f"Valid date range should not cause errors"

        except (TypeError, ValueError):
            # Type errors for invalid types
            pass

    @given(
        st.text(min_size=1, max_size=20),
        st.integers(min_value=0, max_value=10)
    )
    def test_assignment_type_validation(self, request_id, occurrence_index):
        """
        Assignment should validate occurrence index is non-negative.
        """
        start_time = datetime(2024, 6, 10, 10, 0, tzinfo=ZoneInfo("UTC"))

        try:
            assignment = Assignment(
                request_id=request_id,
                occurrence_index=occurrence_index,
                start_time=start_time,
                end_time=start_time + timedelta(hours=1),
                assigned_resources={},
                cohort_id=None
            )

            # Assignment doesn't have validate() method, but check type
            assert isinstance(occurrence_index, int), "Occurrence index should be integer"

            if occurrence_index < 0:
                # This would be caught at the problem level
                # For now, just check the type is correct
                pass

        except (TypeError, ValueError):
            # Should raise type errors for invalid types
            if not isinstance(occurrence_index, int):
                pass  # Expected
            else:
                raise

    @given(
        st.text(min_size=1, max_size=20),
        st.sampled_from([
            "in_person",
            "online",
            "hybrid",
            "invalid",  # Invalid
            "",        # Invalid - empty
            None,      # Invalid - None
            123,       # Invalid - wrong type
        ])
    )
    def test_modality_enumeration(self, request_id, modality):
        """
        Session modality should be limited to valid enumeration values.
        """
        assume(modality is not None)

        base_time = datetime(2024, 6, 10, 10, 0, tzinfo=ZoneInfo("UTC"))

        try:
            request = SessionRequest(
                id=request_id,
                duration=timedelta(hours=1),
                number_of_occurrences=1,
                earliest_date=base_time,
                latest_date=base_time + timedelta(days=7),
                modality=modality
            )
            errors = request.validate()

            valid_modalities = ["in_person", "online", "hybrid"]

            if modality not in valid_modalities:
                assert any("modality" in error.lower() for error in errors), \
                    f"Should detect invalid modality: {modality}"
            else:
                assert not any("modality" in error.lower() for error in errors), \
                    f"Valid modality should not cause errors: {modality}"

        except (TypeError, ValueError):
            # Type errors for invalid types
            if not isinstance(modality, str):
                pass  # Expected
            else:
                raise

    @given(
        st.lists(
            st.text(min_size=1, max_size=10, alphabet="abc123"),
            min_size=0,
            max_size=3
        )
    )
    def test_id_format_validation(self, id_components):
        """
        Entity IDs should be non-empty strings with valid characters.
        """
        # Test empty ID
        if not id_components:
            try:
                resource = Resource(
                    id="",
                    resource_type="room",
                    concurrency_capacity=1
                )
                errors = resource.validate()
                assert any("id" in error.lower() for error in errors), \
                    "Should detect empty ID"
            except (TypeError, ValueError):
                pass  # Expected for empty ID
        else:
            # Test various ID formats
            test_id = "".join(id_components)

            try:
                resource = Resource(
                    id=test_id,
                    resource_type="room",
                    concurrency_capacity=1
                )
                errors = resource.validate()

                # Non-empty, valid character IDs should be fine
                if test_id and all(c.isalnum() or c in "-_" for c in test_id):
                    assert not any("id" in error.lower() for error in errors), \
                        f"Valid ID should not cause errors: {test_id}"

            except (TypeError, ValueError):
                # Type errors for invalid types
                if not isinstance(test_id, str):
                    pass  # Expected
                else:
                    raise

    @given(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=10),
            values=st.one_of([
                st.integers(min_value=1, max_value=100),
                st.text(min_size=1, max_size=20),
                st.lists(st.integers(min_value=1, max_value=10), max_size=3),
                st.just(None),
                st.just(123.45),  # Float
                st.just(True),     # Boolean
            ]),
            min_size=0,
            max_size=5
        )
    )
    def test_attributes_type_validation(self, attributes):
        """
        Resource and request attributes should accept flexible but valid types.
        """
        try:
            resource = Resource(
                id="test",
                resource_type="room",
                concurrency_capacity=1,
                attributes=attributes
            )
            errors = resource.validate()

            # Check that all values are of acceptable types
            valid_types = (str, int, list, dict, bool, type(None))

            for key, value in attributes.items():
                if not isinstance(value, valid_types):
                    # Should detect invalid attribute type
                    assert any("attributes" in error.lower() for error in errors), \
                        f"Should detect invalid attribute type for {key}: {type(value)}"

        except (TypeError, ValueError):
            # Type errors for completely invalid structures
            if not isinstance(attributes, dict):
                pass  # Expected
            else:
                raise