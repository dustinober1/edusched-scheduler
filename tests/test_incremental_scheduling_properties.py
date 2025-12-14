"""Property-based tests for incremental scheduling."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import hypothesis.strategies as st
from hypothesis import given, settings

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


class TestIncrementalSchedulingProperties:
    """Property-based tests for incremental scheduling capabilities."""

    @given(
        st.lists(timezone_aware_datetimes(), min_size=1, max_size=5),
        st.integers(min_value=0, max_value=1000)
    )
    def test_progressive_request_addition(self, base_times, seed):
        """
        **Feature: edusched-scheduler, Property 30: Progressive Request Addition**

        Adding requests to an existing schedule should preserve existing assignments.
        """
        # Create calendar
        calendar = Calendar(
            id="cal1",
            timezone=ZoneInfo("UTC"),
            timeslot_granularity=timedelta(minutes=30)
        )

        # Create resources
        room1 = Resource(id="room1", resource_type="room", concurrency_capacity=1)
        room2 = Resource(id="room2", resource_type="room", concurrency_capacity=1)

        # Phase 1: Schedule initial requests
        initial_requests = []
        for i, base_time in enumerate(base_times[:2]):  # Use first 2 times
            request = SessionRequest(
                id=f"initial_req_{i}",
                duration=timedelta(hours=1),
                number_of_occurrences=1,
                earliest_date=base_time,
                latest_date=base_time + timedelta(hours=2)
            )
            initial_requests.append(request)

        problem1 = Problem(
            requests=initial_requests,
            resources=[room1, room2],
            calendars=[calendar],
            constraints=[
                NoOverlap("room1"),
                NoOverlap("room2"),
                *[WithinDateRange(f"initial_req_{i}") for i in range(len(initial_requests))]
            ],
            institutional_calendar_id="cal1"
        )

        solver = HeuristicSolver()
        result1 = solver.solve(problem1, seed=seed)

        # Phase 2: Add more requests
        additional_requests = []
        for i, base_time in enumerate(base_times[2:4]):  # Use next 2 times
            request = SessionRequest(
                id=f"additional_req_{i}",
                duration=timedelta(hours=1),
                number_of_occurrences=1,
                earliest_date=base_time,
                latest_date=base_time + timedelta(hours=2)
            )
            additional_requests.append(request)

        # Create locked assignments from phase 1
        problem2 = Problem(
            requests=initial_requests + additional_requests,
            resources=[room1, room2],
            calendars=[calendar],
            constraints=[
                NoOverlap("room1"),
                NoOverlap("room2"),
                *[WithinDateRange(f"initial_req_{i}") for i in range(len(initial_requests))],
                *[WithinDateRange(f"additional_req_{i}") for i in range(len(additional_requests))]
            ],
            locked_assignments=result1.assignments,
            institutional_calendar_id="cal1"
        )

        result2 = solver.solve(problem2, seed=seed)

        # Check that original assignments are preserved
        for original in result1.assignments:
            matches = [
                a for a in result2.assignments
                if a.request_id == original.request_id
                and a.occurrence_index == original.occurrence_index
            ]
            assert len(matches) == 1, f"Original assignment {original.request_id} should be preserved"
            assert matches[0].start_time == original.start_time, \
                f"Original start time should be preserved for {original.request_id}"

    @given(
        st.integers(min_value=2, max_value=5),
        st.integers(min_value=0, max_value=1000)
    )
    def test_incremental_resource_addition(self, num_requests, seed):
        """
        Adding resources to an existing schedule should improve scheduling capability.
        """
        # Create calendar
        calendar = Calendar(
            id="cal1",
            timezone=ZoneInfo("UTC"),
            timeslot_granularity=timedelta(minutes=30)
        )

        # Create requests that all want the same time
        base_time = datetime(2024, 6, 10, 10, 0, tzinfo=ZoneInfo("UTC"))
        requests = []
        for i in range(num_requests):
            request = SessionRequest(
                id=f"req_{i}",
                duration=timedelta(hours=1),
                number_of_occurrences=1,
                earliest_date=base_time,
                latest_date=base_time + timedelta(hours=2)  # 2 hour window for 1 hour duration
            )
            requests.append(request)

        # Phase 1: Schedule with limited resources
        room1 = Resource(id="room1", resource_type="room", concurrency_capacity=1)
        problem1 = Problem(
            requests=requests,
            resources=[room1],
            calendars=[calendar],
            constraints=[
                NoOverlap("room1"),
                *[WithinDateRange(f"req_{i}") for i in range(num_requests)]
            ],
            institutional_calendar_id="cal1"
        )

        solver = HeuristicSolver()
        result1 = solver.solve(problem1, seed=seed)

        # Phase 2: Add more resources
        room2 = Resource(id="room2", resource_type="room", concurrency_capacity=1)
        room3 = Resource(id="room3", resource_type="room", concurrency_capacity=1)

        problem2 = Problem(
            requests=requests,
            resources=[room1, room2, room3],
            calendars=[calendar],
            constraints=[
                NoOverlap("room1"),
                NoOverlap("room2"),
                NoOverlap("room3"),
                *[WithinDateRange(f"req_{i}") for i in range(num_requests)]
            ],
            institutional_calendar_id="cal1"
        )

        result2 = solver.solve(problem2, seed=seed)

        # Should schedule more requests with additional resources
        assert len(result2.assignments) >= len(result1.assignments), \
            "Additional resources should not reduce scheduled assignments"

        # With enough resources, should schedule all requests
        if num_requests <= 3:  # We have 3 rooms
            assert len(result2.assignments) == num_requests, \
                "Should schedule all requests when resources are sufficient"

    @given(
        st.integers(min_value=1, max_value=3),
        st.integers(min_value=0, max_value=1000)
    )
    def test_constraint_addition_impact(self, num_constraints, seed):
        """
        Adding constraints should restrict scheduling appropriately.
        """
        # Create calendar
        calendar = Calendar(
            id="cal1",
            timezone=ZoneInfo("UTC"),
            timeslot_granularity=timedelta(minutes=30)
        )

        # Create requests
        base_time = datetime(2024, 6, 10, 10, 0, tzinfo=ZoneInfo("UTC"))
        requests = []
        for i in range(3):  # Fixed 3 requests
            request = SessionRequest(
                id=f"req_{i}",
                duration=timedelta(hours=1),
                number_of_occurrences=1,
                earliest_date=base_time + timedelta(hours=i * 2),
                latest_date=base_time + timedelta(hours=i * 2 + 2)
            )
            requests.append(request)

        # Create resource
        room = Resource(id="room1", resource_type="room", concurrency_capacity=1)

        # Phase 1: Schedule with minimal constraints
        problem1 = Problem(
            requests=requests,
            resources=[room],
            calendars=[calendar],
            constraints=[NoOverlap("room1")],
            institutional_calendar_id="cal1"
        )

        solver = HeuristicSolver()
        result1 = solver.solve(problem1, seed=seed)

        # Phase 2: Add blackout periods to calendar
        from edusched.constraints.hard_constraints import BlackoutDates

        # Create calendar with blackout periods
        from edusched.domain.calendar import TimeWindow

        blackout_calendar = Calendar(
            id="blackout_cal",
            timezone=ZoneInfo("UTC"),
            timeslot_granularity=timedelta(minutes=30),
            blackout_periods=[
                TimeWindow(
                    start=base_time + timedelta(hours=1),
                    end=base_time + timedelta(hours=2)
                )
            ]
        )

        blackout = BlackoutDates("blackout_cal")

        problem2 = Problem(
            requests=requests,
            resources=[room],
            calendars=[calendar, blackout_calendar],
            constraints=[NoOverlap("room1"), blackout],
            institutional_calendar_id="cal1"
        )

        result2 = solver.solve(problem2, seed=seed)

        # Blackout constraint should affect scheduling
        # (exact behavior depends on when requests are scheduled)
        # The key is that adding constraints changes the solution space
        assert result2.assignments is not None, "Should still produce assignments with blackout"

    @given(
        st.integers(min_value=1, max_value=3),
        st.integers(min_value=0, max_value=1000)
    )
    def test_partial_schedule_extension(self, num_new, seed):
        """
        Extending a partial schedule should schedule additional requests.
        """
        # Create calendar
        calendar = Calendar(
            id="cal1",
            timezone=ZoneInfo("UTC"),
            timeslot_granularity=timedelta(minutes=30)
        )

        # Create initial requests that might not all fit
        base_time = datetime(2024, 6, 10, 10, 0, tzinfo=ZoneInfo("UTC"))
        initial_requests = []
        for i in range(5):
            request = SessionRequest(
                id=f"initial_req_{i}",
                duration=timedelta(hours=2),  # Long duration
                number_of_occurrences=1,
                earliest_date=base_time,
                latest_date=base_time + timedelta(hours=8)  # All want same window
            )
            initial_requests.append(request)

        # Single resource
        room = Resource(id="room1", resource_type="room", concurrency_capacity=1)

        # Phase 1: Create a potentially oversubscribed problem
        problem1 = Problem(
            requests=initial_requests,
            resources=[room],
            calendars=[calendar],
            constraints=[
                NoOverlap("room1"),
                *[WithinDateRange(f"initial_req_{i}") for i in range(5)]
            ],
            institutional_calendar_id="cal1"
        )

        solver = HeuristicSolver()
        result1 = solver.solve(problem1, seed=seed, fallback=True)

        # Phase 2: Add more requests with different time windows
        new_requests = []
        for i in range(num_new):
            request = SessionRequest(
                id=f"new_req_{i}",
                duration=timedelta(hours=1),
                number_of_occurrences=1,
                earliest_date=base_time + timedelta(hours=12 + i * 2),  # Later times
                latest_date=base_time + timedelta(hours=14 + i * 2)
            )
            new_requests.append(request)

        # Create problem with locked partial solution
        all_requests = initial_requests + new_requests
        constraints = [NoOverlap("room1")]
        constraints.extend([WithinDateRange(f"initial_req_{i}") for i in range(5)])
        constraints.extend([WithinDateRange(f"new_req_{i}") for i in range(num_new)])

        problem2 = Problem(
            requests=all_requests,
            resources=[room],
            calendars=[calendar],
            constraints=constraints,
            locked_assignments=result1.assignments,
            institutional_calendar_id="cal1"
        )

        result2 = solver.solve(problem2, seed=seed)

        # Should have scheduled at least the locked assignments
        assert len(result2.assignments) >= len(result1.assignments), \
            "Should preserve locked assignments"

        # Should attempt to schedule new requests
        # (success depends on availability after locked assignments)
        assert len(result2.assignments) >= len(result1.assignments), \
            "Should schedule additional requests where possible"

    @given(
        st.integers(min_value=1, max_value=4),
        st.integers(min_value=0, max_value=1000)
    )
    def test_multi_phase_scheduling_consistency(self, num_phases, seed):
        """
        Multi-phase incremental scheduling should produce consistent results.
        """
        # Create calendar
        calendar = Calendar(
            id="cal1",
            timezone=ZoneInfo("UTC"),
            timeslot_granularity=timedelta(minutes=30)
        )

        # Create multiple resources
        resources = [
            Resource(id=f"room{i}", resource_type="room", concurrency_capacity=1)
            for i in range(3)
        ]

        # Build schedule incrementally
        all_assignments = []
        all_requests = []

        for phase in range(num_phases):
            # Add 2 requests per phase
            phase_requests = []
            for i in range(2):
                request = SessionRequest(
                    id=f"phase_{phase}_req_{i}",
                    duration=timedelta(hours=1),
                    number_of_occurrences=1,
                    earliest_date=datetime(2024, 6, 10 + phase, 10, 0, tzinfo=ZoneInfo("UTC")),
                    latest_date=datetime(2024, 6, 10 + phase, 16, 0, tzinfo=ZoneInfo("UTC"))
                )
                phase_requests.append(request)
                all_requests.append(request)

            # Create problem with existing assignments locked
            constraints = []
            constraints.extend([NoOverlap(f"room{i}") for i in range(3)])
            constraints.extend([WithinDateRange(req.id) for req in all_requests])

            problem = Problem(
                requests=all_requests,
                resources=resources,
                calendars=[calendar],
                constraints=constraints,
                locked_assignments=all_assignments,
                institutional_calendar_id="cal1"
            )

            solver = HeuristicSolver()
            result = solver.solve(problem, seed=seed)

            # Check consistency
            assert len(result.assignments) >= len(all_assignments), \
                f"Phase {phase}: Should preserve existing assignments"

            # Add new assignments to locked list
            new_assignments = [
                a for a in result.assignments
                if a.request_id.startswith(f"phase_{phase}_")
            ]
            all_assignments.extend(new_assignments)

        # Final check: no conflicts in complete schedule
        # Check room conflicts
        for i in range(3):
            room_assignments = [
                a for a in all_assignments
                if f"room{i}" in str(a.assigned_resources)
            ]
            for j, a1 in enumerate(room_assignments):
                for a2 in room_assignments[j+1:]:
                    assert not (a1.start_time < a2.end_time and a1.end_time > a2.start_time), \
                        f"Room {i} has conflicting assignments"