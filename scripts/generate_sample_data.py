#!/usr/bin/env python3
"""
Generate sample data for testing EduSched scheduling system.
Creates realistic test data for demonstration purposes.
"""

import csv
import random
from datetime import datetime, date, timedelta
from pathlib import Path

# Create directories
Path("sample_data").mkdir(exist_ok=True)

# Sample data
departments = [
    {"id": "cs", "name": "Computer Science", "head": "prof_johnson"},
    {"id": "math", "name": "Mathematics", "head": "prof_chen"},
    {"id": "physics", "name": "Physics", "head": "prof_williams"},
    {"id": "chemistry", "name": "Chemistry", "head": "prof_davis"},
    {"id": "biology", "name": "Biology", "head": "prof_martinez"},
    {"id": "english", "name": "English", "head": "dr_thompson"},
    {"id": "history", "name": "History", "head": "dr_lee"},
    {"id": "business", "name": "Business", "head": "dr_anderson"}
]

buildings = [
    {"id": "engineering", "name": "Engineering Building", "type": "academic"},
    {"id": "science", "name": "Science Building", "type": "academic"},
    {"id": "humanities", "name": "Humanities Hall", "type": "academic"},
    {"id": "library", "name": "University Library", "type": "academic"},
    {"id": "student_center", "name": "Student Center", "type": "academic"}
]

teachers = []
teacher_counter = 1
for dept in departments:
    num_teachers = random.randint(3, 8)
    for i in range(num_teachers):
        is_professor = random.random() > 0.3
        teachers.append({
            "id": f"prof_{dept['id']}_{i+1:02d}",
            "name": f"Dr. {'Smith' if i == 0 else 'Johnson' if i == 1 else 'Williams' if i == 2 else 'Brown'} {dept['name'].split()[0]}",
            "email": f"instructor{teacher_counter}@university.edu",
            "dept": dept["id"],
            "title": "Professor" if is_professor else "Associate Professor" if random.random() > 0.5 else "Lecturer",
            "max_daily": random.choice([4, 5, 6]),
            "max_weekly": random.choice([12, 15, 18])
        })
        teacher_counter += 1

courses = []
course_counter = 100
for dept in departments:
    # Generate courses for each department
    num_courses = random.randint(5, 15)

    for level in ["101", "201", "301", "401", "499"]:
        if random.random() > 0.3:
            teacher = random.choice([t for t in teachers if t["dept"] == dept["id"]])
            courses.append({
                "id": f"{dept['id'].upper()}{level}",
                "title": f"{'Introduction to' if level == '101' else 'Advanced' if level == '401' else 'Intermediate'} {dept['name']}",
                "dept": dept["id"],
                "teacher": teacher["id"],
                "duration": random.choice([1, 1.5, 2, 3]),
                "occurrences": 14 if level in ["101", "201"] else 12 if level == "301" else 10 if level == "401" else 7,
                "pattern": random.choice(["5days", "3days_mw", "3days_wf", "2days_tf"]),
                "enrollment": random.randint(20, 80),
                "lab": dept["id"] in ["cs", "physics", "chemistry", "biology"] and random.random() > 0.5
            })

rooms = []
# Generate rooms for each building
room_counter = 1
for building in buildings:
    num_rooms = random.randint(10, 30)
    for floor in range(1, random.randint(3, 7)):
        floor_rooms = random.randint(2, 5)
        for i in range(floor_rooms):
            room_type = random.choices(
                ["classroom", "classroom", "classroom", "lab", "lecture_hall", "seminar_room"],
                weights=[40, 30, 20, 5, 3, 2]
            )[0]

            capacity = random.randint(20, 150) if room_type != "seminar_room" else random.randint(10, 30)

            rooms.append({
                "id": f"{building['id'][:3].upper()}{floor:02d}{i+1:02d}",
                "type": room_type,
                "building": building["id"],
                "floor": floor,
                "capacity": capacity,
                "computers": random.randint(20, capacity) if room_type == "lab" else random.randint(10, 30) if random.random() > 0.7 else 0,
                "projector": random.random() > 0.1,
                "smart_board": random.random() > 0.3 if room_type != "lab" else False
            })

