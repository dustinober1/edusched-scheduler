# Data Import Guide

This guide explains how to import scheduling data (buildings, classrooms, teachers, courses, etc.) into EduSched using various formats including CSV, JSON, and Excel.

## Supported Data Types

- **Buildings**: Campus buildings with location and facility information
- **Resources/Classrooms**: Individual rooms, labs, and other spaces
- **Teachers/Instructors**: Faculty and teaching staff with availability
- **Departments**: Academic departments with scheduling constraints
- **Courses/Sessions**: Class sessions to be scheduled
- **Calendars**: Academic calendars and time slot configurations

## Import Methods

### 1. Command Line Tool

The import script provides an easy way to import data from the command line:

```bash
# Import buildings from CSV
python scripts/import_data.py import buildings.csv buildings

# Validate file without importing
python scripts/import_data.py validate teachers.csv teachers

# Create sample templates
python scripts/import_data.py create-templates ./templates

# Validate multiple files at once
python scripts/import_data.py batch-validate *.csv
```

### 2. Python API

Use the `DataImporter` class directly in your Python code:

```python
from edusched.utils.data_import import DataImporter

importer = DataImporter()
buildings = importer.import_file("buildings.csv", "buildings")
```

### 3. REST API

Import data via HTTP endpoints:

```bash
# Upload a file
curl -X POST http://localhost:8000/api/v1/import/upload \
  -F "file=@buildings.csv" \
  -F "data_type=buildings"

# Get sample templates
curl http://localhost:8000/api/v1/import/templates/sample-csvs \
  -o sample_templates.zip

# Import via JSON payload
curl -X POST http://localhost:8000/api/v1/import/batch \
  -H "Content-Type: application/json" \
  -d '{
    "data_type": "teachers",
    "items": [
      {"id": "prof1", "name": "Professor Smith", "email": "smith@univ.edu"}
    ]
  }'
```

## File Formats

### CSV Format

CSV files should have headers in the first row. See below for field specifications by data type.

### JSON Format

JSON files can have two structures:

```json
// Array of objects
[
  {"id": "building1", "name": "Building 1"},
  {"id": "building2", "name": "Building 2"}
]

// Or wrapped object with data field
{
  "data": [
    {"id": "building1", "name": "Building 1"},
    {"id": "building2", "name": "Building 2"}
  ]
}
```

### Excel Format

Excel files (.xlsx, .xls) are supported using pandas. The first row should contain headers.

## Field Specifications

### Buildings (`buildings.csv`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | ✓ | Unique building identifier |
| name | string | ✓ | Building name |
| building_type | string | | ACADEMIC, LIBRARY, etc. |
| address | string | | Street address |
| coordinates | string | | "latitude,longitude" |
| campus_area | string | | Campus area name |
| amenities | string | | Comma-separated amenities list |

Example:
```csv
id,name,building_type,address,coordinates,campus_area,amenities
tech_building,Technology Building,ACADEMIC,123 Tech St,"40.7128,-74.0060",North Campus,"WiFi,Projector,Whiteboard"
```

### Resources/Classrooms (`resources.csv`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | ✓ | Unique resource identifier |
| resource_type | string | | classroom, lab, breakout, etc. |
| capacity | integer | | Maximum number of people |
| building_id | string | | Parent building ID |
| floor_number | integer | | Floor within building |
| attributes | string | | JSON or key=value pairs |

Example:
```csv
id,resource_type,capacity,building_id,floor_number,attributes
Room101,classroom,30,tech_building,1,"computers=30,projector=yes"
Lab301,lab,25,tech_building,3,"computers=25,specialized_software=yes"
```

### Teachers (`teachers.csv`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | ✓ | Unique teacher identifier |
| name | string | ✓ | Full name |
| email | string | | Email address |
| department_id | string | | Primary department |
| title | string | | Professor, Lecturer, etc. |
| preferred_days | string | | Comma-separated days |
| max_daily_hours | integer | | Maximum teaching hours per day |
| preferred_buildings | string | | Comma-separated building IDs |

