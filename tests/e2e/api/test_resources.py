"""E2E tests for resource API endpoints."""

import pytest
import httpx
from typing import Dict, Any

pytestmark = pytest.mark.api


class TestResourceAPI:
    """Test suite for resource API endpoints."""

    @pytest.mark.asyncio
    async def test_create_resource(self, authenticated_client: httpx.AsyncClient, sample_resource_data):
        """TC-API-RES-001: Test creating a new resource."""
        response = await authenticated_client.post("/api/v1/resources", json=sample_resource_data)
        assert response.status_code == 201

        data = response.json()
        assert "id" in data
        assert data["name"] == sample_resource_data["name"]
        assert data["type"] == sample_resource_data["type"]
        assert data["capacity"] == sample_resource_data["capacity"]

        return data["id"]

    @pytest.mark.asyncio
    async def test_get_resource(self, authenticated_client: httpx.AsyncClient, sample_resource_data):
        """Test retrieving a specific resource."""
        # Create a resource first
        create_response = await authenticated_client.post("/api/v1/resources", json=sample_resource_data)
        resource_id = create_response.json()["id"]

        # Retrieve it
        response = await authenticated_client.get(f"/api/v1/resources/{resource_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == resource_id
        assert data["name"] == sample_resource_data["name"]
        assert "availability" in data
        assert "attributes" in data

    @pytest.mark.asyncio
    async def test_list_resources(self, authenticated_client: httpx.AsyncClient):
        """Test listing all resources."""
        response = await authenticated_client.get("/api/v1/resources")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_update_resource(self, authenticated_client: httpx.AsyncClient, sample_resource_data):
        """Test updating a resource."""
        # Create a resource first
        create_response = await authenticated_client.post("/api/v1/resources", json=sample_resource_data)
        resource_id = create_response.json()["id"]

        # Update it
        update_data = {
            "name": "Updated Room 101",
            "capacity": 40
        }
        response = await authenticated_client.put(f"/api/v1/resources/{resource_id}", json=update_data)
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Updated Room 101"
        assert data["capacity"] == 40

    @pytest.mark.asyncio
    async def test_delete_resource(self, authenticated_client: httpx.AsyncClient, sample_resource_data):
        """Test deleting a resource."""
        # Create a resource first
        create_response = await authenticated_client.post("/api/v1/resources", json=sample_resource_data)
        resource_id = create_response.json()["id"]

        # Delete it
        response = await authenticated_client.delete(f"/api/v1/resources/{resource_id}")
        assert response.status_code == 200

        # Verify it's deleted
        response = await authenticated_client.get(f"/api/v1/resources/{resource_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_resource_availability(self, authenticated_client: httpx.AsyncClient, sample_resource_data):
        """Test getting resource availability for a date range."""
        # Create a resource first
        create_response = await authenticated_client.post("/api/v1/resources", json=sample_resource_data)
        resource_id = create_response.json()["id"]

        # Get availability
        response = await authenticated_client.get(
            f"/api/v1/resources/{resource_id}/availability",
            params={
                "start_date": "2024-01-01",
                "end_date": "2024-01-07"
            }
        )
        assert response.status_code == 200

        data = response.json()
        assert "availability" in data
        assert isinstance(data["availability"], dict)

    @pytest.mark.asyncio
    async def test_get_resource_utilization(self, authenticated_client: httpx.AsyncClient):
        """Test getting resource utilization metrics."""
        response = await authenticated_client.get("/api/v1/resources/utilization")
        assert response.status_code == 200

        data = response.json()
        assert "resources" in data
        assert isinstance(data["resources"], list)

    @pytest.mark.asyncio
    async def test_bulk_import_resources(self, authenticated_client: httpx.AsyncClient):
        """TC-API-RES-002: Test bulk importing resources."""
        # This would require multipart form data with a file
        # For now, test that the endpoint exists and returns appropriate response
        response = await authenticated_client.post("/api/v1/resources/bulk-import")
        # Expecting 400 since no file provided
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_resource_validation(self, authenticated_client: httpx.AsyncClient):
        """Test resource data validation."""
        # Test invalid resource data
        invalid_data = {
            "name": "",  # Empty name
            "capacity": -1,  # Negative capacity
            "type": "invalid_type"  # Invalid type
        }

        response = await authenticated_client.post("/api/v1/resources", json=invalid_data)
        assert response.status_code == 422

        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_resource_types_filtering(self, authenticated_client: httpx.AsyncClient):
        """Test filtering resources by type."""
        # Test filtering by classroom type
        response = await authenticated_client.get("/api/v1/resources?type=classroom")
        assert response.status_code == 200

        data = response.json()
        if data:  # If there are resources
            for resource in data:
                assert resource["type"] == "classroom"

    @pytest.mark.asyncio
    async def test_resource_capacity_filtering(self, authenticated_client: httpx.AsyncClient):
        """Test filtering resources by capacity."""
        # Test filtering by minimum capacity
        response = await authenticated_client.get("/api/v1/resources?min_capacity=30")
        assert response.status_code == 200

        data = response.json()
        if data:  # If there are resources
            for resource in data:
                assert resource["capacity"] >= 30