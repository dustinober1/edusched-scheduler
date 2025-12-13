"""Property-based tests for API behavior consistency."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import inspect

import hypothesis.strategies as st
from hypothesis import given, settings, assume

from edusched import solve
from edusched.solvers.heuristic import HeuristicSolver
from edusched.errors import BackendError
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
def simple_problems(draw):
    """Generate simple scheduling problems."""
    # Create calendar
    calendar = Calendar(
        id="cal1",
        timezone=ZoneInfo("UTC"),
        timeslot_granularity=timedelta(minutes=30)
    )

    # Create request
    earliest = draw(timezone_aware_datetimes())
    latest = earliest + timedelta(days=7)
    duration = draw(st.timedeltas(min_value=timedelta(minutes=30), max_value=timedelta(hours=3)))

    request = SessionRequest(
        id=draw(st.text(min_size=1, max_size=10)),
        duration=duration,
        number_of_occurrences=1,
        earliest_date=earliest,
        latest_date=latest
    )

    # Create resource
    resource = Resource(
        id=draw(st.text(min_size=1, max_size=10)),
        resource_type="room",
        concurrency_capacity=1
    )

    # Create constraints
    from edusched.constraints.hard_constraints import NoOverlap, WithinDateRange
    constraints = [
        NoOverlap(resource.id),
        WithinDateRange(request.id)
    ]

    return Problem(
        requests=[request],
        resources=[resource],
        calendars=[calendar],
        constraints=constraints,
        institutional_calendar_id="cal1"
    )


class TestAPIProperties:
    """Property-based tests for API consistency."""

    @given(simple_problems(), st.integers(min_value=0, max_value=1000))
    def test_solve_function_signature(self, problem, seed):
        """
        **Feature: edusched-scheduler, Property 28: API Function Signature**

        The solve() function should accept the expected parameters
        and return a Result object.
        """
        # Check function signature
        sig = inspect.signature(solve)

        expected_params = ['problem', 'backend', 'seed', 'fallback']
        actual_params = list(sig.parameters.keys())

        for param in expected_params:
            assert param in actual_params, f"Parameter '{param}' should be in solve() signature"

        # Check default values
        assert sig.parameters['backend'].default == 'auto', \
            "Backend should default to 'auto'"
        assert sig.parameters['seed'].default is None, \
            "Seed should default to None"
        assert sig.parameters['fallback'].default is False, \
            "Fallback should default to False"

        # Test calling with just problem
        result = solve(problem)
        assert result is not None, "solve() should return a result with just problem"

        # Test calling with all parameters
        result = solve(
            problem=problem,
            backend='heuristic',
            seed=seed,
            fallback=False
        )
        assert result is not None, "solve() should return a result with all parameters"

    @given(simple_problems(), st.integers(min_value=0, max_value=1000))
    def test_direct_solver_vs_api_consistency(self, problem, seed):
        """
        Direct solver usage should produce identical results to API usage.
        """
        # Solve using direct solver
        solver = HeuristicSolver()
        direct_result = solver.solve(problem, seed=seed, fallback=False)

        # Solve using API
        api_result = solve(
            problem=problem,
            backend='heuristic',
            seed=seed,
            fallback=False
        )

        # Results should be identical
        assert direct_result.status == api_result.status, \
            "Status should match between direct solver and API"

        assert direct_result.backend_used == api_result.backend_used, \
            "Backend used should match"

        assert direct_result.seed_used == api_result.seed_used, \
            "Seed used should match"

        assert len(direct_result.assignments) == len(api_result.assignments), \
            "Number of assignments should match"

        assert set(direct_result.unscheduled_requests) == set(api_result.unscheduled_requests), \
            "Unscheduled requests should match"

        # Check assignments match
        for da, aa in zip(direct_result.assignments, api_result.assignments):
            assert da.request_id == aa.request_id, \
                "Assignment request IDs should match"
            assert da.occurrence_index == aa.occurrence_index, \
                "Assignment occurrence indices should match"
            assert da.start_time == aa.start_time, \
                "Assignment start times should match"
            assert da.end_time == aa.end_time, \
                "Assignment end times should match"
            assert da.assigned_resources == aa.assigned_resources, \
                "Assignment resources should match"

    @given(simple_problems(), st.integers(min_value=0, max_value=100))
    def test_seed_parameter_handling(self, problem, seed):
        """
        Seed parameter should be properly handled and preserved.
        """
        # Solve with seed
        result = solve(problem, seed=seed)

        # Seed should be preserved in result
        assert result.seed_used == seed, \
            f"Seed should be preserved: expected {seed}, got {result.seed_used}"

        # Should have backend information
        assert result.backend_used is not None, \
            "Backend should be identified"

        assert isinstance(result.solve_time_seconds, float), \
            "Solve time should be recorded as float"

        assert result.solve_time_seconds >= 0, \
            "Solve time should be non-negative"

    @given(
        simple_problems(),
        st.sampled_from([True, False]),
        st.integers(min_value=0, max_value=100)
    )
    def test_fallback_parameter_effect(self, problem, fallback, seed):
        """
        Fallback parameter should affect solver behavior appropriately.
        """
        result = solve(
            problem=problem,
            seed=seed,
            fallback=fallback
        )

        # Should always return a valid result
        assert result is not None, "Should always return a result"
        assert result.status in ["feasible", "partial", "infeasible"], \
            f"Status should be valid, got {result.status}"

        # With fallback, should never get "infeasible" unless truly impossible
        if fallback and len(problem.requests) > 0:
            # Should attempt partial solutions
            assert result.status in ["feasible", "partial"], \
                "With fallback, should get feasible or partial status"

    @given(simple_problems(), st.text(min_size=1, max_size=20))
    def test_invalid_backend_handling(self, problem, backend_name):
        """
        API should handle invalid backend names gracefully.
        """
        # Skip if using valid backends
        assume(backend_name not in ['heuristic', 'auto', 'ortools'])

        try:
            result = solve(
                problem=problem,
                backend=backend_name
            )
            # If it succeeds, check it's using a default
            assert result.backend_used is not None, \
                "Should use some backend even with invalid name"
        except Exception as e:
            # Should raise a meaningful error
            assert isinstance(e, (ValueError, KeyError, BackendError)), \
                f"Should raise ValueError, KeyError, or BackendError for invalid backend, got {type(e)}"
            assert str(backend_name) in str(e), \
                "Error message should mention the invalid backend name"

    @given(simple_problems())
    def test_result_object_completeness(self, problem):
        """
        Result object from API should have all required attributes.
        """
        result = solve(problem)

        # Check all required attributes exist
        required_attrs = [
            'status',
            'assignments',
            'unscheduled_requests',
            'backend_used',
            'seed_used',
            'solve_time_seconds'
        ]

        for attr in required_attrs:
            assert hasattr(result, attr), f"Result should have {attr} attribute"

        # Check types
        assert isinstance(result.status, str), "Status should be string"
        assert isinstance(result.assignments, list), "Assignments should be list"
        assert isinstance(result.unscheduled_requests, list), "Unscheduled should be list"
        assert isinstance(result.backend_used, str), "Backend should be string"
        assert isinstance(result.solve_time_seconds, float), "Solve time should be float"

        # Check status values
        assert result.status in ["feasible", "partial", "infeasible"], \
            f"Status should be valid, got {result.status}"

        # Check consistency
        assert len(result.assignments) + len(result.unscheduled_requests) == len(problem.requests), \
            "All requests should be either scheduled or unscheduled"

    @given(
        simple_problems(),
        st.integers(min_value=0, max_value=2),
        st.integers(min_value=0, max_value=1000)
    )
    def test_optional_parameter_defaults(self, problem, backend_type, seed):
        """
        Optional parameters should have sensible defaults.
        """
        # Test with no optional parameters
        result1 = solve(problem)

        # Test with explicit defaults
        result2 = solve(
            problem=problem,
            backend='heuristic' if backend_type == 0 else 'heuristic',
            seed=None if seed == 0 else seed,
            fallback=False
        )

        # Both should work
        assert result1 is not None, "Should work with defaults"
        assert result2 is not None, "Should work with explicit parameters"

        # Should have same backend
        assert result1.backend_used == result2.backend_used, \
            "Backend should be consistent"

        # Results should be valid
        for result in [result1, result2]:
            assert result.status in ["feasible", "partial", "infeasible"], \
                f"Status should be valid: {result.status}"
            assert result.solve_time_seconds >= 0, \
                "Solve time should be non-negative"

    @given(simple_problems())
    def test_api_idempotency(self, problem):
        """
        Multiple API calls with same parameters should produce consistent results.
        """
        # Solve twice with same problem
        result1 = solve(problem, seed=42)
        result2 = solve(problem, seed=42)

        # Results should be identical
        assert result1.status == result2.status, \
            "Status should be consistent"

        assert len(result1.assignments) == len(result2.assignments), \
            "Number of assignments should be consistent"

        # Check metadata consistency
        assert result1.seed_used == result2.seed_used, \
            "Seed should be consistent"

        assert result1.backend_used == result2.backend_used, \
            "Backend should be consistent"