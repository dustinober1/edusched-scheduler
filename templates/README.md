# EduSched Template Guide

This directory contains templates for collecting all scheduling data needed to generate optimal class schedules.

## Quick Start

1. **Download the templates** you need from this directory
2. **Fill them out** according to the instructions below
3. **Upload them** to the EduSched system via:
   - Command line: `python -m edusched.scripts.import_data --type [type] --file [filename]`
   - Web interface: Use the bulk import feature
   - API: See API documentation

## Template Files

### 1. Teacher_Template.csv
Collects teacher availability and preferences.

**Required Fields:**
- `Teacher_ID`: Unique identifier (e.g., prof_johnson)
- `Teacher_Name`: Full name
- `Email`: Work email address
- `Department_ID`: Department code

**Optional Fields:**
- `Preferred_Days`: Comma-separated (Monday,Tuesday,etc.)
- `Preferred_Times`: Format "Day: HH:MM-HH:MM;Day: HH:MM-HH:MM"
- `Max_Consecutive_Hours`: Maximum back-to-back teaching hours
- `Max_Daily_Hours`: Maximum teaching hours per day
- `Max_Weekly_Hours`: Maximum teaching hours per week
- `Vacation_Periods`: "YYYY-MM-DD to YYYY-MM-DD:Reason"
- `Conference_Dates`: "YYYY-MM-DD to YYYY-MM-DD:Conference Name"
- `Personal_Days`: Comma-separated dates (YYYY-MM-DD)

**Example:**
```
prof_johnson,Dr. Sarah Johnson,sjohnson@university.edu,cs,Professor,CS001,"Monday,Wednesday,Friday","Monday: 09:00-12:00;Wednesday: 09:00-12:00",3,6,18,"engineering,science",50,25,20,15,"2024-03-10 to 2024-03-17:Spring Break","2024-04-15 to 2024-04-18:ACM Conference","2024-02-14"
```

### 2. Course_Template.csv
Lists all courses that need to be scheduled.

**Required Fields:**
- `Course_ID`: Unique course identifier
- `Course_Title`: Full course name
- `Teacher_ID`: Primary instructor (must match Teacher_Template)
- `Duration_Hours`: Length of each class session
- `Number_of_Occurrences`: How many times the class meets

**Important Fields:**
- `Scheduling_Pattern`:
  - `5days`: Monday-Friday
  - `4days_mt`: Monday-Thursday
  - `4days_tf`: Tuesday-Friday
  - `3days_mw`: Monday-Wednesday
  - `3days_wf`: Wednesday-Friday
  - `2days_mt`: Monday-Tuesday
  - `2days_tf`: Thursday-Friday

### 3. Room_Template.csv
Inventory of all available teaching spaces.

**Required Fields:**
- `Resource_ID`: Unique room identifier
- `Resource_Type`: classroom, lab, lecture_hall, etc.
- `Building_ID`: Building identifier (must match Building_Template)
- `Capacity`: Maximum number of students

**Features:**
- `Has_Computers`: true/false
- `Computer_Count`: Number of computers if applicable
- `Has_Projector`: true/false
- `Special_Equipment`: Any special equipment available

### 4. Building_Template.csv
Campus building information.

**Building_Types:**
- academic: Classroom buildings
- library: Library buildings
- administrative: Office buildings
- dormitory: Residence halls
- recreation: Athletic facilities
- dining: Food service buildings

### 5. Department_Template.csv
Department organizational structure.

**Key Fields:**
- `Unavailable_Days`: Days department doesn't teach
- `Meeting_Time`: Regular department meeting times
- `Special_Notes`: Any special scheduling requirements

### 6. Holiday_Template.csv
Academic calendar and holiday periods.

**Format:**
- Use `TRUE` for holidays affecting all departments
- List specific departments if only some affected
- Include start and end dates for multi-day periods

### 7. Time_Blocker_Template.csv
Institutional time blocking rules.

**Days_of_Week Format:**
- `0`: Monday
- `1`: Tuesday
- `2`: Wednesday
- `3`: Thursday
- `4`: Friday
- `5`: Saturday
- `6`: Sunday

**Examples:**
- `"0,1,2,3,4"`: Monday through Friday
- `"2,4"`: Tuesday and Thursday only

## Common Patterns

### For Research Universities:
- More frequent department meetings
- Research seminar blocks
- Protected faculty research time
- Graduate student defense periods

### For Community Colleges:
- Evening class blocks
- Registration/advising periods
- Adult education setup times
- Shorter class durations

### For Liberal Arts Colleges:
- Common lunch periods
- All-campus events
- Faculty meeting times
- Student activity blocks

## Tips for Successful Data Entry

1. **Be Consistent**: Use the same IDs across all templates
2. **Check Dates**: Use YYYY-MM-DD format for all dates
3. **Validate Times**: Use 24-hour format (HH:MM)
4. **Test Import**: Import a small sample first to verify format
5. **Keep Backups**: Save original templates after data entry

## Troubleshooting

**Common Import Errors:**
- Mismatched IDs between templates
- Incorrect date/time formats
- Missing required fields
- Duplicate IDs in the same file

**Solutions:**
1. Use the validation script before importing
2. Check CSV format with a spreadsheet program
3. Ensure all referenced IDs exist
4. Remove duplicates

## Getting Help

- Email: scheduling-support@university.edu
- Documentation: [link to full documentation]
- Training sessions: Monthly scheduler training available

## Template Updates

Templates are updated annually before scheduling season. Last update: 2024-08-01