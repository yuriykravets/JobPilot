import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.jobs.models import Job
from app.modules.jobs.schemas import (
    JobCreateSchema,
    JobFilterParams,
    JobRegion,
    JobResponse,
    PaginatedJobsResponse,
)
from app.modules.jobs.service import (
    upsert_job,
    seed_jobs_catalog,
    get_paginated_jobs,
    backfill_jobs_embeddings,
)
from app.modules.jobs.feed_ingester import sync_all_live_feeds

router = APIRouter(prefix="/jobs", tags=["Job Discovery"])


@router.get(
    "",
    response_model=PaginatedJobsResponse,
    summary="Search and filter vacancies",
    description="Paginated job search supporting regional filtering (UA, EU, US, REMOTE), salary minimums, skill matching, and keyword search.",
)
async def list_jobs(
    region: Optional[JobRegion] = Query(None, description="Filter by region (UA, EU, US, REMOTE)"),
    search: Optional[str] = Query(None, description="Search keyword in title, company, or description"),
    skill: Optional[str] = Query(None, description="Filter jobs requiring or preferring a specific skill"),
    min_salary: Optional[int] = Query(None, description="Minimum compensation"),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
):
    filters = JobFilterParams(
        region=region,
        search_query=search,
        skill=skill,
        min_salary=min_salary,
        limit=limit,
        offset=offset,
    )
    jobs, total = await get_paginated_jobs(filters, db)
    
    return PaginatedJobsResponse(
        items=[JobResponse.model_validate(j) for j in jobs],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(jobs)) < total,
    )


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job vacancy details by ID",
)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Job).where(Job.id == job_id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found.",
        )
    return JobResponse.model_validate(job)


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a new job vacancy",
    description="Idempotently creates or updates a job posting using its external_id.",
)
async def create_job(
    job_in: JobCreateSchema,
    db: AsyncSession = Depends(get_db),
):
    job = await upsert_job(job_in, db)
    return JobResponse.model_validate(job)


@router.post(
    "/seed",
    status_code=status.HTTP_200_OK,
    summary="Seed catalog with multi-region realistic vacancies",
    description="Populates the database with curated real-world vacancies across Ukraine (UA), Europe (EU), and USA (US).",
)
async def seed_jobs(
    db: AsyncSession = Depends(get_db),
):
    count = await seed_jobs_catalog(db)
    return {
        "status": "success",
        "seeded_count": count,
        "message": f"Successfully ingested {count} vacancies across UA, EU, and US regions.",
    }


@router.post(
    "/sync-live-feeds",
    status_code=status.HTTP_200_OK,
    summary="Synchronize live job feeds from Ukraine (DOU.ua) and Global (Remotive)",
    description="Fetches live developer postings from Ukraine (DOU.ua) and international boards (Remotive), upserting them into PostgreSQL.",
)
async def sync_live_feeds(
    db: AsyncSession = Depends(get_db),
):
    result = await sync_all_live_feeds(db)
    return result


@router.post(
    "/generate-embeddings",
    status_code=status.HTTP_200_OK,
    summary="Generate 768-dim embeddings for all jobs lacking vectors",
    description="Backfills semantic embeddings using Gemini text-embedding-004 so all vacancies can be indexed with HNSW.",
)
async def generate_embeddings_endpoint(
    limit: int = Query(50, ge=1, le=200, description="Max jobs to process in this batch"),
    db: AsyncSession = Depends(get_db),
):
    count = await backfill_jobs_embeddings(db, limit=limit)
    return {
        "status": "success",
        "embedded_jobs_count": count,
        "message": f"Successfully generated and saved embeddings for {count} jobs.",
    }
