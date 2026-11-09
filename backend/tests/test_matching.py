import uuid
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.modules.cv_processing.models import CvProfile
from app.modules.jobs.models import Job
from app.modules.matching.schemas import (
    MatchCalculateRequest,
    LlmJudgeEvaluationSchema,
)
from app.modules.matching.service import (
    _normalize_skill,
    calculate_cosine_similarity,
    calculate_deterministic_score,
    calculate_semantic_score,
    calculate_match_scorecard,
)
from app.core.llm_client import generate_structured_json


def test_skill_normalization():
    assert _normalize_skill("  React.js  ") == "react"
    assert _normalize_skill("K8s") == "kubernetes"
    assert _normalize_skill("PostgreSQL") == "postgresql"
    assert _normalize_skill("AWS Cloud") == "aws"


def test_cosine_similarity():
    # Identical unit vectors -> 1.0
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert calculate_cosine_similarity(v1, v2) == 1.0

    # Orthogonal vectors -> 0.0
    v3 = [0.0, 1.0, 0.0]
    assert calculate_cosine_similarity(v1, v3) == 0.0

    # Opposite vectors -> clamped to 0.0
    v4 = [-1.0, 0.0, 0.0]
    assert calculate_cosine_similarity(v1, v4) == 0.0

    # Empty or mismatched vectors
    assert calculate_cosine_similarity([], []) == 0.0
    assert calculate_cosine_similarity([1.0], [1.0, 2.0]) == 0.0


def test_deterministic_score_perfect_fit():
    cv = CvProfile(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        raw_text="Experienced Kotlin and Android engineer with Jetpack Compose.",
        target_role="Senior Android Engineer",
        years_of_experience=5.0,
        skills=[
            {"name": "Kotlin", "years": 5.0, "source_quote": "Kotlin 5 years"},
            {"name": "Jetpack Compose", "years": 3.0, "source_quote": "Jetpack Compose"},
            {"name": "Coroutines", "years": 4.0, "source_quote": "Coroutines"},
        ],
    )
    job = Job(
        id=uuid.uuid4(),
        title="Senior Android Engineer",
        company_name="TechUA",
        location="Kyiv, Ukraine",
        region="UA",
        raw_description="Looking for Android lead",
        required_skills=["Kotlin", "Jetpack Compose"],
        preferred_skills=["Coroutines"],
        min_experience_years=4.0,
    )

    det_score, matching, missing, exp = calculate_deterministic_score(cv, job)

    assert det_score == 100.0
    assert len(matching) == 3
    assert len(missing) == 0
    assert exp.meets_requirement is True
    assert exp.delta_years == 1.0


def test_deterministic_score_with_gaps_and_deficit():
    cv = CvProfile(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        raw_text="Junior developer with basic Kotlin skills.",
        target_role="Junior Android Developer",
        years_of_experience=1.5,
        skills=[
            {"name": "Kotlin", "years": 1.5, "source_quote": "Kotlin basics"},
        ],
    )
    job = Job(
        id=uuid.uuid4(),
        title="Senior Android Engineer",
        company_name="GlobalApp",
        location="Remote",
        region="REMOTE",
        raw_description="Looking for senior engineer",
        required_skills=["Kotlin", "Jetpack Compose", "Coroutines", "KMP"],
        preferred_skills=["GraphQL"],
        min_experience_years=5.0,
    )

    det_score, matching, missing, exp = calculate_deterministic_score(cv, job)

    # 1 of 4 required skills = 25% * 70 = 17.5
    # 0 of 1 preferred skills = 0% * 15 = 0
    # 1.5 of 5.0 years = 30% * 15 = 4.5
    # Total deterministic = 17.5 + 4.5 = 22.0
    assert det_score == 22.0
    assert len(matching) == 1
    assert len(missing) == 4
    assert exp.meets_requirement is False
    assert exp.delta_years == -3.5


