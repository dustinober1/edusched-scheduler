#!/usr/bin/env python3
"""
Full-stack test script for EduSched.

This script:
1. Generates sample schedule data
2. Submits it to the backend API
3. Verifies the response
4. Tests WebSocket connections
"""

import json
import asyncio
import websockets
import requests
import time
from datetime import datetime, time as dt_time, timedelta
from typing import List, Dict, Any
from dataclasses import dataclass
from pathlib import Path

# Import EduSched modules
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from edusched.domain.problem import Problem, SessionRequest, Resource
from edusched.domain.calendar import Calendar, WeekdayPattern, DateRange
from edusched.constraints.time_conflicts import TimeConflict
from edusched.constraints.capacity import RoomCapacity
from edusched.constraints.blackout_dates import BlackoutDateConstraint
from edusched.core_api import solve


@dataclass
class TestConfig:
    """Configuration for the test."""
    api_url: str = "http://localhost:8000"
    ws_url: str = "ws://localhost:8000"
    test_user_id: str = "test-user-123"


class TestDataGenerator:
    """Generate sample scheduling data for testing."""

    def __init__(self):
        self.courses = []
        self.rooms = []
        self.teachers = []

    def create_sample_courses(self) -> List[Dict[str, Any]]:
        """Create sample course data."""
        courses = [
            {
                "id": "CS101",
                "name": "Introduction to Computer Science",
                "course_code": "CS101",
                "teacher": "Dr. Alice Johnson",
                "enrollment": 30,
                "duration_minutes": 90,
                "sessions_per_week": 3,
                "preferred_days": ["Monday", "Wednesday", "Friday"],
                "preferred_time": dt_time(10, 0),
                "requires_lab": False,
                "requires_computer": True
            },
            {
                "id": "CS201",
                "name": "Data Structures",
                "course_code": "CS201",
                "teacher": "Dr. Bob Smith",
                "enrollment": 25,
                "duration_minutes": 90,
                "sessions_per_week": 2,
                "preferred_days": ["Tuesday", "Thursday"],
                "preferred_time": dt_time(14, 0),
                "requires_lab": False,
                "requires_computer": True
            },
            {
                "id": "CS301",
                "name": "Algorithms",
                "course_code": "CS301",
                "teacher": "Dr. Carol Williams",
                "enrollment": 20,
                "duration_minutes": 90,
                "sessions_per_week": 2,
                "preferred_days": ["Monday", "Wednesday"],
                "preferred_time": dt_time(9, 0),
                "requires_lab": False,
                "requires_computer": True
            },
            {
                "id": "LAB101",
                "name": "Computer Lab",
                "course_code": "LAB101",
                "teacher": "Dr. Alice Johnson",
                "enrollment": 15,
                "duration_minutes": 120,
                "sessions_per_week": 1,
                "preferred_days": ["Friday"],
                "preferred_time": dt_time(13, 0),
                "requires_lab": True,
                "requires_computer": True
            },
            {
                "id": "MATH101",
                "name": "Calculus I",
                "course_code": "MATH101",
                "teacher": "Dr. David Brown",
                "enrollment": 35,
                "duration_minutes": 90,
                "sessions_per_week": 3,
                "preferred_days": ["Monday", "Wednesday", "Friday"],
                "preferred_time": dt_time(11, 0),
                "requires_lab": False,
                "requires_computer": False
            }
        ]
        self.courses = courses
        return courses

    def create_sample_rooms(self) -> List[Dict[str, Any]]:
        """Create sample room data."""
        rooms = [
            {
                "id": "ROOM101",
                "name": "Lecture Hall A",
                "building_id": "MAIN",
                "capacity": 50,
                "has_computer": True,
                "has_projector": True,
                "room_type": "lecture"
            },
            {
                "id": "ROOM102",
                "name": "Classroom B",
                "building_id": "MAIN",
                "capacity": 30,
                "has_computer": True,
                "has_projector": True,
                "room_type": "classroom"
            },
            {
                "id": "LAB201",
                "name": "Computer Lab 1",
                "building_id": "TECH",
                "capacity": 25,
                "has_computer": True,
                "has_projector": True,
                "room_type": "lab"
            },
            {
                "id": "ROOM301",
                "name": "Seminar Room",
                "building_id": "LIBRARY",
                "capacity": 20,
                "has_computer": False,
                "has_projector": True,
                "room_type": "seminar"
            },
            {
                "id": "AUD101",
                "name": "Main Auditorium",
                "building_id": "MAIN",
                "capacity": 100,
                "has_computer": False,
                "has_projector": True,
                "room_type": "auditorium"
            }
        ]
        self.rooms = rooms
        return rooms

    def create_problem(self) -> Problem:
        """Create a scheduling problem from sample data."""
        # Create date range for semester
        start_date = datetime(2024, 1, 15).date()
        end_date = datetime(2024, 5, 15).date()
        date_range = DateRange(start_date, end_date)

        # Create calendars for each weekday pattern
        calendars = []
        weekday_patterns = [
            {"days": [0, 2, 4], "name": "MWF"},  # Monday, Wednesday, Friday
            {"days": [1, 3], "name": "TR"},      # Tuesday, Thursday
            {"days": [4], "name": "F"}           # Friday only
        ]

        for pattern in weekday_patterns:
            calendar = Calendar(
                id=f"cal-{pattern['name']}",
                name=f"{pattern['name']} Pattern",
                weekday_patterns=[WeekdayPattern(pattern["days"])],
                date_ranges=[date_range],
                daily_start_time=dt_time(8, 0),
                daily_end_time=dt_time(18, 0),
                timezone="America/New_York"
            )
            calendars.append(calendar)

        # Create session requests
        requests = []
        for course in self.courses:
            # Find appropriate calendar
            if course["sessions_per_week"] == 3:
                cal_id = "cal-MWF"
            elif course["sessions_per_week"] == 2:
                cal_id = "cal-TR"
            else:
                cal_id = "cal-F"

            calendar = next(c for c in calendars if c.id == cal_id)

            # Create blackout dates for holidays (example)
            blackout_dates = [
                datetime(2024, 3, 11).date(),  # Spring break week
                datetime(2024, 3, 12).date(),
                datetime(2024, 3, 13).date(),
                datetime(2024, 3, 14).date(),
                datetime(2024, 3, 15).date()
            ]

            request = SessionRequest(
                id=course["id"],
                name=course["name"],
                course_code=course["course_code"],
                teacher_name=course["teacher"],
                enrollment=course["enrollment"],
                duration=timedelta(minutes=course["duration_minutes"]),
                calendar=calendar,
                preferred_time=course["preferred_time"],
                requires_lab=course.get("requires_lab", False),
                requires_computer=course.get("requires_computer", False),
                blackout_dates=blackout_dates
            )
            requests.append(request)

        # Create resources (rooms)
        resources = []
        for room in self.rooms:
            # Create availability calendar for the room
            room_calendar = Calendar(
                id=f"room-{room['id']}-cal",
                name=f"Room {room['name']} Availability",
                weekday_patterns=[WeekdayPattern([0, 1, 2, 3, 4])],  # Monday-Friday
                date_ranges=[date_range],
                daily_start_time=dt_time(8, 0),
                daily_end_time=dt_time(18, 0),
                timezone="America/New_York"
            )

            resource = Resource(
                id=room["id"],
                name=room["name"],
                capacity=room["capacity"],
                resource_type=room["room_type"],
                attributes={
                    "building_id": room["building_id"],
                    "has_computer": room["has_computer"],
                    "has_projector": room["has_projector"]
                },
                calendar=room_calendar
            )
            resources.append(resource)

        # Create constraints
        constraints = [
            TimeConflict(),
            RoomCapacity(),
            BlackoutDateConstraint()
        ]

        # Create problem
        problem = Problem(
            requests=requests,
            resources=resources,
            calendars=calendars,
            constraints=constraints
        )

        return problem


