"""Pytest configuration for E2E tests."""

import os
import pytest
import asyncio
from typing import AsyncGenerator
import httpx
from pathlib import Path

# Test configuration
TEST_API_URL = os.getenv("TEST_API_URL", "http://localhost:8000")
TEST_FRONTEND_URL = os.getenv("TEST_FRONTEND_URL", "http://localhost:3000")
TEST_DB_URL = os.getenv("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/edusched_test")

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def api_client() -> httpx.AsyncClient:
    """Create an HTTP client for API testing."""
    async with httpx.AsyncClient(base_url=TEST_API_URL, timeout=30.0) as client:
        yield client

@pytest.fixture
async def auth_token(api_client: httpx.AsyncClient) -> str:
    """Get authentication token for testing."""
    # Login with test credentials
    response = await api_client.post("/auth/login", json={
        "username": "test_user",
        "password": "test_password"
    })
    response.raise_for_status()
    data = response.json()
    return data["access_token"]

@pytest.fixture
async def authenticated_client(api_client: httpx.AsyncClient, auth_token: str) -> httpx.AsyncClient:
    """Create an authenticated API client."""
    api_client.headers["Authorization"] = f"Bearer {auth_token}"
    yield api_client
    # Clean up header
    del api_client.headers["Authorization"]

@pytest.fixture
async def sample_schedule_data():
    """Sample schedule data for testing."""
    return {
        "name": "Test Schedule 2024",
        "solver": "heuristic",
        "optimize": True,
        "seed": 12345,
        "constraints": [
            {
                "type": "time_window",
                "start": "09:00",
                "end": "17:00",
                "days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
            }
        ]
    }

@pytest.fixture
async def sample_resource_data():
    """Sample resource data for testing."""
    return {
        "name": "Room 101",
        "type": "classroom",
        "capacity": 30,
        "building_id": "building-a",
        "attributes": {
            "has_projector": True,
            "has_whiteboard": True,
            "has_computers": False
        },
        "availability": {
            "monday": [["09:00", "17:00"]],
            "tuesday": [["09:00", "17:00"]],
            "wednesday": [["09:00", "17:00"]],
            "thursday": [["09:00", "17:00"]],
            "friday": [["09:00", "17:00"]]
        }
    }

@pytest.fixture
async def cleanup_db():
    """Clean up database after tests."""
    yield
    # Database cleanup logic here
    # This would truncate test tables or reset test data
    pass

@pytest.fixture
def test_data_dir() -> Path:
    """Get the test data directory."""
    return Path(__file__).parent.parent / "test_data"

# Helper functions
async def create_test_schedule(client: httpx.AsyncClient, data: dict) -> dict:
    """Create a test schedule and return its data."""
    response = await client.post("/api/v1/schedules", json=data)
    response.raise_for_status()
    return response.json()

async def create_test_resource(client: httpx.AsyncClient, data: dict) -> dict:
    """Create a test resource and return its data."""
    response = await client.post("/api/v1/resources", json=data)
    response.raise_for_status()
    return response.json()

async def wait_for_websocket_message(ws_url: str, timeout: int = 10) -> dict:
    """Wait for and return a WebSocket message."""
    import websockets
    import json

    async with websockets.connect(ws_url) as websocket:
        try:
            message = await asyncio.wait_for(websocket.recv(), timeout=timeout)
            return json.loads(message)
        except asyncio.TimeoutError:
            raise TimeoutError("No WebSocket message received within timeout")

# Test markers
def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line(
        "markers", "api: mark test as API test"
    )
    config.addinivalue_line(
        "markers", "frontend: mark test as frontend test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )