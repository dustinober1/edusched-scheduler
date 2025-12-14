"""E2E tests for schedule API endpoints."""

import pytest
import httpx
from datetime import datetime

pytestmark = pytest.mark.api


class TestScheduleAPI:
    """Test suite for schedule API endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, api_client: httpx.AsyncClient):
        """TC-API-HC-001: Test basic health check endpoint."""
        response = await api_client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    @pytest.mark.asyncio
    async def test_root_endpoint(self, api_client: httpx.AsyncClient):
        """TC-API-HC-002: Test root endpoint provides API information."""
        response = await api_client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "EduSched API"
        assert "docs" in data
        assert data["health"] == "/health"

    @pytest.mark.asyncio
    async def test_create_schedule(self, authenticated_client: httpx.AsyncClient, sample_schedule_data):
        """TC-API-SCH-001: Test creating a new schedule."""
        response = await authenticated_client.post("/api/v1/schedules", json=sample_schedule_data)
        assert response.status_code == 201

        data = response.json()
        assert "id" in data
        assert data["status"] in ["success", "no_solution"]
        assert data["total_assignments"] >= 0
        assert "solver_time_ms" in data
        assert "assignments" in data

        return data["id"]

    @pytest.mark.asyncio
    async def test_get_schedule(self, authenticated_client: httpx.AsyncClient, sample_schedule_data):
        """TC-API-SCH-002: Test retrieving a specific schedule."""
        # First create a schedule
        create_response = await authenticated_client.post("/api/v1/schedules", json=sample_schedule_data)
        schedule_id = create_response.json()["id"]

        # Then retrieve it
        response = await authenticated_client.get(f"/api/v1/schedules/{schedule_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == schedule_id
        assert data["name"] == sample_schedule_data["name"]
        assert "created_at" in data
        assert "updated_at" in data
        assert "assignments" in data

    @pytest.mark.asyncio
    async def test_get_nonexistent_schedule(self, authenticated_client: httpx.AsyncClient):
        """Test retrieving a non-existent schedule returns 404."""
        fake_id = "non-existent-id"
        response = await authenticated_client.get(f"/api/v1/schedules/{fake_id}")
        assert response.status_code == 404

        data = response.json()
        assert data["detail"] == "Schedule not found"

    @pytest.mark.asyncio
    async def test_list_schedules(self, authenticated_client: httpx.AsyncClient):
        """TC-API-SCH-003: Test listing schedules with pagination."""
        # Test basic listing
        response = await authenticated_client.get("/api/v1/schedules")
        assert response.status_code == 200

        data = response.json()
        assert "schedules" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        assert isinstance(data["schedules"], list)

        # Test pagination
        response = await authenticated_client.get("/api/v1/schedules?limit=5&skip=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["schedules"]) <= 5

        # Test search
        response = await authenticated_client.get("/api/v1/schedules?search=test")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_schedule(self, authenticated_client: httpx.AsyncClient, sample_schedule_data):
        """TC-API-SCH-004: Test updating schedule properties."""
        # Create a schedule first
        create_response = await authenticated_client.post("/api/v1/schedules", json=sample_schedule_data)
        schedule_id = create_response.json()["id"]

        # Update the schedule
        update_data = {
            "name": "Updated Schedule Name",
            "status": "published"
        }
        response = await authenticated_client.put(f"/api/v1/schedules/{schedule_id}", params=update_data)
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Updated Schedule Name"
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_delete_schedule(self, authenticated_client: httpx.AsyncClient, sample_schedule_data):
        """TC-API-SCH-005: Test deleting a schedule."""
        # Create a schedule first
        create_response = await authenticated_client.post("/api/v1/schedules", json=sample_schedule_data)
        schedule_id = create_response.json()["id"]

        # Delete the schedule
        response = await authenticated_client.delete(f"/api/v1/schedules/{schedule_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "Schedule deleted successfully"

        # Verify it's deleted
        response = await authenticated_client.get(f"/api/v1/schedules/{schedule_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_duplicate_schedule(self, authenticated_client: httpx.AsyncClient, sample_schedule_data):
        """TC-API-SCH-006: Test duplicating an existing schedule."""
        # Create a schedule first
        create_response = await authenticated_client.post("/api/v1/schedules", json=sample_schedule_data)
        original_id = create_response.json()["id"]

        # Duplicate it
        response = await authenticated_client.post(f"/api/v1/schedules/{original_id}/duplicate",
                                                  params={"name": "Duplicated Schedule"})
        assert response.status_code == 201

        data = response.json()
        assert data["id"] != original_id
        assert data["name"] == "Duplicated Schedule"
        assert data["duplicated_from"] == original_id

    @pytest.mark.asyncio
    async def test_export_schedule_json(self, authenticated_client: httpx.AsyncClient, sample_schedule_data):
        """TC-API-SCH-007: Test exporting schedule in JSON format."""
        # Create a schedule first
        create_response = await authenticated_client.post("/api/v1/schedules", json=sample_schedule_data)
        schedule_id = create_response.json()["id"]

        # Export as JSON
        response = await authenticated_client.get(f"/api/v1/schedules/{schedule_id}/export?format=json")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    @pytest.mark.asyncio
    async def test_export_schedule_csv(self, authenticated_client: httpx.AsyncClient, sample_schedule_data):
        """TC-API-SCH-007: Test exporting schedule in CSV format."""
        # Create a schedule first
        create_response = await authenticated_client.post("/api/v1/schedules", json=sample_schedule_data)
        schedule_id = create_response.json()["id"]

        # Export as CSV
        response = await authenticated_client.get(f"/api/v1/schedules/{schedule_id}/export?format=csv")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv"

    @pytest.mark.asyncio
    async def test_export_schedule_unsupported_format(self, authenticated_client: httpx.AsyncClient, sample_schedule_data):
        """Test exporting schedule in unsupported format returns error."""
        # Create a schedule first
        create_response = await authenticated_client.post("/api/v1/schedules", json=sample_schedule_data)
        schedule_id = create_response.json()["id"]

        # Try unsupported format
        response = await authenticated_client.get(f"/api/v1/schedules/{schedule_id}/export?format=unsupported")
        assert response.status_code == 400
        assert "Unsupported format" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_schedule_stats(self, authenticated_client: httpx.AsyncClient):
        """TC-API-SCH-008: Test getting schedule statistics."""
        response = await authenticated_client.get("/api/v1/schedules/stats/overview")
        assert response.status_code == 200

        data = response.json()
        assert "total_schedules" in data
        assert "total_assignments" in data
        assert "avg_assignments_per_schedule" in data
        assert "avg_solver_time_ms" in data
        assert "status_distribution" in data
        assert "last_updated" in data

    @pytest.mark.asyncio
    async def test_get_export_formats(self, api_client: httpx.AsyncClient):
        """TC-API-SCH-009: Test getting supported export formats."""
        response = await api_client.get("/api/v1/schedules/formats/supported")
        assert response.status_code == 200

        data = response.json()
        assert "formats" in data
        assert "extensions" in data
        assert isinstance(data["formats"], list)
        assert isinstance(data["extensions"], dict)

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, api_client: httpx.AsyncClient, sample_schedule_data):
        """Test that unauthorized requests are rejected."""
        # Try to create schedule without auth
        response = await api_client.post("/api/v1/schedules", json=sample_schedule_data)
        assert response.status_code == 401

        # Try to access protected endpoint without auth
        response = await api_client.get("/api/v1/schedules")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_schedule_access_control(self, api_client: httpx.AsyncClient):
        """Test that users can only access their own schedules."""
        # Login as user1 and create schedule
        user1_client = httpx.AsyncClient(base_url=api_client.base_url)
        await user1_client.post("/auth/login", json={"username": "user1", "password": "password1"})

        # Login as user2
        user2_client = httpx.AsyncClient(base_url=api_client.base_url)
        await user2_client.post("/auth/login", json={"username": "user2", "password": "password2"})

        # Create schedule as user1
        response = await user1_client.post("/api/v1/schedules", json={"name": "User1 Schedule"})
        schedule_id = response.json()["id"]

        # Try to access as user2
        response = await user2_client.get(f"/api/v1/schedules/{schedule_id}")
        assert response.status_code == 403

        await user1_client.aclose()
        await user2_client.aclose()