@pytest.mark.asyncio
async def test_3tier_scorecard_calculation_with_llm_judge():
    cv = CvProfile(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        raw_text="Lead Fullstack developer with 6 years experience in React, Next.js, and TypeScript.",
        target_role="Senior Frontend Engineer",
        years_of_experience=6.0,
        skills=[
            {"name": "React", "years": 6.0, "source_quote": "6 years React"},
            {"name": "Next.js", "years": 4.0, "source_quote": "Next.js production"},
            {"name": "TypeScript", "years": 5.0, "source_quote": "TypeScript"},
        ],
        embedding=[0.5] * 768,
    )
    job = Job(
        id=uuid.uuid4(),
        title="Senior React / Next.js Developer",
        company_name="VercelPartner",
        location="Kyiv / Remote",
        region="UA",
        raw_description="Senior React engineer needed.",
        required_skills=["React", "TypeScript"],
        preferred_skills=["Next.js", "TailwindCSS"],
        min_experience_years=5.0,
        embedding=[0.5] * 768,
    )

    mock_llm_judge_output = {
        "reasoning_score": 92.0,
        "strengths": ["Extensive React & Next.js production track record", "Strong TypeScript foundation"],
        "gaps": ["TailwindCSS not explicitly highlighted"],
        "recommendations": "Highlight UI styling portfolio and any performance optimizations.",
    }

    with patch(
        "app.modules.matching.service.generate_structured_json",
        new_callable=AsyncMock,
        return_value=mock_llm_judge_output,
    ):
        scorecard = await calculate_match_scorecard(cv, job, provider_override="azure")

        # Deterministic: Req (100% * 70) + Pref (50% * 15 = 7.5) + Exp (100% * 15) = 92.5
        assert scorecard.deterministic_score == 92.5
        # Semantic: identical vectors -> 100.0
        assert scorecard.semantic_score == 100.0
        # LLM Reasoning: 92.0
        assert scorecard.llm_reasoning_score == 92.0

        # Weighted: 0.35 * 92.5 + 0.35 * 100.0 + 0.30 * 92.0 = 94.975
        assert scorecard.overall_score == pytest.approx(94.98, abs=0.02)
        assert scorecard.llm_provider == "azure"


@pytest.mark.asyncio
async def test_azure_llm_client_rate_limit_resilience():
    """
    Simulates Azure OpenAI RateLimitError (HTTP 429 TPM exhaustion),
    verifying exponential backoff retries and subsequent success.
    """
    from openai import RateLimitError
    import httpx

    fake_request = httpx.Request("POST", "https://test.openai.azure.com")
    fake_response = httpx.Response(429, request=fake_request)
    rate_limit_err = RateLimitError("Rate limit exceeded", response=fake_response, body=None)

    mock_success_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '{"reasoning_score": 88.0, "strengths": ["Strong skills"], "gaps": [], "recommendations": "Keep it up"}'
    mock_success_response.choices = [mock_choice]

    mock_azure_client = MagicMock()
    # Fails twice with 429, succeeds on third attempt
    mock_azure_client.chat.completions.create = AsyncMock(
        side_effect=[rate_limit_err, rate_limit_err, mock_success_response]
    )

    with patch("app.core.llm_client.get_azure_client", return_value=mock_azure_client), \
         patch("app.core.llm_client.settings.AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com"), \
         patch("app.core.llm_client.settings.AZURE_OPENAI_API_KEY", "fake_key"), \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

        result = await generate_structured_json(
            prompt="Evaluate candidate",
            system_instruction="You are a judge",
            schema_class=LlmJudgeEvaluationSchema,
            provider_override="azure",
        )

        assert result["reasoning_score"] == 88.0
        # Verify that retries occurred (sleep called twice)
        assert mock_sleep.call_count == 2


@pytest.mark.asyncio
async def test_calculate_match_api_endpoint():
    cv_id = uuid.uuid4()
    job_id = uuid.uuid4()

    mock_response = {
        "id": str(uuid.uuid4()),
        "cv_profile_id": str(cv_id),
        "job_id": str(job_id),
        "job_title": "Senior Cloud Engineer",
        "company_name": "AzureUA",
        "location": "Kyiv, Ukraine",
        "region": "UA",
        "salary_min": 4500,
        "salary_max": 6000,
        "salary_currency": "USD",
        "scorecard": {
            "overall_score": 89.5,
            "deterministic_score": 90.0,
            "semantic_score": 88.0,
            "llm_reasoning_score": 91.0,
            "weights": {"deterministic": 0.35, "semantic": 0.35, "llm_reasoning": 0.30},
            "matching_skills": [{"skill": "Terraform", "evidence": "4 years", "is_required": True}],
            "missing_skills": [],
            "experience_analysis": {
                "candidate_years": 5.0,
                "required_years": 4.0,
                "meets_requirement": True,
                "delta_years": 1.0,
            },
            "recommendations": "Strong candidate. Emphasize multi-region Azure architecture.",
            "llm_provider": "azure",
        },
    }

    with patch(
        "app.modules.matching.router.evaluate_and_save_match",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            res = await client.post(
                "/api/v1/matching/calculate",
                json={
                    "cv_profile_id": str(cv_id),
                    "job_id": str(job_id),
                    "save_to_db": False,
                    "provider": "azure",
                },
            )
            assert res.status_code == 200
            data = res.json()
            assert data["scorecard"]["overall_score"] == 89.5
            assert data["scorecard"]["llm_provider"] == "azure"
            assert data["job_title"] == "Senior Cloud Engineer"

