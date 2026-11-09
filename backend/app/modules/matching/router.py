import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.cv_processing.models import CvProfile
from app.modules.jobs.models import Job
from app.modules.matching.models import JobMatch
from app.modules.matching.schemas import (
    MatchCalculateRequest,
    JobMatchResponse,
    JobMatchScorecard,
    MatchSkillEvidence,
    MissingSkillGap,
    ExperienceAnalysis,
    MatchWeights,
    CandidateRankedMatchesResponse,
)
from app.modules.matching.service import (
    evaluate_and_save_match,
    get_ranked_matches_for_candidate,
)

router = APIRouter(prefix="/matching", tags=["Hybrid Match Scoring"])


@router.post(
    "/calculate",
    response_model=JobMatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate 3-tier match score between a candidate CV and a Job vacancy",
    description=(
        "Executes Tier 1 (Deterministic skills & experience check), "
        "Tier 2 (Vector cosine similarity), and "
        "Tier 3 (LLM Reasoning Judge via Azure OpenAI or Gemini) to generate an explainable scorecard."
    ),
)
async def calculate_match(
    request: MatchCalculateRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        response = await evaluate_and_save_match(
            cv_profile_id=request.cv_profile_id,
            job_id=request.job_id,
            db=db,
            save_to_db=request.save_to_db,
            provider_override=request.provider,
        )
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate match score: {str(e)}",
        )


@router.get(
    "/candidate/{user_id}/jobs",
    response_model=CandidateRankedMatchesResponse,
    summary="Get ranked job recommendations for candidate",
    description="Evaluates active vacancies against the candidate's CV profile and ranks them by overall match score.",
)
async def get_candidate_job_matches(
    user_id: uuid.UUID,
    limit: int = Query(10, ge=1, le=50, description="Max number of matches to return"),
    region: Optional[str] = Query(None, description="Optional region filter: UA, EU, US, REMOTE"),
    provider: Optional[str] = Query(None, description="Optional provider override: azure or gemini"),
    db: AsyncSession = Depends(get_db),
):
    # Lookup CV profile by user_id
    stmt = select(CvProfile).where(CvProfile.user_id == user_id)
    res = await db.execute(stmt)
    cv_profile = res.scalar_one_or_none()

    if not cv_profile:
        # Fallback: check if the passed UUID is actually a CvProfile.id
        cv_stmt2 = select(CvProfile).where(CvProfile.id == user_id)
        cv_res2 = await db.execute(cv_stmt2)
        cv_profile = cv_res2.scalar_one_or_none()

    if not cv_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No CV profile found for user or profile ID '{user_id}'. Please upload a CV first.",
        )

    try:
        ranked_response = await get_ranked_matches_for_candidate(
            cv_profile_id=cv_profile.id,
            db=db,
            limit=limit,
            region=region,
            provider_override=provider,
        )
        return ranked_response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rank job matches: {str(e)}",
        )


@router.get(
    "/{match_id}",
    response_model=JobMatchResponse,
    summary="Retrieve previously calculated match scorecard",
)
async def get_match_by_id(
    match_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(JobMatch, Job, CvProfile)
        .join(Job, JobMatch.job_id == Job.id)
        .join(CvProfile, JobMatch.cv_profile_id == CvProfile.id)
        .where(JobMatch.id == match_id)
    )
    res = await db.execute(stmt)
    row = res.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match record with ID '{match_id}' not found.",
        )

    match_record, job, cv_profile = row

    # Parse JSON fields into typed models
    matching_skills = [MatchSkillEvidence.model_validate(m) for m in (match_record.matching_skills or [])]
    missing_skills = [MissingSkillGap.model_validate(m) for m in (match_record.missing_skills or [])]

    candidate_years = float(cv_profile.years_of_experience or 0.0)
    required_years = float(job.min_experience_years or 0.0)

    exp_analysis = ExperienceAnalysis(
        candidate_years=candidate_years,
        required_years=required_years,
        meets_requirement=candidate_years >= required_years,
        delta_years=round(candidate_years - required_years, 1),
    )

    scorecard = JobMatchScorecard(
        overall_score=float(match_record.overall_score),
        deterministic_score=float(match_record.deterministic_score),
        semantic_score=float(match_record.semantic_score),
        llm_reasoning_score=float(match_record.llm_reasoning_score),
        weights=MatchWeights(deterministic=0.35, semantic=0.35, llm_reasoning=0.30),
        matching_skills=matching_skills,
        missing_skills=missing_skills,
        experience_analysis=exp_analysis,
        recommendations=match_record.recommendations,
        llm_provider=None,
    )

    return JobMatchResponse(
        id=match_record.id,
        cv_profile_id=match_record.cv_profile_id,
        job_id=match_record.job_id,
        job_title=job.title,
        company_name=job.company_name,
        location=job.location,
        region=job.region,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        salary_currency=job.salary_currency,
        scorecard=scorecard,
        created_at=match_record.created_at,
    )
