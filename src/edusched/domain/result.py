"""Result domain model."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

if TYPE_CHECKING:
    from edusched.domain.assignment import Assignment


@dataclass
class InfeasibilityReport:
    """Structured report for infeasible scheduling problems."""

    unscheduled_requests: List[str]
    violated_constraints_summary: Dict[str, int] = field(default_factory=dict)
    top_conflicts: List[str] = field(default_factory=list)
    per_request_explanations: Dict[str, List[str]] = field(default_factory=dict)

    def summary(self) -> str:
        """Generate human-readable summary of infeasibility."""
        lines = [f"Infeasible: {len(self.unscheduled_requests)} requests could not be scheduled"]
        if self.violated_constraints_summary:
            lines.append("Violated constraints:")
            for constraint_type, count in self.violated_constraints_summary.items():
                lines.append(f"  - {constraint_type}: {count} violations")
        return "\n".join(lines)

    def recommendations(self) -> List[str]:
        """Generate actionable suggestions for resolving conflicts."""
        recommendations = []
        if self.violated_constraints_summary:
            recommendations.append("Review and relax conflicting constraints")
        if self.unscheduled_requests:
            recommendations.append("Consider extending date ranges for unscheduled requests")
        return recommendations


@dataclass
class Result:
    """Represents result of a scheduling operation."""

    status: Literal["feasible", "partial", "infeasible"]
    assignments: List["Assignment"]
    unscheduled_requests: List[str]
    objective_score: Optional[float] = None
    backend_used: str = "unknown"
    seed_used: Optional[int] = None
    solve_time_seconds: float = 0.0
    diagnostics: Optional[InfeasibilityReport] = None

    @property
    def solver_time_ms(self) -> float:
        """Get solver time in milliseconds for API compatibility."""
        return self.solve_time_seconds * 1000

    @property
    def feasible(self) -> bool:
        """Backward compatibility property."""
        return self.status == "feasible"

    def to_records(self) -> List[Dict[str, Any]]:
        """
        Export as list of dictionaries using core dependencies.

        Schema: start_time, end_time, request_id, cohort_id, resource_ids, backend, objective_score

        Returns:
            List of dictionaries with assignment data
        """
        records = []
        for assignment in self.assignments:
            record = {
                "start_time": assignment.start_time,
                "end_time": assignment.end_time,
                "request_id": assignment.request_id,
                "cohort_id": assignment.cohort_id,
                "resource_ids": assignment.assigned_resources,
                "backend": self.backend_used,
                "objective_score": self.objective_score,
            }
            records.append(record)
        return records

    def to_dataframe(self) -> Any:
        """
        Export as pandas DataFrame with documented schema.

        Raises:
            MissingOptionalDependency: If pandas is not installed

        Returns:
            pandas DataFrame with assignment data
        """
        try:
            import pandas as pd
        except ImportError:
            from edusched.errors import MissingOptionalDependency

            raise MissingOptionalDependency(
                feature="DataFrame export",
                install_command="pip install edusched[pandas]",
            )

        records = self.to_records()
        df = pd.DataFrame(records)
        df.attrs["schema_version"] = "1.0"
        return df

    def to_ics(self, filename: str) -> None:
        """
        Export as ICS calendar file.

        Requires icalendar extra.

        Args:
            filename: Output file path

        Raises:
            MissingOptionalDependency: If icalendar is not installed
        """
        try:
            from icalendar import Calendar as ICalendar
            from icalendar import Event
        except ImportError:
            from edusched.errors import MissingOptionalDependency

            raise MissingOptionalDependency(
                feature="ICS export",
                install_command="pip install edusched[ics]",
            )

        cal = ICalendar()
        cal.add("prodid", "-//EduSched//EduSched//EN")
        cal.add("version", "2.0")

        for assignment in self.assignments:
            event = Event()
            event.add("summary", f"Session {assignment.request_id}")
            event.add("dtstart", assignment.start_time)
            event.add("dtend", assignment.end_time)
            event.add("uid", f"{assignment.request_id}-{assignment.occurrence_index}@edusched")
            cal.add_component(event)

        with open(filename, "wb") as f:
            f.write(cal.to_ical())

    def to_excel(self, filename: str) -> None:
        """
        Export as formatted Excel spreadsheet.

        Requires openpyxl extra.

        Args:
            filename: Output file path

        Raises:
            MissingOptionalDependency: If openpyxl is not installed
        """
        try:
            from openpyxl import Workbook
        except ImportError:
            from edusched.errors import MissingOptionalDependency

            raise MissingOptionalDependency(
                feature="Excel export",
                install_command="pip install edusched[excel]",
            )

        df = self.to_dataframe()
        df.to_excel(filename, index=False, sheet_name="Schedule")
