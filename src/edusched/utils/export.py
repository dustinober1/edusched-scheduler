"""Schedule export utilities for EduSched.

Provides functionality to export schedules in various formats
including iCal, Excel, PDF, and JSON.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Union

if TYPE_CHECKING:
    from edusched.domain.assignment import Assignment
    from edusched.domain.result import Result


def export_to_json(result: "Result", output_path: Path) -> None:
    """Export schedule to JSON format.

    Args:
        result: Result object containing schedule
        output_path: Path to save JSON file
    """
    # Convert assignments to JSON-serializable format
    assignments_data = []
    for assignment in result.assignments:
        assignment_data = {
            "request": {
                "id": str(assignment.request.id),
                "course_code": getattr(assignment.request, 'course_code', str(assignment.request.id)),
                "duration": float(assignment.request.duration),
                "enrollment": getattr(assignment.request, 'enrollment', 0),
            },
            "resource": {
                "id": str(assignment.resource.id),
                "name": getattr(assignment.resource, 'name', str(assignment.resource.id)),
                "type": getattr(assignment.resource, 'resource_type', 'unknown'),
                "capacity": getattr(assignment.resource, 'capacity', 0),
                "building": getattr(assignment.resource, 'building_id', 'unknown'),
            },
            "schedule": {
                "start_time": assignment.start_time.isoformat(),
                "end_time": assignment.end_time.isoformat(),
                "day_of_week": assignment.start_time.strftime('%A'),
                "date": assignment.start_time.strftime('%Y-%m-%d'),
                "time_slot": f"{assignment.start_time.strftime('%H:%M')} - {assignment.end_time.strftime('%H:%M')}",
            },
        }

        # Add teacher information if available
        if hasattr(assignment.request, 'teacher_id'):
            assignment_data["teacher"] = {
                "id": str(assignment.request.teacher_id),
                "name": getattr(assignment.request, 'teacher_name', 'Unknown'),
            }

        assignments_data.append(assignment_data)

    # Create export data structure
    export_data = {
        "metadata": {
            "exported_at": datetime.now().isoformat(),
            "total_assignments": len(result.assignments),
            "solver_status": getattr(result, 'status', 'unknown'),
            "solver_time_ms": result.solver_time_ms,
            "iterations": getattr(result, 'iterations', 0),
        },
        "assignments": assignments_data,
    }

    # Add summary statistics
    if result.assignments:
        # Group by resource
        resource_usage = {}
        for assignment in result.assignments:
            resource_id = str(assignment.resource.id)
            resource_usage[resource_id] = resource_usage.get(resource_id, 0) + 1

        # Group by day
        daily_schedule = {}
        for assignment in result.assignments:
            date = assignment.start_time.strftime('%Y-%m-%d')
            daily_schedule[date] = daily_schedule.get(date, 0) + 1

        export_data["statistics"] = {
            "resource_utilization": resource_usage,
            "daily_distribution": daily_schedule,
            "utilization_rate": len(result.assignments) / len(result.problem.resources) if result.problem.resources else 0,
        }

    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)


def export_to_csv(result: "Result", output_path: Path) -> None:
    """Export schedule to CSV format.

    Args:
        result: Result object containing schedule
        output_path: Path to save CSV file
    """
    import csv

    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'Date',
            'Day',
            'Start Time',
            'End Time',
            'Course Code',
            'Teacher',
            'Room',
            'Building',
            'Enrollment',
            'Capacity',
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for assignment in result.assignments:
            row = {
                'Date': assignment.start_time.strftime('%Y-%m-%d'),
                'Day': assignment.start_time.strftime('%A'),
                'Start Time': assignment.start_time.strftime('%H:%M'),
                'End Time': assignment.end_time.strftime('%H:%M'),
                'Course Code': getattr(assignment.request, 'course_code', str(assignment.request.id)),
                'Teacher': getattr(assignment.request, 'teacher_name', ''),
                'Room': getattr(assignment.resource, 'name', str(assignment.resource.id)),
                'Building': getattr(assignment.resource, 'building_id', ''),
                'Enrollment': getattr(assignment.request, 'enrollment', ''),
                'Capacity': getattr(assignment.resource, 'capacity', ''),
            }
            writer.writerow(row)


def export_to_ical(result: "Result", output_path: Path) -> None:
    """Export schedule to iCal format.

    Args:
        result: Result object containing schedule
        output_path: Path to save ICS file
    """
    try:
        from icalendar import Calendar, Event
    except ImportError:
        raise ImportError(
            "icalendar package is required for iCal export. "
            "Install with: pip install icalendar"
        )

    # Create calendar
    cal = Calendar()
    cal.add('prodid', '-//EduSched Schedule//edusched//')
    cal.add('version', '2.0')
    cal.add('name', 'Academic Schedule')
    cal.add('description', f'Schedule generated by EduSched on {datetime.now().strftime("%Y-%m-%d")}')

    # Add events for each assignment
    for assignment in result.assignments:
        event = Event()
        event.add('summary', getattr(assignment.request, 'course_code', str(assignment.request.id)))

        # Add teacher to summary if available
        if hasattr(assignment.request, 'teacher_name'):
            event.add('summary', f"{event.get('summary')} - {assignment.request.teacher_name}")

        # Set location
        room_name = getattr(assignment.resource, 'name', str(assignment.resource.id))
        if hasattr(assignment.resource, 'building_id'):
            room_name = f"{room_name} ({assignment.resource.building_id})"
        event.add('location', room_name)

        # Set times
        event.add('dtstart', assignment.start_time)
        event.add('dtend', assignment.end_time)

        # Add description
        description = f"Enrollment: {getattr(assignment.request, 'enrollment', 'N/A')}\n"
        description += f"Room Capacity: {getattr(assignment.resource, 'capacity', 'N/A')}"
        event.add('description', description)

        # Add UID (unique identifier)
        event.add('uid', f"{assignment.request.id}@{assignment.resource.id}@{assignment.start_time.isoformat()}")

        cal.add_component(event)

    # Write to file
    with open(output_path, 'wb') as f:
        f.write(cal.to_ical())


def export_to_excel(result: "Result", output_path: Path) -> None:
    """Export schedule to Excel format.

    Args:
        result: Result object containing schedule
        output_path: Path to save Excel file
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError(
            "pandas package is required for Excel export. "
            "Install with: pip install pandas openpyxl"
        )

    # Create DataFrame from assignments
    data = []
    for assignment in result.assignments:
        row = {
            'Date': assignment.start_time.strftime('%Y-%m-%d'),
            'Day': assignment.start_time.strftime('%A'),
            'Start Time': assignment.start_time.strftime('%H:%M'),
            'End Time': assignment.end_time.strftime('%H:%M'),
            'Duration (hrs)': float(assignment.request.duration),
            'Course Code': getattr(assignment.request, 'course_code', str(assignment.request.id)),
            'Course ID': str(assignment.request.id),
            'Teacher Name': getattr(assignment.request, 'teacher_name', ''),
            'Teacher ID': getattr(assignment.request, 'teacher_id', ''),
            'Room Name': getattr(assignment.resource, 'name', str(assignment.resource.id)),
            'Room ID': str(assignment.resource.id),
            'Room Type': getattr(assignment.resource, 'resource_type', ''),
            'Building': getattr(assignment.resource, 'building_id', ''),
            'Enrollment': getattr(assignment.request, 'enrollment', 0),
            'Room Capacity': getattr(assignment.resource, 'capacity', 0),
            'Utilization %': round(
                (getattr(assignment.request, 'enrollment', 0) /
                 max(getattr(assignment.resource, 'capacity', 1), 1)) * 100, 1
            ),
        }
        data.append(row)

    df = pd.DataFrame(data)

    # Create Excel writer with multiple sheets
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Main schedule sheet
        df.to_excel(writer, sheet_name='Schedule', index=False)

        # Summary statistics sheet
        summary_data = {
            'Metric': [
                'Total Classes',
                'Total Hours Scheduled',
                'Average Class Duration',
                'Average Enrollment',
                'Average Utilization',
                'Solver Time (ms)',
                'Iterations',
            ],
            'Value': [
                len(result.assignments),
                sum(assignment.request.duration for assignment in result.assignments),
                sum(assignment.request.duration for assignment in result.assignments) / max(len(result.assignments), 1),
                sum(getattr(a.request, 'enrollment', 0) for a in result.assignments) / max(len(result.assignments), 1),
                sum(
                    (getattr(a.request, 'enrollment', 0) / max(getattr(a.resource, 'capacity', 1), 1)) * 100
                    for a in result.assignments
                ) / max(len(result.assignments), 1),
                result.solver_time_ms,
                getattr(result, 'iterations', 0),
            ],
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)

        # Room utilization sheet
        if result.assignments:
            room_usage = {}
            for assignment in result.assignments:
                room_id = str(assignment.resource.id)
                room_name = getattr(assignment.resource, 'name', room_id)
                if room_id not in room_usage:
                    room_usage[room_id] = {
                        'Room Name': room_name,
                        'Room Type': getattr(assignment.resource, 'resource_type', ''),
                        'Capacity': getattr(assignment.resource, 'capacity', 0),
                        'Classes': 0,
                        'Total Hours': 0,
                        'Total Enrollment': 0,
                    }
                room_usage[room_id]['Classes'] += 1
                room_usage[room_id]['Total Hours'] += float(assignment.request.duration)
                room_usage[room_id]['Total Enrollment'] += getattr(assignment.request, 'enrollment', 0)

            room_df = pd.DataFrame.from_dict(room_usage, orient='index')
            room_df.reset_index(drop=True, inplace=True)
            room_df.to_excel(writer, sheet_name='Room Utilization', index=False)


