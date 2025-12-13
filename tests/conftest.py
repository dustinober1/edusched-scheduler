"""Pytest configuration and fixtures."""

import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from edusched.domain.calendar import Calendar, TimeWindow
from edusched.domain.resource import Resource
from edusched.domain.session_request import SessionRequest


@pytest.fixture
def utc_tz():
    """UTC timezone fixture."""
    return ZoneInfo("UTC")


@pytest.fixture
def sample_session_request(utc_tz):
    """Create a sample session request."""
    return SessionRequest(
        id="session_1",
        duration=timedelta(hours=1),
        number_of_occurrences=3,
        earliest_date=datetime(2024, 1, 1, tzinfo=utc_tz),
        latest_date=datetime(2024, 1, 31, tzinfo=utc_tz),
        cohort_id="cohort_1",
        modality="in_person",
    )


@pytest.fixture
def sample_resource():
    """Create a sample resource."""
    return Resource(
        id="room_1",
        resource_type="room",
        concurrency_capacity=1,
        attributes={"capacity": 30},
    )


@pytest.fixture
def sample_calendar(utc_tz):
    """Create a sample calendar."""
    return Calendar(
        id="calendar_1",
        timezone=utc_tz,
        timeslot_granularity=timedelta(minutes=15),
        availability_windows=[
            TimeWindow(
                start=datetime(2024, 1, 1, 8, 0, tzinfo=utc_tz),
                end=datetime(2024, 1, 31, 18, 0, tzinfo=utc_tz),
            )
        ],
    )
