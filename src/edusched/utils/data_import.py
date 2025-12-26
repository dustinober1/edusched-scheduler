"""Utilities for importing scheduling data from various file formats."""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import pandas as pd

    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None

from edusched.domain.building import Building, BuildingType
from edusched.domain.calendar import Calendar
from edusched.domain.department import Department
from edusched.domain.resource import Resource
from edusched.domain.session_request import SessionRequest
from edusched.domain.teacher import Teacher


logger = logging.getLogger(__name__)


class DataImportError(Exception):
    """Raised when data import fails."""

    pass


class DataImporter:
    """Utility class for importing scheduling data from various formats."""

    def __init__(self):
        self.importers = {
            "csv": self._import_csv,
            "json": self._import_json,
            "xlsx": self._import_excel if PANDAS_AVAILABLE else self._fallback_excel,
            "xls": self._import_excel if PANDAS_AVAILABLE else self._fallback_excel,
        }

    def import_file(self, file_path: Union[str, Path], data_type: str) -> List[Any]:
        """
        Import data from a file.

        Args:
            file_path: Path to the import file
            data_type: Type of data to import (buildings, resources, teachers, etc.)

        Returns:
            List of imported domain objects

        Raises:
            DataImportError: If import fails
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise DataImportError(f"File not found: {file_path}")

        file_ext = file_path.suffix.lower().lstrip(".")
        if file_ext not in self.importers:
            raise DataImportError(f"Unsupported file format: {file_ext}")

        try:
            raw_data = self.importers[file_ext](file_path)
            return self._process_data(raw_data, data_type)
        except Exception as e:
            raise DataImportError(f"Failed to import {data_type} from {file_path}: {str(e)}")

    def _import_csv(self, file_path: Path) -> List[Dict[str, Any]]:
        """Import data from CSV file."""
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def _import_json(self, file_path: Path) -> List[Dict[str, Any]]:
        """Import data from JSON file."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "data" in data:
            return data["data"]
        else:
            return [data]

    def _import_excel(self, file_path: Path) -> List[Dict[str, Any]]:
        """Import data from Excel file using pandas."""
        df = pd.read_excel(file_path)
        # Replace NaN with None
        df = df.where(pd.notnull(df), None)
        return df.to_dict("records")

    def _fallback_excel(self, file_path: Path) -> List[Dict[str, Any]]:
        """Fallback Excel import without pandas."""
        raise DataImportError(
            "Excel import requires pandas. Install with: pip install pandas openpyxl"
        )

    def _process_data(self, raw_data: List[Dict[str, Any]], data_type: str) -> List[Any]:
        """Process raw data into domain objects."""
        processors = {
            "buildings": self._process_buildings,
            "resources": self._process_resources,
            "teachers": self._process_teachers,
            "departments": self._process_departments,
            "courses": self._process_courses,
            "calendars": self._process_calendars,
        }

        if data_type not in processors:
            raise DataImportError(f"Unknown data type: {data_type}")

        return processors[data_type](raw_data)

    def _process_buildings(self, data: List[Dict[str, Any]]) -> List[Building]:
        """Process building data."""
        buildings = []
        for row in data:
            try:
                # Parse coordinates
                coordinates = None
                if row.get("coordinates"):
                    coords_str = str(row["coordinates"])
                    if "," in coords_str:
                        lat, lon = map(float, coords_str.split(","))
                        coordinates = (lat, lon)

                # Convert building_type string to enum
                building_type = BuildingType.ACADEMIC
                if "building_type" in row and row["building_type"]:
                    type_str = str(row["building_type"]).upper()
                    try:
                        building_type = BuildingType[type_str]
                    except KeyError:
                        # Default to ACADEMIC for unknown types
                        building_type = BuildingType.ACADEMIC

                building = Building(
                    id=str(row["id"]),
                    name=str(row["name"]),
                    building_type=building_type,
                    address=str(row.get("address", "")),
                    coordinates=coordinates,
                    campus_area=row.get("campus_area"),
                    amenities=self._parse_list_field(row.get("amenities")),
                )
                buildings.append(building)
            except Exception as e:
                raise DataImportError(
                    f"Error processing building {row.get('id', 'unknown')}: {str(e)}"
                )

        return buildings

    def _process_resources(self, data: List[Dict[str, Any]]) -> List[Resource]:
        """Process resource/classroom data."""
        resources = []
        for row in data:
            try:
                resource = Resource(
                    id=str(row["id"]),
                    resource_type=str(row.get("resource_type", "classroom")),
                    capacity=int(row["capacity"]) if row.get("capacity") else None,
                    building_id=row.get("building_id"),
                    floor_number=int(row["floor_number"]) if row.get("floor_number") else None,
                    attributes=self._parse_attributes(row.get("attributes")),
                    availability_calendar_id=row.get("availability_calendar_id"),
                )
                resources.append(resource)
            except Exception as e:
                raise DataImportError(
                    f"Error processing resource {row.get('id', 'unknown')}: {str(e)}"
                )

        return resources

    def _process_teachers(self, data: List[Dict[str, Any]]) -> List[Teacher]:
        """Process teacher data."""
        teachers = []
        for row in data:
            try:
                teacher = Teacher(
                    id=str(row["id"]),
                    name=str(row["name"]),
                    email=row.get("email"),
                    department_id=row.get("department_id"),
                    title=row.get("title"),
                    employee_id=row.get("employee_id"),
                    availability_calendar_id=row.get("availability_calendar_id"),
                    preferred_days=self._parse_list_field(row.get("preferred_days")),
                    preferred_times=self._parse_dict_field(row.get("preferred_times")),
                    max_consecutive_hours=int(row["max_consecutive_hours"])
                    if row.get("max_consecutive_hours")
                    else None,
                    max_daily_hours=int(row["max_daily_hours"])
                    if row.get("max_daily_hours")
                    else None,
                    max_weekly_hours=int(row["max_weekly_hours"])
                    if row.get("max_weekly_hours")
                    else None,
                    preferred_buildings=self._parse_list_field(row.get("preferred_buildings")),
                    preferred_room_types=self._parse_list_field(row.get("preferred_room_types")),
                    max_class_size=int(row["max_class_size"])
                    if row.get("max_class_size")
                    else None,
                )
                teachers.append(teacher)
            except Exception as e:
                raise DataImportError(
                    f"Error processing teacher {row.get('id', 'unknown')}: {str(e)}"
                )

        return teachers

    def _process_departments(self, data: List[Dict[str, Any]]) -> List[Department]:
        """Process department data."""
        departments = []
        for row in data:
            try:
                department = Department(
                    id=str(row["id"]),
                    name=str(row["name"]),
                    head=row.get("head"),
                    building_id=row.get("building_id"),
                    contact_email=row.get("contact_email"),
                    contact_phone=row.get("contact_phone"),
                    availability_calendar_id=row.get("availability_calendar_id"),
                    preferred_times=self._parse_dict_field(row.get("preferred_times")),
                    blacked_out_days=self._parse_list_field(row.get("blacked_out_days")),
                    preferred_room_types=self._parse_list_field(row.get("preferred_room_types")),
                    required_amenities=self._parse_list_field(row.get("required_amenities")),
                )
                departments.append(department)
            except Exception as e:
                raise DataImportError(
                    f"Error processing department {row.get('id', 'unknown')}: {str(e)}"
                )

        return departments

    def _process_courses(self, data: List[Dict[str, Any]]) -> List[SessionRequest]:
        """Process course data."""
        from datetime import timedelta
        from zoneinfo import ZoneInfo

        courses = []
        for row in data:
            try:
                # Parse duration
                duration_hours = float(row.get("duration_hours", 1))
                duration = timedelta(hours=duration_hours)

                # Parse dates
                timezone = ZoneInfo(row.get("timezone", "UTC"))
                earliest_date = self._parse_datetime(row["earliest_date"], timezone)
                latest_date = self._parse_datetime(row["latest_date"], timezone)

                # Parse additional teachers
                additional_teachers = None
                if row.get("additional_teachers"):
                    additional_teachers = [
                        t.strip() for t in str(row["additional_teachers"]).split(",") if t.strip()
                    ]

                course = SessionRequest(
                    id=str(row["id"]),
                    duration=duration,
                    number_of_occurrences=int(row["number_of_occurrences"]),
                    earliest_date=earliest_date,
                    latest_date=latest_date,
                    cohort_id=row.get("cohort_id"),
                    modality=row.get("modality", "in_person"),
                    enrollment_count=int(row.get("enrollment_count", 0)),
                    min_capacity=int(row.get("min_capacity", 0)),
                    max_capacity=int(row["max_capacity"]) if row.get("max_capacity") else None,
                    department_id=row.get("department_id"),
                    teacher_id=row.get("teacher_id"),
                    additional_teachers=additional_teachers,
                    preferred_building_id=row.get("preferred_building_id"),
                    required_building_id=row.get("required_building_id"),
                    required_resource_types=self._parse_dict_field(
                        row.get("required_resource_types")
                    ),
                    day_requirements=self._parse_dict_field(row.get("day_requirements")),
                )
                courses.append(course)
            except Exception as e:
                raise DataImportError(
                    f"Error processing course {row.get('id', 'unknown')}: {str(e)}"
                )

        return courses

    def _process_calendars(self, data: List[Dict[str, Any]]) -> List[Calendar]:
        """Process calendar data."""
        from datetime import timedelta
        from zoneinfo import ZoneInfo

        calendars = []
        for row in data:
            try:
                timezone = ZoneInfo(row.get("timezone", "UTC"))
                granularity_minutes = int(row.get("timeslot_granularity_minutes", 30))
                granularity = timedelta(minutes=granularity_minutes)

                calendar = Calendar(
                    id=str(row["id"]), timezone=timezone, timeslot_granularity=granularity
                )
                calendars.append(calendar)
            except Exception as e:
                raise DataImportError(
                    f"Error processing calendar {row.get('id', 'unknown')}: {str(e)}"
                )

        return calendars

    def _parse_list_field(self, value: Any) -> Optional[List[str]]:
        """Parse a field that should be a list of strings."""
        if not value:
            return None
        if isinstance(value, list):
            return [str(v) for v in value]
        return [str(v).strip() for v in str(value).split(",") if v.strip()]

    def _parse_dict_field(self, value: Any) -> Optional[Dict[str, Any]]:
        """Parse a field that should be a dictionary."""
        if not value:
            return None
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # Simple key=value format
                result = {}
                for pair in value.split(","):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        result[k.strip()] = v.strip()
                return result
        return None

    def _parse_attributes(self, value: Any) -> Dict[str, Any]:
        """Parse resource attributes."""
        if not value:
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # Parse computers field specially
                result = {}
                for pair in value.split(","):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        try:
                            result[k.strip()] = int(v)
                        except ValueError:
                            result[k.strip()] = v.strip()
                return result
        return {}

    def _parse_datetime(self, value: Any, timezone) -> datetime:
        """Parse datetime string."""
        if isinstance(value, datetime):
            return value.replace(tzinfo=timezone)

        value_str = str(value)

        # Try common formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M",
            "%m/%d/%Y",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(value_str, fmt)
                return dt.replace(tzinfo=timezone)
            except ValueError:
                continue

        raise ValueError(f"Unable to parse datetime: {value_str}")


