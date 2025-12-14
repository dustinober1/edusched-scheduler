"""Schedule management API routes."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse

from edusched.core_api import solve
from edusched.api.dependencies import get_active_user
from edusched.api.models import (
    AssignmentModel,
    ScheduleRequest,
    ScheduleResponse,
    User,
)
from edusched.domain.problem import Problem
from edusched.utils.data_import import DataImporter
from edusched.utils.export import export_schedule, get_supported_formats

router = APIRouter()


@router.post("/", response_model=ScheduleResponse)
async def create_schedule(
    request_data: ScheduleRequest,
    current_user: User = Depends(get_active_user),
):
    """
    Create a new schedule.

    Args:
        request_data: Schedule generation request
        current_user: Authenticated user

    Returns:
        Generated schedule or error details
    """
    try:
        # Create a minimal problem for testing
        # In production, this would load from database or uploaded files
        problem = Problem(
            requests=[],
            resources=[],
            calendars=[],
            constraints=[],
        )

        # Solve the problem
        result = solve(
            problem,
            backend=request_data.solver or "auto",
            seed=request_data.seed,
            fallback=True,
        )

        # Convert assignments to API model
        assignments = []
        for assignment in result.assignments:
            assignments.append(
                AssignmentModel(
                    request_id=str(assignment.request.id),
                    resource_id=str(assignment.resource.id),
                    start_time=assignment.start_time.isoformat(),
                    end_time=assignment.end_time.isoformat(),
                    course_code=getattr(assignment.request, 'course_code', None),
                    teacher_name=getattr(assignment.request, 'teacher_name', None),
                    room_name=getattr(assignment.resource, 'name', None),
                    building_id=getattr(assignment.resource, 'building_id', None),
                    enrollment=getattr(assignment.request, 'enrollment', None),
                    capacity=getattr(assignment.resource, 'capacity', None),
                )
            )

        return ScheduleResponse(
            id=str(uuid.uuid4()),
            status="success" if assignments else "no_solution",
            total_assignments=len(assignments),
            solver_time_ms=result.solver_time_ms,
            iterations=getattr(result, 'iterations', 0),
            assignments=assignments,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create schedule: {str(e)}",
        )


@router.get("/{schedule_id}")
async def get_schedule(
    schedule_id: str,
    current_user: User = Depends(get_active_user),
):
    """
    Get a specific schedule by ID.

    Args:
        schedule_id: Schedule identifier
        current_user: Authenticated user

    Returns:
        Schedule details

    Raises:
        HTTPException: If schedule not found
    """
    # Placeholder implementation
    # In production, this would retrieve from database
    raise HTTPException(
        status_code=501,
        detail="Schedule retrieval not yet implemented",
    )


@router.put("/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    request_data: ScheduleRequest,
    current_user: User = Depends(get_active_user),
):
    """
    Update an existing schedule.

    Args:
        schedule_id: Schedule identifier
        request_data: Updated schedule request
        current_user: Authenticated user

    Returns:
        Updated schedule

    Raises:
        HTTPException: If schedule not found
    """
    # Placeholder implementation
    raise HTTPException(
        status_code=501,
        detail="Schedule update not yet implemented",
    )


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    current_user: User = Depends(get_active_user),
):
    """
    Delete a schedule.

    Args:
        schedule_id: Schedule identifier
        current_user: Authenticated user

    Returns:
        Success message

    Raises:
        HTTPException: If schedule not found
    """
    # Placeholder implementation
    raise HTTPException(
        status_code=501,
        detail="Schedule deletion not yet implemented",
    )


@router.get("/{schedule_id}/export")
async def export_schedule_endpoint(
    schedule_id: str,
    format: str = Query("json", description="Export format"),
    current_user: User = Depends(get_active_user),
):
    """
    Export a schedule in various formats.

    Args:
        schedule_id: Schedule identifier
        format: Export format (json, csv, ical, excel)
        current_user: Authenticated user

    Returns:
        Exported schedule file

    Raises:
        HTTPException: If schedule not found or format invalid
    """
    # Validate format
    if format not in get_supported_formats():
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {format}. Supported: {', '.join(get_supported_formats())}",
        )

    # Placeholder implementation
    # In production, this would retrieve the schedule from database
    # and export it using the export_schedule utility

    # Create a dummy result for testing
    problem = Problem(requests=[], resources=[], calendars=[], constraints=[])
    from edusched.domain.result import Result
    dummy_result = Result(
        assignments=[],
        problem=problem,
        solver_time_ms=0,
        status="no_solution",
    )

    # Generate export file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"schedule_{schedule_id}_{timestamp}.{format}"
    export_path = Path(f"/tmp/{filename}")

    try:
        export_schedule(dummy_result, export_path, format)

        # Determine media type
        media_types = {
            "json": "application/json",
            "csv": "text/csv",
            "ical": "text/calendar",
            "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }

        return FileResponse(
            path=export_path,
            filename=filename,
            media_type=media_types.get(format, "application/octet-stream"),
        )
    finally:
        # Clean up temporary file
        if export_path.exists():
            export_path.unlink()


@router.get("/")
async def list_schedules(
    skip: int = Query(0, ge=0, description="Number of schedules to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of schedules to return"),
    current_user: User = Depends(get_active_user),
):
    """
    List schedules with pagination.

    Args:
        skip: Number of schedules to skip
        limit: Maximum number of schedules to return
        current_user: Authenticated user

    Returns:
        List of schedules
    """
    # Placeholder implementation
    return {
        "schedules": [],
        "total": 0,
        "skip": skip,
        "limit": limit,
    }


@router.get("/formats/supported")
async def get_export_formats():
    """
    Get list of supported export formats.

    Returns:
        Supported formats and their file extensions
    """
    from edusched.utils.export import get_format_extensions

    return {
        "formats": get_supported_formats(),
        "extensions": get_format_extensions(),
    }