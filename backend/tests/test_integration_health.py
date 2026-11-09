import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import check_db_connection
from app.core.redis import check_redis_connection


@pytest.mark.asyncio
async def test_live_postgres_connection():
    result = await check_db_connection()
    assert result["status"] == "healthy"
    assert result["pgvector_installed"] is True
    assert result["pgvector_version"] != "not installed"
    assert result["latency_ms"] < 200  # Local latency should be well under 200ms


@pytest.mark.asyncio
async def test_live_redis_connection():
    result = await check_redis_connection()
    assert result["status"] == "healthy"
    assert result["latency_ms"] < 200


@pytest.mark.asyncio
async def test_live_health_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["services"]["database"]["status"] == "healthy"
        assert data["services"]["database"]["pgvector_installed"] is True
        assert data["services"]["redis"]["status"] == "healthy"
