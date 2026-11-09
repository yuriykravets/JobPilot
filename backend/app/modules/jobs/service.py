import uuid
from typing import List, Tuple, Optional
from sqlalchemy import select, func, or_, and_, cast, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs.models import Job
from app.modules.jobs.schemas import JobCreateSchema, JobFilterParams, JobRegion
from app.modules.jobs.seed_data import SEED_JOBS
from app.modules.matching.embeddings import build_job_embedding_text, generate_embedding

# Canonical dictionary for consistent skill token casing
CANONICAL_SKILL_NAMES = {
    "kotlin": "Kotlin",
    "android": "Android SDK",
    "compose": "Jetpack Compose",
    "jetpack compose": "Jetpack Compose",
    "coroutines": "Coroutines",
    "flow": "Flow",
    "python": "Python",
    "fastapi": "FastAPI",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "pgvector": "pgvector",
    "redis": "Redis",
    "docker": "Docker",
    "langchain": "LangChain",
    "langgraph": "LangGraph",
    "langfuse": "Langfuse",
    "kmp": "KMP",
    "mvi": "MVI",
    "clean architecture": "Clean Architecture",
    "room": "Room",
    "hilt": "Hilt",
    "ci/cd": "CI/CD",
    "aws": "AWS",
    "gcp": "GCP",
    "kubernetes": "Kubernetes",
    "rag": "RAG",
    "embeddings": "Embeddings",
}


def normalize_skill(skill: str) -> str:
    """Normalizes a skill string to its canonical capitalization."""
    clean = skill.strip()
    return CANONICAL_SKILL_NAMES.get(clean.lower(), clean)


def normalize_skills_list(skills: List[str]) -> List[str]:
    """Cleans, normalizes, and deduplicates a list of skill tokens."""
    seen = set()
    normalized = []
    for s in skills:
        if not s or not s.strip():
            continue
        canon = normalize_skill(s)
        if canon.lower() not in seen:
            seen.add(canon.lower())
            normalized.append(canon)
    return normalized


async def upsert_job(job_in: JobCreateSchema, db: AsyncSession) -> Job:
    """
    Idempotently creates or updates a job posting based on external_id.
    Prevents duplicate entries when re-ingesting feeds or seed data.
    """
    norm_required = normalize_skills_list(job_in.required_skills)
    norm_preferred = normalize_skills_list(job_in.preferred_skills)

    existing_job: Optional[Job] = None
    if job_in.external_id:
        stmt = select(Job).where(Job.external_id == job_in.external_id)
        result = await db.execute(stmt)
        existing_job = result.scalar_one_or_none()

    # Build semantic text for embedding
    embedding_text = build_job_embedding_text(
        title=job_in.title,
        company=job_in.company_name,
        location=job_in.location,
        required_skills=norm_required,
        preferred_skills=norm_preferred,
        description=job_in.raw_description,
    )
    job_embedding = await generate_embedding(embedding_text)

    if existing_job:
        existing_job.title = job_in.title
        existing_job.company_name = job_in.company_name
        existing_job.location = job_in.location
        existing_job.region = job_in.region.value
        existing_job.raw_description = job_in.raw_description
        existing_job.required_skills = norm_required
        existing_job.preferred_skills = norm_preferred
        existing_job.min_experience_years = job_in.min_experience_years
        existing_job.salary_min = job_in.salary_min
        existing_job.salary_max = job_in.salary_max
        existing_job.salary_currency = job_in.salary_currency
        existing_job.source_url = job_in.source_url
        if job_embedding:
            existing_job.embedding = job_embedding
        await db.commit()
        await db.refresh(existing_job)
        return existing_job
    else:
        new_job = Job(
            external_id=job_in.external_id or f"job-{uuid.uuid4().hex[:12]}",
            title=job_in.title,
            company_name=job_in.company_name,
            location=job_in.location,
            region=job_in.region.value,
            raw_description=job_in.raw_description,
            required_skills=norm_required,
            preferred_skills=norm_preferred,
            min_experience_years=job_in.min_experience_years,
            salary_min=job_in.salary_min,
            salary_max=job_in.salary_max,
            salary_currency=job_in.salary_currency,
            source_url=job_in.source_url,
            embedding=job_embedding,
        )
        db.add(new_job)
        await db.commit()
        await db.refresh(new_job)
        return new_job


async def backfill_jobs_embeddings(db: AsyncSession, limit: int = 100) -> int:
    """
    Generates and stores 768-dim embeddings for all jobs currently lacking one.
    """
    stmt = select(Job).where(Job.embedding.is_(None)).limit(limit)
    result = await db.execute(stmt)
    jobs_to_embed = list(result.scalars().all())

    count = 0
    for job in jobs_to_embed:
        embed_text = build_job_embedding_text(
            title=job.title,
            company=job.company_name,
            location=job.location,
            required_skills=job.required_skills,
            preferred_skills=job.preferred_skills,
            description=job.raw_description,
        )
        vec = await generate_embedding(embed_text)
        if vec:
            job.embedding = vec
            count += 1

    await db.commit()
    return count


async def seed_jobs_catalog(db: AsyncSession) -> int:
    """Ingests the curated multi-region dataset into PostgreSQL."""
    count = 0
    for data in SEED_JOBS:
        schema = JobCreateSchema(**data)
        await upsert_job(schema, db)
        count += 1
    return count


async def get_paginated_jobs(
    filters: JobFilterParams,
    db: AsyncSession,
) -> Tuple[List[Job], int]:
    """
    Queries the jobs catalog with dynamic SQL filters, total count, and pagination.
    """
    conditions = [Job.is_active == True]

    # Filter by Region (UA, EU, US, REMOTE)
    if filters.region:
        conditions.append(Job.region == filters.region.value)

    # Filter by Min Salary
    if filters.min_salary is not None:
        conditions.append(
            or_(
                Job.salary_min >= filters.min_salary,
                Job.salary_max >= filters.min_salary,
            )
        )

    # Search query across title, company, or description
    if filters.search_query and filters.search_query.strip():
        term = f"%{filters.search_query.strip()}%"
        conditions.append(
            or_(
                Job.title.ilike(term),
                Job.company_name.ilike(term),
                Job.raw_description.ilike(term),
            )
        )

    # Filter by specific skill
    if filters.skill and filters.skill.strip():
        skill_term = f"%{filters.skill.strip()}%"
        conditions.append(
            or_(
                cast(Job.required_skills, String).ilike(skill_term),
                cast(Job.preferred_skills, String).ilike(skill_term),
            )
        )

    # Count total matching rows
    count_stmt = select(func.count(Job.id)).where(and_(*conditions))
    total_result = await db.execute(count_stmt)
    total_count = total_result.scalar_one() or 0

    # Fetch paginated slice
    query_stmt = (
        select(Job)
        .where(and_(*conditions))
        .order_by(Job.created_at.desc())
        .limit(filters.limit)
        .offset(filters.offset)
    )
    items_result = await db.execute(query_stmt)
    jobs = list(items_result.scalars().all())

    return jobs, total_count
