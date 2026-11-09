from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core import models  # Ensures all SQLAlchemy mappers are loaded in registry
from app.core.database import engine, check_db_connection
from app.core.redis import init_redis, close_redis, check_redis_connection
from app.modules.cv_processing.router import router as cv_router
from app.modules.jobs.router import router as jobs_router
from app.modules.matching.router import router as matching_router
from app.modules.interviews.router import router as interviews_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.
    Handles startup and shutdown events cleanly.
    """
    # Startup: Initialize Redis pool
    try:
        await init_redis()
    except Exception as e:
        print(f"[Startup Warning] Could not connect to Redis: {e}")

    yield

    # Shutdown: Close connections
    await close_redis()
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    description="Production-quality AI-powered job search and interview platform",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(cv_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(matching_router, prefix="/api/v1")
app.include_router(interviews_router, prefix="/api/v1")


@app.get("/", tags=["General"])
async def root():
    return {
        "service": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "status": "online",
        "documentation": "/docs",
    }


@app.get("/health", tags=["Monitoring"])
async def health_check():
    """
    Comprehensive system health check:
    - Tests PostgreSQL connectivity and pgvector extension status
    - Tests Redis connectivity
    """
    db_status = await check_db_connection()
    redis_status = await check_redis_connection()

    is_healthy = (
        db_status.get("status") == "healthy"
        and redis_status.get("status") == "healthy"
    )

    response_payload = {
        "status": "healthy" if is_healthy else "degraded",
        "environment": settings.ENVIRONMENT,
        "services": {
            "database": db_status,
            "redis": redis_status,
        },
    }

    status_code = (
        status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return JSONResponse(status_code=status_code, content=response_payload)
