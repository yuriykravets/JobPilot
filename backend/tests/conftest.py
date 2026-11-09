import pytest
from app.core.database import engine
from app.core.redis import close_redis


@pytest.fixture(autouse=True)
async def cleanup_connections():
    """
    Ensure connection pools are disposed between test event loops.
    Prevents 'Event loop is closed' errors in asyncpg/SQLAlchemy.
    """
    yield
    await engine.dispose()
    await close_redis()
