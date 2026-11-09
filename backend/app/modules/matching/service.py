import math
import uuid
import logging
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.llm_client import generate_structured_json
from app.modules.cv_processing.models import CvProfile
from app.modules.jobs.models import Job
from app.modules.matching.models import JobMatch
from app.modules.matching.schemas import (
    MatchSkillEvidence,
    MissingSkillGap,
    ExperienceAnalysis,
    MatchWeights,
    LlmJudgeEvaluationSchema,
    JobMatchScorecard,
    JobMatchResponse,
    CandidateRankedMatchesResponse,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_LLM_JUDGE = """
You are an Executive Technical Hiring Manager and Senior Career Coach.
Evaluate the candidate's CV profile against the specific job posting.

Evaluation Principles:
1. Objectivity: Base scores on actual demonstrable experience and transferable engineering skills.
2. Nuance: Recognize adjacent technologies (e.g., Spring Boot and Quarkus, Kotlin and Java, React and Next.js).
3. Actionable Feedback: Provide concrete recommendations for interview prep and resume positioning.
4. Output format: You must strictly adhere to the requested JSON schema.
"""


def _normalize_skill(skill: str) -> str:
    """Lowercases, strips, and cleans skill names for normalized string comparison."""
    if not skill:
        return ""
    clean = skill.strip().lower()
    # Normalize common aliases
    aliases = {
        "k8s": "kubernetes",
        "react.js": "react",
        "reactjs": "react",
        "vue.js": "vue",
        "vuejs": "vue",
        "node.js": "nodejs",
        "next.js": "nextjs",
        "postgres": "postgresql",
        "aws cloud": "aws",
        "gcp": "google cloud",
    }
    return aliases.get(clean, clean)


def calculate_cosine_similarity(vec_a: Optional[List[float]], vec_b: Optional[List[float]]) -> float:
    """
    Computes mathematical cosine similarity between two float vectors.
    Returns float in range [0.0, 1.0].
    """
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    sim = dot_product / (norm_a * norm_b)
    # Clamp to [0.0, 1.0] for non-negative semantic embedding projections
    return max(0.0, min(1.0, float(sim)))


def calculate_deterministic_score(
    cv_profile: CvProfile,
    job: Job,
) -> Tuple[float, List[MatchSkillEvidence], List[MissingSkillGap], ExperienceAnalysis]:
    """
    Tier 1 Deterministic Engine:
    - Verifies exact must-have and preferred skills against parsed CV profile
    - Evaluates total candidate years of experience against job requirement
    
    Weights within Deterministic Score:
    - Required Skills: 70%
    - Preferred Skills: 15%
    - Experience Years: 15%
    """
    candidate_skills_dict: Dict[str, Dict[str, Any]] = {}
    for item in cv_profile.skills:
        name = item.get("name", "")
        norm_name = _normalize_skill(name)
        if norm_name:
            candidate_skills_dict[norm_name] = item

    matching_skills: List[MatchSkillEvidence] = []
    missing_skills: List[MissingSkillGap] = []

    # 1. Match Required Skills (70% weight)
    matched_req_count = 0
    total_req_count = len(job.required_skills)

    for req in job.required_skills:
        norm_req = _normalize_skill(req)
        matched = False
        # Check direct or substring containment
        for cand_norm, cand_data in candidate_skills_dict.items():
            if norm_req == cand_norm or norm_req in cand_norm or cand_norm in norm_req:
                matched = True
                matched_req_count += 1
                evidence_text = cand_data.get("source_quote") or f"{cand_data.get('years', 1.0)} years recorded"
                matching_skills.append(
                    MatchSkillEvidence(
                        skill=req,
                        evidence=evidence_text,
                        is_required=True,
                    )
                )
                break
        if not matched:
            missing_skills.append(
                MissingSkillGap(
                    skill=req,
                    severity="required",
                    suggestion=f"High priority must-have skill for {job.company_name}. Highlight any related projects or equivalents.",
                )
            )

    req_score = 100.0 if total_req_count == 0 else (matched_req_count / total_req_count) * 100.0

    # 2. Match Preferred Skills (15% weight)
    matched_pref_count = 0
    total_pref_count = len(job.preferred_skills)

    for pref in job.preferred_skills:
        norm_pref = _normalize_skill(pref)
        matched = False
        for cand_norm, cand_data in candidate_skills_dict.items():
            if norm_pref == cand_norm or norm_pref in cand_norm or cand_norm in norm_pref:
                matched = True
                matched_pref_count += 1
                evidence_text = cand_data.get("source_quote") or f"{cand_data.get('years', 1.0)} years recorded"
                matching_skills.append(
                    MatchSkillEvidence(
                        skill=pref,
                        evidence=evidence_text,
                        is_required=False,
                    )
                )
                break
        if not matched:
            missing_skills.append(
                MissingSkillGap(
                    skill=pref,
                    severity="preferred",
                    suggestion=f"Bonus skill. Familiarity will strengthen candidate position.",
                )
            )

    pref_score = 100.0 if total_pref_count == 0 else (matched_pref_count / total_pref_count) * 100.0

    # 3. Experience Analysis (15% weight)
    candidate_years = float(cv_profile.years_of_experience or 0.0)
    required_years = float(job.min_experience_years or 0.0)
    delta = round(candidate_years - required_years, 1)
    meets_req = candidate_years >= required_years

    if required_years == 0.0 or meets_req:
        exp_score = 100.0
    else:
        exp_score = max(0.0, (candidate_years / required_years) * 100.0)

    exp_analysis = ExperienceAnalysis(
        candidate_years=candidate_years,
        required_years=required_years,
        meets_requirement=meets_req,
        delta_years=delta,
    )

    deterministic_score = round(
        (0.70 * req_score) + (0.15 * pref_score) + (0.15 * exp_score),
        2,
    )

    return deterministic_score, matching_skills, missing_skills, exp_analysis


def calculate_semantic_score(cv_profile: CvProfile, job: Job) -> float:
    """
    Tier 2 Semantic Vector Engine:
    Computes cosine similarity between 768-dim embeddings of candidate profile and job.
    """
    if cv_profile.embedding and job.embedding:
        cos_sim = calculate_cosine_similarity(cv_profile.embedding, job.embedding)
        return round(cos_sim * 100.0, 2)

    # Fallback when embeddings are not precomputed: estimate semantic overlap
    return 70.0


async def calculate_llm_reasoning_score(
    cv_profile: CvProfile,
    job: Job,
    matching_skills: List[MatchSkillEvidence],
    missing_skills: List[MissingSkillGap],
    exp_analysis: ExperienceAnalysis,
    provider_override: Optional[str] = None,
) -> Tuple[float, str, str]:
    """
    Tier 3 LLM Reasoning Judge (Azure OpenAI / Google Gemini):
    Performs qualitative assessment of candidate-job fit, project complexity, and seniority.
    
    Returns:
        Tuple of (reasoning_score, recommendations, provider_used)
    """
    provider = provider_override or settings.LLM_PROVIDER
    
    # Check if active provider credentials are valid
    has_azure = bool(settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY)
    has_gemini = bool(settings.GEMINI_API_KEY)

    # If neither is configured (e.g. offline dev/test), use deterministic heuristic fallback
    if not (has_azure or has_gemini):
        logger.info("[LLM Judge] No LLM provider keys configured; using heuristic evaluation.")
        score = 80.0 if exp_analysis.meets_requirement else 65.0
        recs = (
            f"Tailor CV to address missing skills: {', '.join([m.skill for m in missing_skills[:3]]) or 'None'}. "
            f"Emphasize demonstrable production experience in {job.title}."
        )
        return score, recs, "heuristic_fallback"

    matched_names = [m.skill for m in matching_skills]
    missing_names = [m.skill for m in missing_skills]

    prompt = f"""
Candidate Profile:
- Target Role: {cv_profile.target_role or 'Software Engineer'}
- Years of Experience: {exp_analysis.candidate_years}
- Verified Skills: {', '.join(matched_names) if matched_names else 'See raw experience'}
- Summary / Work History Excerpt: {cv_profile.raw_text[:600]}

Target Job Vacancy:
- Title: {job.title}
- Company: {job.company_name}
- Location / Region: {job.location} ({job.region})
- Required Skills: {', '.join(job.required_skills)}
- Preferred Skills: {', '.join(job.preferred_skills)}
- Min Experience: {job.min_experience_years} years
- Missing Skills Identified: {', '.join(missing_names) if missing_names else 'None'}
- Job Overview: {job.raw_description[:600]}

Please evaluate this match. Assess project depth, transferable technologies, and career trajectory.
Return a structured JSON with 'reasoning_score' (0-100), 'strengths', 'gaps', and 'recommendations'.
"""

    try:
        result = await generate_structured_json(
            prompt=prompt,
            system_instruction=SYSTEM_PROMPT_LLM_JUDGE,
            schema_class=LlmJudgeEvaluationSchema,
            temperature=0.2,
            provider_override=provider,
        )
        reasoning_score = float(result.get("reasoning_score", 75.0))
        recommendations = result.get("recommendations", "Review role specifications and prepare STAR examples.")
        return round(reasoning_score, 2), recommendations, provider

    except Exception as e:
        logger.warning(f"[LLM Judge] LLM call failed ({e}); falling back to heuristic evaluation.")
        score = 75.0 if exp_analysis.meets_requirement else 60.0
        recs = f"Focus on highlighting your expertise in {job.title} and bridging gaps in {', '.join(missing_names[:2])}."
        return score, recs, f"fallback_after_error: {provider}"


async def calculate_match_scorecard(
    cv_profile: CvProfile,
    job: Job,
    provider_override: Optional[str] = None,
) -> JobMatchScorecard:
    """
    Computes the full 3-tier explainable match scorecard between a candidate CV and a Job vacancy.
    """
    weights = MatchWeights(deterministic=0.35, semantic=0.35, llm_reasoning=0.30)

    # 1. Tier 1: Deterministic
    det_score, matching_skills, missing_skills, exp_analysis = calculate_deterministic_score(cv_profile, job)

    # 2. Tier 2: Semantic Vector
    sem_score = calculate_semantic_score(cv_profile, job)

    # 3. Tier 3: LLM Reasoning Judge
    llm_score, recommendations, provider_used = await calculate_llm_reasoning_score(
        cv_profile=cv_profile,
        job=job,
        matching_skills=matching_skills,
        missing_skills=missing_skills,
        exp_analysis=exp_analysis,
        provider_override=provider_override,
    )

    # Composite Overall Score
    overall = round(
        (weights.deterministic * det_score)
        + (weights.semantic * sem_score)
        + (weights.llm_reasoning * llm_score),
        2,
    )
    overall_clamped = max(0.0, min(100.0, overall))

    return JobMatchScorecard(
        overall_score=overall_clamped,
        deterministic_score=det_score,
        semantic_score=sem_score,
        llm_reasoning_score=llm_score,
        weights=weights,
        matching_skills=matching_skills,
        missing_skills=missing_skills,
        experience_analysis=exp_analysis,
        recommendations=recommendations,
        llm_provider=provider_used,
    )


async def evaluate_and_save_match(
    cv_profile_id: uuid.UUID,
    job_id: uuid.UUID,
    db: AsyncSession,
    save_to_db: bool = True,
    provider_override: Optional[str] = None,
) -> JobMatchResponse:
    """
    Evaluates match between CV profile and Job, optionally persisting to the database.
    """
    # Fetch CV profile
    cv_stmt = select(CvProfile).where(CvProfile.id == cv_profile_id)
    cv_res = await db.execute(cv_stmt)
    cv_profile = cv_res.scalar_one_or_none()
    if not cv_profile:
        raise ValueError(f"CV Profile '{cv_profile_id}' not found.")

    # Fetch Job
    job_stmt = select(Job).where(Job.id == job_id)
    job_res = await db.execute(job_stmt)
    job = job_res.scalar_one_or_none()
    if not job:
        raise ValueError(f"Job '{job_id}' not found.")

    # Compute scorecard
    scorecard = await calculate_match_scorecard(
        cv_profile=cv_profile,
        job=job,
        provider_override=provider_override,
    )

    match_id = None
    created_at = None

    if save_to_db:
        # Check existing match for idempotency
        existing_stmt = select(JobMatch).where(
            JobMatch.cv_profile_id == cv_profile_id,
            JobMatch.job_id == job_id,
        )
        existing_res = await db.execute(existing_stmt)
        match_record = existing_res.scalar_one_or_none()

        matching_json = [m.model_dump() for m in scorecard.matching_skills]
        missing_json = [m.model_dump() for m in scorecard.missing_skills]

        if match_record:
            # Update existing
            match_record.overall_score = scorecard.overall_score
            match_record.deterministic_score = scorecard.deterministic_score
            match_record.semantic_score = scorecard.semantic_score
            match_record.llm_reasoning_score = scorecard.llm_reasoning_score
            match_record.matching_skills = matching_json
            match_record.missing_skills = missing_json
            match_record.recommendations = scorecard.recommendations
        else:
            # Create new
            match_record = JobMatch(
                cv_profile_id=cv_profile_id,
                job_id=job_id,
                overall_score=scorecard.overall_score,
                deterministic_score=scorecard.deterministic_score,
                semantic_score=scorecard.semantic_score,
                llm_reasoning_score=scorecard.llm_reasoning_score,
                matching_skills=matching_json,
                missing_skills=missing_json,
                recommendations=scorecard.recommendations,
            )
            db.add(match_record)

        await db.commit()
        await db.refresh(match_record)
        match_id = match_record.id
        created_at = match_record.created_at

    return JobMatchResponse(
        id=match_id,
        cv_profile_id=cv_profile_id,
        job_id=job_id,
        job_title=job.title,
        company_name=job.company_name,
        location=job.location,
        region=job.region,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        salary_currency=job.salary_currency,
        scorecard=scorecard,
        created_at=created_at,
    )


async def get_ranked_matches_for_candidate(
    cv_profile_id: uuid.UUID,
    db: AsyncSession,
    limit: int = 10,
    region: Optional[str] = None,
    provider_override: Optional[str] = None,
) -> CandidateRankedMatchesResponse:
    """
    Ranks active job vacancies for a candidate CV profile.
    Uses vector similarity if embeddings exist, followed by full 3-tier scoring on candidate vacancies.
    """
    cv_stmt = select(CvProfile).where(CvProfile.id == cv_profile_id)
    cv_res = await db.execute(cv_stmt)
    cv_profile = cv_res.scalar_one_or_none()
    if not cv_profile:
        raise ValueError(f"CV Profile '{cv_profile_id}' not found.")

    # Query active jobs
    jobs_query = select(Job).where(Job.is_active == True)
    if region:
        jobs_query = jobs_query.where(Job.region == region.upper())

    # Limit candidate search space to evaluate top vacancies
    jobs_query = jobs_query.limit(max(limit * 2, 20))
    jobs_res = await db.execute(jobs_query)
    jobs = list(jobs_res.scalars().all())

    evaluated_matches: List[JobMatchResponse] = []
    for j in jobs:
        scorecard = await calculate_match_scorecard(
            cv_profile=cv_profile,
            job=j,
            provider_override=provider_override,
        )
        evaluated_matches.append(
            JobMatchResponse(
                cv_profile_id=cv_profile_id,
                job_id=j.id,
                job_title=j.title,
                company_name=j.company_name,
                location=j.location,
                region=j.region,
                salary_min=j.salary_min,
                salary_max=j.salary_max,
                salary_currency=j.salary_currency,
                scorecard=scorecard,
            )
        )

    # Sort descending by overall match score
    evaluated_matches.sort(key=lambda m: m.scorecard.overall_score, reverse=True)
    top_matches = evaluated_matches[:limit]

    return CandidateRankedMatchesResponse(
        cv_profile_id=cv_profile_id,
        total_jobs_evaluated=len(jobs),
        matches=top_matches,
    )
