"""E2E tests for constraint API endpoints."""

import pytest
import httpx

pytestmark = pytest.mark.api


class TestConstraintAPI:
    """Test suite for constraint API endpoints."""

    @pytest.mark.asyncio
    async def test_create_constraint(self, authenticated_client: httpx.AsyncClient):
        """TC-API-CON-001: Test creating a new constraint."""
        constraint_data = {
            "name": "No Monday Classes",
            "type": "time_window",
            "parameters": {
                "days": ["monday"],
                "blackout": True
            },
            "enabled": True
        }

        response = await authenticated_client.post("/api/v1/constraints", json=constraint_data)
        assert response.status_code == 201

        data = response.json()
        assert "id" in data
        assert data["name"] == constraint_data["name"]
        assert data["type"] == constraint_data["type"]
        assert data["enabled"] == constraint_data["enabled"]

        return data["id"]

    @pytest.mark.asyncio
    async def test_get_constraint(self, authenticated_client: httpx.AsyncClient):
        """Test retrieving a specific constraint."""
        # Create a constraint first
        constraint_data = {
            "name": "Room Capacity Limit",
            "type": "capacity",
            "parameters": {
                "max_capacity": 50,
                "resource_types": ["classroom"]
            }
        }

        create_response = await authenticated_client.post("/api/v1/constraints", json=constraint_data)
        constraint_id = create_response.json()["id"]

        # Retrieve it
        response = await authenticated_client.get(f"/api/v1/constraints/{constraint_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == constraint_id
        assert data["name"] == constraint_data["name"]
        assert "parameters" in data

    @pytest.mark.asyncio
    async def test_list_constraints(self, authenticated_client: httpx.AsyncClient):
        """Test listing all constraints."""
        response = await authenticated_client.get("/api/v1/constraints")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_update_constraint(self, authenticated_client: httpx.AsyncClient):
        """Test updating a constraint."""
        # Create a constraint first
        constraint_data = {
            "name": "Teacher Availability",
            "type": "teacher_time",
            "parameters": {
                "teacher_id": "teacher1",
                "max_hours_per_day": 6
            }
        }

        create_response = await authenticated_client.post("/api/v1/constraints", json=constraint_data)
        constraint_id = create_response.json()["id"]

        # Update it
        update_data = {
            "name": "Updated Teacher Availability",
            "enabled": False
        }
        response = await authenticated_client.put(f"/api/v1/constraints/{constraint_id}", json=update_data)
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Updated Teacher Availability"
        assert data["enabled"] == False

    @pytest.mark.asyncio
    async def test_delete_constraint(self, authenticated_client: httpx.AsyncClient):
        """Test deleting a constraint."""
        # Create a constraint first
        constraint_data = {
            "name": "Equipment Requirement",
            "type": "resource_feature",
            "parameters": {
                "feature": "projector",
                "required": True
            }
        }

        create_response = await authenticated_client.post("/api/v1/constraints", json=constraint_data)
        constraint_id = create_response.json()["id"]

        # Delete it
        response = await authenticated_client.delete(f"/api/v1/constraints/{constraint_id}")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_toggle_constraint(self, authenticated_client: httpx.AsyncClient):
        """TC-API-CON-003: Test toggling constraint enabled status."""
        # Create a constraint first
        constraint_data = {
            "name": "Test Constraint",
            "type": "custom",
            "parameters": {},
            "enabled": True
        }

        create_response = await authenticated_client.post("/api/v1/constraints", json=constraint_data)
        constraint_id = create_response.json()["id"]

        # Toggle it off
        response = await authenticated_client.post(f"/api/v1/constraints/{constraint_id}/toggle")
        assert response.status_code == 200

        data = response.json()
        assert data["enabled"] == False

        # Toggle it back on
        response = await authenticated_client.post(f"/api/v1/constraints/{constraint_id}/toggle")
        assert response.status_code == 200

        data = response.json()
        assert data["enabled"] == True

    @pytest.mark.asyncio
    async def test_validate_constraints(self, authenticated_client: httpx.AsyncClient):
        """TC-API-CON-002: Test constraint validation."""
        # Create valid and invalid constraints
        constraints = [
            {
                "type": "time_window",
                "parameters": {
                    "start": "09:00",
                    "end": "17:00",
                    "days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
                }
            },
            {
                "type": "time_window",
                "parameters": {
                    "start": "17:00",  # Start after end - invalid
                    "end": "09:00",
                    "days": []
                }
            }
        ]

        response = await authenticated_client.post("/api/v1/constraints/validate", json={"constraints": constraints})
        assert response.status_code == 200

        data = response.json()
        assert "valid" in data
        assert "errors" in data
        assert len(data["errors"]) > 0  # Should have errors for invalid constraint

    @pytest.mark.asyncio
    async def test_get_constraint_templates(self, authenticated_client: httpx.AsyncClient):
        """Test getting constraint templates."""
        response = await authenticated_client.get("/api/v1/constraints/templates")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        if data:  # If templates exist
            for template in data:
                assert "name" in template
                assert "type" in template
                assert "description" in template

    @pytest.mark.asyncio
    async def test_constraint_types(self, authenticated_client: httpx.AsyncClient):
        """Test creating different types of constraints."""
        constraint_types = [
            {
                "type": "time_window",
                "parameters": {
                    "start": "09:00",
                    "end": "17:00"
                }
            },
            {
                "type": "capacity",
                "parameters": {
                    "max_capacity": 100
                }
            },
            {
                "type": "resource_feature",
                "parameters": {
                    "feature": "projector",
                    "required": True
                }
            },
            {
                "type": "teacher_time",
                "parameters": {
                    "max_consecutive_hours": 3
                }
            }
        ]

        for constraint_data in constraint_types:
            constraint_data["name"] = f"Test {constraint_data['type']}"
            response = await authenticated_client.post("/api/v1/constraints", json=constraint_data)
            assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_constraint_validation_errors(self, authenticated_client: httpx.AsyncClient):
        """Test constraint validation with invalid data."""
        invalid_constraints = [
            {
                "name": "",
                "type": "invalid_type",
                "parameters": None
            },
            {
                "name": "Valid name",
                "type": "time_window",
                "parameters": {
                    "start": "invalid_time"
                }
            }
        ]

        for constraint_data in invalid_constraints:
            response = await authenticated_client.post("/api/v1/constraints", json=constraint_data)
            assert response.status_code == 422

            data = response.json()
            assert "detail" in data

    @pytest.mark.asyncio
    async def test_constraint_priority(self, authenticated_client: httpx.AsyncClient):
        """Test constraint priority ordering."""
        # Create constraints with different priorities
        constraints = []
        for priority in [1, 2, 3]:
            constraint_data = {
                "name": f"Priority {priority} Constraint",
                "type": "custom",
                "parameters": {},
                "priority": priority
            }
            response = await authenticated_client.post("/api/v1/constraints", json=constraint_data)
            constraints.append(response.json())

        # Verify constraints are returned ordered by priority
        response = await authenticated_client.get("/api/v1/constraints?sort=priority")
        assert response.status_code == 200

        data = response.json()
        priorities = [c.get("priority", 0) for c in data]
        assert priorities == sorted(priorities)