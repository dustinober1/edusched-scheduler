"""API endpoints for bulk data import."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from edusched.api.dependencies import get_current_user
from edusched.utils.data_import import DataImporter, DataImportError, create_sample_csv_files

router = APIRouter(prefix="/api/v1/import", tags=["bulk_import"])


@router.get("/templates/sample-csvs")
async def download_sample_csvs(current_user: Any = Depends(get_current_user)):
    """Generate and download sample CSV files for data import."""
    import tempfile
    import zipfile

    # Create temporary directory for sample files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create sample CSV files
        create_sample_csv_files(temp_path)

        # Create zip file
        zip_path = temp_path / "sample_import_templates.zip"
        with zipfile.ZipFile(zip_path, "w") as zip_file:
            for csv_file in temp_path.glob("*_sample.csv"):
                zip_file.write(csv_file, csv_file.name)

        return FileResponse(
            path=zip_path, filename="sample_import_templates.zip", media_type="application/zip"
        )


@router.get("/templates/{data_type}")
async def get_template_schema(data_type: str, current_user: Any = Depends(get_current_user)):
    """Get the field schema for a specific data type."""
    schemas = {
        "buildings": {
            "id": "string (required)",
            "name": "string (required)",
            "building_type": "string (ACADEMIC, LIBRARY, etc.)",
            "address": "string",
            "coordinates": "string (lat,lon)",
            "campus_area": "string",
            "amenities": "string (comma-separated)",
        },
        "resources": {
            "id": "string (required)",
            "resource_type": "string (classroom, lab, breakout, etc.)",
            "capacity": "integer",
            "building_id": "string",
            "floor_number": "integer",
            "attributes": "string (JSON or key=value pairs)",
        },
        "teachers": {
            "id": "string (required)",
            "name": "string (required)",
            "email": "string",
            "department_id": "string",
            "title": "string",
            "preferred_days": "string (comma-separated: monday,tuesday,etc.)",
            "max_daily_hours": "integer",
            "preferred_buildings": "string (comma-separated)",
        },
        "departments": {
            "id": "string (required)",
            "name": "string (required)",
            "head": "string",
            "blacked_out_days": "string (comma-separated)",
            "preferred_room_types": "string (comma-separated)",
        },
        "courses": {
            "id": "string (required)",
            "duration_hours": "number (required)",
            "number_of_occurrences": "integer (required)",
            "earliest_date": "datetime (required, format: YYYY-MM-DD HH:MM)",
            "latest_date": "datetime (required, format: YYYY-MM-DD HH:MM)",
            "enrollment_count": "integer",
            "min_capacity": "integer",
            "department_id": "string",
            "teacher_id": "string",
            "preferred_building_id": "string",
        },
        "calendars": {
            "id": "string (required)",
            "timezone": "string (default: UTC)",
            "timeslot_granularity_minutes": "integer (default: 30)",
        },
    }

    if data_type not in schemas:
        raise HTTPException(status_code=404, detail=f"Unknown data type: {data_type}")

    return {
        "data_type": data_type,
        "schema": schemas[data_type],
        "supported_formats": ["csv", "json", "xlsx", "xls"],
    }


@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    data_type: str = Form(...),
    validate_only: bool = Form(False),
    dry_run: bool = Form(False),
    file: UploadFile = File(...),
    current_user: Any = Depends(get_current_user),
):
    """Upload and import a data file."""
    # Validate data type
    valid_types = ["buildings", "resources", "teachers", "departments", "courses", "calendars"]
    if data_type not in valid_types:
        raise HTTPException(
            status_code=400, detail=f"Invalid data type. Must be one of: {', '.join(valid_types)}"
        )

    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    supported_exts = [".csv", ".json", ".xlsx", ".xls"]
    if file_ext not in supported_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported formats: {', '.join(supported_exts)}",
        )

    try:
        # Save uploaded file temporarily
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Import data
        importer = DataImporter()
        imported_objects = importer.import_file(temp_file_path, data_type)

        # Clean up temp file
        Path(temp_file_path).unlink()

        if validate_only or dry_run:
            # Return preview of what would be imported
            return {
                "status": "preview",
                "data_type": data_type,
                "items_count": len(imported_objects),
                "items_preview": [
                    obj.id if hasattr(obj, "id") else str(obj) for obj in imported_objects[:10]
                ],
                "dry_run": dry_run,
                "validate_only": validate_only,
            }

        # Return successful import result
        return {
            "status": "success",
            "data_type": data_type,
            "items_imported": len(imported_objects),
            "imported_ids": [
                obj.id if hasattr(obj, "id") else str(obj) for obj in imported_objects
            ],
        }

    except DataImportError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/batch")
async def batch_import(data: Dict[str, Any], current_user: Any = Depends(get_current_user)):
    """Import data directly from JSON payload."""
    try:
        data_type = data.get("data_type")
        items = data.get("items", [])

        if not data_type or not items:
            raise HTTPException(
                status_code=400, detail="Must provide 'data_type' and 'items' fields"
            )

        # Process using importer
        importer = DataImporter()
        imported_objects = importer._process_data(items, data_type)

        return {
            "status": "success",
            "data_type": data_type,
            "items_imported": len(imported_objects),
            "imported_ids": [
                obj.id if hasattr(obj, "id") else str(obj) for obj in imported_objects
            ],
        }

    except DataImportError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch import failed: {str(e)}")


@router.get("/status/{import_id}")
async def get_import_status(import_id: str, current_user: Any = Depends(get_current_user)):
    """Get the status of an asynchronous import job."""
    # This would typically check a database or cache for import status
    # For now, return a placeholder response
    return {
        "import_id": import_id,
        "status": "completed",
        "progress": 100,
        "message": "Import completed successfully",
    }


@router.get("/history")
async def get_import_history(
    limit: int = 10, offset: int = 0, current_user: Any = Depends(get_current_user)
):
    """Get the history of import jobs."""
    # This would typically query a database for import history
    # For now, return placeholder data
    return {
        "imports": [
            {
                "id": "imp_001",
                "data_type": "courses",
                "status": "completed",
                "items_count": 25,
                "created_at": datetime.utcnow(),
                "created_by": current_user.username
                if hasattr(current_user, "username")
                else "user",
            }
        ],
        "total": 1,
        "limit": limit,
        "offset": offset,
    }
