"""Conflict detection and resolution API routes."""

from datetime import datetime
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException

from edusched.api.database import db
from edusched.api.dependencies import get_active_user
from edusched.api.events import emit_conflict_detected, emit_conflict_resolved
from edusched.api.models import User

router = APIRouter()


@router.get("/schedule/{schedule_id}/detect")
async def detect_conflicts(
    schedule_id: str,
    current_user: User = Depends(get_active_user),
):
    """
    Detect conflicts in a schedule.

    Args:
        schedule_id: Schedule identifier
        current_user: Authenticated user

    Returns:
        List of detected conflicts

    Raises:
        HTTPException: If schedule not found
    """
    # Get schedule
    schedule = db.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Check permissions
    if schedule.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Convert assignments back to objects for checking
    conflicts = []

    # Check for resource conflicts (double bookings)
    resource_conflicts = _check_resource_conflicts(schedule.assignments)
    conflicts.extend(resource_conflicts)

    # Check for teacher conflicts
    teacher_conflicts = _check_teacher_conflicts(schedule.assignments)
    conflicts.extend(teacher_conflicts)

    # Check for student conflicts
    student_conflicts = _check_student_conflicts(schedule.assignments)
    conflicts.extend(student_conflicts)

    # Check capacity violations
    capacity_conflicts = _check_capacity_conflicts(schedule.assignments)
    conflicts.extend(capacity_conflicts)

    # Sort conflicts by severity
    conflicts.sort(key=lambda c: c["severity"], reverse=True)

    # Emit conflict detected event if conflicts found
    if conflicts:
        await emit_conflict_detected(schedule_id, conflicts)

    return {
        "schedule_id": schedule_id,
        "total_conflicts": len(conflicts),
        "conflicts": conflicts,
        "checked_at": datetime.now().isoformat(),
    }


@router.post("/schedule/{schedule_id}/resolve/{conflict_id}")
async def resolve_conflict(
    schedule_id: str,
    conflict_id: str,
    resolution_type: str,
    current_user: User = Depends(get_active_user),
):
    """
    Resolve a specific conflict.

    Args:
        schedule_id: Schedule identifier
        conflict_id: Conflict identifier
        resolution_type: Type of resolution
        current_user: Authenticated user

    Returns:
        Resolution result

    Raises:
        HTTPException: If schedule not found
    """
    # Get schedule
    schedule = db.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Check permissions
    if schedule.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # In a real implementation, this would apply the resolution
    # For now, we'll just return a success message
    resolution = {
        "conflict_id": conflict_id,
        "resolution_type": resolution_type,
        "resolved_at": datetime.now().isoformat(),
        "resolved_by": current_user.id,
    }

    # Emit conflict resolved event
    await emit_conflict_resolved(schedule_id, [resolution])

    return resolution


@router.get("/schedule/{schedule_id}/summary")
async def get_conflict_summary(
    schedule_id: str,
    current_user: User = Depends(get_active_user),
):
    """
    Get a summary of conflicts in a schedule.

    Args:
        schedule_id: Schedule identifier
        current_user: Authenticated user

    Returns:
        Conflict summary statistics
    """
    # Get schedule
    schedule = db.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Check permissions
    if schedule.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Detect conflicts
    conflicts = []

    # Check all conflict types
    resource_conflicts = _check_resource_conflicts(schedule.assignments)
    teacher_conflicts = _check_teacher_conflicts(schedule.assignments)
    student_conflicts = _check_student_conflicts(schedule.assignments)
    capacity_conflicts = _check_capacity_conflicts(schedule.assignments)

    all_conflicts = resource_conflicts + teacher_conflicts + student_conflicts + capacity_conflicts

    # Group by type
    conflict_types = {
        "resource_conflicts": len(resource_conflicts),
        "teacher_conflicts": len(teacher_conflicts),
        "student_conflicts": len(student_conflicts),
        "capacity_conflicts": len(capacity_conflicts),
    }

    # Group by severity
    severity_counts = {"high": 0, "medium": 0, "low": 0}
    for conflict in all_conflicts:
        severity_counts[conflict["severity"]] = severity_counts.get(conflict["severity"], 0) + 1

    return {
        "schedule_id": schedule_id,
        "total_conflicts": len(all_conflicts),
        "conflict_types": conflict_types,
        "severity_distribution": severity_counts,
        "conflict_rate": len(all_conflicts) / max(len(schedule.assignments), 1),
        "last_checked": datetime.now().isoformat(),
    }


