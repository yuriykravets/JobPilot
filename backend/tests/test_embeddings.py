import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from sqlalchemy import select

from app.main import app
from app.core.database import AsyncSessionLocal
from app.modules.jobs.models import Job
from app.modules.matching.embeddings import (
    build_cv_embedding_text,
    build_job_embedding_text,
    generate_embedding,
)


def test_build_cv_embedding_text():
    text = build_cv_embedding_text(
        target_role="Senior Android Engineer",
        summary="Experienced mobile engineer building reactive apps in Kotlin.",
        skills=[{"name": "Kotlin"}, {"name": "Jetpack Compose"}, {"name": "Coroutines"}],
        work_experiences=[
            {
                "role": "Lead Android Dev",
                "company": "KyivStar",
                "responsibilities": ["Architected MVI app", "Led team of 5"],
            }
        ],
    )
    assert "Target Role: Senior Android Engineer" in text
    assert "Kotlin, Jetpack Compose, Coroutines" in text
    assert "Lead Android Dev at KyivStar" in text


def test_build_job_embedding_text():
    text = build_job_embedding_text(
        title="Senior Android Engineer",
        company="KyivStar",
        location="Kyiv, Ukraine",
        required_skills=["Kotlin", "Jetpack Compose"],
        preferred_skills=["KMP"],
        description="Looking for an experienced Android engineer with Jetpack Compose.",
    )
    assert "Job Title: Senior Android Engineer" in text
    assert "Company: KyivStar" in text
    assert "Must-have Skills: Kotlin, Jetpack Compose" in text


@pytest.mark.asyncio
async def test_generate_embedding_mocked():
    mock_vec = [0.05 * (i % 20) for i in range(768)]
    with patch(
        "app.modules.matching.embeddings.generate_embedding",
        new_callable=AsyncMock,
        return_value=mock_vec,
    ):
        vec = await generate_embedding("Kotlin Android Engineer")
        assert vec is not None
        assert len(vec) == 768


@pytest.mark.asyncio
async def test_backfill_embeddings_endpoint():
    mock_vec = [0.01 * (i % 10) for i in range(768)]
    with patch(
        "app.modules.jobs.service.generate_embedding",
        new_callable=AsyncMock,
        return_value=mock_vec,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            res = await client.post("/api/v1/jobs/generate-embeddings?limit=5")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "success"
            assert "embedded_jobs_count" in data