def export_schedule(
    result: "Result",
    output_path: Path,
    format: str = "auto",
) -> None:
    """
    Export schedule to specified format.

    Args:
        result: Result object containing schedule
        output_path: Output file path
        format: Export format ("auto", "json", "csv", "ical", "excel")

    Raises:
        ValueError: If format is not supported
        ImportError: If required dependencies are missing
    """
    # Determine format from file extension if auto
    if format == "auto":
        suffix = output_path.suffix.lower()
        if suffix == ".json":
            format = "json"
        elif suffix == ".csv":
            format = "csv"
        elif suffix in [".ical", ".ics"]:
            format = "ical"
        elif suffix in [".xlsx", ".xls"]:
            format = "excel"
        else:
            format = "json"  # Default to JSON

    # Export based on format
    if format == "json":
        export_to_json(result, output_path)
    elif format == "csv":
        export_to_csv(result, output_path)
    elif format == "ical":
        export_to_ical(result, output_path)
    elif format == "excel":
        export_to_excel(result, output_path)
    else:
        raise ValueError(f"Unsupported export format: {format}")


def get_supported_formats() -> List[str]:
    """Get list of supported export formats.

    Returns:
        List of supported format names
    """
    return ["json", "csv", "ical", "excel"]


def get_format_extensions() -> Dict[str, List[str]]:
    """Get mapping of formats to file extensions.

    Returns:
        Dictionary mapping format names to list of extensions
    """
    return {
        "json": [".json"],
        "csv": [".csv"],
        "ical": [".ical", ".ics"],
        "excel": [".xlsx", ".xls"],
    }