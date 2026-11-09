import time
from typing import AsyncGenerator, Dict, Any
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy import text
from app.config import settings

# Create async engine with connection pooling
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Automatically tests connections before using them
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async database session per request.
    Rolls back automatically if an unhandled exception occurs.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection() -> Dict[str, Any]:
    """
    Verifies that the database and pgvector extension are available.
    Returns status, latency in milliseconds, and pgvector version.
    """
    start_time = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            # Check basic query execution
            result = await session.execute(text("SELECT 1"))
            result.scalar()

            # Check if pgvector extension is installed
            vector_check = await session.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            )
            pgvector_version = vector_check.scalar()

            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "status": "healthy",
                "latency_ms": latency_ms,
                "pgvector_installed": pgvector_version is not None,
                "pgvector_version": pgvector_version or "not installed",
            }
    except Exception as e:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "status": "unhealthy",
            "latency_ms": latency_ms,
            "error": str(e),
        }
