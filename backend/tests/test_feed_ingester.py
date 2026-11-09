import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock

from app.main import app
from app.modules.jobs.feed_ingester import clean_html_text, parse_salary_string
from app.modules.jobs.schemas import JobCreateSchema, JobRegion


def test_clean_html_text():
    html_input = "<p>Looking for a <strong>Senior Android</strong> dev &amp; Kotlin expert.</p>"
    cleaned = clean_html_text(html_input)
    assert cleaned == "Looking for a Senior Android dev & Kotlin expert."


def test_parse_salary_string():
    min_sal, max_sal, curr = parse_salary_string("$80k - $120k")
    assert min_sal == 80000
    assert max_sal == 120000
    assert curr == "USD"

    min_sal_eur, max_sal_eur, curr_eur = parse_salary_string("€65,000 - €90,000")
    assert min_sal_eur == 65000
    assert max_sal_eur == 90000
    assert curr_eur == "EUR"

    empty_min, empty_max, empty_curr = parse_salary_string(None)
    assert empty_min is None
    assert empty_max is None
    assert empty_curr == "USD"


@pytest.mark.asyncio
async def test_sync_live_feeds_endpoint():
    mock_dou_jobs = [
        JobCreateSchema(
            title="Senior Android Engineer",
            company_name="VRG Soft",
            location="Dnipro, Ukraine",
            region=JobRegion.UA,
            raw_description="Looking for an experienced Android engineer with Jetpack Compose.",
            required_skills=["Kotlin", "Android SDK", "Jetpack Compose"],
            source_url="https://jobs.dou.ua/companies/vrg-soft/vacancies/54216/",
            external_id="dou-test-54216",
        )
    ]
    mock_remotive_jobs = [
        JobCreateSchema(
            title="Senior Full-Stack Developer",
            company_name="Fluence International",
            location="Remote (Worldwide)",
            region=JobRegion.REMOTE,
            raw_description="We are building Next.js and Python platforms for clinical research.",
            required_skills=["Next.js", "Python", "Docker"],
            source_url="https://remotive.com/remote-jobs/123",
            external_id="remotive-test-123",
        )
    ]

    with patch(
        "app.modules.jobs.feed_ingester.fetch_dou_jobs",
        new_callable=AsyncMock,
        return_value=mock_dou_jobs,
    ), patch(
        "app.modules.jobs.feed_ingester.fetch_remotive_jobs",
        new_callable=AsyncMock,
        return_value=mock_remotive_jobs,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            res = await client.post("/api/v1/jobs/sync-live-feeds")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "success"
            assert data["total_synced"] == 2
            assert data["dou_ua_count"] == 1
            assert data["remotive_global_count"] == 1