class FullStackTester:
    """Test the full EduSched stack."""

    def __init__(self, config: TestConfig):
        self.config = config
        self.generator = TestDataGenerator()
        self.test_results = []

    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def record_result(self, test_name: str, passed: bool, details: str = ""):
        """Record a test result."""
        result = {
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)

        status = "✅" if passed else "❌"
        self.log(f"{status} {test_name}: {details}")

    def test_backend_health(self) -> bool:
        """Test if the backend is running and healthy."""
        try:
            response = requests.get(f"{self.config.api_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.record_result(
                    "Backend Health Check",
                    True,
                    f"Status: {data.get('status')}, Version: {data.get('version')}"
                )
                return True
        except Exception as e:
            self.record_result(
                "Backend Health Check",
                False,
                f"Error: {str(e)}"
            )
        return False

    def test_create_schedule(self) -> Dict[str, Any]:
        """Test creating a schedule via the API."""
        # First, solve locally to get expected data
        self.log("Generating sample schedule data...")
        problem = self.generator.create_problem()

        # Solve locally first
        self.log("Solving schedule locally...")
        result = solve(problem, backend="heuristic", seed=42)

        self.log(f"Local solve completed. Generated {len(result.assignments)} assignments.")

        # Now test API
        schedule_request = {
            "solver": "heuristic",
            "seed": 42,
            "optimize": True
        }

        try:
            # Make API request
            self.log("Sending schedule creation request to API...")
            response = requests.post(
                f"{self.config.api_url}/api/v1/schedules/",
                json=schedule_request,
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                self.record_result(
                    "Create Schedule API",
                    True,
                    f"Schedule ID: {data.get('id')}, Assignments: {data.get('total_assignments')}"
                )
                return data
            else:
                self.record_result(
                    "Create Schedule API",
                    False,
                    f"Status: {response.status_code}, Error: {response.text}"
                )
                return {}
        except Exception as e:
            self.record_result(
                "Create Schedule API",
                False,
                f"Exception: {str(e)}"
            )
            return {}

    def test_get_schedule(self, schedule_id: str):
        """Test retrieving a schedule."""
        try:
            response = requests.get(
                f"{self.config.api_url}/api/v1/schedules/{schedule_id}",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                self.record_result(
                    "Get Schedule API",
                    True,
                    f"Retrieved schedule: {data.get('name')}, Assignments: {len(data.get('assignments', []))}"
                )
                return data
            else:
                self.record_result(
                    "Get Schedule API",
                    False,
                    f"Status: {response.status_code}"
                )
        except Exception as e:
            self.record_result(
                "Get Schedule API",
                False,
                f"Exception: {str(e)}"
            )

    def test_list_schedules(self):
        """Test listing schedules."""
        try:
            response = requests.get(
                f"{self.config.api_url}/api/v1/schedules/",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                self.record_result(
                    "List Schedules API",
                    True,
                    f"Found {data.get('total', 0)} schedules"
                )
                return data
            else:
                self.record_result(
                    "List Schedules API",
                    False,
                    f"Status: {response.status_code}"
                )
        except Exception as e:
            self.record_result(
                "List Schedules API",
                False,
                f"Exception: {str(e)}"
            )

    async def test_websocket(self):
        """Test WebSocket connection for real-time updates."""
        try:
            # Construct WebSocket URL
            ws_url = f"{self.config.ws_url}/ws?user_id={self.config.test_user_id}"

            self.log(f"Connecting to WebSocket: {ws_url}")

            async with websockets.connect(ws_url) as websocket:
                self.record_result(
                    "WebSocket Connection",
                    True,
                    "Connected successfully"
                )

                # Send a test message
                await websocket.send(json.dumps({
                    "type": "ping",
                    "timestamp": datetime.now().isoformat()
                }))

                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(response)
                    self.record_result(
                        "WebSocket Communication",
                        True,
                        f"Received: {data.get('type', 'unknown')}"
                    )
                except asyncio.TimeoutError:
                    self.record_result(
                        "WebSocket Communication",
                        False,
                        "No response received within timeout"
                    )

        except Exception as e:
            self.record_result(
                "WebSocket Connection",
                False,
                f"Exception: {str(e)}"
            )

    def test_schedule_export(self, schedule_id: str):
        """Test schedule export functionality."""
        formats = ["json", "csv", "ical"]

        for fmt in formats:
            try:
                response = requests.get(
                    f"{self.config.api_url}/api/v1/schedules/{schedule_id}/export?format={fmt}",
                    timeout=10
                )

                if response.status_code == 200:
                    self.record_result(
                        f"Export Schedule ({fmt})",
                        True,
                        f"Content-Type: {response.headers.get('content-type')}"
                    )
                else:
                    self.record_result(
                        f"Export Schedule ({fmt})",
                        False,
                        f"Status: {response.status_code}"
                    )
            except Exception as e:
                self.record_result(
                    f"Export Schedule ({fmt})",
                    False,
                    f"Exception: {str(e)}"
                )

    def generate_test_report(self):
        """Generate a test report."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["passed"])

        print("\n" + "="*50)
        print("TEST REPORT")
        print("="*50)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print("\nDetailed Results:")
        print("-"*50)

        for result in self.test_results:
            status = "✅" if result["passed"] else "❌"
            print(f"{status} {result['test']}: {result['details']}")

        # Save report to file
        report_path = Path("test_report.json")
        with open(report_path, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total": total_tests,
                    "passed": passed_tests,
                    "failed": total_tests - passed_tests,
                    "success_rate": (passed_tests/total_tests)*100
                },
                "results": self.test_results
            }, f, indent=2)

        print(f"\nReport saved to: {report_path.absolute()}")

    async def run_all_tests(self):
        """Run all tests."""
        self.log("Starting full-stack tests for EduSched...")

        # Test 1: Backend health
        if not self.test_backend_health():
            self.log("Backend is not running. Please start the backend server first.", "ERROR")
            return

        # Test 2: Create schedule
        schedule_data = self.test_create_schedule()
        schedule_id = schedule_data.get("id")

        if schedule_id:
            # Test 3: Get schedule
            self.test_get_schedule(schedule_id)

            # Test 4: List schedules
            self.test_list_schedules()

            # Test 5: Export schedule
            self.test_schedule_export(schedule_id)
        else:
            self.log("Failed to create schedule. Skipping dependent tests.", "WARNING")

        # Test 6: WebSocket
        await self.test_websocket()

        # Generate report
        self.generate_test_report()


def main():
    """Main entry point."""
    print("EduSched Full-Stack Test Suite")
    print("="*50)

    # Check if backend is running
    config = TestConfig()

    # Create and run tester
    tester = FullStackTester(config)

    # Run async tests
    asyncio.run(tester.run_all_tests())


if __name__ == "__main__":
    main()