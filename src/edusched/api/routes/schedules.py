"""Enhanced schedule management API routes with persistence and real-time updates."""

import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse

from edusched.core_api import solve
from edusched.api.database import db
from edusched.api.dependencies import get_active_user
from edusched.api.events import (
    emit_schedule_created,
    emit_schedule_updated,
    emit_solver_started,
    emit_solver_completed,
    emit_solver_failed,
)
from edusched.api.models import (
    AssignmentModel,
    ScheduleRequest,
    ScheduleResponse,
    User,
)
from edusched.domain.problem import Problem
from edusched.domain.result import Result
from edusched.utils.export import export_schedule, get_supported_formats, get_format_extensions

router = APIRouter()


@router.post("/", response_model=ScheduleResponse)
async def create_schedule(
    request_data: ScheduleRequest,
    name: Optional[str] = Query(None, description="Schedule name"),
    current_user: User = Depends(get_active_user),
):
    """
    Create a new schedule.

    Args:
        request_data: Schedule generation request
        name: Optional schedule name
        current_user: Authenticated user

    Returns:
        Generated schedule or error details
    """
    try:
        # Generate schedule name if not provided
        if not name:
            name = f"Schedule {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # Emit solver started event
        await emit_solver_started(
            "temp",  # Will be updated with actual schedule ID
            current_user.id,
            {"solver": request_data.solver, "seed": request_data.seed},
        )

        # Create a problem with sample data for now
        # In production, this would load from user's data
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

        # Create schedule in database
        schedule_id = db.create_schedule(
            name=name,
            user_id=current_user.id,
            assignments=assignments,
            metadata={
                "total_assignments": len(assignments),
                "solver": request_data.solver or "auto",
                "optimize": request_data.optimize,
            },
            solver_config={
                "solver": request_data.solver,
                "seed": request_data.seed,
                "optimize": request_data.optimize,
            },
        )

        # Emit schedule created event
        await emit_schedule_created(
            schedule_id,
            current_user.id,
            {
                "name": name,
                "total_assignments": len(assignments),
                "status": "success" if assignments else "no_solution",
            },
        )

        # Emit solver completed event
        await emit_solver_completed(
            schedule_id,
            current_user.id,
            {
                "status": "success" if assignments else "no_solution",
                "total_assignments": len(assignments),
                "solver_time_ms": result.solver_time_ms,
            },
        )

        return ScheduleResponse(
            id=schedule_id,
            status="success" if assignments else "no_solution",
            total_assignments=len(assignments),
            solver_time_ms=result.solver_time_ms,
            iterations=getattr(result, 'iterations', 0),
            assignments=assignments,
        )

    except Exception as e:
        # Emit solver failed event
        await emit_solver_failed(
            "temp",
            current_user.id,
            str(e),
            {"solver": request_data.solver, "seed": request_data.seed},
        )

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
    schedule = db.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Check if user owns the schedule (in production, add permissions)
    if schedule.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Convert assignments
    assignments = [
        AssignmentModel(**a) for a in schedule.assignments
    ]

    return {
        "id": schedule.id,
        "name": schedule.name,
        "status": schedule.status,
        "created_at": schedule.created_at.isoformat(),
        "updated_at": schedule.updated_at.isoformat(),
        "total_assignments": len(assignments),
        "assignments": assignments,
        "metadata": schedule.metadata,
        "solver_config": schedule.solver_config,
    }


