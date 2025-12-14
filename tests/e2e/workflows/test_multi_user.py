"""E2E tests for multi-user collaboration scenarios."""

import pytest
import httpx
import asyncio
from datetime import datetime

pytestmark = [pytest.mark.api, pytest.mark.integration]


class TestMultiUserCollaboration:
    """Test multi-user collaboration features."""

    @pytest.mark.asyncio
    async def test_concurrent_editing(self):
        """TC-WF-MU-001: Test simultaneous schedule modifications."""
        # Create two authenticated clients for different users
        user1_client = httpx.AsyncClient(base_url="http://localhost:8000")
        user2_client = httpx.AsyncClient(base_url="http://localhost:8000")

        # Login as user1
        await user1_client.post("/auth/login", json={
            "username": "scheduler1",
            "password": "password123"
        })

        # Login as user2
        await user2_client.post("/auth/login", json={
            "username": "scheduler2",
            "password": "password123"
        })

        # User 1 creates a schedule
        schedule_data = {
            "name": "Collaboration Test Schedule",
            "solver": "heuristic"
        }

        response = await user1_client.post("/api/v1/schedules", json=schedule_data)
        assert response.status_code == 201
        schedule_id = response.json()["id"]

        # User 1 opens schedule for editing
        response = await user1_client.post(f"/api/v1/schedules/{schedule_id}/lock")
        assert response.status_code == 200
        lock_token_1 = response.json()["lock_token"]

        # User 2 attempts to edit the same schedule
        response = await user2_client.post(f"/api/v1/schedules/{schedule_id}/lock")
        assert response.status_code == 409  # Conflict - schedule is locked

        # User 1 makes changes
        update_data = {
            "name": "Updated by User 1",
            "metadata": {"last_editor": "user1"}
        }

        response = await user1_client.put(
            f"/api/v1/schedules/{schedule_id}",
            json=update_data,
            headers={"X-Lock-Token": lock_token_1}
        )
        assert response.status_code == 200

        # User 1 releases the lock
        response = await user1_client.delete(
            f"/api/v1/schedules/{schedule_id}/lock",
            headers={"X-Lock-Token": lock_token_1}
        )
        assert response.status_code == 200

        # Now User 2 can edit
        response = await user2_client.post(f"/api/v1/schedules/{schedule_id}/lock")
        assert response.status_code == 200
        lock_token_2 = response.json()["lock_token"]

        # User 2 makes different changes
        update_data_2 = {
            "status": "in_review",
            "metadata": {"last_editor": "user2"}
        }

        response = await user2_client.put(
            f"/api/v1/schedules/{schedule_id}",
            json=update_data_2,
            headers={"X-Lock-Token": lock_token_2}
        )
        assert response.status_code == 200

        # Verify final state contains both changes
        response = await user1_client.get(f"/api/v1/schedules/{schedule_id}")
        schedule = response.json()
        assert schedule["name"] == "Updated by User 1"
        assert schedule["status"] == "in_review"

        await user1_client.aclose()
        await user2_client.aclose()

    @pytest.mark.asyncio
    async def test_permission_management(self):
        """TC-WF-MU-002: Test role-based access control."""
        # Create clients for different roles
        admin_client = httpx.AsyncClient(base_url="http://localhost:8000")
        scheduler_client = httpx.AsyncClient(base_url="http://localhost:8000")
        teacher_client = httpx.AsyncClient(base_url="http://localhost:8000")
        student_client = httpx.AsyncClient(base_url="http://localhost:8000")

        # Login with different roles
        await admin_client.post("/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        await scheduler_client.post("/auth/login", json={
            "username": "scheduler",
            "password": "sched123"
        })
        await teacher_client.post("/auth/login", json={
            "username": "teacher1",
            "password": "teach123"
        })
        await student_client.post("/auth/login", json={
            "username": "student1",
            "password": "stud123"
        })

        # Test administrator permissions
        response = await admin_client.get("/api/v1/users")
        assert response.status_code == 200  # Can view all users

        response = await admin_client.post("/api/v1/system/settings", json={
            "max_schedules_per_user": 10
        })
        assert response.status_code == 200  # Can modify system settings

        # Test scheduler permissions
        response = await scheduler_client.post("/api/v1/schedules", json={
            "name": "Scheduler Test",
            "solver": "heuristic"
        })
        assert response.status_code == 201  # Can create schedules

        response = await scheduler_client.get("/api/v1/schedules")
        assert response.status_code == 200  # Can view all schedules

        # Test teacher permissions
        response = await teacher_client.get("/api/v1/assignments/teacher")
        assert response.status_code == 200  # Can view own assignments

        response = await teacher_client.post("/api/v1/schedules", json={
            "name": "Teacher Schedule"
        })
        assert response.status_code == 403  # Cannot create schedules

        # Test student permissions
        response = await student_client.get("/api/v1/schedules/student")
        assert response.status_code == 200  # Can view own schedule

        response = await student_client.get("/api/v1/schedules")
        assert response.status_code == 403  # Cannot view all schedules

        # Test audit trail
        response = await admin_client.get("/api/v1/audit/trail")
        assert response.status_code == 200
        audit_log = response.json()
        assert len(audit_log) > 0
        # Verify actions are logged with user and timestamp
        for entry in audit_log[:5]:  # Check first 5 entries
            assert "user_id" in entry
            assert "action" in entry
            assert "timestamp" in entry

        # Close clients
        await admin_client.aclose()
        await scheduler_client.aclose()
        await teacher_client.aclose()
        await student_client.aclose()

    @pytest.mark.asyncio
    async def test_real_time_collaboration(self):
        """Test real-time collaboration via WebSocket."""
        import websockets
        import json

        # Create WebSocket connections for two users
        uri_1 = "ws://localhost:8000/ws?user_id=user1&schedule_id=collab-schedule"
        uri_2 = "ws://localhost:8000/ws?user_id=user2&schedule_id=collab-schedule"

        async with websockets.connect(uri_1) as ws1, websockets.connect(uri_2) as ws2:
            # User 1 joins the session
            await ws1.send(json.dumps({
                "type": "join",
                "schedule_id": "collab-schedule"
            }))

            # User 2 joins the session
            await ws2.send(json.dumps({
                "type": "join",
                "schedule_id": "collab-schedule"
            }))

            # Verify both users receive join notification
            msg1 = await ws1.recv()
            msg2 = await ws2.recv()

            data1 = json.loads(msg1)
            data2 = json.loads(msg2)

            assert data1["type"] == "user_joined"
            assert data2["type"] == "user_joined"

            # User 1 makes a change
            change_data = {
                "type": "assignment_update",
                "assignment_id": "assign-123",
                "changes": {
                    "start_time": "10:00",
                    "resource_id": "room-456"
                }
            }

            await ws1.send(json.dumps(change_data))

            # User 2 should receive the change
            msg2 = await ws2.recv()
            data2 = json.loads(msg2)
            assert data2["type"] == "assignment_updated"
            assert data2["assignment_id"] == "assign-123"

            # User 2 adds a comment
            comment_data = {
                "type": "comment",
                "text": "Are we sure about this room change?",
                "assignment_id": "assign-123"
            }

            await ws2.send(json.dumps(comment_data))

            # User 1 should receive the comment
            msg1 = await ws1.recv()
            data1 = json.loads(msg1)
            assert data1["type"] == "comment_added"
            assert data1["text"] == comment_data["text"]

    @pytest.mark.asyncio
    async def test_conflict_resolution(self):
        """Test conflict resolution when multiple users edit simultaneously."""
        # Two users trying to modify the same assignment
        client1 = httpx.AsyncClient(base_url="http://localhost:8000")
        client2 = httpx.AsyncClient(base_url="http://localhost:8000")

        # Login both users
        await client1.post("/auth/login", json={"username": "user1", "password": "pass1"})
        await client2.post("/auth/login", json={"username": "user2", "password": "pass2" })

        # Both users get the schedule
        schedule_id = "test-schedule-123"

        response = await client1.get(f"/api/v1/schedules/{schedule_id}")
        schedule1 = response.json()
        version1 = schedule1["version"]

        response = await client2.get(f"/api/v1/schedules/{schedule_id}")
        schedule2 = response.json()
        version2 = schedule2["version"]

        assert version1 == version2  # Both have same version

        # User 1 makes a change
        update1 = {
            "version": version1,
            "changes": {
                "assignments": {
                    "assign-1": {"room": "room-101"}
                }
            }
        }

        response = await client1.patch(f"/api/v1/schedules/{schedule_id}", json=update1)
        assert response.status_code == 200
        updated_schedule = response.json()
        new_version = updated_schedule["version"]

        # User 2 tries to make a different change based on old version
        update2 = {
            "version": version2,  # Old version!
            "changes": {
                "assignments": {
                    "assign-1": {"room": "room-102"}
                }
            }
        }

        response = await client2.patch(f"/api/v1/schedules/{schedule_id}", json=update2)
        assert response.status_code == 409  # Conflict!

        conflict_response = response.json()
        assert conflict_response["type"] == "version_conflict"
        assert "current_version" in conflict_response
        assert "conflicting_changes" in conflict_response

        # User 2 can now merge changes
        merge_data = {
            "version": conflict_response["current_version"],
            "changes": {
                "assignments": {
                    "assign-2": {"room": "room-103"}
                }
            },
            "resolution": "merge"
        }

        response = await client2.patch(f"/api/v1/schedules/{schedule_id}", json=merge_data)
        assert response.status_code == 200

        await client1.aclose()
        await client2.aclose()