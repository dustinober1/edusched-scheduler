"""E2E tests for edge cases and error handling."""

import pytest
import httpx
import asyncio
from datetime import datetime, timedelta

pytestmark = pytest.mark.api


class TestEdgeCases:
    """Test edge cases and error handling scenarios."""

    @pytest.mark.asyncio
    async def test_intermittent_connection(self):
        """TC-EC-NET-001: Test behavior with intermittent network issues."""
        client = httpx.AsyncClient(base_url="http://localhost:8000", timeout=5.0)

        # Start a long-running operation
        optimization_data = {
            "solver": "advanced",
            "time_limit": 60,  # 1 minute
            "complexity": "high"
        }

        # Start optimization
        response = await client.post("/api/v1/optimization/run", json=optimization_data)
        assert response.status_code == 202
        job_id = response.json()["job_id"]

        # Simulate network drop
        client.close()
        await asyncio.sleep(2)

        # Reconnect and check status
        new_client = httpx.AsyncClient(base_url="http://localhost:8000")
        response = await new_client.get(f"/api/v1/optimization/status/{job_id}")

        # Should still be able to get status
        assert response.status_code == 200
        status = response.json()["status"]
        assert status in ["running", "queued", "completed"]

        await new_client.aclose()

    @pytest.mark.asyncio
    async def test_timeout_scenarios(self):
        """TC-EC-NET-002: Test timeout handling."""
        client = httpx.AsyncClient(base_url="http://localhost:8000", timeout=2.0)

        # Request that takes longer than timeout
        slow_operation_data = {
            "solver": "exhaustive",
            "problem_size": "very_large",
            "time_limit": 300
        }

        try:
            response = await client.post("/api/v1/optimization/run", json=slow_operation_data)
        except httpx.ReadTimeout:
            # Expected - timeout occurred
            pass
        else:
            # If not timeout, it should return quickly with a job ID
            assert response.status_code in [202, 400]

        await client.aclose()

    @pytest.mark.asyncio
    async def test_large_dataset_handling(self, authenticated_client: httpx.AsyncClient):
        """TC-EC-DATA-001: Test with large schedules."""
        # Create schedule with many assignments
        large_schedule_data = {
            "name": "Large Schedule Test",
            "solver": "heuristic",
            "bulk_data": {
                "num_courses": 500,
                "num_rooms": 200,
                "num_teachers": 100
            }
        }

        # Start creation with stream response
        async with authenticated_client.stream(
            "POST",
            "/api/v1/schedules/bulk",
            json=large_schedule_data,
            timeout=300.0
        ) as response:
            assert response.status_code == 200

            # Process streaming response
            chunks = []
            async for chunk in response.aiter_text():
                chunks.append(chunk)
                # Verify progress updates are sent
                if "progress" in chunk:
                    progress_data = response.json()
                    assert "percentage" in progress_data

        # Verify pagination for large data
        response = await authenticated_client.get("/api/v1/schedules/large-schedule/assignments")
        assert response.status_code == 200

        data = response.json()
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert data["total"] > data["page_size"]  # Should have pagination

    @pytest.mark.asyncio
    async def test_invalid_data_states(self, authenticated_client: httpx.AsyncClient):
        """TC-EC-DATA-002: Test with corrupted or invalid data."""
        # Test with impossible time constraints
        invalid_constraint = {
            "type": "time_window",
            "parameters": {
                "start": "17:00",
                "end": "09:00",  # End before start
                "days": []
            }
        }

        response = await authenticated_client.post("/api/v1/constraints", json=invalid_constraint)
        assert response.status_code == 422
        assert "validation" in response.json()["detail"].lower()

        # Test with circular dependencies
        circular_data = {
            "assignments": [
                {
                    "id": "assign-1",
                    "depends_on": ["assign-2"]
                },
                {
                    "id": "assign-2",
                    "depends_on": ["assign-1"]
                }
            ]
        }

        response = await authenticated_client.post("/api/v1/schedules/with-dependencies", json=circular_data)
        assert response.status_code == 400
        assert "circular" in response.json()["detail"].lower()

        # Test with negative values
        invalid_resource = {
            "name": "Room",
            "capacity": -10,  # Negative capacity
            "duration": -60   # Negative duration
        }

        response = await authenticated_client.post("/api/v1/resources", json=invalid_resource)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_resource_exhaustion(self, authenticated_client: httpx.AsyncClient):
        """TC-EC-DATA-003: Test system limits and resource exhaustion."""
        # Test max schedules per user
        schedules_created = []
        max_schedules = 10  # Assuming this is the limit

        for i in range(max_schedules + 1):
            response = await authenticated_client.post("/api/v1/schedules", json={
                "name": f"Schedule {i}"
            })

            if i < max_schedules:
                assert response.status_code == 201
                schedules_created.append(response.json()["id"])
            else:
                # Should hit the limit
                assert response.status_code == 429
                assert "limit" in response.json()["detail"].lower()

        # Clean up
        for schedule_id in schedules_created:
            await authenticated_client.delete(f"/api/v1/schedules/{schedule_id}")

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """TC-EC-CON-001: Test concurrent optimization runs."""
        # Create multiple clients
        clients = [httpx.AsyncClient(base_url="http://localhost:8000") for _ in range(5)]

        # Start multiple optimizations concurrently
        job_ids = []
        for client in clients:
            response = await client.post("/api/v1/optimization/run", json={
                "solver": "heuristic",
                "complexity": "medium"
            })
            assert response.status_code == 202
            job_ids.append(response.json()["job_id"])

        # Verify they're all queued/running
        for job_id in job_ids:
            response = await clients[0].get(f"/api/v1/optimization/status/{job_id}")
            assert response.status_code == 200
            status = response.json()["status"]
            assert status in ["queued", "running", "completed"]

        # Clean up
        for client in clients:
            await client.aclose()

    @pytest.mark.asyncio
    async def test_database_locks(self):
        """TC-EC-CON-002: Test database locking scenarios."""
        # Simulate database lock
        lock_data = {
            "resource": "schedule_table",
            "mode": "exclusive",
            "duration": 10  # seconds
        }

        client = httpx.AsyncClient(base_url="http://localhost:8000")

        # Acquire lock (admin only endpoint)
        await client.post("/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })

        response = await client.post("/api/v1/debug/acquire-lock", json=lock_data)
        assert response.status_code == 200

        # Try to modify schedule while locked
        response = await client.put("/api/v1/schedules/test-schedule", json={
            "name": "Update while locked"
        })

        # Should either queue or return specific error
        assert response.status_code in [202, 423]  # Accepted or Locked

        # Release lock
        await client.post("/api/v1/debug/release-lock", json={"resource": "schedule_table"})

        await client.aclose()

    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(self, authenticated_client: httpx.AsyncClient):
        """Test handling of unicode and special characters."""
        unicode_data = {
            "name": "🎓 Universität Schedule 2024",
            "description": "Testing ñiño, café, 北京, מבחן",
            "courses": [
                {
                    "code": "CS-101-Ñ",
                    "name": "Programming with émojis 💻🚀",
                    "instructor": "Prof. Dr. Müller-Schmidt"
                }
            ]
        }

        response = await authenticated_client.post("/api/v1/schedules", json=unicode_data)
        assert response.status_code == 201

        # Verify data is preserved
        schedule_id = response.json()["id"]
        response = await authenticated_client.get(f"/api/v1/schedules/{schedule_id}")
        schedule = response.json()
        assert "🎓" in schedule["name"]
        assert "ñiño" in schedule["description"]
        assert "💻" in schedule["courses"][0]["name"]

    @pytest.mark.asyncio
    async def test_malformed_requests(self, api_client: httpx.AsyncClient):
        """Test handling of malformed HTTP requests."""
        # Send invalid JSON
        response = await api_client.post(
            "/api/v1/schedules",
            content="{'invalid': json, format}",  # Single quotes are invalid JSON
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

        # Send invalid content type
        response = await api_client.post(
            "/api/v1/schedules",
            content="not json at all",
            headers={"Content-Type": "application/xml"}
        )
        assert response.status_code == 415  # Unsupported Media Type

        # Send huge request
        huge_data = {"data": "x" * 10_000_000}  # 10MB of data
        response = await api_client.post("/api/v1/schedules", json=huge_data)
        assert response.status_code == 413  # Payload Too Large

    @pytest.mark.asyncio
    async def test_memory_limits(self, authenticated_client: httpx.AsyncClient):
        """Test behavior with memory-intensive operations."""
        # Create memory pressure by requesting large exports
        response = await authenticated_client.get(
            "/api/v1/schedules/all/export",
            params={"format": "json", "include_history": True}
        )

        # Should either succeed or fail gracefully
        if response.status_code == 200:
            # If it succeeds, check it's streaming
            assert "transfer-encoding" in response.headers
            assert response.headers["transfer-encoding"] == "chunked"
        else:
            # Should fail with specific error
            assert response.status_code in [429, 503]  # Too Many Requests or Service Unavailable

    @pytest.mark.asyncio
    async def test_graceful_degradation(self, authenticated_client: httpx.AsyncClient):
        """Test graceful degradation when services are unavailable."""
        # Mock service unavailability
        # Note: This would require test infrastructure to disable specific services

        # Test without Redis (if used for caching)
        # Test without database replicas
        # Test without search service

        # For now, test with reduced functionality mode
        response = await authenticated_client.get("/api/v1/status/detailed")
        assert response.status_code == 200

        status = response.json()
        # Should report which services are degraded
        if "services" in status:
            for service, health in status["services"].items():
                if health["status"] == "degraded":
                    assert "reason" in health
                    assert "fallback" in health