import time
from typing import Optional, Dict, Any
import redis.asyncio as aioredis
from app.config import settings

redis_client: Optional[aioredis.Redis] = None


async def init_redis() -> aioredis.Redis:
    """Initialize the Redis connection pool."""
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=3.0,
            socket_connect_timeout=3.0,
        )
    return redis_client


async def close_redis() -> None:
    """Close the Redis connection pool gracefully."""
    global redis_client
    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None


async def check_redis_connection() -> Dict[str, Any]:
    """Check connectivity and latency to the Redis instance."""
    start_time = time.perf_counter()
    try:
        client = await init_redis()
        pong = await client.ping()
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        if pong:
            return {
                "status": "healthy",
                "latency_ms": latency_ms,
            }
        return {
            "status": "unhealthy",
            "latency_ms": latency_ms,
            "error": "Redis did not reply with PONG",
        }
    except Exception as e:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "status": "unhealthy",
            "latency_ms": latency_ms,
            "error": str(e),
        }
