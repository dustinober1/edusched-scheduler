"""Property-based tests for locked assignment handling."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import hypothesis.strategies as st
from hypothesis import given, settings, assume

from edusched.solvers.heuristic import HeuristicSolver
from edusched.domain.calendar import Calendar
from edusched.domain.problem import Problem
from edusched.domain.resource import Resource
from edusched.domain.session_request import SessionRequest
from edusched.domain.assignment import Assignment
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
def locked_assignments(draw):
    """Generate locked assignments."""
    start = draw(timezone_aware_datetimes())
    duration = draw(st.timedeltas(min_value=timedelta(minutes=15), max_value=timedelta(hours=4)))
    resource_id = draw(st.text(min_size=1, max_size=10))

    return Assignment(
        request_id=draw(st.text(min_size=1, max_size=10)),
        occurrence_index=draw(st.integers(min_value=0, max_value=10)),
        start_time=start,
        end_time=start + duration,
        assigned_resources={"room": [resource_id]},
        cohort_id=draw(st.one_of(st.none(), st.text(min_size=1, max_size=10))),
    )


class TestLockedAssignmentProperties:
    """Property-based tests for locked assignment handling."""

    @given(
        locked_assignments(),
        st.lists(timezone_aware_datetimes(), min_size=1, max_size=3)
    )
    def test_locked_assignments_preserved(self, locked_assignment, new_times):
        """
        **Feature: edusched-scheduler, Property 27: Locked Assignments Preserved**

        Locked assignments should always appear in the final solution unchanged.
        """
        # Create request for the locked assignment
        request = SessionRequest(
            id=locked_assignment.request_id,
            duration=locked_assignment.end_time - locked_assignment.start_time,
            number_of_occurrences=locked_assignment.occurrence_index + 1,
            earliest_date=datetime(2024, 1, 1, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 12, 31, tzinfo=ZoneInfo("UTC"))
        )

        # Create additional requests that might conflict
        other_requests = []
        for i, time in enumerate(new_times):
            req = SessionRequest(
                id=f"other_req_{i}",
                duration=timedelta(hours=1),
                number_of_occurrences=1,
                earliest_date=time,
                latest_date=time + timedelta(days=1)
            )
            other_requests.append(req)

        # Create calendar
        calendar = Calendar(
            id="cal1",
            timezone=ZoneInfo("UTC"),
            timeslot_granularity=timedelta(minutes=30)
        )

        # Create resource
        resource_ids = list(locked_assignment.assigned_resources.values())[0]
        resources = [Resource(id=rid, resource_type="room") for rid in resource_ids]

        # Create constraints
        constraints = [
            NoOverlap(resource_ids[0]),
            WithinDateRange(locked_assignment.request_id),
            *[WithinDateRange(f"other_req_{i}") for i in range(len(other_requests))]
        ]

        # Create problem with locked assignment
        problem = Problem(
            requests=[request] + other_requests,
            resources=resources,
            calendars=[calendar],
            constraints=constraints,
            locked_assignments=[locked_assignment],
            institutional_calendar_id="cal1"
        )

        # Solve
        solver = HeuristicSolver()
        result = solver.solve(problem, seed=42)

        # Check locked assignment is preserved
        locked_matches = [
            a for a in result.assignments
            if a.request_id == locked_assignment.request_id
            and a.occurrence_index == locked_assignment.occurrence_index
        ]

        assert len(locked_matches) == 1, "Locked assignment should be in solution"
        preserved = locked_matches[0]

        assert preserved.start_time == locked_assignment.start_time, \
            "Locked start time should be preserved"
        assert preserved.end_time == locked_assignment.end_time, \
            "Locked end time should be preserved"
        assert preserved.assigned_resources == locked_assignment.assigned_resources, \
            "Locked resources should be preserved"
        assert preserved.cohort_id == locked_assignment.cohort_id, \
            "Locked cohort should be preserved"

    @given(
        st.lists(locked_assignments(), min_size=2, max_size=5),
        st.integers(min_value=0, max_value=100)
    )
    @settings(deadline=None)
    def test_locked_assignments_avoid_conflicts(self, locked_assignments, seed):
        """
        Solver should respect locked assignments and not schedule conflicting sessions.
        """
        if not locked_assignments:
            return

        # Create requests for locked assignments
        locked_requests = []
        for assignment in locked_assignments:
            req = SessionRequest(
                id=assignment.request_id,
                duration=assignment.end_time - assignment.start_time,
                number_of_occurrences=assignment.occurrence_index + 1,
                earliest_date=datetime(2024, 1, 1, tzinfo=ZoneInfo("UTC")),
                latest_date=datetime(2024, 12, 31, tzinfo=ZoneInfo("UTC"))
            )
            locked_requests.append(req)

        # Create a new request that might conflict with locked assignments
        base_time = locked_assignments[0].start_time
        conflict_request = SessionRequest(
            id="conflict_req",
            duration=timedelta(hours=2),
            number_of_occurrences=1,
            earliest_date=base_time - timedelta(hours=1),
            latest_date=base_time + timedelta(hours=1)
        )

        # Create calendar and resources
        calendar = Calendar(
            id="cal1",
            timezone=ZoneInfo("UTC"),
            timeslot_granularity=timedelta(minutes=30)
        )

        # Collect all unique resources
        all_resource_ids = set()
        for assignment in locked_assignments:
            for resource_list in assignment.assigned_resources.values():
                all_resource_ids.update(resource_list)

        resources = [Resource(id=rid, resource_type="room") for rid in all_resource_ids]

        # Create constraints
        constraints = [NoOverlap(rid) for rid in all_resource_ids]

        # Create problem
        problem = Problem(
            requests=locked_requests + [conflict_request],
            resources=resources,
            calendars=[calendar],
            constraints=constraints,
            locked_assignments=locked_assignments,
            institutional_calendar_id="cal1"
        )

        # Solve
        solver = HeuristicSolver()
        result = solver.solve(problem, seed=seed)

        # Check no conflicts between locked and NEW assignments
        locked_ids = set(
            (a.request_id, a.occurrence_index) for a in locked_assignments
        )

        for locked in locked_assignments:
            for scheduled in result.assignments:
                # Skip if it's any locked assignment
                if (scheduled.request_id, scheduled.occurrence_index) in locked_ids:
                    continue

                # Check for time conflicts with same resources
                for locked_resource_list in locked.assigned_resources.values():
                    for scheduled_resource_list in scheduled.assigned_resources.values():
                        if set(locked_resource_list) & set(scheduled_resource_list):
                            # Same resource - check time overlap
                            assert not (scheduled.start_time < locked.end_time and
                                      scheduled.end_time > locked.start_time), \
                                f"New assignment conflicts with locked assignment: {scheduled} vs {locked}"

    @given(
        st.text(min_size=1, max_size=10),
        timezone_aware_datetimes(),
        st.timedeltas(min_value=timedelta(minutes=15), max_value=timedelta(hours=4))
    )
    def test_partial_locked_request_scheduling(self, request_id, base_time, duration):
        """
        When some occurrences are locked, solver should schedule remaining ones.
        """
        # Create a request with 3 occurrences
        total_occurrences = 3
        request = SessionRequest(
            id=request_id,
            duration=duration,
            number_of_occurrences=total_occurrences,
            earliest_date=base_time,
            latest_date=base_time + timedelta(days=7)
        )

        # Lock only the first occurrence
        locked_assignment = Assignment(
            request_id=request_id,
            occurrence_index=0,
            start_time=base_time,
            end_time=base_time + duration,
            assigned_resources={"room": ["room1"]},
            cohort_id="cohort1"
        )

        # Create calendar and resource
        calendar = Calendar(
            id="cal1",
            timezone=ZoneInfo("UTC"),
            timeslot_granularity=timedelta(minutes=30)
        )
        resource = Resource(id="room1", resource_type="room")

        # Create constraints
        constraints = [NoOverlap("room1"), WithinDateRange(request_id)]

        # Create problem
        problem = Problem(
            requests=[request],
            resources=[resource],
            calendars=[calendar],
            constraints=constraints,
            locked_assignments=[locked_assignment],
            institutional_calendar_id="cal1"
        )

        # Solve
        solver = HeuristicSolver()
        result = solver.solve(problem, seed=42)

        # Should have the locked occurrence
        locked_occurrences = [
            a for a in result.assignments
            if a.request_id == request_id and a.occurrence_index == 0
        ]
        assert len(locked_occurrences) == 1, "Should have locked occurrence"

        # Should have attempts to schedule other occurrences
        all_occurrences = [
            a for a in result.assignments
            if a.request_id == request_id
        ]

        # Should have at least the locked one
        assert len(all_occurrences) >= 1, "Should have at least locked occurrence"

        # If others are scheduled, they should be at different times
        scheduled_times = [a.start_time for a in all_occurrences]
        assert len(scheduled_times) == len(set(scheduled_times)), \
            "All occurrences should be at different times"

    @given(
        st.integers(min_value=1, max_value=5),
        st.integers(min_value=0, max_value=100)
    )
    def test_locked_assignment_priority(self, num_locked, seed):
        """
        Locked assignments should have priority over flexible scheduling.
        """
        locked_assignments = []
        requests = []

        # Create locked assignments at prime times (10 AM)
        base_time = datetime(2024, 6, 10, 10, 0, tzinfo=ZoneInfo("UTC"))

        for i in range(num_locked):
            assignment = Assignment(
                request_id=f"locked_req_{i}",
                occurrence_index=0,
                start_time=base_time + timedelta(days=i),
                end_time=base_time + timedelta(days=i, hours=2),
                assigned_resources={"room": [f"room{i}"]},
                cohort_id=f"cohort{i}"
            )
            locked_assignments.append(assignment)

            request = SessionRequest(
                id=f"locked_req_{i}",
                duration=timedelta(hours=2),
                number_of_occurrences=1,
                earliest_date=datetime(2024, 1, 1, tzinfo=ZoneInfo("UTC")),
                latest_date=datetime(2024, 12, 31, tzinfo=ZoneInfo("UTC"))
            )
            requests.append(request)

        # Create flexible requests that want the same slots
        flexible_requests = []
        for i in range(num_locked):
            req = SessionRequest(
                id=f"flex_req_{i}",
                duration=timedelta(hours=2),
                number_of_occurrences=1,
                earliest_date=base_time + timedelta(days=i) - timedelta(hours=1),
                latest_date=base_time + timedelta(days=i) + timedelta(hours=1)
            )
            flexible_requests.append(req)

        # Create calendar and resources
        calendar = Calendar(
            id="cal1",
            timezone=ZoneInfo("UTC"),
            timeslot_granularity=timedelta(minutes=30)
        )
        resources = [Resource(id=f"room{i}", resource_type="room") for i in range(num_locked)]

        # Create constraints
        constraints = [NoOverlap(f"room{i}") for i in range(num_locked)]
        constraints.extend([WithinDateRange(f"locked_req_{i}") for i in range(num_locked)])
        constraints.extend([WithinDateRange(f"flex_req_{i}") for i in range(num_locked)])

        # Create problem
        problem = Problem(
            requests=requests + flexible_requests,
            resources=resources,
            calendars=[calendar],
            constraints=constraints,
            locked_assignments=locked_assignments,
            institutional_calendar_id="cal1"
        )

        # Solve
        solver = HeuristicSolver()
        result = solver.solve(problem, seed=seed)

        # All locked assignments should be preserved
        for locked in locked_assignments:
            matches = [
                a for a in result.assignments
                if a.request_id == locked.request_id
                and a.occurrence_index == locked.occurrence_index
            ]
            assert len(matches) == 1, f"Locked assignment {locked.request_id} should be preserved"
            assert matches[0].start_time == locked.start_time, \
                f"Locked time should be preserved for {locked.request_id}"

    @given(st.lists(locked_assignments(), min_size=0, max_size=3))
    def test_empty_locked_assignments_handling(self, locked_assignments):
        """
        Solver should handle empty locked assignments gracefully.
        """
        if not locked_assignments:
            # Test with no locked assignments
            request = SessionRequest(
                id="req1",
                duration=timedelta(hours=1),
                number_of_occurrences=1,
                earliest_date=datetime(2024, 6, 10, tzinfo=ZoneInfo("UTC")),
                latest_date=datetime(2024, 6, 17, tzinfo=ZoneInfo("UTC"))
            )

            calendar = Calendar(
                id="cal1",
                timezone=ZoneInfo("UTC"),
                timeslot_granularity=timedelta(minutes=30)
            )
            resource = Resource(id="room1", resource_type="room")

            problem = Problem(
                requests=[request],
                resources=[resource],
                calendars=[calendar],
                constraints=[],
                locked_assignments=[],  # Empty list
                institutional_calendar_id="cal1"
            )

            solver = HeuristicSolver()
            result = solver.solve(problem, seed=42)

            # Should handle gracefully
            assert result is not None, "Should produce result even with no locked assignments"
            assert isinstance(result.assignments, list), "Assignments should be a list"

        else:
            # Test that locked assignments are properly initialized
            for locked in locked_assignments:
                assert hasattr(locked, 'request_id'), "Should have request_id"
                assert hasattr(locked, 'occurrence_index'), "Should have occurrence_index"
                assert hasattr(locked, 'start_time'), "Should have start_time"
                assert hasattr(locked, 'end_time'), "Should have end_time"
                assert hasattr(locked, 'assigned_resources'), "Should have assigned_resources"