# Write teacher template
with open("sample_data/Teacher_Template.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "Teacher_ID", "Teacher_Name", "Email", "Department_ID", "Title", "Employee_ID",
        "Preferred_Days", "Preferred_Times", "Max_Consecutive_Hours", "Max_Daily_Hours",
        "Max_Weekly_Hours", "Preferred_Buildings", "Max_Class_Size", "Max_Travel_Time_Minutes",
        "Setup_Time_Minutes", "Cleanup_Time_Minutes", "Vacation_Periods", "Conference_Dates", "Personal_Days"
    ])

    for teacher in teachers:
        # Generate random preferences
        all_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        preferred_days = random.sample(all_days, random.randint(3, 5))

        # Generate time preferences
        time_slots = []
        for day in preferred_days:
            if random.random() > 0.3:
                start = random.choice(["09:00", "10:00", "11:00", "14:00"])
                end = str(int(start.split(":")[0]) + random.randint(2, 3)) + ":00"
                time_slots.append(f"{day}: {start}-{end}")

        writer.writerow([
            teacher["id"],
            teacher["name"],
            teacher["email"],
            teacher["dept"],
            teacher["title"],
            f"EMP{random.randint(1000, 9999)}",
            ",".join(preferred_days),
            ";".join(time_slots),
            random.randint(2, 4),
            teacher["max_daily"],
            teacher["max_weekly"],
            ",".join(random.sample(buildings[:3], random.randint(1, 2))),
            random.randint(30, 100),
            random.randint(15, 30),
            random.randint(5, 25),
            random.randint(5, 15),
            f"{date(2024, random.randint(1, 6), random.randint(1, 28))} to {date(2024, random.randint(6, 12), random.randint(1, 28))}: Vacation" if random.random() > 0.7 else "",
            f"{date(2024, random.randint(1, 12), random.randint(1, 28))} to {date(2024, random.randint(1, 12), random.randint(1, 28))}: Conference" if random.random() > 0.8 else "",
            ",".join([str(date(2024, random.randint(1, 12), random.randint(1, 28)).strftime("%Y-%m-%d")) for _ in range(random.randint(0, 3))]) if random.random() > 0.6 else ""
        ])

# Write course template
with open("sample_data/Course_Template.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "Course_ID", "Course_Title", "Department_ID", "Teacher_ID", "Duration_Hours",
        "Number_of_Occurrences", "Earliest_Date", "Latest_Date", "Scheduling_Pattern",
        "Enrollment_Count", "Min_Capacity", "Max_Capacity", "Preferred_Building_ID",
        "Required_Building_ID", "Required_Resource_Types", "Preferred_Time_Slots",
        "Avoid_Holidays", "Min_Gap_Days", "Max_Occurrences_Per_Week", "Cohort_ID", "Modality"
    ])

    for course in courses:
        min_cap = max(10, course["enrollment"] - random.randint(10, 20))
        max_cap = course["enrollment"] + random.randint(10, 30)

        required_resources = "classroom:1"
        if course["lab"]:
            required_resources = f"classroom:1;lab:1"

        writer.writerow([
            course["id"],
            course["title"],
            course["dept"],
            course["teacher"],
            course["duration"],
            course["occurrences"],
            "2024-08-26 09:00",
            "2024-12-13 17:00",
            course["pattern"],
            course["enrollment"],
            min_cap,
            max_cap,
            random.choice([b["id"] for b in buildings[:3]]),
            "",
            required_resources,
            f"{random.choice(['09:00', '10:00', '11:00', '14:00'])}-{random.choice(['10:00', '11:00', '12:00', '15:00', '16:00'])}" if random.random() > 0.5 else "",
            "TRUE",
            random.randint(1, 7),
            random.randint(1, 3),
            f"{course['dept']}_students",
            "in_person"
        ])

# Write room template
with open("sample_data/Room_Template.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "Resource_ID", "Resource_Type", "Building_ID", "Floor_Number", "Capacity",
        "Computer_Count", "Has_Computers", "Has_Projector", "Has_Smart_Board",
        "Special_Equipment", "Availability_Calendar_ID", "Room_Number", "Room_Features"
    ])

    for room in rooms:
        features = "Standard classroom"
        if room["type"] == "lab":
            features = "Laboratory with equipment"
        elif room["type"] == "lecture_hall":
            features = "Large lecture hall"
        elif room["type"] == "seminar_room":
            features = "Small seminar/discussion room"

        writer.writerow([
            room["id"],
            room["type"],
            room["building"],
            room["floor"],
            room["capacity"],
            room["computers"],
            room["computers"] > 0,
            room["projector"],
            room["smart_board"],
            "",
            "",
            room["id"][-3:],
            features
        ])

