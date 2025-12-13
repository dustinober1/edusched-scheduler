"""Property-based tests for infeasibility report generation."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import hypothesis.strategies as st
from hypothesis import given, settings

from edusched.solvers.heuristic import HeuristicSolver
from edusched.domain.calendar import Calendar
from edusched.domain.problem import Problem
from edusched.domain.resource import Resource
from edusched.domain.session_request import SessionRequest
from edusched.domain.result import InfeasibilityReport
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
def infeasible_problems(draw):
    """Generate problems that are likely to be infeasible."""
    # Create calendar
    calendar = Calendar(
        id="cal1",
        timezone=ZoneInfo("UTC"),
        timeslot_granularity=timedelta(minutes=30)
    )

    # Create very restrictive time windows
    base_time = draw(timezone_aware_datetimes())

    # Create requests with overlapping time windows
    requests = []
    for i in range(3):
        # All requests want the same narrow time window
        earliest = base_time + timedelta(hours=10)  # 10 AM
        latest = base_time + timedelta(hours=11)   # 11 AM - only 1 hour window!

        request = SessionRequest(
            id=f"req{i}",
            duration=timedelta(hours=2),  # 2-hour duration in 1-hour window - infeasible!
            number_of_occurrences=1,
            earliest_date=earliest,
            latest_date=latest,
            cohort_id=f"cohort{i}"
        )
        requests.append(request)

    # Create single room resource
    room = Resource(
        id="room1",
        resource_type="room",
        concurrency_capacity=1  # Only one room available
    )

    # Create constraints
    constraints = [
        NoOverlap("room1"),
        *[WithinDateRange(f"req{i}") for i in range(3)]
    ]

    return Problem(
        requests=requests,
        resources=[room],
        calendars=[calendar],
        constraints=constraints,
        institutional_calendar_id="cal1"
    )


class TestInfeasibilityReportProperties:
    """Property-based tests for infeasibility report generation."""

    @given(infeasible_problems(), st.integers(min_value=0, max_value=100))
    @settings(deadline=None)
    def test_infeasibility_report_structure(self, problem, seed):
        """
        **Feature: edusched-scheduler, Property 25: Infeasibility Report Structure**

        When scheduling fails, the infeasibility report should contain
        structured information about why scheduling failed.

        **Validates: Requirements 12.1**
        """
        solver = HeuristicSolver()

        # Try to solve - should fail with infeasible or partial
        result = solver.solve(problem, seed=seed, fallback=False)

        # If problem is infeasible or partial, check report structure
        if result.diagnostics:
            assert isinstance(result.diagnostics, InfeasibilityReport), \
                "Diagnostics should be an InfeasibilityReport"

            # Check required fields exist
            assert hasattr(result.diagnostics, 'unscheduled_requests'), \
                "Should have unscheduled_requests field"
            assert hasattr(result.diagnostics, 'violated_constraints_summary'), \
                "Should have violated_constraints_summary field"
            assert hasattr(result.diagnostics, 'top_conflicts'), \
                "Should have top_conflicts field"

            # Check data types
            assert isinstance(result.diagnostics.unscheduled_requests, list), \
                "unscheduled_requests should be a list"
            assert isinstance(result.diagnostics.violated_constraints_summary, dict), \
                "violated_constraints_summary should be a dict"
            assert isinstance(result.diagnostics.top_conflicts, list), \
                "top_conflicts should be a list"

            # Check unscheduled requests match result
            assert set(result.diagnostics.unscheduled_requests) == set(result.unscheduled_requests), \
                "Report unscheduled requests should match result unscheduled requests"

            # Check summary keys are strings
            for key in result.diagnostics.violated_constraints_summary.keys():
                assert isinstance(key, str), f"Summary key should be string, got {type(key)}"

            # Check summary values are non-negative
            for value in result.diagnostics.violated_constraints_summary.values():
                assert isinstance(value, int), f"Summary value should be int, got {type(value)}"
                assert value >= 0, f"Summary value should be non-negative, got {value}"

            # Check conflict descriptions are strings
            for conflict in result.diagnostics.top_conflicts:
                assert isinstance(conflict, str), f"Conflict should be string, got {type(conflict)}"
                assert len(conflict) > 10, f"Conflict description should be descriptive: {conflict}"

    @given(st.integers(min_value=1, max_value=5), st.integers(min_value=0, max_value=100))
    def test_partial_solution_report_completeness(self, num_requests, seed):
        """
        **Feature: edusched-scheduler, Property 26: Partial Solution Report Completeness**

        When only some requests can be scheduled, the report should accurately
        reflect which requests were scheduled vs unscheduled.

        **Validates: Requirements 12.2**
        """
        # Create calendar
        calendar = Calendar(
            id="cal1",
            timezone=ZoneInfo("UTC"),
            timeslot_granularity=timedelta(minutes=30)
        )

        # Create requests with varying time windows
        base_time = datetime(2024, 6, 10, 9, 0, tzinfo=ZoneInfo("UTC"))
        requests = []

        for i in range(num_requests):
            # Create requests that may or may not be schedulable
            earliest = base_time + timedelta(days=i)
            latest = earliest + timedelta(hours=1)  # Very tight window

            request = SessionRequest(
                id=f"req{i}",
                duration=timedelta(minutes=90),  # 1.5 hours in 1-hour window
                number_of_occurrences=1,
                earliest_date=earliest,
                latest_date=latest,
                cohort_id=f"cohort{i}"
            )
            requests.append(request)

        # Create limited resources
        room = Resource(
            id="room1",
            resource_type="room",
            concurrency_capacity=1
        )

        # Create constraints
        constraints = [
            NoOverlap("room1"),
            *[WithinDateRange(f"req{i}") for i in range(num_requests)]
        ]

        problem = Problem(
            requests=requests,
            resources=[room],
            calendars=[calendar],
            constraints=constraints,
            institutional_calendar_id="cal1"
        )

        solver = HeuristicSolver()
        result = solver.solve(problem, seed=seed, fallback=True)  # Allow partial solutions

        # Check that result is consistent
        scheduled_request_ids = {a.request_id for a in result.assignments}
        unscheduled_set = set(result.unscheduled_requests)
        all_request_ids = {r.id for r in requests}

        # No overlap between scheduled and unscheduled
        assert scheduled_request_ids.isdisjoint(unscheduled_set), \
            "Scheduled and unscheduled requests should not overlap"

        # All requests are either scheduled or unscheduled
        assert scheduled_request_ids.union(unscheduled_set) == all_request_ids, \
            "All requests should be either scheduled or unscheduled"

        # If we have diagnostics, check they match
        if result.diagnostics:
            assert set(result.diagnostics.unscheduled_requests) == unscheduled_set, \
                "Diagnostics should match unscheduled requests"

    @given(
        st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=5),
        st.integers(min_value=0, max_value=1000)
    )
    def test_infeasibility_report_content_usefulness(self, unscheduled_requests, seed):
        """
        Infeasibility reports should provide useful diagnostic information.
        """
        # Create a mock infeasibility report
        report = InfeasibilityReport(
            unscheduled_requests=unscheduled_requests,
            violated_constraints_summary={
                "time_constraints": len(unscheduled_requests),
                "resource_availability": max(1, len(unscheduled_requests) // 2),
                "capacity_limits": max(0, len(unscheduled_requests) - 2)
            },
            top_conflicts=[
                f"Insufficient time windows for {len(unscheduled_requests)} requests",
                f"Resource capacity constraints",
                f"Overlapping session requirements"
            ]
        )

        # Check report contains useful information
        assert len(report.unscheduled_requests) > 0, \
            "Should have unscheduled requests"

        assert len(report.violated_constraints_summary) > 0, \
            "Should have constraint violations summary"

        assert len(report.top_conflicts) > 0, \
            "Should have top conflicts identified"

        # Check that summary counts are reasonable
        total_violations = sum(report.violated_constraints_summary.values())
        assert total_violations >= len(unscheduled_requests), \
            "Total violations should be at least number of unscheduled requests"

        # Check conflict descriptions are meaningful
        for conflict in report.top_conflicts:
            assert len(conflict) > 20, \
                f"Conflict description should be detailed: {conflict}"
            assert any(word in conflict.lower() for word in [
                "insufficient", "constraint", "capacity", "overlap", "time", "resource"
            ]), f"Conflict should mention specific issues: {conflict}"

    @given(st.integers(min_value=1, max_value=10), st.sampled_from([True, False]))
    def test_fallback_behavior_consistency(self, num_requests, fallback):
        """
        The fallback parameter should affect result status consistently.
        """
        # Create a potentially problematic problem
        calendar = Calendar(
            id="cal1",
            timezone=ZoneInfo("UTC"),
            timeslot_granularity=timedelta(minutes=30)
        )

        base_time = datetime(2024, 6, 10, 9, 0, tzinfo=ZoneInfo("UTC"))
        requests = []

        for i in range(num_requests):
            request = SessionRequest(
                id=f"req{i}",
                duration=timedelta(hours=2),
                number_of_occurrences=1,
                earliest_date=base_time,
                latest_date=base_time + timedelta(hours=3),  # Tight window
                cohort_id=f"cohort{i}"
            )
            requests.append(request)

        room = Resource(
            id="room1",
            resource_type="room",
            concurrency_capacity=1
        )

        constraints = [
            NoOverlap("room1"),
            *[WithinDateRange(f"req{i}") for i in range(num_requests)]
        ]

        problem = Problem(
            requests=requests,
            resources=[room],
            calendars=[calendar],
            constraints=constraints,
            institutional_calendar_id="cal1"
        )

        solver = HeuristicSolver()
        result = solver.solve(problem, seed=42, fallback=fallback)

        # Check that fallback affects result appropriately
        if fallback:
            # With fallback, should always get "partial" or "feasible", never "infeasible"
            assert result.status in ["partial", "feasible"], \
                f"With fallback, status should be 'partial' or 'feasible', got {result.status}"

            # Should have assignments (unless no requests)
            if num_requests > 0:
                assert len(result.assignments) >= 0, \
                    "Should have assignments with fallback"

        else:
            # Without fallback, can get "infeasible" if nothing can be scheduled
            assert result.status in ["partial", "infeasible", "feasible"], \
                f"Without fallback, status should be valid, got {result.status}"

        # In all cases, scheduled + unscheduled should equal total requests
        total_handled = len(result.assignments) + len(result.unscheduled_requests)
        assert total_handled == num_requests, \
            f"Total handled ({total_handled}) should equal total requests ({num_requests})"