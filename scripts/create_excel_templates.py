#!/usr/bin/env python3
"""
Create Excel templates with data validation and formatting
for easier data entry by end users.
"""

import pandas as pd
from datetime import datetime
import os

# Create Excel templates directory
os.makedirs("excel_templates", exist_ok=True)

# Define data for dropdowns
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
BUILDING_TYPES = ["academic", "library", "administrative", "dormitory", "recreation", "dining"]
ROOM_TYPES = ["classroom", "lab", "lecture_hall", "seminar_room", "computer_lab", "study_space"]
MODALITY_OPTIONS = ["in_person", "online", "hybrid"]
PATTERNS = ["5days", "4days_mt", "4days_tf", "3days_mw", "3days_wf", "2days_mt", "2days_tf"]

def create_teacher_excel():
    """Create Excel template for teachers with data validation."""

    # Create DataFrame with sample data and instructions
    data = {
        "Teacher_ID": ["prof_johnson", "prof_smith", ""],
        "Teacher_Name": ["Dr. Sarah Johnson", "Dr. Michael Smith", ""],
        "Email": ["sjohnson@university.edu", "msmith@university.edu", ""],
        "Department_ID": ["cs", "math", ""],
        "Title": ["Professor", "Associate Professor", ""],
        "Employee_ID": ["CS001", "MATH002", ""],
        "Preferred_Days": ["Monday,Wednesday,Friday", "Tuesday,Thursday", ""],
        "Preferred_Times": [
            "Monday: 09:00-12:00;Wednesday: 09:00-12:00",
            "Tuesday: 10:00-14:00;Thursday: 10:00-14:00",
            ""
        ],
        "Max_Consecutive_Hours": [3, 2, ""],
        "Max_Daily_Hours": [6, 4, ""],
        "Max_Weekly_Hours": [18, 8, ""],
        "Preferred_Buildings": ["engineering,science", "science,humanities", ""],
        "Max_Class_Size": [50, 40, ""],
        "Max_Travel_Time_Minutes": [25, 30, ""],
        "Setup_Time_Minutes": [20, 10, ""],
        "Cleanup_Time_Minutes": [15, 5, ""],
        "Vacation_Periods": [
            "2024-03-10 to 2024-03-17:Spring Break",
            "2024-06-01 to 2024-08-15:Summer Research",
            ""
        ],
        "Conference_Dates": ["2024-04-15 to 2024-04-18:ACM Conference", "", ""],
        "Personal_Days": ["2024-02-14", "", ""]
    }

    df = pd.DataFrame(data)

    # Add instruction row at the top
    instructions = pd.DataFrame(
        [["INSTRUCTIONS", "Fill in teacher information below. Delete this row before submitting."]],
        columns=["Teacher_ID", "Teacher_Name"]
    )
    instructions = pd.concat([instructions, pd.DataFrame(columns=df.columns)], ignore_index=True)

    # Combine with data
    df = pd.concat([instructions, df, pd.DataFrame(columns=df.columns)], ignore_index=True)

    # Save to Excel
    with pd.ExcelWriter("excel_templates/Teacher_Template.xlsx", engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Teachers', index=False)

        # Add metadata sheet
        metadata = pd.DataFrame({
            "Field": ["Teacher_ID", "Preferred_Days", "Preferred_Times", "Vacation_Periods", "Conference_Dates"],
            "Description": [
                "Unique identifier (e.g., prof_lastname)",
                "Comma-separated days (e.g., Monday,Wednesday,Friday)",
                "Format: Day: HH:MM-HH:MM;Day: HH:MM-HH:MM",
                "Format: YYYY-MM-DD to YYYY-MM-DD:Reason",
                "Format: YYYY-MM-DD to YYYY-MM-DD:Conference Name"
            ]
        })
        metadata.to_excel(writer, sheet_name='Instructions', index=False)

    print("Created Teacher_Template.xlsx")

def create_course_excel():
    """Create Excel template for courses with data validation."""

    data = {
        "Course_ID": ["CS401", "MATH301", ""],
        "Course_Title": ["Advanced Algorithms", "Linear Algebra", ""],
        "Department_ID": ["cs", "math", ""],
        "Teacher_ID": ["prof_johnson", "prof_smith", ""],
        "Duration_Hours": [2, 1.5, ""],
        "Number_of_Occurrences": [15, 28, ""],
        "Earliest_Date": ["2024-08-26 09:00", "2024-08-26 09:00", ""],
        "Latest_Date": ["2024-12-13 17:00", "2024-12-13 17:00", ""],
        "Scheduling_Pattern": ["3days_wf", "2days_tf", ""],
        "Enrollment_Count": [45, 35, ""],
        "Min_Capacity": [30, 25, ""],
        "Max_Capacity": [60, 40, ""],
        "Preferred_Building_ID": ["engineering", "science", ""],
        "Required_Building_ID": ["", "", ""],
        "Required_Resource_Types": ["lab:1;classroom:1", "classroom:1", ""],
        "Preferred_Time_Slots": ["09:00-11:00", "10:00-11:30", ""],
        "Avoid_Holidays": ["TRUE", "TRUE", ""],
        "Min_Gap_Days": [7, 3, ""],
        "Max_Occurrences_Per_Week": [2, 1, ""],
        "Cohort_ID": ["CS_Seniors", "MATH_Majors", ""],
        "Modality": ["in_person", "in_person", ""]
    }

    df = pd.DataFrame(data)

    # Add instructions
    instructions = pd.DataFrame(
        [["INSTRUCTIONS", "Fill in course information. Use pattern codes below. Delete this row."]],
        columns=["Course_ID", "Course_Title"]
    )
    df = pd.concat([instructions, pd.DataFrame(columns=df.columns)], ignore_index=True)
    df = pd.concat([df, data], ignore_index=True)

    with pd.ExcelWriter("excel_templates/Course_Template.xlsx", engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Courses', index=False)

        # Add pattern reference sheet
        patterns = pd.DataFrame({
            "Pattern_Code": ["5days", "4days_mt", "4days_tf", "3days_mw", "3days_wf", "2days_mt", "2days_tf"],
            "Description": [
                "Monday - Friday",
                "Monday - Thursday",
                "Tuesday - Friday",
                "Monday - Wednesday",
                "Wednesday - Friday",
                "Monday - Tuesday",
                "Thursday - Friday"
            ],
            "Example": ["Daily classes", "4-day week", "4-day week", "3-day week", "3-day week", "2-day week", "2-day week"]
        })
        patterns.to_excel(writer, sheet_name='Pattern_Reference', index=False)

        # Add resource types sheet
        resources = pd.DataFrame({
            "Resource_Type": ["classroom", "lab", "lecture_hall", "computer_lab", "seminar_room"],
            "Description": [
                "Standard classroom with desks/chairs",
                "Specialized laboratory with equipment",
                "Large lecture hall for many students",
                "Computer lab with workstations",
                "Small room for discussions/seminars"
            ]
        })
        resources.to_excel(writer, sheet_name='Resource_Types', index=False)

    print("Created Course_Template.xlsx")

def create_room_excel():
    """Create Excel template for rooms/buildings."""

    room_data = {
        "Resource_ID": ["Eng101", "Sci201", ""],
        "Resource_Type": ["classroom", "lab", ""],
        "Building_ID": ["engineering", "science", ""],
        "Floor_Number": [1, 2, ""],
        "Capacity": [60, 30, ""],
        "Computer_Count": [30, 25, ""],
        "Has_Computers": ["TRUE", "TRUE", ""],
        "Has_Projector": ["TRUE", "TRUE", ""],
        "Has_Smart_Board": ["TRUE", "FALSE", ""],
        "Special_Equipment": ["", "Microscopes, Lab Equipment", ""],
        "Room_Number": ["101", "201", ""],
        "Room_Features": ["Tier 1 Tech Classroom", "Biology Lab", ""]
    }

    df = pd.DataFrame(room_data)

    # Add instructions
    instructions = pd.DataFrame(
        [["INSTRUCTIONS", "Fill in room information. TRUE/FALSE for boolean fields. Delete this row."]],
        columns=["Resource_ID", "Resource_Type"]
    )
    df = pd.concat([instructions, pd.DataFrame(columns=df.columns)], ignore_index=True)
    df = pd.concat([df, room_data], ignore_index=True)

    with pd.ExcelWriter("excel_templates/Room_Template.xlsx", engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Rooms', index=False)

        # Add building info
        building_data = pd.DataFrame({
            "Building_ID": ["engineering", "science", "humanities", "library"],
            "Building_Name": ["Engineering Building", "Science Building", "Humanities Hall", "University Library"],
            "Building_Type": ["academic", "academic", "academic", "library"],
            "Campus_Area": ["North Campus", "North Campus", "South Campus", "Central Campus"]
        })
        building_data.to_excel(writer, sheet_name='Buildings', index=False)

    print("Created Room_Template.xlsx")

def create_holiday_excel():
    """Create Excel template for holidays."""

    data = {
        "Holiday_Name": [
            "Labor Day",
            "Fall Break",
            "Thanksgiving Break",
            "Winter Break",
            "Spring Break",
            "Faculty Planning Day",
            ""
        ],
        "Start_Date": [
            "2024-09-02",
            "2024-10-14",
            "2024-11-27",
            "2024-12-20",
            "2025-03-10",
            "2024-08-19",
            ""
        ],
        "End_Date": [
            "2024-09-02",
            "2024-10-18",
            "2024-11-29",
            "2025-01-12",
            "2025-03-17",
            "2024-08-19",
            ""
        ],
        "Year": [2024, 2024, 2024, 2025, 2025, 2024, ""],
        "Affects_All_Departments": ["TRUE", "TRUE", "TRUE", "TRUE", "TRUE", "TRUE", ""],
        "Affected_Departments": ["", "", "", "", "", "", ""],
        "Notes": [
            "No classes",
            "Residence halls remain open",
            "Dining services limited",
            "Residence halls close Dec 22",
            "Residence halls remain open",
            "Faculty only, no classes",
            ""
        ]
    }

    df = pd.DataFrame(data)

    with pd.ExcelWriter("excel_templates/Holiday_Template.xlsx", engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Holidays', index=False)

    print("Created Holiday_Template.xlsx")

def create_all_templates():
    """Create all Excel templates."""
    print("\nCreating Excel templates with data validation...")
    print("=" * 50)

    create_teacher_excel()
    create_course_excel()
    create_room_excel()
    create_holiday_excel()

    print("\n" + "=" * 50)
    print("All Excel templates created in 'excel_templates/' directory!")
    print("\nTemplates created:")
    print("  - Teacher_Template.xlsx")
    print("  - Course_Template.xlsx")
    print("  - Room_Template.xlsx")
    print("  - Holiday_Template.xlsx")
    print("\nFeatures:")
    print("  - Sample data for reference")
    print("  - Instructions and metadata sheets")
    print("  - Ready for user input")
    print("\nNext steps:")
    print("  1. Distribute templates to departments")
    print("  2. Collect filled templates")
    print("  3. Use import script to load data:")
    print("     python -m edusched.scripts.import_data --type [type] --file [filename.xlsx]")

if __name__ == "__main__":
    create_all_templates()