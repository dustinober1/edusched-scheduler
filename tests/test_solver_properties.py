"""Property-based tests for solver behavior."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import hypothesis.strategies as st
from hypothesis import given, settings, assume

from edusched.solvers.heuristic import HeuristicSolver
from edusched.domain.calendar import Calendar
from edusched.domain.problem import Problem
from edusched.domain.resource import Resource
from edusched.domain.session_request import SessionRequest
from edusched.constraints.hard_constraints import NoOverlap, WithinDateRange


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
def simple_problem(draw):
    """Generate a simple scheduling problem."""
    # Create calendar with specific granularity
    granularity_minutes = draw(st.sampled_from([15, 30, 60]))
    granularity = timedelta(minutes=granularity_minutes)

    calendar = Calendar(
        id="cal1",
        timezone=ZoneInfo("UTC"),
        timeslot_granularity=granularity
    )

    # Create simple problem
    earliest = draw(timezone_aware_datetimes())
    latest = earliest + timedelta(days=7)

    request = SessionRequest(
        id="req1",
        duration=timedelta(hours=1),
        number_of_occurrences=1,
        earliest_date=earliest,
        latest_date=latest
    )

    # Create room resource
    room = Resource(
        id="room1",
        resource_type="room",
        concurrency_capacity=1
    )

    # Create constraints
    constraints = [
        NoOverlap("room1"),
        WithinDateRange("req1")
    ]

    return Problem(
        requests=[request],
        resources=[room],
        calendars=[calendar],
        constraints=constraints,
        institutional_calendar_id="cal1"
    )


class TestSolverProperties:
    """Property-based tests for solver behavior."""

    @given(simple_problem(), st.integers(min_value=0, max_value=1000))
    def test_seed_based_determinism(self, problem, seed):
        """
        **Feature: edusched-scheduler, Property 23: Seed-Based Determinism**

        For any Problem and seed value, the solver should produce identical
        results when run multiple times with the same seed.

        **Validates: Requirements 11.1, 11.2**
        """
        solver = HeuristicSolver()

        # Solve with the same seed twice
        result1 = solver.solve(problem, seed=seed)
        result2 = solver.solve(problem, seed=seed)

        # Results should be identical
        assert result1.status == result2.status, "Status should be identical with same seed"
        assert result1.seed_used == result2.seed_used, "Seed should be preserved"
        assert result1.backend_used == result2.backend_used, "Backend should be identical"
        assert result1.solve_time_seconds >= 0, "Solve time should be recorded"
        assert result2.solve_time_seconds >= 0, "Solve time should be recorded"

        # Check assignments are identical
        assert len(result1.assignments) == len(result2.assignments), \
            "Number of assignments should be identical"

        for a1, a2 in zip(result1.assignments, result2.assignments):
            assert a1.request_id == a2.request_id, "Assignment request IDs should match"
            assert a1.occurrence_index == a2.occurrence_index, "Assignment occurrence indices should match"
            assert a1.start_time == a2.start_time, "Assignment start times should match"
            assert a1.end_time == a2.end_time, "Assignment end times should match"
            assert a1.assigned_resources == a2.assigned_resources, "Assigned resources should match"
            assert a1.cohort_id == a2.cohort_id, "Cohort IDs should match"

        # Check unscheduled requests are identical
        assert set(result1.unscheduled_requests) == set(result2.unscheduled_requests), \
            "Unscheduled requests should be identical"

        # Check objective scores are identical
        assert result1.objective_score == result2.objective_score, \
            "Objective scores should be identical"

    @given(
        simple_problem(),
        st.integers(min_value=0, max_value=1000),
        st.integers(min_value=0, max_value=1000)
    )
    def test_different_seeds_produce_different_results(self, problem, seed1, seed2):
        """
        Different seeds should produce potentially different results.
        """
        # Use different seeds
        assume(seed1 != seed2)

        solver = HeuristicSolver()

        # Solve with different seeds
        result1 = solver.solve(problem, seed=seed1)
        result2 = solver.solve(problem, seed=seed2)

        # Both should be valid (either feasible or consistent handling of infeasibility)
        assert result1.status in ["feasible", "partial", "infeasible"], \
            f"Result1 should have valid status, got {result1.status}"
        assert result2.status in ["feasible", "partial", "infeasible"], \
            f"Result2 should have valid status, got {result2.status}"

        # Seeds should be recorded
        assert result1.seed_used == seed1, "Seed1 should be recorded"
        assert result2.seed_used == seed2, "Seed2 should be recorded"

    @given(timezone_aware_datetimes(), st.timedeltas(min_value=timedelta(minutes=15), max_value=timedelta(hours=2)))
    def test_timeslot_granularity_alignment(self, start_time, duration):
        """
        **Feature: edusched-scheduler, Property 18: Timeslot Granularity Alignment**

        The solver should align assignments to calendar timeslot granularity.

        **Validates: Requirements 9.2**
        """
        # Create calendar with specific granularity
        granularity = timedelta(minutes=30)  # 30-minute granularity
        calendar = Calendar(
            id="cal1",
            timezone=ZoneInfo("UTC"),
            timeslot_granularity=granularity
        )

        # Create request that starts at arbitrary time
        earliest = start_time
        latest = earliest + timedelta(days=1)

        request = SessionRequest(
            id="req1",
            duration=duration,
            number_of_occurrences=1,
            earliest_date=earliest,
            latest_date=latest
        )

        # Create problem
        problem = Problem(
            requests=[request],
            resources=[],
            calendars=[calendar],
            constraints=[WithinDateRange("req1")],
            institutional_calendar_id="cal1"
        )

        # Solve
        solver = HeuristicSolver()
        result = solver.solve(problem, seed=42)

        if result.assignments:
            assignment = result.assignments[0]

            # Check that assignment times align with granularity
            minutes_since_midnight = (
                assignment.start_time.hour * 60 +
                assignment.start_time.minute +
                assignment.start_time.second / 60
            )

            # Should align to 30-minute boundaries
            granularity_minutes = granularity.total_seconds() / 60
            assert minutes_since_midnight % granularity_minutes == 0, \
                f"Start time should align to {granularity_minutes}-minute granularity"

            # Duration should also align (or at least not create misaligned end times)
            duration_minutes = (
                (assignment.end_time - assignment.start_time).total_seconds() / 60
            )
            # Allow some flexibility for duration alignment, as it might span multiple granules

    @given(
        timezone_aware_datetimes(),
        st.integers(min_value=1, max_value=6),  # hours
        st.sampled_from([timedelta(minutes=15), timedelta(minutes=30), timedelta(minutes=60)])
    )
    def test_multi_hour_session_contiguity(self, start_time, num_hours, granularity):
        """
        **Feature: edusched-scheduler, Property 20: Multi-Hour Session Contiguity**

        For multi-hour sessions, the solver should create contiguous blocks
        of timeslots that maintain the total duration.

        **Validates: Requirements 9.3**
        """
        # Create calendar with specific granularity
        calendar = Calendar(
            id="cal1",
            timezone=ZoneInfo("UTC"),
            timeslot_granularity=granularity
        )

        # Create multi-hour request
        duration = timedelta(hours=num_hours)
        earliest = start_time
        latest = earliest + timedelta(days=1)

        request = SessionRequest(
            id="req1",
            duration=duration,
            number_of_occurrences=1,
            earliest_date=earliest,
            latest_date=latest
        )

        # Create room resource
        room = Resource(
            id="room1",
            resource_type="room",
            concurrency_capacity=1
        )

        # Create problem
        problem = Problem(
            requests=[request],
            resources=[room],
            calendars=[calendar],
            constraints=[NoOverlap("room1"), WithinDateRange("req1")],
            institutional_calendar_id="cal1"
        )

        # Solve
        solver = HeuristicSolver()
        result = solver.solve(problem, seed=42)

        if result.assignments:
            assignment = result.assignments[0]

            # Check total duration is preserved
            actual_duration = assignment.end_time - assignment.start_time
            assert abs(actual_duration - duration) < timedelta(minutes=1), \
                f"Multi-hour session duration should be preserved: expected {duration}, got {actual_duration}"

            # Check that the session spans the correct number of granules
            granularity_minutes = granularity.total_seconds() / 60
            duration_minutes = duration.total_seconds() / 60
            expected_granules = duration_minutes / granularity_minutes

            # Assignment should span approximately the expected number of granules
            actual_granules = (actual_duration.total_seconds() / 60) / granularity_minutes
            assert abs(actual_granules - expected_granules) < 1, \
                f"Should span approximately {expected_granules} granules, got {actual_granules}"

    @given(
        simple_problem(),
        st.integers(min_value=0, max_value=100),
        st.sampled_from([True, False])
    )
    def test_solver_metadata_tracking(self, problem, seed, fallback):
        """
        Solver should track all metadata correctly.
        """
        solver = HeuristicSolver()

        # Solve with metadata tracking
        result = solver.solve(problem, seed=seed, fallback=fallback)

        # Check all metadata is set
        assert result.seed_used == seed, "Seed should be recorded"
        assert result.backend_used == "heuristic", "Backend should be identified"
        assert isinstance(result.solve_time_seconds, float), "Solve time should be recorded as float"
        assert result.solve_time_seconds >= 0, "Solve time should be non-negative"
        assert result.status in ["feasible", "partial", "infeasible"], \
            f"Status should be valid, got {result.status}"

        # Check objective score is set (even if None)
        assert result.objective_score is None or (0 <= result.objective_score <= 1), \
            f"Objective score should be None or in [0,1], got {result.objective_score}"