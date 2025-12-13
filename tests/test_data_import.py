"""Tests for data import functionality."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from edusched.utils.data_import import DataImporter, DataImportError, create_sample_csv_files
from edusched.domain.building import Building, BuildingType
from edusched.domain.resource import Resource
from edusched.domain.teacher import Teacher
from edusched.domain.department import Department
from edusched.domain.session_request import SessionRequest
from zoneinfo import ZoneInfo


class TestDataImport:
    """Test suite for data import functionality."""

    def test_import_buildings_from_csv(self):
        """Test importing buildings from CSV data."""
        csv_data = """id,name,building_type,address,coordinates,campus_area,amenities
tech_building,Technology Building,ACADEMIC,123 Tech St,"40.7128,-74.0060",North Campus,"WiFi,Projector"
library,University Library,LIBRARY,456 Library Way,"40.7130,-74.0055",Central Campus,"WiFi,Computers"
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_data)
            temp_path = Path(f.name)

        try:
            importer = DataImporter()
            buildings = importer.import_file(temp_path, "buildings")

            assert len(buildings) == 2
            assert buildings[0].id == "tech_building"
            assert buildings[0].name == "Technology Building"
            assert buildings[0].building_type == BuildingType.ACADEMIC
            assert buildings[0].coordinates == (40.7128, -74.0060)
            assert "WiFi" in buildings[0].amenities

            assert buildings[1].id == "library"
            assert buildings[1].building_type == BuildingType.LIBRARY
        finally:
            temp_path.unlink()

    def test_import_resources_from_csv(self):
        """Test importing resources/classrooms from CSV data."""
        csv_data = """id,resource_type,capacity,building_id,floor_number,attributes
Room101,classroom,30,tech_building,1,"computers=30,projector=yes"
Room201,classroom,50,tech_building,2,"computers=0,projector=yes"
Lab301,lab,25,tech_building,3,"computers=25,specialized=true"
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_data)
            temp_path = Path(f.name)

        try:
            importer = DataImporter()
            resources = importer.import_file(temp_path, "resources")

            assert len(resources) == 3

            room101 = next(r for r in resources if r.id == "Room101")
            assert room101.resource_type == "classroom"
            assert room101.capacity == 30
            assert room101.building_id == "tech_building"
            assert room101.floor_number == 1
            assert room101.attributes.get("computers") == 30

            lab301 = next(r for r in resources if r.id == "Lab301")
            assert lab301.resource_type == "lab"
            assert lab301.attributes.get("computers") == 25
        finally:
            temp_path.unlink()

    def test_import_teachers_from_csv(self):
        """Test importing teachers from CSV data."""
        csv_data = """id,name,email,department_id,title,preferred_days,max_daily_hours,preferred_buildings
alice_prof,Alice Smith,alice@univ.edu,cs,Professor,"Monday,Wednesday,Friday",4,tech_building
bob_assist,Bob Johnson,bob@univ.edu,cs,TA,"Tuesday,Thursday",8,"tech_building,library"
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_data)
            temp_path = Path(f.name)

        try:
            importer = DataImporter()
            teachers = importer.import_file(temp_path, "teachers")

            assert len(teachers) == 2

            alice = next(t for t in teachers if t.id == "alice_prof")
            assert alice.name == "Alice Smith"
            assert alice.email == "alice@univ.edu"
            assert alice.department_id == "cs"
            assert alice.title == "Professor"
            assert "monday" in [d.lower() for d in alice.preferred_days]
            assert alice.max_daily_hours == 4
            assert "tech_building" in alice.preferred_buildings
        finally:
            temp_path.unlink()

    def test_import_departments_from_csv(self):
        """Test importing departments from CSV data."""
        csv_data = """id,name,head,blacked_out_days,preferred_room_types
cs,Computer Science,Dr. Smith,"Friday,Saturday,Sunday","classroom,lab"
math,Mathematics,Dr. Jones,"Saturday,Sunday",classroom
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_data)
            temp_path = Path(f.name)

        try:
            importer = DataImporter()
            departments = importer.import_file(temp_path, "departments")

            assert len(departments) == 2

            cs_dept = next(d for d in departments if d.id == "cs")
            assert cs_dept.name == "Computer Science"
            assert cs_dept.head == "Dr. Smith"
            assert "friday" in [d.lower() for d in cs_dept.blacked_out_days]
            assert "classroom" in cs_dept.preferred_room_types
        finally:
            temp_path.unlink()

    def test_import_courses_from_csv(self):
        """Test importing courses from CSV data."""
        csv_data = """id,duration_hours,number_of_occurrences,earliest_date,latest_date,enrollment_count,min_capacity,department_id,teacher_id
