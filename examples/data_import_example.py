"""Example of how to use the data import system."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from edusched.utils.data_import import DataImporter, create_sample_csv_files
from edusched.domain.building import Building, BuildingType
from edusched.domain.resource import Resource
from edusched.domain.teacher import Teacher
from edusched.domain.session_request import SessionRequest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def main():
    """Demonstrate data import functionality."""
    print("=== EduSched Data Import Example ===\n")

    # Create sample CSV files
    print("1. Creating sample CSV files...")
    output_dir = Path("./sample_imports")
    create_sample_csv_files(output_dir)
    print(f"   ✓ Created sample files in {output_dir}\n")

    # Import buildings
    print("2. Importing buildings...")
    importer = DataImporter()
    try:
        buildings = importer.import_file(output_dir / "buildings_sample.csv", "buildings")
        print(f"   ✓ Imported {len(buildings)} buildings:")
        for building in buildings:
            print(f"     - {building.id}: {building.name} ({building.building_type.value})")
    except Exception as e:
        print(f"   ✗ Failed to import buildings: {e}")
    print()

    # Import resources/classrooms
    print("3. Importing classrooms/resources...")
    try:
        resources = importer.import_file(output_dir / "resources_sample.csv", "resources")
        print(f"   ✓ Imported {len(resources)} resources:")
        for resource in resources:
            print(f"     - {resource.id}: {resource.resource_type} (capacity: {resource.capacity or 'N/A'})")
    except Exception as e:
        print(f"   ✗ Failed to import resources: {e}")
    print()

    # Import teachers
    print("4. Importing teachers...")
    try:
        teachers = importer.import_file(output_dir / "teachers_sample.csv", "teachers")
        print(f"   ✓ Imported {len(teachers)} teachers:")
        for teacher in teachers:
            print(f"     - {teacher.id}: {teacher.name} ({teacher.title})")
            if teacher.preferred_days:
                print(f"       Preferred days: {', '.join(teacher.preferred_days)}")
            if teacher.max_daily_hours:
                print(f"       Max daily hours: {teacher.max_daily_hours}")
    except Exception as e:
        print(f"   ✗ Failed to import teachers: {e}")
    print()

    # Import departments
    print("5. Importing departments...")
    try:
        departments = importer.import_file(output_dir / "departments_sample.csv", "departments")
        print(f"   ✓ Imported {len(departments)} departments:")
        for dept in departments:
            print(f"     - {dept.id}: {dept.name}")
            if dept.blacked_out_days:
                print(f"       Blacked out days: {', '.join(dept.blacked_out_days)}")
    except Exception as e:
        print(f"   ✗ Failed to import departments: {e}")
    print()

    # Import courses
    print("6. Importing courses...")
    try:
        courses = importer.import_file(output_dir / "courses_sample.csv", "courses")
        print(f"   ✓ Imported {len(courses)} courses:")
        for course in courses:
            print(f"     - {course.id}: {course.duration} hours, {course.number_of_occurrences} sessions")
            print(f"       Enrollment: {course.enrollment_count}, Teacher: {course.teacher_id}")
            print(f"       Date range: {course.earliest_date} to {course.latest_date}")
    except Exception as e:
        print(f"   ✗ Failed to import courses: {e}")
    print()

    # Demonstrate direct data creation
    print("7. Creating data directly in Python...")
    try:
        # Create a building
        tech_building = Building(
            id="tech_main",
            name="Technology Main Building",
            building_type=BuildingType.ACADEMIC,
            address="123 Innovation Drive",
            campus_area="North Campus"
        )
        print(f"   ✓ Created building: {tech_building.name}")

        # Create a classroom
        classroom = Resource(
            id="Tech101",
            resource_type="classroom",
            capacity=40,
            building_id="tech_main",
            floor_number=2
        )
        print(f"   ✓ Created classroom: {classroom.id} (capacity: {classroom.capacity})")

        # Create a teacher
        professor = Teacher(
            id="john_doe",
            name="John Doe",
            email="john.doe@university.edu",
            preferred_days=["monday", "wednesday", "friday"],
            max_daily_hours=4
        )
        print(f"   ✓ Created teacher: {professor.name}")

        # Create a course
        course = SessionRequest(
            id="intro_programming",
            duration=timedelta(hours=2),
            number_of_occurrences=12,
            earliest_date=datetime(2024, 1, 15, 9, 0, tzinfo=ZoneInfo("UTC")),
            latest_date=datetime(2024, 5, 15, 17, 0, tzinfo=ZoneInfo("UTC")),
            enrollment_count=35,
            min_capacity=30,
            teacher_id="john_doe",
            preferred_building_id="tech_main"
        )
        print(f"   ✓ Created course: {course.id} ({course.enrollment_count} students)")

    except Exception as e:
        print(f"   ✗ Failed to create data: {e}")

    print("\n=== Example Complete ===")
    print("\nTo use the command-line tool:")
    print("  python scripts/import_data.py import buildings.csv buildings")
    print("  python scripts/import_data.py validate teachers.csv teachers")
    print("  python scripts/import_data.py create-templates ./templates")
    print("\nTo use the API:")
    print("  POST /api/v1/import/upload")
    print("  GET  /api/v1/import/templates/sample-csvs")
    print("  POST /api/v1/import/batch")


if __name__ == "__main__":
    main()