"""File upload and download API routes."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

from edusched.api.database import db
from edusched.api.dependencies import get_active_user
from edusched.api.events import emit_data_imported, emit_data_exported
from edusched.api.models import BulkImportResponse, User
from edusched.utils.data_import import DataImporter, DataImportError

router = APIRouter()


@router.post("/upload")
async def upload_schedule_data(
    file: UploadFile = File(...),
    data_type: str = Form(...),
    schedule_id: Optional[str] = Form(None),
    current_user: User = Depends(get_active_user),
):
    """
    Upload schedule data file.

    Args:
        file: Uploaded file
        data_type: Type of data (teachers, courses, resources, etc.)
        schedule_id: Optional schedule ID to associate with
        current_user: Authenticated user

    Returns:
        Upload result
    """
    # Validate file type
    allowed_extensions = {".csv", ".xlsx", ".json"}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}",
        )

    # Validate data type
    valid_types = ["teachers", "courses", "resources", "buildings", "holidays", "time_blockers"]
    if data_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid data type. Valid: {', '.join(valid_types)}",
        )

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = Path(tmp_file.name)

    try:
        # Import data
        importer = DataImporter()
        records_imported = 0
        errors = []
        warnings = []

        if data_type == "teachers":
            teachers = importer.import_teachers(tmp_path)
            records_imported = len(teachers)
        elif data_type == "courses":
            requests = importer.import_courses(tmp_path)
            records_imported = len(requests)
        elif data_type == "resources":
            resources = importer.import_resources(tmp_path)
            records_imported = len(resources)
        elif data_type == "buildings":
            buildings = importer.import_buildings(tmp_path)
            records_imported = len(buildings)
        elif data_type == "holidays":
            calendars = importer.import_holidays(tmp_path)
            records_imported = len(calendars)
        elif data_type == "time_blockers":
            blockers = importer.import_time_blockers(tmp_path)
            records_imported = len(blockers)

        # Emit import event
        await emit_data_imported(
            user_id=current_user.id,
            data={
                "data_type": data_type,
                "filename": file.filename,
                "records_imported": records_imported,
            },
        )

        return BulkImportResponse(
            records_processed=records_imported,
            records_imported=records_imported,
            records_failed=0,
            errors=errors,
            warnings=warnings,
        )

    except DataImportError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Data import failed: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}",
        )
    finally:
        # Clean up temporary file
        tmp_path.unlink(missing_ok=True)


@router.post("/upload/batch")
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_active_user),
):
    """
    Upload multiple data files at once.

    Args:
        files: List of uploaded files
        current_user: Authenticated user

    Returns:
        Batch upload results
    """
    results = []
    total_imported = 0
    total_errors = 0

    for file in files:
        # Determine data type from filename
        filename_lower = file.filename.lower()
        if "teacher" in filename_lower:
            data_type = "teachers"
        elif "course" in filename_lower:
            data_type = "courses"
        elif "resource" in filename_lower or "room" in filename_lower:
            data_type = "resources"
        elif "building" in filename_lower:
            data_type = "buildings"
        elif "holiday" in filename_lower:
            data_type = "holidays"
        elif "blocker" in filename_lower:
            data_type = "time_blockers"
        else:
            # Skip unknown file types
            results.append({
                "filename": file.filename,
                "status": "skipped",
                "message": "Could not determine data type from filename",
            })
            continue

        try:
            # Process each file
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                content = await file.read()
                tmp_file.write(content)
                tmp_path = Path(tmp_file.name)

            # Import data
            importer = DataImporter()
            records = 0

            if data_type == "teachers":
                records = len(importer.import_teachers(tmp_path))
            elif data_type == "courses":
                records = len(importer.import_courses(tmp_path))
            elif data_type == "resources":
                records = len(importer.import_resources(tmp_path))
            elif data_type == "buildings":
                records = len(importer.import_buildings(tmp_path))
            elif data_type == "holidays":
                records = len(importer.import_holidays(tmp_path))
            elif data_type == "time_blockers":
                records = len(importer.import_time_blockers(tmp_path))

            results.append({
                "filename": file.filename,
                "data_type": data_type,
                "status": "success",
                "records_imported": records,
            })
            total_imported += records

            tmp_path.unlink(missing_ok=True)

        except Exception as e:
            results.append({
                "filename": file.filename,
                "status": "error",
                "message": str(e),
            })
            total_errors += 1
            tmp_path.unlink(missing_ok=True)

    return {
        "total_files": len(files),
        "successful": len([r for r in results if r["status"] == "success"]),
        "failed": total_errors,
        "total_records_imported": total_imported,
        "results": results,
    }


@router.get("/download/templates")
async def download_template(
    data_type: str,
    format: str = "csv",
    current_user: User = Depends(get_active_user),
):
    """
    Download a data template file.

    Args:
        data_type: Type of template (teachers, courses, resources, etc.)
        format: Template format (csv, xlsx)
        current_user: Authenticated user

    Returns:
        Template file
    """
    # Validate data type
    template_types = {
        "teachers": "teachers_template",
        "courses": "courses_template",
        "resources": "resources_template",
        "buildings": "buildings_template",
        "holidays": "holidays_template",
        "time_blockers": "time_blockers_template",
    }

    if data_type not in template_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid template type. Valid: {', '.join(template_types.keys())}",
        )

    # Create template file
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        from edusched.utils.data_import import create_sample_csv_files
        create_sample_csv_files(tmp_path)

        # Get appropriate template file
        template_file = tmp_path / f"{template_types[data_type]}.{format}"

        if not template_file.exists():
            # Fallback to CSV
            template_file = tmp_path / f"{template_types[data_type]}.csv"

        # Determine media type
        media_types = {
            "csv": "text/csv",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }

        filename = f"{data_type}_template.{format}"

        return FileResponse(
            path=template_file,
            filename=filename,
            media_type=media_types.get(format, "application/octet-stream"),
        )


@router.get("/schedule/{schedule_id}/export/all")
async def export_schedule_package(
    schedule_id: str,
    include_assignments: bool = True,
    include_conflicts: bool = True,
    include_metadata: bool = True,
    format: str = "zip",
    current_user: User = Depends(get_active_user),
):
    """
    Export complete schedule package with all data.

    Args:
        schedule_id: Schedule identifier
        include_assignments: Include assignment data
        include_conflicts: Include conflict report
        include_metadata: Include metadata
        format: Export format (zip, tar)
        current_user: Authenticated user

    Returns:
        Export package file
    """
    # Get schedule
    schedule = db.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Check permissions
    if schedule.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Create export package
    with tempfile.TemporaryDirectory() as tmp_dir:
        export_path = Path(tmp_dir)

        # Export assignments
        if include_assignments:
            assignments_file = export_path / "assignments.json"
            with open(assignments_file, "w") as f:
                json.dump(schedule.assignments, f, indent=2, default=str)

        # Export conflicts
        if include_conflicts:
            # Would detect conflicts here
            conflicts_file = export_path / "conflicts.json"
            with open(conflicts_file, "w") as f:
                json.dump([], f, indent=2)  # Placeholder

        # Export metadata
        if include_metadata:
            metadata_file = export_path / "metadata.json"
            metadata = {
                "schedule_id": schedule.id,
                "name": schedule.name,
                "status": schedule.status,
                "created_at": schedule.created_at.isoformat(),
                "updated_at": schedule.updated_at.isoformat(),
                "total_assignments": len(schedule.assignments),
                "solver_config": schedule.solver_config,
                "metadata": schedule.metadata,
            }
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2, default=str)

        # Create package
        if format == "zip":
            import zipfile
            package_file = export_path / f"{schedule.name.replace(' ', '_')}_package.zip"
            with zipfile.ZipFile(package_file, 'w') as zipf:
                for file_path in export_path.glob("*"):
                    if file_path.is_file() and file_path != package_file:
                        zipf.write(file_path, file_path.name)

        elif format == "tar":
            import tarfile
            package_file = export_path / f"{schedule.name.replace(' ', '_')}_package.tar.gz"
            with tarfile.open(package_file, 'w:gz') as tar:
                tar.add(export_path, arcname=schedule.name.replace(' ', '_'))

        # Emit export event
        await emit_data_exported(
            user_id=current_user.id,
            data={
                "schedule_id": schedule_id,
                "format": format,
                "includes": {
                    "assignments": include_assignments,
                    "conflicts": include_conflicts,
                    "metadata": include_metadata,
                },
            },
        )

        filename = f"{schedule.name.replace(' ', '_')}_package.{format}"
        media_type = "application/zip" if format == "zip" else "application/gzip"

        return FileResponse(
            path=package_file,
            filename=filename,
            media_type=media_type,
        )


@router.get("/import/history")
async def get_import_history(
    limit: int = 50,
    current_user: User = Depends(get_active_user),
):
    """
    Get data import history.

    Args:
        limit: Maximum number of records
        current_user: Authenticated user

    Returns:
        Import history
    """
    # Get import events from event manager
    from edusched.api.events import event_manager
    from edusched.api.events import EventType

    events = event_manager.get_event_history(
        event_type=EventType.DATA_IMPORTED,
        user_id=current_user.id,
        limit=limit,
    )

    return {
        "imports": events,
        "total": len(events),
    }


@router.get("/export/history")
async def get_export_history(
    limit: int = 50,
    current_user: User = Depends(get_active_user),
):
    """
    Get data export history.

    Args:
        limit: Maximum number of records
        current_user: Authenticated user

    Returns:
        Export history
    """
    # Get export events from event manager
    from edusched.api.events import event_manager
    from edusched.api.events import EventType

    events = event_manager.get_event_history(
        event_type=EventType.DATA_EXPORTED,
        user_id=current_user.id,
        limit=limit,
    )

    return {
        "exports": events,
        "total": len(events),
    }