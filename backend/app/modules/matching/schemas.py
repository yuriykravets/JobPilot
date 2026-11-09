import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class MatchSkillEvidence(BaseModel):
    """
    Skill possessed by the candidate that matches job requirements.
    Contains verified evidence from CV (e.g. quote or years of experience).
    """
    model_config = ConfigDict(from_attributes=True)

    skill: str = Field(description="Normalized skill name")
    evidence: str = Field(description="Verifiable candidate evidence from CV text")
    is_required: bool = Field(default=True, description="True if job marked as must-have, False if preferred")


class MissingSkillGap(BaseModel):
    """
    Skill required or preferred by the job that was not found in candidate CV.
    """
    model_config = ConfigDict(from_attributes=True)

    skill: str = Field(description="Missing skill name")
    severity: str = Field(description="'required' (high impact) or 'preferred' (medium impact)")
    suggestion: Optional[str] = Field(default=None, description="Suggested action to bridge or address this gap")


class ExperienceAnalysis(BaseModel):
    """
    Deterministic comparison of candidate total years vs minimum job requirements.
    """
    model_config = ConfigDict(from_attributes=True)

    candidate_years: float = Field(description="Candidate verified professional experience")
    required_years: float = Field(description="Job minimum required years")
    meets_requirement: bool = Field(description="Whether candidate meets or exceeds minimum requirement")
    delta_years: float = Field(description="Surplus (+) or deficit (-) in years")


class MatchWeights(BaseModel):
    """
    Configurable weights used to synthesize the overall match score.
    Must sum to 1.0.
    """
    deterministic: float = Field(default=0.35, description="Weight for exact skills & experience thresholds (35%)")
    semantic: float = Field(default=0.35, description="Weight for vector cosine similarity (35%)")
    llm_reasoning: float = Field(default=0.30, description="Weight for LLM qualitative judge (30%)")


class LlmJudgeEvaluationSchema(BaseModel):
    """
    Structured Pydantic schema requested from Azure OpenAI or Google Gemini.
    """
    reasoning_score: float = Field(
        ge=0.0,
        le=100.0,
        description="Holistic fit score from 0.0 to 100.0 considering context, project depth, and role alignment",
    )
    strengths: List[str] = Field(
        description="Key competitive advantages of this candidate for the specific vacancy",
    )
    gaps: List[str] = Field(
        description="Identified risks, technology mismatches, or domain gaps",
    )
    recommendations: str = Field(
        description="Tactical advice for the candidate to tailor their CV or prepare for the interview",
    )


class JobMatchScorecard(BaseModel):
    """
    Complete explainable match breakdown across all 3 tiers.
    """
    model_config = ConfigDict(from_attributes=True)

    overall_score: float = Field(ge=0.0, le=100.0, description="Weighted composite score (0-100)")
    deterministic_score: float = Field(ge=0.0, le=100.0, description="Tier 1: Exact skill & experience score")
    semantic_score: float = Field(ge=0.0, le=100.0, description="Tier 2: pgvector cosine similarity score")
    llm_reasoning_score: float = Field(ge=0.0, le=100.0, description="Tier 3: LLM reasoning fit score")

    weights: MatchWeights = Field(default_factory=MatchWeights)
    matching_skills: List[MatchSkillEvidence] = Field(default_factory=list)
    missing_skills: List[MissingSkillGap] = Field(default_factory=list)
    experience_analysis: ExperienceAnalysis
    recommendations: str
    llm_provider: Optional[str] = Field(default=None, description="Provider used ('azure', 'gemini', or 'fallback')")


class MatchCalculateRequest(BaseModel):
    """
    Request payload to evaluate a CV profile against a Job vacancy.
    """
    cv_profile_id: uuid.UUID = Field(description="UUID of the parsed candidate CV profile")
    job_id: uuid.UUID = Field(description="UUID of the job vacancy")
    save_to_db: bool = Field(default=True, description="Whether to persist the result in job_matches table")
    provider: Optional[str] = Field(
        default=None,
        description="Optional provider override ('azure' or 'gemini') for testing and learning",
    )


class JobMatchResponse(BaseModel):
    """
    Full response representing a computed job match.
    """
    model_config = ConfigDict(from_attributes=True)

    id: Optional[uuid.UUID] = Field(default=None, description="Match record ID if saved to DB")
    cv_profile_id: uuid.UUID
    job_id: uuid.UUID

    job_title: Optional[str] = None
    company_name: Optional[str] = None
    location: Optional[str] = None
    region: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = "USD"

    scorecard: JobMatchScorecard
    created_at: Optional[datetime] = None


class CandidateRankedMatchesResponse(BaseModel):
    """
    Ranked list of job matches for a given candidate.
    """
    model_config = ConfigDict(from_attributes=True)

    cv_profile_id: uuid.UUID
    total_jobs_evaluated: int
    matches: List[JobMatchResponse]
