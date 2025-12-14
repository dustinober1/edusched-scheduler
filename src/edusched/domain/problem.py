"""Problem domain model."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

if TYPE_CHECKING:
    from edusched.constraints.base import Constraint
    from edusched.domain.assignment import Assignment
    from edusched.domain.building import Building
    from edusched.domain.calendar import Calendar
    from edusched.domain.department import Department
    from edusched.domain.holiday_calendar import HolidayCalendar
    from edusched.domain.resource import Resource
    from edusched.domain.session_request import SessionRequest
    from edusched.domain.teacher import Teacher
    from edusched.objectives.base import Objective


@dataclass
class ProblemIndices:
    """Cached lookup structures for efficient constraint checking."""

    resource_lookup: Dict[str, "Resource"]
    calendar_lookup: Dict[str, "Calendar"]
    request_lookup: Dict[str, "SessionRequest"]
    building_lookup: Dict[str, "Building"]
    department_lookup: Dict[str, "Department"]
    teacher_lookup: Dict[str, "Teacher"]
    resources_by_type: Dict[str, List["Resource"]]
    qualified_resources: Dict[str, List[str]]
    time_occupancy_maps: Dict[str, Set[Tuple]]
    locked_intervals: Dict[str, Set[Tuple]]


@dataclass
class Problem:
    """Represents a complete scheduling scenario."""

    requests: List["SessionRequest"]
    resources: List["Resource"]
    calendars: List["Calendar"]
    constraints: List["Constraint"]
    objectives: List["Objective"] = field(default_factory=list)
    locked_assignments: List["Assignment"] = field(default_factory=list)
    institutional_calendar_id: Optional[str] = None
    buildings: List["Building"] = field(default_factory=list)  # Buildings for location context
    departments: List["Department"] = field(default_factory=list)  # Academic departments
    teachers: List["Teacher"] = field(default_factory=list)  # Teaching staff
    holiday_calendar: Optional["HolidayCalendar"] = None  # Academic calendar with holidays

    def validate(self) -> List[str]:
        """
        Comprehensive problem validation including timezone-aware datetime checks.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors: List[str] = []

        # Validate requests
        for request in self.requests:
            request_errors = request.validate()
            for error in request_errors:
                errors.append(str(error))

        # Validate calendars exist
        calendar_ids = {cal.id for cal in self.calendars}
        if self.institutional_calendar_id and self.institutional_calendar_id not in calendar_ids:
            errors.append(
                f"institutional_calendar_id '{self.institutional_calendar_id}' not found in calendars"
            )

        # Validate calendar properties
        for calendar in self.calendars:
            if calendar.timezone is None:
                errors.append(f"Calendar '{calendar.id}' has no timezone")

        # Validate resource calendar references
        for resource in self.resources:
            if (
                resource.availability_calendar_id
                and resource.availability_calendar_id not in calendar_ids
            ):
                errors.append(
                    f"Resource '{resource.id}' references unknown calendar "
                    f"'{resource.availability_calendar_id}'"
                )

        return errors

    def canonicalize(self) -> "Problem":
        """
        Sort inputs by ID for deterministic processing and build lookup indices.

        Returns:
            Self for method chaining
        """
        # Sort all collections by ID for deterministic ordering
        self.requests.sort(key=lambda r: r.id)
        self.resources.sort(key=lambda r: r.id)
        self.calendars.sort(key=lambda c: c.id)
        self.locked_assignments.sort(key=lambda a: (a.request_id, a.occurrence_index))

        return self

    def build_indices(self) -> ProblemIndices:
        """
        Build lookup tables and occupancy maps for efficient constraint checking.

        Returns:
            ProblemIndices with all lookup structures
        """
        # Build basic lookups
        resource_lookup = {r.id: r for r in self.resources}
        calendar_lookup = {c.id: c for c in self.calendars}
        request_lookup = {r.id: r for r in self.requests}
        building_lookup = {b.id: b for b in self.buildings}
        department_lookup = {d.id: d for d in self.departments}
        teacher_lookup = {t.id: t for t in self.teachers}

        # Build resources by type
        resources_by_type: Dict[str, List["Resource"]] = {}
        for resource in self.resources:
            if resource.resource_type not in resources_by_type:
                resources_by_type[resource.resource_type] = []
            resources_by_type[resource.resource_type].append(resource)

        # Build qualified resources (placeholder - will be enhanced in task 5.5)
        qualified_resources: Dict[str, List[str]] = {}
        for request in self.requests:
            qualified_resources[request.id] = [
                r.id for r in self.resources if r.can_satisfy(request.required_attributes)
            ]

        # Build time occupancy maps from locked assignments
        time_occupancy_maps: Dict[str, Set[Tuple]] = {}
        for resource in self.resources:
            time_occupancy_maps[resource.id] = set()

        for assignment in self.locked_assignments:
            for resource_type, resource_ids in assignment.assigned_resources.items():
                for resource_id in resource_ids:
                    if resource_id in time_occupancy_maps:
                        time_occupancy_maps[resource_id].add(
                            (assignment.start_time, assignment.end_time)
                        )

        # Build locked intervals
        locked_intervals: Dict[str, Set[Tuple]] = {}
        for resource in self.resources:
            locked_intervals[resource.id] = set()

        for assignment in self.locked_assignments:
            for resource_type, resource_ids in assignment.assigned_resources.items():
                for resource_id in resource_ids:
                    if resource_id in locked_intervals:
                        locked_intervals[resource_id].add(
                            (assignment.start_time, assignment.end_time)
                        )

        return ProblemIndices(
            resource_lookup=resource_lookup,
            calendar_lookup=calendar_lookup,
            request_lookup=request_lookup,
            building_lookup=building_lookup,
            department_lookup=department_lookup,
            teacher_lookup=teacher_lookup,
            resources_by_type=resources_by_type,
            qualified_resources=qualified_resources,
            time_occupancy_maps=time_occupancy_maps,
            locked_intervals=locked_intervals,
        )