Example:
```csv
id,name,email,department_id,title,preferred_days,max_daily_hours,preferred_buildings
alice_prof,Alice Smith,alice@univ.edu,cs,Professor,"Monday,Wednesday,Friday",4,tech_building
```

### Departments (`departments.csv`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | ✓ | Unique department identifier |
| name | string | ✓ | Department name |
| head | string | | Department head |
| blacked_out_days | string | | Days department doesn't teach |
| preferred_room_types | string | | Preferred room types |

Example:
```csv
id,name,head,blacked_out_days,preferred_room_types
cs,Computer Science,Dr. Smith,"Friday,Saturday,Sunday","classroom,lab"
```

### Courses (`courses.csv`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | ✓ | Unique course identifier |
| duration_hours | number | ✓ | Duration per session |
| number_of_occurrences | integer | ✓ | Number of sessions |
| earliest_date | datetime | ✓ | Earliest scheduling date |
| latest_date | datetime | ✓ | Latest scheduling date |
| enrollment_count | integer | | Number of students |
| min_capacity | integer | | Minimum room capacity |
| department_id | string | | Offering department |
| teacher_id | string | | Primary instructor |
| additional_teachers | string | | Comma-separated teacher IDs |
| preferred_building_id | string | | Preferred building |

Example:
```csv
id,duration_hours,number_of_occurrences,earliest_date,latest_date,enrollment_count,min_capacity,department_id,teacher_id
cs101,2,24,"2024-01-15 09:00","2024-05-15 17:00",30,25,cs,alice_prof
```

### Calendars (`calendars.csv`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | ✓ | Unique calendar identifier |
| timezone | string | | Timezone (default: UTC) |
| timeslot_granularity_minutes | integer | | Timeslot length |

Example:
```csv
id,timezone,timeslot_granularity_minutes
academic,UTC,30
```

## Getting Started

1. **Download Sample Templates**:
   ```bash
   python scripts/import_data.py create-templates ./templates
   ```
   Or get them via API: `GET /api/v1/import/templates/sample-csvs`

2. **Fill in Your Data**:
   - Open the CSV files in Excel, Google Sheets, or any spreadsheet editor
   - Fill in your institution's data following the field specifications
   - Save as CSV (UTF-8 encoding)

3. **Validate Before Importing**:
   ```bash
   python scripts/import_data.py validate buildings.csv buildings
   ```

4. **Import Your Data**:
   ```bash
   python scripts/import_data.py import buildings.csv buildings
   ```

## Best Practices

- **Use UTF-8 encoding** for all text files
- **Validate files before importing** to catch errors early
- **Import in dependency order**: Buildings → Resources → Departments → Teachers → Courses
- **Back up existing data** before bulk imports
- **Test with small batches** first before importing large datasets
- **Use consistent IDs** across files for proper relationships

## Error Handling

Common errors and solutions:

- **File not found**: Check file path and ensure file exists
- **Invalid format**: Ensure correct headers and data types
- **Missing required fields**: All fields marked as Required must have values
- **Invalid dates**: Use format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD
- **Invalid enum values**: Use values from the enum definitions (e.g., ACADEMIC, LIBRARY)

## API Reference

### Endpoints

- `GET /api/v1/import/templates/{data_type}` - Get field schema
- `GET /api/v1/import/templates/sample-csvs` - Download sample files
- `POST /api/v1/import/upload` - Upload and import file
- `POST /api/v1/import/batch` - Import via JSON payload
- `GET /api/v1/import/status/{import_id}` - Check import status
- `GET /api/v1/import/history` - List recent imports

### Parameters

- `data_type`: buildings, resources, teachers, departments, courses, calendars
- `validate_only`: Return preview without importing
- `dry_run`: Validate without persisting data

## Integration Examples

See the example file for complete usage scenarios:
```python
python examples/data_import_example.py
```

This demonstrates:
- Creating sample CSV files
- Importing all data types
- Creating data programmatically
- Maintaining relationships between entities