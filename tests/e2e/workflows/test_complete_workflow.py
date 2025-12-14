"""E2E tests for complete scheduling workflows."""

import pytest
import httpx
import asyncio
from datetime import datetime, timedelta

pytestmark = [pytest.mark.api, pytest.mark.integration]


class TestCompleteWorkflow:
    """Test complete end-to-end scheduling workflows."""

    @pytest.mark.asyncio
    async def test_new_institution_setup(self, authenticated_client: httpx.AsyncClient):
        """TC-WF-001: Test complete system initial setup."""
        # 1. Configure institution settings
        settings_data = {
            "name": "Test University",
            "timezone": "America/New_York",
            "academic_year": "2024-2025",
            "semester": "Fall",
            "start_date": "2024-09-01",
            "end_date": "2024-12-20"
        }

        response = await authenticated_client.post("/api/v1/institution/settings", json=settings_data)
        assert response.status_code == 201

        # 2. Create buildings
        buildings = [
            {"name": "Science Building", "code": "SCI"},
            {"name": "Engineering Building", "code": "ENG"},
            {"name": "Library", "code": "LIB"}
        ]

        building_ids = []
        for building in buildings:
            response = await authenticated_client.post("/api/v1/buildings", json=building)
            assert response.status_code == 201
            building_ids.append(response.json()["id"])

        # 3. Create rooms in each building
        rooms_data = []
        for building_id in building_ids:
            for floor in range(1, 4):  # 3 floors
                for room_num in range(1, 11):  # 10 rooms per floor
                    rooms_data.append({
                        "building_id": building_id,
                        "number": f"{floor}0{room_num}",
                        "type": "classroom",
                        "capacity": 30,
                        "attributes": {
                            "has_projector": True,
                            "has_whiteboard": True
                        }
                    })

        # Bulk import rooms
        response = await authenticated_client.post("/api/v1/resources/bulk-import", json={"resources": rooms_data})
        assert response.status_code == 200

        # 4. Create academic calendar
        calendar_data = {
            "semester": "Fall 2024",
            "start_date": "2024-09-01",
            "end_date": "2024-12-20",
            "holidays": [
                {"date": "2024-09-02", "name": "Labor Day"},
                {"date": "2024-10-14", "name": "Fall Break"},
                {"date": "2024-11-11", "name": "Veterans Day"},
                {"date": "2024-11-28", "name": "Thanksgiving"}
            ],
            "exam_period": {
                "start": "2024-12-16",
                "end": "2024-12-20"
            }
        }

        response = await authenticated_client.post("/api/v1/calendar", json=calendar_data)
        assert response.status_code == 201

        # 5. Create departments
        departments = [
            {"name": "Computer Science", "code": "CS"},
            {"name": "Mathematics", "code": "MATH"},
            {"name": "Physics", "code": "PHYS"},
            {"name": "Chemistry", "code": "CHEM"}
        ]

        department_ids = []
        for dept in departments:
            response = await authenticated_client.post("/api/v1/departments", json=dept)
            assert response.status_code == 201
            department_ids.append(response.json()["id"])

        # Verify setup complete
        response = await authenticated_client.get("/api/v1/institution/status")
        assert response.status_code == 200
        status = response.json()
        assert status["buildings"] == 3
        assert status["rooms"] == 90  # 3 buildings * 3 floors * 10 rooms
        assert status["departments"] == 4
        assert status["calendar_configured"] == True

    @pytest.mark.asyncio
    async def test_semester_scheduling_workflow(self, authenticated_client: httpx.AsyncClient):
        """TC-WF-002: Test complete semester scheduling process."""
        # 1. Create new semester schedule
        schedule_data = {
            "name": "Fall 2024 Schedule",
            "semester": "Fall 2024",
            "solver": "heuristic",
            "optimize": True
        }

        response = await authenticated_client.post("/api/v1/schedules", json=schedule_data)
        assert response.status_code == 201
        schedule_id = response.json()["id"]

        # 2. Import course catalog
        courses_data = [
            {
                "code": "CS101",
                "name": "Introduction to Programming",
                "credits": 3,
                "department": "CS",
                "enrollment": 150,
                "sections": 3,
                "duration_minutes": 75,
                "preferred_days": ["monday", "wednesday", "friday"],
                "requirements": {
                    "room_type": "classroom",
                    "min_capacity": 40,
                    "features": ["projector", "computer_lab"]
                }
            },
            {
                "code": "MATH201",
                "name": "Calculus II",
                "credits": 4,
                "department": "MATH",
                "enrollment": 100,
                "sections": 2,
                "duration_minutes": 90,
                "preferred_days": ["tuesday", "thursday"],
                "requirements": {
                    "room_type": "classroom",
                    "min_capacity": 50,
                    "features": ["projector"]
                }
            }
        ]

        response = await authenticated_client.post(f"/api/v1/schedules/{schedule_id}/courses/bulk-import",
                                                 json={"courses": courses_data})
        assert response.status_code == 200

        # 3. Add faculty and their availability
        faculty_data = [
            {
                "name": "Dr. Smith",
                "department": "CS",
                "max_courses": 3,
                "max_hours_per_day": 4,
                "unavailability": [
                    {"day": "tuesday", "start": "14:00", "end": "16:00"}  # Office hours
                ]
            },
            {
                "name": "Dr. Johnson",
                "department": "MATH",
                "max_courses": 4,
                "max_hours_per_day": 5
            }
        ]

        for faculty in faculty_data:
            response = await authenticated_client.post("/api/v1/faculty", json=faculty)
            assert response.status_code == 201

        # 4. Define constraints
        constraints_data = [
            {
                "type": "time_window",
                "parameters": {
                    "start": "08:00",
                    "end": "18:00",
                    "days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
                },
                "priority": 1
            },
            {
                "type": "no_overlap",
                "parameters": {
                    "resource_types": ["teacher", "room"]
                },
                "priority": 1
            },
            {
                "type": "spread",
                "parameters": {
                    "min_gap_minutes": 60,
                    "apply_to": ["teacher"]
                },
                "priority": 2
            }
        ]

        for constraint in constraints_data:
            response = await authenticated_client.post(f"/api/v1/schedules/{schedule_id}/constraints",
                                                     json=constraint)
            assert response.status_code == 201

        # 5. Run optimization
        optimization_request = {
            "schedule_id": schedule_id,
            "solver": "heuristic",
            "objectives": [
                {"type": "minimize_conflicts", "weight": 1.0},
                {"type": "spread_assignments", "weight": 0.8},
                {"type": "utilize_resources", "weight": 0.6}
            ],
            "time_limit": 300  # 5 minutes
        }

        response = await authenticated_client.post("/api/v1/optimization/run", json=optimization_request)
        assert response.status_code == 202
        job_id = response.json()["job_id"]

        # 6. Monitor optimization progress
        max_attempts = 30  # 30 seconds max wait
        for _ in range(max_attempts):
            response = await authenticated_client.get(f"/api/v1/optimization/status/{job_id}")
            status = response.json()["status"]

            if status in ["completed", "failed"]:
                break

            await asyncio.sleep(1)

        assert status == "completed"

        # 7. Get optimization results
        response = await authenticated_client.get(f"/api/v1/optimization/results/{job_id}")
        assert response.status_code == 200

        results = response.json()
        assert results["total_assignments"] > 0
        assert results["conflicts"] == 0
        assert "solver_time_ms" in results

        # 8. Review generated schedule
        response = await authenticated_client.get(f"/api/v1/schedules/{schedule_id}")
        schedule = response.json()

        assert schedule["total_assignments"] == results["total_assignments"]
        assert schedule["status"] == "success"

        # 9. Make manual adjustments
        # Get an assignment to modify
        response = await authenticated_client.get(f"/api/v1/schedules/{schedule_id}/assignments")
        assignments = response.json()

        if assignments:
            assignment_id = assignments[0]["id"]
            update_data = {
                "start_time": "10:00",
                "end_time": "11:15"  # Change to later time
            }

            response = await authenticated_client.put(
                f"/api/v1/schedules/{schedule_id}/assignments/{assignment_id}",
                json=update_data
            )
            assert response.status_code == 200

        # 10. Finalize schedule
        response = await authenticated_client.put(f"/api/v1/schedules/{schedule_id}",
                                                params={"status": "published"})
        assert response.status_code == 200

        # 11. Publish notifications
        response = await authenticated_client.post(f"/api/v1/schedules/{schedule_id}/notify")
        assert response.status_code == 200

        # Verify final state
        response = await authenticated_client.get(f"/api/v1/schedules/{schedule_id}")
        schedule = response.json()
        assert schedule["status"] == "published"

    @pytest.mark.asyncio
    async def test_schedule_modification_workflow(self, authenticated_client: httpx.AsyncClient):
        """TC-WF-003: Test in-semester schedule changes."""
        # Create and populate a schedule first
        # (This would reuse code from the previous test or use setup fixtures)

        # 1. Load active schedule
        response = await authenticated_client.get("/api/v1/schedules?status=published")
        schedules = response.json()
        assert len(schedules) > 0

        schedule_id = schedules[0]["id"]

        # 2. Handle room change request
        # Get an assignment
        response = await authenticated_client.get(f"/api/v1/schedules/{schedule_id}/assignments")
        assignments = response.json()

        if assignments:
            assignment = assignments[0]
            original_room = assignment["resource_id"]

            # Find available room at same time
            new_room_data = {
                "start_time": assignment["start_time"],
                "end_time": assignment["end_time"],
                "min_capacity": assignment.get("enrollment", 20),
                "features": assignment.get("required_features", [])
            }

            response = await authenticated_client.post("/api/v1/resources/find-available", json=new_room_data)
            available_rooms = response.json()

            if available_rooms:
                new_room = available_rooms[0]["id"]

                # Move assignment to new room
                response = await authenticated_client.post(
                    f"/api/v1/schedules/{schedule_id}/assignments/{assignment['id']}/move",
                    json={"resource_id": new_room}
                )
                assert response.status_code == 200

        # 3. Accommodate new course section
        new_section = {
            "course_code": "CS301-02",
            "name": "Advanced Programming - Section 2",
            "enrollment": 25,
            "duration_minutes": 75,
            "teacher_id": "teacher1",
            "preferred_times": [{"day": "monday", "start": "13:00"}]
        }

        response = await authenticated_client.post(
            f"/api/v1/schedules/{schedule_id}/assignments",
            json=new_section
        )
        assert response.status_code == 201

        # 4. Resolve teacher unavailability
        # Mark teacher unavailable for a specific time
        unavailability = {
            "teacher_id": "teacher2",
            "start": "2024-10-15T09:00:00Z",
            "end": "2024-10-15T12:00:00Z",
            "reason": "Conference"
        }

        response = await authenticated_client.post("/api/v1/faculty/unavailability", json=unavailability)
        assert response.status_code == 201

        # 5. Add special event
        event_data = {
            "name": "Guest Lecture: AI in Education",
            "date": "2024-11-05",
            "start_time": "14:00",
            "end_time": "16:00",
            "room_id": "room-auditorium-001",
            "required_features": ["projector", "microphone"]
        }

        response = await authenticated_client.post(f"/api/v1/schedules/{schedule_id}/events", json=event_data)
        assert response.status_code == 201

        # 6. Check for conflicts after all changes
        response = await authenticated_client.post(f"/api/v1/schedules/{schedule_id}/conflicts/check")
        conflicts = response.json()

        if conflicts["total"] > 0:
            # Resolve conflicts
            for conflict in conflicts["items"]:
                resolution = {
                    "conflict_id": conflict["id"],
                    "action": "reschedule",
                    "new_time": conflict["suggestions"][0]
                }

                response = await authenticated_client.post(
                    f"/api/v1/schedules/{schedule_id}/conflicts/resolve",
                    json=resolution
                )
                assert response.status_code == 200

        # 7. Update notifications
        notification_data = {
            "type": "schedule_update",
            "message": "Schedule has been updated with room changes and new sections",
            "recipients": ["all_students", "all_faculty"]
        }

        response = await authenticated_client.post(f"/api/v1/schedules/{schedule_id}/notifications",
                                                 json=notification_data)
        assert response.status_code == 200

        # 8. Verify no conflicts remain
        response = await authenticated_client.get(f"/api/v1/schedules/{schedule_id}/summary")
        summary = response.json()
        assert summary["conflicts"] == 0