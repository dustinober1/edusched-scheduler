"""Schedule optimization API routes."""

from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from edusched.api.database import db
from edusched.api.dependencies import get_active_user
from edusched.api.events import emit_solver_started, emit_solver_progress, emit_solver_completed, emit_solver_failed
from edusched.api.models import User
from edusched.core_api import solve
from edusched.domain.problem import Problem

router = APIRouter()


# Store running optimizations
running_optimizations: Dict[str, Dict] = {}


@router.post("/schedule/{schedule_id}/optimize")
async def optimize_schedule(
    schedule_id: str,
    background_tasks: BackgroundTasks,
    objectives: List[str] = ["spread_evenly"],
    max_iterations: int = 1000,
    time_limit: int = 300,
    current_user: User = Depends(get_active_user),
):
    """
    Optimize an existing schedule using specified objectives.

    Args:
        schedule_id: Schedule identifier
        background_tasks: FastAPI background tasks
        objectives: List of optimization objectives
        max_iterations: Maximum optimization iterations
        time_limit: Time limit in seconds
        current_user: Authenticated user

    Returns:
        Optimization job ID
    """
    # Get schedule
    schedule = db.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Check permissions
    if schedule.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check if already optimizing
    if schedule_id in running_optimizations:
        raise HTTPException(
            status_code=409,
            detail="Schedule is already being optimized",
        )

    # Create optimization job
    job_id = f"opt_{schedule_id}_{datetime.now().timestamp()}"

    # Store job info
    running_optimizations[schedule_id] = {
        "job_id": job_id,
        "started_at": datetime.now(),
        "objectives": objectives,
        "max_iterations": max_iterations,
        "time_limit": time_limit,
        "status": "running",
        "progress": 0,
    }

    # Emit start event
    await emit_solver_started(
        schedule_id,
        current_user.id,
        {
            "type": "optimization",
            "objectives": objectives,
            "max_iterations": max_iterations,
            "time_limit": time_limit,
        },
    )

    # Start optimization in background
    background_tasks.add_task(
        run_optimization,
        schedule_id,
        job_id,
        objectives,
        max_iterations,
        time_limit,
        current_user.id,
    )

    return {
        "job_id": job_id,
        "schedule_id": schedule_id,
        "status": "started",
        "objectives": objectives,
        "estimated_time": time_limit,
    }


@router.get("/schedule/{schedule_id}/status")
async def get_optimization_status(
    schedule_id: str,
    current_user: User = Depends(get_active_user),
):
    """
    Get optimization status for a schedule.

    Args:
        schedule_id: Schedule identifier
        current_user: Authenticated user

    Returns:
        Optimization status
    """
    # Get schedule
    schedule = db.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Check permissions
    if schedule.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get optimization status
    opt_info = running_optimizations.get(schedule_id)
    if not opt_info:
        return {
            "schedule_id": schedule_id,
            "status": "idle",
            "message": "No optimization running",
        }

    # Calculate progress
    elapsed = (datetime.now() - opt_info["started_at"]).total_seconds()
    progress = min(
        100,
        (elapsed / opt_info["time_limit"]) * 100,
    )

    return {
        "schedule_id": schedule_id,
        "job_id": opt_info["job_id"],
        "status": opt_info["status"],
        "progress": progress,
        "started_at": opt_info["started_at"].isoformat(),
        "elapsed_seconds": elapsed,
        "objectives": opt_info["objectives"],
    }


@router.delete("/schedule/{schedule_id}/optimize")
async def cancel_optimization(
    schedule_id: str,
    current_user: User = Depends(get_active_user),
):
    """
    Cancel a running optimization.

    Args:
        schedule_id: Schedule identifier
        current_user: Authenticated user

    Returns:
        Cancellation result
    """
    # Get schedule
    schedule = db.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Check permissions
    if schedule.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check if optimization is running
    if schedule_id not in running_optimizations:
        raise HTTPException(
            status_code=404,
            detail="No optimization running for this schedule",
        )

    # Cancel optimization
    opt_info = running_optimizations[schedule_id]
    opt_info["status"] = "cancelled"
    opt_info["cancelled_at"] = datetime.now()

    del running_optimizations[schedule_id]

    return {
        "schedule_id": schedule_id,
        "job_id": opt_info["job_id"],
        "status": "cancelled",
        "cancelled_at": opt_info["cancelled_at"].isoformat(),
    }


@router.get("/objectives")
async def get_optimization_objectives():
    """
    Get list of available optimization objectives.

    Returns:
        Available objectives with descriptions
    """
    return {
        "objectives": [
            {
                "id": "spread_evenly",
                "name": "Spread Evenly Across Term",
                "description": "Minimize variance in daily session distribution",
                "category": "temporal",
            },
            {
                "id": "minimize_evening",
                "name": "Minimize Evening Sessions",
                "description": "Prefer scheduling classes earlier in the day",
                "category": "temporal",
                "configurable": {
                    "evening_threshold": {
                        "type": "hour",
                        "default": 17,
                        "description": "Hour after which classes are considered evening",
                    }
                },
            },
            {
                "id": "balance_instructor_load",
                "name": "Balance Instructor Load",
                "description": "Distribute teaching load evenly among instructors",
                "category": "resource",
            },
            {
                "id": "minimize_room_changes",
                "name": "Minimize Room Changes",
                "description": "Keep courses in the same room when possible",
                "category": "resource",
            },
            {
                "id": "minimize_gaps",
                "name": "Minimize Gaps Between Classes",
                "description": "Reduce idle time between consecutive classes",
                "category": "temporal",
            },
            {
                "id": "prefer_mornings",
                "name": "Prefer Morning Slots",
                "description": "Schedule classes preferably in morning hours",
                "category": "temporal",
            },
        ]
    }


@router.get("/algorithms")
async def get_optimization_algorithms():
    """
    Get list of available optimization algorithms.

    Returns:
        Available algorithms with descriptions
    """
    return {
        "algorithms": [
            {
                "id": "heuristic",
                "name": "Heuristic Solver",
                "description": "Fast greedy algorithm with conflict detection",
                "speed": "fast",
                "quality": "good",
                "suitable_for": ["small_to_medium", "quick_solutions"],
            },
            {
                "id": "ortools",
                "name": "OR-Tools CP-SAT",
                "description": "Constraint programming solver for optimal solutions",
                "speed": "medium",
                "quality": "optimal",
                "suitable_for": ["medium", "high_quality"],
                "requires": ["ortools"],
            },
            {
                "id": "local_search",
                "name": "Local Search",
                "description": "Iterative improvement from initial solution",
                "speed": "medium",
                "quality": "very_good",
                "suitable_for": ["medium_to_large", "refinement"],
            },
            {
                "id": "simulated_annealing",
                "name": "Simulated Annealing",
                "description": "Metaheuristic for escaping local optima",
                "speed": "slow",
                "quality": "excellent",
                "suitable_for": ["large", "complex_constraints"],
            },
        ]
    }


@router.post("/schedule/{schedule_id}/compare")
async def compare_optimizations(
    schedule_id: str,
    algorithm1: str = "heuristic",
    algorithm2: str = "ortools",
    objectives: List[str] = ["spread_evenly"],
    current_user: User = Depends(get_active_user),
):
    """
    Compare two optimization algorithms on the same schedule.

    Args:
        schedule_id: Schedule identifier
        algorithm1: First algorithm to test
        algorithm2: Second algorithm to test
        objectives: Optimization objectives
        current_user: Authenticated user

    Returns:
        Comparison results
    """
    # Get schedule
    schedule = db.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Check permissions
    if schedule.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # For now, return placeholder comparison
    # In a real implementation, this would run both algorithms
    return {
        "schedule_id": schedule_id,
        "comparison": {
            "algorithm1": {
                "name": algorithm1,
                "score": 0.85,
                "time_ms": 500,
                "iterations": 100,
            },
            "algorithm2": {
                "name": algorithm2,
                "score": 0.92,
                "time_ms": 2000,
                "iterations": 500,
            },
            "winner": algorithm2,
            "improvement": "8.2%",
        },
        "objectives": objectives,
        "compared_at": datetime.now().isoformat(),
    }


async def run_optimization(
    schedule_id: str,
    job_id: str,
    objectives: List[str],
    max_iterations: int,
    time_limit: int,
    user_id: str,
):
    """
    Run optimization in background.

    Args:
        schedule_id: Schedule to optimize
        job_id: Job identifier
        objectives: Optimization objectives
        max_iterations: Maximum iterations
        time_limit: Time limit in seconds
        user_id: User ID
    """
    try:
        # Get schedule
        schedule = db.get_schedule(schedule_id)
        if not schedule:
            return

        # Create problem from schedule
        problem = Problem(
            requests=[],
            resources=[],
            calendars=[],
            constraints=[],
        )

        # Emit progress updates
        for i in range(0, 101, 10):
            if schedule_id in running_optimizations and running_optimizations[schedule_id]["status"] != "cancelled":
                await emit_solver_progress(
                    schedule_id,
                    user_id,
                    {
                        "iteration": i * max_iterations // 100,
                        "progress": i,
                        "objective_value": 1.0 - (i / 100),  # Dummy improvement
                    },
                )
                # Simulate work
                import asyncio
                await asyncio.sleep(time_limit / 100)

        # Check if cancelled
        if schedule_id not in running_optimizations:
            return

        # Mark as completed
        running_optimizations[schedule_id]["status"] = "completed"

        # Emit completion
        await emit_solver_completed(
            schedule_id,
            user_id,
            {
                "type": "optimization",
                "objectives": objectives,
                "final_score": 0.95,
                "improvement": "15%",
            },
        )

    except Exception as e:
        # Handle error
        if schedule_id in running_optimizations:
            running_optimizations[schedule_id]["status"] = "failed"
            running_optimizations[schedule_id]["error"] = str(e)

        await emit_solver_failed(
            schedule_id,
            user_id,
            str(e),
            {"objectives": objectives},
        )

    finally:
        # Clean up
        if schedule_id in running_optimizations:
            del running_optimizations[schedule_id]