def create_sample_csv_files(output_dir: Union[str, Path]):
    """Create sample CSV files for data import templates."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Sample buildings CSV
    buildings_header = [
        "id",
        "name",
        "building_type",
        "address",
        "coordinates",
        "campus_area",
        "amenities",
    ]
    buildings_data = [
        [
            "tech_building",
            "Technology Building",
            "ACADEMIC",
            "123 Tech St",
            "40.7128,-74.0060",
            "North Campus",
            "WiFi,Projector,Whiteboard",
        ],
        [
            "lib_building",
            "University Library",
            "LIBRARY",
            "456 Library Way",
            "40.7130,-74.0055",
            "Central Campus",
            "WiFi,Computers,Study Rooms",
        ],
    ]
    write_csv_file(output_dir / "buildings_sample.csv", buildings_header, buildings_data)

    # Sample resources CSV
    resources_header = [
        "id",
        "resource_type",
        "capacity",
        "building_id",
        "floor_number",
        "attributes",
    ]
    resources_data = [
        ["Room101", "classroom", "30", "tech_building", "1", "computers=30,projector=yes"],
        ["Room201", "classroom", "50", "tech_building", "2", "computers=0,projector=yes"],
        ["Lab301", "lab", "25", "tech_building", "3", "computers=25,specialized_software=yes"],
        ["StudyRoom1", "breakout", "10", "lib_building", "1", ""],
    ]
    write_csv_file(output_dir / "resources_sample.csv", resources_header, resources_data)

    # Sample teachers CSV
    teachers_header = [
        "id",
        "name",
        "email",
        "department_id",
        "title",
        "preferred_days",
        "max_daily_hours",
        "preferred_buildings",
    ]
    teachers_data = [
        [
            "alice_prof",
            "Alice Smith",
            "alice@university.edu",
            "cs",
            "Professor",
            "monday,wednesday,friday",
            "4",
            "tech_building",
        ],
        [
            "bob_prof",
            "Bob Johnson",
            "bob@university.edu",
            "cs",
            "Associate Professor",
            "tuesday,thursday",
            "4",
            "tech_building",
        ],
        [
            "charlie_ta",
            "Charlie Brown",
            "charlie@university.edu",
            "cs",
            "Teaching Assistant",
            "monday,tuesday,wednesday,thursday",
            "8",
            "",
        ],
    ]
    write_csv_file(output_dir / "teachers_sample.csv", teachers_header, teachers_data)

    # Sample departments CSV
    departments_header = ["id", "name", "head", "blacked_out_days", "preferred_room_types"]
    departments_data = [
        ["cs", "Computer Science", "Alice Smith", "friday,saturday,sunday", "classroom,lab"],
        ["math", "Mathematics", "David Lee", "saturday,sunday", "classroom"],
    ]
    write_csv_file(output_dir / "departments_sample.csv", departments_header, departments_data)

    # Sample courses CSV
    courses_header = [
        "id",
        "duration_hours",
        "number_of_occurrences",
        "earliest_date",
        "latest_date",
        "enrollment_count",
        "min_capacity",
        "department_id",
        "teacher_id",
        "preferred_building_id",
    ]
    courses_data = [
        [
            "cs101",
            "2",
            "24",
            "2024-01-15 09:00",
            "2024-05-15 17:00",
            "30",
            "25",
            "cs",
            "alice_prof",
            "tech_building",
        ],
        [
            "cs102",
            "2",
            "24",
            "2024-01-15 09:00",
            "2024-05-15 17:00",
            "25",
            "20",
            "cs",
            "bob_prof",
            "tech_building",
        ],
        [
            "cs301",
            "3",
            "16",
            "2024-01-15 09:00",
            "2024-05-15 17:00",
            "20",
            "15",
            "cs",
            "alice_prof",
            "tech_building",
        ],
    ]
    write_csv_file(output_dir / "courses_sample.csv", courses_header, courses_data)

    logger.info("Sample CSV files created in: %s", output_dir)
    logger.info("Files created:")
    for csv_file in output_dir.glob("*_sample.csv"):
        logger.info("  - %s", csv_file.name)


def write_csv_file(file_path: Path, header: List[str], data: List[List[str]]):
    """Write data to a CSV file."""
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(data)
