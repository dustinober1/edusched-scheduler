"""Tests to verify project setup and basic imports."""

import pytest


def test_edusched_imports():
    """Test that core EduSched modules can be imported."""
    import edusched

    # Check version
    assert hasattr(edusched, "__version__")

    # Check domain model imports
    assert hasattr(edusched, "SessionRequest")
    assert hasattr(edusched, "Resource")
    assert hasattr(edusched, "Calendar")
    assert hasattr(edusched, "Assignment")
    assert hasattr(edusched, "Problem")
    assert hasattr(edusched, "Result")

    # Check constraint imports
    assert hasattr(edusched, "Constraint")
    assert hasattr(edusched, "NoOverlap")
    assert hasattr(edusched, "BlackoutDates")

    # Check objective imports
    assert hasattr(edusched, "Objective")
    assert hasattr(edusched, "SpreadEvenlyAcrossTerm")

    # Check solver imports
    assert hasattr(edusched, "SolverBackend")
    assert hasattr(edusched, "HeuristicSolver")

    # Check error imports
    assert hasattr(edusched, "ValidationError")
    assert hasattr(edusched, "BackendError")


def test_session_request_creation(sample_session_request):
    """Test that SessionRequest can be created."""
    assert sample_session_request.id == "session_1"
    assert sample_session_request.number_of_occurrences == 3
    assert sample_session_request.cohort_id == "cohort_1"


def test_resource_creation(sample_resource):
    """Test that Resource can be created."""
    assert sample_resource.id == "room_1"
    assert sample_resource.resource_type == "room"
    assert sample_resource.concurrency_capacity == 1


def test_calendar_creation(sample_calendar):
    """Test that Calendar can be created."""
    assert sample_calendar.id == "calendar_1"
    assert sample_calendar.timeslot_granularity.total_seconds() == 900  # 15 minutes


def test_session_request_validation(sample_session_request):
    """Test SessionRequest validation."""
    errors = sample_session_request.validate()
    assert len(errors) == 0, f"Unexpected validation errors: {errors}"


def test_session_request_validation_naive_datetime():
    """Test that naive datetimes are rejected."""
    from datetime import datetime, timedelta

    from edusched.domain.session_request import SessionRequest

    request = SessionRequest(
        id="test",
        duration=timedelta(hours=1),
        number_of_occurrences=1,
        earliest_date=datetime(2024, 1, 1),  # Naive datetime
        latest_date=datetime(2024, 1, 31),
    )

    errors = request.validate()
    assert len(errors) > 0
    assert any("timezone-aware" in str(e) for e in errors)


def test_resource_attribute_matching(sample_resource):
    """Test resource attribute matching."""
    # Matching requirements
    assert sample_resource.can_satisfy({"capacity": 30})

    # Non-matching requirements
    assert not sample_resource.can_satisfy({"capacity": 50})

    # Missing attribute
    assert not sample_resource.can_satisfy({"location": "building_a"})

    # Empty requirements
    assert sample_resource.can_satisfy({})


def test_calendar_availability(sample_calendar, utc_tz):
    """Test calendar availability checking."""
    from datetime import datetime

    # Within availability window
    assert sample_calendar.is_available(
        datetime(2024, 1, 15, 10, 0, tzinfo=utc_tz),
        datetime(2024, 1, 15, 11, 0, tzinfo=utc_tz),
    )

    # Outside availability window
    assert not sample_calendar.is_available(
        datetime(2024, 2, 1, 10, 0, tzinfo=utc_tz),
        datetime(2024, 2, 1, 11, 0, tzinfo=utc_tz),
    )
