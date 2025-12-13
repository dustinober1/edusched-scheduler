# EduSched User Guide

A complete guide for using the EduSched educational scheduling system.

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Data Templates](#data-templates)
4. [Scheduling Patterns](#scheduling-patterns)
5. [Teacher Constraints](#teacher-constraints)
6. [Common Workflows](#common-workflows)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

## Overview

EduSched is a comprehensive scheduling system that:
- Optimizes class schedules based on constraints
- Respects teacher availability and preferences
- Manages room assignments efficiently
- Handles institutional requirements
- Supports various scheduling patterns

## Getting Started

### Step 1: Prepare Your Data

Choose your preferred format:
- **CSV templates** - Simple, compatible with Excel/Google Sheets
- **Excel templates** - Formatted with data validation
- **JSON templates** - For programmatic import

### Step 2: Fill Templates

Download templates from the `templates/` directory:
- `Teacher_Template.csv` - Teacher information
- `Course_Template.csv` - Course requests
- `Room_Template.csv` - Room inventory
- `Building_Template.csv` - Campus buildings
- `Holiday_Template.csv` - Academic calendar
- `Time_Blocker_Template.csv` - Institutional constraints

### Step 3: Import Data

```bash
# Import all data
python -m edusched.scripts.import_data --type teachers --file Teacher_Template.csv
python -m edusched.scripts.import_data --type courses --file Course_Template.csv
python -m edusched.scripts.import_data --type resources --file Room_Template.csv

# Or use Excel templates
python -m edusched.scripts.import_data --type teachers --file Teacher_Template.xlsx
```

### Step 4: Generate Schedule

```bash
# Run the scheduler
python -m edusched.scripts.schedule \
  --semester fall_2024 \
  --solver heuristic \
  --seed 42 \
  --output schedule_fall_2024.xlsx
```

## Data Templates

### Teacher Template Fields

| Field | Required | Format | Example |
|-------|----------|--------|---------|
| Teacher_ID | Yes | Unique ID | prof_johnson |
| Teacher_Name | Yes | Full name | Dr. Sarah Johnson |
| Email | Yes | Email address | sjohnson@university.edu |
| Department_ID | Yes | Department code | cs |
| Preferred_Days | No | Comma-separated | Monday,Wednesday,Friday |
| Preferred_Times | No | Day: HH:MM-HH:MM | Monday: 09:00-12:00 |
| Max_Daily_Hours | No | Number | 6 |
| Max_Weekly_Hours | No | Number | 18 |
| Vacation_Periods | No | Date range:Reason | 2024-03-10 to 2024-03-17:Spring Break |
| Setup_Time_Minutes | No | Number | 20 |

### Course Template Fields

| Field | Required | Format | Example |
|-------|----------|--------|---------|
| Course_ID | Yes | Unique ID | CS401 |
| Teacher_ID | Yes | Must match Teacher_Template | prof_johnson |
| Duration_Hours | Yes | Decimal | 2.5 |
| Scheduling_Pattern | Yes | Pattern code | 3days_wf |
| Enrollment_Count | Yes | Number | 45 |
| Required_Resource_Types | No | type:count | classroom:1;lab:1 |

### Room Template Fields

| Field | Required | Format | Example |
|-------|----------|--------|---------|
| Resource_ID | Yes | Unique ID | Eng101 |
| Resource_Type | Yes | Room type | classroom |
| Building_ID | Yes | Must match Building_Template | engineering |
| Capacity | Yes | Number | 60 |
| Has_Computers | No | TRUE/FALSE | TRUE |
| Computer_Count | No | Number | 30 |

## Scheduling Patterns

| Pattern | Days | Best For |
|---------|------|----------|
| `5days` | Monday-Friday | Daily classes, labs |
| `4days_mt` | Monday-Thursday | 4-credit courses |
| `4days_tf` | Tuesday-Friday | 4-credit courses |
| `3days_mw` | Monday-Wednesday | 3-credit courses |
| `3days_wf` | Wednesday-Friday | 3-credit courses |
| `2days_mt` | Monday-Tuesday | 2-credit seminars |
| `2days_tf` | Thursday-Friday | 2-credit seminars |

## Teacher Constraints

### Types of Constraints

1. **Availability Constraints**
   - Preferred teaching days
   - Preferred time slots
   - Maximum daily/weekly hours
   - Maximum consecutive hours

2. **Time Off**
   - Vacation periods
   - Conference attendance
   - Personal days

3. **Logistical**
   - Setup time requirements
   - Cleanup time
   - Travel time between buildings
   - Building preferences

### Example Teacher Profile

```csv
prof_johnson,Dr. Sarah Johnson,sjohnson@university.edu,cs,Professor,CS001,
"Monday,Wednesday,Friday",
"Monday: 09:00-12:00;Wednesday: 09:00-12:00;Friday: 09:00-12:00",
3,6,18,"engineering,science",50,25,20,15,
"2024-03-10 to 2024-03-17:Spring Break",
"2024-04-15 to 2024-04-18:ACM Conference",
"2024-02-14"
```

## Common Workflows

### Workflow 1: New Semester Scheduling

1. **Data Collection Phase** (4-6 weeks before semester)
   - Distribute teacher preference forms
   - Update course catalog
   - Verify room inventory
   - Import holiday calendar

2. **Initial Scheduling** (3-4 weeks before semester)
   - Import all data
   - Run initial schedule
   - Review conflicts
   - Make manual adjustments

3. **Finalization** (2 weeks before semester)
   - Resolve remaining conflicts
   - Finalize schedule
   - Publish to stakeholders

### Workflow 2: Schedule Adjustments

```python
# Handle teacher vacation request
from edusched.utils.schedule_manager import ScheduleManager

manager = ScheduleManager("fall_2024")

# Add new vacation
manager.add_teacher_vacation(
    teacher_id="prof_johnson",
    start_date=date(2024, 10, 15),
    end_date=date(2024, 10, 17),
    reason="Conference"
)

# Reschedule affected classes
manager.reschedule_teacher("prof_johnson")

# Export updated schedule
manager.export_schedule("updated_schedule.xlsx")
```

### Workflow 3: Room Reassignment

```python
# Handle room maintenance
manager = ScheduleManager("fall_2024")

# Mark room unavailable
manager.mark_room_unavailable(
    room_id="Eng101",
    start_date=date(2024, 9, 1),
    end_date=date(2024, 9, 15),
    reason="Renovation"
)

# Reassign classes
manager.reassign_room("Eng101")

# Generate room change notices
manager.generate_change_notices("room_changes.csv")
```

## Troubleshooting

### Common Import Errors

1. **"Teacher ID not found"**
   - Cause: Course references non-existent teacher
   - Solution: Verify teacher exists in Teacher_Template

2. **"Invalid date format"**
   - Cause: Incorrect date format
   - Solution: Use YYYY-MM-DD format

3. **"Duplicate Resource ID"**
   - Cause: Same room ID used twice
   - Solution: Use unique identifiers

### Common Scheduling Issues

1. **Too many conflicts**
   - Reduce constraints
   - Increase time slots
   - Add more resources

2. **Teacher overload**
   - Adjust workload limits
   - Rebalance course assignments

3. **Room shortage**
   - Check room inventory
   - Consider online/hybrid options

## Best Practices

### Data Quality

1. **Use consistent IDs** across all templates
2. **Validate data** before importing
3. **Keep templates updated** each semester
4. **Document exceptions** for special cases

### Constraint Management

1. **Prioritize constraints**:
   - Hard constraints (must have)
   - Soft constraints (nice to have)

2. **Start simple** with basic constraints
3. **Gradually add complexity**
4. **Test with sample data** first

### Communication

1. **Notify teachers** of schedule changes early
2. **Provide explanations** for scheduling decisions
3. **Collect feedback** for future improvements
4. **Document policies** consistently

## API Integration

For custom integrations:

```python
from edusched.api import SchedulingAPI

# Initialize API
api = SchedulingAPI(base_url="https://schedules.university.edu/api")

# Submit scheduling job
job = api.submit_schedule(
    semester="fall_2024",
    constraints=[...],
    preferences=[...]
)

# Monitor progress
status = api.get_job_status(job.id)

# Download results
if status == "complete":
    api.download_schedule(job.id, "schedule.xlsx")
```

## Support

- **Documentation**: [link to docs]
- **Email**: scheduling-support@university.edu
- **Training**: Monthly workshops available
- **FAQ**: Check the troubleshooting section first

## Template Updates

Templates are updated annually before scheduling season:
- Version 1.0: Initial release (2024-08)
- Version 1.1: Added travel time constraints (2024-09)
- Version 1.2: Enhanced holiday calendar (2024-10)

Always use the latest templates for best results.