def _check_resource_conflicts(assignments: List[Dict]) -> List[Dict]:
    """Check for resource (room) conflicts."""
    conflicts = []
    resource_bookings = {}

    for assignment in assignments:
        resource_id = assignment.get("resource_id")
        start_time = datetime.fromisoformat(assignment["start_time"])
        end_time = datetime.fromisoformat(assignment["end_time"])

        if resource_id not in resource_bookings:
            resource_bookings[resource_id] = []

        # Check for overlaps
        for booking in resource_bookings[resource_id]:
            booking_start = datetime.fromisoformat(booking["start_time"])
            booking_end = datetime.fromisoformat(booking["end_time"])

            if _time_overlaps(start_time, end_time, booking_start, booking_end):
                conflicts.append(
                    {
                        "id": f"resource_{resource_id}_{len(conflicts)}",
                        "type": "resource_conflict",
                        "severity": "high",
                        "resource_id": resource_id,
                        "resource_name": assignment.get("room_name", "Unknown"),
                        "conflicting_assignments": [
                            booking["request_id"],
                            assignment["request_id"],
                        ],
                        "time_overlap": {
                            "start": max(start_time, booking_start).isoformat(),
                            "end": min(end_time, booking_end).isoformat(),
                        },
                        "description": f"Room {assignment.get('room_name', resource_id)} is double booked",
                    }
                )

        resource_bookings[resource_id].append(assignment)

    return conflicts


def _check_teacher_conflicts(assignments: List[Dict]) -> List[Dict]:
    """Check for teacher conflicts."""
    conflicts = []
    teacher_bookings = {}

    for assignment in assignments:
        # This assumes assignments have teacher info
        teacher_id = assignment.get("teacher_id")
        if not teacher_id:
            continue

        start_time = datetime.fromisoformat(assignment["start_time"])
        end_time = datetime.fromisoformat(assignment["end_time"])

        if teacher_id not in teacher_bookings:
            teacher_bookings[teacher_id] = []

        # Check for overlaps
        for booking in teacher_bookings[teacher_id]:
            booking_start = datetime.fromisoformat(booking["start_time"])
            booking_end = datetime.fromisoformat(booking["end_time"])

            if _time_overlaps(start_time, end_time, booking_start, booking_end):
                conflicts.append(
                    {
                        "id": f"teacher_{teacher_id}_{len(conflicts)}",
                        "type": "teacher_conflict",
                        "severity": "high",
                        "teacher_id": teacher_id,
                        "teacher_name": assignment.get("teacher_name", "Unknown"),
                        "conflicting_assignments": [
                            booking["request_id"],
                            assignment["request_id"],
                        ],
                        "time_overlap": {
                            "start": max(start_time, booking_start).isoformat(),
                            "end": min(end_time, booking_end).isoformat(),
                        },
                        "description": f"Teacher {assignment.get('teacher_name', teacher_id)} is scheduled for overlapping classes",
                    }
                )

        teacher_bookings[teacher_id].append(assignment)

    return conflicts


def _check_student_conflicts(assignments: List[Dict]) -> List[Dict]:
    """Check for student conflicts (placeholder for student enrollment data)."""
    # In a real implementation, this would check actual student enrollments
    # For now, return empty list
    return []


def _check_capacity_conflicts(assignments: List[Dict]) -> List[Dict]:
    """Check for capacity violations."""
    conflicts = []

    for assignment in assignments:
        enrollment = assignment.get("enrollment", 0)
        capacity = assignment.get("capacity", 0)

        if enrollment > capacity:
            conflicts.append(
                {
                    "id": f"capacity_{assignment['request_id']}",
                    "type": "capacity_violation",
                    "severity": "medium",
                    "request_id": assignment["request_id"],
                    "resource_id": assignment["resource_id"],
                    "room_name": assignment.get("room_name", "Unknown"),
                    "enrollment": enrollment,
                    "capacity": capacity,
                    "over_capacity": enrollment - capacity,
                    "description": f"Room capacity ({capacity}) exceeded by enrollment ({enrollment})",
                }
            )

    return conflicts


def _time_overlaps(start1: datetime, end1: datetime, start2: datetime, end2: datetime) -> bool:
    """Check if two time ranges overlap."""
    return start1 < end2 and start2 < end1


@router.get("/types")
async def get_conflict_types():
    """
    Get list of supported conflict types.

    Returns:
        Conflict types with descriptions
    """
    return {
        "conflict_types": [
            {
                "type": "resource_conflict",
                "name": "Room Conflict",
                "description": "Double booking of the same room",
                "severity": "high",
            },
            {
                "type": "teacher_conflict",
                "name": "Teacher Conflict",
                "description": "Teacher scheduled for overlapping classes",
                "severity": "high",
            },
            {
                "type": "student_conflict",
                "name": "Student Conflict",
                "description": "Student enrolled in overlapping classes",
                "severity": "high",
            },
            {
                "type": "capacity_violation",
                "name": "Capacity Violation",
                "description": "Enrollment exceeds room capacity",
                "severity": "medium",
            },
        ]
    }


@router.get("/resolution/types")
async def get_resolution_types():
    """
    Get list of conflict resolution types.

    Returns:
        Resolution types with descriptions
    """
    return {
        "resolution_types": [
            {
                "type": "move_assignment",
                "name": "Move Assignment",
                "description": "Move one of the conflicting assignments to a different time or room",
            },
            {
                "type": "swap_assignments",
                "name": "Swap Assignments",
                "description": "Swap time slots between two assignments",
            },
            {
                "type": "change_room",
                "name": "Change Room",
                "description": "Move one assignment to a different room",
            },
            {
                "type": "manual_override",
                "name": "Manual Override",
                "description": "Mark conflict as resolved (use with caution)",
            },
        ]
    }
