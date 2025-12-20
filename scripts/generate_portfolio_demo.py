#!/usr/bin/env python3
"""
Generate comprehensive demo data for portfolio showcase.
Creates realistic university scheduling scenario with multiple departments,
courses, teachers, and constraints.
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

# Demo university data
UNIVERSITY_DATA = {
    "departments": [
        {
            "id": "cs_dept",
            "name": "Computer Science Department",
            "head": "Dr. Sarah Chen",
            "building_id": "tech_building",
            "contact_email": "cs@university.edu",
            "preferred_room_types": ["classroom", "lab", "lecture_hall"],
            "required_amenities": ["WiFi", "Projector", "Whiteboard"]
        },
        {
            "id": "math_dept", 
            "name": "Mathematics Department",
            "head": "Dr. Michael Roberts",
            "building_id": "academic_building",
            "contact_email": "math@university.edu",
            "preferred_room_types": ["classroom", "lecture_hall"],
            "required_amenities": ["WiFi", "Whiteboard"]
        },
        {
            "id": "physics_dept",
            "name": "Physics Department", 
            "head": "Dr. Jennifer Liu",
            "building_id": "science_building",
            "contact_email": "physics@university.edu",
            "preferred_room_types": ["classroom", "lab", "lecture_hall"],
            "required_amenities": ["WiFi", "Projector", "Lab Equipment"]
        }
    ],
    
    "teachers": [
        {
            "id": "chen_prof",
            "name": "Dr. Sarah Chen",
            "email": "chen@university.edu",
            "department_id": "cs_dept",
            "title": "Professor",
            "preferred_days": ["monday", "wednesday", "friday"],
            "max_daily_hours": 4,
            "preferred_buildings": ["tech_building"],
            "preferred_room_types": ["classroom", "lab"],
            "max_class_size": 50
        },
        {
            "id": "roberts_prof", 
            "name": "Dr. Michael Roberts",
            "email": "roberts@university.edu",
            "department_id": "math_dept",
            "title": "Professor",
            "preferred_days": ["tuesday", "thursday"],
            "max_daily_hours": 4,
            "preferred_buildings": ["academic_building"],
            "preferred_room_types": ["classroom", "lecture_hall"],
            "max_class_size": 100
        },
        {
            "id": "liu_prof",
            "name": "Dr. Jennifer Liu", 
            "email": "liu@university.edu",
            "department_id": "physics_dept",
            "title": "Professor",
            "preferred_days": ["monday", "wednesday", "friday"],
            "max_daily_hours": 5,
            "preferred_buildings": ["science_building"],
            "preferred_room_types": ["classroom", "lab"],
            "max_class_size": 30
        },
        {
            "id": "johnson_ta",
            "name": "Alex Johnson",
            "email": "johnson@university.edu", 
            "department_id": "cs_dept",
            "title": "Teaching Assistant",
            "preferred_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "max_daily_hours": 8,
            "preferred_buildings": ["tech_building"],
            "preferred_room_types": ["classroom"],
            "max_class_size": 25
        },
        {
            "id": "williams_ta",
            "name": "Emma Williams",
            "email": "williams@university.edu",
            "department_id": "math_dept", 
            "title": "Teaching Assistant",
            "preferred_days": ["tuesday", "thursday"],
            "max_daily_hours": 6,
            "preferred_buildings": ["academic_building"],
            "preferred_room_types": ["classroom"],
            "max_class_size": 30
        }
    ],
    
    "buildings": [
        {
            "id": "tech_building",
            "name": "Technology Building",
            "building_type": "ACADEMIC",
            "address": "123 Tech Street, University Campus",
            "coordinates": "40.7128,-74.0060",
            "campus_area": "North Campus",
            "amenities": "WiFi,Projector,Whiteboard,Computers,Lab Equipment"
        },
        {
            "id": "academic_building",
            "name": "Academic Building", 
            "building_type": "ACADEMIC",
            "address": "456 Academic Way, University Campus",
            "coordinates": "40.7130,-74.0055",
            "campus_area": "Central Campus",
            "amenities": "WiFi,Projector,Whiteboard, Lecture Capture"
        },
        {
            "id": "science_building",
            "name": "Science Building",
            "building_type": "ACADEMIC", 
            "address": "789 Science Avenue, University Campus",
            "coordinates": "40.7132,-74.0050",
            "campus_area": "South Campus",
            "amenities": "WiFi,Projector,Whiteboard,Lab Equipment,Safety Equipment"
        }
    ],
    
    "resources": [
        # Technology Building
        {
            "id": "tech_101",
            "resource_type": "classroom",
            "capacity": 30,
            "building_id": "tech_building",
            "floor_number": 1,
            "attributes": "computers=30,projector=yes,whiteboard=yes"
        },
        {
            "id": "tech_201", 
            "resource_type": "classroom",
            "capacity": 50,
            "building_id": "tech_building",
            "floor_number": 2,
            "attributes": "computers=0,projector=yes,whiteboard=yes"
        },
        {
            "id": "tech_lab_301",
            "resource_type": "lab",
            "capacity": 25,
            "building_id": "tech_building", 
            "floor_number": 3,
            "attributes": "computers=25,projector=yes,specialized_software=yes"
        },
        {
            "id": "tech_auditorium",
            "resource_type": "lecture_hall",
            "capacity": 150,
            "building_id": "tech_building",
            "floor_number": 1,
            "attributes": "computers=0,projector=yes,lecture_capture=yes"
        },
        
        # Academic Building
        {
            "id": "acad_101",
            "resource_type": "classroom", 
            "capacity": 40,
            "building_id": "academic_building",
            "floor_number": 1,
            "attributes": "computers=0,projector=yes,whiteboard=yes"
        },
        {
            "id": "acad_201",
            "resource_type": "classroom",
            "capacity": 60,
            "building_id": "academic_building",
            "floor_number": 2,
            "attributes": "computers=0,projector=yes,whiteboard=yes"
        },
        {
            "id": "acad_lecture_hall",
            "resource_type": "lecture_hall",
            "capacity": 200,
            "building_id": "academic_building",
            "floor_number": 1,
            "attributes": "computers=0,projector=yes,lecture_capture=yes"
        },
        
        # Science Building
        {
            "id": "sci_lab_101",
            "resource_type": "lab",
            "capacity": 20,
            "building_id": "science_building",
            "floor_number": 1,
            "attributes": "computers=20,lab_equipment=yes,safety_equipment=yes"
        },
        {
            "id": "sci_201",
            "resource_type": "classroom",
            "capacity": 35,
            "building_id": "science_building",
            "floor_number": 2,
            "attributes": "computers=0,projector=yes,whiteboard=yes"
        },
        {
            "id": "sci_lecture_hall",
            "resource_type": "lecture_hall",
            "capacity": 120,
            "building_id": "science_building",
            "floor_number": 1,
            "attributes": "computers=0,projector=yes,demo_equipment=yes"
        }
    ],
    
    "courses": [
        # Computer Science Courses
        {
            "id": "cs101",
            "duration_hours": 2,
            "number_of_occurrences": 24,
            "earliest_date": "2024-01-15 09:00",
            "latest_date": "2024-05-15 17:00",
            "enrollment_count": 45,
            "min_capacity": 25,
            "max_capacity": 60,
            "department_id": "cs_dept",
            "teacher_id": "chen_prof",
            "preferred_building_id": "tech_building",
            "required_resource_types": "{\"computers\": \"optional\", \"projector\": \"required\"}"
        },
        {
            "id": "cs102", 
            "duration_hours": 2,
            "number_of_occurrences": 24,
            "earliest_date": "2024-01-15 09:00",
            "latest_date": "2024-05-15 17:00",
            "enrollment_count": 30,
            "min_capacity": 20,
            "max_capacity": 40,
            "department_id": "cs_dept",
            "teacher_id": "chen_prof",
            "preferred_building_id": "tech_building",
            "required_resource_types": "{\"computers\": \"required\", \"specialized_software\": \"optional\"}"
        },
        {
            "id": "cs201",
            "duration_hours": 3,
            "number_of_occurrences": 16,
            "earliest_date": "2024-01-15 10:00",
            "latest_date": "2024-05-15 17:00", 
            "enrollment_count": 25,
            "min_capacity": 15,
            "max_capacity": 30,
            "department_id": "cs_dept",
            "teacher_id": "johnson_ta",
            "preferred_building_id": "tech_building",
            "required_resource_types": "{\"computers\": \"required\", \"specialized_software\": \"required\"}"
        },
        
        # Mathematics Courses
        {
            "id": "math101",
            "duration_hours": 2,
            "number_of_occurrences": 24,
            "earliest_date": "2024-01-15 10:00",
            "latest_date": "2024-05-15 17:00",
            "enrollment_count": 80,
            "min_capacity": 50,
            "max_capacity": 150,
            "department_id": "math_dept",
            "teacher_id": "roberts_prof",
            "preferred_building_id": "academic_building",
            "required_resource_types": "{\"projector\": \"required\", \"whiteboard\": \"required\"}"
        },
        {
            "id": "math201",
            "duration_hours": 2,
            "number_of_occurrences": 24,
            "earliest_date": "2024-01-15 14:00",
            "latest_date": "2024-05-15 17:00",
            "enrollment_count": 35,
            "min_capacity": 25,
            "max_capacity": 50,
            "department_id": "math_dept",
            "teacher_id": "williams_ta",
            "preferred_building_id": "academic_building",
            "required_resource_types": "{\"whiteboard\": \"required\", \"projector\": \"optional\"}"
        },
        
        # Physics Courses
        {
            "id": "phys101",
            "duration_hours": 3,
            "number_of_occurrences": 16,
            "earliest_date": "2024-01-15 09:00",
            "latest_date": "2024-05-15 17:00",
            "enrollment_count": 28,
            "min_capacity": 20,
            "max_capacity": 35,
            "department_id": "physics_dept",
            "teacher_id": "liu_prof",
            "preferred_building_id": "science_building",
            "required_resource_types": "{\"lab_equipment\": \"required\", \"computers\": \"optional\"}"
        },
        {
            "id": "phys201",
            "duration_hours": 3,
            "number_of_occurrences": 16,
            "earliest_date": "2024-01-15 14:00",
            "latest_date": "2024-05-15 17:00",
            "enrollment_count": 22,
            "min_capacity": 15,
            "max_capacity": 30,
            "department_id": "physics_dept",
            "teacher_id": "liu_prof",
            "preferred_building_id": "science_building",
            "required_resource_types": "{\"lab_equipment\": \"required\", \"safety_equipment\": \"required\"}"
        }
    ],
    
    "time_blockers": [
        {
            "id": "spring_break",
            "name": "Spring Break 2024",
            "description": "University spring break period",
            "start_date": "2024-03-10 00:00",
            "end_date": "2024-03-17 23:59",
            "resource_ids": ["all"],
            "resource_types": ["all"]
        },
        {
            "id": "finals_week",
            "name": "Finals Week 2024",
            "description": "Final examination period - no regular classes",
            "start_date": "2024-04-29 00:00", 
            "end_date": "2024-05-03 23:59",
            "resource_ids": ["all"],
            "resource_types": ["all"]
        },
        {
            "id": "tech_maintenance",
            "name": "Tech Building Maintenance",
            "description": "Scheduled maintenance in Technology Building",
            "start_date": "2024-02-15 00:00",
            "end_date": "2024-02-17 23:59",
            "resource_ids": ["tech_101", "tech_201", "tech_lab_301"],
            "resource_types": ["classroom", "lab"]
        }
    ]
}

def write_csv_file(data: List[Dict[str, Any]], filename: str, fieldnames: List[str]):
    """Write data to CSV file."""
    import csv
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def main():
    """Generate all demo data files."""
    output_dir = Path("demo_data")
    output_dir.mkdir(exist_ok=True)
    
    print("🏫 Generating Portfolio Demo Data")
    print("=" * 50)
    
    # Generate departments
    dept_file = output_dir / "departments_demo.csv"
    write_csv_file(
        UNIVERSITY_DATA["departments"],
        str(dept_file),
        ["id", "name", "head", "building_id", "contact_email", "preferred_room_types", "required_amenities"]
    )
    print(f"✓ Created {dept_file.name} with {len(UNIVERSITY_DATA['departments'])} departments")
    
    # Generate teachers
    teachers_file = output_dir / "teachers_demo.csv"
    write_csv_file(
        UNIVERSITY_DATA["teachers"],
        str(teachers_file),
        ["id", "name", "email", "department_id", "title", "preferred_days", "max_daily_hours", 
         "preferred_buildings", "preferred_room_types", "max_class_size"]
    )
    print(f"✓ Created {teachers_file.name} with {len(UNIVERSITY_DATA['teachers'])} teachers")
    
    # Generate buildings
    buildings_file = output_dir / "buildings_demo.csv"
    write_csv_file(
        UNIVERSITY_DATA["buildings"],
        str(buildings_file),
        ["id", "name", "building_type", "address", "coordinates", "campus_area", "amenities"]
    )
    print(f"✓ Created {buildings_file.name} with {len(UNIVERSITY_DATA['buildings'])} buildings")
    
    # Generate resources
    resources_file = output_dir / "resources_demo.csv"
    write_csv_file(
        UNIVERSITY_DATA["resources"],
        str(resources_file),
        ["id", "resource_type", "capacity", "building_id", "floor_number", "attributes"]
    )
    print(f"✓ Created {resources_file.name} with {len(UNIVERSITY_DATA['resources'])} resources")
    
    # Generate courses
    courses_file = output_dir / "courses_demo.csv"
    write_csv_file(
        UNIVERSITY_DATA["courses"],
        str(courses_file),
        ["id", "duration_hours", "number_of_occurrences", "earliest_date", "latest_date",
         "enrollment_count", "min_capacity", "max_capacity", "department_id", "teacher_id",
         "preferred_building_id", "required_resource_types"]
    )
    print(f"✓ Created {courses_file.name} with {len(UNIVERSITY_DATA['courses'])} courses")
    
    # Generate time blockers
    blockers_file = output_dir / "time_blockers_demo.csv"
    write_csv_file(
        UNIVERSITY_DATA["time_blockers"],
        str(blockers_file),
        ["id", "name", "description", "start_date", "end_date", "resource_ids", "resource_types"]
    )
    print(f"✓ Created {blockers_file.name} with {len(UNIVERSITY_DATA['time_blockers'])} time blockers")
    
    # Generate JSON summary
    summary = {
        "generated_at": datetime.now().isoformat(),
        "university": "Demo University",
        "semester": "Spring 2024",
        "statistics": {
            "departments": len(UNIVERSITY_DATA["departments"]),
            "teachers": len(UNIVERSITY_DATA["teachers"]),
            "buildings": len(UNIVERSITY_DATA["buildings"]),
            "resources": len(UNIVERSITY_DATA["resources"]),
            "courses": len(UNIVERSITY_DATA["courses"]),
            "time_blockers": len(UNIVERSITY_DATA["time_blockers"]),
            "total_enrollment": sum(course["enrollment_count"] for course in UNIVERSITY_DATA["courses"]),
            "total_class_hours": sum(
                course["duration_hours"] * course["number_of_occurrences"] 
                for course in UNIVERSITY_DATA["courses"]
            )
        },
        "features_demonstrated": [
            "Multi-department scheduling",
            "Teacher preferences and constraints",
            "Resource capacity management", 
            "Building and room type preferences",
            "Time blocking and blackout periods",
            "Real-time conflict detection",
            "Optimization algorithms",
            "Import/export functionality",
            "WebSocket real-time updates"
        ]
    }
    
    summary_file = output_dir / "demo_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"✓ Created {summary_file.name}")
    
    print("\n" + "=" * 50)
    print("📊 Demo Statistics:")
    print(f"   • {summary['statistics']['departments']} departments")
    print(f"   • {summary['statistics']['teachers']} teachers") 
    print(f"   • {summary['statistics']['buildings']} buildings")
    print(f"   • {summary['statistics']['resources']} total resources")
    print(f"   • {summary['statistics']['courses']} courses")
    print(f"   • {summary['statistics']['total_enrollment']} total student enrollments")
    print(f"   • {summary['statistics']['total_class_hours']} total class hours")
    print(f"\n🎯 Ready for portfolio showcase!")
    print(f"   Upload these files to test the complete scheduling system.")
    print(f"   All files created in: {output_dir.absolute()}")

if __name__ == "__main__":
    main()
