import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch
from app.main import app


@pytest.mark.asyncio
async def test_root_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "JobPilot"
        assert data["status"] == "online"


@pytest.mark.asyncio
async def test_health_endpoint_healthy():
    with patch(
        "app.main.check_db_connection",
        return_value={"status": "healthy", "latency_ms": 2.5, "pgvector_installed": True},
    ), patch(
        "app.main.check_redis_connection",
        return_value={"status": "healthy", "latency_ms": 1.2},
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["services"]["database"]["status"] == "healthy"
            assert data["services"]["redis"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_endpoint_degraded():
    with patch(
        "app.main.check_db_connection",
        return_value={"status": "unhealthy", "error": "Connection refused"},
    ), patch(
        "app.main.check_redis_connection",
        return_value={"status": "healthy", "latency_ms": 1.0},
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health")
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "degraded"
            assert data["services"]["database"]["status"] == "unhealthy"