# Write building template
with open("sample_data/Building_Template.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "Building_ID", "Building_Name", "Building_Type", "Address", "Campus_Area",
        "Coordinates", "Floors", "Total_Rooms", "Accessibility", "Description"
    ])

    for building in buildings:
        campus_area = random.choice(["North Campus", "South Campus", "Central Campus", "West Campus"])
        floors = random.randint(3, 7)

        writer.writerow([
            building["id"],
            building["name"],
            building["type"],
            f"{random.randint(100, 999)} {building['name'].replace(' ', ' ')} Drive, University Town, ST 12345",
            campus_area,
            f"{40.7128 + random.uniform(-0.01, 0.01):.4f},{-74.0060 + random.uniform(-0.01, 0.01):.4f}",
            floors,
            random.randint(15, 50),
            "Wheelchair Accessible, Elevator, Accessible Restrooms",
            f"Main {building['type'].replace('_', ' ')} building with {floors} floors"
        ])

# Write holiday template
with open("sample_data/Holiday_Template.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "Holiday_Name", "Start_Date", "End_Date", "Year", "Affects_All_Departments",
        "Affected_Departments", "Notes"
    ])

    holidays = [
        ("Labor Day", "2024-09-02", "2024-09-02", 2024, True, "", "No classes"),
        ("Fall Break", "2024-10-14", "2024-10-18", 2024, True, "", "No classes, residence halls remain open"),
        ("Thanksgiving Break", "2024-11-27", "2024-11-29", 2024, True, "", "No classes, dining services limited"),
        ("Winter Break", "2024-12-20", "2025-01-12", 2025, True, "", "No classes, residence halls close Dec 22"),
        ("Spring Break", "2025-03-10", "2025-03-17", 2025, True, "", "No classes, residence halls remain open"),
        ("Memorial Day", "2025-05-26", "2025-05-26", 2025, True, "", "No classes"),
        ("Faculty Planning Day", "2024-08-19", "2024-08-19", 2024, True, "", "Faculty only, no classes")
    ]

    for holiday in holidays:
        writer.writerow(holiday)

# Write time blocker template
with open("sample_data/Time_Blocker_Template.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "Block_Name", "Start_Time", "End_Time", "Days_of_Week", "Start_Date", "End_Date",
        "Institution_Type", "Description", "Mandatory"
    ])

    time_blockers = [
        ("Common Lunch", "11:30", "13:30", "0,1,2,3,4", "", "", "", "Common lunch period", True),
        ("Department Meetings", "15:00", "16:30", "2", "", "", "", "Weekly department meetings", True),
        ("Morning Setup", "07:30", "08:30", "0,1,2,3,4", "", "", "Staff only", False),
        ("Evening Cleanup", "21:00", "22:00", "0,1,2,3,4", "", "", "Staff only", False),
        ("Faculty Research Time", "13:00", "17:00", "1", "", "", "research_university", "Protected research time", False),
        ("Graduate Seminars", "16:00", "17:30", "3,4", "", "", "research_university", "Graduate seminar series", False),
        ("Registration Period", "09:00", "17:00", "0,1,2,3,4", "2024-08-20", "2024-08-23", "community_college", "Priority registration", False),
        ("Advising Hours", "10:00", "15:00", "0,1,2,3,4", "2024-04-01", "2024-04-05", "community_college", "Academic advising week", False)
    ]

    for blocker in time_blockers:
        writer.writerow(blocker)

print("\nSample data generated successfully!")
print(f"Files created in 'sample_data/' directory:")
print(f"  - Teacher_Template.csv ({len(teachers)} teachers)")
print(f"  - Course_Template.csv ({len(courses)} courses)")
print(f"  - Room_Template.csv ({len(rooms)} rooms)")
print(f"  - Building_Template.csv ({len(buildings)} buildings)")
print(f"  - Holiday_Template.csv")
print(f"  - Time_Blocker_Template.csv")
print("\nYou can now import these files to test the scheduling system:")
print("  python -m edusched.scripts.import_data --type teachers --file sample_data/Teacher_Template.csv")
print("  python -m edusched.scripts.import_data --type courses --file sample_data/Course_Template.csv")
print("  python -m edusched.scripts.import_data --type resources --file sample_data/Room_Template.csv")