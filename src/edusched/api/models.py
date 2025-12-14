"""Pydantic models for API request/response and data validation."""

from typing import Any, List, Optional

from pydantic import BaseModel, Field


class User(BaseModel):
    """User model for authentication and authorization."""

    id: str
    username: str
    email: str
    is_active: bool = True
    is_superuser: bool = False


class ScheduleRequest(BaseModel):
    """Request model for schedule generation."""

    solver: Optional[str] = Field("auto", description="Solver backend to use")
    seed: Optional[int] = Field(None, description="Random seed for reproducibility")
    optimize: bool = Field(True, description="Whether to run optimization")
    max_time_seconds: Optional[int] = Field(60, description="Maximum solver time")


class ScheduleResponse(BaseModel):
    """Response model for schedule results."""

    id: str
    status: str  # "success", "no_solution", "error"
    total_assignments: int
    solver_time_ms: float
    iterations: int
    assignments: List["AssignmentModel"] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class AssignmentModel(BaseModel):
    """Model for a single schedule assignment."""

    request_id: str
    resource_id: str
    start_time: str  # ISO format datetime
    end_time: str  # ISO format datetime
    course_code: Optional[str] = None
    teacher_name: Optional[str] = None
    room_name: Optional[str] = None
    building_id: Optional[str] = None
    enrollment: Optional[int] = None
    capacity: Optional[int] = None


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str
    message: str
    details: Optional[dict] = None


class ValidationError(BaseModel):
    """Validation error details."""

    field: str
    message: str
    value: Optional[Any] = None


class BulkImportResponse(BaseModel):
    """Response for bulk import operations."""

    records_processed: int
    records_imported: int
    records_failed: int
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ExportOptions(BaseModel):
    """Options for schedule export."""

    format: str = Field("json", description="Export format")
    include_summary: bool = Field(True, description="Include summary statistics")
    include_metadata: bool = Field(True, description="Include solver metadata")
