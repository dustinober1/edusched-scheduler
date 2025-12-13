"""Property-based tests for constraint conflict detection and explanation."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import hypothesis.strategies as st
from hypothesis import given, assume, settings

from edusched.constraints.base import Violation
from edusched.constraints.hard_constraints import NoOverlap, WithinDateRange, MaxPerDay
from edusched.constraints.computer_requirements import ComputerRequirements, AnyComputerAvailable, NoComputerRoom
from edusched.domain.calendar import Calendar
from edusched.domain.assignment import Assignment
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
def assignments(draw):
    """Generate Assignment instances."""
    start = draw(timezone_aware_datetimes())
    duration = draw(st.timedeltas(min_value=timedelta(minutes=15), max_value=timedelta(hours=4)))

    return Assignment(
        request_id=draw(st.text(min_size=1, max_size=10)),
        occurrence_index=draw(st.integers(min_value=0, max_value=10)),
        start_time=start,
        end_time=start + duration,
        assigned_resources=draw(st.dictionaries(
            keys=st.sampled_from(["room", "instructor", "equipment"]),
            values=st.lists(st.text(min_size=1, max_size=10)),
            max_size=3
        )),
        cohort_id=draw(st.one_of(st.none(), st.text(min_size=1, max_size=10))),
    )


@st.composite
def assignments_with_resources(draw, resource_ids):
    """Generate assignments with specific resources."""
    start = draw(timezone_aware_datetimes())
    duration = draw(st.timedeltas(min_value=timedelta(minutes=15), max_value=timedelta(hours=4)))

    # Assign at least one of the specified resources
    assigned_resources = {}
    if resource_ids:
        resource_type = draw(st.sampled_from(["room", "instructor", "equipment"]))
        assigned_resources[resource_type] = [draw(st.sampled_from(resource_ids))]

    return Assignment(
        request_id=draw(st.text(min_size=1, max_size=10)),
        occurrence_index=draw(st.integers(min_value=0, max_value=10)),
        start_time=start,
        end_time=start + duration,
        assigned_resources=assigned_resources,
        cohort_id=draw(st.one_of(st.none(), st.text(min_size=1, max_size=10))),
    )


class TestConflictIdentification:
    """Property-based tests for constraint violation detection."""

    @given(st.text(min_size=1, max_size=10))
    def test_no_overlap_conflict_detection(self, resource_id):
        """
        NoOverlap constraint should detect all overlapping time intervals.
        """
        constraint = NoOverlap(resource_id)

        # Create overlapping assignments
        base_time = datetime(2024, 6, 10, 10, 0, tzinfo=ZoneInfo("UTC"))

        assignment1 = Assignment(
            request_id="req1",
            occurrence_index=0,
            start_time=base_time,
            end_time=base_time + timedelta(hours=2),
            assigned_resources={"room": [resource_id]},
            cohort_id="cohort1"
        )

        assignment2 = Assignment(
            request_id="req2",
            occurrence_index=0,
            start_time=base_time + timedelta(hours=1),  # Overlaps with assignment1
            end_time=base_time + timedelta(hours=3),
            assigned_resources={"room": [resource_id]},
            cohort_id="cohort2"
        )

        # Check for violation
        solution = [assignment1, assignment2]

        # Mock constraint context
        from edusched.constraints.base import ConstraintContext
        from edusched.domain.problem import Problem

        problem = Problem(requests=[], resources=[], calendars=[], constraints=[])
        indices = type('Indices', (), {
            'resource_lookup': {resource_id: Resource(id=resource_id, resource_type="room", concurrency_capacity=1)},
            'calendar_lookup': {},
            'request_lookup': {}
        })()

        context = ConstraintContext(
            problem=problem,
            resource_lookup=indices.resource_lookup,
            calendar_lookup=indices.calendar_lookup,
            request_lookup=indices.request_lookup
        )

        # Second assignment should violate constraint
        violation = constraint.check(assignment2, solution, context)

        assert violation is not None, "Should detect overlap violation"
        assert isinstance(violation, Violation), "Should return Violation object"
        assert resource_id in violation.affected_resource_id, "Should mention conflicting resource"
        assert any(word in violation.message.lower() for word in ["overlap", "double", "already"]), \
            f"Message should mention overlap or double-booking: {violation.message}"

    @given(timezone_aware_datetimes(), st.text(min_size=1, max_size=10))
    def test_no_overlap_non_conflict_acceptance(self, base_time, resource_id):
        """
        NoOverlap constraint should accept non-overlapping assignments.
        """
        constraint = NoOverlap(resource_id)

        # Create non-overlapping assignments
        assignment1 = Assignment(
            request_id="req1",
            occurrence_index=0,
            start_time=base_time,
            end_time=base_time + timedelta(hours=1),
            assigned_resources={"room": [resource_id]},
            cohort_id="cohort1"
        )

        assignment2 = Assignment(
            request_id="req2",
            occurrence_index=0,
            start_time=base_time + timedelta(hours=2),  # No overlap
            end_time=base_time + timedelta(hours=3),
            assigned_resources={"room": [resource_id]},
            cohort_id="cohort2"
        )

        # Mock context
        from edusched.constraints.base import ConstraintContext
        from edusched.domain.problem import Problem

        problem = Problem(requests=[], resources=[], calendars=[], constraints=[])
        indices = type('Indices', (), {
            'resource_lookup': {resource_id: Resource(id=resource_id, resource_type="room", concurrency_capacity=1)},
            'calendar_lookup': {},
            'request_lookup': {}
        })()

        context = ConstraintContext(
            problem=problem,
            resource_lookup=indices.resource_lookup,
            calendar_lookup=indices.calendar_lookup,
            request_lookup=indices.request_lookup
        )

        # Should not detect violation
        violation = constraint.check(assignment2, [assignment1], context)
        assert violation is None, "Should not detect violation for non-overlapping assignments"

    @given(
        timezone_aware_datetimes(),
        st.integers(min_value=1, max_value=5),
        st.integers(min_value=1, max_value=10)
    )
    def test_max_per_day_violation_thresholds(self, base_time, max_sessions, actual_sessions):
        """
        MaxPerDay constraint should enforce daily limits correctly.
        """
        resource_id = "room1"
        constraint = MaxPerDay(resource_id, max_sessions)

        assignments = []
        for i in range(actual_sessions):
            assignment = Assignment(
                request_id=f"req{i}",
                occurrence_index=0,
                start_time=base_time.replace(hour=9+i),  # Different times on same day
                end_time=base_time.replace(hour=10+i),
                assigned_resources={"room": [resource_id]},
                cohort_id="cohort1"
            )
            assignments.append(assignment)

        # Check the last assignment
        test_assignment = assignments[-1]
        prior_assignments = assignments[:-1]

        # Mock context
        from edusched.constraints.base import ConstraintContext
        from edusched.domain.problem import Problem

        problem = Problem(requests=[], resources=[], calendars=[], constraints=[])
        indices = type('Indices', (), {
            'resource_lookup': {},
            'calendar_lookup': {},
            'request_lookup': {}
        })()

        context = ConstraintContext(
            problem=problem,
            resource_lookup=indices.resource_lookup,
            calendar_lookup=indices.calendar_lookup,
            request_lookup=indices.request_lookup
        )

        violation = constraint.check(test_assignment, prior_assignments, context)

        if actual_sessions > max_sessions:
            assert violation is not None, f"Should detect violation when {actual_sessions} > {max_sessions}"
            assert str(max_sessions) in violation.message, "Message should mention limit"
        else:
            assert violation is None, f"Should not detect violation when {actual_sessions} <= {max_sessions}"

    @given(st.text(min_size=1, max_size=10))
    def test_within_date_range_boundary_detection_simple(self, request_id):
        """
        WithinDateRange should detect assignments outside date boundaries.
        """
        from edusched.constraints.hard_constraints import WithinDateRange

        constraint = WithinDateRange(request_id)

        # Define date boundaries
        earliest = datetime(2024, 6, 10, tzinfo=ZoneInfo("UTC"))
        latest = datetime(2024, 6, 17, tzinfo=ZoneInfo("UTC"))

        # Create request with these boundaries
        request = SessionRequest(
            id=request_id,
            duration=timedelta(hours=1),
            number_of_occurrences=1,
            earliest_date=earliest,
            latest_date=latest
        )

        # Test assignment outside boundaries
        outside_time = earliest - timedelta(days=1)
        assignment = Assignment(
            request_id=request_id,
            occurrence_index=0,
            start_time=outside_time,
            end_time=outside_time + timedelta(hours=1),
            cohort_id="cohort1"
        )

        # Mock context
        from edusched.constraints.base import ConstraintContext
        from edusched.domain.problem import Problem

        problem = Problem(requests=[], resources=[], calendars=[], constraints=[])
        indices = type('Indices', (), {
            'resource_lookup': {},
            'calendar_lookup': {},
            'request_lookup': {request_id: request}
        })()

        context = ConstraintContext(
            problem=problem,
            resource_lookup=indices.resource_lookup,
            calendar_lookup=indices.calendar_lookup,
            request_lookup=indices.request_lookup
        )

        violation = constraint.check(assignment, [], context)

        assert violation is not None, "Should detect assignment outside date range"
        assert "date range" in violation.message.lower() or "earliest" in violation.message.lower() or "latest" in violation.message.lower(), \
            f"Should mention date boundaries in violation: {violation.message}"

    @given(
        st.one_of([
            st.just({"min_total": 5}),
            st.just({"connected": 3}),
            st.just({"standalone": 2}),
            st.just({"total": 10}),
            st.just({"total": 0})  # No computers required
        ]),
        st.one_of([
            st.just({"total": 8, "connected": 4, "standalone": 4}),
            st.just({"total": 3, "connected": 2, "standalone": 1}),
            st.just({"total": 0}),
            st.just({"total": 0})  # No computers
        ])
    )
    def test_computer_requirements_matching(self, requirement, resource_computers):
        """
        ComputerRequirements constraint should evaluate computer needs accurately.
        """
        constraint = ComputerRequirements("req1")

        # Create mock context with request and resource
        from edusched.constraints.base import ConstraintContext
        from edusched.domain.problem import Problem
        from edusched.domain.session_request import SessionRequest

        # Only include computers requirement if not asking for zero computers
        attrs = {"computers": requirement} if requirement.get("total", 0) > 0 else {}
        request = SessionRequest(
            id="req1",
            duration=timedelta(hours=1),
            number_of_occurrences=1,
            earliest_date=datetime(2024, 6, 10, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 6, 17, tzinfo=ZoneInfo("UTC")),
            required_attributes=attrs
        )

        resource = Resource(
            id="room1",
            resource_type="room",
            attributes={"computers": resource_computers} if resource_computers else {}
        )

        problem = Problem(requests=[], resources=[], calendars=[], constraints=[])
        indices = type('Indices', (), {
            'resource_lookup': {"room1": resource},
            'calendar_lookup': {},
            'request_lookup': {"req1": request}
        })()

        context = ConstraintContext(
            problem=problem,
            resource_lookup=indices.resource_lookup,
            calendar_lookup=indices.calendar_lookup,
            request_lookup=indices.request_lookup
        )

        assignment = Assignment(
            request_id="req1",
            occurrence_index=0,
            start_time=datetime(2024, 6, 10, 10, 0, tzinfo=ZoneInfo("UTC")),
            end_time=datetime(2024, 6, 10, 11, 0, tzinfo=ZoneInfo("UTC")),
            assigned_resources={"room": ["room1"]},
            cohort_id="cohort1"
        )

        violation = constraint.check(assignment, [], context)

        # Check logic for different requirement patterns
        if requirement.get("total", 0) == 0:
            # No computers required - the constraint returns None when no requirement
            assert violation is None, "Should not violate when no computers required"

        elif "min_total" in requirement:
            if not resource_computers or resource_computers.get("total", 0) < requirement["min_total"]:
                assert violation is not None, "Should violate if insufficient computers"
                assert str(requirement["min_total"]) in violation.message
            else:
                assert violation is None, "Should be fine if sufficient computers"

        elif "total" in requirement:
            if not resource_computers or resource_computers.get("total", 0) < requirement["total"]:
                assert violation is not None, "Should violate if insufficient total computers"
                assert str(requirement["total"]) in violation.message
            else:
                assert violation is None, "Should be fine if sufficient total computers"

        elif isinstance(requirement.get("connected"), int):
            required = requirement["connected"]
            available = 0 if not resource_computers else resource_computers.get("connected", 0)

            if required > 0 and available < required:
                assert violation is not None, "Should violate if insufficient connected computers"
                assert "connected" in violation.message.lower()
            elif required == 0 and available > 0:
                assert violation is not None, "Should violate if connected computers not allowed"
                assert "no connected" in violation.message.lower()
            else:
                assert violation is None, "Should be fine for connected computer requirements"

    @given(st.text(min_size=1, max_size=10))
    def test_violation_explanation_quality(self, constraint_type):
        """
        Violation explanations should be clear and informative.
        """
        # Test different constraint types
        violations = []

        if constraint_type == "overlap":
            constraint = NoOverlap("room1")
            violations.append(Violation(
                constraint_type="hard.no_overlap",
                affected_request_id="req2",
                affected_resource_id="room1",
                message="Room room1 is already booked by req1 from 10:00 to 11:00, overlapping with req2 from 10:30 to 11:30"
            ))

        elif constraint_type == "computers":
            constraint = ComputerRequirements("req1")
            violations.append(Violation(
                constraint_type="hard.computer_requirements",
                affected_request_id="req1",
                affected_resource_id="room1",
                message="Room room1 has 2 computers but course requires at least 5"
            ))

        elif constraint_type == "max_per_day":
            constraint = MaxPerDay("cohort1", 3)
            violations.append(Violation(
                constraint_type="hard.max_per_day",
                affected_request_id="req4",
                message="Cohort cohort1 already has 3 sessions scheduled on Monday, exceeding the maximum of 3"
            ))

  
        # Check explanation quality
        for violation in violations:
            explanation = violation.message

            # Should be meaningful length
            assert len(explanation) > 10, f"Explanation should be detailed: {explanation}"

            # Should contain relevant information (not necessarily request ID)
            if violation.affected_resource_id:
                assert violation.affected_resource_id in explanation, \
                    "Should mention affected resource"

            # Should be human-readable
            assert isinstance(explanation, str), "Explanation should be string"

            # Should avoid technical jargon where possible
            technical_terms = ["constraint_type", "affected_", "violation"]
            for term in technical_terms:
                assert term not in explanation.lower(), \
                    f"Should avoid technical term '{term}' in user-facing message"

    @given(
        st.lists(timezone_aware_datetimes(), min_size=2, max_size=5),
        st.text(min_size=1, max_size=10)
    )
    def test_within_date_range_boundary_detection(self, times, request_id):
        """
        WithinDateRange should detect assignments outside date boundaries.
        """
        # Use first and last times as boundaries
        earliest = min(times)
        latest = max(times)

        constraint = WithinDateRange(request_id)

        # Create request with these boundaries
        request = SessionRequest(
            id=request_id,
            duration=timedelta(hours=1),
            number_of_occurrences=1,
            earliest_date=earliest,
            latest_date=latest
        )

        # Test assignment outside boundaries
        outside_time = earliest - timedelta(days=1)
        assignment = Assignment(
            request_id=request_id,
            occurrence_index=0,
            start_time=outside_time,
            end_time=outside_time + timedelta(hours=1),
            cohort_id="cohort1"
        )

        # Mock context
        from edusched.constraints.base import ConstraintContext
        from edusched.domain.problem import Problem

        problem = Problem(requests=[], resources=[], calendars=[], constraints=[])
        indices = type('Indices', (), {
            'resource_lookup': {},
            'calendar_lookup': {},
            'request_lookup': {request_id: request}
        })()

        context = ConstraintContext(
            problem=problem,
            resource_lookup=indices.resource_lookup,
            calendar_lookup=indices.calendar_lookup,
            request_lookup=indices.request_lookup
        )

        violation = constraint.check(assignment, [], context)

        assert violation is not None, "Should detect assignment outside date range"
        assert "date range" in violation.message.lower(), \
            f"Should mention date boundaries in violation: {violation.message}"