@router.put("/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    name: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_active_user),
):
    """
    Update an existing schedule.

    Args:
        schedule_id: Schedule identifier
        name: New name (optional)
        status: New status (optional)
        current_user: Authenticated user

    Returns:
        Updated schedule

    Raises:
        HTTPException: If schedule not found
    """
    schedule = db.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Check permissions
    if schedule.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Update schedule
    success = db.update_schedule(
        schedule_id,
        name=name,
        metadata={"status": status} if status else None,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update schedule")

    # Emit update event
    await emit_schedule_updated(
        schedule_id,
        current_user.id,
        {"updated_fields": [k for k in ["name", "status"] if locals().get(k)]},
    )

    # Get updated schedule
    updated = db.get_schedule(schedule_id)
    return {
        "id": updated.id,
        "name": updated.name,
        "status": updated.status,
        "updated_at": updated.updated_at.isoformat(),
    }


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
    schedule = db.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Check permissions
    if schedule.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Delete schedule
    success = db.delete_schedule(schedule_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete schedule")

    return {"message": "Schedule deleted successfully"}


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

    # Get schedule
    schedule = db.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Check permissions
    if schedule.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Create Result object from schedule
    problem = Problem(requests=[], resources=[], calendars=[], constraints=[])
    result = Result(
        assignments=[],  # Would need to reconstruct from assignments
        problem=problem,
        solver_time_ms=0,
        status=schedule.status,
    )

    # Generate export file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{schedule.name.replace(' ', '_')}_{timestamp}.{format}"
    export_path = Path(f"/tmp/{filename}")

    try:
        # Export using the data directly
        from edusched.utils.export import export_to_json, export_to_csv, export_to_ical, export_to_excel

        if format == "json":
            export_to_json(result, export_path)
        elif format == "csv":
            export_to_csv(result, export_path)
        elif format == "ical":
            export_to_ical(result, export_path)
        elif format == "excel":
            export_to_excel(result, export_path)

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
    search: Optional[str] = Query(None, description="Search term for schedule names"),
    current_user: User = Depends(get_active_user),
):
    """
    List schedules for the current user with pagination.

    Args:
        skip: Number of schedules to skip
        limit: Maximum number of schedules to return
        search: Search term for schedule names
        current_user: Authenticated user

    Returns:
        List of schedules
    """
    if search:
        # Search schedules
        schedules = db.search_schedules(
            user_id=current_user.id,
            name_filter=search,
            limit=limit,
        )
    else:
        # Get user's schedules
        schedules = db.get_user_schedules(
            current_user.id,
            skip=skip,
            limit=limit,
        )

    # Convert to response format
    schedule_list = []
    for schedule in schedules:
        schedule_list.append({
            "id": schedule.id,
            "name": schedule.name,
            "status": schedule.status,
            "created_at": schedule.created_at.isoformat(),
            "updated_at": schedule.updated_at.isoformat(),
            "total_assignments": len(schedule.assignments),
            "metadata": schedule.metadata,
        })

    return {
        "schedules": schedule_list,
        "total": db.count_user_schedules(current_user.id),
        "skip": skip,
        "limit": limit,
    }


@router.get("/stats/overview")
async def get_schedule_stats(current_user: User = Depends(get_active_user)):
    """
    Get scheduling statistics for the current user.

    Args:
        current_user: Authenticated user

    Returns:
        Scheduling statistics
    """
    user_schedules = db.get_user_schedules(current_user.id, limit=1000)

    total_schedules = len(user_schedules)
    total_assignments = sum(len(s.assignments) for s in user_schedules)

    # Calculate average solver time
    solver_times = [
        s.metadata.get("solver_time_ms", 0) for s in user_schedules
        if "solver_time_ms" in s.metadata
    ]
    avg_solver_time = sum(solver_times) / len(solver_times) if solver_times else 0

    # Status distribution
    status_counts = {}
    for schedule in user_schedules:
        status = schedule.status
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "total_schedules": total_schedules,
        "total_assignments": total_assignments,
        "avg_assignments_per_schedule": total_assignments / max(total_schedules, 1),
        "avg_solver_time_ms": avg_solver_time,
        "status_distribution": status_counts,
        "last_updated": max(
            (s.updated_at for s in user_schedules),
            default=datetime.now()
        ).isoformat(),
    }


@router.get("/formats/supported")
async def get_export_formats():
    """
    Get list of supported export formats.

    Returns:
        Supported formats and their file extensions
    """
    return {
        "formats": get_supported_formats(),
        "extensions": get_format_extensions(),
    }


@router.post("/{schedule_id}/duplicate")
async def duplicate_schedule(
    schedule_id: str,
    name: Optional[str] = Query(None, description="New schedule name"),
    current_user: User = Depends(get_active_user),
):
    """
    Duplicate an existing schedule.

    Args:
        schedule_id: Schedule to duplicate
        name: Name for the new schedule
        current_user: Authenticated user

    Returns:
        New schedule details

    Raises:
        HTTPException: If schedule not found
    """
    # Get original schedule
    original = db.get_schedule(schedule_id)
    if not original:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Check permissions
    if original.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Create name for duplicate
    if not name:
        name = f"{original.name} (Copy)"

    # Convert assignments
    assignments = [
        AssignmentModel(**a) for a in original.assignments
    ]

    # Create new schedule
    new_schedule_id = db.create_schedule(
        name=name,
        user_id=current_user.id,
        assignments=assignments,
        metadata=original.metadata.copy(),
        solver_config=original.solver_config.copy(),
    )

    # Emit creation event
    await emit_schedule_created(
        new_schedule_id,
        current_user.id,
        {
            "name": name,
            "duplicated_from": schedule_id,
            "total_assignments": len(assignments),
        },
    )

    # Get new schedule
    new_schedule = db.get_schedule(new_schedule_id)
    return {
        "id": new_schedule.id,
        "name": new_schedule.name,
        "status": new_schedule.status,
        "created_at": new_schedule.created_at.isoformat(),
        "total_assignments": len(assignments),
        "duplicated_from": schedule_id,
    }