cs101,2,24,"2024-01-15 09:00","2024-05-15 17:00",30,25,cs,alice_prof
cs102,1,48,"2024-01-15 09:00","2024-05-15 17:00",25,20,cs,bob_prof
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_data)
            temp_path = Path(f.name)

        try:
            importer = DataImporter()
            courses = importer.import_file(temp_path, "courses")

            assert len(courses) == 2

            cs101 = next(c for c in courses if c.id == "cs101")
            assert cs101.duration == timedelta(hours=2)
            assert cs101.number_of_occurrences == 24
            assert cs101.enrollment_count == 30
            assert cs101.min_capacity == 25
            assert cs101.department_id == "cs"
            assert cs101.teacher_id == "alice_prof"
            assert cs101.earliest_date.year == 2024
        finally:
            temp_path.unlink()

    def test_import_from_json(self):
        """Test importing data from JSON format."""
        json_data = {
            "data": [
                {
                    "id": "json_building",
                    "name": "JSON Test Building",
                    "building_type": "ACADEMIC",
                    "address": "456 JSON Street"
                },
                {
                    "id": "json_building_2",
                    "name": "JSON Test Building 2",
                    "building_type": "LIBRARY",
                    "address": "789 JSON Avenue"
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(json_data, f)
            temp_path = Path(f.name)

        try:
            importer = DataImporter()
            buildings = importer.import_file(temp_path, "buildings")

            assert len(buildings) == 2
            assert buildings[0].id == "json_building"
            assert buildings[0].name == "JSON Test Building"
            assert buildings[0].building_type == BuildingType.ACADEMIC
        finally:
            temp_path.unlink()

    @patch('pandas.read_excel')
    def test_import_from_excel(self, mock_read_excel):
        """Test importing data from Excel format."""
        # Mock pandas DataFrame
        import pandas as pd
        df_data = {
            'id': ['excel_building'],
            'name': ['Excel Test Building'],
            'building_type': ['ACADEMIC'],
            'address': ['789 Excel Street'],
            'coordinates': [None],
            'campus_area': [None],
            'amenities': [None]
        }
        mock_read_excel.return_value = pd.DataFrame(df_data)

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            temp_path = Path(f.name)

        try:
            importer = DataImporter()
            buildings = importer.import_file(temp_path, "buildings")

            assert len(buildings) == 1
            assert buildings[0].id == "excel_building"
            assert buildings[0].name == "Excel Test Building"
        finally:
            temp_path.unlink()

    def test_import_error_handling(self):
        """Test error handling during import."""
        # Test non-existent file
        importer = DataImporter()
        with pytest.raises(DataImportError, match="File not found"):
            importer.import_file("non_existent.csv", "buildings")

        # Test unsupported format
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test")
            temp_path = Path(f.name)

        try:
            with pytest.raises(DataImportError, match="Unsupported file format"):
                importer.import_file(temp_path, "buildings")
        finally:
            temp_path.unlink()

        # Test invalid data type
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("test")
            temp_path = Path(f.name)

        try:
            with pytest.raises(DataImportError, match="Unknown data type"):
                importer.import_file(temp_path, "invalid_type")
        finally:
            temp_path.unlink()

    def test_parse_list_field(self):
        """Test parsing list fields from various formats."""
        importer = DataImporter()

        # Test comma-separated string
        result = importer._parse_list_field("item1,item2,item3")
        assert result == ["item1", "item2", "item3"]

        # Test with spaces
        result = importer._parse_list_field(" item1 , item2 , item3 ")
        assert result == ["item1", "item2", "item3"]

        # Test empty values
        assert importer._parse_list_field(None) is None
        assert importer._parse_list_field("") is None

        # Test list input
        result = importer._parse_list_field(["a", "b"])
        assert result == ["a", "b"]

    def test_parse_dict_field(self):
        """Test parsing dictionary fields from various formats."""
        importer = DataImporter()

        # Test JSON string
        result = importer._parse_dict_field('{"key1": "value1", "key2": "value2"}')
        assert result == {"key1": "value1", "key2": "value2"}

        # Test key=value format
        result = importer._parse_dict_field("key1=value1,key2=value2")
        assert result == {"key1": "value1", "key2": "value2"}

        # Test empty values
        assert importer._parse_dict_field(None) is None
        assert importer._parse_dict_field("") is None

    def test_parse_datetime(self):
        """Test datetime parsing from various formats."""
        from zoneinfo import ZoneInfo
        importer = DataImporter()
        utc = ZoneInfo("UTC")

        # Test different datetime formats
        test_cases = [
            ("2024-01-15 09:00:00", "2024-01-15 09:00:00"),
            ("2024-01-15 09:00", "2024-01-15 09:00:00"),
            ("2024-01-15", "2024-01-15 00:00:00"),
            ("01/15/2024 09:00", "2024-01-15 09:00:00"),
            ("01/15/2024", "2024-01-15 00:00:00"),
        ]

        for input_str, expected_str in test_cases:
            result = importer._parse_datetime(input_str, utc)
            expected = datetime.strptime(expected_str, "%Y-%m-%d %H:%M:%S")
            expected = expected.replace(tzinfo=utc)
            assert result == expected, f"Failed to parse: {input_str}"

    def test_create_sample_csv_files(self):
        """Test creation of sample CSV files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            create_sample_csv_files(temp_dir)

            temp_path = Path(temp_dir)

            # Check that files were created
            expected_files = [
                "buildings_sample.csv",
                "resources_sample.csv",
                "teachers_sample.csv",
                "departments_sample.csv",
                "courses_sample.csv"
            ]

            for filename in expected_files:
                file_path = temp_path / filename
                assert file_path.exists(), f"Sample file {filename} was not created"

                # Check file has content
                assert file_path.stat().st_size > 0, f"Sample file {filename} is empty"

    def test_integration_workflow(self):
        """Test complete import workflow with all data types."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create sample files
            create_sample_csv_files(temp_path)

            # Import all data types
            importer = DataImporter()

            # Import and verify buildings
            buildings = importer.import_file(temp_path / "buildings_sample.csv", "buildings")
            assert len(buildings) > 0
            assert all(isinstance(b, Building) for b in buildings)

            # Import and verify resources
            resources = importer.import_file(temp_path / "resources_sample.csv", "resources")
            assert len(resources) > 0
            assert all(isinstance(r, Resource) for r in resources)

            # Import and verify teachers
            teachers = importer.import_file(temp_path / "teachers_sample.csv", "teachers")
            assert len(teachers) > 0
            assert all(isinstance(t, Teacher) for t in teachers)

            # Import and verify departments
            departments = importer.import_file(temp_path / "departments_sample.csv", "departments")
            assert len(departments) > 0
            assert all(isinstance(d, Department) for d in departments)

            # Import and verify courses
            courses = importer.import_file(temp_path / "courses_sample.csv", "courses")
            assert len(courses) > 0
            assert all(isinstance(c, SessionRequest) for c in courses)

            # Verify relationships are maintained
            if teachers and resources:
                # Check that teacher preferences reference buildings
                teacher_with_pref = next((t for t in teachers if t.preferred_buildings), None)
                if teacher_with_pref:
                    assert len(teacher_with_pref.preferred_buildings) > 0

            if resources and buildings:
                # Check that resources reference buildings
                resource_with_building = next((r for r in resources if r.building_id), None)
                if resource_with_building:
                    assert resource_with_building.building_id in [b.id for b in buildings]